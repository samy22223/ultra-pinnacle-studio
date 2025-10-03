"""
Standardized API Response Formats for Ultra Pinnacle AI Studio

This module provides consistent response structures across all API endpoints,
including success responses, error responses, and pagination formats.
"""

from typing import Any, Dict, List, Optional, Union
from pydantic import BaseModel, Field
from datetime import datetime, timezone
import uuid


class APIResponse(BaseModel):
    """Standard API response wrapper"""

    success: bool = Field(..., description="Whether the request was successful")
    data: Optional[Any] = Field(None, description="Response data payload")
    message: Optional[str] = Field(None, description="Human-readable message")
    request_id: str = Field(default_factory=lambda: str(uuid.uuid4()), description="Unique request identifier")
    timestamp: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat(),
                          description="Response timestamp in ISO format")
    version: str = Field("v1", description="API version")
    meta: Optional[Dict[str, Any]] = Field(None, description="Additional metadata")


class ErrorDetail(BaseModel):
    """Detailed error information"""

    code: str = Field(..., description="Error code for programmatic handling")
    message: str = Field(..., description="Human-readable error message")
    field: Optional[str] = Field(None, description="Field that caused the error (for validation errors)")
    details: Optional[Dict[str, Any]] = Field(None, description="Additional error details")


class APIErrorResponse(BaseModel):
    """Standard API error response"""

    success: bool = Field(False, description="Always false for error responses")
    error: ErrorDetail = Field(..., description="Error details")
    request_id: str = Field(default_factory=lambda: str(uuid.uuid4()), description="Unique request identifier")
    timestamp: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat(),
                          description="Error timestamp in ISO format")
    version: str = Field("v1", description="API version")
    meta: Optional[Dict[str, Any]] = Field(None, description="Additional metadata")


class PaginationMeta(BaseModel):
    """Pagination metadata"""

    page: int = Field(..., description="Current page number")
    per_page: int = Field(..., description="Items per page")
    total_pages: int = Field(..., description="Total number of pages")
    total_items: int = Field(..., description="Total number of items")
    has_next: bool = Field(..., description="Whether there is a next page")
    has_prev: bool = Field(..., description="Whether there is a previous page")
    next_page: Optional[int] = Field(None, description="Next page number")
    prev_page: Optional[int] = Field(None, description="Previous page number")


class PaginatedResponse(APIResponse):
    """Standard paginated response"""

    data: List[Any] = Field(..., description="List of items")
    pagination: PaginationMeta = Field(..., description="Pagination metadata")


class RateLimitInfo(BaseModel):
    """Rate limiting information"""

    limit: int = Field(..., description="Request limit")
    remaining: int = Field(..., description="Remaining requests")
    reset_time: str = Field(..., description="Time when limit resets (ISO format)")
    retry_after: Optional[int] = Field(None, description="Seconds to wait before retry")


class APIResponseWithRateLimit(APIResponse):
    """Response that includes rate limiting information"""

    rate_limit: RateLimitInfo = Field(..., description="Rate limiting status")


# Error code constants
class ErrorCodes:
    """Standardized error codes"""

    # Authentication errors
    UNAUTHORIZED = "UNAUTHORIZED"
    FORBIDDEN = "FORBIDDEN"
    TOKEN_EXPIRED = "TOKEN_EXPIRED"
    INVALID_TOKEN = "INVALID_TOKEN"

    # Validation errors
    VALIDATION_ERROR = "VALIDATION_ERROR"
    MISSING_REQUIRED_FIELD = "MISSING_REQUIRED_FIELD"
    INVALID_FORMAT = "INVALID_FORMAT"

    # Resource errors
    NOT_FOUND = "NOT_FOUND"
    ALREADY_EXISTS = "ALREADY_EXISTS"
    CONFLICT = "CONFLICT"

    # Rate limiting
    RATE_LIMIT_EXCEEDED = "RATE_LIMIT_EXCEEDED"

    # Server errors
    INTERNAL_ERROR = "INTERNAL_ERROR"
    SERVICE_UNAVAILABLE = "SERVICE_UNAVAILABLE"
    EXTERNAL_SERVICE_ERROR = "EXTERNAL_SERVICE_ERROR"

    # Business logic errors
    INSUFFICIENT_PERMISSIONS = "INSUFFICIENT_PERMISSIONS"
    INVALID_OPERATION = "INVALID_OPERATION"
    QUOTA_EXCEEDED = "QUOTA_EXCEEDED"


def create_success_response(
    data: Any = None,
    message: Optional[str] = None,
    meta: Optional[Dict[str, Any]] = None,
    version: str = "v1"
) -> APIResponse:
    """Create a standardized success response"""
    return APIResponse(
        success=True,
        data=data,
        message=message,
        meta=meta,
        version=version
    )


def create_error_response(
    code: str,
    message: str,
    field: Optional[str] = None,
    details: Optional[Dict[str, Any]] = None,
    meta: Optional[Dict[str, Any]] = None,
    version: str = "v1"
) -> APIErrorResponse:
    """Create a standardized error response"""
    return APIErrorResponse(
        success=False,
        error=ErrorDetail(
            code=code,
            message=message,
            field=field,
            details=details
        ),
        meta=meta,
        version=version
    )


def create_paginated_response(
    items: List[Any],
    page: int,
    per_page: int,
    total_items: int,
    message: Optional[str] = None,
    meta: Optional[Dict[str, Any]] = None,
    version: str = "v1"
) -> PaginatedResponse:
    """Create a standardized paginated response"""
    total_pages = (total_items + per_page - 1) // per_page  # Ceiling division

    pagination = PaginationMeta(
        page=page,
        per_page=per_page,
        total_pages=total_pages,
        total_items=total_items,
        has_next=page < total_pages,
        has_prev=page > 1,
        next_page=page + 1 if page < total_pages else None,
        prev_page=page - 1 if page > 1 else None
    )

    return PaginatedResponse(
        success=True,
        data=items,
        message=message,
        pagination=pagination,
        meta=meta,
        version=version
    )


def create_rate_limited_response(
    retry_after: int,
    limit: int,
    remaining: int,
    reset_time: datetime,
    message: Optional[str] = None
) -> APIErrorResponse:
    """Create a rate limit exceeded error response"""
    return create_error_response(
        code=ErrorCodes.RATE_LIMIT_EXCEEDED,
        message=message or "Rate limit exceeded. Please try again later.",
        details={
            "retry_after": retry_after,
            "limit": limit,
            "remaining": remaining,
            "reset_time": reset_time.isoformat()
        }
    )