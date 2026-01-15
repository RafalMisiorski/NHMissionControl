#!/usr/bin/env python3
"""
Unlock an epoch - Requires explicit confirmation.
"""

import sys
import yaml
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from nh_guardian.epoch_hashes import EpochHashStore


def unlock_epoch(epoch_id: str, reason: str, repo_path: Path = None) -> bool:
    """Unlock an epoch for modification."""
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

    if epoch_config.get("status") != "LOCKED":
        print(f"Warning: Epoch {epoch_id} is not locked (status: {epoch_config.get('status')})")
        return True

    # Log the unlock
    unlock_log = repo_path / "data" / "unlock_log.txt"
    unlock_log.parent.mkdir(parents=True, exist_ok=True)

    with open(unlock_log, "a") as f:
        f.write(f"{datetime.now().isoformat()} | UNLOCK | {epoch_id} | {reason}\n")

    # Update manifest
    manifest["epochs"][epoch_id]["status"] = "ACTIVE"
    manifest["epochs"][epoch_id]["unlocked_at"] = datetime.now().isoformat()
    manifest["epochs"][epoch_id]["unlock_reason"] = reason

    # Move protected_paths back to active_paths
    if "protected_paths" in manifest["epochs"][epoch_id]:
        manifest["epochs"][epoch_id]["active_paths"] = manifest["epochs"][epoch_id].pop("protected_paths")

    with open(manifest_path, "w") as f:
        yaml.dump(manifest, f, default_flow_style=False)

    # Remove stored hashes (they're now invalid)
    hash_store = EpochHashStore(repo_path)
    hash_store.remove_epoch(epoch_id)

    print(f"\nEpoch {epoch_id} unlocked!")
    print(f"  Reason: {reason}")
    print(f"  WARNING: Remember to re-lock when modifications are complete!")

    return True


if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Usage: python unlock_epoch.py <epoch_id> <reason> [repo_path]")
        print("\nExample: python unlock_epoch.py epoch1 'Fix critical auth bug'")
        sys.exit(1)

    epoch_id = sys.argv[1]
    reason = sys.argv[2]
    repo_path = Path(sys.argv[3]) if len(sys.argv) > 3 else Path(".")

    # Require confirmation
    print(f"\nWARNING: You are about to unlock {epoch_id}")
    print(f"Reason: {reason}")
    confirm = input("Type 'UNLOCK' to confirm: ")

    if confirm != "UNLOCK":
        print("Aborted.")
        sys.exit(1)

    success = unlock_epoch(epoch_id, reason, repo_path)
    sys.exit(0 if success else 1)
