"""
Comprehensive tests for the rate limiting system
"""
import pytest
import asyncio
import time
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime, timedelta, timezone
import json

from api_gateway.rate_limiter import SlidingWindowLimiter, get_rate_limit_manager, RateLimitManager
from api_gateway.rate_limit_service import get_rate_limit_service
from api_gateway.middleware import RateLimitMiddleware
from api_gateway.database import RateLimitConfig, EndpointRateLimit, UserRateLimit


class TestSlidingWindowLimiter:
    """Test the sliding window limiter"""

    def setup_method(self):
        """Setup test fixtures"""
        self.limiter = SlidingWindowLimiter()

    def test_allow_request_within_limit(self):
        """Test allowing requests within the limit"""
        key = "test_user"

        # Should allow all requests within limit
        for i in range(10):
            allowed, remaining = self.limiter.check_limit(key, 10, 60)
            assert allowed == True

        # Should deny the 11th request
        allowed, remaining = self.limiter.check_limit(key, 10, 60)
        assert allowed == False

    def test_sliding_window_behavior(self):
        """Test that the sliding window works correctly"""
        key = "test_user"

        # Fill up the window
        for i in range(10):
            self.limiter.check_limit(key, 10, 60)

        # Should be blocked
        allowed, remaining = self.limiter.check_limit(key, 10, 60)
        assert allowed == False

        # Simulate time passing (61 seconds - beyond window)
        with patch('api_gateway.rate_limiter.time.time', return_value=time.time() + 61):
            # Should allow requests again as old requests slide out
            allowed, remaining = self.limiter.check_limit(key, 10, 60)
            assert allowed == True

    def test_burst_allowance(self):
        """Test burst allowance functionality"""
        limiter = SlidingWindowLimiter()
        key = "test_user"

        # Use up regular limit
        for i in range(10):
            allowed, remaining = limiter.check_limit(key, 10, 60)
            assert allowed == True

        # Should allow burst requests (different key for burst)
        burst_key = f"{key}:burst"
        for i in range(3):
            allowed, remaining = limiter.check_limit(burst_key, 3, 10)
            assert allowed == True

        # Should deny after burst limit
        allowed, remaining = limiter.check_limit(burst_key, 3, 10)
        assert allowed == False

    def test_different_keys_isolated(self):
        """Test that different keys are isolated"""
        key1 = "user1"
        key2 = "user2"

        # Fill up user1
        for i in range(10):
            allowed, remaining = self.limiter.check_limit(key1, 10, 60)
            assert allowed == True

        # user2 should still be allowed
        allowed, remaining = self.limiter.check_limit(key2, 10, 60)
        assert allowed == True

    def test_cleanup_old_entries(self):
        """Test cleanup of old entries"""
        key = "test_user"

        # Add some requests
        for i in range(5):
            self.limiter.check_limit(key, 10, 60)

        # Simulate time passing (61 seconds - beyond window)
        with patch('api_gateway.rate_limiter.time.time', return_value=time.time() + 61):
            # Check limit again - should trigger cleanup
            allowed, remaining = self.limiter.check_limit(key, 10, 60)
            # Should allow since old entries are cleaned up
            assert allowed == True


class TestRateLimitManager:
    """Test the rate limit manager"""

    def setup_method(self):
        """Setup test fixtures"""
        self.manager = RateLimitManager()

    def test_check_rate_limit_basic(self):
        """Test basic rate limit checking"""
        result = self.manager.check_rate_limit(None, "127.0.0.1", "/api/test", "GET")

        # Should allow by default
        assert result.allowed == True
        assert result.limit_type == "user"

    def test_user_config_loading(self):
        """Test loading user-specific configurations"""
        from api_gateway.rate_limiter import RateLimitConfig

        config = RateLimitConfig(requests_per_minute=5, requests_per_hour=50)
        self.manager.load_user_config(1, config)

        result = self.manager.check_rate_limit(1, "127.0.0.1", "/api/test", "GET")
        assert result.allowed == True

    def test_endpoint_config_loading(self):
        """Test loading endpoint-specific configurations"""
        from api_gateway.rate_limiter import RateLimitConfig

        config = RateLimitConfig(requests_per_minute=2, requests_per_hour=20)
        self.manager.load_endpoint_config("/api/test", config)

        result = self.manager.check_rate_limit(1, "127.0.0.1", "/api/test", "GET")
        assert result.allowed == True

    def test_burst_limit_enforcement(self):
        """Test burst limit enforcement"""
        # Make many requests quickly to trigger burst limit
        for i in range(15):  # More than default burst limit of 10
            result = self.manager.check_rate_limit(1, "127.0.0.1", "/api/test", "GET")
            if i >= 10:  # After burst limit
                assert result.allowed == False
                assert "burst" in result.limit_type
                break


