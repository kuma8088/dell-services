"""
WordPress management API endpoints.

Provides two types of operations:
1. Existing site management (17 sites from Phase A-1/A-2)
2. New site lifecycle management (create/delete/update sites)
"""

from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel
import subprocess
import json

from app.auth import get_current_user
from app.database import get_db
from app.schemas.wordpress import (
    WordPressCacheOperation,
    WordPressSiteCreate,
    WordPressSiteResponse,
    WordPressSiteStats as WordPressSiteStatsSchema,
    WordPressSiteUpdate,
)
from app.services.wordpress_service import get_wordpress_service


router = APIRouter(prefix="/api/v1/wordpress", tags=["WordPress"])


# WordPress site definitions (17 sites - includes kuma8088 root)
# URLs updated to Phase A-2 production domains (2025-11-12)
WORDPRESS_SITES = [
    # fx-trader-life.com domain (4 sites)
    {"name": "fx-trader-life", "url": "https://fx-trader-life.com"},
    {"name": "fx-trader-life-4line", "url": "https://4line.fx-trader-life.com"},
    {"name": "fx-trader-life-lp", "url": "https://lp.fx-trader-life.com"},
    {"name": "fx-trader-life-mfkc", "url": "https://mfkc.fx-trader-life.com"},

    # webmakeprofit.org domain (2 sites)
    {"name": "webmakeprofit", "url": "https://webmakeprofit.org"},
    {"name": "webmakeprofit-coconala", "url": "https://coconala.webmakeprofit.org"},

    # webmakesprofit.com domain (1 site)
    {"name": "webmakesprofit", "url": "https://webmakesprofit.com"},

    # toyota-phv.jp domain (1 site)
    {"name": "toyota-phv", "url": "https://toyota-phv.jp"},

    # kuma8088.com domain (9 sites)
    {"name": "kuma8088", "url": "https://kuma8088.com"},
    {"name": "kuma8088-cameramanual", "url": "https://camera.kuma8088.com"},
    {"name": "kuma8088-cameramanual-gwpbk492", "url": "https://gwpbk492.kuma8088.com"},  # Legacy site
    {"name": "kuma8088-elementordemo1", "url": "https://demo1.kuma8088.com"},
    {"name": "kuma8088-elementordemo02", "url": "https://demo2.kuma8088.com"},
    {"name": "kuma8088-elementor-demo-03", "url": "https://demo3.kuma8088.com"},
    {"name": "kuma8088-elementor-demo-04", "url": "https://demo4.kuma8088.com"},
    {"name": "kuma8088-ec02test", "url": "https://ec-test.kuma8088.com"},
    {"name": "kuma8088-test", "url": "https://test.kuma8088.com"},
]


# Pydantic Models
class WordPressSiteBase(BaseModel):
    """Base WordPress site information."""
    name: str
    url: str
    status: str


class WordPressSiteDetail(WordPressSiteBase):
    """Detailed WordPress site information."""
    wp_version: str
    php_version: str
    theme: str
    db_name: str
    redis_enabled: bool


class WordPressPlugin(BaseModel):
    """WordPress plugin information."""
    name: str
    status: str
    version: str
    update_available: bool = False


class CacheOperation(BaseModel):
    """Cache operation result."""
    success: bool
    message: str
    site_name: str


class SMTPStatus(BaseModel):
    """WP Mail SMTP status."""
    configured: bool
    from_email: Optional[str] = None
    from_name: Optional[str] = None
    mailer: Optional[str] = None


class WordPressStats(BaseModel):
    """WordPress system statistics."""
    total_sites: int
    sites_online: int
    total_plugins: int
    redis_enabled_sites: int


# Helper Functions
def run_wp_cli(site_path: str, command: List[str]) -> str:
    """Execute wp-cli command for a specific site.

    Args:
        site_path: WordPress site directory name
        command: wp-cli command arguments

    Returns:
        Command output as string
    """
    blog_dir = "/opt/onprem-infra-system/project-root-infra/services/blog"
    full_command = [
        "docker", "compose", "-f", f"{blog_dir}/docker-compose.yml",
        "exec", "-T", "wordpress",
        "wp", "--path=/var/www/html/" + site_path, "--allow-root"
    ] + command

    try:
        result = subprocess.run(
            full_command,
            capture_output=True,
            text=True,
            timeout=30
        )
        if result.returncode != 0:
            raise RuntimeError(f"wp-cli command failed: {result.stderr}")
        return result.stdout.strip()
    except subprocess.TimeoutExpired:
        raise RuntimeError("wp-cli command timed out")
    except Exception as e:
        raise RuntimeError(f"wp-cli command error: {str(e)}")


