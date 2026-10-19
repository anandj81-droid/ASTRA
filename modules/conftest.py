# modules/conftest.py
"""
Shared pytest fixtures for all module tests.

- Registers all modules ONCE per session so registry.get(name) works in tests.
- Provides `client` (FastAPI TestClient) with startup triggered.
- Provides `auth_headers` (JWT bearer token for the seeded test user).
"""
import os
import sys
import pytest

# Ensure project root is importable
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))


@pytest.fixture(scope="session", autouse=True)
def _register_modules_once():
    """Autouse session fixture: import the app so all modules register."""
    # Importing core.main executes register_all_modules() and mounts routes.
    from core.main import app   # noqa: F401
    return app


@pytest.fixture(scope="session")
def app_instance(_register_modules_once):
    from core.main import app
    return app


@pytest.fixture()
def client(app_instance):
    """
    TestClient WITHOUT triggering the app's startup handlers.
    (Some tests want registry state but not DB seeding / route binding
    side effects. Use `client_started` if you need startup run.)
    """
    from fastapi.testclient import TestClient
    return TestClient(app_instance)


@pytest.fixture(scope="session")
def client_started(app_instance):
    """
    TestClient WITH startup/shutdown events fired.
    Use this for endpoint tests that rely on module on_startup() seeding.
    """
    from fastapi.testclient import TestClient
    with TestClient(app_instance) as c:
        yield c


@pytest.fixture()
def auth_headers(client_started):
    """
    Bearer token for the seeded test user.
    Falls back to a locally-minted token if /auth/login is unavailable.
    """
    r = client_started.post(
        "/auth/login",
        json={"email": "test@astra.com", "password": "Test@123"},
    )
    if r.status_code == 200:
        token = r.json()["access_token"]
    else:
        # Fallback: mint directly via core.auth (adjust if your helper differs)
        from core.auth import create_access_token  # type: ignore
        token = create_access_token({"sub": "test@astra.com"})
    return {"Authorization": f"Bearer {token}"}