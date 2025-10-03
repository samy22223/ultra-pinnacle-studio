"""
Advanced AI Ecosystem Monitoring & Diagnostics System

This module provides comprehensive real-time monitoring capabilities for AI components,
including predictive analytics, machine learning-based anomaly detection,
cross-component correlation analysis, performance forecasting, and automated alerting.
"""

from typing import Dict, List, Any, Optional, Callable, Tuple
from dataclasses import dataclass, field
from datetime import datetime, timezone, timedelta
from enum import Enum
import asyncio
import logging
import threading
import time
import statistics
import psutil
import numpy as np
from collections import defaultdict, deque
import json

from .core import AutoHealingAIEngineer, AIComponent, ComponentType

logger = logging.getLogger("ultra_pinnacle")


class HealthStatus(Enum):
    """Component health status"""
    HEALTHY = "healthy"
    WARNING = "warning"
    CRITICAL = "critical"
    FAILED = "failed"
    UNKNOWN = "unknown"


class MetricType(Enum):
    """Types of metrics that can be monitored"""
    PERFORMANCE = "performance"
    RESOURCE_USAGE = "resource_usage"
    ERROR_RATE = "error_rate"
    RESPONSE_TIME = "response_time"
    THROUGHPUT = "throughput"
    ACCURACY = "accuracy"
    CUSTOM = "custom"


