"""
API Registry for Ultra Pinnacle AI Studio

This module provides centralized registration and discovery of API functionalities,
including endpoints, models, services, and capabilities.
"""

from typing import Any, Dict, List, Optional, Callable, Type, Union
from dataclasses import dataclass, field
from enum import Enum
import logging
from datetime import datetime, timezone

logger = logging.getLogger("ultra_pinnacle")


class APIResourceType(Enum):
    """Types of API resources"""

    ENDPOINT = "endpoint"
    MODEL = "model"
    SERVICE = "service"
    PLUGIN = "plugin"
    WEBHOOK = "webhook"
    AUTH_PROVIDER = "auth_provider"
    STORAGE_PROVIDER = "storage_provider"


class APIResourceStatus(Enum):
    """Status of API resources"""

    ACTIVE = "active"
    INACTIVE = "inactive"
    DEPRECATED = "deprecated"
    MAINTENANCE = "maintenance"
    EXPERIMENTAL = "experimental"


@dataclass
class APIResource:
    """Base class for API resources"""

    id: str
    name: str
    type: APIResourceType
    status: APIResourceStatus = APIResourceStatus.ACTIVE
    version: str = "v1"
    description: Optional[str] = None
    tags: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def to_dict(self) -> Dict[str, Any]:
        """Convert resource to dictionary"""
        return {
            "id": self.id,
            "name": self.name,
            "type": self.type.value,
            "status": self.status.value,
            "version": self.version,
            "description": self.description,
            "tags": self.tags,
            "metadata": self.metadata,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat()
        }


@dataclass
class APIEndpoint(APIResource):
    """API endpoint resource"""

    path: str = field(default="")
    methods: List[str] = field(default_factory=list)
    handler: Optional[Callable] = None
    requires_auth: bool = True
    rate_limit: Optional[Dict[str, Any]] = None
    permissions: List[str] = field(default_factory=list)
    input_schema: Optional[Dict[str, Any]] = None
    output_schema: Optional[Dict[str, Any]] = None

    def to_dict(self) -> Dict[str, Any]:
        base_dict = super().to_dict()
        base_dict.update({
            "path": self.path,
            "methods": self.methods,
            "requires_auth": self.requires_auth,
            "rate_limit": self.rate_limit,
            "permissions": self.permissions,
            "input_schema": self.input_schema,
            "output_schema": self.output_schema
        })
        return base_dict


@dataclass
class AIModel(APIResource):
    """AI model resource"""

    provider: str = ""
    model_name: str = ""
    capabilities: List[str] = field(default_factory=list)
    max_tokens: Optional[int] = None
    context_window: Optional[int] = None
    supported_tasks: List[str] = field(default_factory=list)
    pricing: Optional[Dict[str, Any]] = None

    def to_dict(self) -> Dict[str, Any]:
        base_dict = super().to_dict()
        base_dict.update({
            "provider": self.provider,
            "model_name": self.model_name,
            "capabilities": self.capabilities,
            "max_tokens": self.max_tokens,
            "context_window": self.context_window,
            "supported_tasks": self.supported_tasks,
            "pricing": self.pricing
        })
        return base_dict


@dataclass
class APIService(APIResource):
    """API service resource"""

    service_type: str = ""
    endpoints: List[str] = field(default_factory=list)
    dependencies: List[str] = field(default_factory=list)
    health_check_url: Optional[str] = None
    config: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        base_dict = super().to_dict()
        base_dict.update({
            "service_type": self.service_type,
            "endpoints": self.endpoints,
            "dependencies": self.dependencies,
            "health_check_url": self.health_check_url,
            "config": self.config
        })
        return base_dict


@dataclass
class APIPlugin(APIResource):
    """API plugin resource"""

    plugin_type: str = ""
    author: str = ""
    version: str = ""
    entry_point: str = ""
    hooks: List[str] = field(default_factory=list)
    settings: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        base_dict = super().to_dict()
        base_dict.update({
            "plugin_type": self.plugin_type,
            "author": self.author,
            "version": self.version,
            "entry_point": self.entry_point,
            "hooks": self.hooks,
            "settings": self.settings
        })
        return base_dict


