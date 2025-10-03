"""
Notification Service for Ultra Pinnacle AI Studio
Handles notification creation, queuing, delivery tracking, and multi-channel delivery.
"""
import asyncio
import json
import uuid
from typing import Dict, List, Optional, Any, Union
from datetime import datetime, timezone, timedelta
from dataclasses import dataclass
from enum import Enum
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

from sqlalchemy.orm import Session
from sqlalchemy import and_, or_, func

from .database import (
    Notification, NotificationTemplate, NotificationTemplateTranslation,
    NotificationDelivery, NotificationPreference, NotificationHistory,
    NotificationAnalytics, User, get_db
)
from .logging_config import logger


class NotificationChannel(Enum):
    """Supported notification channels"""
    IN_APP = "in_app"
    EMAIL = "email"
    WEBSOCKET = "websocket"
    PUSH = "push"


class NotificationPriority(Enum):
    """Notification priority levels"""
    LOW = "low"
    NORMAL = "normal"
    HIGH = "high"
    URGENT = "urgent"


@dataclass
class NotificationRequest:
    """Request object for creating notifications"""
    template_key: str
    recipient_ids: Union[int, List[int]]
    sender_id: Optional[int] = None
    variables: Optional[Dict[str, Any]] = None
    data: Optional[Dict[str, Any]] = None
    priority: NotificationPriority = NotificationPriority.NORMAL
    expires_in_hours: Optional[int] = None
    channels: Optional[List[NotificationChannel]] = None


