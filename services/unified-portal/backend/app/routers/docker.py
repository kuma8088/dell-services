"""
Docker management API endpoints.
"""

from typing import List, Optional
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel
import subprocess
import json


router = APIRouter(prefix="/api/v1/docker", tags=["Docker"])


# Pydantic Models
class ContainerBase(BaseModel):
    """Base container information."""
    id: str
    name: str
    status: str
    image: str


class ContainerDetail(ContainerBase):
    """Detailed container information with stats."""
    created: str
    ports: List[str]
    stats: dict


class ContainerLogs(BaseModel):
    """Container logs response."""
    logs: str
    lines: int


class DockerStats(BaseModel):
    """Docker system statistics."""
    containers_running: int
    containers_stopped: int
    containers_total: int
    images_count: int


class OperationResult(BaseModel):
    """Result of container operation."""
    success: bool
    message: str
    container_id: Optional[str] = None


# Helper Functions
def run_docker_command(cmd: List[str]) -> str:
    """Execute Docker command and return output."""
    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=30
        )
        if result.returncode != 0:
            raise RuntimeError(f"Docker command failed: {result.stderr}")
        return result.stdout.strip()
    except subprocess.TimeoutExpired:
        raise RuntimeError("Docker command timed out")
    except Exception as e:
        raise RuntimeError(f"Docker command error: {str(e)}")


def get_blog_containers(status_filter: Optional[str] = None) -> List[ContainerBase]:
    """Get Blog System containers."""
    try:
        blog_dir = "/opt/onprem-infra-system/project-root-infra/services/blog"

        # Get container list in JSON format
        cmd_output = run_docker_command([
            "docker", "compose", "-f", f"{blog_dir}/docker-compose.yml",
            "ps", "--format", "json"
        ])

        containers = []
        for line in cmd_output.split('\n'):
            if not line.strip():
                continue

            try:
                container_data = json.loads(line)

                # Apply status filter
                state = container_data.get('State', '')
                if status_filter and state != status_filter:
                    continue

                # Get container ID
                container_id = run_docker_command([
                    "docker", "ps", "-a", "--filter",
                    f"name={container_data['Name']}", "--format", "{{.ID}}"
                ])

                containers.append(ContainerBase(
                    id=container_id if container_id else container_data['Name'],
                    name=container_data.get('Name', 'unknown'),
                    status=state,
                    image=container_data.get('Image', 'unknown')
                ))
            except json.JSONDecodeError:
                continue

        return containers
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to list containers: {str(e)}")


# API Endpoints
@router.get("/containers", response_model=List[ContainerBase])
async def list_containers(status: Optional[str] = Query(None, description="Filter by status (running/stopped)")):
    """
    List all Docker containers in Blog System.

    Args:
        status: Optional filter by container status
    """
    return get_blog_containers(status_filter=status)


@router.get("/containers/{container_id}", response_model=ContainerDetail)
async def get_container_detail(container_id: str):
    """
    Get detailed information about a specific container.

    Args:
        container_id: Container ID or name
    """
    try:
        # Get container inspect output
        inspect_output = run_docker_command([
            "docker", "inspect", container_id
        ])

        inspect_data = json.loads(inspect_output)[0]

        # Get container stats
        stats_output = run_docker_command([
            "docker", "stats", "--no-stream", "--format",
            "{{json .}}", container_id
        ])

        stats_data = json.loads(stats_output) if stats_output else {}

        # Extract port mappings
        ports = []
        port_bindings = inspect_data.get('NetworkSettings', {}).get('Ports', {})
        for container_port, host_bindings in port_bindings.items():
            if host_bindings:
                for binding in host_bindings:
                    ports.append(f"{binding['HostPort']}:{container_port}")

        return ContainerDetail(
            id=inspect_data['Id'][:12],
            name=inspect_data['Name'].lstrip('/'),
            status=inspect_data['State']['Status'],
            image=inspect_data['Config']['Image'],
            created=inspect_data['Created'],
            ports=ports,
            stats={
                "cpu_percent": stats_data.get('CPUPerc', '0%'),
                "memory_usage": stats_data.get('MemUsage', '0B / 0B'),
                "network_io": stats_data.get('NetIO', '0B / 0B'),
                "block_io": stats_data.get('BlockIO', '0B / 0B')
            }
        )
    except RuntimeError as e:
        # RuntimeError from run_docker_command indicates container not found
        if "command failed" in str(e).lower():
            raise HTTPException(status_code=404, detail=f"Container not found: {container_id}")
        raise HTTPException(status_code=500, detail=f"Failed to get container details: {str(e)}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get container details: {str(e)}")


