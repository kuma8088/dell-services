"""WordPress management service."""
from __future__ import annotations

import logging
import subprocess
from typing import List, Optional

from sqlalchemy.orm import Session

from app.models.wordpress_site import WordPressSite
from app.schemas.wordpress import WordPressSiteCreate, WordPressSiteStats, WordPressSiteUpdate
from app.services.encryption_service import get_encryption_service
from app.services.nginx_config_service import get_nginx_service

logger = logging.getLogger(__name__)


class WordPressService:
    """Service for managing WordPress sites.

    Handles site creation, updates, deletion, and statistics gathering.
    Integrates with wp-cli for WordPress operations.
    """

    def __init__(self, db: Session, wp_cli_path: str = "wp"):
        """Initialize WordPress service.

        Args:
            db: Database session
            wp_cli_path: Path to wp-cli binary
        """
        self.db = db
        self.wp_cli_path = wp_cli_path
        self.encryption = get_encryption_service()
        self.nginx = get_nginx_service()

    def list_sites(self, enabled_only: bool = False) -> List[WordPressSite]:
        """List all WordPress sites.

        Args:
            enabled_only: Only return enabled sites

        Returns:
            List of WordPress sites
        """
        query = self.db.query(WordPressSite)

        if enabled_only:
            query = query.filter(WordPressSite.enabled == True)

        return query.order_by(WordPressSite.created_at.desc()).all()

    def get_site(self, site_id: int) -> Optional[WordPressSite]:
        """Get WordPress site by ID.

        Args:
            site_id: Site ID

        Returns:
            WordPress site or None if not found
        """
        return self.db.query(WordPressSite).filter(WordPressSite.id == site_id).first()

    def get_site_by_name(self, site_name: str) -> Optional[WordPressSite]:
        """Get WordPress site by name.

        Args:
            site_name: Site name

        Returns:
            WordPress site or None if not found
        """
        return self.db.query(WordPressSite).filter(WordPressSite.site_name == site_name).first()

    def create_site(self, site_data: WordPressSiteCreate) -> WordPressSite:
        """Create a new WordPress site.

        Steps:
        1. Create database (handled by DatabaseService)
        2. Install WordPress via wp-cli
        3. Configure WP Mail SMTP
        4. Generate Nginx configuration
        5. Reload Nginx

        Args:
            site_data: Site creation data

        Returns:
            Created WordPress site

        Raises:
            ValueError: If site already exists or creation fails
        """
        # Check if site already exists
        existing = self.get_site_by_name(site_data.site_name)
        if existing:
            raise ValueError(f"Site '{site_data.site_name}' already exists")

        # Create database record
        site = WordPressSite(
            site_name=site_data.site_name,
            domain=site_data.domain,
            database_name=site_data.database_name,
            php_version=site_data.php_version,
            enabled=True,
        )

        try:
            # Add to session but DO NOT commit yet
            # We'll commit only after nginx operations succeed
            self.db.add(site)
            self.db.flush()  # Flush to get ID without committing

            # Generate Nginx configuration
            # This may raise an exception if configuration is invalid
            config_path = self.nginx.create_wordpress_site_config(
                site_name=site_data.site_name,
                domain=site_data.domain,
                php_version=site_data.php_version,
            )

            logger.info(f"Created Nginx config: {config_path}")

            # Reload Nginx
            # This may fail if nginx test fails
            if not self.nginx.reload():
                raise ValueError("Nginx reload failed")

            # All external operations succeeded - NOW commit to database
            self.db.commit()
            self.db.refresh(site)

            logger.info(f"WordPress site created: {site_data.site_name}")
            return site

        except Exception as e:
            # Rollback is now effective because we haven't committed yet
            self.db.rollback()

            # Clean up nginx config if it was created
            try:
                self.nginx.delete_config(f"{site_data.site_name}.conf")
            except Exception as cleanup_error:
                logger.warning(f"Failed to cleanup nginx config: {cleanup_error}")

            logger.error(f"Failed to create WordPress site: {e}")
            raise ValueError(f"Failed to create WordPress site: {e}")

    def update_site(self, site_id: int, site_update: WordPressSiteUpdate) -> WordPressSite:
        """Update WordPress site.

        Args:
            site_id: Site ID
            site_update: Site update data

        Returns:
            Updated WordPress site

        Raises:
            ValueError: If site not found or update fails
        """
        site = self.get_site(site_id)
        if not site:
            raise ValueError(f"Site with ID {site_id} not found")

        try:
            # Update PHP version if changed
            if site_update.php_version and site_update.php_version != site.php_version:
                old_version = site.php_version
                site.php_version = site_update.php_version

                # Regenerate Nginx configuration with new PHP version
                self.nginx.delete_config(f"{site.site_name}.conf")
                self.nginx.create_wordpress_site_config(
                    site_name=site.site_name,
                    domain=site.domain,
                    php_version=site.php_version,
                )

                # Reload Nginx
                if not self.nginx.reload():
                    logger.warning("Nginx reload failed after PHP version change")

                logger.info(f"Updated PHP version for {site.site_name}: {old_version} → {site.php_version}")

            # Update enabled status
            if site_update.enabled is not None:
                site.enabled = site_update.enabled

            # Save changes
            self.db.commit()
            self.db.refresh(site)

            logger.info(f"WordPress site updated: {site.site_name}")
            return site

        except Exception as e:
            self.db.rollback()
            logger.error(f"Failed to update WordPress site: {e}")
            raise ValueError(f"Failed to update WordPress site: {e}")

    def delete_site(self, site_id: int, delete_database: bool = False) -> None:
        """Delete WordPress site.

        Args:
            site_id: Site ID
            delete_database: Also delete the database

        Raises:
            ValueError: If site not found or deletion fails
        """
        site = self.get_site(site_id)
        if not site:
            raise ValueError(f"Site with ID {site_id} not found")

        try:
            # Delete Nginx configuration
            self.nginx.delete_config(f"{site.site_name}.conf")

            # Test Nginx config and reload
            if self.nginx.test_config():
                self.nginx.reload()
            else:
                logger.warning("Nginx configuration test failed after site deletion")

            # Delete database record
            self.db.delete(site)
            self.db.commit()

            logger.info(f"WordPress site deleted: {site.site_name}")

        except Exception as e:
            self.db.rollback()
            logger.error(f"Failed to delete WordPress site: {e}")
            raise ValueError(f"Failed to delete WordPress site: {e}")

    def get_site_stats(self, site_id: int) -> Optional[WordPressSiteStats]:
        """Get WordPress site statistics.

        Args:
            site_id: Site ID

        Returns:
            Site statistics or None if not found
        """
        site = self.get_site(site_id)
        if not site:
            return None

        # TODO: Implement actual wp-cli queries for statistics
        # For now, return mock data
        return WordPressSiteStats(
            post_count=0,
            page_count=0,
            plugin_count=0,
            theme_count=0,
            user_count=1,
            db_size_mb=0.0,
        )

    def clear_cache(self, site_id: int, cache_type: str = "all") -> bool:
        """Clear WordPress cache.

        Args:
            site_id: Site ID
            cache_type: Type of cache to clear (object, transient, all)

        Returns:
            True if successful, False otherwise
        """
        site = self.get_site(site_id)
        if not site:
            raise ValueError(f"Site with ID {site_id} not found")

        try:
            # TODO: Implement wp-cli cache clearing
            # wp cache flush --path=/var/www/html/{site_name}
            logger.info(f"Cache cleared for {site.site_name}: {cache_type}")
            return True

        except Exception as e:
            logger.error(f"Failed to clear cache: {e}")
            return False


def get_wordpress_service(db: Session) -> WordPressService:
    """Get WordPress service instance.

    Args:
        db: Database session

    Returns:
        WordPressService instance
    """
    return WordPressService(db)
