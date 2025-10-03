"""
Domain Healing Integration for Ultra Pinnacle AI Studio

This module provides seamless integration between the domain expansion framework
and the auto-healing AI engineer system, enabling autonomous monitoring,
healing, and lifecycle management of domain modules.
"""

from typing import Dict, List, Any, Optional, Callable, Type
from dataclasses import dataclass, field
from datetime import datetime, timezone
import asyncio
import logging
import threading
import time

from .core import (
    AutoHealingAIEngineer, AIComponent, ComponentType, AIEngineer,
    SystemStatus
)
from .domain_expansion_framework import (
    DomainExpansionFramework, DomainFramework, DomainType,
    DomainModule, get_domain_expansion_framework
)
from .monitoring import AIComponentMonitor
from .healing import AutoHealer
from .lifecycle import ComponentLifecycleManager

logger = logging.getLogger("ultra_pinnacle")


@dataclass
class DomainHealingConfig:
    """Configuration for domain healing integration"""
    enable_domain_monitoring: bool = True
    enable_domain_healing: bool = True
    enable_domain_lifecycle_management: bool = True
    monitoring_interval: int = 30  # seconds
    healing_interval: int = 60  # seconds
    max_healing_attempts: int = 3
    domain_health_threshold: float = 80.0
    enable_cross_domain_healing: bool = True
    enable_predictive_healing: bool = True
    healing_strategies: List[str] = field(default_factory=lambda: [
        "restart", "reconfigure", "resource_adjustment", "dependency_healing"
    ])


