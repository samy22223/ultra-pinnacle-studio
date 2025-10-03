"""
Component Lifecycle Management

This module provides comprehensive lifecycle management for AI components,
including deployment, scaling, versioning, rollback, and retirement capabilities.
"""

from typing import Dict, List, Any, Optional, Callable
from dataclasses import dataclass, field
from datetime import datetime, timezone, timedelta
from enum import Enum
import asyncio
import logging
import threading
import time
import json
import os

from .core import AutoHealingAIEngineer, AIComponent, ComponentType

logger = logging.getLogger("ultra_pinnacle")


class LifecycleStage(Enum):
    """Stages in component lifecycle"""
    DEVELOPMENT = "development"
    TESTING = "testing"
    STAGING = "staging"
    PRODUCTION = "production"
    DEPRECATED = "deprecated"
    RETIRED = "retired"


class ScalingStrategy(Enum):
    """Strategies for scaling components"""
    HORIZONTAL = "horizontal"  # Add more instances
    VERTICAL = "vertical"     # Increase resources per instance
    AUTO = "auto"            # Automatic scaling based on load
    MANUAL = "manual"        # Manual scaling


@dataclass
class ComponentVersion:
    """Represents a version of a component"""
    version_id: str
    component_id: str
    version_number: str
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    deployed_at: Optional[datetime] = None
    retired_at: Optional[datetime] = None
    status: str = "created"
    changelog: List[str] = field(default_factory=list)
    compatibility: Dict[str, Any] = field(default_factory=dict)
    performance_baseline: Dict[str, Any] = field(default_factory=dict)
    rollback_available: bool = True


@dataclass
class Deployment:
    """Represents a component deployment"""
    deployment_id: str
    component_id: str
    version_id: str
    stage: LifecycleStage
    instances: int = 1
    resources_allocated: Dict[str, Any] = field(default_factory=dict)
    deployed_at: Optional[datetime] = None
    status: str = "pending"
    health_checks: List[Dict[str, Any]] = field(default_factory=list)
    scaling_config: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ScalingEvent:
    """Represents a scaling event"""
    event_id: str
    component_id: str
    strategy: ScalingStrategy
    action: str  # "scale_up", "scale_down"
    instances_before: int
    instances_after: int
    triggered_by: str  # "auto", "manual", "scheduled"
    triggered_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    reason: str = ""
    performance_impact: Dict[str, Any] = field(default_factory=dict)


