"""
Enhanced Security Module for Ultra Pinnacle AI Studio
Advanced security hardening with encryption, audit logging, and threat detection
"""

import os
import time
import hashlib
import hmac
import secrets
import base64
import json
import re
import ipaddress
from typing import Dict, List, Optional, Tuple, Set
from datetime import datetime, timedelta
from functools import wraps
from fastapi import Request, HTTPException, Depends
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
import logging
import threading
from collections import defaultdict, deque
import cryptography
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC

logger = logging.getLogger("ultra_pinnacle")

class EncryptionManager:
    """Handle encryption/decryption operations"""
    
    def __init__(self, key: Optional[bytes] = None):
        if key is None:
            # Generate a key (in production, load from secure storage)
            key = Fernet.generate_key()
        self.fernet = Fernet(key)
    
    def encrypt(self, data: str) -> str:
        """Encrypt string data"""
        return self.fernet.encrypt(data.encode()).decode()
    
    def decrypt(self, encrypted_data: str) -> str:
        """Decrypt string data"""
        return self.fernet.decrypt(encrypted_data.encode()).decode()
    
    def encrypt_dict(self, data: dict) -> str:
        """Encrypt dictionary data"""
        json_data = json.dumps(data)
        return self.encrypt(json_data)
    
    def decrypt_dict(self, encrypted_data: str) -> dict:
        """Decrypt dictionary data"""
        json_data = self.decrypt(encrypted_data)
        return json.loads(json_data)

class AdvancedRateLimiter:
    """Advanced rate limiter with multiple strategies"""
    
    def __init__(self):
        self.requests: Dict[str, deque] = defaultdict(lambda: deque(maxlen=1000))
        self.blocked_ips: Set[str] = set()
        self.suspicious_ips: Dict[str, int] = defaultdict(int)
        self.lock = threading.Lock()
    
    def is_allowed(self, client_ip: str, endpoint: str = "", user_agent: str = "") -> Tuple[bool, str]:
        """Check if request is allowed with advanced logic"""
        with self.lock:
            # Check if IP is blocked
            if client_ip in self.blocked_ips:
                return False, "IP blocked due to suspicious activity"
            
            current_time = time.time()
            window_1min = current_time - 60
            window_10min = current_time - 600
            
            # Clean old requests
            self.requests[client_ip] = deque(
                (t for t in self.requests[client_ip] if t > window_10min),
                maxlen=1000
            )
            
            requests_1min = sum(1 for t in self.requests[client_ip] if t > window_1min)
            requests_10min = len(self.requests[client_ip])
            
            # Rate limiting rules
            if requests_1min > 30:  # 30 requests per minute
                self._block_ip(client_ip, "High frequency requests")
                return False, "Rate limit exceeded (per minute)"
            
            if requests_10min > 200:  # 200 requests per 10 minutes
                self._block_ip(client_ip, "High volume requests")
                return False, "Rate limit exceeded (per 10 minutes)"
            
            # Suspicious activity detection
            if self._is_suspicious_request(endpoint, user_agent):
                self.suspicious_ips[client_ip] += 1
                if self.suspicious_ips[client_ip] > 5:
                    self._block_ip(client_ip, "Suspicious activity detected")
                    return False, "Suspicious activity detected"
            
            # Record request
            self.requests[client_ip].append(current_time)
            return True, ""
    
    def _is_suspicious_request(self, endpoint: str, user_agent: str) -> bool:
        """Detect suspicious request patterns"""
        suspicious_patterns = [
            r'\.env',
            r'wp-admin',
            r'phpmyadmin',
            r'adminer',
            r'\.\./',
            r'%2e%2e%2f',  # URL encoded ../
            r'<script',
            r'union.*select',
            r';\s*drop',
        ]
        
        check_string = f"{endpoint} {user_agent}".lower()
        
        for pattern in suspicious_patterns:
            if re.search(pattern, check_string, re.IGNORECASE):
                return True
        
        return False
    
    def _block_ip(self, ip: str, reason: str):
        """Block an IP address"""
        self.blocked_ips.add(ip)
        logger.warning(f"Blocked IP {ip}: {reason}")
        
        # Auto-unblock after 1 hour
        def unblock():
            time.sleep(3600)
            self.blocked_ips.discard(ip)
            logger.info(f"Unblocked IP {ip}")
        
        threading.Thread(target=unblock, daemon=True).start()
    
    def get_blocked_ips(self) -> List[str]:
        """Get list of blocked IPs"""
        with self.lock:
            return list(self.blocked_ips)
    
    def unblock_ip(self, ip: str) -> bool:
        """Manually unblock an IP"""
        with self.lock:
            if ip in self.blocked_ips:
                self.blocked_ips.remove(ip)
                logger.info(f"Manually unblocked IP {ip}")
                return True
            return False

