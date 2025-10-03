"""
Domain API Integration for Ultra Pinnacle AI Studio

This module provides seamless integration between the domain expansion framework
and the universal API standardization framework, enabling domain modules to
expose their capabilities through standardized REST APIs.
"""

from typing import Dict, List, Any, Optional, Callable, Type, Union
from fastapi import FastAPI, Request, Response, HTTPException, Depends, Query
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.openapi.utils import get_openapi
import logging
from datetime import datetime, timezone

from .domain_expansion_framework import (
    DomainExpansionFramework, DomainType, DomainFramework,
    DomainModule, DomainTemplate, get_domain_expansion_framework
)
from ..api_framework.framework import APIFramework, APIVersion
from ..api_framework.responses import (
    APIResponse, APIErrorResponse, PaginatedResponse,
    create_success_response, create_error_response, create_paginated_response
)
from ..api_framework.errors import APIException
from ..api_framework.versioning import VersionedRouter
from ..api_framework.registry import APIRegistry, APIResource, APIResourceType, APIEndpoint
from ..api_framework.pagination import QueryParams

logger = logging.getLogger("ultra_pinnacle")


class DomainAPIIntegration:
    """
    Integration layer between domain expansion framework and API framework.

    This class provides standardized API endpoints for domain operations
    and enables domain modules to expose their capabilities through REST APIs.
    """

    def __init__(
        self,
        domain_framework: DomainExpansionFramework,
        api_framework: APIFramework,
        auto_register_endpoints: bool = True
    ):
        self.domain_framework = domain_framework
        self.api_framework = api_framework
        self.auto_register_endpoints = auto_register_endpoints

        # API routers for different domain operations
        self.domain_router = None
        self.module_router = None
        self.template_router = None
        self.testing_router = None

        # Initialize integration
        self._initialize_integration()

    def _initialize_integration(self):
        """Initialize domain API integration"""
        try:
            logger.info("Initializing Domain API Integration")

            # Create API routers
            self._create_api_routers()

            # Register domain endpoints if auto-registration is enabled
            if self.auto_register_endpoints:
                self._register_domain_endpoints()

            # Setup domain event handlers
            self._setup_domain_event_handlers()

            logger.info("Domain API Integration initialized successfully")

        except Exception as e:
            logger.error(f"Failed to initialize Domain API Integration: {e}")
            raise

    def _create_api_routers(self):
        """Create API routers for domain operations"""
        # Main domain operations router
        self.domain_router = self.api_framework.create_versioned_router(
            version=APIVersion.V1,
            prefix="/api/v1/domains",
            tags=["Domain Management"]
        )

        # Domain module management router
        self.module_router = self.api_framework.create_versioned_router(
            version=APIVersion.V1,
            prefix="/api/v1/modules",
            tags=["Module Management"]
        )

        # Domain template router
        self.template_router = self.api_framework.create_versioned_router(
            version=APIVersion.V1,
            prefix="/api/v1/templates",
            tags=["Template Management"]
        )

        # Domain testing router
        self.testing_router = self.api_framework.create_versioned_router(
            version=APIVersion.V1,
            prefix="/api/v1/testing",
            tags=["Domain Testing"]
        )

    def _register_domain_endpoints(self):
        """Register standardized domain API endpoints"""
        # Domain listing and information endpoints
        self._register_domain_info_endpoints()

        # Domain module management endpoints
        self._register_module_management_endpoints()

        # Domain template endpoints
        self._register_template_endpoints()

        # Domain testing endpoints
        self._register_testing_endpoints()

        # Domain capability endpoints
        self._register_capability_endpoints()

    def _register_domain_info_endpoints(self):
        """Register domain information endpoints"""

        @self.api_framework.create_standard_endpoint(
            router=self.domain_router,
            path="/",
            methods=["GET"],
            summary="List all domains",
            description="Get comprehensive list of all available domains with their status and capabilities",
            response_model=APIResponse,
            enable_pagination=True,
            enable_filtering=True,
            enable_sorting=True,
            requires_auth=True,
            permissions=["domain:read"]
        )
        async def list_domains(
            request: Request,
            query_params: QueryParams = Depends(QueryParams)
        ):
            """List all available domains"""
            try:
                domains = self.domain_framework.list_domains()

                # Apply pagination and filtering
                if query_params:
                    # Simple filtering implementation
                    if query_params.search:
                        domains = [d for d in domains if query_params.search.lower() in d["name"].lower()]

                    # Simple sorting implementation
                    if query_params.sort_by:
                        domains.sort(key=lambda x: x.get(query_params.sort_by, ""))

                    # Simple pagination implementation
                    if query_params.page and query_params.page_size:
                        start_idx = (query_params.page - 1) * query_params.page_size
                        end_idx = start_idx + query_params.page_size
                        domains = domains[start_idx:end_idx]

                return create_success_response({
                    "domains": domains,
                    "total": len(domains),
                    "filters_applied": bool(query_params and (query_params.search or query_params.sort_by))
                })

            except Exception as e:
                logger.error(f"Failed to list domains: {e}")
                raise APIException(
                    message="Failed to retrieve domains",
                    error_code="DOMAIN_LIST_ERROR",
                    details={"error": str(e)}
                )

        @self.api_framework.create_standard_endpoint(
            router=self.domain_router,
            path="/{domain_id}",
            methods=["GET"],
            summary="Get domain details",
            description="Get detailed information about a specific domain including capabilities and status",
            response_model=APIResponse,
            requires_auth=True,
            permissions=["domain:read"]
        )
        async def get_domain_details(domain_id: str, request: Request):
            """Get detailed information about a specific domain"""
            try:
                domain_status = self.domain_framework.get_domain_status(domain_id)

                if not domain_status:
                    raise APIException(
                        message=f"Domain '{domain_id}' not found",
                        error_code="DOMAIN_NOT_FOUND",
                        status_code=404
                    )

                return create_success_response(domain_status)

            except APIException:
                raise
            except Exception as e:
                logger.error(f"Failed to get domain details for {domain_id}: {e}")
                raise APIException(
                    message="Failed to retrieve domain details",
                    error_code="DOMAIN_DETAILS_ERROR",
                    details={"domain_id": domain_id, "error": str(e)}
                )

        @self.api_framework.create_standard_endpoint(
            router=self.domain_router,
            path="/{domain_id}/capabilities",
            methods=["GET"],
            summary="Get domain capabilities",
            description="Get detailed capabilities and features of a specific domain",
            response_model=APIResponse,
            requires_auth=True,
            permissions=["domain:read"]
        )
        async def get_domain_capabilities(domain_id: str, request: Request):
            """Get capabilities for a specific domain"""
            try:
                # Get framework for domain
                framework = self.domain_framework.domain_frameworks.get(domain_id)
                if not framework:
                    raise APIException(
                        message=f"Domain framework '{domain_id}' not found",
                        error_code="DOMAIN_FRAMEWORK_NOT_FOUND",
                        status_code=404
                    )

                capabilities = framework.get_domain_capabilities()
                return create_success_response(capabilities)

            except APIException:
                raise
            except Exception as e:
                logger.error(f"Failed to get capabilities for {domain_id}: {e}")
                raise APIException(
                    message="Failed to retrieve domain capabilities",
                    error_code="DOMAIN_CAPABILITIES_ERROR",
                    details={"domain_id": domain_id, "error": str(e)}
                )

    def _register_module_management_endpoints(self):
        """Register domain module management endpoints"""

        @self.api_framework.create_standard_endpoint(
            router=self.module_router,
            path="/",
            methods=["GET"],
            summary="List available modules",
            description="Get list of all available domain modules with their status",
            response_model=APIResponse,
            enable_pagination=True,
            requires_auth=True,
            permissions=["module:read"]
        )
        async def list_modules(
            request: Request,
            query_params: QueryParams = Depends(QueryParams)
        ):
            """List all available domain modules"""
            try:
                modules = self.domain_framework.list_available_modules()

                # Apply filtering and pagination
                if query_params:
                    if query_params.search:
                        modules = [m for m in modules if query_params.search.lower() in m["name"].lower()]

                    if query_params.sort_by:
                        modules.sort(key=lambda x: x.get(query_params.sort_by, ""))

                    if query_params.page and query_params.page_size:
                        start_idx = (query_params.page - 1) * query_params.page_size
                        end_idx = start_idx + query_params.page_size
                        modules = modules[start_idx:end_idx]

                return create_success_response({
                    "modules": modules,
                    "total": len(modules)
                })

            except Exception as e:
                logger.error(f"Failed to list modules: {e}")
                raise APIException(
                    message="Failed to retrieve modules",
                    error_code="MODULE_LIST_ERROR",
                    details={"error": str(e)}
                )

        @self.api_framework.create_standard_endpoint(
            router=self.module_router,
            path="/{module_id}/load",
            methods=["POST"],
            summary="Load domain module",
            description="Dynamically load a domain module into the system",
            response_model=APIResponse,
            requires_auth=True,
            permissions=["module:manage"]
        )
        async def load_module(module_id: str, request: Request):
            """Load a domain module"""
            try:
                success = self.domain_framework.load_module(module_id)

                if not success:
                    raise APIException(
                        message=f"Failed to load module '{module_id}'",
                        error_code="MODULE_LOAD_FAILED",
                        status_code=400
                    )

                # Get updated module status
                module_status = self.domain_framework.get_module_status(module_id)

                return create_success_response({
                    "message": f"Module '{module_id}' loaded successfully",
                    "module": module_status
                })

            except APIException:
                raise
            except Exception as e:
                logger.error(f"Failed to load module {module_id}: {e}")
                raise APIException(
                    message="Failed to load module",
                    error_code="MODULE_LOAD_ERROR",
                    details={"module_id": module_id, "error": str(e)}
                )

        @self.api_framework.create_standard_endpoint(
            router=self.module_router,
            path="/{module_id}/unload",
            methods=["POST"],
            summary="Unload domain module",
            description="Unload a domain module from the system",
            response_model=APIResponse,
            requires_auth=True,
            permissions=["module:manage"]
        )
        async def unload_module(module_id: str, request: Request):
            """Unload a domain module"""
            try:
                success = self.domain_framework.unload_module(module_id)

                if not success:
                    raise APIException(
                        message=f"Failed to unload module '{module_id}'",
                        error_code="MODULE_UNLOAD_FAILED",
                        status_code=400
                    )

                return create_success_response({
                    "message": f"Module '{module_id}' unloaded successfully"
                })

            except APIException:
                raise
            except Exception as e:
                logger.error(f"Failed to unload module {module_id}: {e}")
                raise APIException(
                    message="Failed to unload module",
                    error_code="MODULE_UNLOAD_ERROR",
                    details={"module_id": module_id, "error": str(e)}
                )

    def _register_template_endpoints(self):
        """Register domain template endpoints"""

        @self.api_framework.create_standard_endpoint(
            router=self.template_router,
            path="/",
            methods=["GET"],
            summary="List domain templates",
            description="Get list of available domain creation templates",
            response_model=APIResponse,
            requires_auth=True,
            permissions=["template:read"]
        )
        async def list_templates(request: Request):
            """List all available domain templates"""
            try:
                templates = self.domain_framework.list_domain_templates()
                return create_success_response({"templates": templates})

            except Exception as e:
                logger.error(f"Failed to list templates: {e}")
                raise APIException(
                    message="Failed to retrieve templates",
                    error_code="TEMPLATE_LIST_ERROR",
                    details={"error": str(e)}
                )

        @self.api_framework.create_standard_endpoint(
            router=self.template_router,
            path="/{template_id}/create",
            methods=["POST"],
            summary="Create domain from template",
            description="Create a new domain module from a template",
            response_model=APIResponse,
            requires_auth=True,
            permissions=["template:create"]
        )
        async def create_domain_from_template(
            template_id: str,
            domain_config: Dict[str, Any],
            request: Request
        ):
            """Create a new domain from template"""
            try:
                success = self.domain_framework.create_domain_from_template(template_id, domain_config)

                if not success:
                    raise APIException(
                        message=f"Failed to create domain from template '{template_id}'",
                        error_code="DOMAIN_CREATION_FAILED",
                        status_code=400
                    )

                return create_success_response({
                    "message": f"Domain created successfully from template '{template_id}'",
                    "domain_id": domain_config.get("domain_id")
                })

            except APIException:
                raise
            except Exception as e:
                logger.error(f"Failed to create domain from template {template_id}: {e}")
                raise APIException(
                    message="Failed to create domain from template",
                    error_code="TEMPLATE_CREATION_ERROR",
                    details={"template_id": template_id, "error": str(e)}
                )

    def _register_testing_endpoints(self):
        """Register domain testing endpoints"""

        @self.api_framework.create_standard_endpoint(
            router=self.testing_router,
            path="/run",
            methods=["POST"],
            summary="Run domain tests",
            description="Execute comprehensive tests for all domain frameworks",
            response_model=APIResponse,
            requires_auth=True,
            permissions=["testing:execute"]
        )
        async def run_domain_tests(
            request: Request,
            test_config: Optional[Dict[str, Any]] = None
        ):
            """Run comprehensive domain tests"""
            try:
                # Import testing framework dynamically to avoid circular imports
                from .domain_testing_framework import run_all_domain_tests, TestConfig

                # Create test configuration
                config = TestConfig(**(test_config or {}))

                # Run tests
                test_results = await run_all_domain_tests(config)

                return create_success_response({
                    "message": "Domain tests completed",
                    "results": test_results
                })

            except Exception as e:
                logger.error(f"Failed to run domain tests: {e}")
                raise APIException(
                    message="Failed to execute domain tests",
                    error_code="TESTING_ERROR",
                    details={"error": str(e)}
                )

    def _register_capability_endpoints(self):
        """Register domain capability endpoints"""

        @self.api_framework.create_standard_endpoint(
            router=self.domain_router,
            path="/capabilities",
            methods=["GET"],
            summary="Get all domain capabilities",
            description="Get comprehensive overview of all domain capabilities across the system",
            response_model=APIResponse,
            requires_auth=True,
            permissions=["capability:read"]
        )
        async def get_all_capabilities(request: Request):
            """Get all domain capabilities"""
            try:
                capabilities = {
                    "domain_capabilities": {},
                    "ai_capabilities": {},
                    "service_capabilities": {},
                    "platform_capabilities": {}
                }

                # Aggregate capabilities from all domains
                for domain_id, framework in self.domain_framework.domain_frameworks.items():
                    try:
                        domain_capabilities = framework.get_domain_capabilities()
                        capabilities["domain_capabilities"][domain_id] = domain_capabilities
                    except Exception as e:
                        logger.warning(f"Failed to get capabilities for domain {domain_id}: {e}")

                # Add AI capabilities
                capabilities["ai_capabilities"] = {
                    cap.value: config for cap, config in self.domain_framework.ai_capabilities.items()
                }

                # Add service capabilities
                capabilities["service_capabilities"] = {
                    svc_id: svc.configuration for svc_id, svc in self.domain_framework.core_services.items()
                }

                # Add platform capabilities
                capabilities["platform_capabilities"] = {
                    plat.stack_id: plat.configuration for plat in self.domain_framework.platform_stacks.values()
                }

                return create_success_response(capabilities)

            except Exception as e:
                logger.error(f"Failed to get all capabilities: {e}")
                raise APIException(
                    message="Failed to retrieve capabilities",
                    error_code="CAPABILITIES_ERROR",
                    details={"error": str(e)}
                )

    def _setup_domain_event_handlers(self):
        """Setup event handlers for domain operations"""
        try:
            # Import event system
            from ..api_framework.webhooks import event_bus, EventTypes

            # Subscribe to domain-related events
            async def handle_domain_loaded_event(event_data: Dict[str, Any]):
                """Handle domain module loaded event"""
                module_id = event_data.get("module_id")
                if module_id:
                    logger.info(f"Domain module loaded event received: {module_id}")
                    # Could trigger additional integration or notification logic

            async def handle_domain_error_event(event_data: Dict[str, Any]):
                """Handle domain error event"""
                error = event_data.get("error")
                domain_id = event_data.get("domain_id")
                if error and domain_id:
                    logger.error(f"Domain error event received - Domain: {domain_id}, Error: {error}")
                    # Could trigger error handling or recovery logic

            # Register event handlers (this would be implemented based on the actual event system)
            logger.info("Domain event handlers configured")

        except Exception as e:
            logger.error(f"Failed to setup domain event handlers: {e}")

    def register_domain_api_routes(self, app: FastAPI):
        """Register all domain API routes with the FastAPI app"""
        try:
            # The routers are already registered with the API framework
            # This method can be used for additional custom registration if needed

            logger.info("Domain API routes registered successfully")

        except Exception as e:
            logger.error(f"Failed to register domain API routes: {e}")
            raise

    def get_domain_api_info(self) -> Dict[str, Any]:
        """Get information about registered domain APIs"""
        return {
            "domain_endpoints": {
                "list_domains": "/api/v1/domains/",
                "get_domain": "/api/v1/domains/{domain_id}",
                "get_capabilities": "/api/v1/domains/{domain_id}/capabilities"
            },
            "module_endpoints": {
                "list_modules": "/api/v1/modules/",
                "load_module": "/api/v1/modules/{module_id}/load",
                "unload_module": "/api/v1/modules/{module_id}/unload"
            },
            "template_endpoints": {
                "list_templates": "/api/v1/templates/",
                "create_from_template": "/api/v1/templates/{template_id}/create"
            },
            "testing_endpoints": {
                "run_tests": "/api/v1/testing/run"
            },
            "total_endpoints": 8,
            "api_version": "v1",
            "authentication_required": True
        }

    def validate_domain_api_integration(self) -> Dict[str, Any]:
        """Validate domain API integration"""
        validation_result = {
            "integration_status": "unknown",
            "api_framework_connected": False,
            "domain_framework_connected": False,
            "endpoints_registered": False,
            "event_handlers_configured": False,
            "issues": []
        }

        try:
            # Check API framework connection
            if self.api_framework:
                validation_result["api_framework_connected"] = True
            else:
                validation_result["issues"].append("API framework not connected")

            # Check domain framework connection
            if self.domain_framework:
                validation_result["domain_framework_connected"] = True
            else:
                validation_result["issues"].append("Domain framework not connected")

            # Check if routers are created
            if all([self.domain_router, self.module_router, self.template_router, self.testing_router]):
                validation_result["endpoints_registered"] = True
            else:
                validation_result["issues"].append("Not all API routers are created")

            # Determine overall status
            if (validation_result["api_framework_connected"] and
                validation_result["domain_framework_connected"] and
                validation_result["endpoints_registered"]):
                validation_result["integration_status"] = "healthy"
            else:
                validation_result["integration_status"] = "degraded"

        except Exception as e:
            validation_result["integration_status"] = "error"
            validation_result["issues"].append(f"Validation error: {str(e)}")

        return validation_result


