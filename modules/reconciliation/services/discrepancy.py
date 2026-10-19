from typing import Dict, List
from collections import defaultdict


def _ref_of_stmt(s) -> str:
    """Normalized txn_ref for a statement line (empty string if missing)."""
    return (getattr(s, "txn_ref", "") or "").strip().lower()


def _ref_of_pair(p: Dict) -> str:
    """Normalized txn_ref stored on a match pair dict (empty string if missing)."""
    # matcher.py stores the statement ref under one of these keys
    for k in ("txn_ref", "statement_ref", "reference", "ref"):
        v = p.get(k) if isinstance(p, dict) else None
        if v:
            return str(v).strip().lower()
    return ""


def classify_run(run_id: int, unmatched_ledger: List, unmatched_statement: List,
                 pairs: List[Dict]) -> List[Dict]:
    out: List[Dict] = []

    # ---------------------------------------------------------------------
    # 1. Count how many statement lines share each ref across BOTH pairs
    #    (already matched) and unmatched_statement (still pending).
    #
    #    A ref that appears >1 time total is duplicated. The FIRST
    #    occurrence (whether it landed in pairs or in us) is the primary;
    #    every subsequent occurrence that is still in `us` is a duplicate.
    # ---------------------------------------------------------------------
    ref_total: Dict[str, int] = defaultdict(int)

    for p in pairs:
        k = _ref_of_pair(p)
        if k:
            ref_total[k] += 1

    for s in unmatched_statement:
        k = _ref_of_stmt(s)
        if k:
            ref_total[k] += 1

    # A ref is duplicated if it appeared more than once in total
    duplicated_refs = {k for k, n in ref_total.items() if n > 1}

    # ---------------------------------------------------------------------
    # 2. Decide which unmatched statement lines are duplicates.
    #
    #    We walk the unmatched statement lines in their original order and
    #    keep a per-ref counter starting from however many instances were
    #    already consumed into `pairs`. The first unmatched instance of a
    #    duplicated ref is the *primary* (only if no pair already holds
    #    it); every instance after the first is a duplicate.
    # ---------------------------------------------------------------------
    seen_in_pairs: Dict[str, int] = defaultdict(int)
    for p in pairs:
        k = _ref_of_pair(p)
        if k:
            seen_in_pairs[k] += 1

    duplicate_stmt_ids = set()
    emitted_primary: Dict[str, int] = defaultdict(int)  # count of primaries per ref

    for s in unmatched_statement:
        k = _ref_of_stmt(s)
        if not k or k not in duplicated_refs:
            continue
        # How many of this ref have we already accounted for?
        already = seen_in_pairs.get(k, 0) + emitted_primary.get(k, 0)
        if already >= 1:
            # The ref is already represented (in pairs or by an earlier
            # unmatched line) → this line is a duplicate.
            duplicate_stmt_ids.add(s.id)
        else:
            # First time we see this duplicated ref with no pair holding
            # it → this unmatched line is the primary, not a duplicate.
            emitted_primary[k] += 1

    # ---------------------------------------------------------------------
    # 3. missing_in_statement — one entry per unmatched ledger row
    # ---------------------------------------------------------------------
    for e in unmatched_ledger:
        out.append({
            "run_id": run_id,
            "type": "missing_in_statement",
            "ledger_entry_id": e.id,
            "statement_line_id": None,
            "detail": (f"Ledger {getattr(e, 'external_id', e.id)} "
                       f"({getattr(e, 'currency', '?')} {getattr(e, 'amount', '?')}) "
                       f"has no statement line"),
            "status": "open",
        })

    # ---------------------------------------------------------------------
    # 4. missing_in_ledger — unmatched statement lines that are NOT dupes
    # ---------------------------------------------------------------------
    for s in unmatched_statement:
        if s.id in duplicate_stmt_ids:
            continue
        out.append({
            "run_id": run_id,
            "type": "missing_in_ledger",
            "ledger_entry_id": None,
            "statement_line_id": s.id,
            "detail": (f"Statement {getattr(s, 'txn_ref', '?')} "
                       f"({getattr(s, 'currency', '?')} {getattr(s, 'amount', '?')}) "
                       f"has no ledger entry"),
            "status": "open",
        })

    # ---------------------------------------------------------------------
    # 5. duplicate — one entry per extra occurrence still sitting in `us`
    # ---------------------------------------------------------------------
    for s in unmatched_statement:
        if s.id in duplicate_stmt_ids:
            out.append({
                "run_id": run_id,
                "type": "duplicate",
                "ledger_entry_id": None,
                "statement_line_id": s.id,
                "detail": f"Duplicate statement ref: {_ref_of_stmt(s)}",
                "status": "open",
            })

    return out