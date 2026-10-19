"""Cost Optimizer module tests"""
import pytest
import core.main  # noqa: F401 — triggers module registration

from modules.module_registry import registry

def test_module_registered():
    from modules.module_registry import registry
    m = registry.get("cost_optimizer")
    assert m is not None
    assert m.name == "cost_optimizer"
    assert m.version == "1.0.0"
    assert m.dependencies == ["fx_tool"]


def test_providers_seeded(client, auth_headers):
    r = client.get("/api/v1/cost/providers", headers=auth_headers)
    assert r.status_code == 200
    data = r.json()
    assert data["count"] >= 5
    names = [p["name"] for p in data["providers"]]
    assert "wise" in names
    assert "bank_wire" in names


def test_compare_endpoint(client, auth_headers):
    r = client.get(
        "/api/v1/cost/compare?base=USD&quote=INR&amount=1000",
        headers=auth_headers,
    )
    assert r.status_code == 200
    data = r.json()
    assert "results" in data
    assert len(data["results"]) >= 2
    # Verify sorted by total_cost ascending
    costs = [r["total_cost"] for r in data["results"]]
    assert costs == sorted(costs)
    # Best should be cheaper than worst
    assert data["best"]["total_cost"] <= data["worst"]["total_cost"]


def test_transparency_endpoint(client, auth_headers):
    r = client.get(
        "/api/v1/cost/transparency/wise?base=USD&quote=INR&amount=1000",
        headers=auth_headers,
    )
    assert r.status_code == 200
    data = r.json()
    assert data["provider"] == "wise"
    assert "transparency_score" in data
    assert 0.0 <= data["transparency_score"] <= 1.0