"""
Standardized Error Handling for Ultra Pinnacle AI Studio

This module provides consistent error handling patterns, custom exception classes,
and error response generation across all API endpoints.
"""

from typing import Any, Dict, Optional, Union
from fastapi import HTTPException, Request
from fastapi.responses import JSONResponse
from .responses import APIErrorResponse, ErrorCodes, create_error_response
import logging

logger = logging.getLogger("ultra_pinnacle")


class APIException(Exception):
    """Base exception class for API errors"""

    def __init__(
        self,
        code: str,
        message: str,
        status_code: int = 400,
        field: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
        meta: Optional[Dict[str, Any]] = None
    ):
        self.code = code
        self.message = message
        self.status_code = status_code
        self.field = field
        self.details = details or {}
        self.meta = meta or {}
        super().__init__(self.message)


class AuthenticationError(APIException):
    """Authentication-related errors"""

    def __init__(self, message: str = "Authentication required", **kwargs):
        super().__init__(
            code=ErrorCodes.UNAUTHORIZED,
            message=message,
            status_code=401,
            **kwargs
        )


class AuthorizationError(APIException):
    """Authorization-related errors"""

    def __init__(self, message: str = "Insufficient permissions", **kwargs):
        super().__init__(
            code=ErrorCodes.FORBIDDEN,
            message=message,
            status_code=403,
            **kwargs
        )


class ValidationError(APIException):
    """Validation-related errors"""

    def __init__(self, message: str = "Validation failed", field: Optional[str] = None, **kwargs):
        super().__init__(
            code=ErrorCodes.VALIDATION_ERROR,
            message=message,
            status_code=400,
            field=field,
            **kwargs
        )


class NotFoundError(APIException):
    """Resource not found errors"""

    def __init__(self, message: str = "Resource not found", **kwargs):
        super().__init__(
            code=ErrorCodes.NOT_FOUND,
            message=message,
            status_code=404,
            **kwargs
        )


class ConflictError(APIException):
    """Resource conflict errors"""

    def __init__(self, message: str = "Resource conflict", **kwargs):
        super().__init__(
            code=ErrorCodes.CONFLICT,
            message=message,
            status_code=409,
            **kwargs
        )


class RateLimitError(APIException):
    """Rate limiting errors"""

    def __init__(self, message: str = "Rate limit exceeded", retry_after: Optional[int] = None, **kwargs):
        details = kwargs.get('details', {})
        if retry_after:
            details['retry_after'] = retry_after

        super().__init__(
            code=ErrorCodes.RATE_LIMIT_EXCEEDED,
            message=message,
            status_code=429,
            details=details,
            **kwargs
        )


class ServiceUnavailableError(APIException):
    """Service unavailable errors"""

    def __init__(self, message: str = "Service temporarily unavailable", **kwargs):
        super().__init__(
            code=ErrorCodes.SERVICE_UNAVAILABLE,
            message=message,
            status_code=503,
            **kwargs
        )


class ExternalServiceError(APIException):
    """External service errors"""

    def __init__(self, message: str = "External service error", **kwargs):
        super().__init__(
            code=ErrorCodes.EXTERNAL_SERVICE_ERROR,
            message=message,
            status_code=502,
            **kwargs
        )


class BusinessLogicError(APIException):
    """Business logic errors"""

    def __init__(self, message: str = "Operation not allowed", **kwargs):
        super().__init__(
            code=ErrorCodes.INVALID_OPERATION,
            message=message,
            status_code=400,
            **kwargs
        )


def handle_api_exception(request: Request, exc: APIException) -> JSONResponse:
    """Convert APIException to standardized JSON response"""
    logger.warning(
        f"API Exception: {exc.code} - {exc.message}",
        extra={
            "error_code": exc.code,
            "status_code": exc.status_code,
            "field": exc.field,
            "request_path": request.url.path,
            "request_method": request.method,
            "client_ip": getattr(request.client, 'host', None) if request.client else None
        }
    )

    error_response = create_error_response(
        code=exc.code,
        message=exc.message,
        field=exc.field,
        details=exc.details,
        meta=exc.meta
    )

    return JSONResponse(
        status_code=exc.status_code,
        content=error_response.dict()
    )


def handle_http_exception(request: Request, exc: HTTPException) -> JSONResponse:
    """Convert FastAPI HTTPException to standardized JSON response"""
    # Map HTTP status codes to error codes
    status_to_code = {
        400: ErrorCodes.VALIDATION_ERROR,
        401: ErrorCodes.UNAUTHORIZED,
        403: ErrorCodes.FORBIDDEN,
        404: ErrorCodes.NOT_FOUND,
        409: ErrorCodes.CONFLICT,
        422: ErrorCodes.VALIDATION_ERROR,
        429: ErrorCodes.RATE_LIMIT_EXCEEDED,
        500: ErrorCodes.INTERNAL_ERROR,
        502: ErrorCodes.EXTERNAL_SERVICE_ERROR,
        503: ErrorCodes.SERVICE_UNAVAILABLE,
    }

    error_code = status_to_code.get(exc.status_code, ErrorCodes.INTERNAL_ERROR)

    logger.warning(
        f"HTTP Exception: {exc.status_code} - {exc.detail}",
        extra={
            "error_code": error_code,
            "status_code": exc.status_code,
            "request_path": request.url.path,
            "request_method": request.method,
            "client_ip": getattr(request.client, 'host', None) if request.client else None
        }
    )

    error_response = create_error_response(
        code=error_code,
        message=exc.detail,
        details={"status_code": exc.status_code}
    )

    return JSONResponse(
        status_code=exc.status_code,
        content=error_response.dict()
    )


def handle_generic_exception(request: Request, exc: Exception) -> JSONResponse:
    """Handle unexpected exceptions with standardized error response"""
    logger.error(
        f"Unexpected error: {type(exc).__name__}: {str(exc)}",
        exc_info=True,
        extra={
            "error_type": type(exc).__name__,
            "request_path": request.url.path,
            "request_method": request.method,
            "client_ip": getattr(request.client, 'host', None) if request.client else None
        }
    )

    error_response = create_error_response(
        code=ErrorCodes.INTERNAL_ERROR,
        message="An unexpected error occurred. Please try again later.",
        details={
            "error_type": type(exc).__name__,
            "error_message": str(exc)
        }
    )

    return JSONResponse(
        status_code=500,
        content=error_response.dict()
    )


# Convenience functions for common errors
def raise_not_found(resource_type: str = "Resource", resource_id: Optional[str] = None):
    """Raise a not found error"""
    message = f"{resource_type} not found"
    if resource_id:
        message += f": {resource_id}"
    raise NotFoundError(message)


def raise_forbidden(message: str = "Access denied"):
    """Raise a forbidden error"""
    raise AuthorizationError(message)


def raise_validation_error(message: str, field: Optional[str] = None, details: Optional[Dict[str, Any]] = None):
    """Raise a validation error"""
    raise ValidationError(message, field=field, details=details)


def raise_conflict(message: str = "Resource already exists"):
    """Raise a conflict error"""
    raise ConflictError(message)


def raise_rate_limited(retry_after: Optional[int] = None):
    """Raise a rate limit error"""
    raise RateLimitError(retry_after=retry_after)


def raise_service_unavailable(service_name: Optional[str] = None):
    """Raise a service unavailable error"""
    message = "Service temporarily unavailable"
    if service_name:
        message = f"{service_name} is temporarily unavailable"
    raise ServiceUnavailableError(message)