"""
Test configuration and fixtures.
"""
import pytest
from fastapi.testclient import TestClient
from app.main import app


@pytest.fixture
def client():
    """
    Create a test client for the FastAPI app.
    
    Returns:
        TestClient instance
    """
    return TestClient(app)


@pytest.fixture
def sample_unit_id():
    """Sample unit ID for testing."""
    return "4"
