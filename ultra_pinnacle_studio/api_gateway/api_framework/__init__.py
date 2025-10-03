"""
Universal API Standardization Framework for Ultra Pinnacle AI Studio

This framework provides standardized patterns for:
- Request/Response formats
- Error handling and status codes
- API versioning and backward compatibility
- Authentication and authorization
- Documentation generation
- Pagination, filtering, and sorting
- Rate limiting and throttling
- Analytics and monitoring
- Webhook and event systems
"""

from .framework import initialize_framework, get_framework, APIFramework
from .versioning import APIVersion
from .responses import (
    APIResponse, APIErrorResponse, PaginatedResponse,
    create_success_response, create_error_response, create_paginated_response
)
from .errors import (
    APIException, AuthenticationError, AuthorizationError, ValidationError, NotFoundError
)
from .pagination import QueryParams, get_query_params, apply_query_params
from .registry import APIRegistry, APIResource, APIResourceType, APIEndpoint
from .analytics import AnalyticsMiddleware, record_api_request, record_api_error
from .webhooks import event_bus, webhook_manager, publish_event, EventTypes

__version__ = "1.0.0"
__author__ = "Ultra Pinnacle AI Studio"

__all__ = [
    # Main framework functions
    "initialize_framework",
    "get_framework",
    "APIFramework",

    # Versioning
    "APIVersion",

    # Responses
    "APIResponse",
    "APIErrorResponse",
    "PaginatedResponse",
    "create_success_response",
    "create_error_response",
    "create_paginated_response",

    # Errors
    "APIException",
    "AuthenticationError",
    "AuthorizationError",
    "ValidationError",
    "NotFoundError",

    # Pagination
    "QueryParams",
    "get_query_params",
    "apply_query_params",

    # Registry
    "APIRegistry",
    "APIResource",
    "APIResourceType",
    "APIEndpoint",

    # Analytics
    "AnalyticsMiddleware",
    "record_api_request",
    "record_api_error",

    # Webhooks
    "event_bus",
    "webhook_manager",
    "publish_event",
    "EventTypes",
]