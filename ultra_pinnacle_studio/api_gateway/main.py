from fastapi import FastAPI, HTTPException, Depends, File, UploadFile, Form, Query, WebSocket, WebSocketDisconnect, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
import os
import json
import uuid
import subprocess
import re
import asyncio
from pathlib import Path
from datetime import datetime, timedelta, timezone
from contextlib import asynccontextmanager
import aiofiles
from jose import JWTError, jwt
from .logging_config import logger
from .auth import create_access_token, get_current_user, get_current_active_user, authenticate_user, SECRET_KEY, ALGORITHM, create_refresh_token, ACCESS_TOKEN_EXPIRE_MINUTES, create_user, revoke_refresh_token, refresh_access_token, verify_refresh_token, validate_password, revoke_all_user_refresh_tokens
from .database import PasswordResetToken, AccountLockout
from .database import (
    User, Conversation, Message, ConversationParticipant,
    UserPresence, ActivityLog, CollaborativeDocument, DocumentEdit,
    SupportedLanguage, UserLanguagePreference, Translation,
    TranslationSuggestion, MultilingualContent,
    # Onboarding and Tutorial models
    OnboardingFlow, OnboardingStep, UserOnboardingProgress,
    Tutorial, TutorialProgress, UserTutorialAnalytics,
    HelpCategory, HelpArticle, Tooltip, UserTooltipInteraction,
    SupportChat, SupportMessage
)
from .database import get_db
from sqlalchemy.orm import Session
from .models_safe import ModelManager
from .workers import WorkerManager
from .middleware import setup_middleware
from .language_middleware import LanguageMiddleware
from .translations import setup_translations, _
from .translation_service import get_translation_service
from .cache_manager import get_cache_manager
from .metrics import router as metrics_router
from .validation import (
    ValidatedPromptRequest, ValidatedChatRequest, ValidatedCodeRequest,
    ValidatedSearchRequest, ValidatedLoginRequest, validate_file_upload,
    ValidatedUserProfileUpdate, ValidatedPasswordChange, ValidatedModelSwitch,
    ValidatedConversationCreate, ValidatedImageGenerationRequest,
    ValidatedCodeCompletionRequest, ValidatedPromptEngineeringRequest,
    ValidatedMultiModalRequest, ValidatedCodeRefactoringRequest,
    ValidatedConversionRequest, ValidatedCodeExplanationRequest,
    ValidatedDebugRequest
)
from .woocommerce_endpoints import router as woocommerce_router
from .plugins import PluginManager
from .rate_limit_service import initialize_rate_limits, get_rate_limit_service
from .data_export_import import export_service
from .search_service import SearchService
from .notification_service import get_notification_service
from .oauth_service import get_oauth_service

from .api_framework import initialize_framework, APIVersion

from .config import config

# Import auto-healing service
try:
    from scripts.auto_healer import AutoHealer
    auto_healer = AutoHealer()
except ImportError:
    auto_healer = None

# Initialize managers
logger.debug("Initializing ModelManager, WorkerManager, PluginManager, and NotificationService")
model_manager = ModelManager(config)
worker_manager = WorkerManager(config)
plugin_manager = PluginManager(config)
translation_service = get_translation_service(model_manager)
cache_manager = get_cache_manager()
search_service = SearchService(config)
notification_service = get_notification_service(config)
logger.debug("Managers initialized successfully")

class PromptRequest(BaseModel):
    prompt: str
    model: Optional[str] = None
    temperature: Optional[float] = 0.7
    max_tokens: Optional[int] = 512

class SearchRequest(BaseModel):
    query: str
    limit: Optional[int] = 10

class ChatRequest(BaseModel):
    message: str
    conversation_id: Optional[str] = None
    model: Optional[str] = None

class CodeRequest(BaseModel):
    code: str
    language: str
    task: str  # "analyze", "generate", "refactor", "debug"

class LoginRequest(BaseModel):
    username: str
    password: str

class RegisterRequest(BaseModel):
    username: str
    email: str
    password: str
    full_name: Optional[str] = None

# Response Models
class LoginResponse(BaseModel):
    access_token: str = Field(..., description="JWT access token")
    refresh_token: str = Field(..., description="JWT refresh token")
    token_type: str = Field("bearer", description="Token type")
    expires_in: int = Field(..., description="Access token expiration time in seconds")

class PromptEnhancementResponse(BaseModel):
    enhanced_prompt: str = Field(..., description="The enhanced and improved prompt")

class ChatResponse(BaseModel):
    response: str = Field(..., description="AI-generated response")
    conversation_id: str = Field(..., description="Conversation thread identifier")
    message_id: str = Field(..., description="Unique message identifier")

class TaskSubmissionResponse(BaseModel):
    task_id: str = Field(..., description="Unique task identifier")
    status: str = Field(..., description="Task status")

class HealthResponse(BaseModel):
    status: str = Field(..., description="Service health status")
    timestamp: str = Field(..., description="Current timestamp")
    models_loaded: int = Field(..., description="Number of loaded AI models")
    active_tasks: int = Field(..., description="Number of currently running tasks")

class GitCommit(BaseModel):
    hash: str = Field(..., description="Commit hash")
    message: str = Field(..., description="Commit message")
    author: str = Field(..., description="Author name")
    author_email: str = Field(..., description="Author email")
    date: str = Field(..., description="Commit date")
    branch: Optional[str] = Field(None, description="Branch name")
    tags: List[str] = Field(default_factory=list, description="Associated tags")
    parents: List[str] = Field(default_factory=list, description="Parent commit hashes")
    files_changed: Optional[int] = Field(None, description="Number of files changed")
    insertions: Optional[int] = Field(None, description="Number of insertions")
    deletions: Optional[int] = Field(None, description="Number of deletions")

class GitBranch(BaseModel):
    name: str = Field(..., description="Branch name")
    is_current: bool = Field(..., description="Whether this is the current branch")
    is_remote: bool = Field(..., description="Whether this is a remote branch")
    last_commit: Optional[str] = Field(None, description="Last commit hash")
    last_commit_date: Optional[str] = Field(None, description="Last commit date")

class ModelInfo(BaseModel):
    name: str = Field(..., description="Model name")
    status: str = Field(..., description="Model loading status")
    type: str = Field(..., description="Model type")
    path: Optional[str] = Field(None, description="Model file path")

class ModelsListResponse(BaseModel):
    models: Dict[str, Any] = Field(..., description="Available models")
    default_model: str = Field(..., description="Default model name")


# Ensure directories exist
for dir_path in [config["paths"]["uploads_dir"], config["paths"]["logs_dir"]]:
    Path(dir_path).mkdir(exist_ok=True)

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    logger.info("Starting Ultra Pinnacle AI Studio")

    # Initialize rate limiting from database
    try:
        from .database import SessionLocal
        db = SessionLocal()
        initialize_rate_limits(db)
        db.close()
        logger.info("Rate limiting initialized")
    except Exception as e:
        logger.error(f"Error initializing rate limiting: {e}")

    # Start automatic rate limit adjustment task
    adjustment_task = None
    try:
        adjustment_task = asyncio.create_task(run_rate_limit_adjustments())
        logger.info("Automatic rate limit adjustment task started")
    except Exception as e:
        logger.error(f"Error starting rate limit adjustment task: {e}")

    # Load and initialize plugins
    try:
        discovered_plugins = plugin_manager.discover_plugins()
        logger.info(f"Discovered {len(discovered_plugins)} plugins")

        # Auto-load enabled plugins (in production, this would be configurable)
        loaded_count = 0
        for plugin_id in discovered_plugins[:2]:  # Load first 2 for testing
            if plugin_manager.load_plugin(plugin_id):
                loaded_count += 1
        logger.info(f"Auto-loaded {loaded_count} plugins")

    except Exception as e:
        logger.error(f"Error during plugin initialization: {e}")

    # Initialize and start auto-healing AI engineer system
    try:
        global ai_engineer_system
        if ai_engineer_system:
            ai_engineer_system.start()
            logger.info("Auto-Healing AI Engineer System started")
    except Exception as e:
        logger.error(f"Error starting AI Engineer System: {e}")

    yield

    # Shutdown
    logger.info("Shutting down Ultra Pinnacle AI Studio")

    # Stop AI engineer system
    try:
        if ai_engineer_system:
            ai_engineer_system.stop()
            logger.info("Auto-Healing AI Engineer System stopped")
    except Exception as e:
        logger.error(f"Error stopping AI Engineer System: {e}")

    # Stop rate limit adjustment task
    if adjustment_task:
        adjustment_task.cancel()
        try:
            await adjustment_task
        except asyncio.CancelledError:
            pass
        logger.info("Rate limit adjustment task stopped")

    # Shutdown plugins
    try:
        plugin_manager.shutdown_all()
    except Exception as e:
        logger.error(f"Error during plugin shutdown: {e}")

async def run_rate_limit_adjustments():
    """Background task for automatic rate limit adjustments based on system load"""
    while True:
        try:
            # Check system load every 60 seconds
            await asyncio.sleep(60)

            # Get current system load
            rate_limit_service = get_rate_limit_service()
            manager = rate_limit_service.manager

            if not manager.auto_adjustment_enabled:
                continue

            system_load = manager._get_system_load()
            logger.debug(f"System load: {system_load}%")

            # Update system load metrics in database
            try:
                from .database import SessionLocal
                db = SessionLocal()
                rate_limit_service.update_system_load_metrics(
                    db, system_load, system_load, 0  # Placeholder for active connections
                )
                db.close()
            except Exception as e:
                logger.error(f"Error updating system load metrics: {e}")

            # Adjust rate limits if load is high
            if system_load > manager.high_load_threshold:
                logger.info(f"High system load detected ({system_load}%), reducing rate limits")
                # The adjustment is handled automatically in the _calculate_effective_limits method
                # when checking rate limits

            elif system_load < manager.low_load_threshold:
                logger.debug(f"Low system load ({system_load}%), rate limits at normal levels")

        except asyncio.CancelledError:
            break
        except Exception as e:
            logger.error(f"Error in rate limit adjustment task: {e}")
            await asyncio.sleep(10)  # Wait before retrying

app = FastAPI(
    title=config["app"]["name"],
    version=config["app"]["version"],
    description="""
    Ultra Pinnacle AI Studio - A comprehensive offline AI development platform.

    ## Features

    * **AI Model Management**: Load and manage multiple AI models locally
    * **Prompt Enhancement**: Improve your prompts with AI assistance
    * **Chat Interface**: Interactive conversations with AI models
    * **Code Analysis**: Analyze, generate, refactor, and debug code
    * **Encyclopedia**: Comprehensive knowledge base with search capabilities
    * **File Management**: Secure file upload and management
    * **Background Tasks**: Asynchronous processing for long-running operations
    * **Monitoring**: Health checks, metrics, and performance monitoring

    ## Authentication

    Most endpoints require authentication. Use `/auth/login` to obtain an access token,
    then include it in the Authorization header: `Bearer <token>`

    ## Rate Limiting

    API requests are rate-limited to prevent abuse. Check response headers for rate limit status.
    """,
    lifespan=lifespan,
    contact={
        "name": "Ultra Pinnacle AI Studio",
        "url": "https://github.com/ultra-pinnacle",
        "email": "support@ultra-pinnacle.ai"
    },
    license_info={
        "name": "MIT License",
        "url": "https://opensource.org/licenses/MIT"
    },
    openapi_tags=[
        {
            "name": "authentication",
            "description": "User authentication and authorization"
        },
        {
            "name": "ai",
            "description": "AI model interactions and prompt enhancement"
        },
        {
            "name": "encyclopedia",
            "description": "Knowledge base search and content access"
        },
        {
            "name": "files",
            "description": "File upload and management"
        },
        {
            "name": "tasks",
            "description": "Background task management"
        },
        {
            "name": "monitoring",
            "description": "Health checks and system metrics"
        }
    ]
)

# Initialize API framework
initialize_framework(app)

# Setup middleware
setup_middleware(app, config)

# Add language middleware
app.add_middleware(LanguageMiddleware)

# Include metrics router
app.include_router(metrics_router)

