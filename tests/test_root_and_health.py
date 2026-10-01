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