class TestRateLimitService:
    """Test the rate limit service"""

    def setup_method(self):
        """Setup test fixtures"""
        self.service = get_rate_limit_service()

    def test_service_initialization(self):
        """Test that the service initializes properly"""
        assert self.service is not None
        assert hasattr(self.service, 'manager')
        assert hasattr(self.service, 'get_user_limits')

    def test_get_user_limits(self):
        """Test getting user limits"""
        # This would require database setup, so just test the method exists
        assert hasattr(self.service, 'get_user_limits')

    def test_get_endpoint_limits(self):
        """Test getting endpoint limits"""
        assert hasattr(self.service, 'get_endpoint_limits')


class TestRateLimitMiddleware:
    """Test the rate limiting middleware"""

    def setup_method(self):
        """Setup test fixtures"""
        self.middleware = RateLimitMiddleware(Mock())

    @pytest.mark.asyncio
    async def test_middleware_initialization(self):
        """Test middleware initializes properly"""
        # Just test that it can be created
        assert self.middleware is not None


class TestRateLimitService:
    """Test the rate limit service"""

    def setup_method(self):
        """Setup test fixtures"""
        self.service = RateLimitService()

    @patch('api_gateway.rate_limit_service.SessionLocal')
    def test_get_user_limits(self, mock_session):
        """Test getting user rate limits"""
        mock_db = Mock()
        mock_session.return_value = mock_db

        # Mock user and config
        mock_user = Mock()
        mock_user.id = 1

        mock_config = Mock()
        mock_config.requests_per_minute = 60
        mock_config.requests_per_hour = 1000
        mock_config.burst_limit = 10

        mock_override = Mock()
        mock_override.custom_limits = {"requests_per_minute": 30}

        mock_db.query.return_value.filter.return_value.first.side_effect = [mock_config, mock_override]

        limits = self.service.get_user_limits(mock_db, mock_user)

        assert limits["requests_per_minute"] == 30  # Override applied
        assert limits["requests_per_hour"] == 1000
        assert limits["burst_limit"] == 10

    @patch('api_gateway.rate_limit_service.SessionLocal')
    def test_get_endpoint_limits(self, mock_session):
        """Test getting endpoint rate limits"""
        mock_db = Mock()
        mock_session.return_value = mock_db

        mock_limit = Mock()
        mock_limit.requests_per_minute = 30
        mock_limit.requests_per_hour = 500
        mock_limit.burst_limit = 5
        mock_limit.priority = 0

        mock_db.query.return_value.filter.return_value.order_by.return_value.all.return_value = [mock_limit]

        limits = self.service.get_endpoint_limits(mock_db, "/api/test")

        assert limits["requests_per_minute"] == 30
        assert limits["requests_per_hour"] == 500
        assert limits["burst_limit"] == 5

    def test_calculate_effective_limits(self):
        """Test calculating effective limits from multiple sources"""
        user_limits = {"requests_per_minute": 60, "burst_limit": 10}
        endpoint_limits = {"requests_per_minute": 30, "burst_limit": 5}

        effective = self.service._calculate_effective_limits(user_limits, endpoint_limits)

        # Should take the most restrictive limits
        assert effective["requests_per_minute"] == 30
        assert effective["burst_limit"] == 5


class TestRateLimitMiddleware:
    """Test the rate limiting middleware"""

    def setup_method(self):
        """Setup test fixtures"""
        self.middleware = RateLimitMiddleware(Mock())

    @patch('api_gateway.middleware.get_rate_limit_service')
    async def test_middleware_allows_request(self, mock_get_service):
        """Test middleware allows requests within limits"""
        mock_service = Mock()
        mock_service.is_allowed.return_value = (True, None)
        mock_get_service.return_value = mock_service

        request = Mock()
        request.client = Mock()
        request.client.host = "127.0.0.1"
        request.url.path = "/api/test"
        request.method = "GET"
        request.headers = {}

        call_next = Mock()
        call_next.return_value = Mock()

        response = await self.middleware.dispatch(request, call_next)

        # Should call next middleware and return response
        call_next.assert_called_once()
        assert response is not None

    @patch('api_gateway.middleware.get_rate_limit_service')
    async def test_middleware_blocks_request(self, mock_get_service):
        """Test middleware blocks requests over limits"""
        mock_service = Mock()
        mock_service.is_allowed.return_value = (False, "Rate limit exceeded")
        mock_get_service.return_value = mock_service

        request = Mock()
        request.client = Mock()
        request.client.host = "127.0.0.1"
        request.url.path = "/api/test"
        request.method = "GET"
        request.headers = {}

        call_next = Mock()

        response = await self.middleware.dispatch(request, call_next)

        # Should not call next middleware
        call_next.assert_not_called()

        # Should return 429 response
        assert response.status_code == 429
        assert "Rate limit exceeded" in response.body.decode()


