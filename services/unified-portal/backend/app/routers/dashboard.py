"""
Dashboard API endpoints for system statistics and overview.
"""

from typing import List, Dict, Any
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
import subprocess
import json
import os


router = APIRouter(prefix="/api/v1/dashboard", tags=["Dashboard"])


# Pydantic Models
class SystemStats(BaseModel):
    """System resource statistics."""
    cpu_usage: float
    memory_total_gb: float
    memory_used_gb: float
    memory_percent: float
    disk_total_gb: float
    disk_used_gb: float
    disk_percent: float


class ContainerStats(BaseModel):
    """Docker container statistics."""
    name: str
    status: str
    cpu_percent: str
    memory_usage: str
    memory_limit: str
    network_io: str


class WordPressSiteStatus(BaseModel):
    """WordPress site status."""
    site_name: str
    url: str
    status: str
    redis_connected: bool
    cache_hit_rate: float


class RedisStats(BaseModel):
    """Redis cache statistics."""
    memory_used_mb: float
    memory_total_mb: float
    memory_percent: float
    total_keys: int
    commands_processed: int
    cache_hit_rate: float
    connected_clients: int
    uptime_days: int


class DashboardOverview(BaseModel):
    """Complete dashboard overview."""
    system: SystemStats
    containers: List[ContainerStats]
    wordpress_sites: List[WordPressSiteStatus]
    redis: RedisStats


# Helper Functions
def run_command(cmd: List[str], cwd: str = None) -> str:
    """Execute shell command and return output."""
    try:
        result = subprocess.run(
            cmd,
            cwd=cwd,
            capture_output=True,
            text=True,
            timeout=30
        )
        if result.returncode != 0:
            raise RuntimeError(f"Command failed: {result.stderr}")
        return result.stdout.strip()
    except subprocess.TimeoutExpired:
        raise RuntimeError(f"Command timed out: {' '.join(cmd)}")
    except Exception as e:
        raise RuntimeError(f"Command execution error: {str(e)}")