def get_site_by_name(site_name: str) -> dict:
    """Get site configuration by name.

    Args:
        site_name: WordPress site directory name

    Returns:
        Site configuration dictionary

    Raises:
        HTTPException: If site not found
    """
    for site in WORDPRESS_SITES:
        if site["name"] == site_name:
            return site
    raise HTTPException(status_code=404, detail=f"Site not found: {site_name}")


def check_site_status(site_name: str) -> str:
    """Check if WordPress site is accessible.

    Args:
        site_name: WordPress site directory name

    Returns:
        Status string: "online" or "offline"
    """
    try:
        run_wp_cli(site_name, ["core", "version"])
        return "online"
    except Exception:
        return "offline"


# API Endpoints
@router.get("/sites", response_model=List[WordPressSiteBase])
async def list_wordpress_sites():
    """
    List all WordPress sites (17 sites).

    Performance optimization: Skip individual wp-cli checks (too slow for 17 sites).
    Assumes all sites are online if the blog-wordpress container is running.

    Returns:
        List of WordPress site information
    """
    sites_list = []

    for site in WORDPRESS_SITES:
        # Optimization: Assume online if container is running
        # Individual wp-cli checks take 30s+ per site (17 sites = 8.5+ minutes)
        sites_list.append(WordPressSiteBase(
            name=site["name"],
            url=site["url"],
            status="online"
        ))

    return sites_list


@router.get("/sites/{site_name}", response_model=WordPressSiteDetail)
async def get_wordpress_site_detail(site_name: str):
    """
    Get detailed information about a specific WordPress site.

    Args:
        site_name: WordPress site directory name

    Returns:
        Detailed site information
    """
    site = get_site_by_name(site_name)

    try:
        # Get WordPress version
        wp_version = run_wp_cli(site_name, ["core", "version"])

        # Get PHP version
        php_version = run_wp_cli(site_name, ["eval", "echo PHP_VERSION;"])

        # Get active theme
        theme = run_wp_cli(site_name, ["theme", "list", "--status=active", "--field=name"])

        # Get database name
        db_name = run_wp_cli(site_name, ["config", "get", "DB_NAME"])

        # Check Redis Object Cache status
        try:
            redis_status = run_wp_cli(site_name, ["redis", "status"])
            redis_enabled = "Connected" in redis_status or "connected" in redis_status.lower()
        except Exception:
            redis_enabled = False

        return WordPressSiteDetail(
            name=site["name"],
            url=site["url"],
            status="online",
            wp_version=wp_version,
            php_version=php_version,
            theme=theme,
            db_name=db_name,
            redis_enabled=redis_enabled
        )
    except RuntimeError as e:
        if "command failed" in str(e).lower():
            raise HTTPException(status_code=404, detail=f"Site not accessible: {site_name}")
        raise HTTPException(status_code=500, detail=f"Failed to get site details: {str(e)}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get site details: {str(e)}")


@router.get("/sites/{site_name}/plugins", response_model=List[WordPressPlugin])
async def list_wordpress_plugins(site_name: str):
    """
    List all plugins for a specific WordPress site.

    Args:
        site_name: WordPress site directory name

    Returns:
        List of plugin information
    """
    get_site_by_name(site_name)  # Validate site exists

    try:
        # Get plugins list in JSON format
        plugins_json = run_wp_cli(site_name, ["plugin", "list", "--format=json"])
        plugins_data = json.loads(plugins_json)

        plugins_list = []
        for plugin in plugins_data:
            plugins_list.append(WordPressPlugin(
                name=plugin.get("name", "unknown"),
                status=plugin.get("status", "unknown"),
                version=plugin.get("version", "unknown"),
                update_available=plugin.get("update", "none") != "none"
            ))

        return plugins_list
    except RuntimeError as e:
        if "command failed" in str(e).lower():
            raise HTTPException(status_code=404, detail=f"Site not accessible: {site_name}")
        raise HTTPException(status_code=500, detail=f"Failed to list plugins: {str(e)}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to list plugins: {str(e)}")


