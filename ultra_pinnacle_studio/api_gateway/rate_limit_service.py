"""
Rate Limit Service - Loads and manages rate limit configurations from database
"""

import logging
from typing import Dict, Optional
from .database import (
    get_db, UserType, RateLimitConfig, UserRateLimit,
    EndpointRateLimit, RateLimitLog, SystemLoadMetrics
)
from .rate_limiter import get_rate_limit_manager, RateLimitConfig as LimiterConfig
from sqlalchemy.orm import Session

logger = logging.getLogger("ultra_pinnacle")

class RateLimitService:
    """Service for managing rate limit configurations"""

    def __init__(self):
        self.manager = get_rate_limit_manager()
        self._initialized = False

    def initialize_from_database(self, db: Session):
        """Load all rate limit configurations from database"""
        try:
            # Load user type configurations
            user_types = db.query(UserType).filter(UserType.is_active == True).all()
            for user_type in user_types:
                configs = db.query(RateLimitConfig).filter(
                    RateLimitConfig.user_type_id == user_type.id,
                    RateLimitConfig.is_active == True
                ).all()

                for config in configs:
                    limiter_config = LimiterConfig(
                        requests_per_minute=config.requests_per_minute,
                        requests_per_hour=config.requests_per_hour,
                        requests_per_day=config.requests_per_day,
                        burst_limit=config.burst_limit,
                        window_seconds=config.window_seconds
                    )

                    # Load for all users of this type
                    users_of_type = db.query(UserType).filter(UserType.id == user_type.id).first()
                    if users_of_type:
                        # Note: In a real implementation, you'd load users and their specific configs
                        # For now, we'll use a simplified approach
                        pass

            # Load endpoint-specific configurations
            endpoint_limits = db.query(EndpointRateLimit).filter(
                EndpointRateLimit.is_active == True
            ).all()

            for limit in endpoint_limits:
                limiter_config = LimiterConfig(
                    requests_per_minute=limit.requests_per_minute,
                    requests_per_hour=limit.requests_per_hour,
                    requests_per_day=5000,  # Default daily limit
                    burst_limit=limit.burst_limit,
                    window_seconds=limit.window_seconds
                )

                self.manager.load_endpoint_config(limit.endpoint_pattern, limiter_config)
                logger.info(f"Loaded endpoint rate limit: {limit.endpoint_pattern}")

            # Load user-specific overrides
            user_overrides = db.query(UserRateLimit).filter(
                UserRateLimit.is_active == True
            ).all()

            for override in user_overrides:
                base_config = db.query(RateLimitConfig).filter(
                    RateLimitConfig.id == override.config_id
                ).first()

                if base_config:
                    limiter_config = LimiterConfig(
                        requests_per_minute=base_config.requests_per_minute,
                        requests_per_hour=base_config.requests_per_hour,
                        requests_per_day=base_config.requests_per_day,
                        burst_limit=base_config.burst_limit,
                        window_seconds=base_config.window_seconds
                    )

                    # Apply custom overrides
                    if override.custom_limits:
                        custom = override.custom_limits
                        if 'requests_per_minute' in custom:
                            limiter_config.requests_per_minute = custom['requests_per_minute']
                        if 'requests_per_hour' in custom:
                            limiter_config.requests_per_hour = custom['requests_per_hour']
                        if 'requests_per_day' in custom:
                            limiter_config.requests_per_day = custom['requests_per_day']
                        if 'burst_limit' in custom:
                            limiter_config.burst_limit = custom['burst_limit']

                    self.manager.load_user_config(override.user_id, limiter_config)
                    logger.info(f"Loaded user rate limit override for user {override.user_id}")

            self._initialized = True
            logger.info("Rate limit configurations loaded from database")

        except Exception as e:
            logger.error(f"Error loading rate limit configurations: {e}")
            # Continue with default configurations

    def log_rate_limit_event(self, db: Session, user_id: Optional[int], client_ip: str,
                           endpoint: str, method: str, limit_type: str,
                           limit_exceeded: bool, requests_remaining: int,
                           reset_time, response_time_ms: Optional[float]):
        """Log a rate limit event to database"""
        try:
            log_entry = RateLimitLog(
                user_id=user_id,
                client_ip=client_ip,
                endpoint=endpoint,
                method=method,
                limit_type=limit_type,
                limit_exceeded=limit_exceeded,
                requests_remaining=requests_remaining,
                reset_time=reset_time,
                response_time_ms=response_time_ms
            )
            db.add(log_entry)
            db.commit()
        except Exception as e:
            logger.error(f"Error logging rate limit event: {e}")
            db.rollback()

    def get_rate_limit_stats(self, db: Session, hours: int = 24) -> Dict:
        """Get rate limiting statistics"""
        try:
            from datetime import datetime, timedelta
            from sqlalchemy import func

            cutoff_time = datetime.now() - timedelta(hours=hours)

            # Total requests
            total_requests = db.query(RateLimitLog).filter(
                RateLimitLog.created_at >= cutoff_time
            ).count()

            # Rate limit violations
            violations = db.query(RateLimitLog).filter(
                RateLimitLog.created_at >= cutoff_time,
                RateLimitLog.limit_exceeded == True
            ).count()

            # Top endpoints by requests
            endpoint_stats = db.query(
                RateLimitLog.endpoint,
                func.count(RateLimitLog.id).label('count')
            ).filter(
                RateLimitLog.created_at >= cutoff_time
            ).group_by(RateLimitLog.endpoint).order_by(
                func.count(RateLimitLog.id).desc()
            ).limit(10).all()

            # Top clients by violations
            client_violations = db.query(
                RateLimitLog.client_ip,
                func.count(RateLimitLog.id).label('violations')
            ).filter(
                RateLimitLog.created_at >= cutoff_time,
                RateLimitLog.limit_exceeded == True
            ).group_by(RateLimitLog.client_ip).order_by(
                func.count(RateLimitLog.id).desc()
            ).limit(10).all()

            return {
                "total_requests": total_requests,
                "rate_limit_violations": violations,
                "violation_rate": (violations / total_requests * 100) if total_requests > 0 else 0,
                "top_endpoints": [{"endpoint": ep, "requests": count} for ep, count in endpoint_stats],
                "top_violators": [{"ip": ip, "violations": count} for ip, count in client_violations],
                "time_range_hours": hours
            }

        except Exception as e:
            logger.error(f"Error getting rate limit stats: {e}")
            return {"error": str(e)}

    def update_system_load_metrics(self, db: Session, cpu_percent: float,
                                 memory_percent: float, active_connections: int):
        """Update system load metrics for auto-adjustment"""
        try:
            metrics = SystemLoadMetrics(
                cpu_percent=cpu_percent,
                memory_percent=memory_percent,
                active_connections=active_connections
            )
            db.add(metrics)
            db.commit()

            # Clean up old metrics (keep last 1000 entries)
            old_metrics = db.query(SystemLoadMetrics).order_by(
                SystemLoadMetrics.created_at.desc()
            ).offset(1000).all()

            for metric in old_metrics:
                db.delete(metric)
            db.commit()

        except Exception as e:
            logger.error(f"Error updating system load metrics: {e}")
            db.rollback()

# Global service instance
rate_limit_service = RateLimitService()

def get_rate_limit_service() -> RateLimitService:
    """Get the global rate limit service instance"""
    return rate_limit_service

def initialize_rate_limits(db: Session):
    """Initialize rate limiting from database (called during app startup)"""
    service = get_rate_limit_service()
    if not service._initialized:
        service.initialize_from_database(db)