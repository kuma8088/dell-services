"""
Backup management API endpoints.
"""

from typing import List, Dict, Any
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from datetime import datetime
import os
import glob


router = APIRouter(prefix="/api/v1/backup", tags=["Backup"])


# Pydantic Models
class BackupInfo(BaseModel):
    """Backup information."""
    date: str
    size_mb: float
    path: str
    type: str  # daily, weekly


class MailserverBackups(BaseModel):
    """Mailserver backup list."""
    daily: List[BackupInfo]
    weekly: List[BackupInfo]


class BlogBackups(BaseModel):
    """Blog backup list."""
    backups: List[BackupInfo]


class BackupStats(BaseModel):
    """Backup system statistics."""
    total_backups: int
    total_size_gb: float
    last_backup_time: str
    mailserver_backups: int
    blog_backups: int


class BackupSchedule(BaseModel):
    """Backup schedule information."""
    mailserver_daily: str
    mailserver_weekly: str
    s3_replication: str
    malware_scan: str


# Helper Functions
def get_directory_size(path: str) -> float:
    """Get directory size in MB."""
    total_size = 0
    try:
        for dirpath, dirnames, filenames in os.walk(path):
            for filename in filenames:
                filepath = os.path.join(dirpath, filename)
                if os.path.exists(filepath):
                    total_size += os.path.getsize(filepath)
    except Exception:
        pass
    return round(total_size / (1024 * 1024), 2)


def parse_backup_date(backup_path: str) -> str:
    """Extract date from backup path."""
    # Extract date from path like /mnt/backup-hdd/mailserver/daily/YYYY-MM-DD
    # or weekly format like /mnt/backup-hdd/mailserver/weekly/YYYY-week-WW
    parts = backup_path.split("/")
    for part in reversed(parts):
        # Check for YYYY-MM-DD format
        if len(part) == 10 and part.count("-") == 2:
            try:
                datetime.strptime(part, "%Y-%m-%d")
                return part
            except ValueError:
                pass
        # Check for YYYY-week-WW format
        if "week" in part.lower() and part.count("-") == 2:
            return part
    return "unknown"


# API Endpoints
@router.get("/mailserver/list", response_model=MailserverBackups)
async def list_mailserver_backups():
    """
    List all mailserver backups (daily and weekly).

    Returns:
        Mailserver backup list
    """
    try:
        backup_base = "/mnt/backup-hdd/mailserver"
        daily_backups = []
        weekly_backups = []

        # List daily backups
        daily_path = os.path.join(backup_base, "daily")
        if os.path.exists(daily_path):
            for backup_dir in sorted(glob.glob(f"{daily_path}/*"), reverse=True):
                if os.path.isdir(backup_dir):
                    date = parse_backup_date(backup_dir)
                    size = get_directory_size(backup_dir)
                    daily_backups.append(BackupInfo(
                        date=date,
                        size_mb=size,
                        path=backup_dir,
                        type="daily"
                    ))

        # List weekly backups
        weekly_path = os.path.join(backup_base, "weekly")
        if os.path.exists(weekly_path):
            for backup_dir in sorted(glob.glob(f"{weekly_path}/*"), reverse=True):
                if os.path.isdir(backup_dir):
                    date = parse_backup_date(backup_dir)
                    size = get_directory_size(backup_dir)
                    weekly_backups.append(BackupInfo(
                        date=date,
                        size_mb=size,
                        path=backup_dir,
                        type="weekly"
                    ))

        return MailserverBackups(
            daily=daily_backups,
            weekly=weekly_backups
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to list mailserver backups: {str(e)}")


@router.get("/blog/list", response_model=BlogBackups)
async def list_blog_backups():
    """
    List all blog backups.

    Returns:
        Blog backup list
    """
    try:
        backup_base = "/mnt/backup-hdd/rental/blog"
        backups = []

        # Check daily and weekly backups
        for backup_type in ["daily", "weekly"]:
            backup_path = os.path.join(backup_base, backup_type)
            if os.path.exists(backup_path):
                for backup_dir in sorted(glob.glob(f"{backup_path}/*"), reverse=True):
                    if os.path.isdir(backup_dir):
                        date = parse_backup_date(backup_dir)
                        size = get_directory_size(backup_dir)
                        backups.append(BackupInfo(
                            date=date,
                            size_mb=size,
                            path=backup_dir,
                            type=f"blog-{backup_type}"
                        ))

        return BlogBackups(backups=backups)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to list blog backups: {str(e)}")


@router.get("/stats", response_model=BackupStats)
async def get_backup_stats():
    """
    Get backup system statistics.

    Returns:
        Backup system statistics
    """
    try:
        # Get mailserver backups
        mailserver_backups = await list_mailserver_backups()
        mailserver_count = len(mailserver_backups.daily) + len(mailserver_backups.weekly)

        # Get blog backups
        blog_backups = await list_blog_backups()
        blog_count = len(blog_backups.backups)

        # Calculate total size
        total_size_mb = 0.0
        for backup in mailserver_backups.daily + mailserver_backups.weekly:
            total_size_mb += backup.size_mb
        for backup in blog_backups.backups:
            total_size_mb += backup.size_mb

        total_size_gb = round(total_size_mb / 1024, 2)

        # Get last backup time
        last_backup_time = "不明"
        all_backups = mailserver_backups.daily + mailserver_backups.weekly + blog_backups.backups
        if all_backups:
            # Filter out unknown dates and prefer YYYY-MM-DD format
            date_backups = [b for b in all_backups if b.date != "unknown" and not "week" in b.date.lower()]
            if date_backups:
                sorted_backups = sorted(date_backups, key=lambda x: x.date, reverse=True)
                last_backup_time = sorted_backups[0].date
            else:
                # Fallback to week format if no date format available
                valid_backups = [b for b in all_backups if b.date != "unknown"]
                if valid_backups:
                    sorted_backups = sorted(valid_backups, key=lambda x: x.date, reverse=True)
                    last_backup_time = sorted_backups[0].date

        return BackupStats(
            total_backups=mailserver_count + blog_count,
            total_size_gb=total_size_gb,
            last_backup_time=last_backup_time,
            mailserver_backups=mailserver_count,
            blog_backups=blog_count
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get backup stats: {str(e)}")


@router.get("/schedule", response_model=BackupSchedule)
async def get_backup_schedule():
    """
    Get backup schedule information from cron.

    Returns:
        Backup schedule information
    """
    try:
        # Backup schedules (from CLAUDE.md documentation)
        schedule = BackupSchedule(
            mailserver_daily="Daily at 03:00 AM",
            mailserver_weekly="Sunday at 02:00 AM",
            s3_replication="Daily at 04:00 AM",
            malware_scan="Daily at 05:00 AM"
        )

        return schedule
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get backup schedule: {str(e)}")
