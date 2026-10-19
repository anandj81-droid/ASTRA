import csv
import io
import json
from datetime import datetime
from typing import Dict, List


REQUIRED_CSV_COLS = {"txn_ref", "value_date", "amount", "ccy"}


def _parse_dt(value: str) -> datetime:
    value = (value or "").strip()
    for fmt in ("%Y-%m-%d", "%Y-%m-%dT%H:%M:%S", "%Y-%m-%d %H:%M:%S", "%d-%m-%Y"):
        try:
            return datetime.strptime(value, fmt)
        except ValueError:
            continue
    # last resort
    return datetime.fromisoformat(value)


def parse_statement_csv(raw: str) -> List[Dict]:
    reader = csv.DictReader(io.StringIO(raw))
    if not reader.fieldnames:
        raise ValueError("Empty CSV")
    cols = {c.strip().lower() for c in reader.fieldnames}
    if not REQUIRED_CSV_COLS.issubset(cols):
        missing = REQUIRED_CSV_COLS - cols
        raise ValueError(f"Missing required columns: {sorted(missing)}")
    out: List[Dict] = []
    for row in reader:
        row = {k.strip().lower(): (v or "").strip() for k, v in row.items() if k}
        if not row.get("txn_ref"):
            continue
        out.append({
            "txn_ref": row["txn_ref"],
            "value_date": _parse_dt(row.get("value_date", "")),
            "amount": float(row.get("amount", 0) or 0),
            "currency": (row.get("ccy") or "INR").upper(),
            "counterparty": row.get("counterparty") or None,
            "narration": row.get("narration") or None,
            "status": row.get("status") or None,
        })
    return out


def parse_statement_json(raw: str) -> List[Dict]:
    data = json.loads(raw)
    if isinstance(data, dict):
        data = data.get("lines") or data.get("items") or []
    if not isinstance(data, list):
        raise ValueError("JSON must be a list or {lines:[...]}")
    out: List[Dict] = []
    for row in data:
        ref = str(row.get("txn_ref") or row.get("reference") or "").strip()
        if not ref:
            continue
        vd = row.get("value_date") or row.get("date")
        out.append({
            "txn_ref": ref,
            "value_date": _parse_dt(str(vd)) if vd else None,
            "amount": float(row.get("amount", 0) or 0),
            "currency": str(row.get("currency") or row.get("ccy") or "INR").upper(),
            "counterparty": row.get("counterparty") or row.get("party") or None,
            "narration": row.get("narration") or None,
            "status": row.get("status") or None,
        })
    return out


def parse_statement(raw: str, fmt: str) -> List[Dict]:
    fmt = (fmt or "").lower()
    if fmt == "json":
        return parse_statement_json(raw)
    return parse_statement_csv(raw)