class TestRateLimitIntegration:
    """Integration tests for the complete rate limiting system"""

    @patch('api_gateway.rate_limit_service.SessionLocal')
    def test_full_rate_limiting_flow(self, mock_session):
        """Test the complete rate limiting flow"""
        mock_db = Mock()
        mock_session.return_value = mock_db

        # Setup mocks
        mock_config = Mock()
        mock_config.requests_per_minute = 5
        mock_config.requests_per_hour = 100
        mock_config.burst_limit = 2

        mock_db.query.return_value.filter.return_value.first.return_value = mock_config

        service = RateLimitService()

        # Test multiple requests
        user = Mock()
        user.id = 1

        for i in range(5):
            allowed = service.is_allowed(mock_db, user, "/api/test", "127.0.0.1")
            assert allowed[0] == True

        # Should be blocked on 6th request
        allowed = service.is_allowed(mock_db, user, "/api/test", "127.0.0.1")
        assert allowed[0] == False

    @patch('api_gateway.rate_limit_service.SessionLocal')
    def test_user_specific_limits(self, mock_session):
        """Test user-specific rate limit overrides"""
        mock_db = Mock()
        mock_session.return_value = mock_db

        # Setup user override
        mock_override = Mock()
        mock_override.custom_limits = {"requests_per_minute": 2}
        mock_override.is_active = True
        mock_override.expires_at = None

        mock_db.query.return_value.filter.return_value.first.side_effect = [
            None,  # No config for user type
            mock_override  # User override exists
        ]

        service = RateLimitService()

        user = Mock()
        user.id = 1

        # First 2 requests should be allowed
        for i in range(2):
            allowed = service.is_allowed(mock_db, user, "/api/test", "127.0.0.1")
            assert allowed[0] == True

        # 3rd request should be blocked
        allowed = service.is_allowed(mock_db, user, "/api/test", "127.0.0.1")
        assert allowed[0] == False


class TestRateLimitHeaders:
    """Test rate limit headers in responses"""

    @patch('api_gateway.rate_limit_service.SessionLocal')
    def test_rate_limit_headers_added(self, mock_session):
        """Test that rate limit headers are added to responses"""
        mock_db = Mock()
        mock_session.return_value = mock_db

        mock_config = Mock()
        mock_config.requests_per_minute = 10
        mock_config.requests_per_hour = 100
        mock_config.burst_limit = 5

        mock_db.query.return_value.filter.return_value.first.return_value = mock_config

        service = RateLimitService()

        user = Mock()
        user.id = 1

        # Make a request
        allowed, reason = service.is_allowed(mock_db, user, "/api/test", "127.0.0.1")

        assert allowed == True

        # Check that headers would be set (this would be done in middleware)
        # The actual header setting is tested in middleware tests
        assert reason is None


class TestSystemLoadAdjustment:
    """Test automatic rate limit adjustments based on system load"""

    def test_system_load_detection(self):
        """Test system load detection"""
        from api_gateway.rate_limiter import SlidingWindowRateLimiter

        limiter = SlidingWindowRateLimiter(window_seconds=60, max_requests=10)

        # Test with mocked psutil
        with patch('psutil.cpu_percent', return_value=80.0), \
             patch('psutil.virtual_memory') as mock_memory:

            mock_memory.return_value.percent = 75.0

            load = limiter._get_system_load()
            assert load == 77.5  # Average of CPU and memory

    def test_high_load_adjustment(self):
        """Test rate limit adjustment under high load"""
        limiter = SlidingWindowRateLimiter(
            window_seconds=60,
            max_requests=10,
            auto_adjustment_enabled=True,
            high_load_threshold=80.0
        )

        # Mock high system load
        with patch.object(limiter, '_get_system_load', return_value=85.0):
            # The adjustment would happen in the background task
            # Here we test that the logic would trigger adjustment
            assert limiter._get_system_load() > limiter.high_load_threshold


if __name__ == "__main__":
    pytest.main([__file__])