class APIRegistry:
    """Central registry for API resources"""

    def __init__(self):
        self._resources: Dict[str, APIResource] = {}
        self._resources_by_type: Dict[APIResourceType, Dict[str, APIResource]] = {
            resource_type: {} for resource_type in APIResourceType
        }
        self._tags_index: Dict[str, set] = {}
        logger.info("API Registry initialized")

    def register(self, resource: APIResource) -> None:
        """Register an API resource"""
        if resource.id in self._resources:
            logger.warning(f"Resource {resource.id} already registered, updating")
            self.unregister(resource.id)

        self._resources[resource.id] = resource
        self._resources_by_type[resource.type][resource.id] = resource

        # Update tags index
        for tag in resource.tags:
            if tag not in self._tags_index:
                self._tags_index[tag] = set()
            self._tags_index[tag].add(resource.id)

        logger.info(f"Registered {resource.type.value}: {resource.id}")

    def unregister(self, resource_id: str) -> bool:
        """Unregister an API resource"""
        if resource_id not in self._resources:
            return False

        resource = self._resources[resource_id]

        # Remove from type index
        if resource_id in self._resources_by_type[resource.type]:
            del self._resources_by_type[resource.type][resource_id]

        # Remove from tags index
        for tag in resource.tags:
            if tag in self._tags_index and resource_id in self._tags_index[tag]:
                self._tags_index[tag].remove(resource_id)
                if not self._tags_index[tag]:
                    del self._tags_index[tag]

        # Remove from main registry
        del self._resources[resource_id]

        logger.info(f"Unregistered {resource.type.value}: {resource_id}")
        return True

    def get(self, resource_id: str) -> Optional[APIResource]:
        """Get a resource by ID"""
        return self._resources.get(resource_id)

    def list(
        self,
        resource_type: Optional[APIResourceType] = None,
        status: Optional[APIResourceStatus] = None,
        tags: Optional[List[str]] = None,
        version: Optional[str] = None
    ) -> List[APIResource]:
        """List resources with optional filtering"""
        resources = list(self._resources.values())

        if resource_type:
            resources = [r for r in resources if r.type == resource_type]

        if status:
            resources = [r for r in resources if r.status == status]

        if tags:
            tag_sets = [self._tags_index.get(tag, set()) for tag in tags]
            if tag_sets:
                common_ids = set.intersection(*tag_sets)
                resources = [r for r in resources if r.id in common_ids]

        if version:
            resources = [r for r in resources if r.version == version]

        return resources

    def get_by_type(self, resource_type: APIResourceType) -> Dict[str, APIResource]:
        """Get all resources of a specific type"""
        return dict(self._resources_by_type[resource_type])

    def search(self, query: str) -> List[APIResource]:
        """Search resources by name or description"""
        query_lower = query.lower()
        return [
            resource for resource in self._resources.values()
            if query_lower in resource.name.lower() or
               (resource.description and query_lower in resource.description.lower())
        ]

    def get_endpoints_for_path(self, path: str) -> List[APIEndpoint]:
        """Get endpoints that match a path"""
        endpoints = self.get_by_type(APIResourceType.ENDPOINT)
        return [
            endpoint for endpoint in endpoints.values()
            if isinstance(endpoint, APIEndpoint) and endpoint.path == path
        ]

    def get_models_by_capability(self, capability: str) -> List[AIModel]:
        """Get AI models that support a specific capability"""
        models = self.get_by_type(APIResourceType.MODEL)
        return [
            model for model in models.values()
            if isinstance(model, AIModel) and capability in model.capabilities
        ]

    def get_services_by_type(self, service_type: str) -> List[APIService]:
        """Get services of a specific type"""
        services = self.get_by_type(APIResourceType.SERVICE)
        return [
            service for service in services.values()
            if isinstance(service, APIService) and service.service_type == service_type
        ]

    def update_status(self, resource_id: str, status: APIResourceStatus) -> bool:
        """Update the status of a resource"""
        resource = self.get(resource_id)
        if not resource:
            return False

        resource.status = status
        resource.updated_at = datetime.now(timezone.utc)
        logger.info(f"Updated status of {resource_id} to {status.value}")
        return True

    def get_stats(self) -> Dict[str, Any]:
        """Get registry statistics"""
        stats = {
            "total_resources": len(self._resources),
            "resources_by_type": {},
            "resources_by_status": {},
            "total_tags": len(self._tags_index)
        }

        # Count by type
        for resource_type in APIResourceType:
            count = len(self._resources_by_type[resource_type])
            stats["resources_by_type"][resource_type.value] = count

        # Count by status
        status_counts = {}
        for resource in self._resources.values():
            status = resource.status.value
            status_counts[status] = status_counts.get(status, 0) + 1
        stats["resources_by_status"] = status_counts

        return stats

    def export(self) -> Dict[str, Any]:
        """Export the entire registry"""
        return {
            "resources": [resource.to_dict() for resource in self._resources.values()],
            "stats": self.get_stats(),
            "exported_at": datetime.now(timezone.utc).isoformat()
        }


# Global registry instance
api_registry = APIRegistry()


# Convenience functions
def register_endpoint(
    id: str,
    name: str,
    path: str,
    methods: List[str],
    handler: Callable,
    **kwargs
) -> None:
    """Register an API endpoint"""
    endpoint = APIEndpoint(
        id=id,
        name=name,
        type=APIResourceType.ENDPOINT,
        path=path,
        methods=methods,
        handler=handler,
        **kwargs
    )
    api_registry.register(endpoint)


def register_model(
    id: str,
    name: str,
    provider: str,
    model_name: str,
    **kwargs
) -> None:
    """Register an AI model"""
    model = AIModel(
        id=id,
        name=name,
        type=APIResourceType.MODEL,
        provider=provider,
        model_name=model_name,
        **kwargs
    )
    api_registry.register(model)


def register_service(
    id: str,
    name: str,
    service_type: str,
    **kwargs
) -> None:
    """Register an API service"""
    service = APIService(
        id=id,
        name=name,
        type=APIResourceType.SERVICE,
        service_type=service_type,
        **kwargs
    )
    api_registry.register(service)


def register_plugin(
    id: str,
    name: str,
    plugin_type: str,
    author: str,
    version: str,
    entry_point: str,
    **kwargs
) -> None:
    """Register a plugin"""
    plugin = APIPlugin(
        id=id,
        name=name,
        type=APIResourceType.PLUGIN,
        plugin_type=plugin_type,
        author=author,
        version=version,
        entry_point=entry_point,
        **kwargs
    )
    api_registry.register(plugin)