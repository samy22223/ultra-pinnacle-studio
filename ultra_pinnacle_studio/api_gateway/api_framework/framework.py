"""
Main API Framework Integration for Ultra Pinnacle AI Studio

This module provides the main framework class that integrates all components
and provides standardized API patterns for FastAPI applications.
"""

from typing import Any, Dict, List, Optional, Callable, Type, Union
from fastapi import FastAPI, Request, Response, HTTPException, Depends
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.openapi.utils import get_openapi
import logging
from datetime import datetime, timezone

from .responses import (
    APIResponse, APIErrorResponse, PaginatedResponse,
    create_success_response, create_error_response, create_paginated_response
)
from .errors import (
    APIException, handle_api_exception, handle_http_exception, handle_generic_exception,
    AuthenticationError, AuthorizationError, ValidationError, NotFoundError
)
from .versioning import VersionedRouter, APIVersion, get_api_version, negotiate_version
from .registry import APIRegistry, APIResource, APIResourceType, APIEndpoint
from .pagination import QueryParams, get_query_params, apply_query_params
from .analytics import AnalyticsMiddleware, record_api_request, record_api_error
from .webhooks import event_bus, webhook_manager, publish_event, EventTypes

logger = logging.getLogger("ultra_pinnacle")


class APIFramework:
    """Main API Framework class"""

    def __init__(
        self,
        app: FastAPI,
        supported_versions: Optional[List[APIVersion]] = None,
        enable_analytics: bool = True,
        enable_webhooks: bool = True,
        enable_registry: bool = True
    ):
        self.app = app
        self.supported_versions = supported_versions or [APIVersion.V1]
        self.enable_analytics = enable_analytics
        self.enable_webhooks = enable_webhooks
        self.enable_registry = enable_registry

        # Initialize components
        self.registry = APIRegistry() if enable_registry else None

        # Setup framework middleware and exception handlers
        self._setup_middleware()
        self._setup_exception_handlers()
        self._setup_openapi_customization()

        logger.info("API Framework initialized")

    def _setup_middleware(self):
        """Setup framework middleware"""
        # Add analytics middleware if enabled
        if self.enable_analytics:
            self.app.add_middleware(AnalyticsMiddleware)

        # Add version negotiation middleware
        from .versioning import VersionMiddleware
        self.app.add_middleware(VersionMiddleware, self.supported_versions)

    def _setup_exception_handlers(self):
        """Setup global exception handlers"""

        @self.app.exception_handler(APIException)
        async def api_exception_handler(request: Request, exc: APIException):
            return await handle_api_exception(request, exc)

        @self.app.exception_handler(HTTPException)
        async def http_exception_handler(request: Request, exc: HTTPException):
            return await handle_http_exception(request, exc)

        @self.app.exception_handler(Exception)
        async def generic_exception_handler(request: Request, exc: Exception):
            return await handle_generic_exception(request, exc)

    def _setup_openapi_customization(self):
        """Customize OpenAPI schema generation"""

        def custom_openapi():
            if self.app.openapi_schema:
                return self.app.openapi_schema

            schema = get_openapi(
                title=self.app.title,
                version=self.app.version,
                description=self.app.description,
                routes=self.app.routes,
            )

            # Add framework-specific extensions
            schema["x-api-framework"] = {
                "name": "Ultra Pinnacle API Framework",
                "version": "1.0.0",
                "supported_versions": [v.value for v in self.supported_versions],
                "features": {
                    "analytics": self.enable_analytics,
                    "webhooks": self.enable_webhooks,
                    "registry": self.enable_registry
                }
            }

            self.app.openapi_schema = schema
            return schema

        self.app.openapi = custom_openapi

    def create_versioned_router(
        self,
        version: APIVersion = APIVersion.V1,
        prefix: Optional[str] = None,
        tags: Optional[List[str]] = None,
        **kwargs
    ) -> VersionedRouter:
        """Create a versioned router"""
        router = VersionedRouter(version=version, **kwargs)

        # Register router with framework
        if self.registry:
            # This would register all routes in the router
            pass

        self.app.include_router(router, prefix=prefix, tags=tags)
        return router

    def register_endpoint(
        self,
        id: str,
        name: str,
        path: str,
        methods: List[str],
        handler: Callable,
        version: str = "v1",
        requires_auth: bool = True,
        permissions: Optional[List[str]] = None,
        **metadata
    ) -> None:
        """Register an API endpoint with the framework"""
        if self.registry:
            endpoint = APIEndpoint(
                id=id,
                name=name,
                type=APIResourceType.ENDPOINT,
                version=version,
                path=path,
                methods=methods,
                handler=handler,
                requires_auth=requires_auth,
                permissions=permissions or [],
                metadata=metadata
            )
            self.registry.register(endpoint)

    def create_standard_endpoint(
        self,
        router: VersionedRouter,
        path: str,
        methods: List[str],
        endpoint_func: Callable,
        summary: str = "",
        description: str = "",
        response_model: Optional[Type] = None,
        dependencies: Optional[List[Depends]] = None,
        tags: Optional[List[str]] = None,
        requires_auth: bool = True,
        permissions: Optional[List[str]] = None,
        enable_pagination: bool = False,
        enable_filtering: bool = False,
        enable_sorting: bool = False,
        enable_search: bool = False
    ) -> Callable:
        """Create a standardized endpoint with framework features"""

        dependencies = dependencies or []

        # Add authentication dependency if required
        if requires_auth:
            from .auth import get_current_active_user
            dependencies.append(Depends(get_current_active_user))

        # Add query parameters dependency for advanced features
        if enable_pagination or enable_filtering or enable_sorting or enable_search:
            dependencies.append(Depends(get_query_params))

        async def framework_wrapper(*args, **kwargs):
            start_time = datetime.now(timezone.utc)
            request = kwargs.get('request')

            try:
                # Extract query params if enabled
                query_params = None
                if enable_pagination or enable_filtering or enable_sorting or enable_search:
                    query_params = kwargs.pop('query_params')

                # Execute the endpoint function
                result = await endpoint_func(*args, **kwargs)

                # Apply framework features
                if query_params and hasattr(result, '__iter__') and not isinstance(result, (str, dict)):
                    # Assume it's a list that needs pagination/filtering
                    # In a real implementation, you'd pass the model class and query
                    pass

                # Publish success event
                if self.enable_webhooks:
                    await publish_event(
                        EventTypes.AI_REQUEST_COMPLETED,
                        "api_framework",
                        {"endpoint": path, "method": methods[0] if methods else "GET"},
                        user_id=getattr(kwargs.get('current_user'), 'id', None)
                    )

                # Record analytics
                if self.enable_analytics and request:
                    response_time = (datetime.now(timezone.utc) - start_time).total_seconds()
                    record_api_request(
                        endpoint=path,
                        method=methods[0] if methods else "GET",
                        status_code=200,
                        response_time=response_time,
                        user_id=getattr(kwargs.get('current_user'), 'id', None),
                        client_ip=getattr(request.client, 'host', None) if request.client else None
                    )

                # Return standardized response
                return create_success_response(result)

            except APIException:
                raise
            except Exception as e:
                # Record error analytics
                if self.enable_analytics and request:
                    response_time = (datetime.now(timezone.utc) - start_time).total_seconds()
                    record_api_error(
                        endpoint=path,
                        method=methods[0] if methods else "GET",
                        status_code=500,
                        error_type=type(e).__name__,
                        error_message=str(e),
                        user_id=getattr(kwargs.get('current_user'), 'id', None),
                        client_ip=getattr(request.client, 'host', None) if request.client else None
                    )

                # Publish error event
                if self.enable_webhooks:
                    await publish_event(
                        EventTypes.AI_REQUEST_FAILED,
                        "api_framework",
                        {"endpoint": path, "error": str(e)},
                        user_id=getattr(kwargs.get('current_user'), 'id', None)
                    )

                logger.error(f"Endpoint error: {path} - {e}", exc_info=True)
                raise

        # Set function metadata
        framework_wrapper.__name__ = endpoint_func.__name__
        framework_wrapper.__doc__ = endpoint_func.__doc__

        # Add route to router
        router.add_api_route(
            path=path,
            endpoint=framework_wrapper,
            methods=methods,
            summary=summary,
            description=description,
            response_model=response_model,
            dependencies=dependencies,
            tags=tags
        )

        # Register endpoint
        endpoint_id = f"{router.version.value}_{path.replace('/', '_')}"
        self.register_endpoint(
            id=endpoint_id,
            name=summary or endpoint_func.__name__,
            path=path,
            methods=methods,
            handler=endpoint_func,
            version=router.version.value,
            requires_auth=requires_auth,
            permissions=permissions
        )

        return framework_wrapper

    def get_registry_stats(self) -> Dict[str, Any]:
        """Get registry statistics"""
        if self.registry:
            return self.registry.get_stats()
        return {}

    def get_analytics_data(self) -> Dict[str, Any]:
        """Get analytics data"""
        if self.enable_analytics:
            from .analytics import get_analytics_dashboard_data
            return get_analytics_dashboard_data()
        return {}

    def get_webhook_stats(self) -> Dict[str, Any]:
        """Get webhook statistics"""
        if self.enable_webhooks:
            return webhook_manager.get_webhook_stats()
        return {}


