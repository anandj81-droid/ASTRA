import io
import json
import os
from datetime import datetime

import pytest

from modules.reconciliation.services.statement_parser import (
    parse_statement_csv, parse_statement_json, parse_statement
)
from modules.reconciliation.services.matcher import run_reconciliation
from modules.reconciliation.services.discrepancy import classify_run


DATA_DIR = os.path.join(os.path.dirname(__file__), "..", "data")


class _E:
    """Lightweight stand-in for LedgerEntry in matcher tests."""
    def __init__(self, id, external_id, date, amount, currency="USD",
                 party=None, reference=None):
        self.id = id
        self.external_id = external_id
        self.entry_date = date
        self.amount = amount
        self.currency = currency
        self.party = party
        self.reference = reference or external_id


class _S:
    """Lightweight stand-in for StatementLine."""
    def __init__(self, id, txn_ref, date, amount, currency="USD", counterparty=None):
        self.id = id
        self.txn_ref = txn_ref
        self.value_date = date
        self.amount = amount
        self.currency = currency
        self.counterparty = counterparty


def test_parse_csv_sample():
    with open(os.path.join(DATA_DIR, "sample_statement.csv")) as f:
        lines = parse_statement_csv(f.read())
    assert len(lines) == 10
    assert lines[0]["txn_ref"] == "FX-1001"
    assert lines[0]["currency"] == "USD"


def test_parse_json_sample():
    with open(os.path.join(DATA_DIR, "sample_statement.json")) as f:
        lines = parse_statement_json(f.read())
    assert len(lines) == 10
    assert {l["txn_ref"] for l in lines} >= {"FX-1001", "FX-9999"}


def test_parse_csv_missing_columns_raises():
    with pytest.raises(ValueError):
        parse_statement_csv("foo,bar\n1,2\n")


def test_parse_statement_dispatch():
    raw = "txn_ref,value_date,amount,ccy\nA,2026-01-01,10,USD\n"
    assert len(parse_statement(raw, "csv")) == 1


def test_exact_ref_match():
    d = datetime(2026, 3, 1)
    ledger = [_E(1, "FX-1001", d, 1000.0, party="Acme Exports")]
    stmt = [_S(1, "FX-1001", d, 1000.0, counterparty="Acme Exports")]
    pairs, ul, us = run_reconciliation(ledger, stmt)
    assert len(pairs) == 1
    assert pairs[0]["match_method"] == "exact_ref"
    assert pairs[0]["confidence"] == 1.0
    assert not ul and not us


def test_amount_date_party_match():
    d = datetime(2026, 3, 2)
    ledger = [_E(1, "L-1", d, 2500.0, party="Beta Trading", reference="REF-A")]
    stmt = [_S(1, "STMT-XYZ", d, 2500.0, counterparty="Beta Trading")]
    pairs, ul, us = run_reconciliation(ledger, stmt)
    assert len(pairs) == 1
    assert pairs[0]["match_method"] == "amount_date_party"


def test_amount_date_only_match():
    d = datetime(2026, 3, 3)
    ledger = [_E(1, "L-2", d, 500.0, party="Nobody", reference="REF-B")]
    stmt = [_S(1, "STMT-OTHER", d, 500.0, counterparty="Somebody Else")]
    pairs, ul, us = run_reconciliation(ledger, stmt)
    assert len(pairs) == 1
    assert pairs[0]["match_method"] == "amount_date"


def test_unmatched_both_sides():
    d = datetime(2026, 3, 4)
    ledger = [_E(1, "L-3", d, 999.0, reference="REF-C")]
    stmt = [_S(1, "STMT-C", d, 111.0)]
    pairs, ul, us = run_reconciliation(ledger, stmt)
    assert not pairs
    assert len(ul) == 1 and len(us) == 1


def test_classify_missing_in_statement():
    d = datetime(2026, 3, 5)
    e = _E(1, "FX-1006", d, 450.0)
    out = classify_run(1, [e], [], [])
    assert out[0]["type"] == "missing_in_statement"
    assert out[0]["ledger_entry_id"] == 1


def test_classify_missing_in_ledger():
    d = datetime(2026, 3, 5)
    s = _S(1, "FX-9999", d, 300.0)
    out = classify_run(1, [], [s], [])
    assert out[0]["type"] == "missing_in_ledger"
    assert out[0]["statement_line_id"] == 1


def test_classify_duplicate():
    d = datetime(2026, 3, 5)
    s1 = _S(1, "FX-1008", d, 1100.0)
    s2 = _S(2, "FX-1008", d, 1100.0)
    out = classify_run(1, [], [s1, s2], [])
    types = [d["type"] for d in out]
    assert "duplicate" in types


def test_full_sample_run():
    """End-to-end on the seeded samples: expect 8 matches, some discrepancies."""
    with open(os.path.join(DATA_DIR, "sample_statement.csv")) as f:
        stmt_lines = parse_statement_csv(f.read())
    with open(os.path.join(DATA_DIR, "sample_ledger.json")) as f:
        ledger_rows = json.load(f)["entries"]

    ledger = [
        _E(i + 1, r["external_id"], datetime.fromisoformat(r["date"]),
           r["amount"], r.get("currency", "USD"),
           r.get("party"), r.get("reference"))
        for i, r in enumerate(ledger_rows)
    ]
    stmt = [
        _S(i + 1, r["txn_ref"], r["value_date"], r["amount"],
           r.get("currency", "USD"), r.get("counterparty"))
        for i, r in enumerate(stmt_lines)
    ]

    pairs, ul, us = run_reconciliation(ledger, stmt)
    # 8 unique refs match; the duplicate line cannot match
    assert len(pairs) == 8
    assert len(us) == 2   # dup FX-1008 (2nd) + FX-9999
    assert len(ul) == 2   # FX-1006 + FX-1009

    disc = classify_run(1, ul, us, pairs)
    types = sorted({d["type"] for d in disc})
    assert types == ["duplicate", "missing_in_ledger", "missing_in_statement"]