class AuditLogger:
    """Comprehensive audit logging"""
    
    def __init__(self):
        self.audit_log = deque(maxlen=10000)  # Keep last 10k entries
        self.lock = threading.Lock()
    
    def log_event(self, event_type: str, user: str = "anonymous", resource: str = "",
                  action: str = "", details: Dict = None, ip: str = "", user_agent: str = ""):
        """Log security event"""
        event = {
            "timestamp": datetime.now().isoformat(),
            "event_type": event_type,
            "user": user,
            "resource": resource,
            "action": action,
            "details": details or {},
            "ip": ip,
            "user_agent": user_agent[:200] if user_agent else "",  # Truncate long UAs
            "severity": self._calculate_severity(event_type)
        }
        
        with self.lock:
            self.audit_log.append(event)
        
        # Log to main logger with appropriate level
        log_method = getattr(logger, event["severity"], logger.info)
        log_method(f"AUDIT: {event_type} - User: {user} - Resource: {resource} - Action: {action}")
    
    def _calculate_severity(self, event_type: str) -> str:
        """Calculate log severity based on event type"""
        critical_events = [
            "authentication_failure", "authorization_failure", "suspicious_activity",
            "security_breach", "data_breach", "privilege_escalation"
        ]
        warning_events = [
            "rate_limit_exceeded", "suspicious_request", "unusual_activity",
            "password_change", "permission_change"
        ]
        
        if event_type in critical_events:
            return "error"
        elif event_type in warning_events:
            return "warning"
        else:
            return "info"
    
    def get_audit_log(self, hours: int = 24, event_type: str = None) -> List[Dict]:
        """Get audit log entries"""
        cutoff_time = datetime.now() - timedelta(hours=hours)
        
        with self.lock:
            filtered_logs = [
                log for log in self.audit_log
                if datetime.fromisoformat(log["timestamp"]) > cutoff_time
            ]
            
            if event_type:
                filtered_logs = [log for log in filtered_logs if log["event_type"] == event_type]
            
            return filtered_logs[-1000:]  # Return last 1000 matching entries
    
    def get_security_summary(self) -> Dict:
        """Get security summary statistics"""
        with self.lock:
            recent_logs = self.get_audit_log(hours=24)
            
            summary = {
                "total_events": len(recent_logs),
                "events_by_type": defaultdict(int),
                "events_by_severity": defaultdict(int),
                "top_ips": defaultdict(int),
                "failed_auth_attempts": 0,
                "suspicious_activities": 0
            }
            
            for log in recent_logs:
                summary["events_by_type"][log["event_type"]] += 1
                summary["events_by_severity"][log["severity"]] += 1
                summary["top_ips"][log["ip"]] += 1
                
                if log["event_type"] == "authentication_failure":
                    summary["failed_auth_attempts"] += 1
                elif log["event_type"] in ["suspicious_activity", "suspicious_request"]:
                    summary["suspicious_activities"] += 1
            
            # Convert defaultdicts to regular dicts
            summary["events_by_type"] = dict(summary["events_by_type"])
            summary["events_by_severity"] = dict(summary["events_by_severity"])
            summary["top_ips"] = dict(sorted(summary["top_ips"].items(), key=lambda x: x[1], reverse=True)[:10])
            
            return summary

# Global instances
encryption_manager = EncryptionManager()
advanced_rate_limiter = AdvancedRateLimiter()
audit_logger = AuditLogger()

logger.info("Enhanced security module initialized")