# Global framework instance
api_framework: Optional[APIFramework] = None


def initialize_framework(
    app: FastAPI,
    supported_versions: Optional[List[APIVersion]] = None,
    **kwargs
) -> APIFramework:
    """Initialize the API framework"""
    global api_framework
    api_framework = APIFramework(app, supported_versions, **kwargs)
    return api_framework


def get_framework() -> APIFramework:
    """Get the global framework instance"""
    if api_framework is None:
        raise RuntimeError("API Framework not initialized. Call initialize_framework() first.")
    return api_framework


# Convenience decorators
def versioned_endpoint(
    version: APIVersion = APIVersion.V1,
    methods: List[str] = ["GET"],
    **kwargs
):
    """Decorator for versioned endpoints"""
    def decorator(func: Callable) -> Callable:
        func._api_version = version
        func._api_methods = methods
        func._api_kwargs = kwargs
        return func
    return decorator


def authenticated_endpoint(permissions: Optional[List[str]] = None):
    """Decorator for authenticated endpoints"""
    def decorator(func: Callable) -> Callable:
        func._requires_auth = True
        func._permissions = permissions or []
        return func
    return decorator


# Framework middleware for FastAPI apps
class FrameworkMiddleware:
    """Framework middleware for automatic request/response processing"""

    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            return await self.app(scope, receive, send)

        # Add framework-specific headers
        async def send_wrapper(message):
            if message["type"] == "http.response.start":
                headers = list(message.get("headers", []))
                headers.append([b"X-API-Framework", b"Ultra-Pinnacle/1.0"])
                message["headers"] = headers
            await send(message)

        await self.app(scope, receive, send_wrapper)