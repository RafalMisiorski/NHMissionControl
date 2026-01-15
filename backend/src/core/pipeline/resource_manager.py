"""
Resource Manager - Dynamic port allocation.

Manages port pools and allocations for pipeline runs.
"""

import asyncio
import logging
import socket
from datetime import datetime, timezone
from typing import Optional
from uuid import UUID, uuid4

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.models import ResourceAllocation, ResourceType

logger = logging.getLogger(__name__)


class ResourceManager:
    """
    Dynamic port allocation manager.

    Port Pools:
    - Frontend: 3000-3099
    - Backend: 8000-8099
    - Database: 5432-5499
    - Redis: 6379-6399
    - Test: 9000-9099

    Features:
    - Automatic port allocation from pools
    - Conflict detection
    - Graceful release on task completion
    - Persistent allocation tracking in database
    """

    # Port pool definitions
    PORT_POOLS = {
        "frontend": {
            "resource_type": ResourceType.FRONTEND_PORT,
            "start": 3000,
            "end": 3099,
            "default": 3000,
        },
        "backend": {
            "resource_type": ResourceType.BACKEND_PORT,
            "start": 8000,
            "end": 8099,
            "default": 8000,
        },
        "database": {
            "resource_type": ResourceType.DATABASE_PORT,
            "start": 5432,
            "end": 5499,
            "default": 5432,
        },
        "redis": {
            "resource_type": ResourceType.REDIS_PORT,
            "start": 6379,
            "end": 6399,
            "default": 6379,
        },
        "test": {
            "resource_type": ResourceType.TEST_PORT,
            "start": 9000,
            "end": 9099,
            "default": 9000,
        },
    }

    def __init__(self, db: AsyncSession):
        self.db = db
        self._lock = asyncio.Lock()

    async def allocate_port(
        self,
        task_id: str,
        category: str,
        preferred_port: Optional[int] = None,
        pipeline_run_id: Optional[str] = None,
    ) -> int:
        """
        Allocate a port from the specified pool.

        Args:
            task_id: Task identifier
            category: Port category (frontend, backend, database, redis, test)
            preferred_port: Optional preferred port to try first
            pipeline_run_id: Optional pipeline run reference

        Returns:
            Allocated port number

        Raises:
            ValueError: If category is invalid
            RuntimeError: If no ports available
        """
        if category not in self.PORT_POOLS:
            raise ValueError(f"Invalid category: {category}. Valid: {list(self.PORT_POOLS.keys())}")

        pool = self.PORT_POOLS[category]

        async with self._lock:
            # Get currently allocated ports for this category
            allocated = await self._get_allocated_ports(pool["resource_type"])

            # Try preferred port first
            if preferred_port and preferred_port not in allocated:
                if self._is_port_available(preferred_port):
                    return await self._create_allocation(
                        task_id=task_id,
                        resource_type=pool["resource_type"],
                        port=preferred_port,
                        pipeline_run_id=pipeline_run_id,
                    )

            # Try default port
            default = pool["default"]
            if default not in allocated and self._is_port_available(default):
                return await self._create_allocation(
                    task_id=task_id,
                    resource_type=pool["resource_type"],
                    port=default,
                    pipeline_run_id=pipeline_run_id,
                )

            # Find first available port in range
            for port in range(pool["start"], pool["end"] + 1):
                if port not in allocated and self._is_port_available(port):
                    return await self._create_allocation(
                        task_id=task_id,
                        resource_type=pool["resource_type"],
                        port=port,
                        pipeline_run_id=pipeline_run_id,
                    )

            raise RuntimeError(f"No available ports in {category} pool ({pool['start']}-{pool['end']})")

    async def release_port(self, port: int):
        """
        Release an allocated port.

        Args:
            port: Port number to release
        """
        async with self._lock:
            result = await self.db.execute(
                select(ResourceAllocation)
                .where(ResourceAllocation.value == port)
                .where(ResourceAllocation.is_active == True)
            )
            allocation = result.scalar_one_or_none()

            if allocation:
                allocation.is_active = False
                allocation.released_at = datetime.now(timezone.utc)
                await self.db.commit()
                logger.info(f"Released port {port}")
            else:
                logger.warning(f"Port {port} not found in active allocations")

    async def release_all(self, task_id: str):
        """
        Release all ports allocated to a task.

        Args:
            task_id: Task identifier
        """
        async with self._lock:
            result = await self.db.execute(
                select(ResourceAllocation)
                .where(ResourceAllocation.task_id == task_id)
                .where(ResourceAllocation.is_active == True)
            )
            allocations = result.scalars().all()

            for allocation in allocations:
                allocation.is_active = False
                allocation.released_at = datetime.now(timezone.utc)

            await self.db.commit()
            logger.info(f"Released {len(allocations)} ports for task {task_id}")

    async def get_allocations(self, task_id: str) -> dict[str, int]:
        """
        Get all active port allocations for a task.

        Args:
            task_id: Task identifier

        Returns:
            Dict mapping category to port number
        """
        result = await self.db.execute(
            select(ResourceAllocation)
            .where(ResourceAllocation.task_id == task_id)
            .where(ResourceAllocation.is_active == True)
        )
        allocations = result.scalars().all()

        # Map resource type back to category name
        type_to_category = {
            pool["resource_type"]: name
            for name, pool in self.PORT_POOLS.items()
        }

        return {
            type_to_category.get(a.resource_type, a.resource_type.value): a.value
            for a in allocations
        }

    async def get_pool_status(self) -> dict:
        """
        Get status of all port pools.

        Returns:
            Dict with pool statistics
        """
        status = {}

        for category, pool in self.PORT_POOLS.items():
            allocated = await self._get_allocated_ports(pool["resource_type"])
            total = pool["end"] - pool["start"] + 1

            status[category] = {
                "range": f"{pool['start']}-{pool['end']}",
                "total": total,
                "allocated": len(allocated),
                "available": total - len(allocated),
                "allocated_ports": list(allocated),
            }

        return status

    async def _get_allocated_ports(self, resource_type: ResourceType) -> set[int]:
        """Get all currently allocated ports for a resource type."""
        result = await self.db.execute(
            select(ResourceAllocation.value)
            .where(ResourceAllocation.resource_type == resource_type)
            .where(ResourceAllocation.is_active == True)
        )
        return set(result.scalars().all())

    async def _create_allocation(
        self,
        task_id: str,
        resource_type: ResourceType,
        port: int,
        pipeline_run_id: Optional[str] = None,
    ) -> int:
        """Create a new port allocation record."""
        allocation = ResourceAllocation(
            id=uuid4(),
            task_id=task_id,
            resource_type=resource_type,
            value=port,
            is_active=True,
            pipeline_run_id=UUID(pipeline_run_id) if pipeline_run_id else None,
        )

        self.db.add(allocation)
        await self.db.commit()

        logger.info(f"Allocated port {port} ({resource_type.value}) for task {task_id}")
        return port

    def _is_port_available(self, port: int) -> bool:
        """
        Check if a port is available on the system.

        Args:
            port: Port number to check

        Returns:
            True if port is available
        """
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.settimeout(1)
                result = s.connect_ex(("127.0.0.1", port))
                # If connect_ex returns non-zero, port is not in use
                return result != 0
        except Exception:
            # If we can't check, assume available
            return True

    async def find_available_port(
        self,
        category: str,
        exclude: Optional[set[int]] = None,
    ) -> Optional[int]:
        """
        Find an available port without allocating it.

        Args:
            category: Port category
            exclude: Ports to exclude

        Returns:
            Available port or None
        """
        if category not in self.PORT_POOLS:
            return None

        pool = self.PORT_POOLS[category]
        allocated = await self._get_allocated_ports(pool["resource_type"])
        exclude = exclude or set()

        for port in range(pool["start"], pool["end"] + 1):
            if port not in allocated and port not in exclude:
                if self._is_port_available(port):
                    return port

        return None

    async def cleanup_stale_allocations(self, max_age_hours: int = 24):
        """
        Clean up stale allocations older than max_age_hours.

        Args:
            max_age_hours: Maximum age in hours before cleanup
        """
        from datetime import timedelta

        cutoff = datetime.now(timezone.utc) - timedelta(hours=max_age_hours)

        result = await self.db.execute(
            select(ResourceAllocation)
            .where(ResourceAllocation.is_active == True)
            .where(ResourceAllocation.allocated_at < cutoff)
        )
        stale = result.scalars().all()

        for allocation in stale:
            allocation.is_active = False
            allocation.released_at = datetime.now(timezone.utc)

        await self.db.commit()

        if stale:
            logger.info(f"Cleaned up {len(stale)} stale resource allocations")
