"""
Core Auto-Healing AI Engineer System

This module provides the main orchestration system that coordinates all components
of the auto-healing AI engineer architecture.
"""

from typing import Dict, List, Any, Optional, Callable, Type
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
import asyncio
import logging
import threading
import time

from ..api_framework.registry import APIRegistry, APIResourceType, AIModel, APIService
from ..api_framework import get_framework

logger = logging.getLogger("ultra_pinnacle")


class SystemStatus(Enum):
    """System operational status"""
    INITIALIZING = "initializing"
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    CRITICAL = "critical"
    MAINTENANCE = "maintenance"


class ComponentType(Enum):
    """Types of AI components that can be created"""
    MODEL = "model"
    AGENT = "agent"
    SERVICE = "service"
    TRAINER = "trainer"
    MONITOR = "monitor"
    HEALER = "healer"
    LIFECYCLE_MANAGER = "lifecycle_manager"


@dataclass
class AIComponent:
    """Represents a dynamically created AI component"""
    id: str
    name: str
    type: ComponentType
    domain: str  # healthcare, finance, general, etc.
    capabilities: List[str]
    status: str = "initializing"
    health_score: float = 0.0
    performance_metrics: Dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    last_health_check: Optional[datetime] = None
    dependencies: List[str] = field(default_factory=list)
    configuration: Dict[str, Any] = field(default_factory=dict)
    version: str = "1.0.0"
    instance: Optional[Any] = None  # The actual component instance


@dataclass
class AIEngineer:
    """Represents an AI engineer specialized for certain domains"""
    id: str
    name: str
    specialization: str
    experience_level: int = 1
    skills: List[str] = field(default_factory=list)
    performance_history: List[Dict[str, Any]] = field(default_factory=list)
    active_projects: List[str] = field(default_factory=list)
    status: str = "available"
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