@router.post("/containers/{container_id}/start", response_model=OperationResult)
async def start_container(container_id: str):
    """
    Start a stopped container.

    Args:
        container_id: Container ID or name
    """
    try:
        run_docker_command(["docker", "start", container_id])
        return OperationResult(
            success=True,
            message=f"Container {container_id} started successfully",
            container_id=container_id
        )
    except RuntimeError as e:
        if "command failed" in str(e).lower() or "no such container" in str(e).lower():
            raise HTTPException(status_code=404, detail=f"Container not found: {container_id}")
        raise HTTPException(status_code=500, detail=f"Failed to start container: {str(e)}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to start container: {str(e)}")


@router.post("/containers/{container_id}/stop", response_model=OperationResult)
async def stop_container(container_id: str):
    """
    Stop a running container.

    Args:
        container_id: Container ID or name
    """
    try:
        run_docker_command(["docker", "stop", container_id])
        return OperationResult(
            success=True,
            message=f"Container {container_id} stopped successfully",
            container_id=container_id
        )
    except RuntimeError as e:
        if "command failed" in str(e).lower() or "no such container" in str(e).lower():
            raise HTTPException(status_code=404, detail=f"Container not found: {container_id}")
        raise HTTPException(status_code=500, detail=f"Failed to stop container: {str(e)}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to stop container: {str(e)}")


@router.post("/containers/{container_id}/restart", response_model=OperationResult)
async def restart_container(container_id: str):
    """
    Restart a container.

    Args:
        container_id: Container ID or name
    """
    try:
        run_docker_command(["docker", "restart", container_id])
        return OperationResult(
            success=True,
            message=f"Container {container_id} restarted successfully",
            container_id=container_id
        )
    except RuntimeError as e:
        if "command failed" in str(e).lower() or "no such container" in str(e).lower():
            raise HTTPException(status_code=404, detail=f"Container not found: {container_id}")
        raise HTTPException(status_code=500, detail=f"Failed to restart container: {str(e)}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to restart container: {str(e)}")


@router.get("/containers/{container_id}/logs", response_model=ContainerLogs)
async def get_container_logs(
    container_id: str,
    tail: int = Query(100, description="Number of lines to retrieve from the end")
):
    """
    Get container logs.

    Args:
        container_id: Container ID or name
        tail: Number of lines to retrieve (default: 100)
    """
    try:
        logs_output = run_docker_command([
            "docker", "logs", "--tail", str(tail), container_id
        ])

        log_lines = logs_output.split('\n')

        return ContainerLogs(
            logs=logs_output,
            lines=len(log_lines)
        )
    except subprocess.CalledProcessError:
        raise HTTPException(status_code=404, detail=f"Container not found: {container_id}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get container logs: {str(e)}")


@router.get("/stats", response_model=DockerStats)
async def get_docker_stats():
    """
    Get Docker system statistics.
    """
    try:
        # Get all containers
        all_containers_output = run_docker_command([
            "docker", "ps", "-a", "--format", "{{.State}}"
        ])

        all_states = all_containers_output.split('\n')
        containers_running = sum(1 for state in all_states if state == 'running')
        containers_stopped = sum(1 for state in all_states if state in ['exited', 'stopped'])
        containers_total = len([s for s in all_states if s])

        # Get images count
        images_output = run_docker_command([
            "docker", "images", "--format", "{{.ID}}"
        ])
        images_count = len([img for img in images_output.split('\n') if img])

        return DockerStats(
            containers_running=containers_running,
            containers_stopped=containers_stopped,
            containers_total=containers_total,
            images_count=images_count
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get Docker stats: {str(e)}")
