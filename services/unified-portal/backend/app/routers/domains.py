"""Domain management API endpoints with Cloudflare integration."""
from __future__ import annotations

import csv
import io
import socket
from typing import Dict, List, Optional

import httpx
from fastapi import APIRouter, File, HTTPException, Query, UploadFile
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


class DNSRecordImportError(BaseModel):
    """DNS record import error detail."""

    row: int
    record: dict
    error: str


class DNSRecordImportResult(BaseModel):
    """DNS record import result."""

    success_count: int
    error_count: int
    errors: List[DNSRecordImportError]


class DNSVerificationServerResult(BaseModel):
    """DNS verification result from a single server."""

    server: str
    status: str  # "success", "failed", "timeout"
    records: List[str]
    error: Optional[str] = None


class DNSVerificationResult(BaseModel):
    """DNS verification result from multiple servers."""

    record_type: str
    name: str
    servers: List[DNSVerificationServerResult]
    propagated: bool
    expected_content: Optional[str] = None


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


@router.post("/{domain}/dns/import", response_model=DNSRecordImportResult)
async def import_dns_records(domain: str, file: UploadFile = File(...)):
    """Import DNS records from CSV file.

    Args:
        domain: Domain name
        file: CSV file with DNS records (Type, Name, Content, TTL, Proxied, Priority)

    Returns:
        Import result with success/error counts
    """
    zone_id = await get_zone_id(domain)

    # Validate file type
    if not file.filename.endswith(".csv"):
        raise HTTPException(
            status_code=400,
            detail="File must be a CSV file",
        )

    # Read CSV file
    contents = await file.read()
    csv_text = contents.decode("utf-8")
    csv_reader = csv.DictReader(io.StringIO(csv_text))

    # Process records
    success_count = 0
    error_count = 0
    errors: List[DNSRecordImportError] = []

    async with httpx.AsyncClient() as client:
        for row_num, row in enumerate(csv_reader, start=2):  # Start at 2 (header is row 1)
            try:
                # Validate required fields
                if not all(key in row for key in ["Type", "Name", "Content"]):
                    raise ValueError("Missing required fields (Type, Name, Content)")

                # Parse row data
                record_type = row["Type"].strip()
                name = row["Name"].strip()
                content = row["Content"].strip()
                ttl = int(row.get("TTL", "1").strip() or "1")
                proxied_str = row.get("Proxied", "No").strip().lower()
                proxied = proxied_str in ("yes", "true", "1")
                priority = None

                if "Priority" in row and row["Priority"].strip():
                    priority = int(row["Priority"].strip())

                # Prepare payload
                payload = {
                    "type": record_type,
                    "name": name,
                    "content": content,
                    "ttl": ttl,
                    "proxied": proxied,
                }

                if priority is not None:
                    payload["priority"] = priority

                # Create record via Cloudflare API
                response = await client.post(
                    f"https://api.cloudflare.com/client/v4/zones/{zone_id}/dns_records",
                    headers={
                        "Authorization": f"Bearer {settings.cloudflare_api_token}",
                        "Content-Type": "application/json",
                    },
                    json=payload,
                )

                if response.status_code != 200:
                    raise ValueError(f"Cloudflare API error: {response.text}")

                data = response.json()

                if not data.get("success"):
                    raise ValueError(f"Cloudflare API error: {data.get('errors')}")

                success_count += 1

            except Exception as err:
                error_count += 1
                errors.append(
                    DNSRecordImportError(
                        row=row_num,
                        record=dict(row),
                        error=str(err),
                    )
                )

    return DNSRecordImportResult(
        success_count=success_count,
        error_count=error_count,
        errors=errors,
    )


@router.post("/{domain}/dns/verify", response_model=DNSVerificationResult)
async def verify_dns_record(
    domain: str,
    record_type: str = Query(..., description="DNS record type (A, AAAA, MX, TXT, etc.)"),
    record_name: str = Query(..., description="DNS record name"),
    expected_content: Optional[str] = Query(None, description="Expected content (optional)"),
):
    """Verify DNS record propagation across multiple public DNS servers.

    Args:
        domain: Domain name
        record_type: DNS record type (A, AAAA, MX, TXT, etc.)
        record_name: DNS record name (FQDN)
        expected_content: Expected content to verify (optional)

    Returns:
        DNS verification result from multiple servers
    """
    # Public DNS servers (DNS-over-HTTPS endpoints)
    dns_servers = {
        "Google": "https://dns.google/resolve",
        "Cloudflare": "https://cloudflare-dns.com/dns-query",
        "Quad9": "https://dns.quad9.net/dns-query",
    }

    servers_results: List[DNSVerificationServerResult] = []
    propagated = True

    async with httpx.AsyncClient(timeout=10.0) as client:
        for server_name, server_url in dns_servers.items():
            try:
                # Query DNS using DNS-over-HTTPS
                params = {
                    "name": record_name,
                    "type": record_type,
                }

                response = await client.get(
                    server_url,
                    params=params,
                    headers={"Accept": "application/dns-json"},
                )

                if response.status_code != 200:
                    servers_results.append(
                        DNSVerificationServerResult(
                            server=server_name,
                            status="failed",
                            records=[],
                            error=f"HTTP {response.status_code}",
                        )
                    )
                    propagated = False
                    continue

                data = response.json()

                # Extract records from response
                records = []
                if "Answer" in data:
                    for answer in data["Answer"]:
                        if answer.get("type") == _get_dns_type_number(record_type):
                            records.append(answer.get("data", ""))

                # Check if records match expected content
                if expected_content:
                    if expected_content not in records:
                        propagated = False

                servers_results.append(
                    DNSVerificationServerResult(
                        server=server_name,
                        status="success" if records else "failed",
                        records=records,
                        error=None if records else "No records found",
                    )
                )

                if not records:
                    propagated = False

            except httpx.TimeoutException:
                servers_results.append(
                    DNSVerificationServerResult(
                        server=server_name,
                        status="timeout",
                        records=[],
                        error="Request timeout",
                    )
                )
                propagated = False
            except Exception as err:
                servers_results.append(
                    DNSVerificationServerResult(
                        server=server_name,
                        status="failed",
                        records=[],
                        error=str(err),
                    )
                )
                propagated = False

    return DNSVerificationResult(
        record_type=record_type,
        name=record_name,
        servers=servers_results,
        propagated=propagated,
        expected_content=expected_content,
    )


def _get_dns_type_number(record_type: str) -> int:
    """Get DNS type number from record type string.

    Args:
        record_type: DNS record type (A, AAAA, MX, etc.)

    Returns:
        DNS type number
    """
    dns_types = {
        "A": 1,
        "AAAA": 28,
        "CNAME": 5,
        "MX": 15,
        "TXT": 16,
        "NS": 2,
        "SOA": 6,
        "PTR": 12,
        "SRV": 33,
    }
    return dns_types.get(record_type.upper(), 1)
