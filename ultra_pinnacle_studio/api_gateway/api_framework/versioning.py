"""
API Versioning and Backward Compatibility for Ultra Pinnacle AI Studio

This module provides versioning support for API endpoints, including:
- Versioned routing
- Backward compatibility handling
- Version negotiation
- Deprecation warnings
"""

from typing import Any, Dict, List, Optional, Callable, Union
from fastapi import APIRouter, Request, Response, HTTPException
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
from enum import Enum
import re
import logging
from datetime import datetime, timezone

logger = logging.getLogger("ultra_pinnacle")


class APIVersion(Enum):
    """Supported API versions"""

    V1 = "v1"
    V2 = "v2"  # Future version

    @property
    def version_number(self) -> int:
        """Get version as integer for comparison"""
        return int(self.value[1:])  # Remove 'v' prefix


class VersionCompatibility:
    """Version compatibility matrix"""

    # Define which versions are compatible with each other
    COMPATIBILITY_MATRIX = {
        APIVersion.V1: [APIVersion.V1],
        APIVersion.V2: [APIVersion.V1, APIVersion.V2],  # V2 is backward compatible with V1
    }

    @classmethod
    def is_compatible(cls, requested: APIVersion, supported: APIVersion) -> bool:
        """Check if requested version is compatible with supported version"""
        return requested in cls.COMPATIBILITY_MATRIX.get(supported, [])


class VersionedRouter(APIRouter):
    """Router that supports API versioning"""

    def __init__(
        self,
        version: APIVersion,
        deprecated: bool = False,
        deprecation_date: Optional[datetime] = None,
        sunset_date: Optional[datetime] = None,
        *args,
        **kwargs
    ):
        super().__init__(*args, **kwargs)
        self.version = version
        self.deprecated = deprecated
        self.deprecation_date = deprecation_date
        self.sunset_date = sunset_date

        # Add version prefix to all routes
        if 'prefix' not in kwargs:
            self.prefix = f"/api/{version.value}"

    def add_api_route(
        self,
        path: str,
        endpoint: Callable[..., Any],
        *,
        methods: Optional[List[str]] = None,
        name: Optional[str] = None,
        include_in_schema: bool = True,
        deprecated: Optional[bool] = None,
        **kwargs
    ) -> None:
        """Add a versioned API route"""

        # Add deprecation headers if this version is deprecated
        if self.deprecated or deprecated:
            original_endpoint = endpoint

            async def deprecated_endpoint(*args, **kwargs):
                response = await original_endpoint(*args, **kwargs)
                if isinstance(response, Response):
                    response.headers["X-API-Deprecated"] = "true"
                    if self.deprecation_date:
                        response.headers["X-API-Deprecation-Date"] = self.deprecation_date.isoformat()
                    if self.sunset_date:
                        response.headers["X-API-Sunset-Date"] = self.sunset_date.isoformat()
                return response

            endpoint = deprecated_endpoint

        # Add version info to route tags
        if 'tags' not in kwargs:
            kwargs['tags'] = []
        kwargs['tags'].append(f"version-{self.version.value}")

        super().add_api_route(
            path=path,
            endpoint=endpoint,
            methods=methods,
            name=name,
            include_in_schema=include_in_schema,
            **kwargs
        )


def get_api_version(request: Request) -> APIVersion:
    """Extract API version from request"""
    # Check Accept header for version
    accept_header = request.headers.get("Accept", "")
    version_match = re.search(r'application/vnd\.ultra-pinnacle\.(\w+)\+json', accept_header)
    if version_match:
        version_str = version_match.group(1)
        try:
            return APIVersion(version_str)
        except ValueError:
            pass

    # Check custom header
    version_header = request.headers.get("X-API-Version")
    if version_header:
        try:
            return APIVersion(version_header)
        except ValueError:
            pass

    # Check URL path
    path_parts = request.url.path.strip('/').split('/')
    if len(path_parts) >= 2 and path_parts[0] == 'api':
        version_str = path_parts[1]
        try:
            return APIVersion(version_str)
        except ValueError:
            pass

    # Default to V1
    return APIVersion.V1


