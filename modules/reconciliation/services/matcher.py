from datetime import timedelta
from typing import Dict, List, Tuple

AMOUNT_TOLERANCE = 0.01          # absolute
DATE_WINDOW_DAYS = 2


def _ref_key(entry) -> str:
    return (getattr(entry, "reference", None)
            or getattr(entry, "external_id", None)
            or getattr(entry, "txn_ref", None)
            or "").strip().lower()


def _stmt_ref(line) -> str:
    return (getattr(line, "txn_ref", None) or "").strip().lower()


def _amounts_close(a: float, b: float) -> bool:
    return abs(a - b) <= AMOUNT_TOLERANCE


def _dates_close(d1, d2) -> bool:
    if not d1 or not d2:
        return False
    return abs((d1 - d2).days) <= DATE_WINDOW_DAYS


def _party_match(entry, line) -> bool:
    p = (getattr(entry, "party", None) or "").strip().lower()
    c = (getattr(line, "counterparty", None) or "").strip().lower()
    if not p or not c:
        return False
    return p == c or p in c or c in p


def run_reconciliation(ledger: List, statement: List) -> Tuple[List[Dict], List, List]:
    """
    Returns (pairs, unmatched_ledger, unmatched_statement)
    pairs: list of dicts {ledger_entry_id, statement_line_id, match_method, confidence}
    """
    used_stmt = set()
    used_ledger = set()
    pairs: List[Dict] = []

    # Pass 1 — exact reference match
    stmt_by_ref = {}
    for s in statement:
        stmt_by_ref.setdefault(_stmt_ref(s), []).append(s)

    for e in ledger:
        key = _ref_key(e)
        if not key or key not in stmt_by_ref:
            continue
        candidates = [s for s in stmt_by_ref[key] if id(s) not in used_stmt]
        if not candidates:
            continue
        s = candidates[0]
        pairs.append({
            "ledger_entry_id": e.id, "statement_line_id": s.id,
            "txn_ref": getattr(s, "txn_ref", None),
            "match_method": "exact_ref", "confidence": 1.0,
        })
        used_stmt.add(id(s)); used_ledger.add(id(e))

    # Pass 2 — amount + date + party
    remaining_l = [e for e in ledger if id(e) not in used_ledger]
    remaining_s = [s for s in statement if id(s) not in used_stmt]

    for e in remaining_l:
        for s in remaining_s:
            if id(s) in used_stmt:
                continue
            if (_amounts_close(e.amount, s.amount)
                    and _dates_close(e.entry_date, s.value_date)
                    and _party_match(e, s)):
                pairs.append({
                    "ledger_entry_id": e.id, "statement_line_id": s.id,
                    "txn_ref": getattr(s, "txn_ref", None),
                    "match_method": "amount_date_party", "confidence": 0.9,
                })
                used_stmt.add(id(s)); used_ledger.add(id(e))
                break

    # Pass 3 — amount + date only
    remaining_l = [e for e in ledger if id(e) not in used_ledger]
    remaining_s = [s for s in statement if id(s) not in used_stmt]

    for e in remaining_l:
        for s in remaining_s:
            if id(s) in used_stmt:
                continue
            if _amounts_close(e.amount, s.amount) and _dates_close(e.entry_date, s.value_date):
                pairs.append({
                    "ledger_entry_id": e.id, "statement_line_id": s.id,
                    "txn_ref": getattr(s, "txn_ref", None),
                    "match_method": "amount_date", "confidence": 0.75,
                })
                used_stmt.add(id(s)); used_ledger.add(id(e))
                break

    unmatched_l = [e for e in ledger if id(e) not in used_ledger]
    unmatched_s = [s for s in statement if id(s) not in used_stmt]
    return pairs, unmatched_l, unmatched_s