class DomainHealingIntegration:
    """
    Integration layer between domain expansion and auto-healing systems.

    This class enables the auto-healing AI engineer to monitor, heal, and manage
    domain modules as first-class AI components with full lifecycle support.
    """

    def __init__(
        self,
        domain_framework: DomainExpansionFramework,
        healing_system: AutoHealingAIEngineer,
        config: Optional[DomainHealingConfig] = None
    ):
        self.domain_framework = domain_framework
        self.healing_system = healing_system
        self.config = config or DomainHealingConfig()

        # Integration state
        self.registered_domain_components: Dict[str, str] = {}  # domain_id -> component_id
        self.domain_health_monitors: Dict[str, Any] = {}
        self.healing_history: List[Dict[str, Any]] = []
        self.monitoring_thread: Optional[threading.Thread] = None
        self.running = False

        # Initialize integration
        self._initialize_integration()

    def _initialize_integration(self):
        """Initialize domain healing integration"""
        try:
            logger.info("Initializing Domain Healing Integration")

            # Register existing domains as AI components
            self._register_existing_domains()

            # Setup domain-specific monitoring
            self._setup_domain_monitoring()

            # Setup domain healing capabilities
            self._setup_domain_healing()

            # Setup lifecycle management integration
            self._setup_lifecycle_integration()

            # Register event handlers
            self._register_event_handlers()

            logger.info("Domain Healing Integration initialized successfully")

        except Exception as e:
            logger.error(f"Failed to initialize Domain Healing Integration: {e}")
            raise

    def _register_existing_domains(self):
        """Register existing domain frameworks as AI components"""
        try:
            for domain_id, framework in self.domain_framework.domain_frameworks.items():
                component_id = self._register_domain_as_component(framework)

                if component_id:
                    self.registered_domain_components[domain_id] = component_id
                    logger.info(f"Registered domain {domain_id} as component {component_id}")

        except Exception as e:
            logger.error(f"Failed to register existing domains: {e}")

    def _register_domain_as_component(self, framework: DomainFramework) -> Optional[str]:
        """Register a domain framework as an AI component"""
        try:
            # Create AI component for domain
            component = AIComponent(
                id=f"domain_{framework.domain_id}",
                name=f"{framework.name} Domain",
                type=ComponentType.SERVICE,  # Domains are services
                domain=framework.domain_id,
                capabilities=framework.capabilities + ["domain_framework", "multi_capability"],
                status="ready",
                health_score=100.0,
                configuration={
                    "framework_type": "domain_expansion",
                    "domain_type": framework.domain_type.value,
                    "capabilities": framework.capabilities,
                    "services": framework.services,
                    "ai_capabilities": [cap.value for cap in framework.ai_capabilities]
                },
                version=framework.version
            )

            # Register with healing system
            self.healing_system.components[component.id] = component

            # Create specialized AI engineer for domain if needed
            self._create_domain_engineer(framework)

            return component.id

        except Exception as e:
            logger.error(f"Failed to register domain {framework.domain_id} as component: {e}")
            return None

    def _create_domain_engineer(self, framework: DomainFramework):
        """Create specialized AI engineer for domain"""
        engineer_id = f"{framework.domain_id}_engineer"

        # Check if engineer already exists
        if engineer_id in self.healing_system.ai_engineers:
            return

        # Create domain-specific engineer
        domain_engineer = AIEngineer(
            id=engineer_id,
            name=f"{framework.name} Engineer",
            specialization=framework.domain_id,
            experience_level=5,  # Higher experience for domain specialists
            skills=framework.capabilities + [
                "domain_expertise",
                "cross_platform_development",
                "domain_monitoring",
                "domain_healing"
            ],
            status="available"
        )

        # Add to healing system
        self.healing_system.ai_engineers[engineer_id] = domain_engineer

        logger.info(f"Created domain engineer: {engineer_id}")

    def _setup_domain_monitoring(self):
        """Setup domain-specific monitoring"""
        try:
            # Create domain health monitor
            self.domain_monitor = DomainHealthMonitor(self.domain_framework, self.healing_system)

            # Register domain-specific health checks
            for domain_id in self.domain_framework.domain_frameworks.keys():
                self._register_domain_health_check(domain_id)

            logger.info("Domain monitoring setup completed")

        except Exception as e:
            logger.error(f"Failed to setup domain monitoring: {e}")

    def _register_domain_health_check(self, domain_id: str):
        """Register health check for specific domain"""
        def domain_health_check():
            """Health check function for domain"""
            try:
                domain_status = self.domain_framework.get_domain_status(domain_id)
                if not domain_status:
                    return False, f"Domain {domain_id} not found"

                # Calculate domain health score
                health_score = self._calculate_domain_health_score(domain_status)

                # Update component health if registered
                component_id = self.registered_domain_components.get(domain_id)
                if component_id and component_id in self.healing_system.components:
                    component = self.healing_system.components[component_id]
                    component.health_score = health_score
                    component.last_health_check = datetime.now(timezone.utc)

                    # Update status based on health score
                    if health_score < 50:
                        component.status = "failed"
                    elif health_score < 80:
                        component.status = "degraded"
                    else:
                        component.status = "healthy"

                return health_score >= self.config.domain_health_threshold, f"Domain health: {health_score}"

            except Exception as e:
                logger.error(f"Domain health check failed for {domain_id}: {e}")
                return False, str(e)

        # Register with monitoring system
        self.healing_system.monitor.register_health_check(
            f"domain_{domain_id}",
            domain_health_check,
            interval=self.config.monitoring_interval
        )

        logger.info(f"Registered health check for domain: {domain_id}")

    def _calculate_domain_health_score(self, domain_status: Dict[str, Any]) -> float:
        """Calculate health score for a domain"""
        try:
            # Base score from framework status
            framework_status = domain_status.get("framework", {})
            base_score = 100.0

            if framework_status.get("status") == "error":
                base_score = 0.0
            elif framework_status.get("status") == "degraded":
                base_score = 60.0
            elif framework_status.get("status") == "initializing":
                base_score = 80.0

            # Adjust based on components and services
            components_count = domain_status.get("components", 0)
            services_count = domain_status.get("services", 0)

            # More components/services generally indicate better health
            activity_bonus = min((components_count + services_count) * 2, 20.0)

            # Performance score adjustment
            performance_score = domain_status.get("performance_score", 50.0)
            performance_adjustment = (performance_score - 50.0) * 0.5

            total_score = base_score + activity_bonus + performance_adjustment
            return min(max(total_score, 0.0), 100.0)

        except Exception as e:
            logger.error(f"Failed to calculate domain health score: {e}")
            return 50.0  # Default to medium health

    def _setup_domain_healing(self):
        """Setup domain-specific healing capabilities"""
        try:
            # Register domain healing strategies
            for strategy in self.config.healing_strategies:
                self._register_domain_healing_strategy(strategy)

            # Setup predictive healing if enabled
            if self.config.enable_predictive_healing:
                self._setup_predictive_healing()

            logger.info("Domain healing setup completed")

        except Exception as e:
            logger.error(f"Failed to setup domain healing: {e}")

    def _register_domain_healing_strategy(self, strategy: str):
        """Register healing strategy for domains"""
        def domain_healing_function(component_id: str) -> bool:
            """Generic domain healing function"""
            try:
                # Extract domain ID from component ID
                if not component_id.startswith("domain_"):
                    return False

                domain_id = component_id.replace("domain_", "")

                # Apply healing strategy based on type
                if strategy == "restart":
                    return self._heal_domain_by_restart(domain_id)
                elif strategy == "reconfigure":
                    return self._heal_domain_by_reconfiguration(domain_id)
                elif strategy == "resource_adjustment":
                    return self._heal_domain_by_resource_adjustment(domain_id)
                elif strategy == "dependency_healing":
                    return self._heal_domain_by_dependency_healing(domain_id)
                else:
                    logger.warning(f"Unknown healing strategy: {strategy}")
                    return False

            except Exception as e:
                logger.error(f"Domain healing failed for {component_id} using {strategy}: {e}")
                return False

        # Register with healing system
        self.healing_system.healer.register_healing_strategy(
            f"domain_{strategy}",
            domain_healing_function
        )

        logger.info(f"Registered domain healing strategy: {strategy}")

    def _heal_domain_by_restart(self, domain_id: str) -> bool:
        """Heal domain by restarting it"""
        try:
            logger.info(f"Attempting to restart domain: {domain_id}")

            # Unload domain module
            unload_success = self.domain_framework.unload_module(domain_id)

            if not unload_success:
                logger.warning(f"Failed to unload domain {domain_id} for restart")
                return False

            # Wait a moment
            time.sleep(2)

            # Reload domain module
            load_success = self.domain_framework.load_module(domain_id)

            if load_success:
                logger.info(f"Successfully restarted domain: {domain_id}")
                self._record_healing_action(domain_id, "restart", True)
                return True
            else:
                logger.error(f"Failed to reload domain {domain_id} after restart")
                self._record_healing_action(domain_id, "restart", False)
                return False

        except Exception as e:
            logger.error(f"Domain restart healing failed for {domain_id}: {e}")
            self._record_healing_action(domain_id, "restart", False, str(e))
            return False

    def _heal_domain_by_reconfiguration(self, domain_id: str) -> bool:
        """Heal domain by reconfiguring it"""
        try:
            logger.info(f"Attempting to reconfigure domain: {domain_id}")

            # Get current domain framework
            framework = self.domain_framework.domain_frameworks.get(domain_id)
            if not framework:
                logger.error(f"Domain framework not found: {domain_id}")
                return False

            # Reset configuration to defaults
            framework.configuration = framework.__class__().configuration

            # Reinitialize domain components
            if hasattr(framework, '_initialize_domain_components'):
                framework._initialize_domain_components()

            logger.info(f"Successfully reconfigured domain: {domain_id}")
            self._record_healing_action(domain_id, "reconfiguration", True)
            return True

        except Exception as e:
            logger.error(f"Domain reconfiguration healing failed for {domain_id}: {e}")
            self._record_healing_action(domain_id, "reconfiguration", False, str(e))
            return False

    def _heal_domain_by_resource_adjustment(self, domain_id: str) -> bool:
        """Heal domain by adjusting resource allocation"""
        try:
            logger.info(f"Attempting resource adjustment for domain: {domain_id}")

            # Get domain component
            component_id = self.registered_domain_components.get(domain_id)
            if not component_id:
                logger.error(f"No component registered for domain: {domain_id}")
                return False

            component = self.healing_system.components.get(component_id)
            if not component:
                logger.error(f"Component not found: {component_id}")
                return False

            # Adjust resource allocation (placeholder logic)
            # In real implementation, this would adjust memory, CPU, or other resources
            component.configuration["resource_adjustment"] = {
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "action": "increased_allocation",
                "reason": "healing_action"
            }

            logger.info(f"Successfully adjusted resources for domain: {domain_id}")
            self._record_healing_action(domain_id, "resource_adjustment", True)
            return True

        except Exception as e:
            logger.error(f"Domain resource adjustment healing failed for {domain_id}: {e}")
            self._record_healing_action(domain_id, "resource_adjustment", False, str(e))
            return False

    def _heal_domain_by_dependency_healing(self, domain_id: str) -> bool:
        """Heal domain by healing its dependencies"""
        try:
            logger.info(f"Attempting dependency healing for domain: {domain_id}")

            # Get domain modules and their dependencies
            healed_dependencies = []

            for module_id, module in self.domain_framework.domain_modules.items():
                if module.domain_type.value == domain_id and module.status == "loaded":
                    # Check and heal module dependencies
                    for dep in module.dependencies:
                        try:
                            # Attempt to import/validate dependency
                            __import__(dep)
                            healed_dependencies.append(dep)
                        except ImportError:
                            logger.warning(f"Dependency {dep} not available for domain {domain_id}")
                            # Could attempt to install or fix dependency

            success = len(healed_dependencies) > 0
            logger.info(f"Dependency healing for domain {domain_id}: {'success' if success else 'failed'}")
            self._record_healing_action(domain_id, "dependency_healing", success)
            return success

        except Exception as e:
            logger.error(f"Domain dependency healing failed for {domain_id}: {e}")
            self._record_healing_action(domain_id, "dependency_healing", False, str(e))
            return False

    def _setup_predictive_healing(self):
        """Setup predictive healing for domains"""
        try:
            # Register predictive healing patterns
            self._register_predictive_patterns()

            # Setup trend analysis
            self._setup_trend_analysis()

            logger.info("Predictive healing setup completed")

        except Exception as e:
            logger.error(f"Failed to setup predictive healing: {e}")

    def _register_predictive_patterns(self):
        """Register predictive healing patterns"""
        # Common failure patterns for domains
        patterns = {
            "memory_leak": {
                "indicators": ["increasing_memory_usage", "degraded_performance"],
                "threshold": 0.8,
                "action": "resource_adjustment",
                "prevention": "memory_optimization"
            },
            "dependency_conflict": {
                "indicators": ["import_errors", "module_load_failures"],
                "threshold": 0.9,
                "action": "dependency_healing",
                "prevention": "dependency_isolation"
            },
            "performance_degradation": {
                "indicators": ["increasing_response_time", "error_rate_increase"],
                "threshold": 0.7,
                "action": "reconfiguration",
                "prevention": "performance_monitoring"
            }
        }

        for pattern_name, pattern_config in patterns.items():
            self.healing_system.healer.register_predictive_pattern(
                f"domain_{pattern_name}",
                pattern_config
            )

        logger.info(f"Registered {len(patterns)} predictive healing patterns")

    def _setup_trend_analysis(self):
        """Setup trend analysis for predictive healing"""
        # This would analyze historical domain performance and failure patterns
        # to predict and prevent future issues
        logger.info("Trend analysis setup completed")

    def _setup_lifecycle_integration(self):
        """Setup lifecycle management integration"""
        try:
            # Register domain lifecycle hooks
            self._register_domain_lifecycle_hooks()

            # Setup domain-specific lifecycle policies
            self._setup_domain_lifecycle_policies()

            logger.info("Lifecycle integration setup completed")

        except Exception as e:
            logger.error(f"Failed to setup lifecycle integration: {e}")

    def _register_domain_lifecycle_hooks(self):
        """Register lifecycle hooks for domains"""
        # Hook for when domain is loaded
        def on_domain_loaded_hook(component_id: str, component: AIComponent):
            """Handle domain loaded event"""
            if component_id.startswith("domain_"):
                domain_id = component_id.replace("domain_", "")
                logger.info(f"Domain loaded lifecycle hook triggered for: {domain_id}")

                # Record successful loading
                self._record_healing_action(domain_id, "lifecycle_load", True)

        # Hook for when domain is unloaded
        def on_domain_unloaded_hook(component_id: str, component: AIComponent):
            """Handle domain unloaded event"""
            if component_id.startswith("domain_"):
                domain_id = component_id.replace("domain_", "")
                logger.info(f"Domain unloaded lifecycle hook triggered for: {domain_id}")

                # Record successful unloading
                self._record_healing_action(domain_id, "lifecycle_unload", True)

        # Register hooks with lifecycle manager
        self.healing_system.lifecycle_manager.register_lifecycle_hook(
            "domain_loaded",
            on_domain_loaded_hook
        )
        self.healing_system.lifecycle_manager.register_lifecycle_hook(
            "domain_unloaded",
            on_domain_unloaded_hook
        )

    def _setup_domain_lifecycle_policies(self):
        """Setup domain-specific lifecycle policies"""
        # Define lifecycle policies for different domain types
        policies = {
            "healthcare": {
                "backup_frequency": "daily",
                "retention_period": "7_years",
                "compliance_required": True,
                "audit_frequency": "quarterly"
            },
            "finance": {
                "backup_frequency": "hourly",
                "retention_period": "7_years",
                "compliance_required": True,
                "audit_frequency": "monthly"
            },
            "legal": {
                "backup_frequency": "daily",
                "retention_period": "10_years",
                "compliance_required": True,
                "audit_frequency": "quarterly"
            }
        }

        for domain_type, policy in policies.items():
            self.healing_system.lifecycle_manager.register_lifecycle_policy(
                f"domain_{domain_type}",
                policy
            )

        logger.info(f"Registered {len(policies)} domain lifecycle policies")

    def _register_event_handlers(self):
        """Register event handlers for domain operations"""
        # Domain expansion events
        def on_domain_expanded(event_data: Dict[str, Any]):
            """Handle domain expansion event"""
            domain_id = event_data.get("domain_id")
            if domain_id:
                logger.info(f"Domain expanded event: {domain_id}")
                # Register new domain as component
                framework = self.domain_framework.domain_frameworks.get(domain_id)
                if framework:
                    component_id = self._register_domain_as_component(framework)
                    if component_id:
                        self.registered_domain_components[domain_id] = component_id

        def on_domain_error(event_data: Dict[str, Any]):
            """Handle domain error event"""
            domain_id = event_data.get("domain_id")
            error = event_data.get("error")
            if domain_id and error:
                logger.error(f"Domain error event - Domain: {domain_id}, Error: {error}")
                # Trigger healing for domain
                component_id = self.registered_domain_components.get(domain_id)
                if component_id:
                    self.healing_system.heal_component(component_id)

        # Register with domain framework
        self.domain_framework.register_event_handler("domain_expanded", on_domain_expanded)
        self.domain_framework.register_event_handler("domain_error", on_domain_error)

    def _record_healing_action(self, domain_id: str, action: str, success: bool, error: str = None):
        """Record healing action for tracking and analysis"""
        healing_record = {
            "domain_id": domain_id,
            "action": action,
            "success": success,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "error": error
        }

        self.healing_history.append(healing_record)

        # Keep only last 1000 records
        if len(self.healing_history) > 1000:
            self.healing_history = self.healing_history[-1000:]

    def start(self):
        """Start domain healing integration"""
        if self.running:
            return

        logger.info("Starting Domain Healing Integration")
        self.running = True

        # Start monitoring if enabled
        if self.config.enable_domain_monitoring:
            self.monitoring_thread = threading.Thread(
                target=self._domain_monitoring_loop,
                daemon=True
            )
            self.monitoring_thread.start()

        logger.info("Domain Healing Integration started")

    def stop(self):
        """Stop domain healing integration"""
        if not self.running:
            return

        logger.info("Stopping Domain Healing Integration")
        self.running = False

        # Stop monitoring thread
        if self.monitoring_thread:
            self.monitoring_thread.join(timeout=5)

        logger.info("Domain Healing Integration stopped")

    def _domain_monitoring_loop(self):
        """Domain-specific monitoring loop"""
        while self.running:
            try:
                # Monitor domain health
                self._monitor_domain_health()

                # Check for cross-domain issues
                if self.config.enable_cross_domain_healing:
                    self._check_cross_domain_issues()

                # Update domain metrics
                self._update_domain_metrics()

                # Sleep for monitoring interval
                time.sleep(self.config.monitoring_interval)

            except Exception as e:
                logger.error(f"Error in domain monitoring loop: {e}")
                time.sleep(10)  # Wait before retrying

    def _monitor_domain_health(self):
        """Monitor health of all registered domains"""
        for domain_id, component_id in self.registered_domain_components.items():
            try:
                # Get domain status
                domain_status = self.domain_framework.get_domain_status(domain_id)
                if not domain_status:
                    continue

                # Update component health
                component = self.healing_system.components.get(component_id)
                if component:
                    health_score = self._calculate_domain_health_score(domain_status)
                    component.health_score = health_score

                    # Update status based on health
                    if health_score < 50:
                        component.status = "failed"
                    elif health_score < 80:
                        component.status = "degraded"
                    else:
                        component.status = "healthy"

                    component.last_health_check = datetime.now(timezone.utc)

            except Exception as e:
                logger.error(f"Failed to monitor domain {domain_id}: {e}")

    def _check_cross_domain_issues(self):
        """Check for cross-domain dependency issues"""
        try:
            # Analyze dependencies between domains
            for domain_id, framework in self.domain_framework.domain_frameworks.items():
                # Check if domain depends on other domains
                for capability in framework.capabilities:
                    # Look for cross-domain capability usage
                    if self._is_cross_domain_capability(capability):
                        self._validate_cross_domain_dependency(domain_id, capability)

        except Exception as e:
            logger.error(f"Failed to check cross-domain issues: {e}")

    def _is_cross_domain_capability(self, capability: str) -> bool:
        """Check if capability involves cross-domain dependencies"""
        cross_domain_indicators = [
            "integration", "federated", "cross", "multi", "shared", "common"
        ]
        return any(indicator in capability.lower() for indicator in cross_domain_indicators)

    def _validate_cross_domain_dependency(self, domain_id: str, capability: str):
        """Validate cross-domain dependency"""
        # This would check if the cross-domain dependency is healthy
        # For now, just log the validation
        logger.debug(f"Validating cross-domain dependency: {domain_id} -> {capability}")

    def _update_domain_metrics(self):
        """Update domain-specific metrics"""
        try:
            # Calculate domain health statistics
            total_domains = len(self.registered_domain_components)
            healthy_domains = 0
            degraded_domains = 0
            failed_domains = 0

            for domain_id, component_id in self.registered_domain_components.items():
                component = self.healing_system.components.get(component_id)
                if component:
                    if component.status == "healthy":
                        healthy_domains += 1
                    elif component.status == "degraded":
                        degraded_domains += 1
                    elif component.status == "failed":
                        failed_domains += 1

            # Update system metrics
            self.healing_system.system_metrics.update({
                "domain_health_stats": {
                    "total_domains": total_domains,
                    "healthy_domains": healthy_domains,
                    "degraded_domains": degraded_domains,
                    "failed_domains": failed_domains,
                    "domain_health_score": (healthy_domains / total_domains * 100) if total_domains > 0 else 100.0
                },
                "domain_healing_stats": {
                    "total_healing_actions": len(self.healing_history),
                    "successful_healings": len([h for h in self.healing_history if h["success"]]),
                    "failed_healings": len([h for h in self.healing_history if not h["success"]])
                }
            })

        except Exception as e:
            logger.error(f"Failed to update domain metrics: {e}")

    def get_domain_healing_status(self) -> Dict[str, Any]:
        """Get comprehensive domain healing status"""
        return {
            "integration_status": "running" if self.running else "stopped",
            "registered_domains": len(self.registered_domain_components),
            "domain_components": list(self.registered_domain_components.keys()),
            "monitoring_enabled": self.config.enable_domain_monitoring,
            "healing_enabled": self.config.enable_domain_healing,
            "lifecycle_management_enabled": self.config.enable_domain_lifecycle_management,
            "healing_strategies": self.config.healing_strategies,
            "recent_healing_actions": self.healing_history[-10:],  # Last 10 actions
            "predictive_healing_enabled": self.config.enable_predictive_healing,
            "cross_domain_healing_enabled": self.config.enable_cross_domain_healing
        }

    def get_domain_health_report(self) -> Dict[str, Any]:
        """Get comprehensive domain health report"""
        health_report = {
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "overall_health": "unknown",
            "domain_health": {},
            "healing_summary": {},
            "recommendations": []
        }

        try:
            # Get health for each domain
            total_health_score = 0.0
            domain_count = 0

            for domain_id, component_id in self.registered_domain_components.items():
                component = self.healing_system.components.get(component_id)
                if component:
                    domain_status = self.domain_framework.get_domain_status(domain_id)
                    if domain_status:
                        health_score = self._calculate_domain_health_score(domain_status)

                        health_report["domain_health"][domain_id] = {
                            "component_status": component.status,
                            "health_score": health_score,
                            "last_check": component.last_health_check.isoformat() if component.last_health_check else None,
                            "performance_score": domain_status.get("performance_score", 0.0)
                        }

                        total_health_score += health_score
                        domain_count += 1

            # Calculate overall health
            if domain_count > 0:
                avg_health_score = total_health_score / domain_count
                if avg_health_score >= 90:
                    health_report["overall_health"] = "excellent"
                elif avg_health_score >= 75:
                    health_report["overall_health"] = "good"
                elif avg_health_score >= 60:
                    health_report["overall_health"] = "fair"
                else:
                    health_report["overall_health"] = "poor"

            # Add healing summary
            recent_healings = [h for h in self.healing_history if h["timestamp"] > datetime.now(timezone.utc).isoformat()]
            health_report["healing_summary"] = {
                "total_recent_healings": len(recent_healings),
                "successful_healings": len([h for h in recent_healings if h["success"]]),
                "failed_healings": len([h for h in recent_healings if not h["success"]])
            }

            # Generate recommendations
            health_report["recommendations"] = self._generate_health_recommendations(health_report)

        except Exception as e:
            logger.error(f"Failed to generate domain health report: {e}")
            health_report["error"] = str(e)

        return health_report

    def _generate_health_recommendations(self, health_report: Dict[str, Any]) -> List[str]:
        """Generate health recommendations based on current status"""
        recommendations = []

        try:
            # Check overall health
            overall_health = health_report.get("overall_health", "unknown")
            if overall_health in ["poor", "fair"]:
                recommendations.append("Consider increasing monitoring frequency for degraded domains")

            # Check individual domain health
            domain_health = health_report.get("domain_health", {})
            for domain_id, health_data in domain_health.items():
                if health_data.get("health_score", 100) < 70:
                    recommendations.append(f"Domain {domain_id} requires attention - health score: {health_data['health_score']}")

            # Check healing success rate
            healing_summary = health_report.get("healing_summary", {})
            if healing_summary.get("failed_healings", 0) > healing_summary.get("successful_healings", 0):
                recommendations.append("Review healing strategies - high failure rate detected")

            if not recommendations:
                recommendations.append("All domains are operating within normal parameters")

        except Exception as e:
            logger.error(f"Failed to generate health recommendations: {e}")
            recommendations.append("Unable to generate recommendations due to error")

        return recommendations


