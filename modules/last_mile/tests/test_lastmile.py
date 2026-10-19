"""
Pytest suite for the Last Mile Expediter module.

Run from project root:
    pytest modules/last_mile/tests/ -v
"""
import pytest
from fastapi.testclient import TestClient


@pytest.fixture(scope="module")
def client():
    from core.main import app
    with TestClient(app) as c:
        yield c


# ─── Module registration ───

def test_last_mile_registered(client):
    r = client.get("/modules")
    assert r.status_code == 200
    names = [m["name"] for m in r.json()["modules"]]
    assert "last_mile" in names


def test_last_mile_reports_correct_prefix(client):
    r = client.get("/modules")
    mods = {m["name"]: m for m in r.json()["modules"]}
    assert mods["last_mile"]["api_prefix"] == "/api/v1/lastmile"


# ─── Banks ───

def test_list_banks(client):
    r = client.get("/api/v1/lastmile/banks")
    assert r.status_code == 200
    banks = r.json()
    assert isinstance(banks, list)
    assert len(banks) >= 5
    codes = [b["code"] for b in banks]
    for expected in ("hdfc", "icici", "sbi", "axis", "kotak"):
        assert expected in codes


def test_bank_performance_hdfc(client):
    r = client.get("/api/v1/lastmile/banks/hdfc/performance")
    assert r.status_code == 200
    data = r.json()
    assert data["bank_code"] == "hdfc"
    assert any(c["corridor"] == "USD-INR" for c in data["corridors"])
    usd_inr = next(c for c in data["corridors"] if c["corridor"] == "USD-INR")
    assert 0 < usd_inr["success_rate"] <= 1
    assert usd_inr["total"] >= 1


def test_bank_performance_unknown(client):
    r = client.get("/api/v1/lastmile/banks/nonexistent/performance")
    assert r.status_code == 404


# ─── Routing ───

def test_route_balanced_usd_inr(client):
    r = client.post("/api/v1/lastmile/route", json={
        "source_currency": "USD",
        "target_currency": "INR",
        "amount": 5000,
        "strategy": "balanced",
    })
    assert r.status_code == 200
    data = r.json()
    assert data["corridor"] == "USD-INR"
    assert data["recommended"] is not None
    assert data["recommended"]["bank_code"] in {"hdfc", "icici", "sbi", "axis", "kotak"}
    assert 0 <= data["recommended"]["score"] <= 1
    assert len(data["alternatives"]) >= 1


def test_route_fastest_prefers_quick_settlement(client):
    """ICICI settles in 5400s vs HDFC 7200s — fastest strategy should pick ICICI."""
    r = client.post("/api/v1/lastmile/route", json={
        "source_currency": "USD", "target_currency": "INR",
        "amount": 5000, "strategy": "fastest",
    })
    assert r.status_code == 200
    assert r.json()["recommended"]["bank_code"] == "icici"


def test_route_unknown_corridor(client):
    r = client.post("/api/v1/lastmile/route", json={
        "source_currency": "XYZ", "target_currency": "ABC",
        "amount": 100, "strategy": "balanced",
    })
    assert r.status_code == 200
    assert r.json()["recommended"] is None


# ─── Status tracking ───

def test_status_lifecycle(client):
    ref = "PAY-PYTEST-001"
    r1 = client.post(f"/api/v1/lastmile/status/{ref}/event",
                     json={"status": "initiated", "detail": "py pytest"})
    assert r1.status_code == 200
    assert r1.json()["status"] == "initiated"

    r2 = client.post(f"/api/v1/lastmile/status/{ref}/event",
                     json={"status": "settled", "detail": "credited"})
    assert r2.status_code == 200

    r3 = client.get(f"/api/v1/lastmile/status/{ref}")
    assert r3.status_code == 200
    data = r3.json()
    assert data["current_status"] == "settled"
    assert len(data["events"]) >= 2
    assert data["events"][0]["status"] == "initiated"
    assert data["events"][-1]["status"] == "settled"


def test_status_invalid_value(client):
    ref = "PAY-PYTEST-BAD"
    r = client.post(f"/api/v1/lastmile/status/{ref}/event",
                    json={"status": "bogus_status"})
    assert r.status_code == 200
    assert "error" in r.json()


def test_status_unknown_ref_returns_empty(client):
    r = client.get("/api/v1/lastmile/status/NEVER-SEEN")
    assert r.status_code == 200
    data = r.json()
    assert data["current_status"] is None
    assert data["events"] == []