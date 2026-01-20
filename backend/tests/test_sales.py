"""
Tests for sales endpoints.
"""
import pytest


def test_ytd_sales(client):
    """Test YTD sales endpoint."""
    response = client.get("/v1/ytd-sales")
    assert response.status_code == 200
    data = response.json()
    
    # Check response structure
    assert "current_ytd" in data
    assert "last_ytd" in data
    assert "growth_metrics" in data
    assert "business_unit_name" in data


def test_ytd_sales_with_unit(client, sample_unit_id):
    """Test YTD sales endpoint with unit filter."""
    response = client.get(f"/v1/ytd-sales?unit_id={sample_unit_id}")
    assert response.status_code == 200
    data = response.json()
    assert "current_ytd" in data


def test_mtd_stats(client):
    """Test MTD stats endpoint."""
    response = client.get("/v1/mtd-stats")
    assert response.status_code == 200
    data = response.json()
    
    # Check response structure
    assert "current_month" in data
    assert "previous_month" in data
    assert "growth" in data


def test_mtd_stats_invalid_month(client):
    """Test MTD stats with invalid month."""
    response = client.get("/v1/mtd-stats?month=13")
    assert response.status_code == 400