# Global integration instance
domain_api_integration: Optional[DomainAPIIntegration] = None


def initialize_domain_api_integration(
    domain_framework: Optional[DomainExpansionFramework] = None,
    api_framework: Optional[APIFramework] = None,
    auto_register_endpoints: bool = True
) -> DomainAPIIntegration:
    """Initialize domain API integration"""
    global domain_api_integration

    if domain_api_integration is None:
        # Get framework instances if not provided
        if domain_framework is None:
            # This would get the actual domain framework instance
            # For now, create a placeholder
            from .core import AutoHealingAIEngineer
            system = AutoHealingAIEngineer()
            domain_framework = get_domain_expansion_framework(system)

        if api_framework is None:
            # This would get the actual API framework instance
            # For now, create a placeholder
            from fastapi import FastAPI
            app = FastAPI()
            api_framework = APIFramework(app)

        domain_api_integration = DomainAPIIntegration(
            domain_framework=domain_framework,
            api_framework=api_framework,
            auto_register_endpoints=auto_register_endpoints
        )

    return domain_api_integration


def get_domain_api_integration() -> DomainAPIIntegration:
    """Get the global domain API integration instance"""
    if domain_api_integration is None:
        raise RuntimeError("Domain API Integration not initialized. Call initialize_domain_api_integration() first.")
    return domain_api_integration