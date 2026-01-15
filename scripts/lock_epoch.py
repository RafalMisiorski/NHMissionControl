#!/usr/bin/env python3
"""
Lock an epoch - Generate hashes and mark as LOCKED.
"""

import sys
import yaml
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from nh_guardian.verify_epochs import hash_file
from nh_guardian.epoch_hashes import EpochHashStore


def lock_epoch(epoch_id: str, repo_path: Path = None) -> bool:
    """Lock an epoch by generating and storing hashes."""
    repo_path = repo_path or Path(".")

    # Load manifest
    manifest_path = repo_path / "epochs" / "epoch_manifest.yaml"
    if not manifest_path.exists():
        print(f"Error: Manifest not found at {manifest_path}")
        return False

    with open(manifest_path) as f:
        manifest = yaml.safe_load(f)

    epoch_config = manifest.get("epochs", {}).get(epoch_id)
    if not epoch_config:
        print(f"Error: Epoch {epoch_id} not found in manifest")
        return False

    if epoch_config.get("status") == "LOCKED":
        print(f"Warning: Epoch {epoch_id} is already locked")
        return True

    # Get protected paths
    protected_paths = epoch_config.get("protected_paths", [])
    if not protected_paths:
        # Use active_paths if no protected_paths defined
        protected_paths = epoch_config.get("active_paths", [])

    # Generate hashes for all files
    hash_store = EpochHashStore(repo_path)
    hashes = {}

    for path_pattern in protected_paths:
        if "*" in path_pattern:
            base_path = repo_path / path_pattern.split("*")[0].rstrip("/")
            if base_path.exists():
                for filepath in base_path.rglob("*"):
                    if filepath.is_file():
                        relative_path = str(filepath.relative_to(repo_path))
                        hashes[relative_path] = hash_file(filepath)
                        print(f"  Hashed: {relative_path}")
        else:
            filepath = repo_path / path_pattern
            if filepath.exists() and filepath.is_file():
                relative_path = str(filepath.relative_to(repo_path))
                hashes[relative_path] = hash_file(filepath)
                print(f"  Hashed: {relative_path}")

    # Store hashes
    hash_store.set_epoch_hashes(epoch_id, hashes)

    # Update manifest
    manifest["epochs"][epoch_id]["status"] = "LOCKED"
    manifest["epochs"][epoch_id]["locked_at"] = str(Path.ctime(Path(".")))

    # Move active_paths to protected_paths
    if "active_paths" in manifest["epochs"][epoch_id]:
        manifest["epochs"][epoch_id]["protected_paths"] = manifest["epochs"][epoch_id].pop("active_paths")

    with open(manifest_path, "w") as f:
        yaml.dump(manifest, f, default_flow_style=False)

    print(f"\nEpoch {epoch_id} locked successfully!")
    print(f"  Files locked: {len(hashes)}")

    return True


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python lock_epoch.py <epoch_id> [repo_path]")
        sys.exit(1)

    epoch_id = sys.argv[1]
    repo_path = Path(sys.argv[2]) if len(sys.argv) > 2 else Path(".")

    success = lock_epoch(epoch_id, repo_path)
    sys.exit(0 if success else 1)
