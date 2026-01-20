"""
Tests for health and units endpoints.
"""
import pytest


def test_health_check(client):
    """Test health check endpoint."""
    response = client.get("/v1/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_get_units(client):
    """Test get units endpoint."""
    response = client.get("/v1/units")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    
    # Check structure if data exists
    if len(data) > 0:
        assert "unit_id" in data[0]
        assert "business_unit_name" in data[0]
