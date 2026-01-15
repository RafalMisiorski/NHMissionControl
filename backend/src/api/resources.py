"""
Resources API Routes.

REST endpoints for resource and port management.
"""

from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.database import get_db
from src.core.models import ResourceAllocation, ResourceType
from src.core.pipeline import ResourceManager

router = APIRouter(prefix="/api/v1/resources", tags=["resources"])


# ==========================================================================
# Schemas
# ==========================================================================

class PoolStatus(BaseModel):
    """Status of a single port pool."""
    range: str
    total: int
    allocated: int
    available: int
    allocated_ports: list[int]


class AllPoolsStatus(BaseModel):
    """Status of all port pools."""
    frontend: PoolStatus
    backend: PoolStatus
    database: PoolStatus
    redis: PoolStatus
    test: PoolStatus


class AllocationResponse(BaseModel):
    """Resource allocation response."""
    id: UUID
    task_id: str
    resource_type: str
    value: int
    is_active: bool
    allocated_at: str
    released_at: Optional[str]

    class Config:
        from_attributes = True


class AllocatePortRequest(BaseModel):
    """Request to allocate a port."""
    task_id: str = Field(..., description="Task identifier")
    category: str = Field(..., description="Port category: frontend, backend, database, redis, test")
    preferred_port: Optional[int] = Field(None, description="Preferred port number")


class AllocatePortResponse(BaseModel):
    """Response after port allocation."""
    port: int
    category: str
    task_id: str
    message: str


# ==========================================================================
# Endpoints
# ==========================================================================

@router.get("/ports", response_model=AllPoolsStatus)
async def get_port_status(
    db: AsyncSession = Depends(get_db),
):
    """
    Get status of all port pools.

    Returns allocated/available counts for each pool.
    """
    resource_manager = ResourceManager(db)
    pool_status = await resource_manager.get_pool_status()

    return AllPoolsStatus(
        frontend=PoolStatus(**pool_status.get("frontend", {})),
        backend=PoolStatus(**pool_status.get("backend", {})),
        database=PoolStatus(**pool_status.get("database", {})),
        redis=PoolStatus(**pool_status.get("redis", {})),
        test=PoolStatus(**pool_status.get("test", {})),
    )


@router.get("/ports/{category}")
async def get_pool_status(
    category: str,
    db: AsyncSession = Depends(get_db),
):
    """Get status of a specific port pool."""
    valid_categories = ["frontend", "backend", "database", "redis", "test"]

    if category not in valid_categories:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid category: {category}. Valid: {valid_categories}",
        )

    resource_manager = ResourceManager(db)
    pool_status = await resource_manager.get_pool_status()

    return PoolStatus(**pool_status.get(category, {}))


@router.get("/allocations/{task_id}")
async def get_task_allocations(
    task_id: str,
    db: AsyncSession = Depends(get_db),
):
    """
    Get all resource allocations for a task.

    Returns dict mapping category to port number.
    """
    resource_manager = ResourceManager(db)
    allocations = await resource_manager.get_allocations(task_id)

    if not allocations:
        return {"task_id": task_id, "allocations": {}, "message": "No active allocations"}

    return {
        "task_id": task_id,
        "allocations": allocations,
        "message": f"{len(allocations)} active allocations",
    }


@router.get("/allocations")
async def list_all_allocations(
    active_only: bool = True,
    category: Optional[str] = None,
    limit: int = 100,
    db: AsyncSession = Depends(get_db),
):
    """
    List all resource allocations.

    Args:
        active_only: Only show active allocations
        category: Filter by category
        limit: Maximum results
    """
    query = select(ResourceAllocation).limit(limit)

    if active_only:
        query = query.where(ResourceAllocation.is_active == True)

    if category:
        # Map category name to resource type
        category_map = {
            "frontend": ResourceType.FRONTEND_PORT,
            "backend": ResourceType.BACKEND_PORT,
            "database": ResourceType.DATABASE_PORT,
            "redis": ResourceType.REDIS_PORT,
            "test": ResourceType.TEST_PORT,
        }
        resource_type = category_map.get(category)
        if resource_type:
            query = query.where(ResourceAllocation.resource_type == resource_type)

    result = await db.execute(query.order_by(ResourceAllocation.allocated_at.desc()))
    allocations = result.scalars().all()

    return [_allocation_to_response(a) for a in allocations]


@router.post("/ports/allocate", response_model=AllocatePortResponse)
async def allocate_port(
    request: AllocatePortRequest,
    db: AsyncSession = Depends(get_db),
):
    """
    Allocate a port from a pool.

    Automatically selects an available port, preferring the preferred_port if provided.
    """
    resource_manager = ResourceManager(db)

    try:
        port = await resource_manager.allocate_port(
            task_id=request.task_id,
            category=request.category,
            preferred_port=request.preferred_port,
        )

        return AllocatePortResponse(
            port=port,
            category=request.category,
            task_id=request.task_id,
            message=f"Allocated port {port} from {request.category} pool",
        )

    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )
    except RuntimeError as e:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=str(e),
        )


@router.post("/ports/{port}/release")
async def release_port(
    port: int,
    db: AsyncSession = Depends(get_db),
):
    """Release a specific port back to its pool."""
    resource_manager = ResourceManager(db)
    await resource_manager.release_port(port)

    return {"port": port, "status": "released", "message": f"Port {port} released"}


@router.post("/allocations/{task_id}/release-all")
async def release_all_task_allocations(
    task_id: str,
    db: AsyncSession = Depends(get_db),
):
    """Release all allocations for a task."""
    resource_manager = ResourceManager(db)

    # Get count before release
    allocations = await resource_manager.get_allocations(task_id)
    count = len(allocations)

    await resource_manager.release_all(task_id)

    return {
        "task_id": task_id,
        "released_count": count,
        "message": f"Released {count} allocations for task {task_id}",
    }


@router.post("/cleanup-stale")
async def cleanup_stale_allocations(
    max_age_hours: int = 24,
    db: AsyncSession = Depends(get_db),
):
    """
    Clean up stale allocations older than max_age_hours.

    Useful for recovering ports from abandoned tasks.
    """
    resource_manager = ResourceManager(db)
    await resource_manager.cleanup_stale_allocations(max_age_hours)

    return {
        "status": "completed",
        "message": f"Cleaned up allocations older than {max_age_hours} hours",
    }


@router.get("/find-available/{category}")
async def find_available_port(
    category: str,
    exclude: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
):
    """
    Find an available port without allocating it.

    Args:
        category: Port category
        exclude: Comma-separated list of ports to exclude
    """
    resource_manager = ResourceManager(db)

    exclude_set = set()
    if exclude:
        try:
            exclude_set = {int(p.strip()) for p in exclude.split(",")}
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid exclude parameter. Use comma-separated port numbers.",
            )

    port = await resource_manager.find_available_port(category, exclude_set)

    if port:
        return {"category": category, "available_port": port}
    else:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"No available ports in {category} pool",
        )


# ==========================================================================
# Helper Functions
# ==========================================================================

def _allocation_to_response(alloc: ResourceAllocation) -> AllocationResponse:
    """Convert allocation to response model."""
    return AllocationResponse(
        id=alloc.id,
        task_id=alloc.task_id,
        resource_type=alloc.resource_type.value,
        value=alloc.value,
        is_active=alloc.is_active,
        allocated_at=alloc.allocated_at.isoformat() if alloc.allocated_at else None,
        released_at=alloc.released_at.isoformat() if alloc.released_at else None,
    )