class AnomalySeverity(Enum):
    """Severity levels for anomalies"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class AlertLevel(Enum):
    """Alert escalation levels"""
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


@dataclass
class MetricData:
    """Represents a single metric measurement"""
    name: str
    value: float
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    metric_type: MetricType = MetricType.CUSTOM
    labels: Dict[str, str] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class HealthCheckResult:
    """Result of a health check"""
    component_id: str
    status: HealthStatus
    health_score: float
    metrics: List[MetricData]
    anomalies: List[str]
    recommendations: List[str]
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    duration: float = 0.0  # seconds


@dataclass
class AnomalyPattern:
    """Represents a detected anomaly pattern"""
    id: str
    component_id: str
    pattern_type: str
    severity: AnomalySeverity
    description: str
    detected_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    metrics: Dict[str, Any] = field(default_factory=dict)
    confidence: float = 0.0
    affected_components: List[str] = field(default_factory=list)
    root_cause_analysis: Dict[str, Any] = field(default_factory=dict)
    predicted_impact: Dict[str, Any] = field(default_factory=dict)


@dataclass
class PredictiveInsight:
    """Represents a predictive insight about system behavior"""
    insight_id: str
    component_id: str
    prediction_type: str
    confidence: float
    predicted_value: float
    prediction_horizon: int  # minutes
    generated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    factors: List[str] = field(default_factory=list)
    recommendations: List[str] = field(default_factory=list)


@dataclass
class AlertRule:
    """Represents an alerting rule"""
    rule_id: str
    name: str
    description: str
    condition: Dict[str, Any]
    severity: AlertLevel
    cooldown_period: int = 300  # seconds
    notification_channels: List[str] = field(default_factory=list)
    enabled: bool = True
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


@dataclass
class SystemHealthSnapshot:
    """Represents a comprehensive system health snapshot"""
    snapshot_id: str
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    overall_health_score: float = 0.0
    component_health: Dict[str, float] = field(default_factory=dict)
    system_metrics: Dict[str, Any] = field(default_factory=dict)
    active_anomalies: List[str] = field(default_factory=list)
    performance_trends: Dict[str, Any] = field(default_factory=dict)
    resource_utilization: Dict[str, float] = field(default_factory=dict)


class AIComponentMonitor:
    """
    Comprehensive monitoring system for AI components.

    Provides real-time monitoring, anomaly detection, predictive analytics,
    and health assessment for all AI components in the system.
    """

    def __init__(self, system: AutoHealingAIEngineer):
        self.system = system
        self.config = system.config.get("monitoring", {})

        # Enhanced monitoring state
        self.health_history: Dict[str, List[HealthCheckResult]] = {}
        self.metric_history: Dict[str, List[MetricData]] = {}
        self.anomalies: List[AnomalyPattern] = []
        self.active_alerts: Dict[str, Dict[str, Any]] = {}
        self.predictive_insights: Dict[str, List[PredictiveInsight]] = {}
        self.system_snapshots: List[SystemHealthSnapshot] = []
        self.alert_rules: Dict[str, AlertRule] = {}

        # Advanced monitoring configuration
        self.health_check_interval = self.config.get("health_check_interval", 30)  # seconds
        self.metric_retention_days = self.config.get("metric_retention_days", 7)
        self.anomaly_detection_enabled = self.config.get("anomaly_detection", True)
        self.predictive_analytics_enabled = self.config.get("predictive_analytics", True)
        self.cross_component_analysis_enabled = self.config.get("cross_component_analysis", True)
        self.advanced_alerting_enabled = self.config.get("advanced_alerting", True)

        # Enhanced thresholds
        self.health_thresholds = {
            "performance_degradation": 0.8,  # 80% of normal performance
            "error_rate_threshold": 0.05,    # 5% error rate
            "response_time_threshold": 5.0,  # 5 seconds
            "resource_usage_threshold": 0.9, # 90% resource usage
            "memory_leak_threshold": 0.85,   # 85% memory increase over time
            "cpu_spike_threshold": 0.95,     # 95% CPU usage
            "error_spike_threshold": 0.1     # 10% error rate spike
        }

        # Advanced anomaly detection
        self.baseline_metrics: Dict[str, Dict[str, Any]] = {}
        self.anomaly_thresholds = {
            "z_score_threshold": 3.0,        # Standard deviations
            "trend_change_threshold": 0.5,   # 50% change
            "spike_detection_window": 10,    # measurements
            "correlation_threshold": 0.8,    # Correlation coefficient
            "seasonal_analysis_window": 24   # hours for seasonal patterns
        }

        # Machine learning models for anomaly detection
        self.ml_models: Dict[str, Any] = {}
        self.correlation_matrix: Dict[str, Dict[str, float]] = {}

        # Alert management
        self.last_alert_times: Dict[str, datetime] = {}
        self.alert_escalation_levels: Dict[str, int] = {}

        # Initialize advanced features
        self._initialize_alert_rules()
        self._initialize_ml_models()

        logger.info("Advanced AI Ecosystem Monitor initialized")

    def perform_health_checks(self):
        """Perform health checks on all components"""
        for component_id, component in self.system.components.items():
            try:
                result = self._perform_component_health_check(component)
                self._store_health_result(result)

                # Update component status
                component.status = result.status.value
                component.health_score = result.health_score
                component.last_health_check = result.timestamp

                # Check for anomalies
                if self.anomaly_detection_enabled:
                    anomalies = self._detect_anomalies(component_id, result)
                    if anomalies:
                        self._handle_anomalies(component_id, anomalies, result)

                # Emit health check event
                self.system.emit_event("component_health_checked", {
                    "component_id": component_id,
                    "status": result.status.value,
                    "health_score": result.health_score,
                    "anomalies": len(result.anomalies)
                })

            except Exception as e:
                logger.error(f"Error checking health of component {component_id}: {e}")
                # Mark as failed
                component.status = HealthStatus.FAILED.value
                component.health_score = 0.0

    def _perform_component_health_check(self, component: AIComponent) -> HealthCheckResult:
        """Perform health check on a specific component"""
        start_time = time.time()

        metrics = []
        anomalies = []
        recommendations = []

        try:
            # Gather metrics based on component type
            if component.type == ComponentType.MODEL:
                metrics.extend(self._check_model_metrics(component))
            elif component.type == ComponentType.AGENT:
                metrics.extend(self._check_agent_metrics(component))
            elif component.type == ComponentType.SERVICE:
                metrics.extend(self._check_service_metrics(component))
            else:
                metrics.extend(self._check_generic_metrics(component))

            # Check resource usage
            metrics.extend(self._check_resource_metrics(component))

            # Analyze metrics for issues
            health_score = self._calculate_health_score(metrics)
            status = self._determine_health_status(health_score, metrics)

            # Detect anomalies in current metrics
            component_anomalies = self._analyze_metrics_for_anomalies(component.id, metrics)
            anomalies.extend(component_anomalies)

            # Generate recommendations
            if status != HealthStatus.HEALTHY:
                recommendations.extend(self._generate_recommendations(component, metrics, anomalies))

        except Exception as e:
            logger.error(f"Error during health check for {component.id}: {e}")
            health_score = 0.0
            status = HealthStatus.FAILED
            anomalies.append(f"Health check failed: {str(e)}")
            recommendations.append("Investigate component failure and restart if necessary")

        duration = time.time() - start_time

        return HealthCheckResult(
            component_id=component.id,
            status=status,
            health_score=health_score,
            metrics=metrics,
            anomalies=anomalies,
            recommendations=recommendations,
            duration=duration
        )

    def _check_model_metrics(self, component: AIComponent) -> List[MetricData]:
        """Check metrics specific to AI models"""
        metrics = []

        try:
            # Performance metrics
            metrics.append(MetricData(
                name="inference_time",
                value=self._measure_inference_time(component),
                metric_type=MetricType.RESPONSE_TIME,
                labels={"component_type": "model"}
            ))

            # Accuracy metrics (if available)
            accuracy = self._measure_model_accuracy(component)
            if accuracy is not None:
                metrics.append(MetricData(
                    name="model_accuracy",
                    value=accuracy,
                    metric_type=MetricType.ACCURACY,
                    labels={"component_type": "model"}
                ))

            # Error rate
            error_rate = self._measure_error_rate(component)
            metrics.append(MetricData(
                name="error_rate",
                value=error_rate,
                metric_type=MetricType.ERROR_RATE,
                labels={"component_type": "model"}
            ))

        except Exception as e:
            logger.warning(f"Error checking model metrics for {component.id}: {e}")

        return metrics

    def _check_agent_metrics(self, component: AIComponent) -> List[MetricData]:
        """Check metrics specific to AI agents"""
        metrics = []

        try:
            # Task completion rate
            completion_rate = self._measure_task_completion_rate(component)
            metrics.append(MetricData(
                name="task_completion_rate",
                value=completion_rate,
                metric_type=MetricType.PERFORMANCE,
                labels={"component_type": "agent"}
            ))

            # Decision accuracy
            decision_accuracy = self._measure_decision_accuracy(component)
            if decision_accuracy is not None:
                metrics.append(MetricData(
                    name="decision_accuracy",
                    value=decision_accuracy,
                    metric_type=MetricType.ACCURACY,
                    labels={"component_type": "agent"}
                ))

        except Exception as e:
            logger.warning(f"Error checking agent metrics for {component.id}: {e}")

        return metrics

    def _check_service_metrics(self, component: AIComponent) -> List[MetricData]:
        """Check metrics specific to AI services"""
        metrics = []

        try:
            # Throughput
            throughput = self._measure_service_throughput(component)
            metrics.append(MetricData(
                name="service_throughput",
                value=throughput,
                metric_type=MetricType.THROUGHPUT,
                labels={"component_type": "service"}
            ))

            # Response time
            response_time = self._measure_service_response_time(component)
            metrics.append(MetricData(
                name="service_response_time",
                value=response_time,
                metric_type=MetricType.RESPONSE_TIME,
                labels={"component_type": "service"}
            ))

        except Exception as e:
            logger.warning(f"Error checking service metrics for {component.id}: {e}")

        return metrics

    def _check_generic_metrics(self, component: AIComponent) -> List[MetricData]:
        """Check generic metrics applicable to all components"""
        metrics = []

        try:
            # Uptime
            uptime = self._measure_uptime(component)
            metrics.append(MetricData(
                name="uptime_percentage",
                value=uptime,
                metric_type=MetricType.PERFORMANCE,
                labels={"component_type": "generic"}
            ))

        except Exception as e:
            logger.warning(f"Error checking generic metrics for {component.id}: {e}")

        return metrics

    def _check_resource_metrics(self, component: AIComponent) -> List[MetricData]:
        """Check resource usage metrics"""
        metrics = []

        try:
            # CPU usage
            cpu_usage = psutil.cpu_percent(interval=1)
            metrics.append(MetricData(
                name="cpu_usage",
                value=cpu_usage,
                metric_type=MetricType.RESOURCE_USAGE,
                labels={"resource_type": "cpu"}
            ))

            # Memory usage
            memory = psutil.virtual_memory()
            metrics.append(MetricData(
                name="memory_usage",
                value=memory.percent,
                metric_type=MetricType.RESOURCE_USAGE,
                labels={"resource_type": "memory"}
            ))

            # Disk usage
            disk = psutil.disk_usage('/')
            metrics.append(MetricData(
                name="disk_usage",
                value=disk.percent,
                metric_type=MetricType.RESOURCE_USAGE,
                labels={"resource_type": "disk"}
            ))

        except Exception as e:
            logger.warning(f"Error checking resource metrics: {e}")

        return metrics

    def _measure_inference_time(self, component: AIComponent) -> float:
        """Measure model inference time"""
        # Placeholder - would need actual model inference
        return 0.5  # seconds

    def _measure_model_accuracy(self, component: AIComponent) -> Optional[float]:
        """Measure model accuracy"""
        # Placeholder - would need validation data
        return None

    def _measure_error_rate(self, component: AIComponent) -> float:
        """Measure error rate"""
        # Placeholder - would track actual errors
        return 0.02  # 2%

    def _measure_task_completion_rate(self, component: AIComponent) -> float:
        """Measure task completion rate"""
        # Placeholder
        return 0.95  # 95%

    def _measure_decision_accuracy(self, component: AIComponent) -> Optional[float]:
        """Measure decision accuracy"""
        # Placeholder
        return None

    def _measure_service_throughput(self, component: AIComponent) -> float:
        """Measure service throughput"""
        # Placeholder - requests per second
        return 100.0

    def _measure_service_response_time(self, component: AIComponent) -> float:
        """Measure service response time"""
        # Placeholder
        return 0.2  # seconds

    def _measure_uptime(self, component: AIComponent) -> float:
        """Measure component uptime percentage"""
        # Placeholder - would track actual uptime
        return 99.5

    def _calculate_health_score(self, metrics: List[MetricData]) -> float:
        """Calculate overall health score from metrics"""
        if not metrics:
            return 50.0  # Neutral score

        scores = []

        for metric in metrics:
            score = self._calculate_metric_score(metric)
            scores.append(score)

        # Weighted average
        return statistics.mean(scores) if scores else 50.0

    def _calculate_metric_score(self, metric: MetricData) -> float:
        """Calculate health score for a single metric"""
        # Define healthy ranges for different metric types
        healthy_ranges = {
            MetricType.RESPONSE_TIME: (0, 2.0),  # 0-2 seconds
            MetricType.ERROR_RATE: (0, 0.05),    # 0-5%
            MetricType.RESOURCE_USAGE: (0, 80),  # 0-80%
            MetricType.ACCURACY: (0.8, 1.0),     # 80-100%
            MetricType.THROUGHPUT: (10, float('inf')),  # > 10 req/sec
        }

        if metric.metric_type in healthy_ranges:
            min_val, max_val = healthy_ranges[metric.metric_type]
            if min_val <= metric.value <= max_val:
                return 100.0
            elif metric.value < min_val:
                # Below minimum - could be good or bad depending on type
                if metric.metric_type in [MetricType.ERROR_RATE]:
                    return 100.0  # Lower error rate is better
                else:
                    return 50.0   # Lower throughput is bad
            else:
                # Above maximum - bad for most metrics
                return max(0, 100 - (metric.value - max_val) * 10)
        else:
            # Unknown metric type - assume 80% healthy
            return 80.0

    def _determine_health_status(self, health_score: float, metrics: List[MetricData]) -> HealthStatus:
        """Determine health status from score and metrics"""
        if health_score >= 90:
            return HealthStatus.HEALTHY
        elif health_score >= 70:
            return HealthStatus.WARNING
        elif health_score >= 30:
            return HealthStatus.CRITICAL
        else:
            return HealthStatus.FAILED

    def _analyze_metrics_for_anomalies(self, component_id: str, metrics: List[MetricData]) -> List[str]:
        """Analyze metrics for anomalies"""
        anomalies = []

        for metric in metrics:
            # Check against thresholds
            if metric.metric_type == MetricType.ERROR_RATE:
                if metric.value > self.health_thresholds["error_rate_threshold"]:
                    anomalies.append(f"High error rate: {metric.value:.2%}")
            elif metric.metric_type == MetricType.RESPONSE_TIME:
                if metric.value > self.health_thresholds["response_time_threshold"]:
                    anomalies.append(f"Slow response time: {metric.value:.2f}s")
            elif metric.metric_type == MetricType.RESOURCE_USAGE:
                if metric.value > self.health_thresholds["resource_usage_threshold"]:
                    anomalies.append(f"High resource usage: {metric.value:.1f}%")

        return anomalies

    def _detect_anomalies(self, component_id: str, result: HealthCheckResult) -> List[AnomalyPattern]:
        """Detect anomalies using statistical analysis"""
        anomalies = []

        if component_id not in self.metric_history:
            return anomalies

        # Get recent metrics
        recent_metrics = self.metric_history[component_id][-self.anomaly_thresholds["spike_detection_window"]:]

        for metric in result.metrics:
            # Calculate baseline if not exists
            if component_id not in self.baseline_metrics:
                self.baseline_metrics[component_id] = {}

            if metric.name not in self.baseline_metrics[component_id]:
                # Initialize baseline with first few measurements
                baseline_metrics = [m.value for m in recent_metrics if m.name == metric.name]
                if len(baseline_metrics) >= 5:
                    self.baseline_metrics[component_id][metric.name] = {
                        "mean": statistics.mean(baseline_metrics),
                        "stdev": statistics.stdev(baseline_metrics) if len(baseline_metrics) > 1 else 0
                    }

            baseline = self.baseline_metrics[component_id].get(metric.name)
            if baseline and baseline["stdev"] > 0:
                # Z-score analysis
                z_score = abs(metric.value - baseline["mean"]) / baseline["stdev"]
                if z_score > self.anomaly_thresholds["z_score_threshold"]:
                    anomaly = AnomalyPattern(
                        id=f"{component_id}_{metric.name}_{int(time.time())}",
                        component_id=component_id,
                        pattern_type="statistical_outlier",
                        severity="high" if z_score > 4 else "medium",
                        description=f"Anomalous {metric.name}: {metric.value:.2f} (z-score: {z_score:.2f})",
                        metrics={"z_score": z_score, "value": metric.value, "baseline_mean": baseline["mean"]},
                        confidence=min(z_score / 5, 1.0)  # Confidence based on z-score
                    )
                    anomalies.append(anomaly)

        return anomalies

    def _handle_anomalies(self, component_id: str, anomalies: List[AnomalyPattern], result: HealthCheckResult):
        """Handle detected anomalies"""
        for anomaly in anomalies:
            self.anomalies.append(anomaly)

            # Create alert if not exists
            alert_key = f"{component_id}_{anomaly.pattern_type}"
            if alert_key not in self.active_alerts:
                self.active_alerts[alert_key] = {
                    "component_id": component_id,
                    "anomaly": anomaly,
                    "first_detected": anomaly.detected_at,
                    "last_seen": anomaly.detected_at,
                    "count": 1
                }
            else:
                self.active_alerts[alert_key]["count"] += 1
                self.active_alerts[alert_key]["last_seen"] = anomaly.detected_at

            # Emit anomaly event
            self.system.emit_event("anomaly_detected", {
                "component_id": component_id,
                "anomaly_id": anomaly.id,
                "pattern_type": anomaly.pattern_type,
                "severity": anomaly.severity,
                "description": anomaly.description
            })

    def _generate_recommendations(self, component: AIComponent, metrics: List[MetricData], anomalies: List[str]) -> List[str]:
        """Generate recommendations based on component state"""
        recommendations = []

        # Analyze metrics for specific recommendations
        for metric in metrics:
            if metric.metric_type == MetricType.ERROR_RATE and metric.value > 0.1:
                recommendations.append("High error rate detected. Consider retraining the model or checking input validation.")
            elif metric.metric_type == MetricType.RESPONSE_TIME and metric.value > 10:
                recommendations.append("Slow response time. Consider optimizing the model or increasing resources.")
            elif metric.metric_type == MetricType.RESOURCE_USAGE and metric.value > 95:
                recommendations.append("High resource usage. Consider scaling up resources or optimizing the component.")

        # Add anomaly-based recommendations
        for anomaly in anomalies:
            if "error rate" in anomaly.lower():
                recommendations.append("Investigate error sources and implement better error handling.")
            elif "response time" in anomaly.lower():
                recommendations.append("Profile the component to identify performance bottlenecks.")

        return recommendations

    def _store_health_result(self, result: HealthCheckResult):
        """Store health check result in history"""
        if result.component_id not in self.health_history:
            self.health_history[result.component_id] = []

        self.health_history[result.component_id].append(result)

        # Store metrics
        if result.component_id not in self.metric_history:
            self.metric_history[result.component_id] = []

        self.metric_history[result.component_id].extend(result.metrics)

        # Clean up old data
        self._cleanup_old_data()

    def _cleanup_old_data(self):
        """Clean up old metric and health data"""
        cutoff_date = datetime.now(timezone.utc) - timedelta(days=self.metric_retention_days)

        # Clean health history
        for component_id in self.health_history:
            self.health_history[component_id] = [
                result for result in self.health_history[component_id]
                if result.timestamp > cutoff_date
            ]

        # Clean metric history
        for component_id in self.metric_history:
            self.metric_history[component_id] = [
                metric for metric in self.metric_history[component_id]
                if metric.timestamp > cutoff_date
            ]

        # Clean old anomalies (keep last 100 per component)
        anomaly_counts = {}
        filtered_anomalies = []
        for anomaly in reversed(self.anomalies):
            count = anomaly_counts.get(anomaly.component_id, 0)
            if count < 100:
                filtered_anomalies.append(anomaly)
                anomaly_counts[anomaly.component_id] = count + 1

        self.anomalies = list(reversed(filtered_anomalies))

    def get_component_health_history(self, component_id: str, hours: int = 24) -> List[Dict[str, Any]]:
        """Get health history for a component"""
        if component_id not in self.health_history:
            return []

        cutoff_time = datetime.now(timezone.utc) - timedelta(hours=hours)
        results = [
            result for result in self.health_history[component_id]
            if result.timestamp > cutoff_time
        ]

        return [{
            "timestamp": result.timestamp.isoformat(),
            "status": result.status.value,
            "health_score": result.health_score,
            "anomalies": result.anomalies,
            "recommendations": result.recommendations,
            "duration": result.duration
        } for result in results]

    def get_component_metrics(self, component_id: str, metric_name: Optional[str] = None, hours: int = 24) -> List[Dict[str, Any]]:
        """Get metrics for a component"""
        if component_id not in self.metric_history:
            return []

        cutoff_time = datetime.now(timezone.utc) - timedelta(hours=hours)
        metrics = [
            metric for metric in self.metric_history[component_id]
            if metric.timestamp > cutoff_time and (metric_name is None or metric.name == metric_name)
        ]

        return [{
            "name": metric.name,
            "value": metric.value,
            "timestamp": metric.timestamp.isoformat(),
            "type": metric.metric_type.value,
            "labels": metric.labels
        } for metric in metrics]

    def get_anomalies(self, component_id: Optional[str] = None, hours: int = 24) -> List[Dict[str, Any]]:
        """Get detected anomalies"""
        cutoff_time = datetime.now(timezone.utc) - timedelta(hours=hours)
        anomalies = [
            anomaly for anomaly in self.anomalies
            if anomaly.detected_at > cutoff_time and (component_id is None or anomaly.component_id == component_id)
        ]

        return [{
            "id": anomaly.id,
            "component_id": anomaly.component_id,
            "pattern_type": anomaly.pattern_type,
            "severity": anomaly.severity,
            "description": anomaly.description,
            "detected_at": anomaly.detected_at.isoformat(),
            "confidence": anomaly.confidence
        } for anomaly in anomalies]

    def get_monitoring_stats(self) -> Dict[str, Any]:
        """Get overall monitoring statistics"""
        total_components = len(self.system.components)
        total_anomalies = len(self.anomalies)
        active_alerts = len(self.active_alerts)

        # Calculate average health score
        health_scores = []
        for component in self.system.components.values():
            if component.health_score > 0:
                health_scores.append(component.health_score)

        avg_health_score = statistics.mean(health_scores) if health_scores else 0.0

        return {
            "total_components_monitored": total_components,
            "average_health_score": avg_health_score,
            "total_anomalies_detected": total_anomalies,
            "active_alerts": active_alerts,
            "monitoring_enabled": True,
            "anomaly_detection_enabled": self.anomaly_detection_enabled,
            "predictive_analytics_enabled": self.predictive_analytics_enabled,
            "cross_component_analysis_enabled": self.cross_component_analysis_enabled,
            "advanced_alerting_enabled": self.advanced_alerting_enabled
        }

    def _initialize_alert_rules(self):
        """Initialize default alert rules"""
        default_rules = [
            AlertRule(
                rule_id="high_error_rate",
                name="High Error Rate Alert",
                description="Alert when error rate exceeds threshold",
                condition={"metric": "error_rate", "operator": ">", "threshold": 0.1},
                severity=AlertLevel.ERROR,
                cooldown_period=300,
                notification_channels=["email", "slack"]
            ),
            AlertRule(
                rule_id="performance_degradation",
                name="Performance Degradation Alert",
                description="Alert when performance drops significantly",
                condition={"metric": "health_score", "operator": "<", "threshold": 60},
                severity=AlertLevel.WARNING,
                cooldown_period=600,
                notification_channels=["email", "dashboard"]
            ),
            AlertRule(
                rule_id="resource_exhaustion",
                name="Resource Exhaustion Alert",
                description="Alert when resource usage is critically high",
                condition={"metric": "resource_usage", "operator": ">", "threshold": 0.9},
                severity=AlertLevel.CRITICAL,
                cooldown_period=180,
                notification_channels=["email", "slack", "sms"]
            )
        ]

        for rule in default_rules:
            self.alert_rules[rule.rule_id] = rule

    def _initialize_ml_models(self):
        """Initialize machine learning models for anomaly detection"""
        # Simple moving average model for trend detection
        self.ml_models["trend_detector"] = {
            "type": "moving_average",
            "window_size": 10,
            "sensitivity": 2.0
        }

        # Correlation model for cross-component analysis
        self.ml_models["correlation_analyzer"] = {
            "type": "correlation_matrix",
            "min_correlation_threshold": 0.7,
            "update_interval": 300  # 5 minutes
        }

    def perform_predictive_analytics(self, component_id: str) -> List[PredictiveInsight]:
        """Perform predictive analytics on a component"""
        if not self.predictive_analytics_enabled:
            return []

        insights = []
        component = self.system.components.get(component_id)

        if not component or component_id not in self.metric_history:
            return insights

        # Get recent metrics for trend analysis
        recent_metrics = self.metric_history[component_id][-50:]  # Last 50 measurements

        if len(recent_metrics) < 10:
            return insights  # Need sufficient data for prediction

        # Predict performance trends
        performance_insight = self._predict_performance_trend(component_id, recent_metrics)
        if performance_insight:
            insights.append(performance_insight)

        # Predict resource usage
        resource_insight = self._predict_resource_usage(component_id, recent_metrics)
        if resource_insight:
            insights.append(resource_insight)

        # Predict failure probability
        failure_insight = self._predict_failure_probability(component_id, recent_metrics)
        if failure_insight:
            insights.append(failure_insight)

        # Store insights
        if component_id not in self.predictive_insights:
            self.predictive_insights[component_id] = []
        self.predictive_insights[component_id].extend(insights)

        # Keep only recent insights
        if len(self.predictive_insights[component_id]) > 100:
            self.predictive_insights[component_id] = self.predictive_insights[component_id][-100:]

        return insights

    def _predict_performance_trend(self, component_id: str, metrics: List[MetricData]) -> Optional[PredictiveInsight]:
        """Predict performance trend using linear regression"""
        try:
            # Extract health score metrics
            health_metrics = [m for m in metrics if m.name == "health_score"]
            if len(health_metrics) < 5:
                return None

            # Simple linear regression on recent values
            values = [m.value for m in health_metrics[-10:]]
            if len(values) < 5:
                return None

            # Calculate trend (simplified)
            recent_avg = sum(values[-3:]) / len(values[-3:])
            overall_avg = sum(values) / len(values)

            # Predict next value
            trend = recent_avg - overall_avg
            predicted_value = recent_avg + trend

            confidence = min(abs(trend) * 10, 1.0)  # Higher trend = higher confidence

            return PredictiveInsight(
                insight_id=f"perf_trend_{component_id}_{int(time.time())}",
                component_id=component_id,
                prediction_type="performance_trend",
                confidence=confidence,
                predicted_value=max(0, min(100, predicted_value)),  # Clamp to 0-100
                prediction_horizon=30,  # 30 minutes
                factors=["recent_performance", "trend_analysis"],
                recommendations=self._generate_performance_recommendations(predicted_value, trend)
            )
        except Exception as e:
            logger.warning(f"Error predicting performance trend for {component_id}: {e}")
            return None

    def _predict_resource_usage(self, component_id: str, metrics: List[MetricData]) -> Optional[PredictiveInsight]:
        """Predict resource usage trends"""
        try:
            # Extract CPU and memory metrics
            cpu_metrics = [m for m in metrics if m.name == "cpu_usage"]
            memory_metrics = [m for m in metrics if m.name == "memory_usage"]

            if not cpu_metrics or not memory_metrics:
                return None

            # Use recent values for prediction
            recent_cpu = [m.value for m in cpu_metrics[-10:]]
            recent_memory = [m.value for m in memory_metrics[-10:]]

            if len(recent_cpu) < 5 or len(recent_memory) < 5:
                return None

            # Simple trend analysis
            cpu_trend = recent_cpu[-1] - recent_cpu[0] if len(recent_cpu) > 1 else 0
            memory_trend = recent_memory[-1] - recent_memory[0] if len(recent_memory) > 1 else 0

            # Predict if usage will exceed threshold
            predicted_cpu = recent_cpu[-1] + cpu_trend
            predicted_memory = recent_memory[-1] + memory_trend

            # Check if concerning trend
            if predicted_cpu > 80 or predicted_memory > 85:
                return PredictiveInsight(
                    insight_id=f"resource_pred_{component_id}_{int(time.time())}",
                    component_id=component_id,
                    prediction_type="resource_usage",
                    confidence=0.7,
                    predicted_value=max(predicted_cpu, predicted_memory),
                    prediction_horizon=60,  # 1 hour
                    factors=["cpu_trend", "memory_trend"],
                    recommendations=["Consider scaling up resources", "Optimize resource usage"]
                )

            return None
        except Exception as e:
            logger.warning(f"Error predicting resource usage for {component_id}: {e}")
            return None

    def _predict_failure_probability(self, component_id: str, metrics: List[MetricData]) -> Optional[PredictiveInsight]:
        """Predict probability of component failure"""
        try:
            # Analyze error rates and performance degradation
            error_metrics = [m for m in metrics if m.name == "error_rate"]
            health_metrics = [m for m in metrics if m.name == "health_score"]

            if not error_metrics or not health_metrics:
                return None

            # Calculate failure indicators
            recent_errors = [m.value for m in error_metrics[-10:]]
            recent_health = [m.value for m in health_metrics[-10:]]

            if len(recent_errors) < 5 or len(recent_health) < 5:
                return None

            # Simple failure probability calculation
            avg_error_rate = sum(recent_errors) / len(recent_errors)
            avg_health_score = sum(recent_health) / len(recent_health)

            # Calculate failure probability based on error rate and health degradation
            error_factor = min(avg_error_rate * 10, 1.0)  # Scale error rate to 0-1
            health_factor = max(0, (80 - avg_health_score) / 80)  # Health below 80% indicates risk

            failure_probability = (error_factor + health_factor) / 2

            if failure_probability > 0.3:  # Only report if significant risk
                return PredictiveInsight(
                    insight_id=f"failure_pred_{component_id}_{int(time.time())}",
                    component_id=component_id,
                    prediction_type="failure_probability",
                    confidence=min(failure_probability * 2, 1.0),
                    predicted_value=failure_probability * 100,
                    prediction_horizon=120,  # 2 hours
                    factors=["error_rate", "health_degradation"],
                    recommendations=self._generate_failure_prevention_recommendations(failure_probability)
                )

            return None
        except Exception as e:
            logger.warning(f"Error predicting failure probability for {component_id}: {e}")
            return None

    def _generate_performance_recommendations(self, predicted_value: float, trend: float) -> List[str]:
        """Generate recommendations based on performance prediction"""
        recommendations = []

        if predicted_value < 50:
            recommendations.append("Critical performance degradation predicted - immediate intervention required")
            recommendations.append("Consider component restart or replacement")
        elif predicted_value < 70:
            recommendations.append("Performance degradation predicted - monitor closely")
            recommendations.append("Check for resource constraints or configuration issues")
        elif trend < -5:
            recommendations.append("Declining performance trend detected")
            recommendations.append("Investigate root cause of performance degradation")

        return recommendations

    def _generate_failure_prevention_recommendations(self, failure_probability: float) -> List[str]:
        """Generate failure prevention recommendations"""
        recommendations = []

        if failure_probability > 0.7:
            recommendations.append("High failure probability - prepare backup component")
            recommendations.append("Schedule immediate maintenance window")
        elif failure_probability > 0.5:
            recommendations.append("Moderate failure risk - increase monitoring frequency")
            recommendations.append("Review component configuration and dependencies")
        else:
            recommendations.append("Low but notable failure risk - continue monitoring")

        return recommendations

    def analyze_cross_component_correlations(self) -> Dict[str, Any]:
        """Analyze correlations between different components"""
        if not self.cross_component_analysis_enabled:
            return {}

        correlations = {
            "component_pairs": [],
            "correlation_matrix": {},
            "anomalous_patterns": []
        }

        component_ids = list(self.system.components.keys())
        if len(component_ids) < 2:
            return correlations

        # Build correlation matrix for key metrics
        metrics_to_correlate = ["health_score", "error_rate", "response_time"]

        for i, comp1_id in enumerate(component_ids):
            if comp1_id not in self.correlation_matrix:
                self.correlation_matrix[comp1_id] = {}

            for comp2_id in component_ids[i+1:]:
                if comp2_id not in self.correlation_matrix[comp1_id]:
                    correlation = self._calculate_component_correlation(comp1_id, comp2_id, metrics_to_correlate)

                    self.correlation_matrix[comp1_id][comp2_id] = correlation

                    if abs(correlation) > self.anomaly_thresholds["correlation_threshold"]:
                        correlations["component_pairs"].append({
                            "component1": comp1_id,
                            "component2": comp2_id,
                            "correlation": correlation,
                            "strength": "strong" if abs(correlation) > 0.8 else "moderate"
                        })

        correlations["correlation_matrix"] = self.correlation_matrix
        return correlations

    def _calculate_component_correlation(self, comp1_id: str, comp2_id: str, metrics: List[str]) -> float:
        """Calculate correlation coefficient between two components"""
        try:
            correlation_sum = 0.0
            valid_metrics = 0

            for metric_name in metrics:
                comp1_values = [m.value for m in self.metric_history.get(comp1_id, []) if m.name == metric_name]
                comp2_values = [m.value for m in self.metric_history.get(comp2_id, []) if m.name == metric_name]

                if len(comp1_values) >= 5 and len(comp2_values) >= 5:
                    # Use last 10 values for correlation
                    comp1_recent = comp1_values[-10:]
                    comp2_recent = comp2_values[-10:]

                    if len(comp1_recent) == len(comp2_recent):
                        correlation = np.corrcoef(comp1_recent, comp2_recent)[0, 1]
                        if not np.isnan(correlation):
                            correlation_sum += correlation
                            valid_metrics += 1

            return correlation_sum / valid_metrics if valid_metrics > 0 else 0.0
        except Exception as e:
            logger.warning(f"Error calculating correlation between {comp1_id} and {comp2_id}: {e}")
            return 0.0

    def create_system_health_snapshot(self) -> str:
        """Create a comprehensive system health snapshot"""
        snapshot_id = f"snapshot_{int(time.time())}"

        # Calculate overall health score
        health_scores = [c.health_score for c in self.system.components.values() if c.health_score > 0]
        overall_health_score = sum(health_scores) / len(health_scores) if health_scores else 100.0

        # Gather component health
        component_health = {c_id: c.health_score for c_id, c in self.system.components.items()}

        # Gather system metrics
        system_metrics = self._gather_system_metrics()

        # Get active anomalies
        recent_anomalies = [a.id for a in self.anomalies if a.detected_at > datetime.now(timezone.utc) - timedelta(hours=1)]

        # Analyze performance trends
        performance_trends = self._analyze_performance_trends()

        # Gather resource utilization
        resource_utilization = self._gather_resource_utilization()

        snapshot = SystemHealthSnapshot(
            snapshot_id=snapshot_id,
            overall_health_score=overall_health_score,
            component_health=component_health,
            system_metrics=system_metrics,
            active_anomalies=recent_anomalies,
            performance_trends=performance_trends,
            resource_utilization=resource_utilization
        )

        self.system_snapshots.append(snapshot)

        # Keep only recent snapshots (last 100)
        if len(self.system_snapshots) > 100:
            self.system_snapshots = self.system_snapshots[-100:]

        logger.info(f"Created system health snapshot {snapshot_id} with health score {overall_health_score:.2f}")
        return snapshot_id

    def _gather_system_metrics(self) -> Dict[str, Any]:
        """Gather comprehensive system metrics"""
        return {
            "total_components": len(self.system.components),
            "healthy_components": len([c for c in self.system.components.values() if c.status == "healthy"]),
            "failed_components": len([c for c in self.system.components.values() if c.status == "failed"]),
            "total_anomalies": len(self.anomalies),
            "active_alerts": len(self.active_alerts),
            "monitoring_uptime": self._calculate_monitoring_uptime(),
            "last_snapshot": datetime.now(timezone.utc).isoformat()
        }

    def _analyze_performance_trends(self) -> Dict[str, Any]:
        """Analyze performance trends across all components"""
        trends = {
            "improving_components": [],
            "degrading_components": [],
            "stable_components": []
        }

        for component_id, component in self.system.components.items():
            if component_id in self.health_history and len(self.health_history[component_id]) >= 5:
                recent_checks = self.health_history[component_id][-5:]
                older_checks = self.health_history[component_id][-10:-5] if len(self.health_history[component_id]) >= 10 else recent_checks

                if older_checks:
                    recent_avg = sum(c.health_score for c in recent_checks) / len(recent_checks)
                    older_avg = sum(c.health_score for c in older_checks) / len(older_checks)

                    if recent_avg > older_avg + 5:
                        trends["improving_components"].append(component_id)
                    elif recent_avg < older_avg - 5:
                        trends["degrading_components"].append(component_id)
                    else:
                        trends["stable_components"].append(component_id)

        return trends

    def _gather_resource_utilization(self) -> Dict[str, float]:
        """Gather current resource utilization across all components"""
        utilization = {
            "avg_cpu_usage": 0.0,
            "avg_memory_usage": 0.0,
            "max_cpu_usage": 0.0,
            "max_memory_usage": 0.0
        }

        cpu_values = []
        memory_values = []

        for component in self.system.components.values():
            if component.performance_metrics:
                cpu = component.performance_metrics.get("cpu_usage", 0)
                memory = component.performance_metrics.get("memory_usage", 0)

                if cpu > 0:
                    cpu_values.append(cpu)
                if memory > 0:
                    memory_values.append(memory)

        if cpu_values:
            utilization["avg_cpu_usage"] = sum(cpu_values) / len(cpu_values)
            utilization["max_cpu_usage"] = max(cpu_values)

        if memory_values:
            utilization["avg_memory_usage"] = sum(memory_values) / len(memory_values)
            utilization["max_memory_usage"] = max(memory_values)

        return utilization

    def _calculate_monitoring_uptime(self) -> float:
        """Calculate monitoring system uptime percentage"""
        # Placeholder - would track actual monitoring uptime
        return 99.9

    def get_predictive_insights(self, component_id: str, hours: int = 24) -> List[Dict[str, Any]]:
        """Get predictive insights for a component"""
        if component_id not in self.predictive_insights:
            return []

        cutoff_time = datetime.now(timezone.utc) - timedelta(hours=hours)
        insights = [
            insight for insight in self.predictive_insights[component_id]
            if insight.generated_at > cutoff_time
        ]

        return [{
            "insight_id": insight.insight_id,
            "prediction_type": insight.prediction_type,
            "confidence": insight.confidence,
            "predicted_value": insight.predicted_value,
            "prediction_horizon_minutes": insight.prediction_horizon,
            "generated_at": insight.generated_at.isoformat(),
            "factors": insight.factors,
            "recommendations": insight.recommendations
        } for insight in insights]

    def get_system_snapshots(self, hours: int = 24) -> List[Dict[str, Any]]:
        """Get system health snapshots"""
        cutoff_time = datetime.now(timezone.utc) - timedelta(hours=hours)
        snapshots = [
            snapshot for snapshot in self.system_snapshots
            if snapshot.timestamp > cutoff_time
        ]

        return [{
            "snapshot_id": snapshot.snapshot_id,
            "timestamp": snapshot.timestamp.isoformat(),
            "overall_health_score": snapshot.overall_health_score,
            "component_count": len(snapshot.component_health),
            "active_anomalies_count": len(snapshot.active_anomalies),
            "resource_utilization": snapshot.resource_utilization
        } for snapshot in snapshots]

    def evaluate_alert_rules(self, component_id: str, metrics: List[MetricData]) -> List[AlertRule]:
        """Evaluate alert rules against component metrics"""
        triggered_rules = []

        for rule in self.alert_rules.values():
            if not rule.enabled:
                continue

            # Check cooldown period
            last_trigger = self.last_alert_times.get(f"{component_id}_{rule.rule_id}")
            if last_trigger and (datetime.now(timezone.utc) - last_trigger).total_seconds() < rule.cooldown_period:
                continue

            # Evaluate rule condition
            if self._evaluate_rule_condition(rule.condition, metrics):
                triggered_rules.append(rule)
                self.last_alert_times[f"{component_id}_{rule.rule_id}"] = datetime.now(timezone.utc)

        return triggered_rules

    def _evaluate_rule_condition(self, condition: Dict[str, Any], metrics: List[MetricData]) -> bool:
        """Evaluate a single alert rule condition"""
        metric_name = condition.get("metric")
        operator = condition.get("operator")
        threshold = condition.get("threshold")

        if not metric_name or not operator or threshold is None:
            return False

        # Find matching metric
        metric_value = None
        for metric in metrics:
            if metric.name == metric_name:
                metric_value = metric.value
                break

        if metric_value is None:
            return False

        # Evaluate condition
        if operator == ">":
            return metric_value > threshold
        elif operator == "<":
            return metric_value < threshold
        elif operator == ">=":
            return metric_value >= threshold
        elif operator == "<=":
            return metric_value <= threshold
        elif operator == "==":
            return metric_value == threshold

        return False

    def get_advanced_monitoring_stats(self) -> Dict[str, Any]:
        """Get comprehensive monitoring statistics"""
        base_stats = self.get_monitoring_stats()

        # Add advanced metrics
        total_snapshots = len(self.system_snapshots)
        total_predictive_insights = sum(len(insights) for insights in self.predictive_insights.values())
        active_alert_rules = len([r for r in self.alert_rules.values() if r.enabled])

        # Calculate prediction accuracy (placeholder)
        prediction_accuracy = 85.0  # Would be calculated from historical predictions

        # Cross-component analysis stats
        correlation_pairs = len([
            pair for pair in self.correlation_matrix.values()
            for corr in pair.values() if abs(corr) > 0.7
        ])

        return {
            **base_stats,
            "total_snapshots": total_snapshots,
            "total_predictive_insights": total_predictive_insights,
            "active_alert_rules": active_alert_rules,
            "prediction_accuracy": prediction_accuracy,
            "cross_component_correlations": correlation_pairs,
            "monitoring_coverage": self._calculate_monitoring_coverage()
        }

    def _calculate_monitoring_coverage(self) -> float:
        """Calculate monitoring coverage percentage"""
        if not self.system.components:
            return 100.0

        monitored_components = len([
            c_id for c_id, history in self.health_history.items()
            if len(history) > 0
        ])

        return (monitored_components / len(self.system.components)) * 100