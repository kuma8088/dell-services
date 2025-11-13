"""
PHP management API endpoints.
"""

from typing import List
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
import subprocess
import re


router = APIRouter(prefix="/api/v1/php", tags=["PHP"])


# Pydantic Models
class PHPVersion(BaseModel):
    """PHP version information."""
    version: str
    major: int
    minor: int
    patch: int


class PHPModule(BaseModel):
    """PHP module information."""
    name: str
    version: str


class PHPConfig(BaseModel):
    """PHP configuration information."""
    memory_limit: str
    max_execution_time: str
    upload_max_filesize: str
    post_max_size: str
    display_errors: str
    error_reporting: str


class PHPStats(BaseModel):
    """PHP system statistics."""
    version: str
    modules_count: int
    memory_limit: str


# Helper Functions
def run_php_command(command: List[str]) -> str:
    """Execute PHP command via docker exec.

    Args:
        command: Command to execute in WordPress container

    Returns:
        Command output as string
    """
    blog_dir = "/opt/onprem-infra-system/project-root-infra/services/blog"

    full_command = [
        "docker", "compose", "-f", f"{blog_dir}/docker-compose.yml",
        "exec", "-T", "wordpress"
    ] + command

    try:
        result = subprocess.run(
            full_command,
            capture_output=True,
            text=True,
            timeout=30
        )
        if result.returncode != 0:
            raise RuntimeError(f"PHP command failed: {result.stderr}")
        return result.stdout.strip()
    except subprocess.TimeoutExpired:
        raise RuntimeError("PHP command timed out")
    except Exception as e:
        raise RuntimeError(f"PHP command error: {str(e)}")


# API Endpoints
@router.get("/version", response_model=PHPVersion)
async def get_php_version():
    """
    Get PHP version information.

    Returns:
        PHP version details
    """
    try:
        # Get PHP version
        version_output = run_php_command(["php", "-v"])

        # Parse version from output (e.g., "PHP 8.3.27 (cli)...")
        version_match = re.search(r'PHP (\d+)\.(\d+)\.(\d+)', version_output)

        if not version_match:
            raise RuntimeError("Failed to parse PHP version")

        major = int(version_match.group(1))
        minor = int(version_match.group(2))
        patch = int(version_match.group(3))
        version = f"{major}.{minor}.{patch}"

        return PHPVersion(
            version=version,
            major=major,
            minor=minor,
            patch=patch
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get PHP version: {str(e)}")


@router.get("/modules", response_model=List[PHPModule])
async def list_php_modules():
    """
    List all loaded PHP modules.

    Returns:
        List of PHP modules with versions
    """
    try:
        # Get list of loaded PHP modules
        modules_output = run_php_command(["php", "-m"])

        modules = []
        lines = modules_output.split('\n')

        # Skip header lines and get modules
        in_modules_section = False
        for line in lines:
            line = line.strip()
            if line == '[PHP Modules]':
                in_modules_section = True
                continue
            if line == '[Zend Modules]':
                in_modules_section = False
                continue

            if in_modules_section and line and not line.startswith('['):
                # Get module version if available
                try:
                    version_cmd = f"php -r \"echo phpversion('{line}');\""
                    version = run_php_command(["sh", "-c", version_cmd])
                    if not version or version == "0":
                        version = "n/a"
                except:
                    version = "n/a"

                modules.append(PHPModule(
                    name=line,
                    version=version
                ))

        return modules
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to list PHP modules: {str(e)}")


@router.get("/config", response_model=PHPConfig)
async def get_php_config():
    """
    Get PHP configuration settings.

    Returns:
        PHP configuration information
    """
    try:
        # Get PHP configuration values
        config_cmd = """php -r "
        echo 'memory_limit=' . ini_get('memory_limit') . PHP_EOL;
        echo 'max_execution_time=' . ini_get('max_execution_time') . PHP_EOL;
        echo 'upload_max_filesize=' . ini_get('upload_max_filesize') . PHP_EOL;
        echo 'post_max_size=' . ini_get('post_max_size') . PHP_EOL;
        echo 'display_errors=' . ini_get('display_errors') . PHP_EOL;
        echo 'error_reporting=' . ini_get('error_reporting') . PHP_EOL;
        " """

        config_output = run_php_command(["sh", "-c", config_cmd])

        # Parse configuration
        config = {}
        for line in config_output.split('\n'):
            if '=' in line:
                key, value = line.split('=', 1)
                config[key.strip()] = value.strip()

        return PHPConfig(
            memory_limit=config.get('memory_limit', 'unknown'),
            max_execution_time=config.get('max_execution_time', 'unknown'),
            upload_max_filesize=config.get('upload_max_filesize', 'unknown'),
            post_max_size=config.get('post_max_size', 'unknown'),
            display_errors=config.get('display_errors', 'unknown'),
            error_reporting=config.get('error_reporting', 'unknown')
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get PHP config: {str(e)}")


@router.get("/stats", response_model=PHPStats)
async def get_php_stats():
    """
    Get PHP system statistics.

    Returns:
        PHP system statistics
    """
    try:
        # Get PHP version
        version_output = run_php_command(["php", "-v"])
        version_match = re.search(r'PHP (\d+\.\d+\.\d+)', version_output)
        version = version_match.group(1) if version_match else "unknown"

        # Get modules count
        modules_output = run_php_command(["php", "-m"])
        modules_count = 0
        in_modules_section = False
        for line in modules_output.split('\n'):
            line = line.strip()
            if line == '[PHP Modules]':
                in_modules_section = True
                continue
            if line == '[Zend Modules]':
                break
            if in_modules_section and line and not line.startswith('['):
                modules_count += 1

        # Get memory limit
        memory_cmd = "php -r \"echo ini_get('memory_limit');\""
        memory_limit = run_php_command(["sh", "-c", memory_cmd])

        return PHPStats(
            version=version,
            modules_count=modules_count,
            memory_limit=memory_limit
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get PHP stats: {str(e)}")
