"""
Universal API Registry Integration

This module provides integration between the auto-healing AI engineer system
and the universal API registry, enabling seamless registration and discovery
of dynamically created AI components.
"""

from typing import Dict, List, Any, Optional, Callable
from datetime import datetime, timezone
import logging

from ..api_framework.registry import (
    APIRegistry, APIResource, APIResourceType, AIModel, APIService,
    APIEndpoint, APIRegistry as GlobalRegistry
)
from .core import AutoHealingAIEngineer, AIComponent, ComponentType

logger = logging.getLogger("ultra_pinnacle")


class UniversalAPIRegistryIntegration:
    """
    Integrates the auto-healing AI engineer system with the universal API registry.

    Automatically registers newly created components and maintains synchronization
    between the AI engineer system and the API registry.
    """

    def __init__(self, system: AutoHealingAIEngineer):
        self.system = system
        self.config = system.config.get("registry_integration", {})

        # Registry references
        self.global_registry = GlobalRegistry()
        self.local_registry: Dict[str, APIResource] = {}

        # Integration settings
        self.auto_register = self.config.get("auto_register", True)
        self.sync_interval = self.config.get("sync_interval", 30)  # seconds
        self.register_health_endpoints = self.config.get("register_health_endpoints", True)

        # Component type mappings
        self.component_type_mapping = {
            ComponentType.MODEL: APIResourceType.MODEL,
            ComponentType.AGENT: APIResourceType.SERVICE,  # Agents as services
            ComponentType.SERVICE: APIResourceType.SERVICE,
            ComponentType.MONITOR: APIResourceType.SERVICE,
            ComponentType.HEALER: APIResourceType.SERVICE,
            ComponentType.TRAINER: APIResourceType.SERVICE,
            ComponentType.LIFECYCLE_MANAGER: APIResourceType.SERVICE
        }

        # Register event handlers
        self.system.register_event_handler("component_created", self._on_component_created)
        self.system.register_event_handler("component_updated", self._on_component_updated)
        self.system.register_event_handler("component_deleted", self._on_component_deleted)

        logger.info("Universal API Registry Integration initialized")

    def register_component(self, component: AIComponent) -> bool:
        """Register a component with the universal API registry"""
        try:
            # Create appropriate API resource
            api_resource = self._create_api_resource(component)

            if api_resource:
                # Register with global registry
                self.global_registry.register(api_resource)
                self.local_registry[component.id] = api_resource

                # Register health endpoint if enabled
                if self.register_health_endpoints:
                    self._register_health_endpoint(component)

                logger.info(f"Registered component {component.id} with API registry")
                return True

        except Exception as e:
            logger.error(f"Failed to register component {component.id}: {e}")

        return False

    def unregister_component(self, component_id: str) -> bool:
        """Unregister a component from the API registry"""
        try:
            # Remove from global registry
            success = self.global_registry.unregister(component_id)

            # Remove from local registry
            if component_id in self.local_registry:
                del self.local_registry[component_id]

            if success:
                logger.info(f"Unregistered component {component_id} from API registry")
            return success

        except Exception as e:
            logger.error(f"Failed to unregister component {component_id}: {e}")

        return False

    def _create_api_resource(self, component: AIComponent) -> Optional[APIResource]:
        """Create an API resource from an AI component"""
        resource_type = self.component_type_mapping.get(component.type)

        if not resource_type:
            logger.warning(f"No mapping found for component type {component.type}")
            return None

        # Create resource based on type
        if resource_type == APIResourceType.MODEL:
            return self._create_model_resource(component)
        elif resource_type == APIResourceType.SERVICE:
            return self._create_service_resource(component)
        else:
            return self._create_generic_resource(component, resource_type)

    def _create_model_resource(self, component: AIComponent) -> AIModel:
        """Create an AI model resource"""
        # Extract model-specific configuration
        model_config = component.configuration
        provider = model_config.get("provider", "auto_healing_system")
        model_name = model_config.get("model_name", component.name)

        # Determine capabilities
        capabilities = component.capabilities or ["general_ai"]
        if component.domain != "general":
            capabilities.append(f"{component.domain}_specialization")

        return AIModel(
            id=component.id,
            name=component.name,
            type=APIResourceType.MODEL,
            version=component.version,
            description=f"Auto-generated {component.type.value} for {component.domain}",
            tags=[component.domain, component.type.value, "auto_healing"],
            provider=provider,
            model_name=model_name,
            capabilities=capabilities,
            max_tokens=model_config.get("max_tokens"),
            context_window=model_config.get("context_window"),
            supported_tasks=self._get_supported_tasks(component),
            metadata={
                "auto_generated": True,
                "health_score": component.health_score,
                "created_by": "auto_healing_ai_engineer",
                "domain": component.domain
            }
        )

    def _create_service_resource(self, component: AIComponent) -> APIService:
        """Create an API service resource"""
        # Generate endpoints based on component type
        endpoints = self._generate_service_endpoints(component)

        return APIService(
            id=component.id,
            name=component.name,
            type=APIResourceType.SERVICE,
            version=component.version,
            description=f"Auto-generated {component.type.value} service for {component.domain}",
            tags=[component.domain, component.type.value, "auto_healing"],
            service_type=f"ai_{component.type.value}",
            endpoints=endpoints,
            health_check_url=f"/api/ai-engineer/components/{component.id}/health",
            config={
                "auto_generated": True,
                "health_score": component.health_score,
                "capabilities": component.capabilities,
                "domain": component.domain
            },
            metadata={
                "created_by": "auto_healing_ai_engineer",
                "component_type": component.type.value,
                "performance_metrics": component.performance_metrics
            }
        )

    def _create_generic_resource(self, component: AIComponent, resource_type: APIResourceType) -> APIResource:
        """Create a generic API resource"""
        return APIResource(
            id=component.id,
            name=component.name,
            type=resource_type,
            version=component.version,
            description=f"Auto-generated {component.type.value} for {component.domain}",
            tags=[component.domain, component.type.value, "auto_healing"],
            metadata={
                "auto_generated": True,
                "health_score": component.health_score,
                "capabilities": component.capabilities,
                "domain": component.domain,
                "created_by": "auto_healing_ai_engineer"
            }
        )

    def _generate_service_endpoints(self, component: AIComponent) -> List[str]:
        """Generate API endpoints for a service component"""
        base_endpoints = [
            f"/api/ai-engineer/components/{component.id}",
            f"/api/ai-engineer/components/{component.id}/status"
        ]

        # Add type-specific endpoints
        if component.type == ComponentType.MODEL:
            base_endpoints.extend([
                f"/api/ai-engineer/components/{component.id}/predict",
                f"/api/ai-engineer/components/{component.id}/train"
            ])
        elif component.type == ComponentType.AGENT:
            base_endpoints.extend([
                f"/api/ai-engineer/components/{component.id}/execute",
                f"/api/ai-engineer/components/{component.id}/status"
            ])
        elif component.type == ComponentType.SERVICE:
            base_endpoints.extend([
                f"/api/ai-engineer/components/{component.id}/process",
                f"/api/ai-engineer/components/{component.id}/metrics"
            ])

        return base_endpoints

    def _get_supported_tasks(self, component: AIComponent) -> List[str]:
        """Get supported tasks for a model component"""
        task_mapping = {
            "general": ["text_generation", "question_answering", "summarization"],
            "healthcare": ["medical_diagnosis", "symptom_analysis", "treatment_recommendation"],
            "finance": ["risk_assessment", "market_analysis", "fraud_detection"],
            "education": ["content_generation", "assessment_creation", "personalized_learning"]
        }

        return task_mapping.get(component.domain, ["general_ai"])

    def _register_health_endpoint(self, component: AIComponent):
        """Register a health endpoint for the component"""
        try:
            from ..api_framework import get_framework

            framework = get_framework()

            # Create health endpoint
            endpoint = APIEndpoint(
                id=f"{component.id}_health",
                name=f"{component.name} Health Check",
                type=APIResourceType.ENDPOINT,
                version="v1",
                path=f"/api/ai-engineer/components/{component.id}/health",
                methods=["GET"],
                requires_auth=False,
                metadata={
                    "component_id": component.id,
                    "auto_generated": True
                }
            )

            framework.registry.register(endpoint)
            logger.debug(f"Registered health endpoint for component {component.id}")

        except Exception as e:
            logger.warning(f"Failed to register health endpoint for {component.id}: {e}")

    def update_component_registration(self, component: AIComponent):
        """Update an existing component registration"""
        try:
            # Get existing resource
            existing_resource = self.local_registry.get(component.id)
            if not existing_resource:
                # Register as new if not found
                self.register_component(component)
                return

            # Update resource metadata
            existing_resource.metadata.update({
                "health_score": component.health_score,
                "performance_metrics": component.performance_metrics,
                "last_updated": datetime.now(timezone.utc).isoformat()
            })

            # Update status tags
            existing_resource.tags = [
                tag for tag in existing_resource.tags
                if not tag.startswith("status_")
            ]
            existing_resource.tags.append(f"status_{component.status}")

            # Update in global registry
            self.global_registry.register(existing_resource)

            logger.debug(f"Updated registration for component {component.id}")

        except Exception as e:
            logger.error(f"Failed to update registration for {component.id}: {e}")

    def sync_with_registry(self):
        """Synchronize local components with the global registry"""
        try:
            # Get all AI engineer components from global registry
            ai_engineer_resources = self.global_registry.list(tags=["auto_healing"])

            # Check for components that exist in registry but not locally
            registry_component_ids = {r.id for r in ai_engineer_resources}
            local_component_ids = set(self.system.components.keys())

            # Components in registry but not in system (orphaned)
            orphaned_ids = registry_component_ids - local_component_ids
            for orphaned_id in orphaned_ids:
                logger.warning(f"Found orphaned component in registry: {orphaned_id}")
                # Could optionally clean up orphaned registrations

            # Components in system but not in registry (missing registration)
            missing_ids = local_component_ids - registry_component_ids
            for missing_id in missing_ids:
                component = self.system.components.get(missing_id)
                if component:
                    logger.info(f"Re-registering missing component: {missing_id}")
                    self.register_component(component)

        except Exception as e:
            logger.error(f"Failed to sync with registry: {e}")

    def get_registered_components(self) -> List[Dict[str, Any]]:
        """Get all components registered with the API registry"""
        components = []

        for resource in self.local_registry.values():
            component_data = {
                "id": resource.id,
                "name": resource.name,
                "type": resource.type.value,
                "version": resource.version,
                "status": resource.status.value,
                "tags": resource.tags,
                "metadata": resource.metadata,
                "registered_at": resource.created_at.isoformat()
            }

            # Add type-specific data
            if isinstance(resource, AIModel):
                component_data.update({
                    "provider": resource.provider,
                    "model_name": resource.model_name,
                    "capabilities": resource.capabilities,
                    "max_tokens": resource.max_tokens
                })
            elif isinstance(resource, APIService):
                component_data.update({
                    "service_type": resource.service_type,
                    "endpoints": resource.endpoints,
                    "health_check_url": resource.health_check_url
                })

            components.append(component_data)

        return components

    def discover_components(self, filters: Optional[Dict[str, Any]] = None) -> List[APIResource]:
        """Discover components in the registry based on filters"""
        filters = filters or {}

        # Start with all AI engineer components
        resources = self.global_registry.list(tags=["auto_healing"])

        # Apply filters
        if "type" in filters:
            resource_type = filters["type"]
            if isinstance(resource_type, str):
                resource_type = APIResourceType(resource_type)
            resources = [r for r in resources if r.type == resource_type]

        if "domain" in filters:
            domain = filters["domain"]
            resources = [r for r in resources if domain in r.tags]

        if "capabilities" in filters:
            required_caps = filters["capabilities"]
            filtered_resources = []
            for resource in resources:
                if isinstance(resource, AIModel):
                    if all(cap in resource.capabilities for cap in required_caps):
                        filtered_resources.append(resource)
                elif isinstance(resource, APIService):
                    # Check service capabilities in metadata
                    service_caps = resource.metadata.get("capabilities", [])
                    if all(cap in service_caps for cap in required_caps):
                        filtered_resources.append(resource)
            resources = filtered_resources

        if "min_health_score" in filters:
            min_score = filters["min_health_score"]
            resources = [
                r for r in resources
                if r.metadata.get("health_score", 0) >= min_score
            ]

        return resources

    def get_component_endpoints(self, component_id: str) -> List[Dict[str, Any]]:
        """Get all endpoints for a registered component"""
        resource = self.local_registry.get(component_id)
        if not resource or not isinstance(resource, APIService):
            return []

        endpoints = []
        for endpoint_path in resource.endpoints:
            # Find the actual endpoint resource
            endpoint_resources = self.global_registry.list(
                resource_type=APIResourceType.ENDPOINT
            )

            for endpoint_res in endpoint_resources:
                if isinstance(endpoint_res, APIEndpoint) and endpoint_res.path == endpoint_path:
                    endpoints.append({
                        "id": endpoint_res.id,
                        "path": endpoint_res.path,
                        "methods": endpoint_res.methods,
                        "requires_auth": endpoint_res.requires_auth,
                        "description": endpoint_res.metadata.get("description", "")
                    })
                    break

        return endpoints

    def create_component_token(self, component_id: str, permissions: List[str] = None) -> Optional[str]:
        """Create an access token for a component"""
        # This would integrate with the auth system to create component-specific tokens
        # Placeholder for now
        logger.info(f"Component token creation not implemented for {component_id}")
        return None

    def validate_component_access(self, component_id: str, token: str) -> bool:
        """Validate access token for a component"""
        # Placeholder for token validation
        return True

    # Event handlers
    def _on_component_created(self, event_data: Dict[str, Any]):
        """Handle component creation event"""
        component_id = event_data.get("component_id")
        if component_id and self.auto_register:
            component = self.system.components.get(component_id)
            if component:
                self.register_component(component)

    def _on_component_updated(self, event_data: Dict[str, Any]):
        """Handle component update event"""
        component_id = event_data.get("component_id")
        if component_id:
            component = self.system.components.get(component_id)
            if component:
                self.update_component_registration(component)

    def _on_component_deleted(self, event_data: Dict[str, Any]):
        """Handle component deletion event"""
        component_id = event_data.get("component_id")
        if component_id:
            self.unregister_component(component_id)

    def get_registry_stats(self) -> Dict[str, Any]:
        """Get registry integration statistics"""
        total_registered = len(self.local_registry)
        healthy_components = len([
            r for r in self.local_registry.values()
            if r.metadata.get("health_score", 0) >= 80
        ])

        # Count by type
        type_counts = {}
        for resource in self.local_registry.values():
            res_type = resource.type.value
            type_counts[res_type] = type_counts.get(res_type, 0) + 1

        return {
            "total_registered_components": total_registered,
            "healthy_registered_components": healthy_components,
            "registration_health_percentage": (healthy_components / max(1, total_registered)) * 100,
            "components_by_type": type_counts,
            "auto_registration_enabled": self.auto_register,
            "health_endpoints_registered": self.register_health_endpoints
        }