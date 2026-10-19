#!/usr/bin/env python3
"""
Astra Platform — Demo Seed Script
==================================
Resets module-specific data so a fresh demo starts from a known state.
Does NOT touch users, currencies, or FX rules (keeps login working).

Usage:
    python3 scripts/seed_demo.py
    python3 scripts/seed_demo.py --hard   # also wipe recon tables + re-seed providers

Design: Option A (soft reset). Safe to run repeatedly.
"""
import argparse
import glob
import logging
import os
import sqlite3
import sys

# Ensure project root is on sys.path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

logging.basicConfig(level=logging.INFO, format="%(message)s")
log = logging.getLogger("seed")


def find_db() -> str:
    """Locate the primary SQLite database file."""
    candidates = [p for p in glob.glob("*.db") if not p.endswith((".bak", ".backup"))]
    if not candidates:
        raise FileNotFoundError("No .db file found in project root")
    # Prefer astra.db if present
    for c in candidates:
        if c == "astra.db":
            return c
    return candidates[0]


def clear_recon_tables(db: str) -> None:
    """Clear reconciliation tables only."""
    tables = [
        "recon_matches",
        "recon_discrepancies",
        "recon_runs",
        "recon_statement_lines",
        "recon_statement_imports",
        "recon_ledger_entries",
    ]
    conn = sqlite3.connect(db)
    cleared = 0
    for t in tables:
        try:
            conn.execute(f"DELETE FROM {t}")
            cleared += 1
        except sqlite3.OperationalError as e:
            log.info(f"  skip {t}: {e}")
    conn.commit()
    conn.close()
    log.info(f"🧹 Cleared {cleared} reconciliation table(s)")


def clear_last_mile_status(db: str) -> None:
    """Clear any tracked payment statuses so demo statuses start empty."""
    tables = ["lastmile_status_events", "lastmile_payments", "payment_status_events"]
    conn = sqlite3.connect(db)
    cleared = 0
    for t in tables:
        try:
            conn.execute(f"DELETE FROM {t}")
            cleared += 1
        except sqlite3.OperationalError:
            pass
    conn.commit()
    conn.close()
    if cleared:
        log.info(f"🧹 Cleared {cleared} last_mile status table(s)")


def reseed_providers_and_banks() -> None:
    """
    Re-import modules so their on_startup() runs and re-seeds providers/banks.
    Since module seeds are idempotent (guard on existing rows), this is safe.
    """
    log.info("🌱 Re-seeding cost providers + banks...")
    from core.main import app  # noqa: F401 — triggers module registration
    from modules.module_registry import registry

    # initialize_all is idempotent via module_base._initialized guard
    registry.initialize_all(app)
    log.info("✅ Module seeds ensured")


def import_sample_recon_data() -> None:
    """Import the sample ledger + statement for the demo."""
    log.info("📥 Importing sample reconciliation data...")
    from datetime import datetime
    import json
    import csv
    import io
    from core.database import SessionLocal
    from modules.reconciliation.models import LedgerEntry, StatementImport, StatementLine

    db = SessionLocal()
    try:
        # ── ledger ──
        ledger_path = "modules/reconciliation/data/sample_ledger.json"
        if os.path.exists(ledger_path):
            with open(ledger_path) as f:
                payload = json.load(f)
            created = 0
            for e in payload.get("entries", []):
                db.add(LedgerEntry(
                    external_id=e["external_id"],
                    entry_date=datetime.fromisoformat(e["date"]),
                    amount=float(e["amount"]),
                    currency=e.get("currency", "USD"),
                    party=e.get("party"),
                    reference=e.get("reference"),
                    direction=e.get("direction", "debit"),
                    source="seed_demo",
                ))
                created += 1
            db.commit()
            log.info(f"   ledger: {created} entries")

        # ── statement ──
        # Use our own CSV parsing to avoid guessing the parser's return type.
        stmt_path = "modules/reconciliation/data/sample_statement.csv"
        if os.path.exists(stmt_path):
            with open(stmt_path, "r", newline="") as f:
                reader = csv.DictReader(f)
                rows = list(reader)

            imp = StatementImport(
                filename="sample_statement.csv",
                format="csv",
                line_count=len(rows),
            )
            db.add(imp)
            db.flush()  # populates imp.id

            for r in rows:
                # Sample CSV headers: txn_ref,value_date,amount,ccy,counterparty,narration,status
                value_date = None
                vd = r.get("value_date") or ""
                if vd:
                    try:
                        value_date = datetime.fromisoformat(vd)
                    except ValueError:
                        try:
                            value_date = datetime.strptime(vd, "%Y-%m-%d")
                        except ValueError:
                            value_date = None

                db.add(StatementLine(
                    import_id=imp.id,
                    txn_ref=r.get("txn_ref") or "",
                    value_date=value_date,
                    amount=float(r.get("amount") or 0),
                    currency=r.get("ccy") or "USD",
                    counterparty=r.get("counterparty"),
                    narration=r.get("narration"),
                    status=r.get("status"),
                ))
            db.commit()
            log.info(f"   statement: {len(rows)} lines (import_id={imp.id})")
    finally:
        db.close()

def main() -> None:
    parser = argparse.ArgumentParser(description="Astra demo seeder")
    parser.add_argument("--hard", action="store_true",
                        help="Also reseed providers/banks and import recon data")
    args = parser.parse_args()

    db = find_db()
    log.info(f"📂 Using DB: {db}")

    clear_recon_tables(db)
    clear_last_mile_status(db)

    if args.hard:
        reseed_providers_and_banks()
        import_sample_recon_data()
        log.info("✅ Hard reset complete — recon data ready to demo")
    else:
        log.info("✅ Soft reset complete — module tables cleared, "
                 "users/currencies/rules preserved")
        log.info("   Run with --hard to also re-seed providers and import recon data")


if __name__ == "__main__":
    main()