class ComponentLifecycleManager:
    """
    Manages the complete lifecycle of AI components.

    Handles deployment, scaling, versioning, monitoring, and retirement
    of AI components throughout their lifecycle.
    """

    def __init__(self, system: AutoHealingAIEngineer):
        self.system = system
        self.config = system.config.get("lifecycle", {})

        # Lifecycle state
        self.versions: Dict[str, ComponentVersion] = {}
        self.deployments: Dict[str, Deployment] = {}
        self.scaling_events: Dict[str, ScalingEvent] = {}
        self.retirement_schedule: Dict[str, datetime] = {}

        # Lifecycle configuration
        self.auto_scaling_enabled = self.config.get("auto_scaling", True)
        self.version_retention_days = self.config.get("version_retention_days", 90)
        self.max_instances_per_component = self.config.get("max_instances_per_component", 10)
        self.scaling_check_interval = self.config.get("scaling_check_interval", 60)  # seconds

        # Scaling thresholds
        self.scaling_thresholds = {
            "cpu_high": self.config.get("cpu_high_threshold", 80),
            "cpu_low": self.config.get("cpu_low_threshold", 20),
            "memory_high": self.config.get("memory_high_threshold", 85),
            "memory_low": self.config.get("memory_low_threshold", 30),
            "response_time_high": self.config.get("response_time_high_threshold", 2.0),  # seconds
            "throughput_high": self.config.get("throughput_high_threshold", 1000),  # requests/sec
        }

        # Background tasks
        self.running = False
        self.scaling_thread: Optional[threading.Thread] = None
        self.cleanup_thread: Optional[threading.Thread] = None

        logger.info("Component Lifecycle Manager initialized")

    def start(self):
        """Start the lifecycle management system"""
        if self.running:
            return

        self.running = True

        # Start background threads
        self.scaling_thread = threading.Thread(target=self._scaling_loop, daemon=True)
        self.scaling_thread.start()

        self.cleanup_thread = threading.Thread(target=self._cleanup_loop, daemon=True)
        self.cleanup_thread.start()

        logger.info("Component Lifecycle Manager started")

    def stop(self):
        """Stop the lifecycle management system"""
        if not self.running:
            return

        self.running = False

        # Wait for threads to finish
        if self.scaling_thread:
            self.scaling_thread.join(timeout=5)
        if self.cleanup_thread:
            self.cleanup_thread.join(timeout=5)

        logger.info("Component Lifecycle Manager stopped")

    def deploy_component(
        self,
        component_id: str,
        version_number: str,
        stage: LifecycleStage = LifecycleStage.PRODUCTION,
        instances: int = 1,
        resources: Optional[Dict[str, Any]] = None
    ) -> str:
        """Deploy a component to a specific stage"""
        component = self.system.components.get(component_id)
        if not component:
            raise ValueError(f"Component {component_id} not found")

        # Create version if it doesn't exist
        version_id = f"{component_id}_v{version_number}"
        if version_id not in self.versions:
            version = ComponentVersion(
                version_id=version_id,
                component_id=component_id,
                version_number=version_number,
                changelog=[f"Initial deployment to {stage.value}"]
            )
            self.versions[version_id] = version
        else:
            version = self.versions[version_id]

        # Create deployment
        deployment_id = f"deploy_{component_id}_{stage.value}_{int(time.time())}"

        deployment = Deployment(
            deployment_id=deployment_id,
            component_id=component_id,
            version_id=version_id,
            stage=stage,
            instances=instances,
            resources_allocated=resources or self._calculate_default_resources(component),
            scaling_config=self._get_default_scaling_config(component)
        )

        self.deployments[deployment_id] = deployment

        # Execute deployment
        self._execute_deployment(deployment)

        logger.info(f"Deployed component {component_id} version {version_number} to {stage.value}")
        return deployment_id

    def _execute_deployment(self, deployment: Deployment):
        """Execute a component deployment"""
        try:
            # Simulate deployment process
            deployment.status = "deploying"
            time.sleep(2)  # Simulate deployment time

            # Update version status
            version = self.versions.get(deployment.version_id)
            if version:
                version.deployed_at = datetime.now(timezone.utc)
                version.status = "deployed"

            # Update deployment status
            deployment.deployed_at = datetime.now(timezone.utc)
            deployment.status = "active"

            # Update component stage
            component = self.system.components.get(deployment.component_id)
            if component:
                component.status = f"deployed_{deployment.stage.value}"

            logger.info(f"Successfully deployed {deployment.deployment_id}")

        except Exception as e:
            logger.error(f"Failed to deploy {deployment.deployment_id}: {e}")
            deployment.status = "failed"

    def _calculate_default_resources(self, component: AIComponent) -> Dict[str, Any]:
        """Calculate default resource allocation for a component"""
        base_resources = {
            "cpu_cores": 1,
            "memory_gb": 2,
            "disk_gb": 10,
            "network_bandwidth_mbps": 100
        }

        # Adjust based on component type
        if component.type == ComponentType.MODEL:
            base_resources["memory_gb"] = 4
            base_resources["disk_gb"] = 20
        elif component.type == ComponentType.SERVICE:
            base_resources["cpu_cores"] = 2
            base_resources["network_bandwidth_mbps"] = 500

        return base_resources

    def _get_default_scaling_config(self, component: AIComponent) -> Dict[str, Any]:
        """Get default scaling configuration for a component"""
        return {
            "strategy": ScalingStrategy.AUTO.value,
            "min_instances": 1,
            "max_instances": min(5, self.max_instances_per_component),
            "scale_up_threshold": 75,  # percent
            "scale_down_threshold": 25,  # percent
            "cooldown_period": 300  # seconds
        }

    def scale_component(
        self,
        component_id: str,
        instances: int,
        strategy: ScalingStrategy = ScalingStrategy.AUTO,
        reason: str = ""
    ) -> bool:
        """Scale a component to specified number of instances"""
        component = self.system.components.get(component_id)
        if not component:
            return False

        # Find active deployment
        active_deployment = None
        for deployment in self.deployments.values():
            if (deployment.component_id == component_id and
                deployment.status == "active" and
                deployment.stage == LifecycleStage.PRODUCTION):
                active_deployment = deployment
                break

        if not active_deployment:
            logger.warning(f"No active deployment found for component {component_id}")
            return False

        instances_before = active_deployment.instances

        # Validate scaling limits
        if instances < 1 or instances > self.max_instances_per_component:
            logger.error(f"Invalid instance count {instances} for component {component_id}")
            return False

        try:
            # Execute scaling
            self._execute_scaling(active_deployment, instances)

            # Record scaling event
            event = ScalingEvent(
                event_id=f"scale_{component_id}_{int(time.time())}",
                component_id=component_id,
                strategy=strategy,
                action="scale_up" if instances > instances_before else "scale_down",
                instances_before=instances_before,
                instances_after=instances,
                triggered_by="manual",
                reason=reason
            )

            self.scaling_events[event.event_id] = event

            logger.info(f"Scaled component {component_id} from {instances_before} to {instances} instances")
            return True

        except Exception as e:
            logger.error(f"Failed to scale component {component_id}: {e}")
            return False

    def _execute_scaling(self, deployment: Deployment, target_instances: int):
        """Execute scaling operation"""
        # Simulate scaling time
        time.sleep(1)

        deployment.instances = target_instances

        # Update resource allocation proportionally
        for resource, amount in deployment.resources_allocated.items():
            if isinstance(amount, (int, float)):
                # Scale resources based on instance count
                deployment.resources_allocated[resource] = amount * target_instances

    def _scaling_loop(self):
        """Background loop for automatic scaling"""
        while self.running:
            try:
                if self.auto_scaling_enabled:
                    self._check_auto_scaling()

                time.sleep(self.scaling_check_interval)

            except Exception as e:
                logger.error(f"Error in scaling loop: {e}")
                time.sleep(10)

    def _check_auto_scaling(self):
        """Check and execute automatic scaling decisions"""
        for component_id, component in self.system.components.items():
            if component.status not in ["healthy", "deployed_production"]:
                continue

            # Find active deployment
            active_deployment = None
            for deployment in self.deployments.values():
                if (deployment.component_id == component_id and
                    deployment.status == "active" and
                    deployment.stage == LifecycleStage.PRODUCTION):
                    active_deployment = deployment
                    break

            if not active_deployment:
                continue

            # Check scaling conditions
            scaling_decision = self._analyze_scaling_needs(component, active_deployment)

            if scaling_decision:
                action, target_instances, reason = scaling_decision
                self.scale_component(
                    component_id,
                    target_instances,
                    ScalingStrategy.AUTO,
                    reason
                )

    def _analyze_scaling_needs(self, component: AIComponent, deployment: Deployment) -> Optional[tuple]:
        """Analyze if a component needs scaling"""
        metrics = component.performance_metrics

        if not metrics:
            return None

        current_instances = deployment.instances
        max_instances = deployment.scaling_config.get("max_instances", 5)

        # Check CPU usage
        cpu_usage = metrics.get("cpu_usage", 0)
        if cpu_usage > self.scaling_thresholds["cpu_high"] and current_instances < max_instances:
            return ("scale_up", min(current_instances + 1, max_instances), f"High CPU usage: {cpu_usage}%")

        # Check memory usage
        memory_usage = metrics.get("memory_usage", 0)
        if memory_usage > self.scaling_thresholds["memory_high"] and current_instances < max_instances:
            return ("scale_up", min(current_instances + 1, max_instances), f"High memory usage: {memory_usage}%")

        # Check response time
        response_time = metrics.get("response_time", 0)
        if response_time > self.scaling_thresholds["response_time_high"] and current_instances < max_instances:
            return ("scale_up", min(current_instances + 1, max_instances), f"Slow response time: {response_time}s")

        # Check for scale down conditions
        min_instances = deployment.scaling_config.get("min_instances", 1)
        scale_down_threshold = deployment.scaling_config.get("scale_down_threshold", 25)

        if (cpu_usage < self.scaling_thresholds["cpu_low"] and
            memory_usage < self.scaling_thresholds["memory_low"] and
            current_instances > min_instances):
            return ("scale_down", max(current_instances - 1, min_instances), f"Low resource usage: CPU {cpu_usage}%, Memory {memory_usage}%")

        return None

    def create_version(
        self,
        component_id: str,
        version_number: str,
        changelog: List[str],
        compatibility: Optional[Dict[str, Any]] = None
    ) -> str:
        """Create a new version of a component"""
        version_id = f"{component_id}_v{version_number}"

        if version_id in self.versions:
            raise ValueError(f"Version {version_number} already exists for component {component_id}")

        version = ComponentVersion(
            version_id=version_id,
            component_id=component_id,
            version_number=version_number,
            changelog=changelog,
            compatibility=compatibility or {}
        )

        self.versions[version_id] = version

        # Establish baseline performance for this version
        component = self.system.components.get(component_id)
        if component:
            version.performance_baseline = {
                "health_score": component.health_score,
                "metrics": component.performance_metrics.copy(),
                "created_at": datetime.now(timezone.utc).isoformat()
            }

        logger.info(f"Created version {version_number} for component {component_id}")
        return version_id

    def rollback_component(self, component_id: str, target_version: str) -> bool:
        """Rollback a component to a previous version"""
        component = self.system.components.get(component_id)
        if not component:
            return False

        version_id = f"{component_id}_v{target_version}"
        version = self.versions.get(version_id)

        if not version or not version.rollback_available:
            logger.error(f"Cannot rollback to version {target_version} for component {component_id}")
            return False

        try:
            # Find current deployment
            current_deployment = None
            for deployment in self.deployments.values():
                if (deployment.component_id == component_id and
                    deployment.status == "active"):
                    current_deployment = deployment
                    break

            if current_deployment:
                # Create rollback deployment
                rollback_deployment_id = self.deploy_component(
                    component_id,
                    target_version,
                    current_deployment.stage,
                    current_deployment.instances,
                    current_deployment.resources_allocated
                )

                # Mark old deployment as rolled back
                current_deployment.status = "rolled_back"

                logger.info(f"Successfully rolled back component {component_id} to version {target_version}")
                return True

        except Exception as e:
            logger.error(f"Failed to rollback component {component_id}: {e}")

        return False

    def retire_component(self, component_id: str, reason: str = "") -> bool:
        """Retire a component"""
        component = self.system.components.get(component_id)
        if not component:
            return False

        try:
            # Update component status
            component.status = "retired"

            # Mark all deployments as retired
            for deployment in self.deployments.values():
                if deployment.component_id == component_id:
                    deployment.status = "retired"

            # Mark versions as retired
            for version in self.versions.values():
                if version.component_id == component_id:
                    version.retired_at = datetime.now(timezone.utc)
                    version.status = "retired"

            # Schedule for cleanup
            self.retirement_schedule[component_id] = datetime.now(timezone.utc) + timedelta(days=30)

            logger.info(f"Retired component {component_id}: {reason}")
            return True

        except Exception as e:
            logger.error(f"Failed to retire component {component_id}: {e}")
            return False

    def _cleanup_loop(self):
        """Background loop for cleanup operations"""
        while self.running:
            try:
                self._cleanup_old_versions()
                self._cleanup_retired_components()

                time.sleep(3600)  # Run cleanup hourly

            except Exception as e:
                logger.error(f"Error in cleanup loop: {e}")
                time.sleep(60)

    def _cleanup_old_versions(self):
        """Clean up old versions beyond retention period"""
        cutoff_date = datetime.now(timezone.utc) - timedelta(days=self.version_retention_days)

        versions_to_remove = []
        for version_id, version in self.versions.items():
            if (version.created_at < cutoff_date and
                version.status in ["retired", "superseded"] and
                not self._version_has_active_deployments(version_id)):
                versions_to_remove.append(version_id)

        for version_id in versions_to_remove:
            del self.versions[version_id]
            logger.info(f"Cleaned up old version {version_id}")

    def _cleanup_retired_components(self):
        """Clean up retired components after grace period"""
        now = datetime.now(timezone.utc)

        components_to_cleanup = []
        for component_id, retirement_date in self.retirement_schedule.items():
            if now > retirement_date:
                components_to_cleanup.append(component_id)

        for component_id in components_to_cleanup:
            # Remove from system
            if component_id in self.system.components:
                del self.system.components[component_id]

            # Clean up related data
            self._cleanup_component_data(component_id)

            del self.retirement_schedule[component_id]
            logger.info(f"Cleaned up retired component {component_id}")

    def _cleanup_component_data(self, component_id: str):
        """Clean up all data related to a component"""
        # Remove deployments
        deployments_to_remove = [
            d_id for d_id, deployment in self.deployments.items()
            if deployment.component_id == component_id
        ]
        for d_id in deployments_to_remove:
            del self.deployments[d_id]

        # Remove versions
        versions_to_remove = [
            v_id for v_id, version in self.versions.items()
            if version.component_id == component_id
        ]
        for v_id in versions_to_remove:
            del self.versions[v_id]

        # Remove scaling events
        scaling_to_remove = [
            e_id for e_id, event in self.scaling_events.items()
            if event.component_id == component_id
        ]
        for e_id in scaling_to_remove:
            del self.scaling_events[e_id]

    def _version_has_active_deployments(self, version_id: str) -> bool:
        """Check if a version has any active deployments"""
        return any(
            deployment.version_id == version_id and deployment.status == "active"
            for deployment in self.deployments.values()
        )

    def get_component_deployments(self, component_id: str) -> List[Dict[str, Any]]:
        """Get all deployments for a component"""
        component_deployments = [
            deployment for deployment in self.deployments.values()
            if deployment.component_id == component_id
        ]

        return [{
            "deployment_id": d.deployment_id,
            "version_id": d.version_id,
            "stage": d.stage.value,
            "instances": d.instances,
            "status": d.status,
            "deployed_at": d.deployed_at.isoformat() if d.deployed_at else None,
            "resources_allocated": d.resources_allocated
        } for d in component_deployments]

    def get_component_versions(self, component_id: str) -> List[Dict[str, Any]]:
        """Get all versions for a component"""
        component_versions = [
            version for version in self.versions.values()
            if version.component_id == component_id
        ]

        return [{
            "version_id": v.version_id,
            "version_number": v.version_number,
            "status": v.status,
            "created_at": v.created_at.isoformat(),
            "deployed_at": v.deployed_at.isoformat() if v.deployed_at else None,
            "changelog": v.changelog
        } for v in component_versions]

    def get_scaling_history(self, component_id: str, hours: int = 24) -> List[Dict[str, Any]]:
        """Get scaling history for a component"""
        cutoff_time = datetime.now(timezone.utc) - timedelta(hours=hours)

        component_events = [
            event for event in self.scaling_events.values()
            if event.component_id == component_id and event.triggered_at > cutoff_time
        ]

        return [{
            "event_id": e.event_id,
            "strategy": e.strategy.value,
            "action": e.action,
            "instances_before": e.instances_before,
            "instances_after": e.instances_after,
            "triggered_by": e.triggered_by,
            "triggered_at": e.triggered_at.isoformat(),
            "reason": e.reason
        } for e in component_events]

    def get_lifecycle_stats(self) -> Dict[str, Any]:
        """Get lifecycle management statistics"""
        total_deployments = len(self.deployments)
        active_deployments = len([d for d in self.deployments.values() if d.status == "active"])
        total_versions = len(self.versions)
        retired_components = len(self.retirement_schedule)

        # Calculate deployment success rate
        successful_deployments = len([d for d in self.deployments.values() if d.status == "active"])
        deployment_success_rate = (successful_deployments / max(1, total_deployments)) * 100

        # Scaling statistics
        total_scaling_events = len(self.scaling_events)
        auto_scaling_events = len([e for e in self.scaling_events.values() if e.triggered_by == "auto"])

        return {
            "total_deployments": total_deployments,
            "active_deployments": active_deployments,
            "deployment_success_rate": deployment_success_rate,
            "total_versions": total_versions,
            "retired_components": retired_components,
            "total_scaling_events": total_scaling_events,
            "auto_scaling_events": auto_scaling_events,
            "auto_scaling_percentage": (auto_scaling_events / max(1, total_scaling_events)) * 100
        }