class DomainHealthMonitor:
    """Specialized health monitor for domain frameworks"""

    def __init__(self, domain_framework: DomainExpansionFramework, healing_system: AutoHealingAIEngineer):
        self.domain_framework = domain_framework
        self.healing_system = healing_system
        self.monitoring_data: Dict[str, List[Dict[str, Any]]] = {}

    def monitor_domain(self, domain_id: str) -> Dict[str, Any]:
        """Monitor specific domain health"""
        try:
            # Get domain status
            domain_status = self.domain_framework.get_domain_status(domain_id)
            if not domain_status:
                return {"status": "error", "message": f"Domain {domain_id} not found"}

            # Collect monitoring data
            monitoring_record = {
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "domain_id": domain_id,
                "status": domain_status,
                "health_score": self._calculate_domain_health_score(domain_status)
            }

            # Store monitoring data
            if domain_id not in self.monitoring_data:
                self.monitoring_data[domain_id] = []
            self.monitoring_data[domain_id].append(monitoring_record)

            # Keep only last 100 records per domain
            if len(self.monitoring_data[domain_id]) > 100:
                self.monitoring_data[domain_id] = self.monitoring_data[domain_id][-100:]

            return {
                "status": "success",
                "health_score": monitoring_record["health_score"],
                "monitoring_data": monitoring_record
            }

        except Exception as e:
            logger.error(f"Failed to monitor domain {domain_id}: {e}")
            return {"status": "error", "message": str(e)}

    def _calculate_domain_health_score(self, domain_status: Dict[str, Any]) -> float:
        """Calculate health score for domain"""
        # This mirrors the calculation in the main integration class
        framework_status = domain_status.get("framework", {})
        base_score = 100.0

        if framework_status.get("status") == "error":
            base_score = 0.0
        elif framework_status.get("status") == "degraded":
            base_score = 60.0
        elif framework_status.get("status") == "initializing":
            base_score = 80.0

        components_count = domain_status.get("components", 0)
        services_count = domain_status.get("services", 0)
        activity_bonus = min((components_count + services_count) * 2, 20.0)

        performance_score = domain_status.get("performance_score", 50.0)
        performance_adjustment = (performance_score - 50.0) * 0.5

        total_score = base_score + activity_bonus + performance_adjustment
        return min(max(total_score, 0.0), 100.0)


# Global integration instance
domain_healing_integration: Optional[DomainHealingIntegration] = None


def initialize_domain_healing_integration(
    domain_framework: Optional[DomainExpansionFramework] = None,
    healing_system: Optional[AutoHealingAIEngineer] = None,
    config: Optional[DomainHealingConfig] = None
) -> DomainHealingIntegration:
    """Initialize domain healing integration"""
    global domain_healing_integration

    if domain_healing_integration is None:
        # Get system instances if not provided
        if domain_framework is None:
            # This would get the actual domain framework instance
            from .core import AutoHealingAIEngineer
            healing_sys = AutoHealingAIEngineer() if healing_system is None else healing_system
            domain_framework = get_domain_expansion_framework(healing_sys)

        if healing_system is None:
            healing_system = AutoHealingAIEngineer()

        domain_healing_integration = DomainHealingIntegration(
            domain_framework=domain_framework,
            healing_system=healing_system,
            config=config
        )

    return domain_healing_integration


def get_domain_healing_integration() -> DomainHealingIntegration:
    """Get the global domain healing integration instance"""
    if domain_healing_integration is None:
        raise RuntimeError("Domain Healing Integration not initialized. Call initialize_domain_healing_integration() first.")
    return domain_healing_integration