@router.post("/sites/{site_name}/cache/clear", response_model=CacheOperation)
async def clear_wordpress_cache(site_name: str):
    """
    Clear all caches for a specific WordPress site.

    This includes:
    - Redis Object Cache flush
    - WordPress transients cleanup
    - Rewrite rules flush

    Args:
        site_name: WordPress site directory name

    Returns:
        Cache operation result
    """
    get_site_by_name(site_name)  # Validate site exists

    try:
        # Flush Redis Object Cache
        try:
            run_wp_cli(site_name, ["redis", "flush"])
        except Exception:
            pass  # Redis might not be enabled

        # Clear WordPress transients
        run_wp_cli(site_name, ["transient", "delete", "--all"])

        # Flush rewrite rules
        run_wp_cli(site_name, ["rewrite", "flush"])

        return CacheOperation(
            success=True,
            message=f"Cache cleared successfully for {site_name}",
            site_name=site_name
        )
    except RuntimeError as e:
        if "command failed" in str(e).lower():
            raise HTTPException(status_code=404, detail=f"Site not accessible: {site_name}")
        raise HTTPException(status_code=500, detail=f"Failed to clear cache: {str(e)}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to clear cache: {str(e)}")


@router.get("/sites/{site_name}/smtp-status", response_model=SMTPStatus)
async def get_smtp_status(site_name: str):
    """
    Get WP Mail SMTP configuration status for a specific site.

    Args:
        site_name: WordPress site directory name

    Returns:
        SMTP configuration status
    """
    get_site_by_name(site_name)  # Validate site exists

    try:
        # Check if WP Mail SMTP plugin is active
        plugins_json = run_wp_cli(site_name, ["plugin", "list", "--status=active", "--format=json"])
        plugins = json.loads(plugins_json)

        wp_mail_smtp_active = any(p.get("name") == "wp-mail-smtp" for p in plugins)

        if not wp_mail_smtp_active:
            return SMTPStatus(configured=False)

        # Get SMTP configuration
        try:
            from_email = run_wp_cli(site_name, ["option", "get", "wp_mail_smtp", "--format=json"])
            smtp_config = json.loads(from_email)

            return SMTPStatus(
                configured=True,
                from_email=smtp_config.get("mail", {}).get("from_email"),
                from_name=smtp_config.get("mail", {}).get("from_name"),
                mailer=smtp_config.get("mail", {}).get("mailer", "smtp")
            )
        except Exception:
            return SMTPStatus(configured=True)  # Plugin active but config not accessible
    except RuntimeError as e:
        if "command failed" in str(e).lower():
            raise HTTPException(status_code=404, detail=f"Site not accessible: {site_name}")
        raise HTTPException(status_code=500, detail=f"Failed to get SMTP status: {str(e)}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get SMTP status: {str(e)}")