# Notification endpoints
@app.get(
    "/api/notifications",
    response_model=List[Dict[str, Any]],
    summary="Get User Notifications",
    description="Get notifications for the current user with optional filtering",
    tags=["notifications"]
)
async def get_user_notifications(
    limit: int = Query(50, description="Maximum number of notifications to return", ge=1, le=200),
    offset: int = Query(0, description="Number of notifications to skip", ge=0),
    unread_only: bool = Query(False, description="Return only unread notifications"),
    category: Optional[str] = Query(None, description="Filter by notification category"),
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Get notifications for the current user"""
    try:
        notifications = await notification_service.get_user_notifications(
            current_user.id, limit, offset, unread_only, db
        )

        # Apply category filter if specified
        if category:
            notifications = [n for n in notifications if n.get('category') == category]

        return notifications
    except Exception as e:
        logger.error(f"Error getting user notifications: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get(
    "/api/notifications/unread-count",
    response_model=Dict[str, int],
    summary="Get Unread Notification Count",
    description="Get the count of unread notifications for the current user",
    tags=["notifications"]
)
async def get_unread_notification_count(
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Get unread notification count"""
    try:
        count = await notification_service.get_unread_count(current_user.id, db)
        return {"unread_count": count}
    except Exception as e:
        logger.error(f"Error getting unread count: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post(
    "/api/notifications/{notification_id}/read",
    response_model=Dict[str, str],
    summary="Mark Notification as Read",
    description="Mark a specific notification as read",
    tags=["notifications"]
)
async def mark_notification_read(
    notification_id: str,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Mark notification as read"""
    try:
        success = await notification_service.mark_as_read(notification_id, current_user.id, db)
        if not success:
            raise HTTPException(status_code=404, detail="Notification not found")
        return {"message": "Notification marked as read"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error marking notification as read: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post(
    "/api/notifications/mark-all-read",
    response_model=Dict[str, str],
    summary="Mark All Notifications as Read",
    description="Mark all notifications for the current user as read",
    tags=["notifications"]
)
async def mark_all_notifications_read(
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Mark all notifications as read"""
    try:
        # Get all unread notifications
        notifications = await notification_service.get_user_notifications(
            current_user.id, limit=1000, unread_only=True, db=db
        )

        marked_count = 0
        for notification in notifications:
            success = await notification_service.mark_as_read(notification['id'], current_user.id, db)
            if success:
                marked_count += 1

        return {"message": f"Marked {marked_count} notifications as read"}
    except Exception as e:
        logger.error(f"Error marking all notifications as read: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.delete(
    "/api/notifications/{notification_id}",
    response_model=Dict[str, str],
    summary="Delete Notification",
    description="Delete a specific notification",
    tags=["notifications"]
)
async def delete_notification(
    notification_id: str,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Delete a notification"""
    try:
        # Check ownership
        notification = db.query(Notification).filter(
            Notification.id == notification_id,
            Notification.recipient_id == current_user.id
        ).first()

        if not notification:
            raise HTTPException(status_code=404, detail="Notification not found")

        # Archive before deletion
        await notification_service._archive_notification(notification, "deleted", db)

        # Delete notification and deliveries
        db.query(NotificationDelivery).filter(
            NotificationDelivery.notification_id == notification_id
        ).delete()

        db.delete(notification)
        db.commit()

        return {"message": "Notification deleted successfully"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting notification: {e}")
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))

# Notification preferences endpoints
@app.get(
    "/api/notifications/preferences",
    response_model=List[Dict[str, Any]],
    summary="Get Notification Preferences",
    description="Get notification preferences for the current user",
    tags=["notifications"]
)
async def get_notification_preferences(
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Get user notification preferences"""
    try:
        preferences = db.query(NotificationPreference).filter(
            NotificationPreference.user_id == current_user.id
        ).all()

        result = []
        for pref in preferences:
            result.append({
                "id": pref.id,
                "template_key": pref.template_key,
                "category": pref.category,
                "channel": pref.channel,
                "enabled": pref.enabled,
                "created_at": pref.created_at.isoformat(),
                "updated_at": pref.updated_at.isoformat()
            })

        return result
    except Exception as e:
        logger.error(f"Error getting notification preferences: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.put(
    "/api/notifications/preferences",
    response_model=Dict[str, str],
    summary="Update Notification Preferences",
    description="Update notification preferences for the current user",
    tags=["notifications"]
)
async def update_notification_preferences(
    preferences: List[Dict[str, Any]],
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Update user notification preferences"""
    try:
        for pref_data in preferences:
            # Find existing preference or create new one
            existing = db.query(NotificationPreference).filter(
                NotificationPreference.user_id == current_user.id,
                NotificationPreference.template_key == pref_data.get('template_key'),
                NotificationPreference.category == pref_data.get('category'),
                NotificationPreference.channel == pref_data.get('channel')
            ).first()

            if existing:
                existing.enabled = pref_data.get('enabled', True)
                existing.updated_at = datetime.now(timezone.utc)
            else:
                preference = NotificationPreference(
                    user_id=current_user.id,
                    template_key=pref_data.get('template_key'),
                    category=pref_data.get('category'),
                    channel=pref_data.get('channel'),
                    enabled=pref_data.get('enabled', True)
                )
                db.add(preference)

        db.commit()
        return {"message": "Notification preferences updated successfully"}
    except Exception as e:
        logger.error(f"Error updating notification preferences: {e}")
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))

# Admin notification endpoints
@app.post(
    "/admin/notifications/broadcast",
    response_model=Dict[str, str],
    summary="Broadcast Notification to All Users",
    description="Send a notification to all users (admin only)",
    tags=["admin", "notifications"]
)
async def broadcast_notification(
    template_key: str,
    variables: Optional[Dict[str, Any]] = None,
    channels: Optional[List[str]] = None,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Broadcast notification to all users"""
    if not current_user.is_superuser:
        raise HTTPException(status_code=403, detail="Admin access required")

    try:
        # Get all active users
        users = db.query(User).filter(User.is_active == True).all()
        recipient_ids = [user.id for user in users]

        # Create notification request
        from .notification_service import NotificationRequest, NotificationChannel, NotificationPriority
        request = NotificationRequest(
            template_key=template_key,
            recipient_ids=recipient_ids,
            sender_id=current_user.id,
            variables=variables,
            priority=NotificationPriority.HIGH,
            channels=[NotificationChannel(c) for c in (channels or ["in_app", "email"])]
        )

        # Send notifications
        notification_ids = await notification_service.create_notification(request, db)

        return {"message": f"Broadcast sent to {len(recipient_ids)} users", "notification_ids": notification_ids}
    except Exception as e:
        logger.error(f"Error broadcasting notification: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get(
    "/admin/notifications/analytics",
    response_model=Dict[str, Any],
    summary="Get Notification Analytics",
    description="Get notification system analytics (admin only)",
    tags=["admin", "notifications"]
)
async def get_notification_analytics(
    days: int = Query(30, description="Number of days to analyze", ge=1, le=365),
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Get notification analytics"""
    if not current_user.is_superuser:
        raise HTTPException(status_code=403, detail="Admin access required")

    try:
        cutoff_date = datetime.now(timezone.utc) - timedelta(days=days)

        # Get analytics data
        analytics = db.query(NotificationAnalytics).filter(
            NotificationAnalytics.date >= cutoff_date
        ).all()

        # Aggregate by metric type
        sent_count = sum(a.count for a in analytics if a.metric_type == "sent")
        delivered_count = sum(a.count for a in analytics if a.metric_type == "delivered")
        read_count = sum(a.count for a in analytics if a.metric_type == "read")

        # Get delivery status breakdown
        delivery_stats = db.query(
            NotificationDelivery.status,
            db.func.count(NotificationDelivery.id)
        ).filter(
            NotificationDelivery.created_at >= cutoff_date
        ).group_by(NotificationDelivery.status).all()

        delivery_breakdown = {status: count for status, count in delivery_stats}

        # Get template usage
        template_usage = db.query(
            NotificationAnalytics.template_key,
            db.func.sum(NotificationAnalytics.count)
        ).filter(
            NotificationAnalytics.date >= cutoff_date,
            NotificationAnalytics.metric_type == "sent"
        ).group_by(NotificationAnalytics.template_key).all()

        template_breakdown = {template: count for template, count in template_usage}

        return {
            "period_days": days,
            "total_sent": sent_count,
            "total_delivered": delivered_count,
            "total_read": read_count,
            "delivery_rate": (delivered_count / sent_count * 100) if sent_count > 0 else 0,
            "read_rate": (read_count / sent_count * 100) if sent_count > 0 else 0,
            "delivery_status_breakdown": delivery_breakdown,
            "template_usage": template_breakdown
        }
    except Exception as e:
        logger.error(f"Error getting notification analytics: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get(
    "/admin/notifications/templates",
    response_model=List[Dict[str, Any]],
    summary="List Notification Templates",
    description="Get all notification templates (admin only)",
    tags=["admin", "notifications"]
)
async def list_notification_templates(
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """List notification templates"""
    if not current_user.is_superuser:
        raise HTTPException(status_code=403, detail="Admin access required")

    try:
        templates = db.query(NotificationTemplate).all()

        result = []
        for template in templates:
            # Get translations count
            translation_count = db.query(NotificationTemplateTranslation).filter(
                NotificationTemplateTranslation.template_id == template.id
            ).count()

            result.append({
                "id": template.id,
                "template_key": template.template_key,
                "name": template.name,
                "description": template.description,
                "category": template.category,
                "channels": template.channels,
                "requires_opt_in": template.requires_opt_in,
                "is_active": template.is_active,
                "translation_count": translation_count,
                "created_at": template.created_at.isoformat(),
                "updated_at": template.updated_at.isoformat()
            })

        return result
    except Exception as e:
        logger.error(f"Error listing notification templates: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get(
    "/admin/notifications/history",
    response_model=List[Dict[str, Any]],
    summary="Get Notification History",
    description="Get archived notification history (admin only)",
    tags=["admin", "notifications"]
)
async def get_notification_history(
    limit: int = Query(100, description="Maximum number of records to return", ge=1, le=1000),
    offset: int = Query(0, description="Number of records to skip", ge=0),
    user_id: Optional[int] = Query(None, description="Filter by user ID"),
    template_key: Optional[str] = Query(None, description="Filter by template key"),
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Get notification history"""
    if not current_user.is_superuser:
        raise HTTPException(status_code=403, detail="Admin access required")

    try:
        query = db.query(NotificationHistory)

        if user_id:
            query = query.filter(NotificationHistory.recipient_id == user_id)
        if template_key:
            query = query.filter(NotificationHistory.template_key == template_key)

        history = query.order_by(NotificationHistory.interaction_timestamp.desc()).offset(offset).limit(limit).all()

        result = []
        for record in history:
            result.append({
                "id": record.id,
                "notification_id": record.notification_id,
                "template_key": record.template_key,
                "recipient_id": record.recipient_id,
                "sender_id": record.sender_id,
                "title": record.title,
                "message": record.message,
                "category": record.category,
                "priority": record.priority,
                "channels_sent": record.channels_sent,
                "delivery_status": record.delivery_status,
                "user_interaction": record.user_interaction,
                "interaction_timestamp": record.interaction_timestamp.isoformat()
            })

        return result
    except Exception as e:
        logger.error(f"Error getting notification history: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# Add plugin routes dynamically
plugin_routes = plugin_manager.get_api_routes()
for route in plugin_routes:
    try:
        # Convert plugin route format to FastAPI format
        methods = route.get('methods', ['GET'])
        path = route['path']
        handler = route['handler']
        summary = route.get('summary', '')

        # Add route to app
        app.add_api_route(
            path=path,
            endpoint=handler,
            methods=methods,
            summary=summary,
            tags=["plugins"]
        )
        logger.debug(f"Added plugin route: {methods} {path}")
    except Exception as e:
        logger.error(f"Error adding plugin route {route.get('path', 'unknown')}: {e}")

# Authentication endpoints
@app.post(
    "/auth/login",
    response_model=LoginResponse,
    summary="User Login",
    description="""
    Authenticate a user and obtain an access token.

    **Credentials:**
    - Username: demo
    - Password: demo123

    The returned access token should be included in the Authorization header
    for subsequent API requests: `Authorization: Bearer <token>`
    """,
    response_description="Access token and token type",
    tags=["authentication"]
)
async def login(
    username: str = Form(..., description="Username"),
    password: str = Form(..., description="Password"),
    db: Session = Depends(get_db)
):
    """
    Authenticate user and return access and refresh tokens.

    - **username**: User's username (3-50 characters, alphanumeric + hyphens/underscores)
    - **password**: User's password (6-128 characters)
    """
    user = authenticate_user(db, username, password)
    if not user:
        raise HTTPException(status_code=401, detail="Invalid credentials")

    # Create tokens
    access_token = create_access_token(data={"sub": user.username})
    refresh_token = create_refresh_token(db, user.id)

    logger.info(f"User {user.username} logged in")
    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "token_type": "bearer",
        "expires_in": ACCESS_TOKEN_EXPIRE_MINUTES * 60
    }

@app.post(
    "/auth/register",
    response_model=LoginResponse,
    summary="User Registration",
    description="Register a new user account",
    tags=["authentication"]
)
async def register(request: RegisterRequest, db: Session = Depends(get_db)):
    """
    Register a new user account.

    - **username**: Desired username (3-50 characters, alphanumeric + hyphens/underscores)
    - **email**: User's email address
    - **password**: User's password (must meet security requirements)
    - **full_name**: Optional full name
    """
    # Validate username format
    import re
    if not re.match(r'^[a-zA-Z0-9_-]{3,50}$', request.username):
        raise HTTPException(status_code=400, detail="Invalid username format")

    # Validate email format
    if not re.match(r'^[^\s@]+@[^\s@]+\.[^\s@]+$', request.email):
        raise HTTPException(status_code=400, detail="Invalid email format")

    # Create user
    user = create_user(db, request.username, request.email, request.password, request.full_name)
    if not user:
        raise HTTPException(status_code=400, detail="Registration failed. User may already exist or password doesn't meet requirements.")

    # Create tokens
    access_token = create_access_token(data={"sub": user.username})
    refresh_token = create_refresh_token(db, user.id)

    logger.info(f"User {user.username} registered successfully")
    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "token_type": "bearer",
        "expires_in": ACCESS_TOKEN_EXPIRE_MINUTES * 60
    }

@app.post(
    "/auth/refresh",
    response_model=LoginResponse,
    summary="Refresh Access Token",
    description="Refresh an expired access token using a valid refresh token",
    tags=["authentication"]
)
async def refresh_token(refresh_token: str = Form(..., description="Refresh token"), db: Session = Depends(get_db)):
    """
    Refresh access token using refresh token.

    - **refresh_token**: Valid refresh token
    """
    new_access_token = refresh_access_token(db, refresh_token)
    if not new_access_token:
        raise HTTPException(status_code=401, detail="Invalid or expired refresh token")

    # Get user from refresh token
    refresh_token_obj = verify_refresh_token(db, refresh_token)
    if not refresh_token_obj:
        raise HTTPException(status_code=401, detail="Invalid refresh token")

    # Create new refresh token (rotate refresh tokens)
    new_refresh_token = create_refresh_token(db, refresh_token_obj.user_id)

    # Revoke old refresh token
    revoke_refresh_token(db, refresh_token)

    logger.info(f"Access token refreshed for user {refresh_token_obj.user.username}")
    return {
        "access_token": new_access_token,
        "refresh_token": new_refresh_token,
        "token_type": "bearer",
        "expires_in": ACCESS_TOKEN_EXPIRE_MINUTES * 60
    }

@app.get(
    "/auth/oauth/{provider}",
    summary="OAuth Login URL",
    description="Get OAuth authorization URL for Google or GitHub",
    tags=["authentication"]
)
async def oauth_login(provider: str, state: Optional[str] = None):
    """
    Get OAuth authorization URL.

    - **provider**: OAuth provider ('google' or 'github')
    - **state**: Optional state parameter for CSRF protection
    """
    if provider not in ['google', 'github']:
        raise HTTPException(status_code=400, detail="Unsupported OAuth provider")

    oauth_service = get_oauth_service()
    try:
        result = oauth_service.get_authorization_url(provider, state)
        return result
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.get(
    "/auth/oauth/{provider}/callback",
    response_model=LoginResponse,
    summary="OAuth Callback",
    description="Handle OAuth callback and authenticate user",
    tags=["authentication"]
)
async def oauth_callback(
    provider: str,
    code: str = Query(..., description="Authorization code"),
    state: str = Query(..., description="State parameter"),
    db: Session = Depends(get_db)
):
    """
    Handle OAuth callback.

    - **provider**: OAuth provider ('google' or 'github')
    - **code**: Authorization code from OAuth provider
    - **state**: State parameter for CSRF protection
    """
    if provider not in ['google', 'github']:
        raise HTTPException(status_code=400, detail="Unsupported OAuth provider")

    oauth_service = get_oauth_service()

    try:
        # Exchange code for token
        token_data = await oauth_service.exchange_code_for_token(provider, code, state)

        # Get user info
        user_info = await oauth_service.get_user_info(provider, token_data['access_token'])

        # Authenticate or create user
        user = await oauth_service.authenticate_or_create_user(db, provider, user_info, token_data)

        # Create tokens
        access_token = create_access_token(data={"sub": user.username})
        refresh_token = create_refresh_token(db, user.id)

        logger.info(f"User {user.username} authenticated via {provider} OAuth")
        return {
            "access_token": access_token,
            "refresh_token": refresh_token,
            "token_type": "bearer",
            "expires_in": ACCESS_TOKEN_EXPIRE_MINUTES * 60
        }

    except Exception as e:
        logger.error(f"OAuth authentication failed for {provider}: {e}")
        raise HTTPException(status_code=400, detail=f"OAuth authentication failed: {str(e)}")

@app.post(
    "/auth/logout",
    response_model=Dict[str, str],
    summary="User Logout",
    description="Logout user and invalidate refresh tokens",
    tags=["authentication"]
)
async def logout(
    refresh_token: str = Form(..., description="Refresh token to revoke"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Logout user by revoking refresh token.

    - **refresh_token**: Refresh token to revoke
    """
    revoke_refresh_token(db, refresh_token)
    logger.info(f"User {current_user.username} logged out")
    return {"message": "Logged out successfully"}

@app.get(
    "/auth/me",
    response_model=Dict[str, Any],
    summary="Current User Profile",
    description="Get current user profile information",
    tags=["authentication"]
)
async def get_current_user_profile(current_user: User = Depends(get_current_active_user), db: Session = Depends(get_db)):
    """Get current user profile"""
    # Get user roles
    roles = [user_role.role.name for user_role in current_user.user_roles]

    # Get user permissions
    permissions = set()
    for user_role in current_user.user_roles:
        for role_permission in user_role.role.role_permissions:
            permissions.add(role_permission.permission.name)

    return {
        "id": current_user.id,
        "username": current_user.username,
        "email": current_user.email,
        "full_name": current_user.full_name,
        "is_active": current_user.is_active,
        "is_superuser": current_user.is_superuser,
        "email_verified": current_user.email_verified,
        "roles": roles,
        "permissions": list(permissions),
        "created_at": current_user.created_at.isoformat(),
        "updated_at": current_user.updated_at.isoformat()
    }

# User profile management endpoints
@app.get(
    "/users/profile",
    response_model=Dict[str, Any],
    summary="Get User Profile",
    description="Get the current user's profile information",
    tags=["users"]
)
async def get_user_profile(current_user: User = Depends(get_current_active_user)):
    """Get current user profile"""
    return {
        "id": current_user.id,
        "username": current_user.username,
        "email": current_user.email,
        "full_name": current_user.full_name,
        "is_active": current_user.is_active,
        "is_superuser": current_user.is_superuser,
        "created_at": current_user.created_at.isoformat(),
        "updated_at": current_user.updated_at.isoformat()
    }

@app.put(
    "/auth/profile",
    response_model=Dict[str, str],
    summary="Update User Profile",
    description="Update current user profile information",
    tags=["authentication"]
)
async def update_user_profile(
    full_name: Optional[str] = Form(None),
    email: Optional[str] = Form(None),
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Update user profile"""
    if full_name is not None:
        current_user.full_name = full_name

    if email is not None:
        # Check if email is already taken
        existing_user = db.query(User).filter(User.email == email, User.id != current_user.id).first()
        if existing_user:
            raise HTTPException(status_code=400, detail="Email already in use")

        current_user.email = email
        current_user.email_verified = False  # Require re-verification

    current_user.updated_at = datetime.now(timezone.utc)
    db.commit()

    logger.info(f"User {current_user.username} updated profile")
    return {"message": "Profile updated successfully"}

@app.post(
    "/auth/forgot-password",
    response_model=Dict[str, str],
    summary="Forgot Password",
    description="Request password reset token",
    tags=["authentication"]
)
async def forgot_password(email: str = Form(..., description="User email"), db: Session = Depends(get_db)):
    """Request password reset"""
    import secrets
    import hashlib

    user = db.query(User).filter(User.email == email).first()
    if not user:
        # Don't reveal if email exists or not
        return {"message": "If the email exists, a password reset link has been sent"}

    # Generate reset token
    token = secrets.token_urlsafe(32)
    token_hash = hashlib.sha256(token.encode()).hexdigest()

    expires_at = datetime.now(timezone.utc) + timedelta(hours=24)  # 24 hour expiry

    reset_token = PasswordResetToken(
        id=secrets.token_urlsafe(16),
        user_id=user.id,
        token_hash=token_hash,
        email=email,
        expires_at=expires_at
    )

    db.add(reset_token)
    db.commit()

    # TODO: Send email with reset link
    # For now, just log it
    reset_url = f"http://localhost:3000/reset-password?token={token}"
    logger.info(f"Password reset requested for {email}. Reset URL: {reset_url}")

    return {"message": "If the email exists, a password reset link has been sent"}

@app.post(
    "/auth/reset-password",
    response_model=Dict[str, str],
    summary="Reset Password",
    description="Reset password using reset token",
    tags=["authentication"]
)
async def reset_password(
    token: str = Form(..., description="Reset token"),
    new_password: str = Form(..., description="New password"),
    db: Session = Depends(get_db)
):
    """Reset password using token"""
    import hashlib

    token_hash = hashlib.sha256(token.encode()).hexdigest()

    reset_token = db.query(PasswordResetToken).filter(
        PasswordResetToken.token_hash == token_hash,
        PasswordResetToken.is_used == False,
        PasswordResetToken.expires_at > datetime.now(timezone.utc)
    ).first()

    if not reset_token:
        raise HTTPException(status_code=400, detail="Invalid or expired reset token")

    user = reset_token.user

    # Validate new password
    if not validate_password(new_password):
        raise HTTPException(status_code=400, detail="Password does not meet security requirements")

    # Update password
    user.hashed_password = get_password_hash(new_password)
    user.password_changed_at = datetime.now(timezone.utc)
    user.failed_login_attempts = 0  # Reset failed attempts
    user.lockout_until = None

    # Mark token as used
    reset_token.is_used = True
    reset_token.used_at = datetime.now(timezone.utc)

    db.commit()

    # Revoke all refresh tokens for security
    revoke_all_user_refresh_tokens(db, user.id)

    logger.info(f"Password reset successful for user {user.username}")
    return {"message": "Password reset successful"}

@app.get(
    "/auth/csrf-token",
    response_model=Dict[str, str],
    summary="Get CSRF Token",
    description="Get a CSRF token for form submissions",
    tags=["authentication"]
)
async def get_csrf_token(current_user: User = Depends(get_current_user)):
    """Get CSRF token"""
    from .csrf_middleware import create_csrf_token
    token = await create_csrf_token(current_user.id)
    return {"csrf_token": token}

# Admin user management endpoints
@app.get(
    "/admin/users",
    response_model=List[Dict[str, Any]],
    summary="List All Users",
    description="Get a list of all users (admin only)",
    tags=["admin"]
)
async def list_all_users(
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """List all users - admin only"""
    if not current_user.is_superuser:
        raise HTTPException(status_code=403, detail="Admin access required")

    users = db.query(User).all()
    return [{
        "id": user.id,
        "username": user.username,
        "email": user.email,
        "full_name": user.full_name,
        "is_active": user.is_active,
        "is_superuser": user.is_superuser,
        "created_at": user.created_at.isoformat(),
        "updated_at": user.updated_at.isoformat()
    } for user in users]

@app.put(
    "/admin/users/{user_id}",
    response_model=Dict[str, str],
    summary="Update User",
    description="Update user information (admin only)",
    tags=["admin"]
)
async def update_user(
    user_id: int,
    user_data: Dict[str, Any],
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Update user - admin only"""
    if not current_user.is_superuser:
        raise HTTPException(status_code=403, detail="Admin access required")

    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    # Update allowed fields
    allowed_fields = ["email", "full_name", "is_active", "is_superuser"]
    for field in allowed_fields:
        if field in user_data:
            setattr(user, field, user_data[field])

    user.updated_at = datetime.now(timezone.utc)
    db.commit()

    logger.info(f"Admin {current_user.username} updated user {user.username}")
    return {"message": "User updated successfully"}

@app.post(
    "/admin/users/{user_id}/ban",
    response_model=Dict[str, str],
    summary="Ban User",
    description="Ban a user account (admin only)",
    tags=["admin"]
)
async def ban_user(
    user_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Ban user - admin only"""
    if not current_user.is_superuser:
        raise HTTPException(status_code=403, detail="Admin access required")

    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    if user.is_superuser:
        raise HTTPException(status_code=400, detail="Cannot ban administrator accounts")

    user.is_active = False
    user.updated_at = datetime.now(timezone.utc)
    db.commit()

    logger.info(f"Admin {current_user.username} banned user {user.username}")
    return {"message": "User banned successfully"}

@app.post(
    "/admin/users/{user_id}/unban",
    response_model=Dict[str, str],
    summary="Unban User",
    description="Unban a user account (admin only)",
    tags=["admin"]
)
async def unban_user(
    user_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Unban user - admin only"""
    if not current_user.is_superuser:
        raise HTTPException(status_code=403, detail="Admin access required")

    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    user.is_active = True
    user.updated_at = datetime.now(timezone.utc)
    db.commit()

    logger.info(f"Admin {current_user.username} unbanned user {user.username}")
    return {"message": "User unbanned successfully"}

@app.delete(
    "/admin/users/{user_id}",
    response_model=Dict[str, str],
    summary="Delete User",
    description="Delete a user account (admin only)",
    tags=["admin"]
)
async def delete_user(
    user_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Delete user - admin only"""
    if not current_user.is_superuser:
        raise HTTPException(status_code=403, detail="Admin access required")

    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    if user.is_superuser:
        raise HTTPException(status_code=400, detail="Cannot delete administrator accounts")

    # Prevent self-deletion
    if user.id == current_user.id:
        raise HTTPException(status_code=400, detail="Cannot delete your own account")

    db.delete(user)
    db.commit()

    logger.info(f"Admin {current_user.username} deleted user {user.username}")
    return {"message": "User deleted successfully"}

@app.put(
    "/users/profile",
    response_model=Dict[str, str],
    summary="Update User Profile",
    description="Update the current user's profile information",
    tags=["users"]
)
async def update_user_profile(
    request: ValidatedUserProfileUpdate,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Update current user profile"""
    updated = False

    if request.email is not None and request.email != current_user.email:
        # Check if email is already taken
        existing_user = db.query(User).filter(
            User.email == request.email,
            User.id != current_user.id
        ).first()
        if existing_user:
            raise HTTPException(status_code=400, detail="Email already registered")

        current_user.email = request.email
        updated = True

    if request.full_name is not None and request.full_name != current_user.full_name:
        current_user.full_name = request.full_name
        updated = True

    if updated:
        current_user.updated_at = datetime.now(timezone.utc)
        db.commit()
        logger.info(f"User {current_user.username} updated profile")
        return {"message": "Profile updated successfully"}
    else:
        return {"message": "No changes made"}

@app.post(
    "/users/change-password",
    response_model=Dict[str, str],
    summary="Change Password",
    description="Change the current user's password",
    tags=["users"]
)
async def change_password(
    request: ValidatedPasswordChange,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Change current user password"""
    # Verify current password
    if not authenticate_user(db, current_user.username, request.current_password):
        raise HTTPException(status_code=400, detail="Current password is incorrect")

    # Hash new password
    from .auth import get_password_hash
    current_user.hashed_password = get_password_hash(request.new_password)
    current_user.updated_at = datetime.now(timezone.utc)
    db.commit()

    logger.info(f"User {current_user.username} changed password")
    return {"message": "Password changed successfully"}

# Model management endpoints
@app.post(
    "/models/switch",
    response_model=Dict[str, str],
    summary="Switch AI Model",
    description="Switch the current user's default AI model for conversations",
    tags=["ai"]
)
async def switch_model(
    request: ValidatedModelSwitch,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Switch user's default AI model"""
    # Verify model exists
    available_models = model_manager.list_models()
    if request.model_name not in available_models:
        raise HTTPException(status_code=400, detail=f"Model '{request.model_name}' not available")

    # For now, store in user preferences (could be added to User model later)
    # This is a placeholder - in a real implementation, you'd add a preferences field to User
    logger.info(f"User {current_user.username} switched to model {request.model_name}")
    return {"message": f"Switched to model '{request.model_name}'", "model": request.model_name}

@app.get(
    "/models/status",
    response_model=Dict[str, Any],
    summary="Get Model Status",
    description="Get the status and information of all available AI models",
    tags=["ai"]
)
async def get_model_status():
    """Get status of all AI models"""
    models = model_manager.list_models()
    model_status = {}

    for model_name, model_info in models.items():
        # Check if model file exists
        config_models = config.get("models", {})
        model_config = config_models.get(model_name, {})
        model_path = model_config.get("path", "")

        status = "available"
        if model_config and not Path(model_path).exists():
            status = "file_not_found"
        elif isinstance(model_info, dict) and model_info.get("type") == "mock_llama":
            status = "mock"

        model_status[model_name] = {
            "name": model_name,
            "status": status,
            "type": model_info.get("type", "unknown") if isinstance(model_info, dict) else "loaded",
            "path": model_path
        }

    return {"models": model_status, "default_model": config["models"]["default_model"]}

# Conversation history endpoints
@app.post(
    "/conversations",
    response_model=Dict[str, str],
    summary="Create Conversation",
    description="Create a new conversation thread",
    tags=["conversations"]
)
async def create_conversation(
    request: ValidatedConversationCreate,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Create a new conversation"""
    conversation_id = str(uuid.uuid4())

    conversation = Conversation(
        id=conversation_id,
        title=request.title,
        model=config["models"]["default_model"],
        created_by=current_user.id,
        is_public=False
    )

    # Add creator as owner participant
    participant = ConversationParticipant(
        conversation_id=conversation_id,
        user_id=current_user.id,
        permission_level="owner"
    )

    db.add(conversation)
    db.add(participant)
    db.commit()

    # Log activity
    activity = ActivityLog(
        conversation_id=conversation_id,
        user_id=current_user.id,
        activity_type="created",
        details={"title": request.title}
    )
    db.add(activity)
    db.commit()

    logger.info(f"User {current_user.username} created conversation {conversation_id}")
    return {"conversation_id": conversation_id, "title": conversation.title}

@app.get(
    "/conversations",
    response_model=List[Dict[str, Any]],
    summary="List Conversations",
    description="Get a list of conversations the current user participates in",
    tags=["conversations"]
)
async def list_conversations(
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """List user's conversations"""
    # Get conversations where user is a participant
    conversations = db.query(Conversation).join(
        ConversationParticipant,
        Conversation.id == ConversationParticipant.conversation_id
    ).filter(
        ConversationParticipant.user_id == current_user.id
    ).order_by(Conversation.updated_at.desc()).all()

    result = []
    for conv in conversations:
        # Get message count
        message_count = db.query(Message).filter(
            Message.conversation_id == conv.id
        ).count()

        # Get participant info
        participant = db.query(ConversationParticipant).filter(
            ConversationParticipant.conversation_id == conv.id,
            ConversationParticipant.user_id == current_user.id
        ).first()

        # Get participant count
        participant_count = db.query(ConversationParticipant).filter(
            ConversationParticipant.conversation_id == conv.id
        ).count()

        result.append({
            "id": conv.id,
            "title": conv.title,
            "model": conv.model,
            "is_public": conv.is_public,
            "permission_level": participant.permission_level if participant else "viewer",
            "participant_count": participant_count,
            "message_count": message_count,
            "created_at": conv.created_at.isoformat(),
            "updated_at": conv.updated_at.isoformat()
        })

    return result

@app.get(
    "/conversations/{conversation_id}",
    response_model=Dict[str, Any],
    summary="Get Conversation",
    description="Get a specific conversation with all its messages",
    tags=["conversations"]
)
async def get_conversation(
    conversation_id: str,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Get a specific conversation with messages"""
    # Check if user has access to this conversation
    participant = db.query(ConversationParticipant).filter(
        ConversationParticipant.conversation_id == conversation_id,
        ConversationParticipant.user_id == current_user.id
    ).first()

    if not participant:
        raise HTTPException(status_code=404, detail="Conversation not found or access denied")

    conversation = db.query(Conversation).filter(
        Conversation.id == conversation_id
    ).first()

    if not conversation:
        raise HTTPException(status_code=404, detail="Conversation not found")

    messages = db.query(Message).filter(
        Message.conversation_id == conversation_id
    ).order_by(Message.created_at).all()

    message_list = []
    for msg in messages:
        message_list.append({
            "id": msg.id,
            "role": msg.role,
            "content": msg.content,
            "model": msg.model,
            "tokens_used": msg.tokens_used,
            "user_id": msg.user_id,
            "created_at": msg.created_at.isoformat()
        })

    # Get participants
    participants = db.query(ConversationParticipant).filter(
        ConversationParticipant.conversation_id == conversation_id
    ).all()

    participant_list = []
    for p in participants:
        user = db.query(User).filter(User.id == p.user_id).first()
        if user:
            participant_list.append({
                "user_id": p.user_id,
                "username": user.username,
                "permission_level": p.permission_level,
                "joined_at": p.joined_at.isoformat(),
                "last_active_at": p.last_active_at.isoformat()
            })

    return {
        "id": conversation.id,
        "title": conversation.title,
        "model": conversation.model,
        "is_public": conversation.is_public,
        "created_by": conversation.created_by,
        "user_permission": participant.permission_level,
        "participants": participant_list,
        "messages": message_list,
        "created_at": conversation.created_at.isoformat(),
        "updated_at": conversation.updated_at.isoformat()
    }

@app.delete(
    "/conversations/{conversation_id}",
    response_model=Dict[str, str],
    summary="Delete Conversation",
    description="Delete a conversation and all its messages (owner only)",
    tags=["conversations"]
)
async def delete_conversation(
    conversation_id: str,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Delete a conversation"""
    # Check if user is owner
    participant = db.query(ConversationParticipant).filter(
        ConversationParticipant.conversation_id == conversation_id,
        ConversationParticipant.user_id == current_user.id,
        ConversationParticipant.permission_level == "owner"
    ).first()

    if not participant:
        raise HTTPException(status_code=403, detail="Only conversation owners can delete conversations")

    conversation = db.query(Conversation).filter(
        Conversation.id == conversation_id
    ).first()

    if not conversation:
        raise HTTPException(status_code=404, detail="Conversation not found")

    # Delete will cascade to messages and participants due to relationships
    db.delete(conversation)
    db.commit()

    logger.info(f"User {current_user.username} deleted conversation {conversation_id}")
    return {"message": "Conversation deleted successfully"}

# Collaborative conversation endpoints
@app.post(
    "/conversations/{conversation_id}/join",
    response_model=Dict[str, str],
    summary="Join Conversation",
    description="Join a public conversation or accept an invitation",
    tags=["conversations"]
)
async def join_conversation(
    conversation_id: str,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Join a conversation"""
    conversation = db.query(Conversation).filter(Conversation.id == conversation_id).first()
    if not conversation:
        raise HTTPException(status_code=404, detail="Conversation not found")

    # Check if already a participant
    existing_participant = db.query(ConversationParticipant).filter(
        ConversationParticipant.conversation_id == conversation_id,
        ConversationParticipant.user_id == current_user.id
    ).first()

    if existing_participant:
        return {"message": "Already a participant in this conversation"}

    # For now, allow joining public conversations
    if not conversation.is_public:
        raise HTTPException(status_code=403, detail="This conversation is private")

    # Add as viewer
    participant = ConversationParticipant(
        conversation_id=conversation_id,
        user_id=current_user.id,
        permission_level="viewer"
    )

    db.add(participant)

    # Log activity
    activity = ActivityLog(
        conversation_id=conversation_id,
        user_id=current_user.id,
        activity_type="joined",
        details={"permission_level": "viewer"}
    )
    db.add(activity)

    db.commit()

    logger.info(f"User {current_user.username} joined conversation {conversation_id}")
    return {"message": "Successfully joined conversation"}

@app.post(
    "/conversations/{conversation_id}/leave",
    response_model=Dict[str, str],
    summary="Leave Conversation",
    description="Leave a conversation (owners cannot leave, must delete instead)",
    tags=["conversations"]
)
async def leave_conversation(
    conversation_id: str,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Leave a conversation"""
    participant = db.query(ConversationParticipant).filter(
        ConversationParticipant.conversation_id == conversation_id,
        ConversationParticipant.user_id == current_user.id
    ).first()

    if not participant:
        raise HTTPException(status_code=404, detail="Not a participant in this conversation")

    if participant.permission_level == "owner":
        raise HTTPException(status_code=400, detail="Owners cannot leave conversations. Delete the conversation instead.")

    # Remove participant
    db.delete(participant)

    # Log activity
    activity = ActivityLog(
        conversation_id=conversation_id,
        user_id=current_user.id,
        activity_type="left",
        details={}
    )
    db.add(activity)

    db.commit()

    logger.info(f"User {current_user.username} left conversation {conversation_id}")
    return {"message": "Successfully left conversation"}

@app.put(
    "/conversations/{conversation_id}/permissions/{user_id}",
    response_model=Dict[str, str],
    summary="Update User Permissions",
    description="Update another user's permissions in a conversation (owner only)",
    tags=["conversations"]
)
async def update_user_permissions(
    conversation_id: str,
    user_id: int,
    permission_level: str,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Update user permissions in a conversation"""
    # Check if current user is owner
    owner_check = db.query(ConversationParticipant).filter(
        ConversationParticipant.conversation_id == conversation_id,
        ConversationParticipant.user_id == current_user.id,
        ConversationParticipant.permission_level == "owner"
    ).first()

    if not owner_check:
        raise HTTPException(status_code=403, detail="Only owners can manage permissions")

    if permission_level not in ["viewer", "editor", "owner"]:
        raise HTTPException(status_code=400, detail="Invalid permission level")

    # Prevent demoting self if only owner
    if user_id == current_user.id and permission_level != "owner":
        owner_count = db.query(ConversationParticipant).filter(
            ConversationParticipant.conversation_id == conversation_id,
            ConversationParticipant.permission_level == "owner"
        ).count()
        if owner_count <= 1:
            raise HTTPException(status_code=400, detail="Cannot demote the last owner")

    participant = db.query(ConversationParticipant).filter(
        ConversationParticipant.conversation_id == conversation_id,
        ConversationParticipant.user_id == user_id
    ).first()

    if not participant:
        raise HTTPException(status_code=404, detail="User is not a participant in this conversation")

    old_permission = participant.permission_level
    participant.permission_level = permission_level

    # Log activity
    activity = ActivityLog(
        conversation_id=conversation_id,
        user_id=current_user.id,
        activity_type="permission_change",
        details={
            "target_user_id": user_id,
            "old_permission": old_permission,
            "new_permission": permission_level
        }
    )
    db.add(activity)

    db.commit()

    logger.info(f"User {current_user.username} changed permissions for user {user_id} in conversation {conversation_id}")
    return {"message": f"User permissions updated to {permission_level}"}

@app.get(
    "/conversations/{conversation_id}/activities",
    response_model=List[Dict[str, Any]],
    summary="Get Conversation Activities",
    description="Get recent activities in a conversation",
    tags=["conversations"]
)
async def get_conversation_activities(
    conversation_id: str,
    limit: int = Query(50, description="Maximum number of activities to return", ge=1, le=200),
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Get conversation activities"""
    # Check access
    participant = db.query(ConversationParticipant).filter(
        ConversationParticipant.conversation_id == conversation_id,
        ConversationParticipant.user_id == current_user.id
    ).first()

    if not participant:
        raise HTTPException(status_code=404, detail="Conversation not found or access denied")

    activities = db.query(ActivityLog).filter(
        ActivityLog.conversation_id == conversation_id
    ).order_by(ActivityLog.created_at.desc()).limit(limit).all()

    result = []
    for activity in activities:
        user = db.query(User).filter(User.id == activity.user_id).first()
        result.append({
            "id": activity.id,
            "user_id": activity.user_id,
            "username": user.username if user else "Unknown",
            "activity_type": activity.activity_type,
            "details": activity.details,
            "created_at": activity.created_at.isoformat()
        })

    return result

# User presence endpoints
@app.post(
    "/presence/online",
    response_model=Dict[str, str],
    summary="Set User Online",
    description="Mark user as online and optionally set current conversation",
    tags=["presence"]
)
async def set_user_online(
    conversation_id: Optional[str] = None,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Set user as online"""
    presence = db.query(UserPresence).filter(UserPresence.user_id == current_user.id).first()

    if not presence:
        presence = UserPresence(user_id=current_user.id)

    presence.is_online = True
    presence.last_seen = datetime.now(timezone.utc)
    presence.current_conversation_id = conversation_id

    if not presence.id:  # New record
        db.add(presence)

    db.commit()

    logger.info(f"User {current_user.username} set online")
    return {"message": "User marked as online"}

@app.post(
    "/presence/offline",
    response_model=Dict[str, str],
    summary="Set User Offline",
    description="Mark user as offline",
    tags=["presence"]
)
async def set_user_offline(
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Set user as offline"""
    presence = db.query(UserPresence).filter(UserPresence.user_id == current_user.id).first()

    if presence:
        presence.is_online = False
        presence.last_seen = datetime.now(timezone.utc)
        presence.current_conversation_id = None
        db.commit()

    logger.info(f"User {current_user.username} set offline")
    return {"message": "User marked as offline"}

@app.get(
    "/presence/online-users",
    response_model=List[Dict[str, Any]],
    summary="Get Online Users",
    description="Get list of currently online users",
    tags=["presence"]
)
async def get_online_users(
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Get online users"""
    online_users = db.query(UserPresence).filter(
        UserPresence.is_online == True
    ).all()

    result = []
    for presence in online_users:
        user = db.query(User).filter(User.id == presence.user_id).first()
        if user:
            result.append({
                "user_id": user.id,
                "username": user.username,
                "current_conversation_id": presence.current_conversation_id,
                "last_seen": presence.last_seen.isoformat()
            })

    return result

# Collaborative documents endpoints
@app.post(
    "/conversations/{conversation_id}/documents",
    response_model=Dict[str, str],
    summary="Create Document",
    description="Create a new collaborative document in a conversation",
    tags=["documents"]
)
async def create_document(
    conversation_id: str,
    title: str,
    document_type: str,
    content: str = "",
    language: Optional[str] = None,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Create a collaborative document"""
    # Check permissions
    participant = db.query(ConversationParticipant).filter(
        ConversationParticipant.conversation_id == conversation_id,
        ConversationParticipant.user_id == current_user.id
    ).first()

    if not participant or participant.permission_level == "viewer":
        raise HTTPException(status_code=403, detail="Insufficient permissions to create documents")

    if document_type not in ["prompt", "code", "note"]:
        raise HTTPException(status_code=400, detail="Invalid document type")

    document_id = str(uuid.uuid4())

    document = CollaborativeDocument(
        id=document_id,
        conversation_id=conversation_id,
        title=title,
        document_type=document_type,
        content=content,
        language=language,
        created_by=current_user.id
    )

    db.add(document)

    # Log activity
    activity = ActivityLog(
        conversation_id=conversation_id,
        user_id=current_user.id,
        activity_type="document_created",
        details={"document_id": document_id, "title": title, "type": document_type}
    )
    db.add(activity)

    db.commit()

    logger.info(f"User {current_user.username} created document {document_id} in conversation {conversation_id}")
    return {"document_id": document_id, "message": "Document created successfully"}

@app.get(
    "/conversations/{conversation_id}/documents",
    response_model=List[Dict[str, Any]],
    summary="List Documents",
    description="Get all documents in a conversation",
    tags=["documents"]
)
async def list_documents(
    conversation_id: str,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """List conversation documents"""
    # Check access
    participant = db.query(ConversationParticipant).filter(
        ConversationParticipant.conversation_id == conversation_id,
        ConversationParticipant.user_id == current_user.id
    ).first()

    if not participant:
        raise HTTPException(status_code=404, detail="Conversation not found or access denied")

    documents = db.query(CollaborativeDocument).filter(
        CollaborativeDocument.conversation_id == conversation_id
    ).order_by(CollaborativeDocument.updated_at.desc()).all()

    result = []
    for doc in documents:
        creator = db.query(User).filter(User.id == doc.created_by).first()
        result.append({
            "id": doc.id,
            "title": doc.title,
            "document_type": doc.document_type,
            "language": doc.language,
            "created_by": doc.created_by,
            "creator_username": creator.username if creator else "Unknown",
            "version": doc.version,
            "created_at": doc.created_at.isoformat(),
            "updated_at": doc.updated_at.isoformat()
        })

    return result

@app.get(
    "/documents/{document_id}",
    response_model=Dict[str, Any],
    summary="Get Document",
    description="Get a specific collaborative document",
    tags=["documents"]
)
async def get_document(
    document_id: str,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Get a document"""
    document = db.query(CollaborativeDocument).filter(CollaborativeDocument.id == document_id).first()
    if not document:
        raise HTTPException(status_code=404, detail="Document not found")

    # Check conversation access
    participant = db.query(ConversationParticipant).filter(
        ConversationParticipant.conversation_id == document.conversation_id,
        ConversationParticipant.user_id == current_user.id
    ).first()

    if not participant:
        raise HTTPException(status_code=404, detail="Document not found or access denied")

    creator = db.query(User).filter(User.id == document.created_by).first()

    return {
        "id": document.id,
        "conversation_id": document.conversation_id,
        "title": document.title,
        "document_type": document.document_type,
        "content": document.content,
        "language": document.language,
        "created_by": document.created_by,
        "creator_username": creator.username if creator else "Unknown",
        "version": document.version,
        "created_at": document.created_at.isoformat(),
        "updated_at": document.updated_at.isoformat()
    }

@app.put(
    "/documents/{document_id}",
    response_model=Dict[str, str],
    summary="Update Document",
    description="Update a collaborative document content",
    tags=["documents"]
)
async def update_document(
    document_id: str,
    content: str,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Update document content"""
    document = db.query(CollaborativeDocument).filter(CollaborativeDocument.id == document_id).first()
    if not document:
        raise HTTPException(status_code=404, detail="Document not found")

    # Check permissions
    participant = db.query(ConversationParticipant).filter(
        ConversationParticipant.conversation_id == document.conversation_id,
        ConversationParticipant.user_id == current_user.id
    ).first()

    if not participant or participant.permission_level == "viewer":
        raise HTTPException(status_code=403, detail="Insufficient permissions to edit documents")

    old_content = document.content
    document.content = content
    document.version += 1

    # Log edit
    edit = DocumentEdit(
        document_id=document_id,
        user_id=current_user.id,
        edit_type="replace",
        position=0,
        old_content=old_content,
        new_content=content
    )
    db.add(edit)

    # Log activity
    activity = ActivityLog(
        conversation_id=document.conversation_id,
        user_id=current_user.id,
        activity_type="document_edited",
        details={"document_id": document_id, "version": document.version}
    )
    db.add(activity)

    db.commit()

    logger.info(f"User {current_user.username} updated document {document_id}")
    return {"message": "Document updated successfully"}

# Plugin management endpoints
@app.get(
    "/plugins",
    response_model=List[Dict[str, Any]],
    summary="List Plugins",
    description="Get a list of all loaded plugins with their status",
    tags=["plugins"]
)
async def list_plugins():
    """List all plugins"""
    return plugin_manager.list_plugins()

@app.post(
    "/plugins/{plugin_id}/load",
    response_model=Dict[str, str],
    summary="Load Plugin",
    description="Load and initialize a specific plugin",
    tags=["plugins"]
)
async def load_plugin(plugin_id: str):
    """Load a plugin"""
    try:
        if plugin_manager.load_plugin(plugin_id):
            return {"message": f"Plugin {plugin_id} loaded successfully"}
        else:
            raise HTTPException(status_code=500, detail=f"Failed to load plugin {plugin_id}")
    except Exception as e:
        logger.error(f"Error loading plugin {plugin_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post(
    "/plugins/{plugin_id}/unload",
    response_model=Dict[str, str],
    summary="Unload Plugin",
    description="Unload and shutdown a specific plugin",
    tags=["plugins"]
)
async def unload_plugin(plugin_id: str):
    """Unload a plugin"""
    try:
        if plugin_manager.unload_plugin(plugin_id):
            return {"message": f"Plugin {plugin_id} unloaded successfully"}
        else:
            raise HTTPException(status_code=404, detail=f"Plugin {plugin_id} not found")
    except Exception as e:
        logger.error(f"Error unloading plugin {plugin_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post(
    "/plugins/{plugin_id}/enable",
    response_model=Dict[str, str],
    summary="Enable Plugin",
    description="Enable a loaded plugin",
    tags=["plugins"]
)
async def enable_plugin(plugin_id: str):
    """Enable a plugin"""
    try:
        if plugin_manager.enable_plugin(plugin_id):
            return {"message": f"Plugin {plugin_id} enabled successfully"}
        else:
            raise HTTPException(status_code=400, detail=f"Failed to enable plugin {plugin_id}")
    except Exception as e:
        logger.error(f"Error enabling plugin {plugin_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post(
    "/plugins/{plugin_id}/disable",
    response_model=Dict[str, str],
    summary="Disable Plugin",
    description="Disable an enabled plugin",
    tags=["plugins"]
)
async def disable_plugin(plugin_id: str):
    """Disable a plugin"""
    try:
        if plugin_manager.disable_plugin(plugin_id):
            return {"message": f"Plugin {plugin_id} disabled successfully"}
        else:
            raise HTTPException(status_code=400, detail=f"Failed to disable plugin {plugin_id}")
    except Exception as e:
        logger.error(f"Error disabling plugin {plugin_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get(
    "/plugins/{plugin_id}/status",
    response_model=Dict[str, Any],
    summary="Get Plugin Status",
    description="Get the current status and information of a specific plugin",
    tags=["plugins"]
)
async def get_plugin_status(plugin_id: str):
    """Get plugin status"""
    try:
        state = plugin_manager.get_plugin_state(plugin_id)
        if state == PluginState.UNLOADED:
            raise HTTPException(status_code=404, detail=f"Plugin {plugin_id} not found")

        plugin_info = None
        if plugin_id in plugin_manager.plugins:
            plugin = plugin_manager.plugins[plugin_id]
            plugin_info = {
                "name": plugin.name,
                "version": plugin.version,
                "state": plugin.state.value,
                "description": plugin.metadata.description if plugin.metadata else "",
                "author": plugin.metadata.author if plugin.metadata else ""
            }

        return {
            "plugin_id": plugin_id,
            "state": state.value,
            "info": plugin_info
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting plugin status for {plugin_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get(
    "/plugins/marketplace",
    response_model=Dict[str, Any],
    summary="Get Available Plugins",
    description="Get list of available plugins from the marketplace",
    tags=["plugins"]
)
async def get_available_plugins():
    """Get available plugins from marketplace"""
    try:
        plugins = plugin_manager.fetch_available_plugins()
        return {
            "plugins": plugins,
            "total": len(plugins)
        }
    except Exception as e:
        logger.error(f"Error fetching available plugins: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post(
    "/plugins/marketplace/{plugin_name}/install",
    response_model=Dict[str, str],
    summary="Install Plugin",
    description="Install a plugin from the marketplace",
    tags=["plugins"]
)
async def install_plugin_from_marketplace(plugin_name: str, version: str = "latest"):
    """Install plugin from marketplace"""
    try:
        if plugin_manager.install_plugin(plugin_name, version):
            return {"message": f"Plugin {plugin_name} installed successfully"}
        else:
            raise HTTPException(status_code=500, detail=f"Failed to install plugin {plugin_name}")
    except Exception as e:
        logger.error(f"Error installing plugin {plugin_name}: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post(
    "/plugins/marketplace/{plugin_name}/uninstall",
    response_model=Dict[str, str],
    summary="Uninstall Plugin",
    description="Uninstall a plugin",
    tags=["plugins"]
)
async def uninstall_plugin_from_marketplace(plugin_name: str):
    """Uninstall plugin"""
    try:
        if plugin_manager.uninstall_plugin(plugin_name):
            return {"message": f"Plugin {plugin_name} uninstalled successfully"}
        else:
            raise HTTPException(status_code=404, detail=f"Plugin {plugin_name} not found")
    except Exception as e:
        logger.error(f"Error uninstalling plugin {plugin_name}: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post(
    "/plugins/marketplace/{plugin_name}/update",
    response_model=Dict[str, str],
    summary="Update Plugin",
    description="Update a plugin to the latest version",
    tags=["plugins"]
)
async def update_plugin_from_marketplace(plugin_name: str):
    """Update plugin"""
    try:
        if plugin_manager.update_plugin(plugin_name):
            return {"message": f"Plugin {plugin_name} updated successfully"}
        else:
            raise HTTPException(status_code=500, detail=f"Failed to update plugin {plugin_name}")
    except Exception as e:
        logger.error(f"Error updating plugin {plugin_name}: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get(
    "/plugins/updates",
    response_model=Dict[str, Any],
    summary="Check Plugin Updates",
    description="Check for available plugin updates",
    tags=["plugins"]
)
async def check_plugin_updates():
    """Check for plugin updates"""
    try:
        updates = plugin_manager.check_plugin_updates()
        return {
            "updates": updates,
            "total": len(updates)
        }
    except Exception as e:
        logger.error(f"Error checking plugin updates: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get(
    "/plugins/{plugin_id}/settings",
    response_model=Dict[str, Any],
    summary="Get Plugin Settings",
    description="Get settings for a specific plugin",
    tags=["plugins"]
)
async def get_plugin_settings(plugin_id: str):
    """Get plugin settings"""
    try:
        if plugin_id not in plugin_manager.plugins:
            raise HTTPException(status_code=404, detail=f"Plugin {plugin_id} not found")

        plugin = plugin_manager.plugins[plugin_id]
        return {
            "plugin_id": plugin_id,
            "settings": plugin._settings
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting settings for plugin {plugin_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.put(
    "/plugins/{plugin_id}/settings",
    response_model=Dict[str, str],
    summary="Update Plugin Settings",
    description="Update settings for a specific plugin",
    tags=["plugins"]
)
async def update_plugin_settings(plugin_id: str, settings: Dict[str, Any]):
    """Update plugin settings"""
    try:
        if plugin_id not in plugin_manager.plugins:
            raise HTTPException(status_code=404, detail=f"Plugin {plugin_id} not found")

        plugin = plugin_manager.plugins[plugin_id]

        # Update settings
        for key, value in settings.items():
            plugin.set_setting(key, value)

        # Notify plugin of settings change
        plugin.on_settings_changed(settings)

        # Save settings
        plugin.save_settings()

        return {"message": f"Settings updated for plugin {plugin_id}"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating settings for plugin {plugin_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# Health and info endpoints
@app.get("/")
async def read_root():
    """Root endpoint with studio information"""
    return {
        "message": f"{config['app']['name']} v{config['app']['version']}",
        "status": "running",
        "features": config.get("features", {})
    }

@app.get("/health")
async def health_check():
    """Comprehensive health check endpoint"""
    health_status = {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "checks": {}
    }

    # Database health check
    try:
        logger.debug("Performing database health check")
        # Simple database connectivity test
        from .database import SessionLocal
        from sqlalchemy import text
        db = SessionLocal()
        result = db.execute(text("SELECT 1"))
        db.close()
        logger.debug("Database health check passed")
        health_status["checks"]["database"] = {"status": "healthy", "details": "Connected"}
    except Exception as e:
        logger.error(f"Database health check failed: {e}")
        health_status["checks"]["database"] = {"status": "unhealthy", "details": str(e)}
        health_status["status"] = "degraded"

    # Model manager health check
    try:
        models = model_manager.list_models()
        loaded_models = sum(1 for m in models.values() if m.get("loaded", False))
        health_status["checks"]["models"] = {
            "status": "healthy",
            "details": f"{loaded_models}/{len(models)} models loaded"
        }
    except Exception as e:
        health_status["checks"]["models"] = {"status": "unhealthy", "details": str(e)}
        health_status["status"] = "degraded"

    # Worker manager health check
    try:
        active_tasks = len([t for t in worker_manager.tasks.values() if t["status"] == "running"])
        health_status["checks"]["workers"] = {
            "status": "healthy",
            "details": f"{active_tasks} active tasks"
        }
    except Exception as e:
        health_status["checks"]["workers"] = {"status": "unhealthy", "details": str(e)}
        health_status["status"] = "degraded"

    # File system health check
    try:
        config_paths = config.get("paths", {})
        for path_name, path_value in config_paths.items():
            if os.path.exists(path_value):
                health_status["checks"][f"filesystem_{path_name}"] = {"status": "healthy", "details": "Accessible"}
            else:
                health_status["checks"][f"filesystem_{path_name}"] = {"status": "warning", "details": "Path not found"}
    except Exception as e:
        health_status["checks"]["filesystem"] = {"status": "unhealthy", "details": str(e)}

    # Overall status determination
    unhealthy_checks = [check for check in health_status["checks"].values() if check["status"] == "unhealthy"]
    if unhealthy_checks:
        health_status["status"] = "unhealthy"
    elif any(check["status"] == "warning" for check in health_status["checks"].values()):
        health_status["status"] = "warning"

    return health_status

@app.get("/models")
async def list_models():
    """List available models"""
    return {"models": model_manager.list_models()}

@app.get("/workers")
async def list_workers():
    """List available workers"""
    return {"workers": worker_manager.list_workers()}

# AI endpoints
@app.post(
    "/enhance_prompt",
    response_model=PromptEnhancementResponse,
    summary="Enhance AI Prompt",
    description="""
    Use AI to enhance and improve a prompt by adding context, clarification, or rephrasing.

    The AI will analyze your input prompt and provide an enhanced version that may:
    - Add more specific context
    - Clarify ambiguous requirements
    - Improve grammar and structure
    - Add relevant constraints or examples

    **Example Request:**
    ```json
    {
      "prompt": "Write a story about cats",
      "model": "llama-2-7b-chat",
      "temperature": 0.7,
      "max_tokens": 256
    }
    ```

    **Example Response:**
    ```json
    {
      "enhanced_prompt": "Write a compelling short story about adventurous cats exploring an ancient Egyptian temple, incorporating elements of mystery, friendship, and discovery. The story should feature 2-3 main cat characters with distinct personalities, include vivid descriptions of the temple's architecture and artifacts, and build suspense through gradual revelations about the temple's secrets."
    }
    ```
    """,
    response_description="Enhanced prompt text",
    tags=["ai"]
)
async def enhance_prompt(request: ValidatedPromptRequest, current_user: User = Depends(get_current_active_user)):
    """
    Enhance a prompt using AI assistance.

    - **prompt**: The original prompt text to enhance (1-10000 characters)
    - **model**: Optional AI model to use (defaults to configured default)
    - **temperature**: Creativity level (0.0-2.0, default 0.7)
    - **max_tokens**: Maximum response length (1-4096, default 512)
    """
    try:
        model_name = request.model or config["models"]["default_model"]
        enhanced = model_manager.generate_text(
            model_name,
            f"Enhance this prompt by providing additional context, clarification, or rephrasing: {request.prompt}",
            max_tokens=request.max_tokens,
            temperature=request.temperature
        )
        logger.info(f"Enhanced prompt for user {current_user.username}")
        return {"enhanced_prompt": enhanced}
    except Exception as e:
        logger.error(f"Error enhancing prompt: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post(
    "/chat",
    response_model=Dict[str, Any],
    summary="Chat with AI",
    description="""
    Have a conversation with an AI model. Send a message and receive an AI-generated response.

    Supports conversation threading via conversation_id for maintaining context
    across multiple messages.

    **Example Request:**
    ```json
    {
      "message": "Explain quantum computing in simple terms",
      "conversation_id": null,
      "model": "llama-2-7b-chat"
    }
    ```

    **Example Response:**
    ```json
    {
      "response": "Quantum computing uses quantum mechanics principles like superposition and entanglement to perform calculations. Unlike classical bits (0 or 1), quantum bits (qubits) can exist in multiple states simultaneously, allowing quantum computers to solve certain problems much faster than classical computers.",
      "conversation_id": "abc123def456",
      "message_id": "msg789ghi012"
    }
    ```
    """,
    response_description="AI response and conversation identifier",
    tags=["ai"]
)
async def chat(request: ValidatedChatRequest, current_user: User = Depends(get_current_active_user), db: Session = Depends(get_db)):
    """
    Send a message to an AI model and receive a response.

    - **message**: Your message to the AI (1-5000 characters)
    - **conversation_id**: Optional conversation thread identifier (32-character hex)
    - **model**: Optional AI model to use (defaults to configured default)
    """
    try:
        model_name = request.model or config["models"]["default_model"]

        # Validate model exists
        available_models = model_manager.list_models()
        if model_name not in available_models:
            raise HTTPException(status_code=400, detail=f"Model '{model_name}' not available")

        # Get or create conversation
        conversation_id = request.conversation_id
        if not conversation_id:
            conversation_id = str(uuid.uuid4())
            conversation = Conversation(
                id=conversation_id,
                title=f"Chat {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M')}",
                model=model_name,
                created_by=current_user.id
            )
            # Add creator as owner participant
            participant = ConversationParticipant(
                conversation_id=conversation_id,
                user_id=current_user.id,
                permission_level="owner"
            )
            db.add(conversation)
            db.add(participant)
            logger.debug(f"Created new conversation {conversation_id} for user {current_user.username}")
        else:
            # Check if user has access to this conversation
            participant = db.query(ConversationParticipant).filter(
                ConversationParticipant.conversation_id == conversation_id,
                ConversationParticipant.user_id == current_user.id
            ).first()
            if not participant:
                raise HTTPException(status_code=404, detail="Conversation not found or access denied")

            conversation = db.query(Conversation).filter(
                Conversation.id == conversation_id
            ).first()
            if not conversation:
                raise HTTPException(status_code=404, detail="Conversation not found")

        # Save user message
        user_message = Message(
            conversation_id=conversation_id,
            user_id=current_user.id,
            role="user",
            content=request.message,
            model=model_name
        )
        db.add(user_message)

        # Generate AI response
        response = model_manager.generate_text(
            model_name,
            request.message,
            max_tokens=256
        )

        # Save AI response
        ai_message = Message(
            conversation_id=conversation_id,
            role="assistant",
            content=response,
            model=model_name,
            tokens_used=len(response.split())  # Rough estimate
        )
        db.add(ai_message)

        # Update conversation timestamp
        conversation.updated_at = datetime.now(timezone.utc)

        db.commit()

        logger.info(f"Chat response for user {current_user.username} in conversation {conversation_id}")
        return {
            "response": response,
            "conversation_id": conversation_id,
            "message_id": str(ai_message.id)
        }
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"Error in chat: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# WebSocket connection manager for real-time chat
class ConnectionManager:
    def __init__(self):
        self.active_connections: Dict[str, List[WebSocket]] = {}  # conversation_id -> list of websockets

    async def connect(self, websocket: WebSocket, conversation_id: str):
        await websocket.accept()
        if conversation_id not in self.active_connections:
            self.active_connections[conversation_id] = []
        self.active_connections[conversation_id].append(websocket)
        logger.info(f"WebSocket connected to conversation {conversation_id}")

    def disconnect(self, websocket: WebSocket, conversation_id: str):
        if conversation_id in self.active_connections:
            if websocket in self.active_connections[conversation_id]:
                self.active_connections[conversation_id].remove(websocket)
            if not self.active_connections[conversation_id]:
                del self.active_connections[conversation_id]
        logger.info(f"WebSocket disconnected from conversation {conversation_id}")

    async def broadcast_to_conversation(self, conversation_id: str, message: Dict[str, Any]):
        """Broadcast message to all connections in a conversation"""
        if conversation_id in self.active_connections:
            disconnected = []
            for websocket in self.active_connections[conversation_id]:
                try:
                    await websocket.send_json(message)
                except Exception as e:
                    logger.error(f"Error sending message to websocket: {e}")
                    disconnected.append(websocket)

            # Clean up disconnected websockets
            for websocket in disconnected:
                self.disconnect(websocket, conversation_id)

manager = ConnectionManager()

# Integrate notification service with WebSocket manager
# Notification WebSocket manager
notification_connections: Dict[int, WebSocket] = {}  # user_id -> websocket

notification_service.set_websocket_manager(manager)
notification_service.set_notification_connections(notification_connections)

@app.websocket("/ws/notifications")
async def websocket_notifications(
    websocket: WebSocket,
    token: str = Query(..., description="JWT access token"),
    db: Session = Depends(get_db)
):
    """
    WebSocket endpoint for real-time notifications.

    - **token**: JWT access token for authentication
    """
    # Authenticate user from token
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        if username is None:
            await websocket.close(code=1008, reason="Invalid token")
            return
    except JWTError:
        await websocket.close(code=1008, reason="Invalid token")
        return

    # Get user
    user = get_user(db, username=username)
    if not user:
        await websocket.close(code=1008, reason="User not found")
        return

    # Connect to notifications
    await websocket.accept()
    notification_connections[user.id] = websocket
    logger.info(f"User {user.username} connected to notification WebSocket")

    try:
        while True:
            # Receive message from client
            data = await websocket.receive_json()

            message_type = data.get("type")

            if message_type == "mark_read":
                # Mark notification as read
                notification_id = data.get("notification_id")
                if notification_id:
                    success = await notification_service.mark_as_read(notification_id, user.id, db)
                    if success:
                        await websocket.send_json({
                            "type": "notification_updated",
                            "content": {"notification_id": notification_id, "status": "read"}
                        })

            elif message_type == "mark_all_read":
                # Mark all notifications as read
                notifications = await notification_service.get_user_notifications(
                    user.id, limit=1000, unread_only=True, db=db
                )

                marked_count = 0
                for notification in notifications:
                    success = await notification_service.mark_as_read(notification['id'], user.id, db)
                    if success:
                        marked_count += 1

                await websocket.send_json({
                    "type": "bulk_update",
                    "content": {"marked_count": marked_count, "status": "read"}
                })

            elif message_type == "ping":
                # Respond to ping
                await websocket.send_json({"type": "pong"})

            else:
                await websocket.send_json({
                    "type": "error",
                    "content": {"message": f"Unknown message type: {message_type}"}
                })

    except WebSocketDisconnect:
        if user.id in notification_connections:
            del notification_connections[user.id]
        logger.info(f"User {user.username} disconnected from notification WebSocket")
    except Exception as e:
        logger.error(f"Notification WebSocket error for user {user.username}: {e}")
        if user.id in notification_connections:
            del notification_connections[user.id]
        try:
            await websocket.close(code=1011, reason="Internal server error")
        except:
            pass

@app.websocket("/ws/chat/{conversation_id}")
async def websocket_chat(
    websocket: WebSocket,
    conversation_id: str,
    token: str = Query(..., description="JWT access token"),
    db: Session = Depends(get_db)
):
    """
    WebSocket endpoint for real-time chat in a conversation.

    - **conversation_id**: The conversation identifier
    - **token**: JWT access token for authentication
    """
    # Authenticate user from token
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        if username is None:
            await websocket.close(code=1008, reason="Invalid token")
            return
    except JWTError:
        await websocket.close(code=1008, reason="Invalid token")
        return

    # Get user
    user = get_user(db, username=username)
    if not user:
        await websocket.close(code=1008, reason="User not found")
        return

    # Verify conversation access
    participant = db.query(ConversationParticipant).filter(
        ConversationParticipant.conversation_id == conversation_id,
        ConversationParticipant.user_id == user.id
    ).first()

    if not participant:
        await websocket.close(code=1008, reason="Conversation not found or access denied")
        return

    conversation = db.query(Conversation).filter(Conversation.id == conversation_id).first()
    if not conversation:
        await websocket.close(code=1008, reason="Conversation not found")
        return

    # Connect to conversation
    await manager.connect(websocket, conversation_id)

    try:
        while True:
            # Receive message from client
            data = await websocket.receive_json()

            message_type = data.get("type")
            content = data.get("content", {})

            if message_type == "chat_message":
                # Process chat message
                user_message = content.get("message", "")
                model_name = content.get("model", conversation.model)

                # Validate model
                available_models = model_manager.list_models()
                if model_name not in available_models:
                    await websocket.send_json({
                        "type": "error",
                        "content": {"message": f"Model '{model_name}' not available"}
                    })
                    continue

                # Save user message
                user_msg = Message(
                    conversation_id=conversation_id,
                    user_id=user.id,
                    role="user",
                    content=user_message,
                    model=model_name
                )
                db.add(user_msg)

                # Generate AI response
                response = model_manager.generate_text(model_name, user_message, max_tokens=256)

                # Save AI response
                ai_msg = Message(
                    conversation_id=conversation_id,
                    role="assistant",
                    content=response,
                    model=model_name,
                    tokens_used=len(response.split())
                )
                db.add(ai_msg)

                # Update conversation timestamp
                conversation.updated_at = datetime.now(timezone.utc)
                db.commit()

                # Broadcast AI response to all connected clients
                response_data = {
                    "type": "ai_response",
                    "content": {
                        "response": response,
                        "conversation_id": conversation_id,
                        "message_id": str(ai_msg.id),
                        "user_id": None,  # AI messages don't have user_id
                        "model": model_name,
                        "timestamp": ai_msg.created_at.isoformat()
                    }
                }
                await manager.broadcast_to_conversation(conversation_id, response_data)

                # Log activity
                activity = ActivityLog(
                    conversation_id=conversation_id,
                    user_id=user.id,
                    activity_type="message",
                    details={"message_type": "ai_response", "model": model_name}
                )
                db.add(activity)
                db.commit()

                logger.info(f"Real-time chat response for user {user.username} in conversation {conversation_id}")

            elif message_type == "ping":
                # Respond to ping
                await websocket.send_json({"type": "pong"})

            elif message_type == "user_presence":
                # Update user presence
                is_online = content.get("is_online", True)
                presence = db.query(UserPresence).filter(UserPresence.user_id == user.id).first()
                if not presence:
                    presence = UserPresence(user_id=user.id)
                    db.add(presence)

                presence.is_online = is_online
                presence.last_seen = datetime.now(timezone.utc)
                presence.current_conversation_id = conversation_id if is_online else None
                db.commit()

                # Broadcast presence update to all conversation participants
                presence_data = {
                    "type": "user_presence_update",
                    "content": {
                        "user_id": user.id,
                        "username": user.username,
                        "is_online": is_online,
                        "conversation_id": conversation_id,
                        "timestamp": presence.last_seen.isoformat()
                    }
                }
                await manager.broadcast_to_conversation(conversation_id, presence_data)

            elif message_type == "document_edit":
                # Handle collaborative document editing
                document_id = content.get("document_id")
                edit_type = content.get("edit_type", "replace")
                position = content.get("position", 0)
                new_content = content.get("content", "")

                # Check permissions
                participant = db.query(ConversationParticipant).filter(
                    ConversationParticipant.conversation_id == conversation_id,
                    ConversationParticipant.user_id == user.id
                ).first()

                if not participant or participant.permission_level == "viewer":
                    await websocket.send_json({
                        "type": "error",
                        "content": {"message": "Insufficient permissions to edit documents"}
                    })
                    continue

                # Get document
                document = db.query(CollaborativeDocument).filter(
                    CollaborativeDocument.id == document_id,
                    CollaborativeDocument.conversation_id == conversation_id
                ).first()

                if not document:
                    await websocket.send_json({
                        "type": "error",
                        "content": {"message": "Document not found"}
                    })
                    continue

                old_content = document.content

                # Apply edit based on type
                if edit_type == "replace":
                    document.content = new_content
                elif edit_type == "insert":
                    document.content = document.content[:position] + new_content + document.content[position:]
                elif edit_type == "delete":
                    delete_length = len(new_content)  # new_content contains the deleted text
                    document.content = document.content[:position] + document.content[position + delete_length:]

                document.version += 1

                # Log edit
                edit = DocumentEdit(
                    document_id=document_id,
                    user_id=user.id,
                    edit_type=edit_type,
                    position=position,
                    old_content=old_content,
                    new_content=document.content
                )
                db.add(edit)

                # Log activity
                activity = ActivityLog(
                    conversation_id=conversation_id,
                    user_id=user.id,
                    activity_type="document_edited",
                    details={"document_id": document_id, "edit_type": edit_type, "version": document.version}
                )
                db.add(activity)

                db.commit()

                # Broadcast document update
                edit_data = {
                    "type": "document_update",
                    "content": {
                        "document_id": document_id,
                        "content": document.content,
                        "version": document.version,
                        "edited_by": user.id,
                        "editor_username": user.username,
                        "edit_type": edit_type,
                        "position": position,
                        "timestamp": datetime.now(timezone.utc).isoformat()
                    }
                }
                await manager.broadcast_to_conversation(conversation_id, edit_data)

            else:
                await websocket.send_json({
                    "type": "error",
                    "content": {"message": f"Unknown message type: {message_type}"}
                })

    except WebSocketDisconnect:
        manager.disconnect(websocket, conversation_id)
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
        manager.disconnect(websocket, conversation_id)
        try:
            await websocket.close(code=1011, reason="Internal server error")
        except:
            pass

@app.post("/code/{task}")
async def code_task(task: str, request: ValidatedCodeRequest, current_user: User = Depends(get_current_active_user)):
    """Code analysis, generation, or refactoring"""
    if task not in ["analyze", "generate", "refactor", "debug"]:
        raise HTTPException(status_code=400, detail="Invalid task type")

    try:
        # Submit as background task
        task_id = await worker_manager.submit_task("code_analysis", {
            "code": request.code,
            "language": request.language,
            "task": task
        })
        return {"task_id": task_id, "status": "submitted"}
    except Exception as e:
        logger.error(f"Error submitting code task: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# Advanced AI Features Endpoints

@app.post(
    "/ai/generate-image",
    response_model=Dict[str, Any],
    summary="Generate Image with AI",
    description="""
    Generate images using Stable Diffusion or other diffusion models.

    Supports real-time preview and various parameters for image generation.
    """,
    tags=["ai"]
)
async def generate_image(request: ValidatedImageGenerationRequest, current_user: User = Depends(get_current_active_user)):
    """
    Generate an image using AI diffusion models.

    - **prompt**: Text description of the image to generate (1-1000 characters)
    - **model**: Optional AI model to use (defaults to configured default)
    - **width/height**: Image dimensions (64-2048 pixels)
    - **steps**: Number of diffusion steps (1-100)
    - **guidance_scale**: How closely to follow the prompt (1.0-20.0)
    - **negative_prompt**: What to avoid in the image (max 500 characters)
    """
    try:
        model_name = request.model or config["models"]["default_model"]

        # Validate model exists and supports image generation
        available_models = model_manager.list_models()
        if model_name not in available_models:
            raise HTTPException(status_code=400, detail=f"Model '{model_name}' not available")

        model_info = available_models[model_name]
        if not (model_info.get("type") == "diffusion" or "diffusion" in model_name.lower()):
            raise HTTPException(status_code=400, detail=f"Model '{model_name}' does not support image generation")

        # Submit as background task for image generation
        task_id = await worker_manager.submit_task("image_generation", {
            "prompt": request.prompt,
            "model": model_name,
            "width": request.width,
            "height": request.height,
            "steps": request.steps,
            "guidance_scale": request.guidance_scale,
            "negative_prompt": request.negative_prompt,
            "user_id": current_user.id
        })

        return {
            "task_id": task_id,
            "status": "generating",
            "estimated_time": "30-120 seconds",
            "model": model_name
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error starting image generation: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post(
    "/ai/complete-code",
    response_model=Dict[str, Any],
    summary="Code Completion and Suggestions",
    description="Get intelligent code completion suggestions based on context",
    tags=["ai"]
)
async def complete_code(request: ValidatedCodeCompletionRequest, current_user: User = Depends(get_current_active_user)):
    """
    Get code completion suggestions.

    - **code**: Current code content
    - **language**: Programming language
    - **cursor_position**: Position in code for completion
    - **context**: Additional context information
    - **model**: Optional AI model to use
    """
    try:
        model_name = request.model or config["models"]["default_model"]

        # Generate completion using AI model
        prompt = f"""Complete the following {request.language} code at the cursor position.
Context: {request.context}

Code:
{request.code[:request.cursor_position]}[CURSOR]{request.code[request.cursor_position:]}

Provide only the completion text, no explanations:"""

        completion = model_manager.generate_text(
            model_name,
            prompt,
            max_tokens=256,
            temperature=0.3
        )

        return {
            "completion": completion.strip(),
            "language": request.language,
            "cursor_position": request.cursor_position,
            "model": model_name
        }
    except Exception as e:
        logger.error(f"Error generating code completion: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post(
    "/ai/engineer-prompt",
    response_model=Dict[str, Any],
    summary="Advanced Prompt Engineering",
    description="Enhance prompts with AI-powered templates and suggestions",
    tags=["ai"]
)
async def engineer_prompt(request: ValidatedPromptEngineeringRequest, current_user: User = Depends(get_current_active_user)):
    """
    Engineer and enhance prompts using AI.

    - **base_prompt**: Original prompt to enhance
    - **task_type**: Type of task (creative, technical, business, educational, other)
    - **style**: Writing style preference
    - **length**: Desired prompt length
    - **model**: Optional AI model to use
    """
    try:
        model_name = request.model or config["models"]["default_model"]

        enhancement_prompt = f"""Enhance this prompt for a {request.task_type} task with {request.style} style and {request.length} length:

Original: {request.base_prompt}

Provide an enhanced version that is more effective and detailed:"""

        enhanced_prompt = model_manager.generate_text(
            model_name,
            enhancement_prompt,
            max_tokens=512,
            temperature=0.7
        )

        # Generate template suggestions
        template_prompt = f"Generate 3 alternative prompt templates for {request.task_type} tasks in {request.style} style:"
        templates = model_manager.generate_text(
            model_name,
            template_prompt,
            max_tokens=300,
            temperature=0.8
        )

        return {
            "enhanced_prompt": enhanced_prompt.strip(),
            "templates": templates.strip().split('\n\n')[:3],
            "task_type": request.task_type,
            "style": request.style,
            "model": model_name
        }
    except Exception as e:
        logger.error(f"Error engineering prompt: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post(
    "/ai/multimodal",
    response_model=Dict[str, Any],
    summary="Multi-modal AI Interaction",
    description="Process text, images, and code together for comprehensive AI responses",
    tags=["ai"]
)
async def multimodal_interaction(request: ValidatedMultiModalRequest, current_user: User = Depends(get_current_active_user)):
    """
    Handle multi-modal AI interactions.

    - **text_prompt**: Text input
    - **image_data**: Base64 encoded image data
    - **code_content**: Code to analyze or generate
    - **task**: Type of task (analyze, generate, convert, describe, combine)
    - **model**: Optional AI model to use
    """
    try:
        model_name = request.model or config["models"]["default_model"]

        # Build comprehensive prompt from all modalities
        prompt_parts = []
        if request.text_prompt:
            prompt_parts.append(f"Text: {request.text_prompt}")
        if request.image_data:
            prompt_parts.append("Image: [Image data provided]")
        if request.code_content:
            prompt_parts.append(f"Code: {request.code_content}")

        combined_prompt = f"Task: {request.task}\n\n" + "\n\n".join(prompt_parts)
        combined_prompt += "\n\nProvide a comprehensive response combining all provided inputs:"

        response = model_manager.generate_text(
            model_name,
            combined_prompt,
            max_tokens=1024,
            temperature=0.7
        )

        return {
            "response": response.strip(),
            "task": request.task,
            "modalities_used": {
                "text": bool(request.text_prompt),
                "image": bool(request.image_data),
                "code": bool(request.code_content)
            },
            "model": model_name
        }
    except Exception as e:
        logger.error(f"Error in multimodal interaction: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post(
    "/ai/refactor-code",
    response_model=Dict[str, Any],
    summary="AI-Powered Code Refactoring",
    description="Get AI suggestions for code refactoring and optimization",
    tags=["ai"]
)
async def refactor_code(request: ValidatedCodeRefactoringRequest, current_user: User = Depends(get_current_active_user)):
    """
    Refactor code using AI suggestions.

    - **code**: Code to refactor
    - **language**: Programming language
    - **refactoring_type**: Type of refactoring (optimize, simplify, modernize, security, performance)
    - **model**: Optional AI model to use
    """
    try:
        model_name = request.model or config["models"]["default_model"]

        refactor_prompt = f"""Refactor this {request.language} code for {request.refactoring_type}:

{request.code}

Provide the refactored version with explanations of changes:"""

        refactored_code = model_manager.generate_text(
            model_name,
            refactor_prompt,
            max_tokens=2048,
            temperature=0.3
        )

        return {
            "refactored_code": refactored_code.strip(),
            "language": request.language,
            "refactoring_type": request.refactoring_type,
            "model": model_name
        }
    except Exception as e:
        logger.error(f"Error refactoring code: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post(
    "/ai/convert",
    response_model=Dict[str, Any],
    summary="Convert Between Text and Images",
    description="Convert between text and image formats using AI",
    tags=["ai"]
)
async def convert_content(request: ValidatedConversionRequest, current_user: User = Depends(get_current_active_user)):
    """
    Convert between different content types.

    - **input_type**: Type of input (text or image)
    - **output_type**: Desired output type (text or image)
    - **content**: Input content
    - **model**: Optional AI model to use
    """
    try:
        model_name = request.model or config["models"]["default_model"]

        if request.input_type == "text" and request.output_type == "image":
            # Text to image
            task_id = await worker_manager.submit_task("text_to_image", {
                "text": request.content,
                "model": model_name,
                "user_id": current_user.id
            })
            return {
                "task_id": task_id,
                "conversion_type": "text_to_image",
                "status": "processing"
            }

        elif request.input_type == "image" and request.output_type == "text":
            # Image to text (captioning)
            caption_prompt = f"Describe this image in detail: [Image data would be processed here]"
            caption = model_manager.generate_text(
                model_name,
                caption_prompt,
                max_tokens=256,
                temperature=0.7
            )
            return {
                "result": caption.strip(),
                "conversion_type": "image_to_text",
                "model": model_name
            }

        else:
            raise HTTPException(status_code=400, detail="Unsupported conversion type")

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error converting content: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post(
    "/ai/explain-code",
    response_model=Dict[str, Any],
    summary="Code Explanation and Documentation",
    description="Generate explanations and documentation for code",
    tags=["ai"]
)
async def explain_code(request: ValidatedCodeExplanationRequest, current_user: User = Depends(get_current_active_user)):
    """
    Explain code with AI-generated documentation.

    - **code**: Code to explain
    - **language**: Programming language
    - **explanation_level**: Beginner, intermediate, or advanced
    - **include_examples**: Whether to include code examples
    - **model**: Optional AI model to use
    """
    try:
        model_name = request.model or config["models"]["default_model"]

        explain_prompt = f"""Explain this {request.language} code at a {request.explanation_level} level:

{request.code}

{'Include practical examples in the explanation.' if request.include_examples else ''}

Provide a clear, comprehensive explanation:"""

        explanation = model_manager.generate_text(
            model_name,
            explain_prompt,
            max_tokens=1024,
            temperature=0.5
        )

        return {
            "explanation": explanation.strip(),
            "language": request.language,
            "level": request.explanation_level,
            "includes_examples": request.include_examples,
            "model": model_name
        }
    except Exception as e:
        logger.error(f"Error explaining code: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post(
    "/ai/debug",
    response_model=Dict[str, Any],
    summary="AI-Assisted Debugging",
    description="Get AI-powered debugging assistance with error analysis and fix suggestions",
    tags=["ai"]
)
async def debug_code(request: ValidatedDebugRequest, current_user: User = Depends(get_current_active_user)):
    """
    Debug code with AI assistance.

    - **code**: Code to debug
    - **language**: Programming language
    - **error_message**: Error message if available
    - **stack_trace**: Stack trace if available
    - **model**: Optional AI model to use
    """
    try:
        model_name = request.model or config["models"]["default_model"]

        debug_prompt = f"""Debug this {request.language} code:

Code:
{request.code}

{f'Error Message: {request.error_message}' if request.error_message else ''}
{f'Stack Trace: {request.stack_trace}' if request.stack_trace else ''}

Analyze the code for bugs, provide fixes, and explain the issues:"""

        analysis = model_manager.generate_text(
            model_name,
            debug_prompt,
            max_tokens=1024,
            temperature=0.3
        )

        return {
            "analysis": analysis.strip(),
            "language": request.language,
            "has_error_info": bool(request.error_message or request.stack_trace),
            "model": model_name
        }
    except Exception as e:
        logger.error(f"Error debugging code: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# Encyclopedia endpoints
@app.get("/encyclopedia/list")
async def list_encyclopedia():
    """List available encyclopedia topics"""
    try:
        encyclopedia_dir = config["paths"]["encyclopedia_dir"]
        topics = [f.replace('.md', '') for f in os.listdir(encyclopedia_dir) if f.endswith('.md')]
        return {"topics": topics}
    except Exception as e:
        logger.error(f"Error listing encyclopedia: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/encyclopedia/{topic}")
async def get_topic(topic: str):
    """Get content of a specific encyclopedia topic"""
    try:
        encyclopedia_dir = config["paths"]["encyclopedia_dir"]
        file_path = f"{encyclopedia_dir.rstrip('/')}/{topic}.md"
        if os.path.exists(file_path):
            with open(file_path, 'r') as f:
                content = f.read()
            return {"topic": topic, "content": content}
        else:
            raise HTTPException(status_code=404, detail="Topic not found")
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting topic {topic}: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/encyclopedia/search")
async def search_encyclopedia(request: ValidatedSearchRequest):
    """Search encyclopedia for a query"""
    try:
        encyclopedia_dir = config["paths"]["encyclopedia_dir"]
        query = request.query.lower()
        results = []
        for file in os.listdir(encyclopedia_dir):
            if file.endswith('.md'):
                topic = file.replace('.md', '')
                with open(f"{encyclopedia_dir.rstrip('/')}/{file}", 'r') as f:
                    content = f.read()
                if query in content.lower():
                    lines = content.split('\n')
                    matches = [line.strip() for line in lines if query in line.lower()][:request.limit]
                    results.append({"topic": topic, "matches": matches})
        return {"query": request.query, "results": results}
    except Exception as e:
        logger.error(f"Error searching encyclopedia: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# Advanced Search API Endpoints

@app.post(
    "/api/search",
    response_model=Dict[str, Any],
    summary="Advanced Search",
    description="""
    Perform advanced search across all content types with filtering, ranking, and analytics.

    **Features:**
    - Full-text search across conversations, documents, encyclopedia, help articles, and users
    - Advanced filtering by content type, date range, language, tags, and users
    - Intelligent ranking and relevance scoring
    - Real-time search analytics and suggestions
    - Faceted search results

    **Search Syntax:**
    - `"exact phrase"` - Exact phrase search
    - `word1 AND word2` - Both words must be present
    - `word1 OR word2` - Either word can be present
    - `title:"specific title"` - Search in title field only

    **Filters:**
    - `content_types`: List of content types to search in
    - `languages`: Language codes to filter by
    - `date_from`/`date_to`: Date range in ISO format
    - `user_ids`: Filter by specific users
    - `tags`: Filter by tags
    """,
    tags=["search"]
)
async def advanced_search(
    query: str = Query(..., description="Search query string"),
    content_types: Optional[List[str]] = Query(None, description="Content types to search in"),
    languages: Optional[List[str]] = Query(None, description="Language codes to filter by"),
    date_from: Optional[str] = Query(None, description="Start date (ISO format)"),
    date_to: Optional[str] = Query(None, description="End date (ISO format)"),
    user_ids: Optional[List[int]] = Query(None, description="Filter by user IDs"),
    tags: Optional[List[str]] = Query(None, description="Filter by tags"),
    limit: int = Query(50, description="Maximum results to return", ge=1, le=200),
    offset: int = Query(0, description="Results offset for pagination", ge=0),
    sort_by: str = Query("relevance", description="Sort by: relevance, date, title"),
    current_user: User = Depends(get_current_active_user),
    request: Request = None
):
    """
    Advanced search across all content types.

    - **query**: Search query with support for exact phrases and boolean operators
    - **content_types**: Filter by content type (conversation, document, encyclopedia, help, user)
    - **languages**: Filter by language codes
    - **date_from/date_to**: Date range filters
    - **user_ids**: Filter by specific user IDs
    - **tags**: Filter by content tags
    - **limit/offset**: Pagination controls
    - **sort_by**: Sort results by relevance, date, or title
    """
    try:
        filters = {}
        if content_types:
            filters['content_types'] = content_types
        if languages:
            filters['languages'] = languages
        if date_from:
            filters['date_from'] = date_from
        if date_to:
            filters['date_to'] = date_to
        if user_ids:
            filters['user_ids'] = user_ids
        if tags:
            filters['tags'] = tags

        # Get client IP for analytics
        client_ip = getattr(request.client, 'host', None) if request else None
        user_agent = request.headers.get('user-agent') if request else None

        results = await search_service.search(
            query=query,
            filters=filters,
            user_id=current_user.id,
            limit=limit,
            offset=offset,
            sort_by=sort_by,
            ip_address=client_ip,
            user_agent=user_agent
        )

        return results

    except Exception as e:
        logger.error(f"Error in advanced search: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get(
    "/api/search/suggestions",
    response_model=List[str],
    summary="Get Search Suggestions",
    description="Get autocomplete suggestions based on search prefix",
    tags=["search"]
)
async def get_search_suggestions(
    q: str = Query(..., description="Query prefix for suggestions", min_length=1),
    limit: int = Query(10, description="Maximum suggestions to return", ge=1, le=20)
):
    """Get search suggestions for autocomplete"""
    try:
        suggestions = await search_service.get_suggestions(q, limit)
        return suggestions
    except Exception as e:
        logger.error(f"Error getting search suggestions: {e}")
        return []

@app.get(
    "/api/search/popular",
    response_model=List[Dict[str, Any]],
    summary="Get Popular Search Queries",
    description="Get most popular search queries with analytics",
    tags=["search"]
)
async def get_popular_searches(
    limit: int = Query(20, description="Maximum queries to return", ge=1, le=100),
    current_user: User = Depends(get_current_active_user)
):
    """Get popular search queries"""
    if not current_user.is_superuser:
        raise HTTPException(status_code=403, detail="Admin access required")

    try:
        popular = await search_service.get_popular_queries(limit)
        return popular
    except Exception as e:
        logger.error(f"Error getting popular searches: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post(
    "/api/search/save",
    response_model=Dict[str, str],
    summary="Save Search",
    description="Save a search query with filters for later use",
    tags=["search"]
)
async def save_search(
    name: str = Query(..., description="Name for the saved search"),
    query: str = Query(..., description="Search query"),
    filters: Dict[str, Any] = None,
    description: Optional[str] = Query(None, description="Optional description"),
    current_user: User = Depends(get_current_active_user)
):
    """Save a search for later use"""
    try:
        success = await search_service.save_search(
            user_id=current_user.id,
            name=name,
            query=query,
            filters=filters or {},
            description=description
        )

        if success:
            return {"message": "Search saved successfully"}
        else:
            raise HTTPException(status_code=500, detail="Failed to save search")

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error saving search: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get(
    "/api/search/saved",
    response_model=List[Dict[str, Any]],
    summary="Get Saved Searches",
    description="Get user's saved searches",
    tags=["search"]
)
async def get_saved_searches(current_user: User = Depends(get_current_active_user)):
    """Get user's saved searches"""
    try:
        searches = await search_service.get_saved_searches(current_user.id)
        return searches
    except Exception as e:
        logger.error(f"Error getting saved searches: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post(
    "/api/search/export",
    response_model=Dict[str, str],
    summary="Export Search Results",
    description="Export search results to file (JSON, CSV, or PDF)",
    tags=["search"]
)
async def export_search_results(
    query: str = Query(..., description="Search query"),
    filters: Dict[str, Any] = None,
    format: str = Query("json", description="Export format: json, csv, pdf"),
    current_user: User = Depends(get_current_active_user)
):
    """Export search results"""
    if format not in ["json", "csv", "pdf"]:
        raise HTTPException(status_code=400, detail="Invalid export format")

    try:
        export_id = await search_service.export_search_results(
            query=query,
            filters=filters or {},
            format=format,
            user_id=current_user.id
        )

        return {"export_id": export_id, "message": "Export started successfully"}

    except Exception as e:
        logger.error(f"Error exporting search results: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get(
    "/api/search/export/{export_id}",
    summary="Download Search Export",
    description="Download completed search export file",
    tags=["search"]
)
async def download_search_export(
    export_id: str,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Download search export file"""
    from .search_models import SearchExport

    export_record = db.query(SearchExport).filter(
        SearchExport.id == export_id,
        SearchExport.user_id == current_user.id
    ).first()

    if not export_record:
        raise HTTPException(status_code=404, detail="Export not found")

    if export_record.status != "completed":
        raise HTTPException(status_code=400, detail="Export is not yet completed")

    if not export_record.file_path or not os.path.exists(export_record.file_path):
        raise HTTPException(status_code=404, detail="Export file not found")

    # Check expiration
    if export_record.expires_at and datetime.now(timezone.utc) > export_record.expires_at:
        raise HTTPException(status_code=410, detail="Export file has expired")

    return FileResponse(
        path=export_record.file_path,
        filename=f"search_export_{export_id}.{export_record.format}",
        media_type="application/octet-stream"
    )

@app.get(
    "/api/search/stats",
    response_model=Dict[str, Any],
    summary="Get Search Statistics",
    description="Get comprehensive search system statistics (admin only)",
    tags=["search"]
)
async def get_search_stats(current_user: User = Depends(get_current_active_user)):
    """Get search system statistics"""
    if not current_user.is_superuser:
        raise HTTPException(status_code=403, detail="Admin access required")

    try:
        stats = await search_service.get_search_stats()
        return stats
    except Exception as e:
        logger.error(f"Error getting search stats: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post(
    "/api/search/reindex",
    response_model=Dict[str, str],
    summary="Reindex All Content",
    description="Trigger full reindexing of all content (admin only)",
    tags=["search"]
)
async def reindex_content(current_user: User = Depends(get_current_active_user)):
    """Reindex all content"""
    if not current_user.is_superuser:
        raise HTTPException(status_code=403, detail="Admin access required")

    try:
        # Run reindexing in background
        asyncio.create_task(search_service.reindex_all_content())
        return {"message": "Reindexing started in background"}
    except Exception as e:
        logger.error(f"Error starting reindexing: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# File upload/download
@app.post("/upload")
async def upload_file(file: UploadFile = File(...), current_user: User = Depends(get_current_active_user)):
    """Upload a file"""
    try:
        # Validate file upload
        validate_file_upload(file.file, file.filename, file.content_type)

        upload_dir = Path(config["paths"]["uploads_dir"])
        upload_dir.mkdir(exist_ok=True)

        file_path = upload_dir / f"{uuid.uuid4()}_{file.filename}"
        async with aiofiles.open(file_path, 'wb') as f:
            content = await file.read()
            await f.write(content)

        logger.info(f"File uploaded by {current_user.username}: {file.filename}")
        return {"filename": file.filename, "path": str(file_path)}
    except Exception as e:
        logger.error(f"Error uploading file: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# Canvas project management
class CanvasProject(BaseModel):
    id: Optional[str] = None
    name: str = Field(..., description="Project name")
    layers: List[Dict[str, Any]] = Field(..., description="Canvas layers data")
    created_at: Optional[str] = None
    updated_at: Optional[str] = None

class CanvasSaveRequest(BaseModel):
    name: str
    layers: List[Dict[str, Any]]

@app.post("/canvas/save", response_model=Dict[str, str], tags=["canvas"])
async def save_canvas_project(request: CanvasSaveRequest, current_user: User = Depends(get_current_active_user)):
    """Save a canvas project"""
    try:
        project_id = str(uuid.uuid4())
        project_data = {
            "id": project_id,
            "name": request.name,
            "layers": request.layers,
            "user_id": current_user.id,
            "created_at": datetime.now(timezone.utc).isoformat(),
            "updated_at": datetime.now(timezone.utc).isoformat()
        }

        # Save to file (in production, use database)
        projects_dir = Path(config["paths"]["uploads_dir"]) / "projects"
        projects_dir.mkdir(exist_ok=True)

        project_file = projects_dir / f"{project_id}.json"
        with open(project_file, 'w') as f:
            json.dump(project_data, f, indent=2)

        logger.info(f"Canvas project saved by {current_user.username}: {request.name}")
        return {"project_id": project_id, "message": "Project saved successfully"}
    except Exception as e:
        logger.error(f"Error saving canvas project: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/canvas/projects", response_model=List[Dict[str, Any]], tags=["canvas"])
async def list_canvas_projects(current_user: User = Depends(get_current_active_user)):
    """List user's canvas projects"""
    try:
        projects_dir = Path(config["paths"]["uploads_dir"]) / "projects"
        projects_dir.mkdir(exist_ok=True)

        projects = []
        for file_path in projects_dir.glob("*.json"):
            try:
                with open(file_path, 'r') as f:
                    project = json.load(f)
                    if project.get("user_id") == current_user.id:
                        projects.append({
                            "id": project["id"],
                            "name": project["name"],
                            "created_at": project["created_at"],
                            "updated_at": project["updated_at"]
                        })
            except Exception as e:
                logger.warning(f"Error reading project file {file_path}: {e}")

        return sorted(projects, key=lambda x: x["updated_at"], reverse=True)
    except Exception as e:
        logger.error(f"Error listing canvas projects: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/canvas/projects/{project_id}", response_model=CanvasProject, tags=["canvas"])
async def load_canvas_project(project_id: str, current_user: User = Depends(get_current_active_user)):
    """Load a canvas project"""
    try:
        projects_dir = Path(config["paths"]["uploads_dir"]) / "projects"
        project_file = projects_dir / f"{project_id}.json"

        if not project_file.exists():
            raise HTTPException(status_code=404, detail="Project not found")

        with open(project_file, 'r') as f:
            project = json.load(f)

        if project.get("user_id") != current_user.id:
            raise HTTPException(status_code=403, detail="Access denied")

        return CanvasProject(**project)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error loading canvas project: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.delete("/canvas/projects/{project_id}", response_model=Dict[str, str], tags=["canvas"])
async def delete_canvas_project(project_id: str, current_user: User = Depends(get_current_active_user)):
    """Delete a canvas project"""
    try:
        projects_dir = Path(config["paths"]["uploads_dir"]) / "projects"
        project_file = projects_dir / f"{project_id}.json"

        if not project_file.exists():
            raise HTTPException(status_code=404, detail="Project not found")

        # Check ownership
        with open(project_file, 'r') as f:
            project = json.load(f)

        if project.get("user_id") != current_user.id:
            raise HTTPException(status_code=403, detail="Access denied")

        project_file.unlink()
        logger.info(f"Canvas project deleted by {current_user.username}: {project_id}")
        return {"message": "Project deleted successfully"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting canvas project: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# Task management
@app.get("/tasks/{task_id}")
async def get_task_status(task_id: str, current_user: User = Depends(get_current_active_user)):
    """Get status of a background task"""
    try:
        return await worker_manager.get_task_status(task_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"Error getting task status: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# Git utility functions
def run_git_command(command: List[str], cwd: Optional[str] = None) -> str:
    """Run a git command and return the output"""
    try:
        result = subprocess.run(
            ["git"] + command,
            cwd=cwd or str(Path(__file__).parent.parent),
            capture_output=True,
            text=True,
            check=True
        )
        return result.stdout.strip()
    except subprocess.CalledProcessError as e:
        logger.error(f"Git command failed: {' '.join(command)} - {e.stderr}")
        raise HTTPException(status_code=500, detail=f"Git command failed: {e.stderr}")

def get_git_branches() -> List[GitBranch]:
    """Get all git branches"""
    try:
        # Get current branch
        current_branch = run_git_command(["rev-parse", "--abbrev-ref", "HEAD"])

        # Get all branches
        branches_output = run_git_command(["branch", "-a"])

        branches = []
        for line in branches_output.split('\n'):
            if not line.strip():
                continue

            is_current = line.startswith('*')
            branch_name = line.strip().lstrip('*').strip()

            # Skip remote branches for now, focus on local
            if 'remotes/' in branch_name:
                continue

            # Get last commit info
            try:
                last_commit = run_git_command(["rev-parse", branch_name])
                last_commit_date = run_git_command(["log", "-1", "--format=%ci", branch_name])
            except:
                last_commit = None
                last_commit_date = None

            branches.append(GitBranch(
                name=branch_name,
                is_current=is_current,
                is_remote=False,
                last_commit=last_commit,
                last_commit_date=last_commit_date
            ))

        return branches
    except Exception as e:
        logger.error(f"Error getting git branches: {e}")
        return []

def get_git_commits(
    branch: Optional[str] = None,
    author: Optional[str] = None,
    since: Optional[str] = None,
    until: Optional[str] = None,
    limit: int = 50,
    skip: int = 0
) -> List[GitCommit]:
    """Get git commits with optional filters"""
    try:
        command = ["log", "--pretty=format:%H|%s|%an|%ae|%ci|%D", f"--max-count={limit}", f"--skip={skip}"]

        if branch:
            command.append(branch)
        else:
            command.append("--all")

        if author:
            command.extend(["--author", author])

        if since:
            command.extend(["--since", since])

        if until:
            command.extend(["--until", until])

        output = run_git_command(command)

        commits = []
        for line in output.split('\n'):
            if not line.strip():
                continue

            parts = line.split('|', 5)
            if len(parts) < 6:
                continue

            commit_hash, message, author_name, author_email, date, refs = parts

            # Parse refs for tags and branch info
            tags = []
            branch_ref = None
            if refs:
                refs_list = [ref.strip() for ref in refs.split(',')]
                for ref in refs_list:
                    if ref.startswith('tag: '):
                        tags.append(ref[5:])
                    elif ref.startswith('HEAD -> '):
                        branch_ref = ref[8:]
                    elif not ref.startswith('origin/'):
                        branch_ref = ref

            # Get additional stats
            try:
                stats_output = run_git_command(["show", "--stat", "--format=", commit_hash])
                files_changed = len([l for l in stats_output.split('\n') if '|' in l])
                insertions = sum(int(match.group(1)) for match in re.finditer(r'(\d+) insertions', stats_output))
                deletions = sum(int(match.group(1)) for match in re.finditer(r'(\d+) deletions', stats_output))
            except:
                files_changed = None
                insertions = None
                deletions = None

            # Get parents
            try:
                parents_output = run_git_command(["rev-parse", f"{commit_hash}^@"])
                parents = parents_output.split('\n') if parents_output else []
            except:
                parents = []

            commits.append(GitCommit(
                hash=commit_hash,
                message=message,
                author=author_name,
                author_email=author_email,
                date=date,
                branch=branch_ref,
                tags=tags,
                parents=parents,
                files_changed=files_changed,
                insertions=insertions,
                deletions=deletions
            ))

        return commits
    except Exception as e:
        logger.error(f"Error getting git commits: {e}")
        return []

def get_git_authors() -> List[str]:
    """Get list of all commit authors"""
    try:
        output = run_git_command(["log", "--format=%an", "--all"])
        authors = list(set(output.split('\n')))
        return sorted([a for a in authors if a])
    except Exception as e:
        logger.error(f"Error getting git authors: {e}")
        return []

# Git API endpoints
@app.get(
    "/git/branches",
    response_model=List[GitBranch],
    summary="Get Git Branches",
    description="Get a list of all git branches in the repository",
    tags=["git"]
)
async def get_branches():
    """Get all git branches"""
    return get_git_branches()

@app.get(
    "/git/authors",
    response_model=List[str],
    summary="Get Git Authors",
    description="Get a list of all commit authors in the repository",
    tags=["git"]
)
async def get_authors():
    """Get all git commit authors"""
    return get_git_authors()

@app.get(
    "/git/commits",
    response_model=List[GitCommit],
    summary="Get Git Commits",
    description="""
    Get git commit history with optional filtering.

    Supports filtering by branch, author, date range, and pagination.
    """,
    tags=["git"]
)
async def get_commits(
    branch: Optional[str] = Query(None, description="Filter by branch name"),
    author: Optional[str] = Query(None, description="Filter by author name"),
    since: Optional[str] = Query(None, description="Filter commits since date (ISO format or relative like '1 week ago')"),
    until: Optional[str] = Query(None, description="Filter commits until date (ISO format or relative)"),
    limit: int = Query(50, description="Maximum number of commits to return", ge=1, le=1000),
    skip: int = Query(0, description="Number of commits to skip for pagination", ge=0)
):
    """Get git commits with optional filters"""
    return get_git_commits(branch, author, since, until, limit, skip)

@app.get(
    "/git/commits/{commit_hash}",
    response_model=GitCommit,
    summary="Get Commit Details",
    description="Get detailed information about a specific commit",
    tags=["git"]
)
async def get_commit_details(commit_hash: str):
    """Get details of a specific commit"""
    try:
        commits = get_git_commits(limit=1)
        for commit in commits:
            if commit.hash.startswith(commit_hash):
                return commit
        raise HTTPException(status_code=404, detail="Commit not found")
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting commit details: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get(
    "/git/commits/{commit_hash}/diff",
    response_model=Dict[str, Any],
    summary="Get Commit Diff",
    description="Get the diff/patch for a specific commit",
    tags=["git"]
)
async def get_commit_diff(commit_hash: str):
    """Get the diff for a specific commit"""
    try:
        diff_output = run_git_command(["show", "--no-merges", "--format=", commit_hash])
        return {
            "commit_hash": commit_hash,
            "diff": diff_output
        }
    except Exception as e:
        logger.error(f"Error getting commit diff: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get(
    "/git/commits/{commit_hash}/files",
    response_model=Dict[str, Any],
    summary="Get Commit Files",
    description="Get the list of files changed in a specific commit",
    tags=["git"]
)
async def get_commit_files(commit_hash: str):
    """Get files changed in a commit"""
    try:
        files_output = run_git_command(["show", "--name-status", "--format=", commit_hash])
        files = []
        for line in files_output.split('\n'):
            if '\t' in line:
                status, filename = line.split('\t', 1)
                files.append({
                    "status": status,
                    "filename": filename
                })

        return {
            "commit_hash": commit_hash,
            "files": files
        }
    except Exception as e:
        logger.error(f"Error getting commit files: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# Dashboard endpoint
from fastapi.responses import FileResponse

@app.get("/dashboard")
async def dashboard_page():
    """Serve the monitoring dashboard"""
    dashboard_path = Path(__file__).parent.parent / "web_ui" / "dashboard.html"
    return FileResponse(dashboard_path, media_type="text/html")

@app.get("/commits")
async def commits_page():
    """Serve the commit history interface"""
    commits_path = Path(__file__).parent.parent / "web_ui" / "commits.html"
    return FileResponse(commits_path, media_type="text/html")

# Auto-healing endpoints
@app.get(
    "/auto-healing/health-report",
    response_model=Dict[str, Any],
    summary="Get Auto-Healing Health Report",
    description="Get comprehensive health report from the auto-healing service",
    tags=["auto-healing"]
)
async def get_auto_healing_report():
    """Get auto-healing health report"""
    if not auto_healer:
        raise HTTPException(status_code=503, detail="Auto-healing service not available")

    try:
        return auto_healer.get_health_report()
    except Exception as e:
        logger.error(f"Error getting auto-healing report: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post(
    "/auto-healing/restart-service/{service_name}",
    response_model=Dict[str, str],
    summary="Force Restart Service",
    description="Force restart a specific service using the auto-healing system",
    tags=["auto-healing"]
)
async def restart_service(service_name: str):
    """Force restart a service"""
    if not auto_healer:
        raise HTTPException(status_code=503, detail="Auto-healing service not available")

    try:
        success = auto_healer.force_restart_service(service_name)
        if success:
            return {"message": f"Service {service_name} restarted successfully"}
        else:
            raise HTTPException(status_code=500, detail=f"Failed to restart service {service_name}")
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error restarting service {service_name}: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get(
    "/auto-healing/status",
    response_model=Dict[str, Any],
    summary="Get Auto-Healing Service Status",
    description="Get the current status of the auto-healing service",
    tags=["auto-healing"]
)
async def get_auto_healing_status():
    """Get auto-healing service status"""
    if not auto_healer:
        return {
            "status": "unavailable",
            "message": "Auto-healing service not initialized"
        }

    return {
        "status": "running" if auto_healer.is_running else "stopped",
        "services_monitored": len(auto_healer.services_config),
        "health_checks_count": len(auto_healer.health_history),
        "recovery_attempts": auto_healer.recovery_attempts
    }

# Auto-Healing AI Engineer System Endpoints

@app.get(
    "/api/ai-engineer/health",
    response_model=Dict[str, Any],
    summary="Get AI Engineer System Health",
    description="Get comprehensive health status of the auto-healing AI engineer system",
    tags=["ai-engineer"]
)
async def get_ai_engineer_health():
    """Get AI engineer system health status"""
    if not ai_engineer_system:
        raise HTTPException(status_code=503, detail="AI Engineer System not available")

    try:
        return ai_engineer_system.get_system_status()
    except Exception as e:
        logger.error(f"Error getting AI engineer health: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get(
    "/api/ai-engineer/components",
    response_model=List[Dict[str, Any]],
    summary="List AI Components",
    description="Get a list of all AI components managed by the system",
    tags=["ai-engineer"]
)
async def list_ai_components(
    component_type: Optional[str] = Query(None, description="Filter by component type"),
    domain: Optional[str] = Query(None, description="Filter by domain"),
    status: Optional[str] = Query(None, description="Filter by status")
):
    """List AI components with optional filtering"""
    if not ai_engineer_system:
        raise HTTPException(status_code=503, detail="AI Engineer System not available")

    try:
        # Convert string parameters to enums if provided
        component_type_enum = None
        if component_type:
            try:
                from .auto_healing_ai_engineer.core import ComponentType
                component_type_enum = ComponentType(component_type.upper())
            except ValueError:
                raise HTTPException(status_code=400, detail=f"Invalid component type: {component_type}")

        components = ai_engineer_system.list_components(component_type_enum, domain)

        # Apply status filter if provided
        if status:
            components = [c for c in components if c["status"] == status]

        return components
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error listing AI components: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get(
    "/api/ai-engineer/components/{component_id}",
    response_model=Dict[str, Any],
    summary="Get Component Details",
    description="Get detailed information about a specific AI component",
    tags=["ai-engineer"]
)
async def get_ai_component(component_id: str):
    """Get detailed information about a specific AI component"""
    if not ai_engineer_system:
        raise HTTPException(status_code=503, detail="AI Engineer System not available")

    try:
        component = ai_engineer_system.get_component_status(component_id)
        if not component:
            raise HTTPException(status_code=404, detail="Component not found")

        return component
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting AI component {component_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post(
    "/api/ai-engineer/create-component",
    response_model=Dict[str, str],
    summary="Create AI Component",
    description="Request creation of a new AI component",
    tags=["ai-engineer"]
)
async def create_ai_component(
    component_type: str = Form(..., description="Type of component to create"),
    domain: str = Form(..., description="Domain for the component"),
    requirements: str = Form(..., description="JSON string of requirements"),
    engineer_id: Optional[str] = Form(None, description="Specific AI engineer to use")
):
    """Create a new AI component"""
    if not ai_engineer_system:
        raise HTTPException(status_code=503, detail="AI Engineer System not available")

    try:
        # Parse requirements
        import json
        requirements_dict = json.loads(requirements)

        # Convert component type
        from .auto_healing_ai_engineer.core import ComponentType
        component_type_enum = ComponentType(component_type.upper())

        component_id = ai_engineer_system.create_component(
            component_type_enum,
            domain,
            requirements_dict,
            engineer_id
        )

        return {"component_id": component_id, "message": "Component creation initiated"}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except json.JSONDecodeError:
        raise HTTPException(status_code=400, detail="Invalid requirements JSON")
    except Exception as e:
        logger.error(f"Error creating AI component: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post(
    "/api/ai-engineer/heal-component",
    response_model=Dict[str, str],
    summary="Heal AI Component",
    description="Attempt to heal a failing AI component",
    tags=["ai-engineer"]
)
async def heal_ai_component(component_id: str = Form(..., description="ID of component to heal")):
    """Heal a failing AI component"""
    if not ai_engineer_system:
        raise HTTPException(status_code=503, detail="AI Engineer System not available")

    try:
        success = ai_engineer_system.heal_component(component_id)
        if success:
            return {"message": f"Component {component_id} healing initiated"}
        else:
            raise HTTPException(status_code=500, detail=f"Failed to heal component {component_id}")
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error healing AI component {component_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get(
    "/api/ai-engineer/dashboard",
    response_model=Dict[str, Any],
    summary="AI Engineer Dashboard",
    description="Get comprehensive dashboard data for the AI engineer system",
    tags=["ai-engineer"]
)
async def get_ai_engineer_dashboard():
    """Get comprehensive dashboard data"""
    if not ai_engineer_system:
        raise HTTPException(status_code=503, detail="AI Engineer System not available")

    try:
        system_status = ai_engineer_system.get_system_status()
        components = ai_engineer_system.list_components()

        # Get recent health history (last 24 hours)
        recent_health = []
        if hasattr(ai_engineer_system, 'health_history'):
            import datetime
            cutoff = datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(hours=24)
            recent_health = [
                h for h in ai_engineer_system.health_history[-100:]  # Last 100 entries
                if datetime.datetime.fromisoformat(h['timestamp']) > cutoff
            ]

        # Get AI engineers status
        ai_engineers = []
        if hasattr(ai_engineer_system, 'ai_engineers'):
            for engineer_id, engineer in ai_engineer_system.ai_engineers.items():
                ai_engineers.append({
                    "id": engineer.id,
                    "name": engineer.name,
                    "specialization": engineer.specialization,
                    "experience_level": engineer.experience_level,
                    "status": engineer.status,
                    "active_projects": len(engineer.active_projects),
                    "skills": engineer.skills
                })

        return {
            "system_status": system_status,
            "components": components,
            "ai_engineers": ai_engineers,
            "health_history": recent_health[-50:],  # Last 50 entries
            "timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat()
        }
    except Exception as e:
        logger.error(f"Error getting AI engineer dashboard: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get(
    "/api/ai-engineer/metrics",
    response_model=Dict[str, Any],
    summary="AI Engineer Metrics",
    description="Get detailed metrics for the AI engineer system",
    tags=["ai-engineer"]
)
async def get_ai_engineer_metrics():
    """Get detailed system metrics"""
    if not ai_engineer_system:
        raise HTTPException(status_code=503, detail="AI Engineer System not available")

    try:
        # Get system metrics
        system_metrics = ai_engineer_system.system_metrics.copy()

        # Add component type breakdown
        component_types = {}
        domains = {}
        for component in ai_engineer_system.components.values():
            comp_type = component.type.value
            domain = component.domain

            component_types[comp_type] = component_types.get(comp_type, 0) + 1
            domains[domain] = domains.get(domain, 0) + 1

        system_metrics["component_types"] = component_types
        system_metrics["domains"] = domains

        # Add performance metrics
        performance_data = {
            "average_health_score": sum(c.health_score for c in ai_engineer_system.components.values()) / max(1, len(ai_engineer_system.components)),
            "total_components_created": len(ai_engineer_system.components),
            "active_components": len([c for c in ai_engineer_system.components.values() if c.status == "healthy"]),
            "failed_components": len([c for c in ai_engineer_system.components.values() if c.status == "failed"])
        }

        return {
            "system_metrics": system_metrics,
            "performance_data": performance_data,
            "timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat()
        }
    except Exception as e:
        logger.error(f"Error getting AI engineer metrics: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# Import auto-upgrade service
try:
    from scripts.auto_upgrader import AutoUpgrader
    auto_upgrader = AutoUpgrader()
except ImportError:
    auto_upgrader = None

# Import backup manager
try:
    from scripts.backup_restore import BackupManager
    backup_manager = BackupManager(config)
except ImportError:
    backup_manager = None

# Import auto-healing AI engineer system
try:
    from .auto_healing_ai_engineer import get_auto_healing_ai_engineer
    ai_engineer_system = get_auto_healing_ai_engineer()
except ImportError:
    ai_engineer_system = None

# Auto-upgrade endpoints
@app.get(
    "/auto-upgrade/status",
    response_model=Dict[str, Any],
    summary="Get Auto-Upgrade Status",
    description="Get the current status of the auto-upgrade service",
    tags=["auto-upgrade"]
)
async def get_auto_upgrade_status():
    """Get auto-upgrade service status"""
    if not auto_upgrader:
        raise HTTPException(status_code=503, detail="Auto-upgrade service not available")

    try:
        return auto_upgrader.get_upgrade_status()
    except Exception as e:
        logger.error(f"Error getting auto-upgrade status: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get(
    "/auto-upgrade/available-updates",
    response_model=Dict[str, Any],
    summary="Check for Available Updates",
    description="Check all repositories for available updates",
    tags=["auto-upgrade"]
)
async def check_available_updates():
    """Check for available updates"""
    if not auto_upgrader:
        raise HTTPException(status_code=503, detail="Auto-upgrade service not available")

    try:
        return auto_upgrader.list_available_updates()
    except Exception as e:
        logger.error(f"Error checking for updates: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post(
    "/auto-upgrade/manual-upgrade",
    response_model=Dict[str, str],
    summary="Perform Manual Upgrade",
    description="Perform a manual upgrade for a specific component",
    tags=["auto-upgrade"]
)
async def manual_upgrade(request: Dict[str, str]):
    """Perform manual upgrade"""
    if not auto_upgrader:
        raise HTTPException(status_code=503, detail="Auto-upgrade service not available")

    component = request.get("component")
    version = request.get("version")
    download_url = request.get("download_url")

    if not all([component, version, download_url]):
        raise HTTPException(status_code=400, detail="Missing required parameters: component, version, download_url")

    try:
        success = auto_upgrader.manual_upgrade(component, version, download_url)
        if success:
            return {"message": f"Upgrade completed successfully: {component} to {version}"}
        else:
            raise HTTPException(status_code=500, detail=f"Upgrade failed for {component}")
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error performing manual upgrade: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# Enhanced logging endpoints
@app.get(
    "/logging/stats",
    response_model=Dict[str, Any],
    summary="Get Logging Statistics",
    description="Get aggregated logging statistics and performance metrics",
    tags=["logging"]
)
async def get_logging_stats():
    """Get logging statistics"""
    try:
        from .logging_config import enhanced_logger
        return {
            "performance_stats": enhanced_logger.get_performance_stats(),
            "aggregated_stats": enhanced_logger.get_aggregated_stats(),
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        logger.error(f"Error getting logging stats: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get(
    "/logging/performance/{operation}",
    response_model=Dict[str, Any],
    summary="Get Performance Stats for Operation",
    description="Get performance statistics for a specific operation",
    tags=["logging"]
)
async def get_operation_performance(operation: str):
    """Get performance stats for specific operation"""
    try:
        from .logging_config import enhanced_logger
        stats = enhanced_logger.get_performance_stats(operation)
        if not stats:
            raise HTTPException(status_code=404, detail=f"No performance data found for operation: {operation}")
        return stats
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting performance stats: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# Include enhanced metrics router
from .metrics_enhanced import router as enhanced_metrics_router
app.include_router(enhanced_metrics_router, prefix="/metrics", tags=["monitoring"])

# Rate limiting admin endpoints
@app.get(
    "/admin/rate-limits/configs",
    response_model=List[Dict[str, Any]],
    summary="Get Rate Limit Configurations",
    description="Get all rate limit configurations (admin only)",
    tags=["admin", "rate-limiting"]
)
async def get_rate_limit_configs(
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Get all rate limit configurations"""
    if not current_user.is_superuser:
        raise HTTPException(status_code=403, detail="Admin access required")

    configs = db.query(RateLimitConfig).filter(RateLimitConfig.is_active == True).all()
    return [{
        "id": config.id,
        "name": config.name,
        "user_type_id": config.user_type_id,
        "requests_per_minute": config.requests_per_minute,
        "requests_per_hour": config.requests_per_hour,
        "requests_per_day": config.requests_per_day,
        "burst_limit": config.burst_limit,
        "window_seconds": config.window_seconds,
        "description": config.description,
        "created_at": config.created_at.isoformat()
    } for config in configs]

@app.post(
    "/admin/rate-limits/configs",
    response_model=Dict[str, str],
    summary="Create Rate Limit Configuration",
    description="Create a new rate limit configuration (admin only)",
    tags=["admin", "rate-limiting"]
)
async def create_rate_limit_config(
    name: str,
    user_type_id: Optional[int] = None,
    requests_per_minute: int = 60,
    requests_per_hour: int = 1000,
    requests_per_day: int = 5000,
    burst_limit: int = 10,
    window_seconds: int = 60,
    description: Optional[str] = None,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Create a new rate limit configuration"""
    if not current_user.is_superuser:
        raise HTTPException(status_code=403, detail="Admin access required")

    # Check if name already exists
    existing = db.query(RateLimitConfig).filter(RateLimitConfig.name == name).first()
    if existing:
        raise HTTPException(status_code=400, detail="Configuration name already exists")

    config = RateLimitConfig(
        name=name,
        user_type_id=user_type_id,
        requests_per_minute=requests_per_minute,
        requests_per_hour=requests_per_hour,
        requests_per_day=requests_per_day,
        burst_limit=burst_limit,
        window_seconds=window_seconds,
        description=description
    )

    db.add(config)
    db.commit()

    # Reload rate limit configurations
    from .rate_limit_service import initialize_rate_limits, get_rate_limit_service
    import asyncio
    from concurrent.futures import ThreadPoolExecutor
    initialize_rate_limits(db)

    logger.info(f"Admin {current_user.username} created rate limit config: {name}")
    return {"message": "Rate limit configuration created successfully"}

@app.put(
    "/admin/rate-limits/configs/{config_id}",
    response_model=Dict[str, str],
    summary="Update Rate Limit Configuration",
    description="Update an existing rate limit configuration (admin only)",
    tags=["admin", "rate-limiting"]
)
async def update_rate_limit_config(
    config_id: int,
    name: Optional[str] = None,
    requests_per_minute: Optional[int] = None,
    requests_per_hour: Optional[int] = None,
    requests_per_day: Optional[int] = None,
    burst_limit: Optional[int] = None,
    window_seconds: Optional[int] = None,
    description: Optional[str] = None,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Update a rate limit configuration"""
    if not current_user.is_superuser:
        raise HTTPException(status_code=403, detail="Admin access required")

    config = db.query(RateLimitConfig).filter(RateLimitConfig.id == config_id).first()
    if not config:
        raise HTTPException(status_code=404, detail="Configuration not found")

    # Update fields
    if name is not None:
        # Check name uniqueness
        existing = db.query(RateLimitConfig).filter(
            RateLimitConfig.name == name,
            RateLimitConfig.id != config_id
        ).first()
        if existing:
            raise HTTPException(status_code=400, detail="Configuration name already exists")
        config.name = name

    if requests_per_minute is not None:
        config.requests_per_minute = requests_per_minute
    if requests_per_hour is not None:
        config.requests_per_hour = requests_per_hour
    if requests_per_day is not None:
        config.requests_per_day = requests_per_day
    if burst_limit is not None:
        config.burst_limit = burst_limit
    if window_seconds is not None:
        config.window_seconds = window_seconds
    if description is not None:
        config.description = description

    config.updated_at = datetime.now(timezone.utc)
    db.commit()

    # Reload rate limit configurations
    from .rate_limit_service import initialize_rate_limits, get_rate_limit_service
    initialize_rate_limits(db)

    logger.info(f"Admin {current_user.username} updated rate limit config: {config.name}")
    return {"message": "Rate limit configuration updated successfully"}

@app.get(
    "/admin/rate-limits/endpoints",
    response_model=List[Dict[str, Any]],
    summary="Get Endpoint Rate Limits",
    description="Get all endpoint-specific rate limits (admin only)",
    tags=["admin", "rate-limiting"]
)
async def get_endpoint_rate_limits(
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Get all endpoint rate limits"""
    if not current_user.is_superuser:
        raise HTTPException(status_code=403, detail="Admin access required")

    limits = db.query(EndpointRateLimit).filter(EndpointRateLimit.is_active == True).all()
    return [{
        "id": limit.id,
        "endpoint_pattern": limit.endpoint_pattern,
        "method": limit.method,
        "requests_per_minute": limit.requests_per_minute,
        "requests_per_hour": limit.requests_per_hour,
        "burst_limit": limit.burst_limit,
        "window_seconds": limit.window_seconds,
        "priority": limit.priority,
        "description": limit.description,
        "created_at": limit.created_at.isoformat()
    } for limit in limits]

@app.post(
    "/admin/rate-limits/endpoints",
    response_model=Dict[str, str],
    summary="Create Endpoint Rate Limit",
    description="Create a new endpoint-specific rate limit (admin only)",
    tags=["admin", "rate-limiting"]
)
async def create_endpoint_rate_limit(
    endpoint_pattern: str,
    method: str = "*",
    requests_per_minute: int = 30,
    requests_per_hour: int = 500,
    burst_limit: int = 5,
    window_seconds: int = 60,
    priority: int = 0,
    description: Optional[str] = None,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Create a new endpoint rate limit"""
    if not current_user.is_superuser:
        raise HTTPException(status_code=403, detail="Admin access required")

    # Check if pattern+method already exists
    existing = db.query(EndpointRateLimit).filter(
        EndpointRateLimit.endpoint_pattern == endpoint_pattern,
        EndpointRateLimit.method == method
    ).first()
    if existing:
        raise HTTPException(status_code=400, detail="Endpoint rate limit already exists")

    limit = EndpointRateLimit(
        endpoint_pattern=endpoint_pattern,
        method=method,
        requests_per_minute=requests_per_minute,
        requests_per_hour=requests_per_hour,
        burst_limit=burst_limit,
        window_seconds=window_seconds,
        priority=priority,
        description=description
    )

    db.add(limit)
    db.commit()

    # Reload rate limit configurations
    from .rate_limit_service import initialize_rate_limits, get_rate_limit_service
    initialize_rate_limits(db)

    logger.info(f"Admin {current_user.username} created endpoint rate limit: {endpoint_pattern}")
    return {"message": "Endpoint rate limit created successfully"}

@app.get(
    "/admin/rate-limits/users/{user_id}/overrides",
    response_model=List[Dict[str, Any]],
    summary="Get User Rate Limit Overrides",
    description="Get rate limit overrides for a specific user (admin only)",
    tags=["admin", "rate-limiting"]
)
async def get_user_rate_limits(
    user_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Get user-specific rate limit overrides"""
    if not current_user.is_superuser:
        raise HTTPException(status_code=403, detail="Admin access required")

    overrides = db.query(UserRateLimit).filter(
        UserRateLimit.user_id == user_id,
        UserRateLimit.is_active == True
    ).all()

    result = []
    for override in overrides:
        config = db.query(RateLimitConfig).filter(RateLimitConfig.id == override.config_id).first()
        result.append({
            "id": override.id,
            "config_id": override.config_id,
            "config_name": config.name if config else "Unknown",
            "custom_limits": override.custom_limits,
            "is_active": override.is_active,
            "expires_at": override.expires_at.isoformat() if override.expires_at else None,
            "created_by": override.created_by,
            "created_at": override.created_at.isoformat()
        })

    return result

@app.post(
    "/admin/rate-limits/users/{user_id}/overrides",
    response_model=Dict[str, str],
    summary="Create User Rate Limit Override",
    description="Create a rate limit override for a specific user (admin only)",
    tags=["admin", "rate-limiting"]
)
async def create_user_rate_limit_override(
    user_id: int,
    config_id: int,
    custom_limits: Optional[Dict[str, Any]] = None,
    expires_at: Optional[str] = None,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Create a user-specific rate limit override"""
    if not current_user.is_superuser:
        raise HTTPException(status_code=403, detail="Admin access required")

    # Check if user exists
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    # Check if config exists
    config = db.query(RateLimitConfig).filter(RateLimitConfig.id == config_id).first()
    if not config:
        raise HTTPException(status_code=404, detail="Rate limit configuration not found")

    # Check if override already exists
    existing = db.query(UserRateLimit).filter(
        UserRateLimit.user_id == user_id,
        UserRateLimit.config_id == config_id
    ).first()
    if existing:
        raise HTTPException(status_code=400, detail="Override already exists for this user and config")

    expires_datetime = None
    if expires_at:
        try:
            from datetime import datetime
            expires_datetime = datetime.fromisoformat(expires_at.replace('Z', '+00:00'))
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid expires_at format")

    override = UserRateLimit(
        user_id=user_id,
        config_id=config_id,
        custom_limits=custom_limits,
        expires_at=expires_datetime,
        created_by=current_user.id
    )

    db.add(override)
    db.commit()

    # Reload rate limit configurations
    from .rate_limit_service import initialize_rate_limits
    initialize_rate_limits(db)

    logger.info(f"Admin {current_user.username} created rate limit override for user {user_id}")
    return {"message": "User rate limit override created successfully"}

@app.get(
    "/admin/rate-limits/stats",
    response_model=Dict[str, Any],
    summary="Get Rate Limiting Statistics",
    description="Get comprehensive rate limiting statistics (admin only)",
    tags=["admin", "rate-limiting"]
)
async def get_rate_limit_stats(
    hours: int = 24,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Get rate limiting statistics"""
    if not current_user.is_superuser:
        raise HTTPException(status_code=403, detail="Admin access required")

    from .rate_limit_service import get_rate_limit_service
    service = get_rate_limit_service()
    return service.get_rate_limit_stats(db, hours)

@app.post(
    "/admin/rate-limits/clear-cache",
    response_model=Dict[str, str],
    summary="Clear Rate Limit Cache",
    description="Clear all rate limiting caches (admin only)",
    tags=["admin", "rate-limiting"]
)
async def clear_rate_limit_cache(
    current_user: User = Depends(get_current_active_user)
):
    """Clear rate limiting cache"""
    if not current_user.is_superuser:
        raise HTTPException(status_code=403, detail="Admin access required")

    from .rate_limiter import get_rate_limit_manager
    manager = get_rate_limit_manager()

    # Clear in-memory cache
    if hasattr(manager.limiter, 'memory_storage'):
        manager.limiter.memory_storage.clear()

    # Note: Redis cache would need separate clearing if implemented

    logger.info(f"Admin {current_user.username} cleared rate limit cache")
    return {"message": "Rate limit cache cleared successfully"}

# Translation and Internationalization endpoints
@app.get(
    "/api/languages",
    response_model=List[Dict[str, Any]],
    summary="Get Supported Languages",
    description="Get list of all supported languages",
    tags=["i18n"]
)
async def get_supported_languages(db: Session = Depends(get_db)):
    """Get all supported languages"""
    languages = db.query(SupportedLanguage).filter(SupportedLanguage.is_active == True).all()
    return [{
        "code": lang.code,
        "name": lang.name,
        "native_name": lang.native_name,
        "is_rtl": lang.is_rtl
    } for lang in languages]

@app.get(
    "/api/user/language",
    response_model=Dict[str, str],
    summary="Get User Language Preference",
    description="Get current user's language preference",
    tags=["i18n"]
)
async def get_user_language(current_user: User = Depends(get_current_active_user), db: Session = Depends(get_db)):
    """Get user's language preference"""
    preference = db.query(UserLanguagePreference).filter(
        UserLanguagePreference.user_id == current_user.id,
        UserLanguagePreference.is_preferred == True
    ).first()

    if preference:
        return {"language_code": preference.language_code}
    else:
        return {"language_code": "en"}  # Default

@app.put(
    "/api/user/language",
    response_model=Dict[str, str],
    summary="Set User Language Preference",
    description="Set current user's language preference",
    tags=["i18n"]
)
async def set_user_language(language_code: str, current_user: User = Depends(get_current_active_user), db: Session = Depends(get_db)):
    """Set user's language preference"""
    # Validate language code
    supported = db.query(SupportedLanguage).filter(
        SupportedLanguage.code == language_code,
        SupportedLanguage.is_active == True
    ).first()

    if not supported:
        raise HTTPException(status_code=400, detail="Unsupported language code")

    # Remove existing preferred language
    db.query(UserLanguagePreference).filter(
        UserLanguagePreference.user_id == current_user.id,
        UserLanguagePreference.is_preferred == True
    ).update({"is_preferred": False})

    # Add or update preference
    preference = db.query(UserLanguagePreference).filter(
        UserLanguagePreference.user_id == current_user.id,
        UserLanguagePreference.language_code == language_code
    ).first()

    if preference:
        preference.is_preferred = True
        preference.updated_at = datetime.now(timezone.utc)
    else:
        preference = UserLanguagePreference(
            user_id=current_user.id,
            language_code=language_code,
            is_preferred=True
        )
        db.add(preference)

    db.commit()
    return {"message": "Language preference updated"}

@app.get(
    "/api/translations/{namespace}/{key}",
    response_model=Dict[str, Any],
    summary="Get Translation",
    description="Get translation for a specific key in a namespace",
    tags=["i18n"]
)
async def get_translation(namespace: str, key: str, request: Request, db: Session = Depends(get_db)):
    """Get translation for current language with caching"""
    language = getattr(request.state, 'language', 'en')

    # Try cache first
    cache_key = f"{namespace}:{key}:{language}"
    cached_value = await cache_manager.get_translation(namespace, key, language)
    if cached_value is not None:
        return {"value": cached_value, "language": language, "cached": True}

    # Cache miss - query database
    translation = db.query(Translation).filter(
        Translation.namespace == namespace,
        Translation.key == key,
        Translation.language_code == language,
        Translation.is_approved == True
    ).first()

    if translation:
        value = translation.value
    else:
        # Return key if no translation found
        value = f"{namespace}:{key}"

    # Cache the result
    await cache_manager.set_translation(namespace, key, language, value)

    return {"value": value, "language": language, "cached": False}

@app.get(
    "/api/translations/{namespace}",
    response_model=Dict[str, Any],
    summary="Get Namespace Translations",
    description="Get all translations for a namespace in current language",
    tags=["i18n"]
)
async def get_namespace_translations(namespace: str, request: Request, db: Session = Depends(get_db)):
    """Get all translations for a namespace"""
    language = getattr(request.state, 'language', 'en')

    translations = db.query(Translation).filter(
        Translation.namespace == namespace,
        Translation.language_code == language,
        Translation.is_approved == True
    ).all()

    result = {}
    for trans in translations:
        result[trans.key] = trans.value

    return {"translations": result, "language": language, "namespace": namespace}

@app.get(
    "/api/translations",
    response_model=Dict[str, Any],
    summary="Get All Translations",
    description="Get all translations for current language (admin only)",
    tags=["i18n"]
)
async def get_all_translations(request: Request, current_user: User = Depends(get_current_active_user), db: Session = Depends(get_db)):
    """Get all translations for current language"""
    if not current_user.is_superuser:
        raise HTTPException(status_code=403, detail="Admin access required")

    language = getattr(request.state, 'language', 'en')

    translations = db.query(Translation).filter(
        Translation.language_code == language
    ).all()

    result = {}
    for trans in translations:
        if trans.namespace not in result:
            result[trans.namespace] = {}
        result[trans.namespace][trans.key] = {
            "value": trans.value,
            "approved": trans.is_approved
        }

    return {"translations": result, "language": language}

# Plugin management endpoints
@app.get(
    "/api/plugins",
    response_model=List[Dict[str, Any]],
    summary="List Installed Plugins",
    description="Get a list of all installed plugins with their status",
    tags=["plugins"]
)
async def list_plugins():
    """List all installed plugins"""
    return plugin_manager.list_plugins()

@app.post(
    "/api/plugins/{plugin_id}/enable",
    response_model=Dict[str, str],
    summary="Enable Plugin",
    description="Enable a specific plugin",
    tags=["plugins"]
)
async def enable_plugin(plugin_id: str):
    """Enable a plugin"""
    if plugin_manager.enable_plugin(plugin_id):
        return {"message": f"Plugin {plugin_id} enabled successfully"}
    else:
        raise HTTPException(status_code=400, detail=f"Failed to enable plugin {plugin_id}")

@app.post(
    "/api/plugins/{plugin_id}/disable",
    response_model=Dict[str, str],
    summary="Disable Plugin",
    description="Disable a specific plugin",
    tags=["plugins"]
)
async def disable_plugin(plugin_id: str):
    """Disable a plugin"""
    if plugin_manager.disable_plugin(plugin_id):
        return {"message": f"Plugin {plugin_id} disabled successfully"}
    else:
        raise HTTPException(status_code=400, detail=f"Failed to disable plugin {plugin_id}")

@app.delete(
    "/api/plugins/{plugin_id}",
    response_model=Dict[str, str],
    summary="Unload Plugin",
    description="Unload a specific plugin",
    tags=["plugins"]
)
async def unload_plugin(plugin_id: str):
    """Unload a plugin"""
    if plugin_manager.unload_plugin(plugin_id):
        return {"message": f"Plugin {plugin_id} unloaded successfully"}
    else:
        raise HTTPException(status_code=400, detail=f"Failed to unload plugin {plugin_id}")

@app.get(
    "/api/plugins/{plugin_id}/settings",
    response_model=Dict[str, Any],
    summary="Get Plugin Settings",
    description="Get settings for a specific plugin",
    tags=["plugins"]
)
async def get_plugin_settings(plugin_id: str):
    """Get plugin settings"""
    if plugin_id in plugin_manager.plugins:
        plugin = plugin_manager.plugins[plugin_id]
        return {"settings": plugin._settings}
    else:
        raise HTTPException(status_code=404, detail=f"Plugin {plugin_id} not found")

@app.put(
    "/api/plugins/{plugin_id}/settings",
    response_model=Dict[str, str],
    summary="Update Plugin Settings",
    description="Update settings for a specific plugin",
    tags=["plugins"]
)
async def update_plugin_settings(plugin_id: str, settings: Dict[str, Any]):
    """Update plugin settings"""
    if plugin_id in plugin_manager.plugins:
        plugin = plugin_manager.plugins[plugin_id]
        plugin._settings.update(settings)
        plugin_manager._save_plugin_settings(plugin_id, plugin)
        plugin.on_settings_changed(settings)
        return {"message": f"Settings updated for plugin {plugin_id}"}
    else:
        raise HTTPException(status_code=404, detail=f"Plugin {plugin_id} not found")

@app.get(
    "/api/plugins/marketplace",
    response_model=Dict[str, List[Dict[str, Any]]],
    summary="Get Marketplace Plugins",
    description="Get available plugins from the marketplace",
    tags=["plugins"]
)
async def get_marketplace_plugins():
    """Get marketplace plugins"""
    plugins = plugin_manager.fetch_available_plugins()
    return {"plugins": plugins}

@app.post(
    "/api/plugins/marketplace/{plugin_name}/install",
    response_model=Dict[str, str],
    summary="Install Plugin from Marketplace",
    description="Install a plugin from the marketplace",
    tags=["plugins"]
)
async def install_plugin_from_marketplace(plugin_name: str, version: str = "latest"):
    """Install plugin from marketplace"""
    if plugin_manager.install_plugin(plugin_name, version):
        return {"message": f"Plugin {plugin_name} installed successfully"}
    else:
        raise HTTPException(status_code=400, detail=f"Failed to install plugin {plugin_name}")

# Enhanced security endpoints
@app.get(
    "/security/audit-log",
    response_model=Dict[str, Any],
    summary="Get Security Audit Log",
    description="Get security audit log entries with optional filtering",
    tags=["security"]
)
async def get_audit_log(hours: int = 24, event_type: str = None):
    """Get security audit log"""
    try:
        from .security_enhanced import audit_logger
        logs = audit_logger.get_audit_log(hours=hours, event_type=event_type)
        return {
            "logs": logs,
            "total_entries": len(logs),
            "time_range_hours": hours,
            "filter_event_type": event_type
        }
    except Exception as e:
        logger.error(f"Error getting audit log: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get(
    "/security/summary",
    response_model=Dict[str, Any],
    summary="Get Security Summary",
    description="Get security summary statistics and alerts",
    tags=["security"]
)
async def get_security_summary():
    """Get security summary"""
    try:
        from .security_enhanced import audit_logger, advanced_rate_limiter
        summary = audit_logger.get_security_summary()
        summary["blocked_ips"] = advanced_rate_limiter.get_blocked_ips()
        summary["timestamp"] = datetime.now().isoformat()
        return summary
    except Exception as e:
        logger.error(f"Error getting security summary: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post(
    "/security/unblock-ip",
    response_model=Dict[str, str],
    summary="Unblock IP Address",
    description="Manually unblock a previously blocked IP address",
    tags=["security"]
)
async def unblock_ip(ip_address: str):
    """Unblock an IP address"""
    try:
        from .security_enhanced import advanced_rate_limiter
        success = advanced_rate_limiter.unblock_ip(ip_address)
        if success:
            return {"message": f"IP {ip_address} has been unblocked"}
        else:
            raise HTTPException(status_code=404, detail=f"IP {ip_address} was not blocked")
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error unblocking IP: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get(
    "/security/blocked-ips",
    response_model=List[str],
    summary="Get Blocked IP Addresses",
    description="Get list of currently blocked IP addresses",
    tags=["security"]
)
async def get_blocked_ips():
    """Get blocked IPs"""
    try:
        from .security_enhanced import advanced_rate_limiter
        return advanced_rate_limiter.get_blocked_ips()
    except Exception as e:
        logger.error(f"Error getting blocked IPs: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# Feedback and improvement endpoints
@app.post(
    "/feedback/submit",
    response_model=Dict[str, str],
    summary="Submit User Feedback",
    description="Submit user feedback for system improvement",
    tags=["feedback"]
)
async def submit_feedback(
    feedback_type: str,
    content: Dict[str, Any],
    rating: Optional[int] = None,
    current_user: User = Depends(get_current_active_user)
):
    """Submit user feedback"""
    try:
        from .feedback import feedback_collector
        feedback_id = feedback_collector.collect_feedback(
            user_id=str(current_user.id),
            feedback_type=feedback_type,
            content=content,
            rating=rating
        )
        return {"feedback_id": feedback_id, "message": "Feedback submitted successfully"}
    except Exception as e:
        logger.error(f"Error submitting feedback: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get(
    "/feedback/stats",
    response_model=Dict[str, Any],
    summary="Get Feedback Statistics",
    description="Get statistics about user feedback",
    tags=["feedback"]
)
async def get_feedback_stats():
    """Get feedback statistics"""
    try:
        from .feedback import feedback_collector
        return feedback_collector.get_feedback_stats()
    except Exception as e:
        logger.error(f"Error getting feedback stats: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get(
    "/improvements/suggestions",
    response_model=List[Dict[str, Any]],
    summary="Get Improvement Suggestions",
    description="Get top improvement suggestions based on user feedback",
    tags=["improvements"]
)
async def get_improvement_suggestions(limit: int = 10):
    """Get improvement suggestions"""
    try:
        from .feedback import improvement_tracker
        return improvement_tracker.get_top_improvements(limit)
    except Exception as e:
        logger.error(f"Error getting improvement suggestions: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post(
    "/improvements/{improvement_id}/vote",
    response_model=Dict[str, str],
    summary="Vote for Improvement",
    description="Vote for a suggested improvement",
    tags=["improvements"]
)
async def vote_for_improvement(
    improvement_id: str,
    current_user: User = Depends(get_current_active_user)
):
    """Vote for an improvement"""
    try:
        from .feedback import improvement_tracker
        success = improvement_tracker.vote_for_improvement(improvement_id, str(current_user.id))
        if success:
            return {"message": "Vote recorded successfully"}
        else:
            raise HTTPException(status_code=400, detail="Already voted or improvement not found")
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error voting for improvement: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get(
    "/compatibility/check",
    response_model=Dict[str, Any],
    summary="Check API Compatibility",
    description="Check compatibility of client version with requested features",
    tags=["compatibility"]
)
async def check_compatibility(
    client_version: str,
    features: str,  # comma-separated list
):
    """Check API compatibility"""
    try:
        from .feedback import compatibility_manager
        feature_list = [f.strip() for f in features.split(",")]
        return compatibility_manager.check_compatibility(client_version, feature_list)
    except Exception as e:
        logger.error(f"Error checking compatibility: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get(
    "/insights/recommendations",
    response_model=List[str],
    summary="Get AI-Powered Recommendations",
    description="Get AI-powered recommendations based on system data and feedback",
    tags=["insights"]
)
async def get_ai_recommendations():
    """Get AI-powered recommendations"""
    try:
        from .feedback import ai_insights
        from .metrics_enhanced import metrics_collector
        from .feedback import feedback_collector

        system_metrics = metrics_collector.get_system_metrics()
        feedback_stats = feedback_collector.get_feedback_stats()

        return ai_insights.generate_recommendations(system_metrics, feedback_stats)
    except Exception as e:
        logger.error(f"Error getting AI recommendations: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# Backup management endpoints
@app.get(
    "/backup/list",
    response_model=List[Dict[str, Any]],
    summary="List Backups",
    description="Get a list of all available backups with detailed information",
    tags=["backup"]
)
async def list_backups(current_user: User = Depends(get_current_active_user)):
    """List all backups"""
    if not backup_manager:
        raise HTTPException(status_code=503, detail="Backup system not available")

    try:
        return backup_manager.list_backups()
    except Exception as e:
        logger.error(f"Error listing backups: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post(
    "/backup/create",
    response_model=Dict[str, str],
    summary="Create Backup",
    description="Create a new backup with optional encryption and type selection",
    tags=["backup"]
)
async def create_backup(
    name: Optional[str] = None,
    backup_type: str = "full",
    encryption_password: Optional[str] = None,
    current_user: User = Depends(get_current_active_user)
):
    """Create a new backup"""
    if not backup_manager:
        raise HTTPException(status_code=503, detail="Backup system not available")

    if backup_type not in ["full", "incremental"]:
        raise HTTPException(status_code=400, detail="Invalid backup type")

    try:
        backup_path = backup_manager.create_backup(name, backup_type, encryption_password)
        return {"backup_path": backup_path, "message": "Backup created successfully"}
    except Exception as e:
        logger.error(f"Error creating backup: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post(
    "/backup/restore",
    response_model=Dict[str, str],
    summary="Restore Backup",
    description="Restore from a backup archive with optional decryption",
    tags=["backup"]
)
async def restore_backup(
    backup_name: str,
    target_dir: Optional[str] = None,
    decryption_password: Optional[str] = None,
    current_user: User = Depends(get_current_active_user)
):
    """Restore from backup"""
    if not backup_manager:
        raise HTTPException(status_code=503, detail="Backup system not available")

    try:
        success = backup_manager.restore_backup(backup_name, target_dir, decryption_password)
        if success:
            return {"message": "Backup restored successfully"}
        else:
            raise HTTPException(status_code=500, detail="Backup restoration failed")
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error restoring backup: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.delete(
    "/backup/cleanup",
    response_model=Dict[str, str],
    summary="Cleanup Old Backups",
    description="Remove backups older than the retention period",
    tags=["backup"]
)
async def cleanup_backups(
    retention_days: int = 30,
    current_user: User = Depends(get_current_active_user)
):
    """Clean up old backups"""
    if not backup_manager:
        raise HTTPException(status_code=503, detail="Backup system not available")

    try:
        removed = backup_manager.cleanup_old_backups(retention_days)
        return {"message": f"Cleanup completed: {removed} old backups removed"}
    except Exception as e:
        logger.error(f"Error cleaning up backups: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get(
    "/backup/status",
    response_model=Dict[str, Any],
    summary="Backup System Status",
    description="Get the current status of the backup system",
    tags=["backup"]
)
async def get_backup_status(current_user: User = Depends(get_current_active_user)):
    """Get backup system status"""
    if not backup_manager:
        return {
            "status": "unavailable",
            "message": "Backup system not initialized"
        }

    scheduler_running = backup_manager.scheduler_thread and backup_manager.scheduler_thread.is_alive() if hasattr(backup_manager, 'scheduler_thread') else False

    return {
        "status": "running" if scheduler_running else "stopped",
        "cloud_storage": "enabled" if backup_manager.cloud_manager.enabled else "disabled",
        "encryption": "enabled" if backup_manager.encryption_manager.encryption_key else "disabled",
        "incremental_backups": "enabled" if backup_manager.incremental_enabled else "disabled",
        "notifications": "enabled" if backup_manager.notification_manager.enabled else "disabled",
        "last_full_backup": backup_manager.incremental_data.get('last_full_backup')
    }

@app.post(
    "/backup/scheduler/start",
    response_model=Dict[str, str],
    summary="Start Backup Scheduler",
    description="Start the automated backup scheduler",
    tags=["backup"]
)
async def start_backup_scheduler(current_user: User = Depends(get_current_active_user)):
    """Start backup scheduler"""
    if not backup_manager:
        raise HTTPException(status_code=503, detail="Backup system not available")

    try:
        backup_manager.start_scheduler()
        return {"message": "Backup scheduler started"}
    except Exception as e:
        logger.error(f"Error starting backup scheduler: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post(
    "/backup/scheduler/stop",
    response_model=Dict[str, str],
    summary="Stop Backup Scheduler",
    description="Stop the automated backup scheduler",
    tags=["backup"]
)
async def stop_backup_scheduler(current_user: User = Depends(get_current_active_user)):
    """Stop backup scheduler"""
    if not backup_manager:
        raise HTTPException(status_code=503, detail="Backup system not available")

    try:
        backup_manager.stop_scheduler()
        return {"message": "Backup scheduler stopped"}
    except Exception as e:
        logger.error(f"Error stopping backup scheduler: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post(
    "/backup/verify",
    response_model=Dict[str, str],
    summary="Verify Backup Integrity",
    description="Verify the integrity of a backup archive",
    tags=["backup"]
)
async def verify_backup(
    backup_name: str,
    current_user: User = Depends(get_current_active_user)
):
    """Verify backup integrity"""
    if not backup_manager:
        raise HTTPException(status_code=503, detail="Backup system not available")

    try:
        backups = backup_manager.list_backups()
        backup = next((b for b in backups if b['filename'] == backup_name), None)
        if not backup:
            raise HTTPException(status_code=404, detail="Backup not found")

        if backup['checksum_valid']:
            return {"message": "Backup integrity verified", "status": "valid"}
        else:
            return {"message": "Backup integrity check failed", "status": "invalid"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error verifying backup: {e}")
# Cache management endpoints
@app.get(
    "/api/cache/stats",
    response_model=Dict[str, Any],
    summary="Get Cache Statistics",
    description="Get comprehensive cache performance statistics",
    tags=["cache"]
)
async def get_cache_stats(current_user: User = Depends(get_current_active_user)):
    """Get cache statistics"""
    if not current_user.is_superuser:
        raise HTTPException(status_code=403, detail="Admin access required")

    return cache_manager.get_stats()

@app.post(
    "/api/cache/clear",
    response_model=Dict[str, str],
    summary="Clear Cache",
    description="Clear cache by type or all caches",
    tags=["cache"]
)
async def clear_cache(
    cache_type: Optional[str] = None,
    current_user: User = Depends(get_current_active_user)
):
    """Clear cache"""
    if not current_user.is_superuser:
        raise HTTPException(status_code=403, detail="Admin access required")

    success = await cache_manager.clear_cache(cache_type)
    if success:
        cache_desc = f"{cache_type} cache" if cache_type else "all caches"
        return {"message": f"Successfully cleared {cache_desc}"}
    else:
        raise HTTPException(status_code=500, detail="Failed to clear cache")
        raise HTTPException(status_code=500, detail=str(e))

# Data Export/Import endpoints
@app.post(
    "/api/exports",
    response_model=Dict[str, str],
    summary="Create Data Export",
    description="Create a new data export operation with GDPR compliance",
    tags=["data-export"]
)
async def create_export(
    export_type: str,
    format: str,
    data_scope: Dict[str, Any],
    filters: Optional[Dict[str, Any]] = None,
    encryption_password: Optional[str] = None,
    current_user: User = Depends(get_current_active_user),
    request: Request = None
):
    """Create a new data export operation"""
    if export_type not in ["user_data", "conversations", "bulk_admin"]:
        raise HTTPException(status_code=400, detail="Invalid export type")

    # Admin check for bulk exports
    if export_type == "bulk_admin" and not current_user.is_superuser:
        raise HTTPException(status_code=403, detail="Admin access required for bulk export")

    try:
        operation_id = await export_service.create_export_operation(
            user_id=current_user.id,
            export_type=export_type,
            format=format,
            data_scope=data_scope,
            filters=filters,
            encryption_password=encryption_password,
            requested_by_ip=getattr(request.client, 'host', None) if request else None,
            user_agent=request.headers.get('user-agent') if request else None
        )

        return {"operation_id": operation_id, "message": "Export operation created successfully"}
    except Exception as e:
        logger.error(f"Error creating export: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get(
    "/api/exports/{operation_id}",
    response_model=Dict[str, Any],
    summary="Get Export Status",
    description="Get the status and details of an export operation",
    tags=["data-export"]
)
async def get_export_status(
    operation_id: str,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Get export operation status"""
    operation = db.query(ExportOperation).filter(ExportOperation.id == operation_id).first()
    if not operation:
        raise HTTPException(status_code=404, detail="Export operation not found")

    # Check ownership (users can only see their own exports, admins can see all)
    if operation.user_id != current_user.id and not current_user.is_superuser:
        raise HTTPException(status_code=403, detail="Access denied")

    return {
        "id": operation.id,
        "user_id": operation.user_id,
        "export_type": operation.export_type,
        "format": operation.format,
        "status": operation.status,
        "progress": operation.progress,
        "file_size": operation.file_size,
        "checksum": operation.checksum,
        "download_url": operation.download_url,
        "expires_at": operation.expires_at.isoformat() if operation.expires_at else None,
        "error_message": operation.error_message,
        "created_at": operation.created_at.isoformat(),
        "started_at": operation.started_at.isoformat() if operation.started_at else None,
        "completed_at": operation.completed_at.isoformat() if operation.completed_at else None
    }

@app.get(
    "/api/exports",
    response_model=List[Dict[str, Any]],
    summary="List Export Operations",
    description="List export operations for the current user or all users (admin)",
    tags=["data-export"]
)
async def list_exports(
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
    limit: int = Query(50, description="Maximum number of operations to return", ge=1, le=200)
):
    """List export operations"""
    query = db.query(ExportOperation)

    # Non-admin users can only see their own exports
    if not current_user.is_superuser:
        query = query.filter(ExportOperation.user_id == current_user.id)

    operations = query.order_by(ExportOperation.created_at.desc()).limit(limit).all()

    return [{
        "id": op.id,
        "user_id": op.user_id,
        "export_type": op.export_type,
        "format": op.format,
        "status": op.status,
        "progress": op.progress,
        "file_size": op.file_size,
        "download_url": op.download_url,
        "expires_at": op.expires_at.isoformat() if op.expires_at else None,
        "created_at": op.created_at.isoformat(),
        "completed_at": op.completed_at.isoformat() if op.completed_at else None
    } for op in operations]

@app.get(
    "/api/exports/download/{operation_id}",
    summary="Download Export File",
    description="Download the completed export file",
    tags=["data-export"]
)
async def download_export(
    operation_id: str,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Download export file"""
    operation = db.query(ExportOperation).filter(ExportOperation.id == operation_id).first()
    if not operation:
        raise HTTPException(status_code=404, detail="Export operation not found")

    # Check ownership
    if operation.user_id != current_user.id and not current_user.is_superuser:
        raise HTTPException(status_code=403, detail="Access denied")

    if operation.status != "completed":
        raise HTTPException(status_code=400, detail="Export is not yet completed")

    if not operation.file_path or not os.path.exists(operation.file_path):
        raise HTTPException(status_code=404, detail="Export file not found")

    # Check expiration
    if operation.expires_at and datetime.now(timezone.utc) > operation.expires_at:
        raise HTTPException(status_code=410, detail="Export file has expired")

    # Log download
    audit_log = AuditLog(
        user_id=current_user.id,
        action="export_download",
        resource="export_operation",
        resource_id=operation_id,
        details={"export_type": operation.export_type, "format": operation.format}
    )
    db.add(audit_log)
    db.commit()

    return FileResponse(
        path=operation.file_path,
        filename=f"export_{operation_id}.{operation.format}",
        media_type="application/octet-stream"
    )

@app.delete(
    "/api/exports/{operation_id}",
    response_model=Dict[str, str],
    summary="Delete Export Operation",
    description="Delete an export operation and its associated file",
    tags=["data-export"]
)
async def delete_export(
    operation_id: str,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Delete export operation"""
    operation = db.query(ExportOperation).filter(ExportOperation.id == operation_id).first()
    if not operation:
        raise HTTPException(status_code=404, detail="Export operation not found")

    # Check ownership
    if operation.user_id != current_user.id and not current_user.is_superuser:
        raise HTTPException(status_code=403, detail="Access denied")

    # Delete file if it exists
    if operation.file_path and os.path.exists(operation.file_path):
        try:
            os.remove(operation.file_path)
        except Exception as e:
            logger.warning(f"Failed to delete export file {operation.file_path}: {e}")

    # Delete database record
    db.delete(operation)
    db.commit()

    logger.info(f"Export operation {operation_id} deleted by user {current_user.username}")
    return {"message": "Export operation deleted successfully"}

# Admin export management endpoints
@app.get(
    "/admin/exports",
    response_model=List[Dict[str, Any]],
    summary="List All Export Operations (Admin)",
    description="List all export operations across all users (admin only)",
    tags=["admin", "data-export"]
)
async def list_all_exports(
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
    limit: int = Query(100, description="Maximum number of operations to return", ge=1, le=500),
    status: Optional[str] = Query(None, description="Filter by status")
):
    """List all export operations (admin only)"""
    if not current_user.is_superuser:
        raise HTTPException(status_code=403, detail="Admin access required")

    query = db.query(ExportOperation)

    if status:
        query = query.filter(ExportOperation.status == status)

    operations = query.order_by(ExportOperation.created_at.desc()).limit(limit).all()

    return [{
        "id": op.id,
        "user_id": op.user_id,
        "username": db.query(User).filter(User.id == op.user_id).first().username,
        "export_type": op.export_type,
        "format": op.format,
        "status": op.status,
        "progress": op.progress,
        "file_size": op.file_size,
        "created_at": op.created_at.isoformat(),
        "completed_at": op.completed_at.isoformat() if op.completed_at else None,
        "error_message": op.error_message
    } for op in operations]

@app.get(
    "/admin/exports/stats",
    response_model=Dict[str, Any],
    summary="Get Export Statistics (Admin)",
    description="Get comprehensive export statistics (admin only)",
    tags=["admin", "data-export"]
)
async def get_export_stats(
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
    days: int = Query(30, description="Number of days to analyze", ge=1, le=365)
):
    """Get export statistics (admin only)"""
    if not current_user.is_superuser:
        raise HTTPException(status_code=403, detail="Admin access required")

    cutoff_date = datetime.now(timezone.utc) - timedelta(days=days)

    # Count operations by status
    status_counts = db.query(
        ExportOperation.status,
        db.func.count(ExportOperation.id)
    ).filter(
        ExportOperation.created_at >= cutoff_date
    ).group_by(ExportOperation.status).all()

    # Count operations by type
    type_counts = db.query(
        ExportOperation.export_type,
        db.func.count(ExportOperation.id)
    ).filter(
        ExportOperation.created_at >= cutoff_date
    ).group_by(ExportOperation.export_type).all()

    # Count operations by format
    format_counts = db.query(
        ExportOperation.format,
        db.func.count(ExportOperation.id)
    ).filter(
        ExportOperation.created_at >= cutoff_date
    ).group_by(ExportOperation.format).all()

    # Calculate total file size
    total_size_result = db.query(
        db.func.sum(ExportOperation.file_size)
    ).filter(
        ExportOperation.created_at >= cutoff_date,
        ExportOperation.status == "completed"
    ).first()

    total_size = total_size_result[0] if total_size_result[0] else 0

    return {
        "period_days": days,
        "total_operations": sum(count for _, count in status_counts),
        "status_breakdown": {status: count for status, count in status_counts},
        "type_breakdown": {export_type: count for export_type, count in type_counts},
        "format_breakdown": {format_type: count for format_type, count in format_counts},
        "total_file_size_bytes": total_size,
        "average_file_size_bytes": total_size / max(1, sum(count for _, count in status_counts if _ == "completed"))
    }

# Onboarding and Tutorial System Endpoints

# Onboarding Flow Management
@app.get(
    "/api/onboarding/flows",
    response_model=List[Dict[str, Any]],
    summary="Get Available Onboarding Flows",
    description="Get all available onboarding flows for the current user",
    tags=["onboarding"]
)
async def get_onboarding_flows(current_user: User = Depends(get_current_active_user), db: Session = Depends(get_db)):
    """Get available onboarding flows for the user"""
    # Get flows for user's type or generic flows
    flows = db.query(OnboardingFlow).filter(
        OnboardingFlow.is_active == True,
        db.or_(
            OnboardingFlow.user_type_id == current_user.user_type_id,
            OnboardingFlow.user_type_id.is_(None)
        )
    ).all()

    result = []
    for flow in flows:
        # Check if user has already completed this flow
        progress = db.query(UserOnboardingProgress).filter(
            UserOnboardingProgress.user_id == current_user.id,
            UserOnboardingProgress.flow_id == flow.id,
            UserOnboardingProgress.status == "completed"
        ).first()

        result.append({
            "id": flow.id,
            "name": flow.name,
            "display_name": flow.display_name,
            "description": flow.description,
            "is_default": flow.is_default,
            "completed": progress is not None,
            "user_type": flow.user_type.name if flow.user_type else None
        })

    return result

@app.get(
    "/api/onboarding/progress",
    response_model=Dict[str, Any],
    summary="Get User Onboarding Progress",
    description="Get the current user's onboarding progress",
    tags=["onboarding"]
)
async def get_onboarding_progress(current_user: User = Depends(get_current_active_user), db: Session = Depends(get_db)):
    """Get user's onboarding progress"""
    # Find active progress or create default flow progress
    progress = db.query(UserOnboardingProgress).filter(
        UserOnboardingProgress.user_id == current_user.id,
        UserOnboardingProgress.status.in_(["not_started", "in_progress"])
    ).first()

    if not progress:
        # Find default flow for user's type
        default_flow = db.query(OnboardingFlow).filter(
            OnboardingFlow.is_active == True,
            OnboardingFlow.is_default == True,
            db.or_(
                OnboardingFlow.user_type_id == current_user.user_type_id,
                OnboardingFlow.user_type_id.is_(None)
            )
        ).first()

        if default_flow:
            progress = UserOnboardingProgress(
                user_id=current_user.id,
                flow_id=default_flow.id,
                status="not_started"
            )
            db.add(progress)
            db.commit()

    if not progress:
        return {"has_progress": False, "message": "No onboarding flow available"}

    flow = db.query(OnboardingFlow).filter(OnboardingFlow.id == progress.flow_id).first()
    steps = db.query(OnboardingStep).filter(OnboardingStep.flow_id == progress.flow_id).order_by(OnboardingStep.step_order).all()

    step_progress = []
    for step in steps:
        is_completed = step.id in (progress.completed_steps or [])
        is_skipped = step.id in (progress.skipped_steps or [])

        step_progress.append({
            "id": step.id,
            "title": step.title,
            "description": step.description,
            "content_type": step.content_type,
            "target_element": step.target_element,
            "content": step.content,
            "is_required": step.is_required,
            "auto_advance": step.auto_advance,
            "estimated_duration": step.estimated_duration,
            "status": "completed" if is_completed else ("skipped" if is_skipped else "pending"),
            "order": step.step_order
        })

    return {
        "has_progress": True,
        "flow": {
            "id": flow.id,
            "name": flow.name,
            "display_name": flow.display_name,
            "description": flow.description
        },
        "progress": {
            "id": progress.id,
            "status": progress.status,
            "current_step_id": progress.current_step_id,
            "completed_steps": progress.completed_steps or [],
            "skipped_steps": progress.skipped_steps or [],
            "started_at": progress.started_at.isoformat() if progress.started_at else None,
            "completed_at": progress.completed_at.isoformat() if progress.completed_at else None,
            "total_time_spent": progress.total_time_spent
        },
        "steps": step_progress
    }

@app.post(
    "/api/onboarding/start",
    response_model=Dict[str, str],
    summary="Start Onboarding",
    description="Start the onboarding process for the user",
    tags=["onboarding"]
)
async def start_onboarding(current_user: User = Depends(get_current_active_user), db: Session = Depends(get_db)):
    """Start onboarding for the user"""
    # Find or create progress
    progress = db.query(UserOnboardingProgress).filter(
        UserOnboardingProgress.user_id == current_user.id,
        UserOnboardingProgress.status.in_(["not_started", "in_progress"])
    ).first()

    if not progress:
        # Find default flow
        default_flow = db.query(OnboardingFlow).filter(
            OnboardingFlow.is_active == True,
            OnboardingFlow.is_default == True,
            db.or_(
                OnboardingFlow.user_type_id == current_user.user_type_id,
                OnboardingFlow.user_type_id.is_(None)
            )
        ).first()

        if not default_flow:
            raise HTTPException(status_code=404, detail="No default onboarding flow available")

        progress = UserOnboardingProgress(
            user_id=current_user.id,
            flow_id=default_flow.id,
            status="in_progress",
            started_at=datetime.now(timezone.utc)
        )
        db.add(progress)
    else:
        progress.status = "in_progress"
        if not progress.started_at:
            progress.started_at = datetime.now(timezone.utc)

    progress.last_activity_at = datetime.now(timezone.utc)
    db.commit()

    return {"message": "Onboarding started successfully"}

@app.post(
    "/api/onboarding/step/{step_id}/complete",
    response_model=Dict[str, str],
    summary="Complete Onboarding Step",
    description="Mark an onboarding step as completed",
    tags=["onboarding"]
)
async def complete_onboarding_step(
    step_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Complete an onboarding step"""
    # Find user's progress
    progress = db.query(UserOnboardingProgress).filter(
        UserOnboardingProgress.user_id == current_user.id,
        UserOnboardingProgress.status == "in_progress"
    ).first()

    if not progress:
        raise HTTPException(status_code=404, detail="No active onboarding progress found")

    # Verify step belongs to flow
    step = db.query(OnboardingStep).filter(
        OnboardingStep.id == step_id,
        OnboardingStep.flow_id == progress.flow_id
    ).first()

    if not step:
        raise HTTPException(status_code=404, detail="Step not found in current flow")

    # Update progress
    completed_steps = progress.completed_steps or []
    if step_id not in completed_steps:
        completed_steps.append(step_id)
        progress.completed_steps = completed_steps

    # Remove from skipped if it was skipped
    skipped_steps = progress.skipped_steps or []
    if step_id in skipped_steps:
        skipped_steps.remove(step_id)
        progress.skipped_steps = skipped_steps

    # Set as current step
    progress.current_step_id = step_id
    progress.last_activity_at = datetime.now(timezone.utc)

    # Check if flow is completed
    all_steps = db.query(OnboardingStep).filter(OnboardingStep.flow_id == progress.flow_id).all()
    required_steps = [s.id for s in all_steps if s.is_required]

    if all(step_id in completed_steps for step_id in required_steps):
        progress.status = "completed"
        progress.completed_at = datetime.now(timezone.utc)

    db.commit()

    return {"message": "Step completed successfully"}

@app.post(
    "/api/onboarding/step/{step_id}/skip",
    response_model=Dict[str, str],
    summary="Skip Onboarding Step",
    description="Skip an onboarding step (if allowed)",
    tags=["onboarding"]
)
async def skip_onboarding_step(
    step_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Skip an onboarding step"""
    # Find user's progress
    progress = db.query(UserOnboardingProgress).filter(
        UserOnboardingProgress.user_id == current_user.id,
        UserOnboardingProgress.status == "in_progress"
    ).first()

    if not progress:
        raise HTTPException(status_code=404, detail="No active onboarding progress found")

    # Verify step belongs to flow
    step = db.query(OnboardingStep).filter(
        OnboardingStep.id == step_id,
        OnboardingStep.flow_id == progress.flow_id
    ).first()

    if not step:
        raise HTTPException(status_code=404, detail="Step not found in current flow")

    if step.is_required:
        raise HTTPException(status_code=400, detail="Cannot skip required step")

    # Update progress
    skipped_steps = progress.skipped_steps or []
    if step_id not in skipped_steps:
        skipped_steps.append(step_id)
        progress.skipped_steps = skipped_steps

    progress.last_activity_at = datetime.now(timezone.utc)
    db.commit()

    return {"message": "Step skipped successfully"}

@app.post(
    "/api/onboarding/skip",
    response_model=Dict[str, str],
    summary="Skip Entire Onboarding",
    description="Skip the entire onboarding process",
    tags=["onboarding"]
)
async def skip_onboarding(current_user: User = Depends(get_current_active_user), db: Session = Depends(get_db)):
    """Skip entire onboarding"""
    progress = db.query(UserOnboardingProgress).filter(
        UserOnboardingProgress.user_id == current_user.id,
        UserOnboardingProgress.status == "in_progress"
    ).first()

    if progress:
        progress.status = "skipped"
        progress.completed_at = datetime.now(timezone.utc)
        progress.last_activity_at = datetime.now(timezone.utc)
        db.commit()

    return {"message": "Onboarding skipped successfully"}

# Tutorial Management Endpoints
@app.get(
    "/api/tutorials",
    response_model=List[Dict[str, Any]],
    summary="Get Available Tutorials",
    description="Get list of available tutorials with user progress",
    tags=["tutorials"]
)
async def get_tutorials(
    category: Optional[str] = None,
    difficulty: Optional[str] = None,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Get available tutorials"""
    query = db.query(Tutorial).filter(Tutorial.is_active == True)

    if category:
        query = query.filter(Tutorial.category == category)
    if difficulty:
        query = query.filter(Tutorial.difficulty_level == difficulty)

    tutorials = query.order_by(Tutorial.created_at.desc()).all()

    result = []
    for tutorial in tutorials:
        # Get user's progress
        progress = db.query(TutorialProgress).filter(
            TutorialProgress.user_id == current_user.id,
            TutorialProgress.tutorial_id == tutorial.id
        ).first()

        result.append({
            "id": tutorial.id,
            "title": tutorial.title,
            "description": tutorial.description,
            "category": tutorial.category,
            "difficulty_level": tutorial.difficulty_level,
            "content_type": tutorial.content_type,
            "video_url": tutorial.video_url,
            "thumbnail_url": tutorial.thumbnail_url,
            "estimated_duration": tutorial.estimated_duration,
            "tags": tutorial.tags or [],
            "view_count": tutorial.view_count,
            "completion_count": tutorial.completion_count,
            "average_rating": tutorial.average_rating,
            "user_progress": {
                "status": progress.status if progress else "not_started",
                "progress_percentage": progress.progress_percentage if progress else 0.0,
                "time_spent": progress.time_spent if progress else 0,
                "completed_at": progress.completed_at.isoformat() if progress and progress.completed_at else None,
                "rating": progress.rating if progress else None
            } if progress else None
        })

    return result

@app.get(
    "/api/tutorials/{tutorial_id}",
    response_model=Dict[str, Any],
    summary="Get Tutorial Details",
    description="Get detailed information about a specific tutorial",
    tags=["tutorials"]
)
async def get_tutorial(
    tutorial_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Get tutorial details"""
    tutorial = db.query(Tutorial).filter(
        Tutorial.id == tutorial_id,
        Tutorial.is_active == True
    ).first()

    if not tutorial:
        raise HTTPException(status_code=404, detail="Tutorial not found")

    # Get user's progress
    progress = db.query(TutorialProgress).filter(
        TutorialProgress.user_id == current_user.id,
        TutorialProgress.tutorial_id == tutorial_id
    ).first()

    # Increment view count
    tutorial.view_count += 1
    db.commit()

    return {
        "id": tutorial.id,
        "title": tutorial.title,
        "description": tutorial.description,
        "category": tutorial.category,
        "difficulty_level": tutorial.difficulty_level,
        "content_type": tutorial.content_type,
        "video_url": tutorial.video_url,
        "thumbnail_url": tutorial.thumbnail_url,
        "content": tutorial.content,
        "estimated_duration": tutorial.estimated_duration,
        "tags": tutorial.tags or [],
        "view_count": tutorial.view_count,
        "completion_count": tutorial.completion_count,
        "average_rating": tutorial.average_rating,
        "user_progress": {
            "status": progress.status if progress else "not_started",
            "progress_percentage": progress.progress_percentage if progress else 0.0,
            "current_position": progress.current_position if progress else None,
            "time_spent": progress.time_spent if progress else 0,
            "completed_at": progress.completed_at.isoformat() if progress and progress.completed_at else None,
            "rating": progress.rating if progress else None,
            "feedback": progress.feedback if progress else None
        } if progress else None
    }

@app.post(
    "/api/tutorials/{tutorial_id}/start",
    response_model=Dict[str, str],
    summary="Start Tutorial",
    description="Start watching a tutorial",
    tags=["tutorials"]
)
async def start_tutorial(
    tutorial_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Start a tutorial"""
    tutorial = db.query(Tutorial).filter(
        Tutorial.id == tutorial_id,
        Tutorial.is_active == True
    ).first()

    if not tutorial:
        raise HTTPException(status_code=404, detail="Tutorial not found")

    # Find or create progress
    progress = db.query(TutorialProgress).filter(
        TutorialProgress.user_id == current_user.id,
        TutorialProgress.tutorial_id == tutorial_id
    ).first()

    if not progress:
        progress = TutorialProgress(
            user_id=current_user.id,
            tutorial_id=tutorial_id,
            status="in_progress"
        )
        db.add(progress)
    else:
        progress.status = "in_progress"

    progress.last_activity_at = datetime.now(timezone.utc)
    db.commit()

    # Log analytics
    analytics = UserTutorialAnalytics(
        user_id=current_user.id,
        tutorial_id=tutorial_id,
        event_type="started",
        event_data={"source": "api"}
    )
    db.add(analytics)
    db.commit()

    return {"message": "Tutorial started successfully"}

@app.post(
    "/api/tutorials/{tutorial_id}/progress",
    response_model=Dict[str, str],
    summary="Update Tutorial Progress",
    description="Update progress for an interactive tutorial",
    tags=["tutorials"]
)
async def update_tutorial_progress(
    tutorial_id: int,
    progress_percentage: float,
    current_position: Optional[Dict[str, Any]] = None,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Update tutorial progress"""
    progress = db.query(TutorialProgress).filter(
        TutorialProgress.user_id == current_user.id,
        TutorialProgress.tutorial_id == tutorial_id
    ).first()

    if not progress:
        raise HTTPException(status_code=404, detail="Tutorial progress not found")

    progress.progress_percentage = progress_percentage
    if current_position:
        progress.current_position = current_position
    progress.last_activity_at = datetime.now(timezone.utc)

    # Check if completed
    if progress_percentage >= 100.0 and progress.status != "completed":
        progress.status = "completed"
        progress.completed_at = datetime.now(timezone.utc)

        # Update tutorial completion count
        tutorial = db.query(Tutorial).filter(Tutorial.id == tutorial_id).first()
        if tutorial:
            tutorial.completion_count += 1

    db.commit()

    # Log analytics
    analytics = UserTutorialAnalytics(
        user_id=current_user.id,
        tutorial_id=tutorial_id,
        event_type="progress_update",
        event_data={"progress_percentage": progress_percentage}
    )
    db.add(analytics)
    db.commit()

    return {"message": "Progress updated successfully"}

@app.post(
    "/api/tutorials/{tutorial_id}/complete",
    response_model=Dict[str, str],
    summary="Complete Tutorial",
    description="Mark a tutorial as completed",
    tags=["tutorials"]
)
async def complete_tutorial(
    tutorial_id: int,
    rating: Optional[int] = None,
    feedback: Optional[str] = None,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Complete a tutorial"""
    progress = db.query(TutorialProgress).filter(
        TutorialProgress.user_id == current_user.id,
        TutorialProgress.tutorial_id == tutorial_id
    ).first()

    if not progress:
        raise HTTPException(status_code=404, detail="Tutorial progress not found")

    progress.status = "completed"
    progress.progress_percentage = 100.0
    progress.completed_at = datetime.now(timezone.utc)
    progress.last_activity_at = datetime.now(timezone.utc)

    if rating is not None:
        progress.rating = rating
    if feedback:
        progress.feedback = feedback

    # Update tutorial completion count and rating
    tutorial = db.query(Tutorial).filter(Tutorial.id == tutorial_id).first()
    if tutorial:
        tutorial.completion_count += 1
        if rating is not None:
            # Simple average rating calculation
            total_ratings = tutorial.completion_count
            current_avg = tutorial.average_rating or 0.0
            tutorial.average_rating = (current_avg * (total_ratings - 1) + rating) / total_ratings

    db.commit()

    # Log analytics
    analytics = UserTutorialAnalytics(
        user_id=current_user.id,
        tutorial_id=tutorial_id,
        event_type="completed",
        event_data={"rating": rating}
    )
    db.add(analytics)
    db.commit()

    return {"message": "Tutorial completed successfully"}

# Help Center Endpoints
@app.get(
    "/api/help/categories",
    response_model=List[Dict[str, Any]],
    summary="Get Help Categories",
    description="Get all help categories",
    tags=["help"]
)
async def get_help_categories(db: Session = Depends(get_db)):
    """Get help categories"""
    categories = db.query(HelpCategory).filter(HelpCategory.is_active == True).order_by(HelpCategory.sort_order).all()

    result = []
    for category in categories:
        article_count = db.query(HelpArticle).filter(
            HelpArticle.category_id == category.id,
            HelpArticle.is_active == True
        ).count()

        result.append({
            "id": category.id,
            "name": category.name,
            "display_name": category.display_name,
            "description": category.description,
            "icon": category.icon,
            "article_count": article_count
        })

    return result

@app.get(
    "/api/help/articles",
    response_model=List[Dict[str, Any]],
    summary="Get Help Articles",
    description="Get help articles with optional filtering",
    tags=["help"]
)
async def get_help_articles(
    category_id: Optional[int] = None,
    search: Optional[str] = None,
    limit: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db)
):
    """Get help articles"""
    query = db.query(HelpArticle).filter(HelpArticle.is_active == True)

    if category_id:
        query = query.filter(HelpArticle.category_id == category_id)

    if search:
        search_term = f"%{search}%"
        query = query.filter(
            db.or_(
                HelpArticle.title.ilike(search_term),
                HelpArticle.content.ilike(search_term),
                HelpArticle.summary.ilike(search_term)
            )
        )

    articles = query.order_by(HelpArticle.view_count.desc()).limit(limit).all()

    result = []
    for article in articles:
        category = db.query(HelpCategory).filter(HelpCategory.id == article.category_id).first()

        result.append({
            "id": article.id,
            "title": article.title,
            "slug": article.slug,
            "summary": article.summary,
            "category": {
                "id": category.id if category else None,
                "name": category.name if category else None,
                "display_name": category.display_name if category else None
            },
            "difficulty_level": article.difficulty_level,
            "view_count": article.view_count,
            "helpful_votes": article.helpful_votes,
            "total_votes": article.total_votes,
            "is_featured": article.is_featured,
            "created_at": article.created_at.isoformat()
        })

    return result

@app.get(
    "/api/help/articles/{article_id}",
    response_model=Dict[str, Any],
    summary="Get Help Article",
    description="Get a specific help article",
    tags=["help"]
)
async def get_help_article(article_id: int, db: Session = Depends(get_db)):
    """Get help article"""
    article = db.query(HelpArticle).filter(
        HelpArticle.id == article_id,
        HelpArticle.is_active == True
    ).first()

    if not article:
        raise HTTPException(status_code=404, detail="Article not found")

    # Increment view count
    article.view_count += 1
    db.commit()

    category = db.query(HelpCategory).filter(HelpCategory.id == article.category_id).first()

    return {
        "id": article.id,
        "title": article.title,
        "slug": article.slug,
        "content": article.content,
        "summary": article.summary,
        "category": {
            "id": category.id if category else None,
            "name": category.name if category else None,
            "display_name": category.display_name if category else None
        },
        "tags": article.tags or [],
        "difficulty_level": article.difficulty_level,
        "view_count": article.view_count,
        "helpful_votes": article.helpful_votes,
        "total_votes": article.total_votes,
        "is_featured": article.is_featured,
        "created_at": article.created_at.isoformat(),
        "updated_at": article.updated_at.isoformat()
    }

@app.post(
    "/api/help/articles/{article_id}/vote",
    response_model=Dict[str, str],
    summary="Vote on Help Article",
    description="Vote whether a help article was helpful",
    tags=["help"]
)
async def vote_help_article(
    article_id: int,
    helpful: bool,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Vote on help article"""
    article = db.query(HelpArticle).filter(HelpArticle.id == article_id).first()

    if not article:
        raise HTTPException(status_code=404, detail="Article not found")

    if helpful:
        article.helpful_votes += 1
    article.total_votes += 1

    db.commit()

    return {"message": "Vote recorded successfully"}

# Tooltip Management Endpoints
@app.get(
    "/api/tooltips",
    response_model=List[Dict[str, Any]],
    summary="Get Active Tooltips",
    description="Get tooltips that should be shown to the current user",
    tags=["tooltips"]
)
async def get_active_tooltips(current_user: User = Depends(get_current_active_user), db: Session = Depends(get_db)):
    """Get active tooltips for user"""
    # Get all active tooltips
    tooltips = db.query(Tooltip).filter(Tooltip.is_active == True).all()

    result = []
    for tooltip in tooltips:
        # Check user type restrictions
        if tooltip.user_type_restrictions:
            user_type_name = current_user.user_type.name if current_user.user_type else None
            if user_type_name not in tooltip.user_type_restrictions:
                continue

        # Check if user has already seen this tooltip (if show_once is true)
        if tooltip.show_once:
            interaction = db.query(UserTooltipInteraction).filter(
                UserTooltipInteraction.user_id == current_user.id,
                UserTooltipInteraction.tooltip_id == tooltip.id
            ).first()
            if interaction:
                continue

        # Check conditions (simplified - could be more complex)
        show_tooltip = True
        if tooltip.conditions:
            # For now, just check basic conditions
            # This could be expanded to check user behavior, feature usage, etc.
            pass

        if show_tooltip:
            result.append({
                "id": tooltip.id,
                "identifier": tooltip.identifier,
                "title": tooltip.title,
                "content": tooltip.content,
                "target_element": tooltip.target_element,
                "trigger_event": tooltip.trigger_event,
                "position": tooltip.position,
                "priority": tooltip.priority
            })

    # Sort by priority
    result.sort(key=lambda x: x["priority"], reverse=True)

    return result

@app.post(
    "/api/tooltips/{tooltip_id}/interact",
    response_model=Dict[str, str],
    summary="Record Tooltip Interaction",
    description="Record user interaction with a tooltip",
    tags=["tooltips"]
)
async def record_tooltip_interaction(
    tooltip_id: int,
    interaction_type: str,
    interaction_data: Optional[Dict[str, Any]] = None,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Record tooltip interaction"""
    if interaction_type not in ["viewed", "dismissed", "clicked", "followed_link"]:
        raise HTTPException(status_code=400, detail="Invalid interaction type")

    interaction = UserTooltipInteraction(
        user_id=current_user.id,
        tooltip_id=tooltip_id,
        interaction_type=interaction_type,
        interaction_data=interaction_data
    )

    db.add(interaction)
    db.commit()

    return {"message": "Interaction recorded successfully"}

# Support Chat Endpoints
@app.post(
    "/api/support/chats",
    response_model=Dict[str, str],
    summary="Create Support Chat",
    description="Create a new support chat conversation",
    tags=["support"]
)
async def create_support_chat(
    subject: Optional[str] = None,
    category: Optional[str] = None,
    priority: str = "normal",
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Create a new support chat"""
    if priority not in ["low", "normal", "high", "urgent"]:
        raise HTTPException(status_code=400, detail="Invalid priority level")

    chat_id = str(uuid.uuid4())

    chat = SupportChat(
        id=chat_id,
        user_id=current_user.id,
        subject=subject,
        category=category,
        priority=priority
    )

    db.add(chat)
    db.commit()

    return {"chat_id": chat_id, "message": "Support chat created successfully"}

@app.get(
    "/api/support/chats",
    response_model=List[Dict[str, Any]],
    summary="Get User Support Chats",
    description="Get support chats for the current user",
    tags=["support"]
)
async def get_support_chats(current_user: User = Depends(get_current_active_user), db: Session = Depends(get_db)):
    """Get user's support chats"""
    chats = db.query(SupportChat).filter(SupportChat.user_id == current_user.id).order_by(SupportChat.updated_at.desc()).all()

    result = []
    for chat in chats:
        # Get latest message
        latest_message = db.query(SupportMessage).filter(
            SupportMessage.chat_id == chat.id
        ).order_by(SupportMessage.created_at.desc()).first()

        # Count unread messages (from agent)
        unread_count = db.query(SupportMessage).filter(
            SupportMessage.chat_id == chat.id,
            SupportMessage.is_from_user == False,
            SupportMessage.is_read == False
        ).count()

        result.append({
            "id": chat.id,
            "subject": chat.subject,
            "status": chat.status,
            "priority": chat.priority,
            "category": chat.category,
            "is_live_chat": chat.is_live_chat,
            "assigned_to": chat.assigned_to,
            "created_at": chat.created_at.isoformat(),
            "updated_at": chat.updated_at.isoformat(),
            "resolved_at": chat.resolved_at.isoformat() if chat.resolved_at else None,
            "latest_message": {
                "content": latest_message.content[:100] + "..." if latest_message and len(latest_message.content) > 100 else latest_message.content if latest_message else None,
                "created_at": latest_message.created_at.isoformat() if latest_message else None,
                "is_from_user": latest_message.is_from_user if latest_message else None
            } if latest_message else None,
            "unread_count": unread_count
        })

    return result

@app.get(
    "/api/support/chats/{chat_id}",
    response_model=Dict[str, Any],
    summary="Get Support Chat",
    description="Get a specific support chat with messages",
    tags=["support"]
)
async def get_support_chat(
    chat_id: str,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Get support chat details"""
    chat = db.query(SupportChat).filter(SupportChat.id == chat_id).first()

    if not chat or chat.user_id != current_user.id:
        raise HTTPException(status_code=404, detail="Chat not found")

    messages = db.query(SupportMessage).filter(SupportMessage.chat_id == chat_id).order_by(SupportMessage.created_at).all()

    message_list = []
    for msg in messages:
        message_list.append({
            "id": msg.id,
            "message_type": msg.message_type,
            "content": msg.content,
            "attachments": msg.attachments or [],
            "is_from_user": msg.is_from_user,
            "is_read": msg.is_read,
            "created_at": msg.created_at.isoformat()
        })

    # Mark agent messages as read
    db.query(SupportMessage).filter(
        SupportMessage.chat_id == chat_id,
        SupportMessage.is_from_user == False,
        SupportMessage.is_read == False
    ).update({"is_read": True})

    db.commit()

    return {
        "id": chat.id,
        "subject": chat.subject,
        "status": chat.status,
        "priority": chat.priority,
        "category": chat.category,
        "is_live_chat": chat.is_live_chat,
        "assigned_to": chat.assigned_to,
        "created_at": chat.created_at.isoformat(),
        "updated_at": chat.updated_at.isoformat(),
        "resolved_at": chat.resolved_at.isoformat() if chat.resolved_at else None,
        "messages": message_list
    }

@app.post(
    "/api/support/chats/{chat_id}/messages",
    response_model=Dict[str, str],
    summary="Send Support Message",
    description="Send a message in a support chat",
    tags=["support"]
)
async def send_support_message(
    chat_id: str,
    content: str,
    message_type: str = "text",
    attachments: Optional[List[Dict[str, Any]]] = None,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Send a message in support chat"""
    chat = db.query(SupportChat).filter(SupportChat.id == chat_id).first()

    if not chat or chat.user_id != current_user.id:
        raise HTTPException(status_code=404, detail="Chat not found")

    if chat.status == "closed":
        raise HTTPException(status_code=400, detail="Cannot send messages to closed chat")

    if message_type not in ["text", "file"]:
        raise HTTPException(status_code=400, detail="Invalid message type")

    message = SupportMessage(
        chat_id=chat_id,
        content=content,
        message_type=message_type,
        attachments=attachments,
        is_from_user=True
    )

    chat.updated_at = datetime.now(timezone.utc)

    db.add(message)
    db.commit()

    return {"message": "Message sent successfully"}

# Data Import endpoints
@app.post(
    "/api/imports",
    response_model=Dict[str, str],
    summary="Create Data Import",
    description="Create a new data import operation for user data migration",
    tags=["data-import"]
)
async def create_import(
    import_type: str,
    source_url: Optional[str] = None,
    file: Optional[UploadFile] = File(None),
    validation_rules: Optional[Dict[str, Any]] = None,
    current_user: User = Depends(get_current_active_user),
    request: Request = None
):
    """Create a new data import operation"""
    if import_type not in ["user_data", "conversations", "bulk_admin"]:
        raise HTTPException(status_code=400, detail="Invalid import type")

    # Admin check for bulk imports
    if import_type == "bulk_admin" and not current_user.is_superuser:
        raise HTTPException(status_code=403, detail="Admin access required for bulk import")

    try:
        import_data = None
        if file:
            # Read uploaded file
            import_data = await file.read()
        elif source_url:
            # Download from URL (placeholder - would need implementation)
            raise HTTPException(status_code=501, detail="URL import not implemented yet")

        operation_id = await export_service.create_import_operation(
            user_id=current_user.id,
            import_type=import_type,
            import_data=import_data,
            validation_rules=validation_rules,
            requested_by_ip=getattr(request.client, 'host', None) if request else None,
            user_agent=request.headers.get('user-agent') if request else None
        )

        return {"operation_id": operation_id, "message": "Import operation created successfully"}
    except Exception as e:
        logger.error(f"Error creating import: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get(
    "/api/imports/{operation_id}",
    response_model=Dict[str, Any],
    summary="Get Import Status",
    description="Get the status and details of an import operation",
    tags=["data-import"]
)
async def get_import_status(
    operation_id: str,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Get import operation status"""
    operation = db.query(ImportOperation).filter(ImportOperation.id == operation_id).first()
    if not operation:
        raise HTTPException(status_code=404, detail="Import operation not found")

    # Check ownership (users can only see their own imports, admins can see all)
    if operation.user_id != current_user.id and not current_user.is_superuser:
        raise HTTPException(status_code=403, detail="Access denied")

    return {
        "id": operation.id,
        "user_id": operation.user_id,
        "import_type": operation.import_type,
        "status": operation.status,
        "progress": operation.progress,
        "records_processed": operation.records_processed,
        "records_failed": operation.records_failed,
        "validation_errors": operation.validation_errors,
        "error_message": operation.error_message,
        "created_at": operation.created_at.isoformat(),
        "started_at": operation.started_at.isoformat() if operation.started_at else None,
        "completed_at": operation.completed_at.isoformat() if operation.completed_at else None
    }

@app.get(
    "/api/imports",
    response_model=List[Dict[str, Any]],
    summary="List Import Operations",
    description="List import operations for the current user or all users (admin)",
    tags=["data-import"]
)
async def list_imports(
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
    limit: int = Query(50, description="Maximum number of operations to return", ge=1, le=200)
):
    """List import operations"""
    query = db.query(ImportOperation)

    # Non-admin users can only see their own imports
    if not current_user.is_superuser:
        query = query.filter(ImportOperation.user_id == current_user.id)

    operations = query.order_by(ImportOperation.created_at.desc()).limit(limit).all()

    return [{
        "id": op.id,
        "user_id": op.user_id,
        "import_type": op.import_type,
        "status": op.status,
        "progress": op.progress,
        "records_processed": op.records_processed,
        "records_failed": op.records_failed,
        "created_at": op.created_at.isoformat(),
        "completed_at": op.completed_at.isoformat() if op.completed_at else None
    } for op in operations]

@app.delete(
    "/api/imports/{operation_id}",
    response_model=Dict[str, str],
    summary="Delete Import Operation",
    description="Delete an import operation and its associated data",
    tags=["data-import"]
)
async def delete_import(
    operation_id: str,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Delete import operation"""
    operation = db.query(ImportOperation).filter(ImportOperation.id == operation_id).first()
    if not operation:
        raise HTTPException(status_code=404, detail="Import operation not found")

    # Check ownership
    if operation.user_id != current_user.id and not current_user.is_superuser:
        raise HTTPException(status_code=403, detail="Access denied")

    # Delete database record
    db.delete(operation)
    db.commit()

    logger.info(f"Import operation {operation_id} deleted by user {current_user.username}")
    return {"message": "Import operation deleted successfully"}

# Admin import management endpoints
@app.get(
    "/admin/imports",
    response_model=List[Dict[str, Any]],
    summary="List All Import Operations (Admin)",
    description="List all import operations across all users (admin only)",
    tags=["admin", "data-import"]
)
async def list_all_imports(
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
    limit: int = Query(100, description="Maximum number of operations to return", ge=1, le=500),
    status: Optional[str] = Query(None, description="Filter by status")
):
    """List all import operations (admin only)"""
    if not current_user.is_superuser:
        raise HTTPException(status_code=403, detail="Admin access required")

    query = db.query(ImportOperation)

    if status:
        query = query.filter(ImportOperation.status == status)

    operations = query.order_by(ImportOperation.created_at.desc()).limit(limit).all()

    return [{
        "id": op.id,
        "user_id": op.user_id,
        "username": db.query(User).filter(User.id == op.user_id).first().username,
        "import_type": op.import_type,
        "status": op.status,
        "progress": op.progress,
        "records_processed": op.records_processed,
        "records_failed": op.records_failed,
        "created_at": op.created_at.isoformat(),
        "completed_at": op.completed_at.isoformat() if op.completed_at else None,
        "error_message": op.error_message
    } for op in operations]

@app.get(
    "/admin/imports/stats",
    response_model=Dict[str, Any],
    summary="Get Import Statistics (Admin)",
    description="Get comprehensive import statistics (admin only)",
    tags=["admin", "data-import"]
)
async def get_import_stats(
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
    days: int = Query(30, description="Number of days to analyze", ge=1, le=365)
):
    """Get import statistics (admin only)"""
    if not current_user.is_superuser:
        raise HTTPException(status_code=403, detail="Admin access required")

    cutoff_date = datetime.now(timezone.utc) - timedelta(days=days)

    # Count operations by status
    status_counts = db.query(
        ImportOperation.status,
        db.func.count(ImportOperation.id)
    ).filter(
        ImportOperation.created_at >= cutoff_date
    ).group_by(ImportOperation.status).all()

    # Count operations by type
    type_counts = db.query(
        ImportOperation.import_type,
        db.func.count(ImportOperation.id)
    ).filter(
        ImportOperation.created_at >= cutoff_date
    ).group_by(ImportOperation.import_type).all()

    # Calculate total records processed
    total_processed_result = db.query(
        db.func.sum(ImportOperation.records_processed)
    ).filter(
        ImportOperation.created_at >= cutoff_date,
        ImportOperation.status == "completed"
    ).first()

    total_processed = total_processed_result[0] if total_processed_result[0] else 0

    return {
        "period_days": days,
        "total_operations": sum(count for _, count in status_counts),
        "status_breakdown": {status: count for status, count in status_counts},
        "type_breakdown": {import_type: count for import_type, count in type_counts},
        "total_records_processed": total_processed,
        "average_records_per_operation": total_processed / max(1, sum(count for _, count in status_counts if _ == "completed"))
    }
