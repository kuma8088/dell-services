"""
WordPress management API endpoints.
"""

from typing import List, Optional
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
import subprocess
import json


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
    List all WordPress sites (16 sites).

    Returns:
        List of WordPress site information
    """
    sites_list = []

    for site in WORDPRESS_SITES:
        status = check_site_status(site["name"])
        sites_list.append(WordPressSiteBase(
            name=site["name"],
            url=site["url"],
            status=status
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

    Returns:
        WordPress system statistics
    """
    try:
        sites_online = 0
        total_plugins = 0
        redis_enabled_sites = 0

        for site in WORDPRESS_SITES:
            try:
                # Check if site is online
                run_wp_cli(site["name"], ["core", "version"])
                sites_online += 1

                # Count plugins
                plugins_json = run_wp_cli(site["name"], ["plugin", "list", "--format=json"])
                plugins = json.loads(plugins_json)
                total_plugins += len(plugins)

                # Check Redis status
                try:
                    redis_status = run_wp_cli(site["name"], ["redis", "status"])
                    if "Connected" in redis_status or "connected" in redis_status.lower():
                        redis_enabled_sites += 1
                except Exception:
                    pass
            except Exception:
                pass  # Site offline or error

        return WordPressStats(
            total_sites=len(WORDPRESS_SITES),
            sites_online=sites_online,
            total_plugins=total_plugins,
            redis_enabled_sites=redis_enabled_sites
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get WordPress stats: {str(e)}")
