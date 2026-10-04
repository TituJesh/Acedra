from unittest.mock import MagicMock
from fastapi import status
from app.dependencies import get_db
from app.main import app


def test_root_endpoint(client):
    """Test the root welcome endpoint."""
    response = client.get("/")
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert data["message"] == "Welcome to Acedra Student Management System"
    assert "X-Process-Time" in response.headers


def test_health_check_healthy(client):
    """Test the health check endpoint when the database is healthy."""
    response = client.get("/health")
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert data["status"] == "healthy"
    assert data["database"] == "healthy"
    assert data["environment"] == "testing"


def test_health_check_unhealthy(client):
    """Test the health check endpoint returns 503 when the database fails."""
    mock_db = MagicMock()
    mock_db.execute.side_effect = Exception("Database connection failure")

    def _broken_get_db():
        yield mock_db

    app.dependency_overrides[get_db] = _broken_get_db
    try:
        response = client.get("/health")
        assert response.status_code == status.HTTP_503_SERVICE_UNAVAILABLE
        data = response.json()
        assert data["status"] == "degraded"
        assert data["database"] == "unhealthy"
    finally:
        del app.dependency_overrides[get_db]


def test_global_exception_handler(admin_headers):
    """Test that unexpected server exceptions return a 500 JSON response."""
    from unittest.mock import patch
    from fastapi.testclient import TestClient

    with TestClient(app, raise_server_exceptions=False) as custom_client:
        with patch("sqlalchemy.orm.Session.query", side_effect=RuntimeError("Unexpected database crash")):
            response = custom_client.get("/departments/", headers=admin_headers)
            assert response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
            assert response.json() == {"detail": "Internal server error"}

