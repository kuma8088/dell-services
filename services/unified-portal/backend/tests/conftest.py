"""Pytest configuration and fixtures."""

import pytest
from fastapi.testclient import TestClient
from app.main import app


@pytest.fixture
def client():
    """Create FastAPI test client."""
    return TestClient(app)


@pytest.fixture
def mock_docker_containers():
    """Mock Docker container data for testing."""
    return [
        {
            "name": "blog-wordpress",
            "status": "running",
            "id": "abc123",
            "image": "wordpress:6.4-php8.2-apache",
            "created": "2025-11-13T10:00:00Z",
            "ports": ["8080:80"],
        },
        {
            "name": "blog-mariadb",
            "status": "running",
            "id": "def456",
            "image": "mariadb:11.0",
            "created": "2025-11-13T10:00:00Z",
            "ports": ["3306:3306"],
        },
    ]
