"""Domain management API endpoints with Cloudflare integration."""
from __future__ import annotations

from typing import List, Optional

import httpx
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel

from app.config import get_settings

router = APIRouter(prefix="/api/v1/domains", tags=["Domains"])
settings = get_settings()


# Pydantic models
class DNSRecordCreate(BaseModel):
    """DNS record creation request."""

    type: str  # A, AAAA, CNAME, MX, TXT, etc.
    name: str  # @ for root, or subdomain
    content: str  # IP address, domain, or text value
    ttl: int = 1  # 1 = Auto
    proxied: bool = False  # Cloudflare proxy (orange cloud)
    priority: Optional[int] = None  # For MX records


class DNSRecordUpdate(BaseModel):
    """DNS record update request."""

    content: Optional[str] = None
    ttl: Optional[int] = None
    proxied: Optional[bool] = None
    priority: Optional[int] = None


class DNSRecord(BaseModel):
    """DNS record response."""

    id: str
    type: str
    name: str
    content: str
    ttl: int
    proxied: bool
    priority: Optional[int] = None


class Zone(BaseModel):
    """Cloudflare zone (domain) response."""

    id: str
    name: str
    status: str
    name_servers: List[str]


# Helper functions
async def get_zone_id(domain: str) -> str:
    """Get Cloudflare zone ID from domain name.

    Args:
        domain: Domain name (e.g., kuma8088.com)

    Returns:
        Zone ID

    Raises:
        HTTPException: If zone not found or API error
    """
    if not settings.cloudflare_api_token:
        raise HTTPException(
            status_code=500,
            detail="Cloudflare API token not configured",
        )

    async with httpx.AsyncClient() as client:
        response = await client.get(
            f"https://api.cloudflare.com/client/v4/zones?name={domain}",
            headers={
                "Authorization": f"Bearer {settings.cloudflare_api_token}",
                "Content-Type": "application/json",
            },
        )

        if response.status_code != 200:
            raise HTTPException(
                status_code=response.status_code,
                detail=f"Cloudflare API error: {response.text}",
            )

        data = response.json()

        if not data.get("success"):
            raise HTTPException(
                status_code=400,
                detail=f"Cloudflare API error: {data.get('errors')}",
            )

        result = data.get("result", [])
        if not result:
            raise HTTPException(
                status_code=404,
                detail=f"Zone not found for domain: {domain}",
            )

        return result[0]["id"]


# API endpoints
@router.get("/zones", response_model=List[Zone])
async def list_zones():
    """List all Cloudflare zones (domains).

    Returns:
        List of zones
    """
    if not settings.cloudflare_api_token:
        raise HTTPException(
            status_code=500,
            detail="Cloudflare API token not configured",
        )

    async with httpx.AsyncClient() as client:
        response = await client.get(
            "https://api.cloudflare.com/client/v4/zones",
            headers={
                "Authorization": f"Bearer {settings.cloudflare_api_token}",
                "Content-Type": "application/json",
            },
        )

        if response.status_code != 200:
            raise HTTPException(
                status_code=response.status_code,
                detail=f"Cloudflare API error: {response.text}",
            )

        data = response.json()

        if not data.get("success"):
            raise HTTPException(
                status_code=400,
                detail=f"Cloudflare API error: {data.get('errors')}",
            )

        result = data.get("result", [])
        return [
            Zone(
                id=zone["id"],
                name=zone["name"],
                status=zone["status"],
                name_servers=zone.get("name_servers", []),
            )
            for zone in result
        ]


@router.get("/{domain}/dns", response_model=List[DNSRecord])
async def get_dns_records(
    domain: str,
    record_type: Optional[str] = Query(None, description="Filter by DNS record type"),
):
    """Get DNS records for a domain.

    Args:
        domain: Domain name
        record_type: Optional filter by record type (A, MX, etc.)

    Returns:
        List of DNS records
    """
    zone_id = await get_zone_id(domain)

    params = {}
    if record_type:
        params["type"] = record_type

    async with httpx.AsyncClient() as client:
        response = await client.get(
            f"https://api.cloudflare.com/client/v4/zones/{zone_id}/dns_records",
            headers={
                "Authorization": f"Bearer {settings.cloudflare_api_token}",
                "Content-Type": "application/json",
            },
            params=params,
        )

        if response.status_code != 200:
            raise HTTPException(
                status_code=response.status_code,
                detail=f"Cloudflare API error: {response.text}",
            )

        data = response.json()

        if not data.get("success"):
            raise HTTPException(
                status_code=400,
                detail=f"Cloudflare API error: {data.get('errors')}",
            )

        result = data.get("result", [])
        return [
            DNSRecord(
                id=record["id"],
                type=record["type"],
                name=record["name"],
                content=record["content"],
                ttl=record["ttl"],
                proxied=record.get("proxied", False),
                priority=record.get("priority"),
            )
            for record in result
        ]