class AutoHealingAIEngineer:
    """
    Main orchestration system for auto-healing AI engineering.

    This system autonomously monitors, creates, heals, and manages AI components
    to ensure continuous operation and capability expansion.
    """

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        self.config = config or {}
        self.status = SystemStatus.INITIALIZING

        # Core components
        self.monitor = None
        self.factory = None
        self.healer = None
        self.trainer = None
        self.lifecycle_manager = None
        self.registry_integration = None

        # System state
        self.components: Dict[str, AIComponent] = {}
        self.ai_engineers: Dict[str, AIEngineer] = {}
        self.system_metrics: Dict[str, Any] = {}
        self.health_history: List[Dict[str, Any]] = []

        # Control flags
        self.running = False
        self.monitoring_thread: Optional[threading.Thread] = None
        self.healing_thread: Optional[threading.Thread] = None

        # Event system
        self.event_handlers: Dict[str, List[Callable]] = {}

        # Initialize system
        self._initialize_system()

    def _initialize_system(self):
        """Initialize all system components"""
        try:
            logger.info("Initializing Auto-Healing AI Engineer System")

            # Import and initialize components
            from .monitoring import AIComponentMonitor
            from .factory import DynamicComponentFactory
            from .healing import AutoHealer
            from .training import AIEngineerTrainer
            from .lifecycle import ComponentLifecycleManager
            from .registry_integration import UniversalAPIRegistryIntegration

            # Create components
            self.monitor = AIComponentMonitor(self)
            self.factory = DynamicComponentFactory(self)
            self.healer = AutoHealer(self)
            self.trainer = AIEngineerTrainer(self)
            self.lifecycle_manager = ComponentLifecycleManager(self)
            self.registry_integration = UniversalAPIRegistryIntegration(self)

            # Initialize AI engineers
            self._initialize_ai_engineers()

            # Register with API framework
            self._register_with_api_framework()

            self.status = SystemStatus.HEALTHY
            logger.info("Auto-Healing AI Engineer System initialized successfully")

        except Exception as e:
            logger.error(f"Failed to initialize system: {e}")
            self.status = SystemStatus.CRITICAL
            raise

    def _initialize_ai_engineers(self):
        """Initialize base AI engineers"""
        base_engineers = [
            {
                "id": "general_ai_engineer",
                "name": "General AI Engineer",
                "specialization": "general",
                "skills": ["model_creation", "monitoring", "optimization"]
            },
            {
                "id": "healthcare_ai_engineer",
                "name": "Healthcare AI Engineer",
                "specialization": "healthcare",
                "skills": ["medical_model_creation", "health_data_processing", "diagnostic_ai"]
            },
            {
                "id": "finance_ai_engineer",
                "name": "Finance AI Engineer",
                "specialization": "finance",
                "skills": ["financial_modeling", "risk_assessment", "market_prediction"]
            }
        ]

        for engineer_data in base_engineers:
            engineer = AIEngineer(**engineer_data)
            self.ai_engineers[engineer.id] = engineer

    def _register_with_api_framework(self):
        """Register system with the API framework"""
        try:
            framework = get_framework()

            # Register the system as a service
            service_resource = APIService(
                id="auto_healing_ai_engineer",
                name="Auto-Healing AI Engineer System",
                service_type="ai_engineering",
                endpoints=[
                    "/api/ai-engineer/health",
                    "/api/ai-engineer/components",
                    "/api/ai-engineer/create-component",
                    "/api/ai-engineer/heal-component"
                ],
                health_check_url="/api/ai-engineer/health",
                config={
                    "capabilities": ["monitoring", "healing", "component_creation"],
                    "supported_domains": ["general", "healthcare", "finance", "education"]
                }
            )

            framework.registry.register(service_resource)
            logger.info("Registered with API framework")

        except Exception as e:
            logger.warning(f"Failed to register with API framework: {e}")

    def start(self):
        """Start the auto-healing AI engineer system"""
        if self.running:
            return

        logger.info("Starting Auto-Healing AI Engineer System")
        self.running = True

        # Start monitoring thread
        self.monitoring_thread = threading.Thread(target=self._monitoring_loop, daemon=True)
        self.monitoring_thread.start()

        # Start healing thread
        self.healing_thread = threading.Thread(target=self._healing_loop, daemon=True)
        self.healing_thread.start()

        # Start component lifecycle management
        self.lifecycle_manager.start()

        logger.info("Auto-Healing AI Engineer System started")

    def stop(self):
        """Stop the auto-healing AI engineer system"""
        if not self.running:
            return

        logger.info("Stopping Auto-Healing AI Engineer System")
        self.running = False

        # Stop threads
        if self.monitoring_thread:
            self.monitoring_thread.join(timeout=5)
        if self.healing_thread:
            self.healing_thread.join(timeout=5)

        # Stop lifecycle manager
        self.lifecycle_manager.stop()

        logger.info("Auto-Healing AI Engineer System stopped")

    def _monitoring_loop(self):
        """Main monitoring loop"""
        while self.running:
            try:
                self.monitor.perform_health_checks()
                self._update_system_metrics()
                self._check_system_health()

                # Sleep for monitoring interval
                time.sleep(self.config.get("monitoring_interval", 30))

            except Exception as e:
                logger.error(f"Error in monitoring loop: {e}")
                time.sleep(10)  # Wait before retrying

    def _healing_loop(self):
        """Main healing loop"""
        while self.running:
            try:
                self.healer.check_for_issues()
                self.healer.perform_healing_actions()

                # Sleep for healing interval
                time.sleep(self.config.get("healing_interval", 60))

            except Exception as e:
                logger.error(f"Error in healing loop: {e}")
                time.sleep(10)  # Wait before retrying

    def _update_system_metrics(self):
        """Update overall system metrics"""
        self.system_metrics = {
            "total_components": len(self.components),
            "healthy_components": len([c for c in self.components.values() if c.status == "healthy"]),
            "degraded_components": len([c for c in self.components.values() if c.status == "degraded"]),
            "failed_components": len([c for c in self.components.values() if c.status == "failed"]),
            "active_ai_engineers": len([e for e in self.ai_engineers.values() if e.status == "active"]),
            "system_health_score": self._calculate_system_health_score(),
            "timestamp": datetime.now(timezone.utc).isoformat()
        }

    def _calculate_system_health_score(self) -> float:
        """Calculate overall system health score"""
        if not self.components:
            return 100.0

        total_score = 0.0
        for component in self.components.values():
            total_score += component.health_score

        return total_score / len(self.components)

    def _check_system_health(self):
        """Check overall system health and update status"""
        health_score = self.system_metrics.get("system_health_score", 100.0)
        failed_components = self.system_metrics.get("failed_components", 0)

        if failed_components > 0 or health_score < 50:
            self.status = SystemStatus.CRITICAL
        elif health_score < 80:
            self.status = SystemStatus.DEGRADED
        else:
            self.status = SystemStatus.HEALTHY

        # Record health history
        self.health_history.append({
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "health_score": health_score,
            "status": self.status.value,
            "metrics": self.system_metrics.copy()
        })

        # Keep only last 1000 entries
        if len(self.health_history) > 1000:
            self.health_history = self.health_history[-1000:]

    def create_component(
        self,
        component_type: ComponentType,
        domain: str,
        requirements: Dict[str, Any],
        engineer_id: Optional[str] = None
    ) -> str:
        """Request creation of a new AI component"""
        # Find suitable AI engineer
        engineer = self._find_suitable_engineer(component_type, domain, engineer_id)

        if not engineer:
            raise ValueError(f"No suitable AI engineer found for {component_type.value} in {domain}")

        # Create component via factory
        component_id = self.factory.create_component(component_type, domain, requirements, engineer)

        # Register component
        self.components[component_id] = self.factory.get_component(component_id)

        # Update engineer status
        engineer.active_projects.append(component_id)
        engineer.status = "busy"

        logger.info(f"Created component {component_id} using engineer {engineer.name}")
        return component_id

    def _find_suitable_engineer(
        self,
        component_type: ComponentType,
        domain: str,
        engineer_id: Optional[str] = None
    ) -> Optional[AIEngineer]:
        """Find a suitable AI engineer for the task"""
        if engineer_id:
            return self.ai_engineers.get(engineer_id)

        # Find available engineers with matching skills
        suitable_engineers = []
        for engineer in self.ai_engineers.values():
            if engineer.status != "available":
                continue

            # Check specialization match
            if engineer.specialization == domain or engineer.specialization == "general":
                # Check skill match
                required_skills = self._get_required_skills(component_type)
                if any(skill in engineer.skills for skill in required_skills):
                    suitable_engineers.append(engineer)

        # Return engineer with highest experience level
        if suitable_engineers:
            return max(suitable_engineers, key=lambda e: e.experience_level)

        return None

    def _get_required_skills(self, component_type: ComponentType) -> List[str]:
        """Get required skills for component type"""
        skill_map = {
            ComponentType.MODEL: ["model_creation"],
            ComponentType.AGENT: ["agent_creation", "model_creation"],
            ComponentType.SERVICE: ["service_creation", "api_design"],
            ComponentType.MONITOR: ["monitoring", "metrics"],
            ComponentType.HEALER: ["healing", "diagnostics"],
            ComponentType.TRAINER: ["training", "optimization"],
            ComponentType.LIFECYCLE_MANAGER: ["lifecycle_management", "resource_management"]
        }
        return skill_map.get(component_type, [])

    def heal_component(self, component_id: str) -> bool:
        """Attempt to heal a failing component"""
        component = self.components.get(component_id)
        if not component:
            return False

        return self.healer.heal_component(component)

    def get_system_status(self) -> Dict[str, Any]:
        """Get comprehensive system status"""
        return {
            "status": self.status.value,
            "health_score": self.system_metrics.get("system_health_score", 100.0),
            "components": {
                "total": len(self.components),
                "healthy": self.system_metrics.get("healthy_components", 0),
                "degraded": self.system_metrics.get("degraded_components", 0),
                "failed": self.system_metrics.get("failed_components", 0)
            },
            "ai_engineers": {
                "total": len(self.ai_engineers),
                "active": self.system_metrics.get("active_ai_engineers", 0),
                "available": len([e for e in self.ai_engineers.values() if e.status == "available"])
            },
            "running": self.running,
            "last_health_check": datetime.now(timezone.utc).isoformat()
        }

    def get_component_status(self, component_id: str) -> Optional[Dict[str, Any]]:
        """Get status of a specific component"""
        component = self.components.get(component_id)
        if not component:
            return None

        return {
            "id": component.id,
            "name": component.name,
            "type": component.type.value,
            "domain": component.domain,
            "status": component.status,
            "health_score": component.health_score,
            "performance_metrics": component.performance_metrics,
            "created_at": component.created_at.isoformat(),
            "last_health_check": component.last_health_check.isoformat() if component.last_health_check else None,
            "version": component.version
        }

    def list_components(self, component_type: Optional[ComponentType] = None, domain: Optional[str] = None) -> List[Dict[str, Any]]:
        """List all components with optional filtering"""
        components = list(self.components.values())

        if component_type:
            components = [c for c in components if c.type == component_type]

        if domain:
            components = [c for c in components if c.domain == domain]

        return [{
            "id": c.id,
            "name": c.name,
            "type": c.type.value,
            "domain": c.domain,
            "status": c.status,
            "health_score": c.health_score,
            "created_at": c.created_at.isoformat()
        } for c in components]

    def register_event_handler(self, event_type: str, handler: Callable):
        """Register an event handler"""
        if event_type not in self.event_handlers:
            self.event_handlers[event_type] = []
        self.event_handlers[event_type].append(handler)

    def emit_event(self, event_type: str, data: Dict[str, Any]):
        """Emit an event to all registered handlers"""
        if event_type in self.event_handlers:
            for handler in self.event_handlers[event_type]:
                try:
                    asyncio.create_task(handler(data))
                except Exception as e:
                    logger.error(f"Error in event handler for {event_type}: {e}")


# Global instance
auto_healing_ai_engineer: Optional[AutoHealingAIEngineer] = None


def get_auto_healing_ai_engineer() -> AutoHealingAIEngineer:
    """Get the global auto-healing AI engineer instance"""
    global auto_healing_ai_engineer
    if auto_healing_ai_engineer is None:
        auto_healing_ai_engineer = AutoHealingAIEngineer()
    return auto_healing_ai_engineer


def initialize_auto_healing_system(config: Optional[Dict[str, Any]] = None) -> AutoHealingAIEngineer:
    """Initialize the auto-healing AI engineer system"""
    global auto_healing_ai_engineer
    auto_healing_ai_engineer = AutoHealingAIEngineer(config)
    return auto_healing_ai_engineer