def negotiate_version(request: Request, supported_versions: List[APIVersion]) -> APIVersion:
    """Negotiate the best API version based on client request"""
    requested_version = get_api_version(request)

    # Check if requested version is directly supported
    if requested_version in supported_versions:
        return requested_version

    # Check compatibility
    for supported_version in supported_versions:
        if VersionCompatibility.is_compatible(requested_version, supported_version):
            logger.info(f"Using compatible version {supported_version.value} for requested {requested_version.value}")
            return supported_version

    # Fallback to latest supported version
    latest_version = max(supported_versions, key=lambda v: v.version_number)
    logger.warning(f"Requested version {requested_version.value} not supported, falling back to {latest_version.value}")
    return latest_version


class VersionMiddleware(BaseHTTPMiddleware):
    """Middleware for API version handling"""

    def __init__(self, app, supported_versions: List[APIVersion]):
        super().__init__(app)
        self.supported_versions = supported_versions

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        # Skip version negotiation for non-API routes
        if not request.url.path.startswith('/api/'):
            return await call_next(request)

        # Negotiate version
        negotiated_version = negotiate_version(request, self.supported_versions)

        # Add version info to request state
        request.state.api_version = negotiated_version

        # Add version headers to response
        response = await call_next(request)

        if isinstance(response, Response):
            response.headers["X-API-Version"] = negotiated_version.value
            response.headers["X-API-Supported-Versions"] = ",".join(v.value for v in self.supported_versions)

            # Add deprecation warnings
            if negotiated_version == APIVersion.V1:
                response.headers["X-API-Warning"] = "This API version is deprecated. Please migrate to v2."

        return response


def versioned_endpoint(
    version: APIVersion,
    deprecated: bool = False,
    min_version: Optional[APIVersion] = None,
    max_version: Optional[APIVersion] = None
):
    """Decorator for versioned endpoints"""
    def decorator(func: Callable) -> Callable:
        # Store version metadata on the function
        func._api_version = version
        func._deprecated = deprecated
        func._min_version = min_version
        func._max_version = max_version

        return func
    return decorator


def create_versioned_router(
    version: APIVersion,
    deprecated: bool = False,
    deprecation_date: Optional[datetime] = None,
    sunset_date: Optional[datetime] = None
) -> VersionedRouter:
    """Create a versioned router"""
    return VersionedRouter(
        version=version,
        deprecated=deprecated,
        deprecation_date=deprecation_date,
        sunset_date=sunset_date
    )


# Version migration helpers
def migrate_request_data(request_data: Dict[str, Any], from_version: APIVersion, to_version: APIVersion) -> Dict[str, Any]:
    """Migrate request data between versions"""
    # This is a placeholder for version migration logic
    # In practice, you'd implement specific migration rules

    migrations = {
        (APIVersion.V1, APIVersion.V2): lambda data: data,  # No changes needed
        (APIVersion.V2, APIVersion.V1): lambda data: data,  # No changes needed
    }

    migration_func = migrations.get((from_version, to_version))
    if migration_func:
        return migration_func(request_data)

    return request_data


def migrate_response_data(response_data: Dict[str, Any], from_version: APIVersion, to_version: APIVersion) -> Dict[str, Any]:
    """Migrate response data between versions"""
    # This is a placeholder for version migration logic
    # In practice, you'd implement specific migration rules

    migrations = {
        (APIVersion.V1, APIVersion.V2): lambda data: data,  # No changes needed
        (APIVersion.V2, APIVersion.V1): lambda data: data,  # No changes needed
    }

    migration_func = migrations.get((from_version, to_version))
    if migration_func:
        return migration_func(response_data)

    return response_data


# Version compatibility checking
def check_version_compatibility(endpoint_version: APIVersion, request_version: APIVersion) -> bool:
    """Check if endpoint version is compatible with request version"""
    return VersionCompatibility.is_compatible(request_version, endpoint_version)


def get_version_info() -> Dict[str, Any]:
    """Get information about supported API versions"""
    return {
        "current_version": APIVersion.V1.value,
        "supported_versions": [v.value for v in APIVersion],
        "deprecated_versions": [],  # Add deprecated versions here
        "version_matrix": {
            version.value: [compat.value for compat in VersionCompatibility.COMPATIBILITY_MATRIX[version]]
            for version in APIVersion
        }
    }