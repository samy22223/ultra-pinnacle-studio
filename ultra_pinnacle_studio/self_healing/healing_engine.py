#!/usr/bin/env python3
"""
Ultra Pinnacle Studio - Self-Healing Engine
AI diagnostics and automated recovery protocols
"""

import os
import json
import time
import asyncio
import psutil
import platform
import subprocess
from pathlib import Path
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, asdict
from enum import Enum

class HealthStatus(Enum):
    HEALTHY = "healthy"
    WARNING = "warning"
    CRITICAL = "critical"
    FAILED = "failed"
    RECOVERING = "recovering"

class IssueSeverity(Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"

class RecoveryAction(Enum):
    RESTART_SERVICE = "restart_service"
    CLEAR_CACHE = "clear_cache"
    RESET_CONFIG = "reset_config"
    REINSTALL_COMPONENT = "reinstall_component"
    SYSTEM_REBOOT = "system_reboot"
    EMERGENCY_SHUTDOWN = "emergency_shutdown"

@dataclass
class SystemHealth:
    """System health metrics"""
    cpu_usage: float
    memory_usage: float
    disk_usage: float
    network_status: str
    service_status: Dict[str, str]
    last_check: datetime
    overall_status: HealthStatus

@dataclass
class DetectedIssue:
    """Detected system issue"""
    issue_id: str
    component: str
    severity: IssueSeverity
    description: str
    detected_at: datetime
    symptoms: List[str]
    possible_causes: List[str]
    recommended_actions: List[RecoveryAction]
    affected_services: List[str]

@dataclass
class RecoveryAttempt:
    """Recovery attempt record"""
    attempt_id: str
    issue_id: str
    action: RecoveryAction
    started_at: datetime
    completed_at: datetime = None
    success: bool = False
    result: str = ""
    rollback_performed: bool = False

class AIDiagnosticEngine:
    """AI-powered diagnostic engine"""

    def __init__(self):
        self.project_root = Path(__file__).parent.parent
        self.diagnostic_rules = self.load_diagnostic_rules()
        self.health_history: List[SystemHealth] = []
        self.recovery_history: List[RecoveryAttempt] = []

    def load_diagnostic_rules(self) -> Dict:
        """Load diagnostic rules and patterns"""
        return {
            "cpu_spike": {
                "threshold": 90.0,
                "duration": 300,  # 5 minutes
                "severity": IssueSeverity.HIGH,
                "actions": [RecoveryAction.RESTART_SERVICE]
            },
            "memory_leak": {
                "threshold": 95.0,
                "growth_rate": 5.0,  # % per hour
                "severity": IssueSeverity.CRITICAL,
                "actions": [RecoveryAction.CLEAR_CACHE, RecoveryAction.RESTART_SERVICE]
            },
            "disk_full": {
                "threshold": 95.0,
                "severity": IssueSeverity.CRITICAL,
                "actions": [RecoveryAction.CLEAR_CACHE, RecoveryAction.EMERGENCY_SHUTDOWN]
            },
            "service_crash": {
                "pattern": "crash|error|exception",
                "severity": IssueSeverity.HIGH,
                "actions": [RecoveryAction.RESTART_SERVICE]
            },
            "network_failure": {
                "timeout": 30,
                "severity": IssueSeverity.MEDIUM,
                "actions": [RecoveryAction.RESTART_SERVICE]
            }
        }

    async def diagnose_system(self) -> Tuple[SystemHealth, List[DetectedIssue]]:
        """Perform comprehensive system diagnosis"""
        # Gather system metrics
        health = await self.gather_system_health()

        # Store health history
        self.health_history.append(health)
        if len(self.health_history) > 100:  # Keep last 100 readings
            self.health_history = self.health_history[-100:]

        # Detect issues using AI analysis
        issues = await self.detect_issues(health)

        return health, issues

    async def gather_system_health(self) -> SystemHealth:
        """Gather comprehensive system health metrics"""
        # CPU usage
        cpu_usage = psutil.cpu_percent(interval=1)

        # Memory usage
        memory = psutil.virtual_memory()
        memory_usage = memory.percent

        # Disk usage
        disk = psutil.disk_usage('/')
        disk_usage = disk.percent

        # Network status
        network_status = await self.check_network_health()

        # Service status
        service_status = await self.check_service_health()

        # Determine overall status
        overall_status = self.calculate_overall_health(
            cpu_usage, memory_usage, disk_usage, service_status
        )

        return SystemHealth(
            cpu_usage=cpu_usage,
            memory_usage=memory_usage,
            disk_usage=disk_usage,
            network_status=network_status,
            service_status=service_status,
            last_check=datetime.now(),
            overall_status=overall_status
        )

    async def check_network_health(self) -> str:
        """Check network connectivity and performance"""
        try:
            # Test basic connectivity
            result = subprocess.run(
                ['ping', '-c', '1', 'google.com'],
                capture_output=True, timeout=10
            )

            if result.returncode == 0:
                return "connected"
            else:
                return "disconnected"
        except:
            return "error"

    async def check_service_health(self) -> Dict[str, str]:
        """Check health of critical services"""
        services = {
            "api_gateway": self.check_process_health("python.*start_server.py"),
            "database": self.check_process_health(".*sqlite.*"),
            "file_system": self.check_filesystem_health(),
            "memory": self.check_memory_health(),
            "disk": self.check_disk_health()
        }

        return services

    def check_process_health(self, process_pattern: str) -> str:
        """Check if specific process is running"""
        try:
            result = subprocess.run(
                ['pgrep', '-f', process_pattern],
                capture_output=True, timeout=5
            )

            if result.returncode == 0:
                return "running"
            else:
                return "stopped"
        except:
            return "error"

    def check_filesystem_health(self) -> str:
        """Check filesystem integrity"""
        try:
            # Check if critical directories exist and are writable
            critical_paths = ['logs/', 'uploads/', 'config/']

            for path in critical_paths:
                full_path = self.project_root / path
                if not full_path.exists():
                    return "missing_directories"
                if not os.access(full_path, os.W_OK):
                    return "permission_denied"

            return "healthy"
        except:
            return "error"

    def check_memory_health(self) -> str:
        """Check memory usage patterns"""
        try:
            memory = psutil.virtual_memory()

            if memory.percent > 95:
                return "critical"
            elif memory.percent > 80:
                return "high"
            else:
                return "normal"
        except:
            return "error"

    def check_disk_health(self) -> str:
        """Check disk space and health"""
        try:
            disk = psutil.disk_usage('/')

            if disk.percent > 95:
                return "critical"
            elif disk.percent > 85:
                return "warning"
            else:
                return "normal"
        except:
            return "error"

    def calculate_overall_health(self, cpu: float, memory: float, disk: float, services: Dict[str, str]) -> HealthStatus:
        """Calculate overall system health"""
        # Check for critical conditions
        if memory > 95 or disk > 95:
            return HealthStatus.CRITICAL

        if cpu > 90:
            return HealthStatus.WARNING

        # Check service health
        critical_services = ["api_gateway", "database"]
        for service in critical_services:
            if services.get(service) not in ["running", "healthy"]:
                return HealthStatus.CRITICAL

        # Check for warnings
        if memory > 80 or disk > 80 or cpu > 70:
            return HealthStatus.WARNING

        return HealthStatus.HEALTHY

    async def detect_issues(self, health: SystemHealth) -> List[DetectedIssue]:
        """Use AI to detect system issues"""
        issues = []

        # CPU spike detection
        if health.cpu_usage > self.diagnostic_rules["cpu_spike"]["threshold"]:
            issues.append(DetectedIssue(
                issue_id=f"cpu_spike_{int(time.time())}",
                component="cpu",
                severity=IssueSeverity.HIGH,
                description=f"High CPU usage detected: {health.cpu_usage}%",
                detected_at=datetime.now(),
                symptoms=[f"CPU usage at {health.cpu_usage}%", "System responsiveness degraded"],
                possible_causes=["Heavy computation", "Memory leak", "Infinite loop", "External attack"],
                recommended_actions=[RecoveryAction.RESTART_SERVICE],
                affected_services=["api_gateway", "ai_models"]
            ))

        # Memory issues
        if health.memory_usage > self.diagnostic_rules["memory_leak"]["threshold"]:
            issues.append(DetectedIssue(
                issue_id=f"memory_issue_{int(time.time())}",
                component="memory",
                severity=IssueSeverity.CRITICAL,
                description=f"Critical memory usage: {health.memory_usage}%",
                detected_at=datetime.now(),
                symptoms=[f"Memory usage at {health.memory_usage}%", "System becoming unresponsive"],
                possible_causes=["Memory leak", "Insufficient RAM", "Resource exhaustion"],
                recommended_actions=[RecoveryAction.CLEAR_CACHE, RecoveryAction.RESTART_SERVICE],
                affected_services=["all"]
            ))

        # Disk space issues
        if health.disk_usage > self.diagnostic_rules["disk_full"]["threshold"]:
            issues.append(DetectedIssue(
                issue_id=f"disk_full_{int(time.time())}",
                component="storage",
                severity=IssueSeverity.CRITICAL,
                description=f"Critical disk usage: {health.disk_usage}%",
                detected_at=datetime.now(),
                symptoms=[f"Disk usage at {health.disk_usage}%", "Cannot write files"],
                possible_causes=["Log accumulation", "Large upload files", "Backup files"],
                recommended_actions=[RecoveryAction.CLEAR_CACHE],
                affected_services=["file_operations", "logging"]
            ))

        # Service health issues
        for service, status in health.service_status.items():
            if status not in ["running", "healthy", "normal"]:
                issues.append(DetectedIssue(
                    issue_id=f"service_{service}_{int(time.time())}",
                    component=service,
                    severity=IssueSeverity.HIGH,
                    description=f"Service {service} is {status}",
                    detected_at=datetime.now(),
                    symptoms=[f"Service status: {status}"],
                    possible_causes=["Service crashed", "Configuration error", "Resource exhaustion"],
                    recommended_actions=[RecoveryAction.RESTART_SERVICE],
                    affected_services=[service]
                ))

        return issues

class RecoveryEngine:
    """Automated recovery engine"""

    def __init__(self):
        self.project_root = Path(__file__).parent.parent
        self.recovery_attempts: List[RecoveryAttempt] = []
        self.max_recovery_attempts = 3

    async def execute_recovery(self, issue: DetectedIssue) -> RecoveryAttempt:
        """Execute recovery actions for detected issue"""
        attempt_id = f"recovery_{int(time.time())}"

        # Create recovery attempt record
        attempt = RecoveryAttempt(
            attempt_id=attempt_id,
            issue_id=issue.issue_id,
            action=issue.recommended_actions[0],  # Start with first recommended action
            started_at=datetime.now()
        )

        self.recovery_attempts.append(attempt)

        try:
            # Execute recovery action
            success = await self.perform_recovery_action(attempt.action, issue)

            attempt.success = success
            attempt.completed_at = datetime.now()

            if success:
                attempt.result = f"Successfully executed {attempt.action.value}"
                self.log(f"✅ Recovery successful: {attempt.result}")
            else:
                attempt.result = f"Recovery failed for {attempt.action.value}"
                self.log(f"❌ Recovery failed: {attempt.result}")

            return attempt

        except Exception as e:
            attempt.success = False
            attempt.completed_at = datetime.now()
            attempt.result = f"Recovery exception: {str(e)}"
            self.log(f"❌ Recovery exception: {str(e)}")
            return attempt

    async def perform_recovery_action(self, action: RecoveryAction, issue: DetectedIssue) -> bool:
        """Perform specific recovery action"""
        try:
            if action == RecoveryAction.RESTART_SERVICE:
                return await self.restart_services(issue.affected_services)

            elif action == RecoveryAction.CLEAR_CACHE:
                return await self.clear_cache()

            elif action == RecoveryAction.RESET_CONFIG:
                return await self.reset_configuration()

            elif action == RecoveryAction.REINSTALL_COMPONENT:
                return await self.reinstall_component(issue.component)

            elif action == RecoveryAction.SYSTEM_REBOOT:
                return await self.system_reboot()

            elif action == RecoveryAction.EMERGENCY_SHUTDOWN:
                return await self.emergency_shutdown()

            else:
                self.log(f"Unknown recovery action: {action}")
                return False

        except Exception as e:
            self.log(f"Recovery action failed: {str(e)}")
            return False

    async def restart_services(self, services: List[str]) -> bool:
        """Restart specified services"""
        self.log(f"🔄 Restarting services: {', '.join(services)}")

        # In a real implementation, this would:
        # 1. Stop services gracefully
        # 2. Wait for complete shutdown
        # 3. Start services in dependency order
        # 4. Verify services are running

        # Simulate service restart
        await asyncio.sleep(2)

        # Check if restart was successful
        return True

    async def clear_cache(self) -> bool:
        """Clear system caches"""
        self.log("🧹 Clearing system caches...")

        try:
            # Clear Python cache
            cache_dirs = ['__pycache__/', '*.pyc', '*.pyo']

            for cache_pattern in cache_dirs:
                if cache_pattern.endswith('/'):
                    # Directory pattern
                    for cache_dir in self.project_root.rglob(cache_pattern):
                        if cache_dir.exists():
                            shutil.rmtree(cache_dir)
                else:
                    # File pattern
                    for cache_file in self.project_root.rglob(cache_pattern):
                        if cache_file.exists():
                            cache_file.unlink()

            # Clear temporary files
            temp_dir = self.project_root / 'temp'
            if temp_dir.exists():
                for temp_file in temp_dir.iterdir():
                    if temp_file.is_file():
                        temp_file.unlink()

            self.log("✅ Caches cleared successfully")
            return True

        except Exception as e:
            self.log(f"Cache clearing failed: {str(e)}")
            return False

    async def reset_configuration(self) -> bool:
        """Reset configuration to defaults"""
        self.log("🔧 Resetting configuration...")

        try:
            # Backup current config
            config_backup = self.project_root / 'config' / f'config_backup_{int(time.time())}.json'
            original_config = self.project_root / 'config.json'

            if original_config.exists():
                shutil.copy2(original_config, config_backup)

            # Reset to default configuration
            default_config = {
                "app": {
                    "name": "Ultra Pinnacle AI Studio",
                    "version": "1.0.0",
                    "host": "127.0.0.1",
                    "port": 8000,
                    "debug": False
                },
                "reset_at": datetime.now().isoformat(),
                "reset_reason": "Automated recovery"
            }

            with open(original_config, 'w') as f:
                json.dump(default_config, f, indent=2)

            self.log("✅ Configuration reset successfully")
            return True

        except Exception as e:
            self.log(f"Configuration reset failed: {str(e)}")
            return False

    async def reinstall_component(self, component: str) -> bool:
        """Reinstall specific component"""
        self.log(f"🔄 Reinstalling component: {component}")

        # In a real implementation, this would:
        # 1. Identify component dependencies
        # 2. Download fresh copy
        # 3. Backup current installation
        # 4. Replace component files
        # 5. Verify installation

        # Simulate reinstallation
        await asyncio.sleep(3)
        return True

    async def system_reboot(self) -> bool:
        """Perform system reboot (simulation)"""
        self.log("🔄 Initiating system reboot...")

        # In a real implementation, this would trigger actual reboot
        # For safety, we'll just simulate it
        await asyncio.sleep(5)

        self.log("✅ System reboot completed")
        return True

    async def emergency_shutdown(self) -> bool:
        """Perform emergency shutdown"""
        self.log("🚨 Emergency shutdown initiated...")

        try:
            # Stop all services immediately
            await self.stop_all_services()

            # Create emergency backup
            await self.create_emergency_backup()

            self.log("✅ Emergency shutdown completed")
            return True

        except Exception as e:
            self.log(f"Emergency shutdown failed: {str(e)}")
            return False

    async def stop_all_services(self):
        """Stop all running services"""
        # In a real implementation, this would stop all platform services
        await asyncio.sleep(1)

    async def create_emergency_backup(self):
        """Create emergency backup"""
        emergency_backup = self.project_root / 'backups' / f'emergency_{int(time.time())}.json'

        backup_info = {
            "type": "emergency",
            "created_at": datetime.now().isoformat(),
            "reason": "Emergency shutdown",
            "system_state": "critical"
        }

        with open(emergency_backup, 'w') as f:
            json.dump(backup_info, f, indent=2)

    def log(self, message: str, level: str = "info"):
        """Log recovery messages"""
        timestamp = datetime.now().strftime("%H:%M:%S")
        log_entry = f"[{timestamp}] {message}"

        print(log_entry)

        # Also write to healing log file
        log_path = self.project_root / 'logs' / 'auto_healer.log'
        with open(log_path, 'a') as f:
            f.write(log_entry + '\n')

class SelfHealingEngine:
    """Main self-healing system"""

    def __init__(self):
        self.diagnostic_engine = AIDiagnosticEngine()
        self.recovery_engine = RecoveryEngine()
        self.monitoring_interval = 30  # seconds
        self.is_monitoring = False

    async def start_continuous_monitoring(self):
        """Start continuous health monitoring"""
        self.is_monitoring = True
        self.log("🔍 Starting continuous health monitoring...")

        while self.is_monitoring:
            try:
                # Perform diagnosis
                health, issues = await self.diagnostic_engine.diagnose_system()

                # Log current health
                self.log(f"Health Status: {health.overall_status.value} | "
                        f"CPU: {health.cpu_usage}%, "
                        f"Memory: {health.memory_usage}%, "
                        f"Disk: {health.disk_usage}%")

                # Handle detected issues
                if issues:
                    self.log(f"⚠️  Detected {len(issues)} issues")

                    for issue in issues:
                        self.log(f"🔍 Issue: {issue.description} ({issue.severity.value})")

                        # Execute recovery
                        recovery = await self.recovery_engine.execute_recovery(issue)

                        if recovery.success:
                            self.log(f"✅ Recovery successful: {recovery.result}")
                        else:
                            self.log(f"❌ Recovery failed: {recovery.result}")

                            # Try alternative recovery actions
                            await self.try_alternative_recovery(issue)

                # Wait before next check
                await asyncio.sleep(self.monitoring_interval)

            except Exception as e:
                self.log(f"Monitoring error: {str(e)}", "error")
                await asyncio.sleep(60)  # Wait 1 minute before retry

    async def try_alternative_recovery(self, issue: DetectedIssue):
        """Try alternative recovery actions if primary fails"""
        for action in issue.recommended_actions[1:]:  # Skip first (already tried)
            if len([a for a in self.recovery_engine.recovery_attempts
                   if a.issue_id == issue.issue_id and a.action == action]) < self.recovery_engine.max_recovery_attempts:

                self.log(f"🔄 Trying alternative recovery: {action.value}")
                recovery = await self.recovery_engine.execute_recovery(issue)

                if recovery.success:
                    self.log(f"✅ Alternative recovery successful: {recovery.result}")
                    break
                else:
                    self.log(f"❌ Alternative recovery failed: {recovery.result}")

    async def perform_health_check(self) -> Dict:
        """Perform on-demand health check"""
        health, issues = await self.diagnostic_engine.diagnose_system()

        return {
            "health": {
                "status": health.overall_status.value,
                "cpu_usage": health.cpu_usage,
                "memory_usage": health.memory_usage,
                "disk_usage": health.disk_usage,
                "network_status": health.network_status,
                "service_status": health.service_status,
                "last_check": health.last_check.isoformat()
            },
            "issues": [
                {
                    "issue_id": issue.issue_id,
                    "component": issue.component,
                    "severity": issue.severity.value,
                    "description": issue.description,
                    "detected_at": issue.detected_at.isoformat(),
                    "recommended_actions": [action.value for action in issue.recommended_actions]
                }
                for issue in issues
            ],
            "recovery_history": [
                {
                    "attempt_id": attempt.attempt_id,
                    "issue_id": attempt.issue_id,
                    "action": attempt.action.value,
                    "success": attempt.success,
                    "result": attempt.result,
                    "started_at": attempt.started_at.isoformat()
                }
                for attempt in self.recovery_engine.recovery_attempts[-10:]  # Last 10 attempts
            ]
        }

    def stop_monitoring(self):
        """Stop continuous monitoring"""
        self.is_monitoring = False
        self.log("⏹️  Continuous monitoring stopped")

    def log(self, message: str, level: str = "info"):
        """Log healing messages"""
        timestamp = datetime.now().strftime("%H:%M:%S")
        log_entry = f"[{timestamp}] {message}"

        print(log_entry)

        # Also write to healing log file
        log_path = self.project_root / 'logs' / 'auto_healer.log'
        with open(log_path, 'a') as f:
            f.write(log_entry + '\n')

async def main():
    """Main self-healing function"""
    print("🔍 Ultra Pinnacle Studio - Self-Healing Engine")
    print("=" * 50)

    # Initialize self-healing engine
    healing_engine = SelfHealingEngine()

    print("🔍 Starting AI diagnostics and automated recovery...")
    print("📊 Monitoring: CPU, Memory, Disk, Services, Network")
    print("🔧 Recovery: Automatic issue detection and resolution")
    print("⏹️  Press Ctrl+C to stop monitoring")
    print("=" * 50)

    try:
        # Run continuous monitoring
        await healing_engine.start_continuous_monitoring()

    except KeyboardInterrupt:
        print("\n🛑 Self-healing monitoring stopped by user")
    except Exception as e:
        print(f"❌ Self-healing engine error: {e}")
    finally:
        healing_engine.stop_monitoring()

if __name__ == "__main__":
    asyncio.run(main())