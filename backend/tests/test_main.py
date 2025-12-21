"""Tests for the main FastAPI application."""

import sys
import os

# Add the parent directory to Python path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest
from fastapi.testclient import TestClient


def test_root_endpoint(test_client: TestClient):
    """Test the root endpoint returns correct information."""
    response = test_client.get("/")
    
    assert response.status_code == 200
    data = response.json()
    
    assert "message" in data
    assert "version" in data
    assert "environment" in data
    assert "status" in data
    assert data["status"] == "healthy"


def test_health_check_endpoint(test_client: TestClient):
    """Test the health check endpoint."""
    response = test_client.get("/health")
    
    assert response.status_code == 200
    data = response.json()
    
    assert data["status"] == "healthy"
    assert "service" in data
    assert "version" in data
    assert "environment" in data


def test_metrics_endpoint(test_client: TestClient):
    """Test that metrics endpoint is accessible."""
    response = test_client.get("/metrics")
    
    # Metrics endpoint should return 200 and prometheus format
    assert response.status_code == 200
    assert "text/plain" in response.headers.get("content-type", "")