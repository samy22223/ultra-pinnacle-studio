"""
Scalability Module for Ultra Pinnacle AI Studio
Load balancing, horizontal scaling, and auto-scaling capabilities
"""

import os
import time
import asyncio
import threading
from typing import Dict, List, Optional, Any, Callable
from datetime import datetime, timedelta
import json
import hashlib
import random
import statistics
from concurrent.futures import ThreadPoolExecutor
import psutil

from .logging_config import logger

class LoadBalancer:
    """Load balancer with multiple strategies"""
    
    def __init__(self):
        self.backends = {}  # service_name -> list of instances
        self.health_checks = {}  # instance -> health status
        self.metrics = {}  # instance -> performance metrics
        self.lock = threading.Lock()
    
    def add_backend(self, service_name: str, instance_url: str, weight: int = 1):
        """Add backend instance"""
        with self.lock:
            if service_name not in self.backends:
                self.backends[service_name] = []
            self.backends[service_name].append({
                "url": instance_url,
                "weight": weight,
                "active": True,
                "connections": 0,
                "last_health_check": 0
            })
            logger.info(f"Added backend {instance_url} for service {service_name}")
    
    def remove_backend(self, service_name: str, instance_url: str):
        """Remove backend instance"""
        with self.lock:
            if service_name in self.backends:
                self.backends[service_name] = [
                    b for b in self.backends[service_name]
                    if b["url"] != instance_url
                ]
                logger.info(f"Removed backend {instance_url} for service {service_name}")
    
    def get_backend(self, service_name: str, strategy: str = "round_robin") -> Optional[str]:
        """Get next backend using specified strategy"""
        with self.lock:
            if service_name not in self.backends:
                return None
            
            active_backends = [b for b in self.backends[service_name] if b["active"]]
            if not active_backends:
                return None
            
            if strategy == "round_robin":
                return self._round_robin(service_name, active_backends)
            elif strategy == "least_connections":
                return self._least_connections(active_backends)
            elif strategy == "weighted":
                return self._weighted(active_backends)
            elif strategy == "random":
                return random.choice(active_backends)["url"]
            else:
                return active_backends[0]["url"]
    
    def _round_robin(self, service_name: str, backends: List[Dict]) -> str:
        """Round-robin load balancing"""
        # Simple round-robin using a counter
        if not hasattr(self, f"_rr_counter_{service_name}"):
            setattr(self, f"_rr_counter_{service_name}", 0)
        
        counter = getattr(self, f"_rr_counter_{service_name}")
        backend = backends[counter % len(backends)]
        setattr(self, f"_rr_counter_{service_name}", counter + 1)
        return backend["url"]
    
    def _least_connections(self, backends: List[Dict]) -> str:
        """Least connections load balancing"""
        return min(backends, key=lambda b: b["connections"])["url"]
    
    def _weighted(self, backends: List[Dict]) -> str:
        """Weighted load balancing"""
        total_weight = sum(b["weight"] for b in backends)
        rand = random.uniform(0, total_weight)
        
        current_weight = 0
        for backend in backends:
            current_weight += backend["weight"]
            if rand <= current_weight:
                return backend["url"]
        
        return backends[0]["url"]
    
    def update_connection_count(self, instance_url: str, delta: int):
        """Update connection count for instance"""
        with self.lock:
            for service_backends in self.backends.values():
                for backend in service_backends:
                    if backend["url"] == instance_url:
                        backend["connections"] = max(0, backend["connections"] + delta)
                        break
    
    def mark_unhealthy(self, instance_url: str):
        """Mark instance as unhealthy"""
        with self.lock:
            for service_backends in self.backends.values():
                for backend in service_backends:
                    if backend["url"] == instance_url:
                        backend["active"] = False
                        logger.warning(f"Marked backend {instance_url} as unhealthy")
                        break
    
    def mark_healthy(self, instance_url: str):
        """Mark instance as healthy"""
        with self.lock:
            for service_backends in self.backends.values():
                for backend in service_backends:
                    if backend["url"] == instance_url:
                        backend["active"] = True
                        logger.info(f"Marked backend {instance_url} as healthy")
                        break

class AutoScaler:
    """Auto-scaling manager"""
    
    def __init__(self, min_instances: int = 1, max_instances: int = 10):
        self.min_instances = min_instances
        self.max_instances = max_instances
        self.current_instances = min_instances
        self.cpu_threshold_high = 70.0
        self.cpu_threshold_low = 30.0
        self.memory_threshold_high = 80.0
        self.memory_threshold_low = 40.0
        self.scale_up_cooldown = 300  # 5 minutes
        self.scale_down_cooldown = 600  # 10 minutes
        self.last_scale_up = 0
        self.last_scale_down = 0
        self.monitoring = False
    
    def start_monitoring(self):
        """Start auto-scaling monitoring"""
        self.monitoring = True
        monitor_thread = threading.Thread(target=self._monitor_loop, daemon=True)
        monitor_thread.start()
        logger.info("Auto-scaling monitoring started")
    
    def stop_monitoring(self):
        """Stop auto-scaling monitoring"""
        self.monitoring = False
    
    def _monitor_loop(self):
        """Monitor system and scale as needed"""
        while self.monitoring:
            try:
                self._check_scaling_conditions()
            except Exception as e:
                logger.error(f"Auto-scaling error: {e}")
            time.sleep(60)  # Check every minute
    
    def _check_scaling_conditions(self):
        """Check if scaling is needed"""
        current_time = time.time()
        
        # Get system metrics
        cpu_percent = psutil.cpu_percent(interval=5)
        memory_percent = psutil.virtual_memory().percent
        
        # Scale up conditions
        if (cpu_percent > self.cpu_threshold_high or memory_percent > self.memory_threshold_high):
            if (current_time - self.last_scale_up > self.scale_up_cooldown and 
                self.current_instances < self.max_instances):
                self._scale_up()
                self.last_scale_up = current_time
        
        # Scale down conditions
        elif (cpu_percent < self.cpu_threshold_low and memory_percent < self.memory_threshold_low):
            if (current_time - self.last_scale_down > self.scale_down_cooldown and 
                self.current_instances > self.min_instances):
                self._scale_down()
                self.last_scale_down = current_time
    
    def _scale_up(self):
        """Scale up by adding instances"""
        self.current_instances += 1
        logger.info(f"Scaling up to {self.current_instances} instances")
        
        # TODO: Implement actual instance creation
        # This would integrate with container orchestration (Docker, Kubernetes)
    
    def _scale_down(self):
        """Scale down by removing instances"""
        self.current_instances -= 1
        logger.info(f"Scaling down to {self.current_instances} instances")
        
        # TODO: Implement actual instance removal
        # This would integrate with container orchestration
    
    def get_scaling_status(self) -> Dict[str, Any]:
        """Get current scaling status"""
        return {
            "current_instances": self.current_instances,
            "min_instances": self.min_instances,
            "max_instances": self.max_instances,
            "cpu_threshold_high": self.cpu_threshold_high,
            "cpu_threshold_low": self.cpu_threshold_low,
            "memory_threshold_high": self.memory_threshold_high,
            "memory_threshold_low": self.memory_threshold_low,
            "last_scale_up": datetime.fromtimestamp(self.last_scale_up).isoformat() if self.last_scale_up else None,
            "last_scale_down": datetime.fromtimestamp(self.last_scale_down).isoformat() if self.last_scale_down else None
        }

# Global instances
load_balancer = LoadBalancer()
auto_scaler = AutoScaler()

# Start auto-scaling
auto_scaler.start_monitoring()

logger.info("Scalability module initialized")