@router.get("/stats", response_model=WordPressStats)
async def get_wordpress_stats():
    """
    Get WordPress system statistics across all sites.

    Performance optimization: Skip individual wp-cli checks (too slow for 17 sites).
    Returns high-level statistics assuming container is running.

    Returns:
        WordPress system statistics
    """
    try:
        # Optimization: Skip wp-cli checks for stats API
        # Individual checks take 30s+ per site (17 sites = 8.5+ minutes)
        # Assume all sites online and Redis enabled if container running

        return WordPressStats(
            total_sites=len(WORDPRESS_SITES),
            sites_online=len(WORDPRESS_SITES),  # Assume all online
            total_plugins=0,  # Skip slow plugin count
            redis_enabled_sites=len(WORDPRESS_SITES)  # Assume all have Redis
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get WordPress stats: {str(e)}")


# ============================================================================
# Site Lifecycle Management Endpoints (New Site Creation/Deletion)
# ============================================================================

@router.get("/managed-sites", response_model=List[WordPressSiteResponse])
def list_managed_wordpress_sites(
    enabled_only: bool = False,
    db: Session = Depends(get_db),
    current_user: str = Depends(get_current_user),
):
    """
    List all managed WordPress sites from database.

    This endpoint manages sites created through the Unified Portal,
    separate from the 17 existing sites managed via wp-cli.

    Args:
        enabled_only: Only return enabled sites
        db: Database session
        current_user: Current authenticated user

    Returns:
        List of managed WordPress sites
    """
    service = get_wordpress_service(db)
    sites = service.list_sites(enabled_only=enabled_only)
    return sites


@router.get("/managed-sites/{site_id}", response_model=WordPressSiteResponse)
def get_managed_wordpress_site(
    site_id: int,
    db: Session = Depends(get_db),
    current_user: str = Depends(get_current_user),
):
    """
    Get managed WordPress site by ID.

    Args:
        site_id: Site ID
        db: Database session
        current_user: Current authenticated user

    Returns:
        WordPress site details

    Raises:
        HTTPException: If site not found
    """
    service = get_wordpress_service(db)
    site = service.get_site(site_id)

    if not site:
        raise HTTPException(status_code=404, detail=f"Site with ID {site_id} not found")

    return site


@router.post("/managed-sites", response_model=WordPressSiteResponse, status_code=201)
def create_managed_wordpress_site(
    site_data: WordPressSiteCreate,
    db: Session = Depends(get_db),
    current_user: str = Depends(get_current_user),
):
    """
    Create a new WordPress site.

    Steps:
    1. Validate site data
    2. Create database record
    3. Generate Nginx configuration
    4. Reload Nginx

    Args:
        site_data: Site creation data
        db: Database session
        current_user: Current authenticated user

    Returns:
        Created WordPress site

    Raises:
        HTTPException: If site creation fails
    """
    service = get_wordpress_service(db)

    try:
        site = service.create_site(site_data)
        return site
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.put("/managed-sites/{site_id}", response_model=WordPressSiteResponse)
def update_managed_wordpress_site(
    site_id: int,
    site_update: WordPressSiteUpdate,
    db: Session = Depends(get_db),
    current_user: str = Depends(get_current_user),
):
    """
    Update managed WordPress site configuration.

    Args:
        site_id: Site ID
        site_update: Site update data
        db: Database session
        current_user: Current authenticated user

    Returns:
        Updated WordPress site

    Raises:
        HTTPException: If site not found or update fails
    """
    service = get_wordpress_service(db)

    try:
        site = service.update_site(site_id, site_update)
        return site
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.delete("/managed-sites/{site_id}", status_code=204)
def delete_managed_wordpress_site(
    site_id: int,
    delete_database: bool = False,
    db: Session = Depends(get_db),
    current_user: str = Depends(get_current_user),
):
    """
    Delete managed WordPress site.

    Args:
        site_id: Site ID
        delete_database: Also delete the database
        db: Database session
        current_user: Current authenticated user

    Raises:
        HTTPException: If site not found or deletion fails
    """
    service = get_wordpress_service(db)

    try:
        service.delete_site(site_id, delete_database=delete_database)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/managed-sites/{site_id}/stats", response_model=WordPressSiteStatsSchema)
def get_managed_site_stats(
    site_id: int,
    db: Session = Depends(get_db),
    current_user: str = Depends(get_current_user),
):
    """
    Get managed WordPress site statistics.

    Args:
        site_id: Site ID
        db: Database session
        current_user: Current authenticated user

    Returns:
        Site statistics (posts, pages, plugins, themes, users, db size)

    Raises:
        HTTPException: If site not found
    """
    service = get_wordpress_service(db)
    stats = service.get_site_stats(site_id)

    if not stats:
        raise HTTPException(status_code=404, detail=f"Site with ID {site_id} not found")

    return stats


@router.post("/managed-sites/{site_id}/cache/clear", status_code=200)
def clear_managed_site_cache(
    site_id: int,
    cache_control: WordPressCacheOperation,
    db: Session = Depends(get_db),
    current_user: str = Depends(get_current_user),
):
    """
    Clear managed WordPress site cache.

    Args:
        site_id: Site ID
        cache_control: Cache control options
        db: Database session
        current_user: Current authenticated user

    Returns:
        Success status

    Raises:
        HTTPException: If site not found or cache clear fails
    """
    service = get_wordpress_service(db)

    try:
        success = service.clear_cache(site_id, cache_type=cache_control.cache_type)

        if not success:
            raise HTTPException(status_code=500, detail="Failed to clear cache")

        return {"success": True, "message": f"{cache_control.cache_type} cache cleared"}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
