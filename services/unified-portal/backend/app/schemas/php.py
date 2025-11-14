"""PHP Pydantic schemas."""
from __future__ import annotations

from typing import Any, Optional

from pydantic import BaseModel, Field


class PhpVersionBase(BaseModel):
    """Base PHP version schema."""

    version: str = Field(..., pattern=r"^\d+\.\d+$", description="PHP version (e.g., 7.4, 8.0, 8.1, 8.2)")


class PhpVersionAdd(PhpVersionBase):
    """Schema for adding a PHP version."""

    docker_image: Optional[str] = Field(None, description="Custom Docker image (defaults to php:{version}-fpm)")


class PhpVersionResponse(PhpVersionBase):
    """Schema for PHP version response."""

    installed: bool = Field(True, description="Whether version is installed")
    sites_count: int = Field(0, description="Number of sites using this version")
    container_status: str = Field("unknown", description="Docker container status (running, stopped, not_found)")

    class Config:
        """Pydantic config."""

        from_attributes = True


class PhpConfigBase(BaseModel):
    """Base PHP configuration schema."""

    version: str = Field(..., pattern=r"^\d+\.\d+$", description="PHP version")


class PhpConfigResponse(PhpConfigBase):
    """Schema for PHP configuration response."""

    config: dict[str, Any] = Field(default_factory=dict, description="PHP configuration settings")
    ini_file_path: str = Field("", description="Path to php.ini file")


class PhpConfigUpdate(PhpConfigBase):
    """Schema for updating PHP configuration."""

    settings: dict[str, str] = Field(..., description="PHP settings to update (key-value pairs)")


class PhpExtensionBase(BaseModel):
    """Base PHP extension schema."""

    version: str = Field(..., pattern=r"^\d+\.\d+$", description="PHP version")
    extension_name: str = Field(..., min_length=1, description="Extension name (e.g., gd, mysqli, opcache)")


class PhpExtensionInstall(PhpExtensionBase):
    """Schema for installing a PHP extension."""

    pass


class PhpExtensionResponse(BaseModel):
    """Schema for PHP extension response."""

    name: str = Field(..., description="Extension name")
    version: Optional[str] = Field(None, description="Extension version")
    enabled: bool = Field(False, description="Whether extension is enabled")

    class Config:
        """Pydantic config."""

        from_attributes = True


class PhpModuleResponse(BaseModel):
    """Schema for PHP module response."""

    name: str = Field(..., description="Module name")
    description: Optional[str] = Field(None, description="Module description")

    class Config:
        """Pydantic config."""

        from_attributes = True
