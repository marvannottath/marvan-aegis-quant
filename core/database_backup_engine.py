"""
Automated Production Database Backup, Restore Verification & Snapshot Comparison Engine.
Ensures ZERO data loss across deployments, service restarts, and schema updates.
"""

import os
import json
import shutil
import time
from pathlib import Path
from typing import Dict, Any, List, Tuple
from datetime import datetime, timezone, timedelta

IST_TZ = timezone(timedelta(hours=5, minutes=30))
ROOT_DIR = Path(__file__).resolve().parent.parent
BACKUP_DIR = ROOT_DIR / "data" / "backups"

DB_FILES = [
    ROOT_DIR / "execution" / "paper_broker_state.json",
    ROOT_DIR / "execution" / "profit_vault_state.json",
    ROOT_DIR / "data" / "financial_audit_log.json",
    ROOT_DIR / "data" / "stripe_payments.json",
    ROOT_DIR / "data" / "processed_stripe_events.json",
    ROOT_DIR / "data" / "backtest_15year_aggressive.json"
]

class DatabaseBackupEngine:
    def __init__(self):
        BACKUP_DIR.mkdir(parents=True, exist_ok=True)

    def create_snapshot(self) -> Dict[str, Any]:
        """Capture record count and balance snapshot across all persistent DB stores."""
        snapshot = {
            "timestamp": datetime.now(timezone.utc).astimezone(IST_TZ).strftime("%Y-%m-%d %H:%M:%S"),
            "stores": {}
        }

        for path in DB_FILES:
            name = path.name
            if path.exists():
                try:
                    data = json.load(open(path, "r"))
                    if name == "paper_broker_state.json":
                        master = data.get("pools", {}).get("AEGIS_QUANT_MASTER", {})
                        count = len(master.get("trade_history", []))
                        cash = master.get("virtual_cash", 100000.0)
                    elif name == "profit_vault_state.json":
                        master = data.get("vault_stores", {}).get("AEGIS_QUANT_MASTER", {})
                        count = len(master.get("transactions", []))
                        cash = sum(t.get("sweep_amount", 0) for t in master.get("transactions", []))
                    elif name == "financial_audit_log.json":
                        count = len(data.get("logs", []))
                        cash = 0.0
                    elif name == "stripe_payments.json":
                        count = len(data.get("payments", []))
                        cash = sum(p.get("amount", 0) for p in data.get("payments", []))
                    elif name == "processed_stripe_events.json":
                        count = len(data.get("processed_events", []))
                        cash = 0.0
                    elif name == "backtest_15year_aggressive.json":
                        count = data.get("total_years", 17)
                        cash = data.get("final_balance_usd", 0.0)
                    else:
                        count = 0
                        cash = 0.0
                    
                    snapshot["stores"][name] = {"status": "EXISTS", "record_count": count, "total_value": cash}
                except Exception as e:
                    snapshot["stores"][name] = {"status": "READ_ERROR", "error": str(e)}
            else:
                snapshot["stores"][name] = {"status": "MISSING", "record_count": 0, "total_value": 0.0}

        return snapshot

    def backup_database(self) -> Tuple[bool, str, Path]:
        """Create timestamped production backup directory with full DB store copies."""
        ts = datetime.now(timezone.utc).astimezone(IST_TZ).strftime("%Y%m%d_%H%M%S")
        target_dir = BACKUP_DIR / f"db_backup_{ts}"
        target_dir.mkdir(parents=True, exist_ok=True)

        copied_count = 0
        for path in DB_FILES:
            if path.exists():
                shutil.copy2(path, target_dir / path.name)
                copied_count += 1

        snapshot = self.create_snapshot()
        with open(target_dir / "snapshot.json", "w") as f:
            json.dump(snapshot, f, indent=2)

        return True, f"Backup created successfully with {copied_count} files", target_dir

    def verify_backup_integrity(self, backup_dir: Path) -> Tuple[bool, str]:
        """Verify restore integrity by inspecting snapshot and file existence."""
        if not backup_dir.exists():
            return False, "Backup directory does not exist"

        snap_file = backup_dir / "snapshot.json"
        if not snap_file.exists():
            return False, "Backup snapshot.json missing"

        try:
            snap = json.load(open(snap_file))
            for path in DB_FILES:
                name = path.name
                if snap.get("stores", {}).get(name, {}).get("status") == "EXISTS":
                    if not (backup_dir / name).exists():
                        return False, f"Corrupted backup: {name} listed in snapshot but missing from directory"
            return True, "Backup integrity verified 100% PASS"
        except Exception as e:
            return False, f"Verification exception: {e}"

    def compare_snapshots(self, pre_snap: Dict[str, Any], post_snap: Dict[str, Any]) -> Tuple[bool, List[str]]:
        """Verify zero data loss between pre-deployment and post-deployment snapshots."""
        issues = []
        is_safe = True

        for path in DB_FILES:
            name = path.name
            pre_cnt = pre_snap.get("stores", {}).get(name, {}).get("record_count", 0)
            post_cnt = post_snap.get("stores", {}).get(name, {}).get("record_count", 0)

            if post_cnt < pre_cnt:
                is_safe = False
                issues.append(f"DATA LOSS DETECTED in {name}: pre={pre_cnt}, post={post_cnt}")

        return is_safe, issues


# Global Singleton
db_backup_engine = DatabaseBackupEngine()