@router.post("/{domain}/dns", response_model=DNSRecord)
async def create_dns_record(domain: str, record: DNSRecordCreate):
    """Create a DNS record.

    Args:
        domain: Domain name
        record: DNS record data

    Returns:
        Created DNS record
    """
    zone_id = await get_zone_id(domain)

    payload = {
        "type": record.type,
        "name": record.name,
        "content": record.content,
        "ttl": record.ttl,
        "proxied": record.proxied,
    }

    if record.priority is not None:
        payload["priority"] = record.priority

    async with httpx.AsyncClient() as client:
        response = await client.post(
            f"https://api.cloudflare.com/client/v4/zones/{zone_id}/dns_records",
            headers={
                "Authorization": f"Bearer {settings.cloudflare_api_token}",
                "Content-Type": "application/json",
            },
            json=payload,
        )

        if response.status_code != 200:
            raise HTTPException(
                status_code=response.status_code,
                detail=f"Cloudflare API error: {response.text}",
            )

        data = response.json()

        if not data.get("success"):
            raise HTTPException(
                status_code=400,
                detail=f"Cloudflare API error: {data.get('errors')}",
            )

        result = data["result"]
        return DNSRecord(
            id=result["id"],
            type=result["type"],
            name=result["name"],
            content=result["content"],
            ttl=result["ttl"],
            proxied=result.get("proxied", False),
            priority=result.get("priority"),
        )


@router.put("/{domain}/dns/{record_id}", response_model=DNSRecord)
async def update_dns_record(
    domain: str, record_id: str, record: DNSRecordUpdate
):
    """Update a DNS record.

    Args:
        domain: Domain name
        record_id: DNS record ID
        record: Updated DNS record data

    Returns:
        Updated DNS record
    """
    zone_id = await get_zone_id(domain)

    # Get existing record first
    async with httpx.AsyncClient() as client:
        get_response = await client.get(
            f"https://api.cloudflare.com/client/v4/zones/{zone_id}/dns_records/{record_id}",
            headers={
                "Authorization": f"Bearer {settings.cloudflare_api_token}",
                "Content-Type": "application/json",
            },
        )

        if get_response.status_code != 200:
            raise HTTPException(
                status_code=get_response.status_code,
                detail=f"Cloudflare API error: {get_response.text}",
            )

        existing_data = get_response.json()
        if not existing_data.get("success"):
            raise HTTPException(
                status_code=400,
                detail=f"Cloudflare API error: {existing_data.get('errors')}",
            )

        existing = existing_data["result"]

        # Prepare update payload (merge with existing)
        payload = {
            "type": existing["type"],
            "name": existing["name"],
            "content": record.content or existing["content"],
            "ttl": record.ttl or existing["ttl"],
            "proxied": record.proxied if record.proxied is not None else existing.get("proxied", False),
        }

        if "priority" in existing or record.priority is not None:
            payload["priority"] = record.priority or existing.get("priority")

        # Update record
        put_response = await client.put(
            f"https://api.cloudflare.com/client/v4/zones/{zone_id}/dns_records/{record_id}",
            headers={
                "Authorization": f"Bearer {settings.cloudflare_api_token}",
                "Content-Type": "application/json",
            },
            json=payload,
        )

        if put_response.status_code != 200:
            raise HTTPException(
                status_code=put_response.status_code,
                detail=f"Cloudflare API error: {put_response.text}",
            )

        data = put_response.json()

        if not data.get("success"):
            raise HTTPException(
                status_code=400,
                detail=f"Cloudflare API error: {data.get('errors')}",
            )

        result = data["result"]
        return DNSRecord(
            id=result["id"],
            type=result["type"],
            name=result["name"],
            content=result["content"],
            ttl=result["ttl"],
            proxied=result.get("proxied", False),
            priority=result.get("priority"),
        )


@router.delete("/{domain}/dns/{record_id}")
async def delete_dns_record(domain: str, record_id: str):
    """Delete a DNS record.

    Args:
        domain: Domain name
        record_id: DNS record ID

    Returns:
        Success message
    """
    zone_id = await get_zone_id(domain)

    async with httpx.AsyncClient() as client:
        response = await client.delete(
            f"https://api.cloudflare.com/client/v4/zones/{zone_id}/dns_records/{record_id}",
            headers={
                "Authorization": f"Bearer {settings.cloudflare_api_token}",
                "Content-Type": "application/json",
            },
        )

        if response.status_code != 200:
            raise HTTPException(
                status_code=response.status_code,
                detail=f"Cloudflare API error: {response.text}",
            )

        data = response.json()

        if not data.get("success"):
            raise HTTPException(
                status_code=400,
                detail=f"Cloudflare API error: {data.get('errors')}",
            )

        return {"success": True, "message": "DNS record deleted successfully"}
