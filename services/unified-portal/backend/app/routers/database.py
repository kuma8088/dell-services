"""
Database management API endpoints.
"""

from typing import List
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
import subprocess
import json
import os


router = APIRouter(prefix="/api/v1/database", tags=["Database"])


# Pydantic Models
class DatabaseStatus(BaseModel):
    """Database connection status."""
    connected: bool
    version: str
    uptime: int  # seconds


class DatabaseInfo(BaseModel):
    """Database information."""
    name: str
    size_mb: float


class DatabaseDetail(DatabaseInfo):
    """Detailed database information."""
    tables_count: int
    rows_count: int


class DatabaseStats(BaseModel):
    """Database system statistics."""
    total_databases: int
    total_size_mb: float
    mariadb_version: str


# Helper Functions
def run_mysql_command(query: str) -> str:
    """Execute MySQL query via docker exec.

    Args:
        query: SQL query to execute

    Returns:
        Query result as string
    """
    # Get container name
    blog_dir = "/opt/onprem-infra-system/project-root-infra/services/blog"

    # Load password from .env file
    env_file = os.path.join(blog_dir, ".env")
    mysql_password = "wordpress_root_password"  # default

    if os.path.exists(env_file):
        with open(env_file, 'r') as f:
            for line in f:
                if line.startswith('MYSQL_ROOT_PASSWORD='):
                    mysql_password = line.split('=', 1)[1].strip()
                    break

    # Execute via docker exec with container name
    docker_cmd = [
        "docker", "exec", "-i", "blog-mariadb",
        "mysql", "-u", "root", f"-p{mysql_password}",
        "-e", query
    ]

    try:
        result = subprocess.run(
            docker_cmd,
            capture_output=True,
            text=True,
            timeout=30
        )
        if result.returncode != 0:
            raise RuntimeError(f"MySQL command failed: {result.stderr}")
        return result.stdout.strip()
    except subprocess.TimeoutExpired:
        raise RuntimeError("MySQL command timed out")
    except Exception as e:
        raise RuntimeError(f"MySQL command error: {str(e)}")


# API Endpoints
@router.get("/status", response_model=DatabaseStatus)
async def get_database_status():
    """
    Get MariaDB database connection status.

    Returns:
        Database connection status and version
    """
    try:
        # Check connection and get version
        version_output = run_mysql_command("SELECT VERSION();")
        version = version_output.split('\n')[1] if '\n' in version_output else version_output

        # Get uptime
        uptime_output = run_mysql_command("SHOW GLOBAL STATUS LIKE 'Uptime';")
        uptime = 0
        if '\n' in uptime_output:
            lines = uptime_output.split('\n')
            for line in lines[1:]:
                if 'Uptime' in line:
                    parts = line.split()
                    if len(parts) >= 2:
                        uptime = int(parts[1])
                        break

        return DatabaseStatus(
            connected=True,
            version=version,
            uptime=uptime
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get database status: {str(e)}")


@router.get("/list", response_model=List[DatabaseInfo])
async def list_databases():
    """
    List all databases in MariaDB.

    Returns:
        List of database information with sizes
    """
    try:
        # Get database list with sizes
        query = """
        SELECT
            table_schema AS 'database',
            ROUND(SUM(data_length + index_length) / 1024 / 1024, 2) AS 'size_mb'
        FROM information_schema.tables
        WHERE table_schema NOT IN ('information_schema', 'performance_schema', 'mysql', 'sys')
        GROUP BY table_schema
        ORDER BY table_schema;
        """

        output = run_mysql_command(query)
        databases = []

        if '\n' in output:
            lines = output.split('\n')[1:]  # Skip header
            for line in lines:
                if line.strip():
                    parts = line.split()
                    if len(parts) >= 2:
                        db_name = parts[0]
                        size_mb = float(parts[1]) if parts[1] != 'NULL' else 0.0
                        databases.append(DatabaseInfo(
                            name=db_name,
                            size_mb=size_mb
                        ))

        return databases
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to list databases: {str(e)}")


@router.get("/{db_name}/size", response_model=DatabaseDetail)
async def get_database_size(db_name: str):
    """
    Get detailed size information for a specific database.

    Args:
        db_name: Database name

    Returns:
        Detailed database size information
    """
    try:
        # Check if database exists
        check_query = f"SHOW DATABASES LIKE '{db_name}';"
        check_output = run_mysql_command(check_query)

        if db_name not in check_output:
            raise HTTPException(status_code=404, detail=f"Database not found: {db_name}")

        # Get database size
        size_query = f"""
        SELECT
            ROUND(SUM(data_length + index_length) / 1024 / 1024, 2) AS size_mb
        FROM information_schema.tables
        WHERE table_schema = '{db_name}';
        """
        size_output = run_mysql_command(size_query)
        size_mb = 0.0
        if '\n' in size_output:
            lines = size_output.split('\n')
            if len(lines) > 1 and lines[1].strip() and lines[1].strip() != 'NULL':
                size_mb = float(lines[1].strip())

        # Get tables count
        tables_query = f"""
        SELECT COUNT(*) AS tables_count
        FROM information_schema.tables
        WHERE table_schema = '{db_name}';
        """
        tables_output = run_mysql_command(tables_query)
        tables_count = 0
        if '\n' in tables_output:
            lines = tables_output.split('\n')
            if len(lines) > 1:
                tables_count = int(lines[1].strip())

        # Get total rows count
        rows_query = f"""
        SELECT SUM(table_rows) AS total_rows
        FROM information_schema.tables
        WHERE table_schema = '{db_name}';
        """
        rows_output = run_mysql_command(rows_query)
        rows_count = 0
        if '\n' in rows_output:
            lines = rows_output.split('\n')
            if len(lines) > 1 and lines[1].strip() and lines[1].strip() != 'NULL':
                rows_count = int(float(lines[1].strip()))

        return DatabaseDetail(
            name=db_name,
            size_mb=size_mb,
            tables_count=tables_count,
            rows_count=rows_count
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get database size: {str(e)}")


@router.get("/stats", response_model=DatabaseStats)
async def get_database_stats():
    """
    Get database system statistics.

    Returns:
        Database system statistics
    """
    try:
        # Get MariaDB version
        version_output = run_mysql_command("SELECT VERSION();")
        version = version_output.split('\n')[1] if '\n' in version_output else version_output

        # Get total databases count and size
        query = """
        SELECT
            COUNT(DISTINCT table_schema) AS db_count,
            ROUND(SUM(data_length + index_length) / 1024 / 1024, 2) AS total_size_mb
        FROM information_schema.tables
        WHERE table_schema NOT IN ('information_schema', 'performance_schema', 'mysql', 'sys');
        """

        output = run_mysql_command(query)
        total_databases = 0
        total_size_mb = 0.0

        if '\n' in output:
            lines = output.split('\n')
            if len(lines) > 1:
                parts = lines[1].split()
                if len(parts) >= 2:
                    total_databases = int(parts[0])
                    total_size_mb = float(parts[1]) if parts[1] != 'NULL' else 0.0

        return DatabaseStats(
            total_databases=total_databases,
            total_size_mb=total_size_mb,
            mariadb_version=version
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get database stats: {str(e)}")
