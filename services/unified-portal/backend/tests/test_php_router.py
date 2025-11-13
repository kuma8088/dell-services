"""Tests for PHP management API endpoints."""

import pytest


class TestPHPVersion:
    """Tests for GET /api/v1/php/version endpoint."""

    def test_php_version_success(self, client):
        """Test successful PHP version retrieval."""
        response = client.get("/api/v1/php/version")

        assert response.status_code == 200
        data = response.json()
        assert "version" in data
        assert "major" in data
        assert "minor" in data
        assert "patch" in data


class TestPHPModules:
    """Tests for GET /api/v1/php/modules endpoint."""

    def test_list_php_modules_success(self, client):
        """Test successful PHP modules listing."""
        response = client.get("/api/v1/php/modules")

        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) > 0  # Should have some modules

        # Verify module structure
        module = data[0]
        assert "name" in module
        assert "version" in module


class TestPHPConfig:
    """Tests for GET /api/v1/php/config endpoint."""

    def test_get_php_config_success(self, client):
        """Test successful PHP configuration retrieval."""
        response = client.get("/api/v1/php/config")

        assert response.status_code == 200
        data = response.json()
        assert "memory_limit" in data
        assert "max_execution_time" in data
        assert "upload_max_filesize" in data
        assert "post_max_size" in data


class TestPHPStats:
    """Tests for PHP statistics endpoints."""

    def test_get_php_stats_summary(self, client):
        """Test PHP system stats summary."""
        response = client.get("/api/v1/php/stats")

        assert response.status_code == 200
        data = response.json()
        assert "version" in data
        assert "modules_count" in data
        assert "memory_limit" in data
