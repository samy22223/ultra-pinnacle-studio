"""
Universal Webhook and Event System for Ultra Pinnacle AI Studio

This module provides a comprehensive event-driven architecture with:
- Event publishing and subscription
- Webhook delivery system
- Event filtering and routing
- Retry mechanisms and failure handling
- Event persistence and replay
"""

from typing import Any, Dict, List, Optional, Callable, Union, Awaitable
from dataclasses import dataclass, field
from datetime import datetime, timezone, timedelta
from enum import Enum
import asyncio
import aiohttp
import json
import logging
import hashlib
import hmac
import secrets
from concurrent.futures import ThreadPoolExecutor

logger = logging.getLogger("ultra_pinnacle")


class EventPriority(Enum):
    """Event priority levels"""

    LOW = "low"
    NORMAL = "normal"
    HIGH = "high"
    URGENT = "urgent"


class EventStatus(Enum):
    """Event processing status"""

    PENDING = "pending"
    PROCESSING = "processing"
    DELIVERED = "delivered"
    FAILED = "failed"
    RETRYING = "retrying"


@dataclass
class Event:
    """Event data structure"""

    id: str
    type: str
    source: str
    data: Dict[str, Any]
    priority: EventPriority = EventPriority.NORMAL
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    metadata: Dict[str, Any] = field(default_factory=dict)
    correlation_id: Optional[str] = None
    user_id: Optional[int] = None
    session_id: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert event to dictionary"""
        return {
            "id": self.id,
            "type": self.type,
            "source": self.source,
            "data": self.data,
            "priority": self.priority.value,
            "timestamp": self.timestamp.isoformat(),
            "metadata": self.metadata,
            "correlation_id": self.correlation_id,
            "user_id": self.user_id,
            "session_id": self.session_id
        }


@dataclass
class WebhookConfig:
    """Webhook configuration"""

    id: str
    url: str
    events: List[str]  # Event types to subscribe to
    secret: str  # Webhook secret for signature verification
    is_active: bool = True
    retry_count: int = 3
    timeout: int = 30  # seconds
    headers: Dict[str, str] = field(default_factory=dict)
    filters: Dict[str, Any] = field(default_factory=dict)  # Event filtering rules
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def should_deliver_event(self, event: Event) -> bool:
        """Check if this webhook should receive the event"""
        if not self.is_active:
            return False

        if event.type not in self.events and "*" not in self.events:
            return False

        # Apply filters
        for key, value in self.filters.items():
            if key in event.data and event.data[key] != value:
                return False

        return True


@dataclass
class WebhookDelivery:
    """Webhook delivery attempt"""

    id: str
    webhook_id: str
    event_id: str
    attempt_number: int
    status: EventStatus
    status_code: Optional[int] = None
    response_body: Optional[str] = None
    error_message: Optional[str] = None
    delivered_at: Optional[datetime] = None
    next_retry_at: Optional[datetime] = None
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def to_dict(self) -> Dict[str, Any]:
        """Convert delivery to dictionary"""
        return {
            "id": self.id,
            "webhook_id": self.webhook_id,
            "event_id": self.event_id,
            "attempt_number": self.attempt_number,
            "status": self.status.value,
            "status_code": self.status_code,
            "response_body": self.response_body,
            "error_message": self.error_message,
            "delivered_at": self.delivered_at.isoformat() if self.delivered_at else None,
            "next_retry_at": self.next_retry_at.isoformat() if self.next_retry_at else None,
            "created_at": self.created_at.isoformat()
        }


class EventBus:
    """Central event bus for publishing and subscribing to events"""

    def __init__(self):
        self._subscribers: Dict[str, List[Callable]] = {}
        self._event_history: List[Event] = []
        self._max_history_size = 10000
        self._lock = asyncio.Lock()

    async def publish(self, event: Event) -> None:
        """Publish an event to all subscribers"""
        async with self._lock:
            # Store event in history
            self._event_history.append(event)
            if len(self._event_history) > self._max_history_size:
                self._event_history.pop(0)

        logger.info(f"Publishing event: {event.type} from {event.source}")

        # Notify subscribers
        tasks = []
        for subscriber in self._subscribers.get(event.type, []):
            tasks.append(asyncio.create_task(self._notify_subscriber(subscriber, event)))

        for subscriber in self._subscribers.get("*", []):  # Wildcard subscribers
            tasks.append(asyncio.create_task(self._notify_subscriber(subscriber, event)))

        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)

    async def subscribe(self, event_type: str, callback: Callable[[Event], Awaitable[None]]) -> None:
        """Subscribe to events of a specific type"""
        async with self._lock:
            if event_type not in self._subscribers:
                self._subscribers[event_type] = []
            self._subscribers[event_type].append(callback)
            logger.info(f"Subscribed to event type: {event_type}")

    async def unsubscribe(self, event_type: str, callback: Callable[[Event], Awaitable[None]]) -> None:
        """Unsubscribe from events"""
        async with self._lock:
            if event_type in self._subscribers:
                try:
                    self._subscribers[event_type].remove(callback)
                    if not self._subscribers[event_type]:
                        del self._subscribers[event_type]
                    logger.info(f"Unsubscribed from event type: {event_type}")
                except ValueError:
                    pass

    async def _notify_subscriber(self, subscriber: Callable[[Event], Awaitable[None]], event: Event) -> None:
        """Notify a subscriber of an event"""
        try:
            await subscriber(event)
        except Exception as e:
            logger.error(f"Error notifying subscriber for event {event.type}: {e}")

    def get_event_history(self, event_type: Optional[str] = None, limit: int = 100) -> List[Event]:
        """Get event history"""
        history = self._event_history
        if event_type:
            history = [e for e in history if e.type == event_type]

        return history[-limit:]


class WebhookManager:
    """Manages webhook configurations and delivery"""

    def __init__(self, event_bus: EventBus):
        self.event_bus = event_bus
        self.webhooks: Dict[str, WebhookConfig] = {}
        self.deliveries: Dict[str, List[WebhookDelivery]] = {}
        self._executor = ThreadPoolExecutor(max_workers=10)
        self._session: Optional[aiohttp.ClientSession] = None

        # Subscribe to all events for webhook processing (only if event loop is running)
        try:
            loop = asyncio.get_running_loop()
            asyncio.create_task(self._setup_event_subscription())
        except RuntimeError:
            # No event loop running, subscription will be handled externally
            pass

    async def _setup_event_subscription(self):
        """Setup event subscription for webhook processing"""
        await self.event_bus.subscribe("*", self._process_event_for_webhooks)

    async def register_webhook(self, config: WebhookConfig) -> None:
        """Register a new webhook"""
        self.webhooks[config.id] = config
        self.deliveries[config.id] = []
        logger.info(f"Registered webhook: {config.id} -> {config.url}")

    async def unregister_webhook(self, webhook_id: str) -> bool:
        """Unregister a webhook"""
        if webhook_id in self.webhooks:
            del self.webhooks[webhook_id]
            if webhook_id in self.deliveries:
                del self.deliveries[webhook_id]
            logger.info(f"Unregistered webhook: {webhook_id}")
            return True
        return False

    async def _process_event_for_webhooks(self, event: Event) -> None:
        """Process an event for all registered webhooks"""
        tasks = []
        for webhook in self.webhooks.values():
            if webhook.should_deliver_event(event):
                tasks.append(asyncio.create_task(self._deliver_to_webhook(webhook, event)))

        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)

    async def _deliver_to_webhook(self, webhook: WebhookConfig, event: Event) -> None:
        """Deliver an event to a specific webhook"""
        delivery_id = f"{webhook.id}_{event.id}_{len(self.deliveries[webhook.id])}"

        # Create delivery record
        delivery = WebhookDelivery(
            id=delivery_id,
            webhook_id=webhook.id,
            event_id=event.id,
            attempt_number=len(self.deliveries[webhook.id]) + 1,
            status=EventStatus.PENDING
        )
        self.deliveries[webhook.id].append(delivery)

        try:
            # Prepare payload
            payload = event.to_dict()
            payload_json = json.dumps(payload)

            # Generate signature
            signature = self._generate_signature(payload_json, webhook.secret)

            # Prepare headers
            headers = {
                "Content-Type": "application/json",
                "X-Webhook-Signature": signature,
                "X-Webhook-Event-Type": event.type,
                "X-Webhook-Event-ID": event.id,
                "X-Webhook-Source": event.source,
                "User-Agent": "Ultra-Pinnacle-Webhook/1.0",
                **webhook.headers
            }

            # Initialize session if needed
            if self._session is None:
                self._session = aiohttp.ClientSession()

            # Send webhook
            delivery.status = EventStatus.PROCESSING
            async with self._session.post(
                webhook.url,
                data=payload_json,
                headers=headers,
                timeout=aiohttp.ClientTimeout(total=webhook.timeout)
            ) as response:
                delivery.status_code = response.status
                delivery.response_body = await response.text()

                if response.status >= 200 and response.status < 300:
                    delivery.status = EventStatus.DELIVERED
                    delivery.delivered_at = datetime.now(timezone.utc)
                    logger.info(f"Webhook delivered successfully: {webhook.id} -> {webhook.url}")
                else:
                    await self._handle_delivery_failure(webhook, delivery, f"HTTP {response.status}: {delivery.response_body}")

        except asyncio.TimeoutError:
            await self._handle_delivery_failure(webhook, delivery, "Timeout")
        except aiohttp.ClientError as e:
            await self._handle_delivery_failure(webhook, delivery, f"Client error: {str(e)}")
        except Exception as e:
            await self._handle_delivery_failure(webhook, delivery, f"Unexpected error: {str(e)}")

    async def _handle_delivery_failure(self, webhook: WebhookConfig, delivery: WebhookDelivery, error: str) -> None:
        """Handle webhook delivery failure"""
        delivery.status = EventStatus.FAILED
        delivery.error_message = error

        # Check if we should retry
        if delivery.attempt_number < webhook.retry_count:
            # Exponential backoff: 1s, 4s, 16s, etc.
            delay_seconds = 4 ** (delivery.attempt_number - 1)
            delivery.next_retry_at = datetime.now(timezone.utc) + timedelta(seconds=delay_seconds)
            delivery.status = EventStatus.RETRYING

            # Schedule retry
            asyncio.create_task(self._schedule_retry(webhook, delivery))
            logger.warning(f"Webhook delivery failed, retrying in {delay_seconds}s: {webhook.id}")
        else:
            logger.error(f"Webhook delivery failed permanently: {webhook.id} - {error}")

    async def _schedule_retry(self, webhook: WebhookConfig, delivery: WebhookDelivery) -> None:
        """Schedule a webhook retry"""
        if delivery.next_retry_at:
            delay = (delivery.next_retry_at - datetime.now(timezone.utc)).total_seconds()
            if delay > 0:
                await asyncio.sleep(delay)

            # Find the original event (simplified - in production, you'd store events)
            # For now, we'll create a retry event
            retry_event = Event(
                id=f"retry_{delivery.event_id}",
                type="webhook_retry",
                source="webhook_system",
                data={"original_event_id": delivery.event_id, "webhook_id": webhook.id}
            )

            await self._deliver_to_webhook(webhook, retry_event)

    def _generate_signature(self, payload: str, secret: str) -> str:
        """Generate webhook signature"""
        return hmac.new(
            secret.encode(),
            payload.encode(),
            hashlib.sha256
        ).hexdigest()

    def get_webhook_stats(self, webhook_id: Optional[str] = None) -> Dict[str, Any]:
        """Get webhook delivery statistics"""
        if webhook_id:
            deliveries = self.deliveries.get(webhook_id, [])
        else:
            deliveries = []
            for delivery_list in self.deliveries.values():
                deliveries.extend(delivery_list)

        total_deliveries = len(deliveries)
        successful_deliveries = len([d for d in deliveries if d.status == EventStatus.DELIVERED])
        failed_deliveries = len([d for d in deliveries if d.status == EventStatus.FAILED])

        return {
            "total_deliveries": total_deliveries,
            "successful_deliveries": successful_deliveries,
            "failed_deliveries": failed_deliveries,
            "success_rate": successful_deliveries / max(1, total_deliveries),
            "webhooks_count": len(self.webhooks)
        }

    async def close(self):
        """Clean up resources"""
        if self._session:
            await self._session.close()
        self._executor.shutdown(wait=True)


# Global instances
event_bus = EventBus()
webhook_manager = WebhookManager(event_bus)


# Convenience functions for event publishing
async def publish_event(
    event_type: str,
    source: str,
    data: Dict[str, Any],
    priority: EventPriority = EventPriority.NORMAL,
    user_id: Optional[int] = None,
    session_id: Optional[str] = None,
    correlation_id: Optional[str] = None,
    **metadata
) -> str:
    """Publish an event"""
    event_id = secrets.token_urlsafe(32)
    event = Event(
        id=event_id,
        type=event_type,
        source=source,
        data=data,
        priority=priority,
        user_id=user_id,
        session_id=session_id,
        correlation_id=correlation_id,
        metadata=metadata
    )

    await event_bus.publish(event)
    return event_id


def subscribe_to_events(event_type: str):
    """Decorator to subscribe to events"""
    def decorator(func: Callable[[Event], Awaitable[None]]):
        asyncio.create_task(event_bus.subscribe(event_type, func))
        return func
    return decorator


# Predefined event types
class EventTypes:
    """Standard event types"""

    # User events
    USER_REGISTERED = "user.registered"
    USER_LOGGED_IN = "user.logged_in"
    USER_LOGGED_OUT = "user.logged_out"
    USER_PROFILE_UPDATED = "user.profile_updated"

    # AI/Model events
    AI_REQUEST_STARTED = "ai.request_started"
    AI_REQUEST_COMPLETED = "ai.request_completed"
    AI_REQUEST_FAILED = "ai.request_failed"
    MODEL_LOADED = "model.loaded"
    MODEL_UNLOADED = "model.unloaded"

    # Conversation events
    CONVERSATION_CREATED = "conversation.created"
    CONVERSATION_UPDATED = "conversation.updated"
    CONVERSATION_DELETED = "conversation.deleted"
    MESSAGE_SENT = "message.sent"

    # File events
    FILE_UPLOADED = "file.uploaded"
    FILE_DOWNLOADED = "file.downloaded"
    FILE_DELETED = "file.deleted"

    # System events
    SYSTEM_STARTUP = "system.startup"
    SYSTEM_SHUTDOWN = "system.shutdown"
    BACKUP_COMPLETED = "backup.completed"
    BACKUP_FAILED = "backup.failed"

    # Plugin events
    PLUGIN_INSTALLED = "plugin.installed"
    PLUGIN_UNINSTALLED = "plugin.uninstalled"
    PLUGIN_ENABLED = "plugin.enabled"
    PLUGIN_DISABLED = "plugin.disabled"

    # Webhook events
    WEBHOOK_DELIVERED = "webhook.delivered"
    WEBHOOK_FAILED = "webhook.failed"