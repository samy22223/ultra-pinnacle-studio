#!/usr/bin/env python3
"""
Auto-Healing Service for Ultra Pinnacle Studio
Provides automatic fault detection, recovery, and self-diagnostic capabilities
"""

import os
import sys
import time
import json
import psutil
import requests
import logging
import subprocess
from pathlib import Path
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
import threading
import signal

# Add parent directory to path for imports
sys.path.append(str(Path(__file__).parent.parent))

from api_gateway.config import config
from api_gateway.logging_config import logger

class AutoHealer:
    """Auto-healing service with comprehensive monitoring and recovery"""
    
    def __init__(self, config_path: Optional[str] = None):
        self.config = config
        self.project_root = Path(__file__).parent.parent
        self.logs_dir = self.project_root / "logs"
        self.services_config = self._load_services_config()
        self.health_history = []
        self.recovery_attempts = {}
        self.is_running = False
        self.monitor_thread = None
        
        # Setup logging
        self.logger = logging.getLogger("auto_healer")
        self.logger.setLevel(logging.INFO)
        handler = logging.FileHandler(self.logs_dir / "auto_healer.log")
        handler.setFormatter(logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        ))
        self.logger.addHandler(handler)
    
    def _load_services_config(self) -> Dict[str, Any]:
        """Load service configuration for monitoring"""
        return {
            "backend": {
                "name": "FastAPI Backend",
                "port": 8000,
                "health_endpoint": "http://localhost:8000/health",
                "start_command": ["python", "-m", "uvicorn", "api_gateway.main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"],
                "cwd": str(self.project_root / "api_gateway"),
                "max_restart_attempts": 3,
                "restart_delay": 30,
                "health_check_interval": 30
            },
            "frontend": {
                "name": "React Frontend", 
                "port": 3000,
                "health_endpoint": "http://localhost:3000",
                "start_command": ["npm", "start"],
                "cwd": str(self.project_root / "web_ui"),
                "max_restart_attempts": 3,
                "restart_delay": 15,
                "health_check_interval": 60
            },
            "llama_service": {
                "name": "Llama AI Service",
                "port": 8080,
                "health_endpoint": "http://localhost:8080/health",
                "start_command": ["./start_llama_service.sh"],
                "cwd": str(self.project_root / "ai_runtimes" / "llama_service"),
                "max_restart_attempts": 2,
                "restart_delay": 60,
                "health_check_interval": 120,
                "optional": True
            },
            "stable_diffusion": {
                "name": "Stable Diffusion",
                "port": 7860,
                "health_endpoint": "http://localhost:7860",
                "start_command": ["./start_auto1111.sh"],
                "cwd": str(self.project_root / "ai_runtimes" / "sd_automatic"),
                "max_restart_attempts": 2,
                "restart_delay": 120,
                "health_check_interval": 180,
                "optional": True
            }
        }
    
    def start_monitoring(self):
        """Start the auto-healing monitoring service"""
        self.logger.info("Starting Auto-Healing Service")
        self.is_running = True
        
        # Start monitoring thread
        self.monitor_thread = threading.Thread(target=self._monitor_loop, daemon=True)
        self.monitor_thread.start()
        
        # Setup signal handlers
        signal.signal(signal.SIGTERM, self._signal_handler)
        signal.signal(signal.SIGINT, self._signal_handler)
        
        self.logger.info("Auto-Healing Service started successfully")
    
    def stop_monitoring(self):
        """Stop the auto-healing monitoring service"""
        self.logger.info("Stopping Auto-Healing Service")
        self.is_running = False
        if self.monitor_thread and self.monitor_thread.is_alive():
            self.monitor_thread.join(timeout=5)
        self.logger.info("Auto-Healing Service stopped")
    
    def _signal_handler(self, signum, frame):
        """Handle shutdown signals"""
        self.logger.info(f"Received signal {signum}, shutting down")
        self.stop_monitoring()
    
    def _monitor_loop(self):
        """Main monitoring loop"""
        while self.is_running:
            try:
                self._perform_health_checks()
                self._check_system_resources()
                self._cleanup_old_logs()
                time.sleep(10)  # Check every 10 seconds
            except Exception as e:
                self.logger.error(f"Error in monitoring loop: {e}")
                time.sleep(30)  # Wait longer on error
    
    def _perform_health_checks(self):
        """Perform health checks on all services"""
        for service_name, service_config in self.services_config.items():
            try:
                health_status = self._check_service_health(service_name, service_config)
                self._record_health_status(service_name, health_status)
                
                if not health_status["healthy"]:
                    self._attempt_service_recovery(service_name, service_config, health_status)
                    
            except Exception as e:
                self.logger.error(f"Error checking health for {service_name}: {e}")
    
    def _check_service_health(self, service_name: str, service_config: Dict[str, Any]) -> Dict[str, Any]:
        """Check health of a specific service"""
        health_status = {
            "service": service_name,
            "healthy": False,
            "timestamp": datetime.now().isoformat(),
            "checks": {}
        }
        
        # Check if process is running
        process_running = self._is_process_running(service_name, service_config)
        health_status["checks"]["process"] = {
            "status": "healthy" if process_running else "unhealthy",
            "details": "Process is running" if process_running else "Process not found"
        }
        
        # Check health endpoint if available
        if "health_endpoint" in service_config:
            endpoint_healthy = self._check_health_endpoint(service_config["health_endpoint"])
            health_status["checks"]["endpoint"] = {
                "status": "healthy" if endpoint_healthy else "unhealthy", 
                "details": f"Endpoint {'accessible' if endpoint_healthy else 'not accessible'}"
            }
        else:
            health_status["checks"]["endpoint"] = {
                "status": "not_applicable",
                "details": "No health endpoint configured"
            }
        
        # Check port availability
        port_available = self._is_port_available(service_config["port"])
        health_status["checks"]["port"] = {
            "status": "healthy" if port_available else "unhealthy",
            "details": f"Port {service_config['port']} {'available' if port_available else 'not available'}"
        }
        
        # Overall health determination
        critical_checks = ["process", "port"]
        if "health_endpoint" in service_config:
            critical_checks.append("endpoint")
            
        health_status["healthy"] = all(
            health_status["checks"][check]["status"] == "healthy" 
            for check in critical_checks
        )
        
        return health_status
    
    def _is_process_running(self, service_name: str, service_config: Dict[str, Any]) -> bool:
        """Check if service process is running"""
        try:
            # Check for PID file
            pid_file = self.logs_dir / f"{service_name}.pid"
            if pid_file.exists():
                with open(pid_file, 'r') as f:
                    pid = int(f.read().strip())
                return psutil.pid_exists(pid)
            
            # Fallback: check for processes by port
            for conn in psutil.net_connections():
                if conn.laddr and conn.laddr.port == service_config["port"]:
                    return True
                    
            return False
        except Exception as e:
            self.logger.error(f"Error checking process for {service_name}: {e}")
            return False
    
    def _check_health_endpoint(self, endpoint: str) -> bool:
        """Check if health endpoint is accessible"""
        try:
            response = requests.get(endpoint, timeout=5)
            return response.status_code == 200
        except:
            return False
    
    def _is_port_available(self, port: int) -> bool:
        """Check if port is available"""
        try:
            for conn in psutil.net_connections():
                if conn.laddr and conn.laddr.port == port:
                    return True
            return False
        except:
            return False
    
    def _record_health_status(self, service_name: str, health_status: Dict[str, Any]):
        """Record health status for monitoring"""
        self.health_history.append(health_status)
        
        # Keep only last 1000 records
        if len(self.health_history) > 1000:
            self.health_history = self.health_history[-1000:]
        
        # Log unhealthy services
        if not health_status["healthy"]:
            self.logger.warning(f"Service {service_name} is unhealthy: {health_status}")
    
    def _attempt_service_recovery(self, service_name: str, service_config: Dict[str, Any], health_status: Dict[str, Any]):
        """Attempt to recover an unhealthy service"""
        # Check recovery attempt limits
        if service_name not in self.recovery_attempts:
            self.recovery_attempts[service_name] = []
        
        recent_attempts = [
            attempt for attempt in self.recovery_attempts[service_name]
            if attempt > datetime.now() - timedelta(hours=1)
        ]
        
        if len(recent_attempts) >= service_config["max_restart_attempts"]:
            self.logger.error(f"Max restart attempts reached for {service_name}")
            return
        
        # Check if service is optional and should be skipped
        if service_config.get("optional", False):
            # Only attempt recovery if the service was previously running
            if not self._was_service_recently_healthy(service_name):
                self.logger.info(f"Skipping recovery for optional service {service_name}")
                return
        
        self.logger.info(f"Attempting recovery for service {service_name}")
        
        # Kill existing process if running
        self._kill_service_process(service_name, service_config)
        
        # Wait before restart
        time.sleep(service_config["restart_delay"])
        
        # Start service
        success = self._start_service(service_name, service_config)
        
        if success:
            self.logger.info(f"Successfully recovered service {service_name}")
            self.recovery_attempts[service_name].append(datetime.now())
        else:
            self.logger.error(f"Failed to recover service {service_name}")
    
    def _was_service_recently_healthy(self, service_name: str, hours: int = 24) -> bool:
        """Check if service was healthy recently"""
        cutoff = datetime.now() - timedelta(hours=hours)
        recent_health = [
            h for h in self.health_history
            if h["service"] == service_name and 
            datetime.fromisoformat(h["timestamp"]) > cutoff
        ]
        return any(h["healthy"] for h in recent_health)
    
    def _kill_service_process(self, service_name: str, service_config: Dict[str, Any]):
        """Kill existing service process"""
        try:
            pid_file = self.logs_dir / f"{service_name}.pid"
            if pid_file.exists():
                with open(pid_file, 'r') as f:
                    pid = int(f.read().strip())
                if psutil.pid_exists(pid):
                    process = psutil.Process(pid)
                    process.terminate()
                    process.wait(timeout=10)
                    self.logger.info(f"Killed process {pid} for {service_name}")
                pid_file.unlink()
        except Exception as e:
            self.logger.error(f"Error killing process for {service_name}: {e}")
    
    def _start_service(self, service_name: str, service_config: Dict[str, Any]) -> bool:
        """Start a service"""
        try:
            self.logger.info(f"Starting service {service_name}")
            
            # Create log file
            log_file = self.logs_dir / f"{service_name}.log"
            
            with open(log_file, 'a') as log:
                process = subprocess.Popen(
                    service_config["start_command"],
                    cwd=service_config["cwd"],
                    stdout=log,
                    stderr=log,
                    preexec_fn=os.setsid if os.name != 'nt' else None
                )
            
            # Save PID
            pid_file = self.logs_dir / f"{service_name}.pid"
            with open(pid_file, 'w') as f:
                f.write(str(process.pid))
            
            # Wait a bit for service to start
            time.sleep(5)
            
            # Verify service started
            if self._is_process_running(service_name, service_config):
                self.logger.info(f"Service {service_name} started successfully")
                return True
            else:
                self.logger.error(f"Service {service_name} failed to start")
                return False
                
        except Exception as e:
            self.logger.error(f"Error starting service {service_name}: {e}")
            return False
    
    def _check_system_resources(self):
        """Check system resource usage"""
        try:
            cpu_percent = psutil.cpu_percent(interval=1)
            memory = psutil.virtual_memory()
            disk = psutil.disk_usage('/')
            
            # Log warnings for high resource usage
            if cpu_percent > 90:
                self.logger.warning(f"High CPU usage: {cpu_percent}%")
            if memory.percent > 90:
                self.logger.warning(f"High memory usage: {memory.percent}%")
            if disk.percent > 90:
                self.logger.warning(f"Low disk space: {disk.percent}% used")
                
        except Exception as e:
            self.logger.error(f"Error checking system resources: {e}")
    
    def _cleanup_old_logs(self):
        """Clean up old log files"""
        try:
            # Remove logs older than 30 days
            cutoff = datetime.now() - timedelta(days=30)
            for log_file in self.logs_dir.glob("*.log"):
                if log_file.stat().st_mtime < cutoff.timestamp():
                    log_file.unlink()
                    self.logger.info(f"Removed old log file: {log_file}")
                    
        except Exception as e:
            self.logger.error(f"Error cleaning up logs: {e}")
    
    def get_health_report(self) -> Dict[str, Any]:
        """Get comprehensive health report"""
        report = {
            "timestamp": datetime.now().isoformat(),
            "services": {},
            "system_resources": {},
            "recovery_stats": self.recovery_attempts.copy()
        }
        
        # Service health
        for service_name, service_config in self.services_config.items():
            recent_health = [
                h for h in self.health_history[-10:]  # Last 10 checks
                if h["service"] == service_name
            ]
            if recent_health:
                latest = recent_health[-1]
                report["services"][service_name] = {
                    "name": service_config["name"],
                    "healthy": latest["healthy"],
                    "last_check": latest["timestamp"],
                    "uptime_percent": sum(1 for h in recent_health if h["healthy"]) / len(recent_health) * 100
                }
        
        # System resources
        try:
            cpu_percent = psutil.cpu_percent()
            memory = psutil.virtual_memory()
            disk = psutil.disk_usage('/')
            
            report["system_resources"] = {
                "cpu_percent": cpu_percent,
                "memory_percent": memory.percent,
                "memory_used_gb": memory.used / (1024**3),
                "memory_total_gb": memory.total / (1024**3),
                "disk_percent": disk.percent,
                "disk_used_gb": disk.used / (1024**3),
                "disk_total_gb": disk.total / (1024**3)
            }
        except Exception as e:
            self.logger.error(f"Error getting system resources: {e}")
        
        return report
    
    def force_restart_service(self, service_name: str) -> bool:
        """Force restart a specific service"""
        if service_name not in self.services_config:
            return False
        
        service_config = self.services_config[service_name]
        self.logger.info(f"Forcing restart of service {service_name}")
        
        self._kill_service_process(service_name, service_config)
        time.sleep(5)
        return self._start_service(service_name, service_config)


def main():
    """Main entry point"""
    healer = AutoHealer()
    
    try:
        healer.start_monitoring()
        
        # Keep running until interrupted
        while healer.is_running:
            time.sleep(1)
            
    except KeyboardInterrupt:
        pass
    finally:
        healer.stop_monitoring()


if __name__ == "__main__":
    main()
