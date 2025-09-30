import pytest
from fastapi.testclient import TestClient
from app import app

client = TestClient(app)

def test_healthcheck():
    """Test the healthcheck endpoint."""
    response = client.get("/api/v1/healthcheck")
    assert response.status_code == 200
    data = response.json()
    assert "status" in data
    assert data["status"] == "OK"
    assert "timestamp" in data

def test_get_reviews():
    """Test getting reviews."""
    response = client.get("/api/v1/reviews")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    
def test_get_metrics():
    """Test getting metrics."""
    response = client.get("/api/v1/metrics/overview")
    assert response.status_code == 200
    data = response.json()
    assert "total_pending" in data
    assert "validated_today" in data
    assert "accuracy_vs_machine" in data
    assert "total_reviews" in data

def test_get_review_detail():
    """Test getting a specific review."""
    response = client.get("/api/v1/reviews/R001")
    assert response.status_code == 200
    data = response.json()
    assert data["response_id"] == "R001"
    
def test_validate_review():
    """Test validating a review."""
    response = client.post("/api/v1/reviews/R001/validate", json={
        "decision": "accept"
    })
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert data["review_id"] == "R001"

def test_debug_frontend():
    """Test the debug frontend endpoint."""
    response = client.get("/api/debug/frontend")
    assert response.status_code == 200
    data = response.json()
    assert "build_dir" in data
    assert "build_dir_exists" in data
    assert "assets" in data