def get_system_stats() -> SystemStats:
    """Get system resource statistics from /proc filesystem."""
    try:
        # Read CPU stats from /proc/stat
        with open('/proc/stat', 'r') as f:
            cpu_line = f.readline()
            cpu_values = [float(x) for x in cpu_line.split()[1:]]
            cpu_total = sum(cpu_values)
            cpu_idle = cpu_values[3]  # idle time
            cpu_usage = 100.0 * (1.0 - cpu_idle / cpu_total) if cpu_total > 0 else 0.0

        # Read memory stats from /proc/meminfo
        meminfo = {}
        with open('/proc/meminfo', 'r') as f:
            for line in f:
                if ':' in line:
                    key, value = line.split(':', 1)
                    meminfo[key.strip()] = int(value.strip().split()[0])

        mem_total_kb = meminfo.get('MemTotal', 0)
        mem_available_kb = meminfo.get('MemAvailable', meminfo.get('MemFree', 0))
        memory_total_gb = mem_total_kb / (1024 * 1024)
        memory_available_gb = mem_available_kb / (1024 * 1024)
        memory_used_gb = memory_total_gb - memory_available_gb
        memory_percent = (memory_used_gb / memory_total_gb) * 100 if memory_total_gb > 0 else 0.0

        # Read disk stats (this still works in container)
        disk_output = run_command(["df", "-BG", "/"])
        disk_lines = disk_output.split('\n')
        disk_data = disk_lines[1].split()
        disk_total_gb = float(disk_data[1].replace('G', ''))
        disk_used_gb = float(disk_data[2].replace('G', ''))
        disk_percent = float(disk_data[4].replace('%', ''))

        return SystemStats(
            cpu_usage=round(cpu_usage, 2),
            memory_total_gb=round(memory_total_gb, 2),
            memory_used_gb=round(memory_used_gb, 2),
            memory_percent=round(memory_percent, 2),
            disk_total_gb=disk_total_gb,
            disk_used_gb=disk_used_gb,
            disk_percent=disk_percent
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get system stats: {str(e)}")


def get_container_stats() -> List[ContainerStats]:
    """Get Docker container statistics from blog service."""
    try:
        # Get blog containers using docker ps
        ps_output = run_command([
            "docker", "ps", "-a",
            "--filter", "name=blog-",
            "--format", "{{.Names}}\t{{.State}}"
        ])

        containers = []
        for line in ps_output.split('\n'):
            if not line.strip():
                continue

            parts = line.split('\t')
            if len(parts) != 2:
                continue

            container_name = parts[0]
            state = parts[1]

            # Get detailed stats for running containers
            if state == 'running':
                try:
                    stats_cmd_output = run_command([
                        "docker", "stats", "--no-stream", "--format",
                        "{{.CPUPerc}}\t{{.MemUsage}}\t{{.NetIO}}", container_name
                    ])

                    if stats_cmd_output:
                        stats_parts = stats_cmd_output.split('\t')
                        cpu_percent = stats_parts[0] if len(stats_parts) > 0 else "0%"
                        mem_usage = stats_parts[1] if len(stats_parts) > 1 else "0B / 0B"
                        network_io = stats_parts[2] if len(stats_parts) > 2 else "0B / 0B"

                        mem_parts = mem_usage.split(' / ')
                        memory_usage = mem_parts[0] if len(mem_parts) > 0 else "0B"
                        memory_limit = mem_parts[1] if len(mem_parts) > 1 else "0B"
                    else:
                        cpu_percent = "0%"
                        memory_usage = "0B"
                        memory_limit = "0B"
                        network_io = "0B / 0B"
                except Exception:
                    cpu_percent = "0%"
                    memory_usage = "0B"
                    memory_limit = "0B"
                    network_io = "0B / 0B"
            else:
                cpu_percent = "0%"
                memory_usage = "0B"
                memory_limit = "0B"
                network_io = "0B / 0B"

            containers.append(ContainerStats(
                name=container_name,
                status=state,
                cpu_percent=cpu_percent,
                memory_usage=memory_usage,
                memory_limit=memory_limit,
                network_io=network_io
            ))

        return containers
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get container stats: {str(e)}")


def get_wordpress_sites_status() -> List[WordPressSiteStatus]:
    """Get status for all 16 WordPress sites."""
    try:
        # WordPress sites list (from wordpress.py)
        sites = [
            ("fx-trader-life", "https://fx-trader-life.com"),
            ("fx-trader-life-4line", "https://4line.fx-trader-life.com"),
            ("fx-trader-life-lp", "https://lp.fx-trader-life.com"),
            ("fx-trader-life-mfkc", "https://mfkc.fx-trader-life.com"),
            ("webmakeprofit", "https://webmakeprofit.org"),
            ("webmakeprofit-coconala", "https://coconala.webmakeprofit.org"),
            ("webmakesprofit", "https://webmakesprofit.com"),
            ("toyota-phv", "https://toyota-phv.jp"),
            ("kuma8088", "https://kuma8088.com"),
            ("kuma8088-cameramanual", "https://camera.kuma8088.com"),
            ("kuma8088-cameramanual-gwpbk492", "https://gwpbk492.kuma8088.com"),
            ("kuma8088-elementordemo1", "https://demo1.kuma8088.com"),
            ("kuma8088-elementordemo02", "https://demo2.kuma8088.com"),
            ("kuma8088-elementor-demo-03", "https://demo3.kuma8088.com"),
            ("kuma8088-elementor-demo-04", "https://demo4.kuma8088.com"),
            ("kuma8088-ec02test", "https://ec-test.kuma8088.com"),
            ("kuma8088-test", "https://test.kuma8088.com"),
        ]

        sites_status = []

        for site_name, url in sites:
            try:
                # Check Redis status for the site using docker exec
                redis_output = run_command([
                    "docker", "exec", "-i", "blog-wordpress",
                    "wp", "redis", "status",
                    f"--path=/var/www/html/{site_name}",
                    "--allow-root",
                    "--skip-themes"
                ])

                redis_connected = "Status: Connected" in redis_output

                # Extract cache hit rate if available
                cache_hit_rate = 0.0
                if "Hit rate:" in redis_output:
                    hit_rate_line = [line for line in redis_output.split('\n') if 'Hit rate:' in line][0]
                    hit_rate_str = hit_rate_line.split('Hit rate:')[1].strip().replace('%', '')
                    cache_hit_rate = float(hit_rate_str)

                status = "running" if redis_connected else "degraded"

            except Exception:
                redis_connected = False
                cache_hit_rate = 0.0
                status = "unknown"

            sites_status.append(WordPressSiteStatus(
                site_name=site_name,
                url=url,
                status=status,
                redis_connected=redis_connected,
                cache_hit_rate=cache_hit_rate
            ))

        return sites_status
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get WordPress sites status: {str(e)}")


def get_redis_stats() -> RedisStats:
    """Get Redis cache statistics."""
    try:
        # Get Redis INFO using docker exec
        info_output = run_command([
            "docker", "exec", "-i", "blog-redis",
            "redis-cli", "INFO"
        ])

        # Parse INFO output
        info_dict = {}
        for line in info_output.split('\n'):
            if ':' in line and not line.startswith('#'):
                key, value = line.split(':', 1)
                info_dict[key.strip()] = value.strip()

        # Extract metrics
        memory_used_mb = float(info_dict.get('used_memory', '0')) / (1024 * 1024)
        memory_total_mb = 512.0  # From docker-compose.yml maxmemory setting
        memory_percent = (memory_used_mb / memory_total_mb) * 100

        # Get total keys across all databases
        total_keys = 0
        for i in range(16):
            db_key = f'db{i}'
            if db_key in info_dict:
                keys_part = info_dict[db_key].split(',')[0]
                keys_count = int(keys_part.split('=')[1])
                total_keys += keys_count

        commands_processed = int(info_dict.get('total_commands_processed', '0'))
        connected_clients = int(info_dict.get('connected_clients', '0'))
        uptime_seconds = int(info_dict.get('uptime_in_seconds', '0'))
        uptime_days = uptime_seconds // 86400

        # Calculate cache hit rate
        keyspace_hits = int(info_dict.get('keyspace_hits', '0'))
        keyspace_misses = int(info_dict.get('keyspace_misses', '0'))
        total_requests = keyspace_hits + keyspace_misses
        cache_hit_rate = (keyspace_hits / total_requests * 100) if total_requests > 0 else 0.0

        return RedisStats(
            memory_used_mb=round(memory_used_mb, 2),
            memory_total_mb=memory_total_mb,
            memory_percent=round(memory_percent, 2),
            total_keys=total_keys,
            commands_processed=commands_processed,
            cache_hit_rate=round(cache_hit_rate, 2),
            connected_clients=connected_clients,
            uptime_days=uptime_days
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get Redis stats: {str(e)}")


# API Endpoints
@router.get("/overview", response_model=DashboardOverview)
async def get_dashboard_overview():
    """
    Get complete dashboard overview with system stats, containers, WordPress sites, and Redis.
    """
    try:
        system = get_system_stats()
        containers = get_container_stats()
        wordpress_sites = get_wordpress_sites_status()
        redis = get_redis_stats()

        return DashboardOverview(
            system=system,
            containers=containers,
            wordpress_sites=wordpress_sites,
            redis=redis
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get dashboard overview: {str(e)}"
        )


@router.get("/system", response_model=SystemStats)
async def get_system():
    """Get system resource statistics."""
    return get_system_stats()


@router.get("/containers", response_model=List[ContainerStats])
async def get_containers():
    """Get Docker container statistics."""
    return get_container_stats()


@router.get("/wordpress", response_model=List[WordPressSiteStatus])
async def get_wordpress():
    """Get WordPress sites status."""
    return get_wordpress_sites_status()


@router.get("/redis", response_model=RedisStats)
async def get_redis():
    """Get Redis cache statistics."""
    return get_redis_stats()
