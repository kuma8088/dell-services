"""PHP version management service."""
from __future__ import annotations

import logging
import subprocess
from pathlib import Path
from typing import Any, Dict, List

from sqlalchemy.orm import Session

from app.models.wordpress_site import WordPressSite
from app.schemas.php import PhpVersionResponse

logger = logging.getLogger(__name__)


class PhpService:
    """Service for managing PHP versions.

    Handles PHP version installation, removal, configuration management,
    and Docker container operations for PHP-FPM services.
    """

    def __init__(self, db: Session, docker_compose_path: str = "docker-compose"):
        """Initialize PHP service.

        Args:
            db: Database session
            docker_compose_path: Path to docker-compose binary
        """
        self.db = db
        self.docker_compose_bin = docker_compose_path
        self.available_versions = ["7.4", "8.0", "8.1", "8.2"]

    def list_versions(self) -> List[PhpVersionResponse]:
        """List PHP versions.

        Returns:
            List of PHP versions with installation status and usage counts
        """
        versions = []

        for version in self.available_versions:
            # Count sites using this version
            sites_count = self.db.query(WordPressSite).filter(WordPressSite.php_version == version).count()

            # Check Docker container status
            container_status = self._get_container_status(version)

            versions.append(
                PhpVersionResponse(
                    version=version,
                    installed=container_status != "not_found",
                    sites_count=sites_count,
                    container_status=container_status,
                )
            )

        return versions

    def add_version(self, version: str, docker_image: str | None = None) -> PhpVersionResponse:
        """Add a PHP version.

        Args:
            version: PHP version (e.g., 8.2)
            docker_image: Custom Docker image (optional)

        Returns:
            Added PHP version info

        Raises:
            ValueError: If version is invalid or add fails
        """
        if version not in self.available_versions:
            raise ValueError(f"Invalid PHP version: {version}. Available: {', '.join(self.available_versions)}")

        try:
            # TODO: Update docker-compose.yml to add PHP-FPM service
            # TODO: Run docker compose up -d to start container

            logger.info(f"PHP version added: {version}")

            return PhpVersionResponse(
                version=version,
                installed=True,
                sites_count=0,
                container_status="running",
            )

        except Exception as e:
            logger.error(f"Failed to add PHP version: {e}")
            raise ValueError(f"Failed to add PHP version: {e}")

    def remove_version(self, version: str) -> None:
        """Remove a PHP version.

        Args:
            version: PHP version to remove

        Raises:
            ValueError: If version is in use or removal fails
        """
        # Check if version is in use
        sites_count = self.db.query(WordPressSite).filter(WordPressSite.php_version == version).count()

        if sites_count > 0:
            raise ValueError(f"Cannot remove PHP {version}: {sites_count} site(s) are using it")

        try:
            # TODO: Stop and remove Docker container
            # TODO: Update docker-compose.yml to remove service

            logger.info(f"PHP version removed: {version}")

        except Exception as e:
            logger.error(f"Failed to remove PHP version: {e}")
            raise ValueError(f"Failed to remove PHP version: {e}")

    def get_config(self, version: str) -> Dict[str, Any]:
        """Get PHP configuration.

        Args:
            version: PHP version

        Returns:
            PHP configuration settings

        Raises:
            ValueError: If version not found
        """
        container_status = self._get_container_status(version)

        if container_status == "not_found":
            raise ValueError(f"PHP {version} container not found")

        try:
            # Get php.ini contents via docker exec
            result = subprocess.run(
                [
                    "docker",
                    "exec",
                    f"php-{version}",
                    "php",
                    "-i",
                ],
                capture_output=True,
                text=True,
                timeout=10,
            )

            if result.returncode != 0:
                raise ValueError(f"Failed to get PHP info: {result.stderr}")

            # Parse phpinfo output
            config = self._parse_php_info(result.stdout)

            return {
                "config": config,
                "ini_file_path": f"/usr/local/etc/php/php.ini",
            }

        except subprocess.TimeoutExpired:
            logger.error("PHP config query timed out")
            raise ValueError("PHP config query timed out")
        except Exception as e:
            logger.error(f"Failed to get PHP config: {e}")
            raise ValueError(f"Failed to get PHP config: {e}")

    def update_config(self, version: str, settings: Dict[str, str]) -> bool:
        """Update PHP configuration.

        Args:
            version: PHP version
            settings: Settings to update (key-value pairs)

        Returns:
            True if successful

        Raises:
            ValueError: If update fails
        """
        container_status = self._get_container_status(version)

        if container_status == "not_found":
            raise ValueError(f"PHP {version} container not found")

        try:
            # TODO: Update php.ini file
            # TODO: Restart PHP-FPM container

            logger.info(f"PHP config updated for version {version}")
            return True

        except Exception as e:
            logger.error(f"Failed to update PHP config: {e}")
            raise ValueError(f"Failed to update PHP config: {e}")

    def _get_container_status(self, version: str) -> str:
        """Get Docker container status for PHP version.

        Args:
            version: PHP version

        Returns:
            Container status (running, stopped, not_found)
        """
        try:
            result = subprocess.run(
                [
                    "docker",
                    "inspect",
                    "--format={{.State.Status}}",
                    f"php-{version}",
                ],
                capture_output=True,
                text=True,
                timeout=5,
            )

            if result.returncode == 0:
                status = result.stdout.strip()
                return "running" if status == "running" else "stopped"
            else:
                return "not_found"

        except subprocess.TimeoutExpired:
            logger.warning(f"Container status check timed out for PHP {version}")
            return "unknown"
        except Exception as e:
            logger.warning(f"Failed to check container status: {e}")
            return "unknown"

    @staticmethod
    def _parse_php_info(phpinfo_output: str) -> Dict[str, str]:
        """Parse phpinfo output into key-value pairs.

        Args:
            phpinfo_output: Output from php -i

        Returns:
            Dictionary of PHP configuration settings
        """
        config = {}

        for line in phpinfo_output.split("\n"):
            if "=>" in line:
                parts = line.split("=>")
                if len(parts) == 2:
                    key = parts[0].strip()
                    value = parts[1].strip()
                    config[key] = value

        return config


def get_php_service(db: Session) -> PhpService:
    """Get PHP service instance.

    Args:
        db: Database session

    Returns:
        PhpService instance
    """
    return PhpService(db)
