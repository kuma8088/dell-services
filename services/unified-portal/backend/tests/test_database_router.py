"""Tests for Database management API endpoints."""

import pytest


class TestDatabaseStatus:
    """Tests for GET /api/v1/database/status endpoint."""

    def test_database_status_success(self, client):
        """Test successful database status retrieval."""
        response = client.get("/api/v1/database/status")

        assert response.status_code == 200
        data = response.json()
        assert "connected" in data
        assert "version" in data
        assert "uptime" in data


class TestDatabaseList:
    """Tests for GET /api/v1/database/list endpoint."""

    def test_list_databases_success(self, client):
        """Test successful database listing."""
        response = client.get("/api/v1/database/list")

        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) >= 15  # At least 15 WordPress databases

        # Verify database structure
        if len(data) > 0:
            db = data[0]
            assert "name" in db
            assert "size_mb" in db


class TestDatabaseSize:
    """Tests for GET /api/v1/database/{db_name}/size endpoint."""

    def test_get_database_size_success(self, client):
        """Test successful database size retrieval."""
        # Get first database from list
        list_response = client.get("/api/v1/database/list")
        databases = list_response.json()

        if len(databases) > 0:
            db_name = databases[0]["name"]
            response = client.get(f"/api/v1/database/{db_name}/size")

            assert response.status_code == 200
            data = response.json()
            assert "name" in data
            assert "size_mb" in data
            assert "tables_count" in data

    def test_get_database_size_not_found(self, client):
        """Test database size with invalid name."""
        response = client.get("/api/v1/database/nonexistent_db/size")

        assert response.status_code == 404
        data = response.json()
        assert "detail" in data


class TestDatabaseStats:
    """Tests for Database statistics endpoints."""

    def test_get_database_stats_summary(self, client):
        """Test database system stats summary."""
        response = client.get("/api/v1/database/stats")

        assert response.status_code == 200
        data = response.json()
        assert "total_databases" in data
        assert "total_size_mb" in data
        assert "mariadb_version" in data
