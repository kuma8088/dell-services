"""Tests for WordPress management API endpoints."""

import pytest
from unittest.mock import patch, MagicMock


class TestWordPressSitesList:
    """Tests for GET /api/v1/wordpress/sites endpoint."""

    def test_list_sites_success(self, client):
        """Test successful WordPress sites listing."""
        response = client.get("/api/v1/wordpress/sites")

        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) == 16  # 16 WordPress sites

        # Verify response structure
        if len(data) > 0:
            site = data[0]
            assert "name" in site
            assert "url" in site
            assert "status" in site


class TestWordPressSiteDetail:
    """Tests for GET /api/v1/wordpress/sites/{site_name} endpoint."""

    def test_get_site_detail_success(self, client):
        """Test successful site detail retrieval."""
        # Use first site from list
        list_response = client.get("/api/v1/wordpress/sites")
        sites = list_response.json()

        if len(sites) > 0:
            site_name = sites[0]["name"]
            response = client.get(f"/api/v1/wordpress/sites/{site_name}")

            assert response.status_code == 200
            data = response.json()
            assert data["name"] == site_name
            assert "url" in data
            assert "wp_version" in data
            assert "php_version" in data
            assert "theme" in data

    def test_get_site_not_found(self, client):
        """Test site detail with invalid name."""
        response = client.get("/api/v1/wordpress/sites/nonexistent_site")

        assert response.status_code == 404
        data = response.json()
        assert "detail" in data


class TestWordPressPlugins:
    """Tests for WordPress plugins management endpoints."""

    def test_list_plugins_success(self, client):
        """Test successful plugins listing."""
        # Get first site
        list_response = client.get("/api/v1/wordpress/sites")
        sites = list_response.json()

        if len(sites) > 0:
            site_name = sites[0]["name"]
            response = client.get(f"/api/v1/wordpress/sites/{site_name}/plugins")

            assert response.status_code == 200
            data = response.json()
            assert isinstance(data, list)

            # Verify plugin structure
            if len(data) > 0:
                plugin = data[0]
                assert "name" in plugin
                assert "status" in plugin
                assert "version" in plugin

    def test_list_plugins_site_not_found(self, client):
        """Test plugins listing with invalid site."""
        response = client.get("/api/v1/wordpress/sites/nonexistent/plugins")

        assert response.status_code == 404


class TestWordPressCacheManagement:
    """Tests for WordPress cache management endpoints."""

    def test_clear_cache_success(self, client):
        """Test successful cache clear operation."""
        # Get first site
        list_response = client.get("/api/v1/wordpress/sites")
        sites = list_response.json()

        if len(sites) > 0:
            site_name = sites[0]["name"]
            response = client.post(f"/api/v1/wordpress/sites/{site_name}/cache/clear")

            assert response.status_code == 200
            data = response.json()
            assert "success" in data
            assert "message" in data

    def test_clear_cache_site_not_found(self, client):
        """Test cache clear with invalid site."""
        response = client.post("/api/v1/wordpress/sites/nonexistent/cache/clear")

        assert response.status_code == 404


class TestWordPressSMTPStatus:
    """Tests for WP Mail SMTP status endpoints."""

    def test_smtp_status_success(self, client):
        """Test successful SMTP status retrieval."""
        # Get first site
        list_response = client.get("/api/v1/wordpress/sites")
        sites = list_response.json()

        if len(sites) > 0:
            site_name = sites[0]["name"]
            response = client.get(f"/api/v1/wordpress/sites/{site_name}/smtp-status")

            assert response.status_code == 200
            data = response.json()
            assert "configured" in data
            assert "from_email" in data

    def test_smtp_status_site_not_found(self, client):
        """Test SMTP status with invalid site."""
        response = client.get("/api/v1/wordpress/sites/nonexistent/smtp-status")

        assert response.status_code == 404


class TestWordPressStats:
    """Tests for WordPress statistics endpoints."""

    def test_get_wordpress_stats_summary(self, client):
        """Test WordPress system stats summary."""
        response = client.get("/api/v1/wordpress/stats")

        assert response.status_code == 200
        data = response.json()
        assert "total_sites" in data
        assert "sites_online" in data
        assert "total_plugins" in data
        assert "redis_enabled_sites" in data