class NotificationService:
    """Core notification service handling all notification operations"""

    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self._delivery_queue = asyncio.Queue()
        self._running = False
        self._delivery_workers = []

        # Email configuration
        self.smtp_config = config.get("notifications", {}).get("smtp", {})
        self.email_from = self.smtp_config.get("from", "noreply@ultra-pinnacle.ai")

        # WebSocket manager (will be injected)
        self.websocket_manager = None
        self.notification_connections = {}

        # Start delivery workers
        self._start_delivery_workers()

    def set_websocket_manager(self, manager):
        """Set the WebSocket connection manager"""
        self.websocket_manager = manager

    def set_notification_connections(self, connections: Dict[int, Any]):
        """Set the notification WebSocket connections"""
        self.notification_connections = connections

    def _start_delivery_workers(self, num_workers: int = 3):
        """Start background workers for processing notification deliveries"""
        self._running = True
        try:
            loop = asyncio.get_running_loop()
            for i in range(num_workers):
                worker = asyncio.create_task(self._delivery_worker(f"worker-{i}"))
                self._delivery_workers.append(worker)
                logger.info(f"Started notification delivery worker {i}")
        except RuntimeError:
            # No event loop running, workers will be started externally
            logger.info("No event loop running, notification workers will be started externally")

    async def _delivery_worker(self, worker_name: str):
        """Background worker for processing notification deliveries"""
        logger.info(f"Notification delivery worker {worker_name} started")

        while self._running:
            try:
                # Get delivery task from queue
                delivery_id = await self._delivery_queue.get()

                # Process delivery
                await self._process_delivery(delivery_id)

                # Mark task as done
                self._delivery_queue.task_done()

            except Exception as e:
                logger.error(f"Error in delivery worker {worker_name}: {e}")
                await asyncio.sleep(1)  # Brief pause before retrying

        logger.info(f"Notification delivery worker {worker_name} stopped")

    async def _process_delivery(self, delivery_id: int):
        """Process a single notification delivery"""
        db = next(get_db())

        try:
            # Get delivery record
            delivery = db.query(NotificationDelivery).filter(
                NotificationDelivery.id == delivery_id
            ).first()

            if not delivery:
                logger.warning(f"Delivery {delivery_id} not found")
                return

            # Skip if already processed
            if delivery.status in ["sent", "delivered"]:
                return

            # Update attempt count
            delivery.attempt_count += 1
            delivery.last_attempt_at = datetime.now(timezone.utc)

            # Process based on channel
            success = False
            if delivery.channel == NotificationChannel.IN_APP.value:
                success = await self._deliver_in_app(delivery, db)
            elif delivery.channel == NotificationChannel.EMAIL.value:
                success = await self._deliver_email(delivery, db)
            elif delivery.channel == NotificationChannel.WEBSOCKET.value:
                success = await self._deliver_websocket(delivery, db)
            elif delivery.channel == NotificationChannel.PUSH.value:
                success = await self._deliver_push(delivery, db)

            # Update delivery status
            if success:
                delivery.status = "sent"
                delivery.delivered_at = datetime.now(timezone.utc)
                logger.info(f"Successfully delivered notification {delivery.notification_id} via {delivery.channel}")
            else:
                # Check if we should retry
                if delivery.attempt_count < delivery.max_attempts:
                    delivery.status = "retry"
                    # Exponential backoff: 5 minutes * 2^(attempt-1)
                    retry_delay = timedelta(minutes=5 * (2 ** (delivery.attempt_count - 1)))
                    delivery.retry_after = datetime.now(timezone.utc) + retry_delay
                    # Re-queue for retry
                    await self._delivery_queue.put(delivery_id)
                else:
                    delivery.status = "failed"
                    delivery.failed_at = datetime.now(timezone.utc)
                    logger.error(f"Failed to deliver notification {delivery.notification_id} via {delivery.channel} after {delivery.attempt_count} attempts")

            db.commit()

        except Exception as e:
            logger.error(f"Error processing delivery {delivery_id}: {e}")
            db.rollback()
        finally:
            db.close()

    async def create_notification(self, request: NotificationRequest, db: Session) -> Optional[str]:
        """Create a new notification and queue deliveries"""
        try:
            # Get template
            template = db.query(NotificationTemplate).filter(
                NotificationTemplate.template_key == request.template_key,
                NotificationTemplate.is_active == True
            ).first()

            if not template:
                logger.error(f"Notification template '{request.template_key}' not found")
                return None

            # Handle single recipient
            recipient_ids = [request.recipient_ids] if isinstance(request.recipient_ids, int) else request.recipient_ids

            notification_ids = []

            for recipient_id in recipient_ids:
                # Check user preferences
                if not self._check_user_preferences(recipient_id, template, request.channels, db):
                    logger.debug(f"Skipping notification for user {recipient_id} due to preferences")
                    continue

                # Get user language preference
                user_lang = self._get_user_language(recipient_id, db)

                # Get template translation
                translation = db.query(NotificationTemplateTranslation).filter(
                    NotificationTemplateTranslation.template_id == template.id,
                    NotificationTemplateTranslation.language_code == user_lang,
                    NotificationTemplateTranslation.is_approved == True
                ).first()

                if not translation:
                    # Fallback to English
                    translation = db.query(NotificationTemplateTranslation).filter(
                        NotificationTemplateTranslation.template_id == template.id,
                        NotificationTemplateTranslation.language_code == "en",
                        NotificationTemplateTranslation.is_approved == True
                    ).first()

                if not translation:
                    logger.error(f"No translation found for template {request.template_key}")
                    continue

                # Render notification content
                title = self._render_template(translation.title, request.variables or {})
                message = self._render_template(translation.body, request.variables or {})

                # Calculate expiration
                expires_at = None
                if request.expires_in_hours:
                    expires_at = datetime.now(timezone.utc) + timedelta(hours=request.expires_in_hours)

                # Create notification
                notification_id = str(uuid.uuid4())
                notification = Notification(
                    id=notification_id,
                    template_id=template.id,
                    recipient_id=recipient_id,
                    sender_id=request.sender_id,
                    title=title,
                    message=message,
                    data=request.data,
                    priority=request.priority.value,
                    category=template.category,
                    expires_at=expires_at,
                    action_url=translation.action_url,
                    action_text=translation.action_text
                )

                db.add(notification)

                # Determine channels to use
                channels = request.channels or [NotificationChannel(c) for c in template.channels]

                # Create delivery records and queue them
                for channel in channels:
                    # Check channel-specific preferences
                    if not self._check_channel_preference(recipient_id, template.template_key, channel.value, db):
                        continue

                    delivery = NotificationDelivery(
                        notification_id=notification_id,
                        channel=channel.value,
                        recipient_address=self._get_recipient_address(recipient_id, channel.value, db)
                    )
                    db.add(delivery)
                    db.flush()  # Get delivery ID

                    # Queue for delivery
                    await self._delivery_queue.put(delivery.id)

                notification_ids.append(notification_id)

            db.commit()

            # Update analytics
            await self._update_analytics(template.template_key, template.category, len(notification_ids), db)

            logger.info(f"Created {len(notification_ids)} notifications for template {request.template_key}")
            return notification_ids[0] if len(notification_ids) == 1 else notification_ids

        except Exception as e:
            logger.error(f"Error creating notification: {e}")
            db.rollback()
            return None

    def _check_user_preferences(self, user_id: int, template: NotificationTemplate,
                              channels: Optional[List[NotificationChannel]], db: Session) -> bool:
        """Check if user has opted in to receive this type of notification"""
        if not template.requires_opt_in:
            return True

        # Check for template-specific preference
        preference = db.query(NotificationPreference).filter(
            NotificationPreference.user_id == user_id,
            NotificationPreference.template_key == template.template_key,
            NotificationPreference.enabled == True
        ).first()

        if preference:
            return True

        # Check for category preference
        category_pref = db.query(NotificationPreference).filter(
            NotificationPreference.user_id == user_id,
            NotificationPreference.category == template.category,
            NotificationPreference.template_key.is_(None),
            NotificationPreference.enabled == True
        ).first()

        return category_pref is not None

    def _check_channel_preference(self, user_id: int, template_key: str, channel: str, db: Session) -> bool:
        """Check if user wants notifications via this channel"""
        # Check template-specific channel preference
        preference = db.query(NotificationPreference).filter(
            NotificationPreference.user_id == user_id,
            or_(
                and_(NotificationPreference.template_key == template_key, NotificationPreference.channel == channel),
                and_(NotificationPreference.template_key.is_(None), NotificationPreference.channel == channel)
            ),
            NotificationPreference.enabled == True
        ).first()

        return preference is not None if preference else True  # Default to enabled

    def _get_user_language(self, user_id: int, db: Session) -> str:
        """Get user's preferred language"""
        from .database import UserLanguagePreference
        pref = db.query(UserLanguagePreference).filter(
            UserLanguagePreference.user_id == user_id,
            UserLanguagePreference.is_preferred == True
        ).first()

        return pref.language_code if pref else "en"

    def _render_template(self, template: str, variables: Dict[str, Any]) -> str:
        """Simple template rendering with variable substitution"""
        result = template
        for key, value in variables.items():
            result = result.replace(f"{{{{ {key} }}}}", str(value))
        return result

    def _get_recipient_address(self, user_id: int, channel: str, db: Session) -> Optional[str]:
        """Get the appropriate address for the recipient based on channel"""
        user = db.query(User).filter(User.id == user_id).first()
        if not user:
            return None

        if channel == NotificationChannel.EMAIL.value:
            return user.email
        elif channel == NotificationChannel.PUSH.value:
            # Would need device token storage - placeholder
            return None
        elif channel == NotificationChannel.WEBSOCKET.value:
            return str(user_id)  # Use user ID as identifier
        else:
            return str(user_id)

    async def _deliver_in_app(self, delivery: NotificationDelivery, db: Session) -> bool:
        """Deliver in-app notification (already stored in database)"""
        # In-app notifications are delivered by storing them in the database
        # The frontend will poll or use WebSocket to get them
        return True

    async def _deliver_email(self, delivery: NotificationDelivery, db: Session) -> bool:
        """Deliver notification via email"""
        try:
            if not self.smtp_config:
                logger.warning("SMTP not configured, skipping email delivery")
                return False

            # Get notification
            notification = db.query(Notification).filter(
                Notification.id == delivery.notification_id
            ).first()

            if not notification:
                return False

            # Create email message
            msg = MIMEMultipart()
            msg['From'] = self.email_from
            msg['To'] = delivery.recipient_address
            msg['Subject'] = notification.title

            # Add HTML body
            html_body = f"""
            <html>
            <body>
                <h2>{notification.title}</h2>
                <p>{notification.message}</p>
                {f'<p><a href="{notification.action_url}">{notification.action_text}</a></p>' if notification.action_url else ''}
            </body>
            </html>
            """

            msg.attach(MIMEText(html_body, 'html'))

            # Send email
            server = smtplib.SMTP(self.smtp_config.get('host', 'localhost'), self.smtp_config.get('port', 587))
            if self.smtp_config.get('use_tls', True):
                server.starttls()

            if self.smtp_config.get('username'):
                server.login(self.smtp_config['username'], self.smtp_config['password'])

            server.send_message(msg)
            server.quit()

            return True

        except Exception as e:
            logger.error(f"Error sending email: {e}")
            delivery.error_message = str(e)
            return False

    async def _deliver_websocket(self, delivery: NotificationDelivery, db: Session) -> bool:
        """Deliver notification via WebSocket"""
        try:
            # Get notification
            notification = db.query(Notification).filter(
                Notification.id == delivery.notification_id
            ).first()

            if not notification:
                return False

            # Send via notification WebSocket
            message_data = {
                "type": "notification",
                "data": {
                    "id": notification.id,
                    "title": notification.title,
                    "message": notification.message,
                    "priority": notification.priority,
                    "category": notification.category,
                    "action_url": notification.action_url,
                    "action_text": notification.action_text,
                    "created_at": notification.created_at.isoformat()
                }
            }

            # Send to specific user (assuming user_id is stored in recipient_address)
            user_id = int(delivery.recipient_address)
            if user_id in self.notification_connections:
                websocket = self.notification_connections[user_id]
                try:
                    await websocket.send_json(message_data)
                    return True
                except Exception as e:
                    logger.warning(f"Failed to send notification to user {user_id}: {e}")
                    # Remove disconnected websocket
                    if user_id in self.notification_connections:
                        del self.notification_connections[user_id]
                    return False
            else:
                logger.debug(f"User {user_id} not connected to notification WebSocket")
                return False

        except Exception as e:
            logger.error(f"Error sending WebSocket notification: {e}")
            delivery.error_message = str(e)
            return False

    async def _deliver_push(self, delivery: NotificationDelivery, db: Session) -> bool:
        """Deliver notification via push notification (placeholder)"""
        # This would integrate with FCM, APNs, etc.
        logger.info(f"Push notification delivery not implemented yet for {delivery.notification_id}")
        return False

    async def _update_analytics(self, template_key: str, category: str, count: int, db: Session):
        """Update notification analytics"""
        try:
            today = datetime.now(timezone.utc).date()

            # Update sent count
            analytics = NotificationAnalytics(
                date=today,
                template_key=template_key,
                category=category,
                metric_type="sent",
                count=count
            )

            # Use upsert logic (simplified)
            existing = db.query(NotificationAnalytics).filter(
                NotificationAnalytics.date == today,
                NotificationAnalytics.template_key == template_key,
                NotificationAnalytics.metric_type == "sent"
            ).first()

            if existing:
                existing.count += count
            else:
                db.add(analytics)

            db.commit()

        except Exception as e:
            logger.error(f"Error updating analytics: {e}")
            db.rollback()

    async def mark_as_read(self, notification_id: str, user_id: int, db: Session) -> bool:
        """Mark a notification as read"""
        try:
            notification = db.query(Notification).filter(
                Notification.id == notification_id,
                Notification.recipient_id == user_id
            ).first()

            if not notification:
                return False

            if not notification.is_read:
                notification.is_read = True
                notification.read_at = datetime.now(timezone.utc)
                db.commit()

                # Archive to history
                await self._archive_notification(notification, "read", db)

            return True

        except Exception as e:
            logger.error(f"Error marking notification as read: {e}")
            db.rollback()
            return False

    async def _archive_notification(self, notification: Notification, interaction: str, db: Session):
        """Archive notification to history"""
        try:
            # Get delivery status
            deliveries = db.query(NotificationDelivery).filter(
                NotificationDelivery.notification_id == notification.id
            ).all()

            channels_sent = [d.channel for d in deliveries]
            delivery_status = {d.channel: d.status for d in deliveries}

            history = NotificationHistory(
                notification_id=notification.id,
                template_key=notification.template.template_key,
                recipient_id=notification.recipient_id,
                sender_id=notification.sender_id,
                title=notification.title,
                message=notification.message,
                category=notification.category,
                priority=notification.priority,
                channels_sent=channels_sent,
                delivery_status=delivery_status,
                user_interaction=interaction,
                interaction_timestamp=datetime.now(timezone.utc)
            )

            db.add(history)
            db.commit()

        except Exception as e:
            logger.error(f"Error archiving notification: {e}")
            db.rollback()

    async def get_user_notifications(self, user_id: int, limit: int = 50, offset: int = 0,
                                   unread_only: bool = False, db: Session = Optional[Session]) -> List[Dict[str, Any]]:
        """Get notifications for a user"""
        if db is None:
            db = next(get_db())

        try:
            query = db.query(Notification).filter(
                Notification.recipient_id == user_id,
                or_(
                    Notification.expires_at.is_(None),
                    Notification.expires_at > datetime.now(timezone.utc)
                )
            )

            if unread_only:
                query = query.filter(Notification.is_read == False)

            notifications = query.order_by(Notification.created_at.desc()).offset(offset).limit(limit).all()

            result = []
            for notification in notifications:
                result.append({
                    "id": notification.id,
                    "title": notification.title,
                    "message": notification.message,
                    "priority": notification.priority,
                    "category": notification.category,
                    "is_read": notification.is_read,
                    "action_url": notification.action_url,
                    "action_text": notification.action_text,
                    "created_at": notification.created_at.isoformat(),
                    "expires_at": notification.expires_at.isoformat() if notification.expires_at else None
                })

            return result

        except Exception as e:
            logger.error(f"Error getting user notifications: {e}")
            return []
        finally:
            if db:
                db.close()

    async def get_unread_count(self, user_id: int, db: Session = None) -> int:
        """Get count of unread notifications for a user"""
        if db is None:
            db = next(get_db())

        try:
            count = db.query(func.count(Notification.id)).filter(
                Notification.recipient_id == user_id,
                Notification.is_read == False,
                or_(
                    Notification.expires_at.is_(None),
                    Notification.expires_at > datetime.now(timezone.utc)
                )
            ).scalar()

            return count or 0

        except Exception as e:
            logger.error(f"Error getting unread count: {e}")
            return 0
        finally:
            if db:
                db.close()

    async def shutdown(self):
        """Shutdown the notification service"""
        logger.info("Shutting down notification service")
        self._running = False

        # Wait for workers to finish
        if self._delivery_workers:
            await asyncio.gather(*self._delivery_workers, return_exceptions=True)

        logger.info("Notification service shutdown complete")


# Global notification service instance
_notification_service = None

def get_notification_service(config: Dict[str, Any] = None) -> NotificationService:
    """Get the global notification service instance"""
    global _notification_service
    if _notification_service is None:
        if config is None:
            # Load config if not provided
            import os
            config_path = os.path.join(os.path.dirname(__file__), '..', 'config.json')
            with open(config_path, "r") as f:
                config = json.load(f)
        _notification_service = NotificationService(config)
    return _notification_service