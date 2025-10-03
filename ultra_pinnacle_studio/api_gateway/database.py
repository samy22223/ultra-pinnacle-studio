"""
Database layer for Ultra Pinnacle AI Studio
"""
from sqlalchemy import create_engine, Column, Integer, String, Text, DateTime, Date, Boolean, ForeignKey, JSON, Float, Index, UniqueConstraint
# cspell:ignore sessionmaker
from sqlalchemy.orm import declarative_base
from sqlalchemy.orm import sessionmaker, relationship
from sqlalchemy.pool import StaticPool
from datetime import datetime, timezone
import json
import os
from .logging_config import logger

# Load config
config_path = os.path.join(os.path.dirname(__file__), '..', 'config.json')
with open(config_path, "r") as f:
    config = json.load(f)

# Database configuration
DATABASE_URL = config.get("database", {}).get("url", "sqlite:///./ultra_pinnacle.db")

# Create engine
if DATABASE_URL.startswith("sqlite"):
    engine = create_engine(
        DATABASE_URL,
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
        echo=config.get("database", {}).get("echo", False)
    )
else:
    engine = create_engine(DATABASE_URL, echo=config.get("database", {}).get("echo", False))

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

class User(Base):
    """User model"""
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, index=True, nullable=False)
    email = Column(String, unique=True, index=True, nullable=False)
    full_name = Column(String)
    hashed_password = Column(String, nullable=False)
    is_active = Column(Boolean, default=True)
    is_superuser = Column(Boolean, default=False)
    user_type_id = Column(Integer, ForeignKey("user_types.id"), nullable=True, default=1)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    # Enhanced authentication fields
    failed_login_attempts = Column(Integer, default=0)
    last_failed_login = Column(DateTime)
    lockout_until = Column(DateTime)
    password_changed_at = Column(DateTime)
    email_verified = Column(Boolean, default=False)
    email_verification_token = Column(String)
    email_verification_expires = Column(DateTime)
    two_factor_enabled = Column(Boolean, default=False)
    two_factor_secret = Column(String)  # Encrypted

    # Relationships
    conversations_created = relationship("Conversation", foreign_keys="[Conversation.created_by]", back_populates="creator")
    conversation_participations = relationship("ConversationParticipant", back_populates="user")
    file_uploads = relationship("FileUpload", back_populates="user")
    audit_logs = relationship("AuditLog", back_populates="user")
    tasks = relationship("Task", back_populates="user")
    presence = relationship("UserPresence", back_populates="user", uselist=False)
    activities = relationship("ActivityLog", back_populates="user")
    message_authors = relationship("Message", foreign_keys="[Message.user_id]", back_populates="user")
    document_creators = relationship("CollaborativeDocument", foreign_keys="[CollaborativeDocument.created_by]", back_populates="creator")
    document_editors = relationship("DocumentEdit", foreign_keys="[DocumentEdit.user_id]", back_populates="user")
    user_type = relationship("UserType", back_populates="users")
    rate_limit_overrides = relationship("UserRateLimit", back_populates="user", foreign_keys="[UserRateLimit.user_id]")
    sent_notifications = relationship("Notification", foreign_keys="[Notification.sender_id]", back_populates="sender")
    received_notifications = relationship("Notification", foreign_keys="[Notification.recipient_id]", back_populates="recipient")
    notification_history = relationship("NotificationHistory", foreign_keys="[NotificationHistory.recipient_id]", back_populates="recipient")

    # Enhanced authentication relationships
    user_roles = relationship("UserRole", foreign_keys="[UserRole.user_id]", back_populates="user")
    sessions = relationship("UserSession", back_populates="user")
    refresh_tokens = relationship("RefreshToken", back_populates="user")
    oauth_accounts = relationship("OAuthAccount", back_populates="user")
    password_reset_tokens = relationship("PasswordResetToken", back_populates="user")
    lockouts = relationship("AccountLockout", foreign_keys="[AccountLockout.user_id]", back_populates="user")
    csrf_tokens = relationship("CSRFToken", back_populates="user")

class Conversation(Base):
    """Chat conversation model - now supports multiple participants"""
    __tablename__ = "conversations"

    id = Column(String, primary_key=True, index=True)
    title = Column(String, default="New Conversation")
    model = Column(String)
    is_public = Column(Boolean, default=False)  # Public conversations visible to all users
    created_by = Column(Integer, ForeignKey("users.id"), nullable=False)  # Original creator/owner
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    # Relationships
    creator = relationship("User", foreign_keys=[created_by])
    participants = relationship("ConversationParticipant", back_populates="conversation", cascade="all, delete-orphan")
    messages = relationship("Message", back_populates="conversation", cascade="all, delete-orphan")
    documents = relationship("CollaborativeDocument", back_populates="conversation", cascade="all, delete-orphan")
    activities = relationship("ActivityLog", back_populates="conversation", cascade="all, delete-orphan")

class Message(Base):
    """Chat message model"""
    __tablename__ = "messages"

    id = Column(Integer, primary_key=True, index=True)
    conversation_id = Column(String, ForeignKey("conversations.id"), nullable=False)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True)  # For user messages
    role = Column(String, nullable=False)  # "user" or "assistant"
    content = Column(Text, nullable=False)
    model = Column(String)
    tokens_used = Column(Integer, default=0)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    # Relationships
    conversation = relationship("Conversation", back_populates="messages")
    user = relationship("User", foreign_keys=[user_id])

class ConversationParticipant(Base):
    """Many-to-many relationship between users and conversations with permissions"""
    __tablename__ = "conversation_participants"

    id = Column(Integer, primary_key=True, index=True)
    conversation_id = Column(String, ForeignKey("conversations.id"), nullable=False)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    permission_level = Column(String, default="viewer")  # "owner", "editor", "viewer"
    joined_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    last_active_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    # Relationships
    conversation = relationship("Conversation", back_populates="participants")
    user = relationship("User", back_populates="conversation_participations")

    __table_args__ = (
        {"sqlite_autoincrement": True},
    )

class UserPresence(Base):
    """Tracks user presence and online status"""
    __tablename__ = "user_presence"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, unique=True)
    is_online = Column(Boolean, default=False)
    last_seen = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    current_conversation_id = Column(String, ForeignKey("conversations.id"), nullable=True)

    # Relationships
    user = relationship("User", back_populates="presence")
    current_conversation = relationship("Conversation")

class ActivityLog(Base):
    """Logs collaborative activities"""
    __tablename__ = "activity_logs"

    id = Column(Integer, primary_key=True, index=True)
    conversation_id = Column(String, ForeignKey("conversations.id"), nullable=False)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    activity_type = Column(String, nullable=False)  # "joined", "left", "message", "edit", "permission_change"
    details = Column(JSON)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    # Relationships
    conversation = relationship("Conversation", back_populates="activities")
    user = relationship("User", back_populates="activities")

class CollaborativeDocument(Base):
    """Editable documents for collaborative editing"""
    __tablename__ = "collaborative_documents"

    id = Column(String, primary_key=True, index=True)
    conversation_id = Column(String, ForeignKey("conversations.id"), nullable=False)
    title = Column(String, nullable=False)
    document_type = Column(String, nullable=False)  # "prompt", "code", "note"
    content = Column(Text, default="")
    language = Column(String)  # For code documents
    created_by = Column(Integer, ForeignKey("users.id"), nullable=False)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))
    version = Column(Integer, default=1)

    # Relationships
    conversation = relationship("Conversation", back_populates="documents")
    creator = relationship("User", foreign_keys=[created_by])
    edits = relationship("DocumentEdit", back_populates="document", cascade="all, delete-orphan")

class DocumentEdit(Base):
    """Tracks edits to collaborative documents"""
    __tablename__ = "document_edits"

    id = Column(Integer, primary_key=True, index=True)
    document_id = Column(String, ForeignKey("collaborative_documents.id"), nullable=False)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    edit_type = Column(String, nullable=False)  # "insert", "delete", "replace"
    position = Column(Integer, nullable=False)
    old_content = Column(Text)
    new_content = Column(Text)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    # Relationships
    document = relationship("CollaborativeDocument", back_populates="edits")
    user = relationship("User", foreign_keys=[user_id])

class Task(Base):
    """Background task model"""
    __tablename__ = "tasks"

    id = Column(String, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    type = Column(String, nullable=False)
    status = Column(String, default="pending")  # pending, running, completed, failed
    data = Column(JSON)
    result = Column(JSON)
    error = Column(Text)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    started_at = Column(DateTime)
    completed_at = Column(DateTime)

    # Relationships
    user = relationship("User", back_populates="tasks")

class FileUpload(Base):
    """File upload model"""
    __tablename__ = "file_uploads"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    filename = Column(String, nullable=False)
    original_filename = Column(String, nullable=False)
    file_path = Column(String, nullable=False)
    file_size = Column(Integer, nullable=False)
    content_type = Column(String)
    uploaded_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    # Relationships
    user = relationship("User", back_populates="file_uploads")

class AuditLog(Base):
    """Audit log for security events"""
    __tablename__ = "audit_logs"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    action = Column(String, nullable=False)
    resource = Column(String)
    resource_id = Column(String)
    details = Column(JSON)
    ip_address = Column(String)
    user_agent = Column(String)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    # Relationships
    user = relationship("User", back_populates="audit_logs")

class SupportedLanguage(Base):
    """Supported languages for the application"""
    __tablename__ = "supported_languages"

    id = Column(Integer, primary_key=True, index=True)
    code = Column(String(10), unique=True, nullable=False)  # e.g., 'en', 'es', 'fr'
    name = Column(String(100), nullable=False)  # e.g., 'English', 'Español'
    native_name = Column(String(100))  # e.g., 'English', 'Español'
    is_rtl = Column(Boolean, default=False)  # Right-to-left language
    is_active = Column(Boolean, default=True)  # Whether language is currently supported
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

class UserLanguagePreference(Base):
    """User language preferences"""
    __tablename__ = "user_language_preferences"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    language_code = Column(String(10), nullable=False)
    is_preferred = Column(Boolean, default=False)  # Primary preferred language
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    # Relationships
    user = relationship("User", backref="language_preferences")

    __table_args__ = (
        {"sqlite_autoincrement": True},
    )

class Translation(Base):
    """Translation keys and values for different languages"""
    __tablename__ = "translations"

    id = Column(Integer, primary_key=True, index=True)
    namespace = Column(String(50), nullable=False)  # e.g., 'common', 'auth', 'chat'
    key = Column(String(255), nullable=False)  # e.g., 'welcome.title', 'buttons.save'
    language_code = Column(String(10), nullable=False)
    value = Column(Text, nullable=False)  # Translated text
    is_approved = Column(Boolean, default=False)  # Whether translation is approved
    created_by = Column(Integer, ForeignKey("users.id"))  # Who created/approved this translation
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    # Relationships
    creator = relationship("User", foreign_keys=[created_by])

    __table_args__ = (
        {"sqlite_autoincrement": True},
    )

class TranslationSuggestion(Base):
    """Community translation suggestions"""
    __tablename__ = "translation_suggestions"

    id = Column(Integer, primary_key=True, index=True)
    translation_id = Column(Integer, ForeignKey("translations.id"), nullable=False)
    suggested_value = Column(Text, nullable=False)
    suggested_by = Column(Integer, ForeignKey("users.id"), nullable=False)
    votes = Column(Integer, default=0)
    status = Column(String(20), default="pending")  # pending, approved, rejected
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    # Relationships
    translation = relationship("Translation", backref="suggestions")
    suggester = relationship("User", foreign_keys=[suggested_by])

class MultilingualContent(Base):
    """Multi-language support for user-generated content"""
    __tablename__ = "multilingual_content"

    id = Column(Integer, primary_key=True, index=True)
    content_type = Column(String(50), nullable=False)  # e.g., 'conversation', 'document', 'comment'
    content_id = Column(Integer, nullable=False)  # ID of the original content
    language_code = Column(String(10), nullable=False)
    title = Column(Text)  # Translated title
    content = Column(Text)  # Translated content
    content_metadata = Column(JSON)  # Additional metadata
    created_by = Column(Integer, ForeignKey("users.id"), nullable=False)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    # Relationships
    creator = relationship("User", foreign_keys=[created_by])

    __table_args__ = (
        {"sqlite_autoincrement": True},
    )

class UserType(Base):
    """User types for rate limiting (free, premium, enterprise, etc.)"""
    __tablename__ = "user_types"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(50), unique=True, nullable=False)  # e.g., 'free', 'premium', 'enterprise'
    display_name = Column(String(100), nullable=False)
    description = Column(Text)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    # Relationships
    users = relationship("User", back_populates="user_type")

class RateLimitConfig(Base):
    """Global rate limit configurations"""
    __tablename__ = "rate_limit_configs"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), unique=True, nullable=False)  # e.g., 'default_free', 'premium_limits'
    user_type_id = Column(Integer, ForeignKey("user_types.id"), nullable=True)  # Null for global defaults
    requests_per_minute = Column(Integer, default=60)
    requests_per_hour = Column(Integer, default=1000)
    requests_per_day = Column(Integer, default=5000)
    burst_limit = Column(Integer, default=10)  # Burst allowance
    window_seconds = Column(Integer, default=60)  # Sliding window size
    is_active = Column(Boolean, default=True)
    description = Column(Text)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    # Relationships
    user_type = relationship("UserType", backref="rate_limit_configs")

class UserRateLimit(Base):
    """Per-user rate limit overrides"""
    __tablename__ = "user_rate_limits"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    config_id = Column(Integer, ForeignKey("rate_limit_configs.id"), nullable=False)
    custom_limits = Column(JSON)  # Override specific limits
    is_active = Column(Boolean, default=True)
    expires_at = Column(DateTime, nullable=True)  # For temporary overrides
    created_by = Column(Integer, ForeignKey("users.id"), nullable=False)  # Admin who set this
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    # Relationships
    user = relationship("User", foreign_keys=[user_id])
    config = relationship("RateLimitConfig")
    creator = relationship("User", foreign_keys=[created_by])

    __table_args__ = (
        {"sqlite_autoincrement": True},
    )

class EndpointRateLimit(Base):
    """Endpoint-specific rate limits"""
    __tablename__ = "endpoint_rate_limits"

    id = Column(Integer, primary_key=True, index=True)
    endpoint_pattern = Column(String(255), nullable=False)  # e.g., '/api/chat', '/api/models/*'
    method = Column(String(10), default='*')  # HTTP method or '*' for all
    requests_per_minute = Column(Integer, default=30)
    requests_per_hour = Column(Integer, default=500)
    burst_limit = Column(Integer, default=5)
    window_seconds = Column(Integer, default=60)
    priority = Column(Integer, default=0)  # Higher priority overrides lower
    is_active = Column(Boolean, default=True)
    description = Column(Text)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

class RateLimitLog(Base):
    """Rate limiting events for monitoring and analytics"""
    __tablename__ = "rate_limit_logs"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    client_ip = Column(String(45), nullable=False)  # IPv4/IPv6
    endpoint = Column(String(255), nullable=False)
    method = Column(String(10), nullable=False)
    user_agent = Column(Text)
    limit_type = Column(String(50), nullable=False)  # 'user', 'endpoint', 'global'
    limit_exceeded = Column(Boolean, default=False)
    requests_remaining = Column(Integer, nullable=True)
    reset_time = Column(DateTime, nullable=True)
    response_time_ms = Column(Float, nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    # Relationships
    user = relationship("User")

    # Note: Indexes can be added later if needed for performance

class SystemLoadMetrics(Base):
    """System load metrics for automatic rate limit adjustments"""
    __tablename__ = "system_load_metrics"

    id = Column(Integer, primary_key=True, index=True)
    cpu_percent = Column(Float, nullable=False)
    memory_percent = Column(Float, nullable=False)
    disk_io_percent = Column(Float, nullable=True)
    network_io_percent = Column(Float, nullable=True)
    active_connections = Column(Integer, default=0)
    queue_length = Column(Integer, default=0)
    response_time_avg = Column(Float, nullable=True)  # Average response time in ms
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    # Note: Indexes can be added later if needed for performance

# Enhanced Authentication Models

class Role(Base):
    """User roles for role-based access control"""
    __tablename__ = "roles"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(50), unique=True, nullable=False)  # 'admin', 'moderator', 'user', 'premium'
    display_name = Column(String(100), nullable=False)
    description = Column(Text)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    # Relationships
    user_roles = relationship("UserRole", back_populates="role")
    role_permissions = relationship("RolePermission", back_populates="role")

class Permission(Base):
    """Individual permissions that can be assigned to roles"""
    __tablename__ = "permissions"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), unique=True, nullable=False)  # 'create_user', 'delete_post', 'manage_system'
    display_name = Column(String(200), nullable=False)
    description = Column(Text)
    resource = Column(String(100))  # 'user', 'post', 'system', etc.
    action = Column(String(50))  # 'create', 'read', 'update', 'delete', 'manage'
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    # Relationships
    permissions = relationship("RolePermission", back_populates="permission")

class UserRole(Base):
    """Many-to-many relationship between users and roles"""
    __tablename__ = "user_roles"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    role_id = Column(Integer, ForeignKey("roles.id"), nullable=False)
    assigned_by = Column(Integer, ForeignKey("users.id"), nullable=True)  # Who assigned this role
    assigned_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    expires_at = Column(DateTime, nullable=True)  # For temporary role assignments

    # Relationships
    user = relationship("User", foreign_keys=[user_id], back_populates="user_roles")
    role = relationship("Role", foreign_keys=[role_id], back_populates="user_roles")
    assigner = relationship("User", foreign_keys=[assigned_by])

    __table_args__ = (
        UniqueConstraint('user_id', 'role_id', name='unique_user_role'),
    )

class RolePermission(Base):
    """Many-to-many relationship between roles and permissions"""
    __tablename__ = "role_permissions"

    id = Column(Integer, primary_key=True, index=True)
    role_id = Column(Integer, ForeignKey("roles.id"), nullable=False)
    permission_id = Column(Integer, ForeignKey("permissions.id"), nullable=False)
    assigned_by = Column(Integer, ForeignKey("users.id"), nullable=True)
    assigned_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    # Relationships
    role = relationship("Role", back_populates="role_permissions")
    permission = relationship("Permission", back_populates="permissions")
    assigner = relationship("User", foreign_keys=[assigned_by])

    __table_args__ = (
        UniqueConstraint('role_id', 'permission_id', name='unique_role_permission'),
    )

class UserSession(Base):
    """User sessions for session management"""
    __tablename__ = "user_sessions"

    id = Column(String, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    device_info = Column(JSON)  # Browser, OS, device details
    ip_address = Column(String(45))  # IPv4/IPv6
    user_agent = Column(Text)
    location = Column(JSON)  # Geographic location if available
    is_active = Column(Boolean, default=True)
    last_activity = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    expires_at = Column(DateTime, nullable=False)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    # Relationships
    user = relationship("User", back_populates="sessions")

    # Indexes
    __table_args__ = (
        Index('idx_session_user_active', 'user_id', 'is_active'),
        Index('idx_session_expires', 'expires_at'),
    )

class RefreshToken(Base):
    """JWT refresh tokens"""
    __tablename__ = "refresh_tokens"

    id = Column(String, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    token_hash = Column(String, nullable=False)  # Hashed token for security
    device_info = Column(JSON)
    ip_address = Column(String(45))
    user_agent = Column(Text)
    is_active = Column(Boolean, default=True)
    expires_at = Column(DateTime, nullable=False)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    last_used_at = Column(DateTime)

    # Relationships
    user = relationship("User", back_populates="refresh_tokens")

    # Indexes
    __table_args__ = (
        Index('idx_refresh_user_active', 'user_id', 'is_active'),
        Index('idx_refresh_expires', 'expires_at'),
    )

class OAuthAccount(Base):
    """OAuth provider accounts linked to users"""
    __tablename__ = "oauth_accounts"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    provider = Column(String(50), nullable=False)  # 'google', 'github'
    provider_user_id = Column(String, nullable=False)
    provider_username = Column(String)
    provider_email = Column(String)
    access_token = Column(Text)  # Encrypted
    refresh_token = Column(Text)  # Encrypted
    token_expires_at = Column(DateTime)
    scopes = Column(JSON)  # OAuth scopes granted
    profile_data = Column(JSON)  # Additional profile data from provider
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    # Relationships
    user = relationship("User", back_populates="oauth_accounts")

    __table_args__ = (
        UniqueConstraint('provider', 'provider_user_id', name='unique_provider_user'),
        Index('idx_oauth_user_provider', 'user_id', 'provider'),
    )

class PasswordResetToken(Base):
    """Password reset tokens"""
    __tablename__ = "password_reset_tokens"

    id = Column(String, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    token_hash = Column(String, nullable=False)  # Hashed token
    email = Column(String, nullable=False)  # Email at time of request
    is_used = Column(Boolean, default=False)
    expires_at = Column(DateTime, nullable=False)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    used_at = Column(DateTime)
    used_ip = Column(String(45))

    # Relationships
    user = relationship("User", back_populates="password_reset_tokens")

    # Indexes
    __table_args__ = (
        Index('idx_reset_user', 'user_id', 'is_used'),
        Index('idx_reset_expires', 'expires_at'),
    )

class AccountLockout(Base):
    """Account lockout tracking"""
    __tablename__ = "account_lockouts"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    reason = Column(String(100), default="failed_login_attempts")  # 'failed_login', 'suspicious_activity'
    lockout_until = Column(DateTime, nullable=False)
    failed_attempts = Column(Integer, default=0)
    last_failed_attempt = Column(DateTime)
    ip_addresses = Column(JSON)  # List of IPs that triggered lockout
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    unlocked_at = Column(DateTime)
    unlocked_by = Column(Integer, ForeignKey("users.id"), nullable=True)  # Admin who unlocked

    # Relationships
    user = relationship("User", foreign_keys=[user_id], back_populates="lockouts")
    unlocker = relationship("User", foreign_keys=[unlocked_by])

    # Indexes
    __table_args__ = (
        Index('idx_lockout_user_active', 'user_id', 'is_active'),
        Index('idx_lockout_until', 'lockout_until'),
    )

class CSRFToken(Base):
    """CSRF protection tokens"""
    __tablename__ = "csrf_tokens"

    id = Column(String, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    session_id = Column(String, ForeignKey("user_sessions.id"), nullable=True)
    token_hash = Column(String, nullable=False)  # Hashed token
    is_active = Column(Boolean, default=True)
    expires_at = Column(DateTime, nullable=False)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    last_used_at = Column(DateTime)

    # Relationships
    user = relationship("User", back_populates="csrf_tokens")
    session = relationship("UserSession", backref="csrf_tokens")

    # Indexes
    __table_args__ = (
        Index('idx_csrf_user_active', 'user_id', 'is_active'),
        Index('idx_csrf_expires', 'expires_at'),
    )


# Onboarding and Tutorial System Models

class OnboardingFlow(Base):
    """Defines different onboarding flows for different user types"""
    __tablename__ = "onboarding_flows"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False)  # e.g., 'regular_user', 'admin_user', 'premium_user'
    display_name = Column(String(200), nullable=False)
    description = Column(Text)
    user_type_id = Column(Integer, ForeignKey("user_types.id"), nullable=True)  # Null for generic flows
    is_active = Column(Boolean, default=True)
    is_default = Column(Boolean, default=False)  # Default flow for user type
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    # Relationships
    user_type = relationship("UserType", backref="onboarding_flows")
    steps = relationship("OnboardingStep", back_populates="flow", cascade="all, delete-orphan")


class OnboardingStep(Base):
    """Individual steps in an onboarding flow"""
    __tablename__ = "onboarding_steps"

    id = Column(Integer, primary_key=True, index=True)
    flow_id = Column(Integer, ForeignKey("onboarding_flows.id"), nullable=False)
    step_order = Column(Integer, nullable=False)  # Order within the flow
    title = Column(String(200), nullable=False)
    description = Column(Text)
    content_type = Column(String(50), nullable=False)  # 'modal', 'tooltip', 'highlight', 'interactive'
    target_element = Column(String(255))  # CSS selector for highlighting/interaction
    content = Column(JSON)  # Flexible content structure (text, images, actions, etc.)
    is_required = Column(Boolean, default=True)  # Whether step can be skipped
    auto_advance = Column(Boolean, default=False)  # Auto-advance after completion
    estimated_duration = Column(Integer, default=30)  # Estimated seconds to complete
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    # Relationships
    flow = relationship("OnboardingFlow", back_populates="steps")


class UserOnboardingProgress(Base):
    """Tracks user's progress through onboarding flows"""
    __tablename__ = "user_onboarding_progress"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    flow_id = Column(Integer, ForeignKey("onboarding_flows.id"), nullable=False)
    current_step_id = Column(Integer, ForeignKey("onboarding_steps.id"), nullable=True)
    status = Column(String(20), default="not_started")  # 'not_started', 'in_progress', 'completed', 'skipped'
    completed_steps = Column(JSON, default=list)  # List of completed step IDs
    skipped_steps = Column(JSON, default=list)  # List of skipped step IDs
    started_at = Column(DateTime)
    completed_at = Column(DateTime)
    last_activity_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    total_time_spent = Column(Integer, default=0)  # Total seconds spent
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    # Relationships
    user = relationship("User", backref="onboarding_progress")
    flow = relationship("OnboardingFlow", backref="user_progress")
    current_step = relationship("OnboardingStep")


class Tutorial(Base):
    """Video tutorials and walkthroughs"""
    __tablename__ = "tutorials"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(200), nullable=False)
    description = Column(Text)
    category = Column(String(100), nullable=False)  # 'getting_started', 'ai_chat', 'collaborative_editing', 'admin_features', etc.
    difficulty_level = Column(String(20), default="beginner")  # 'beginner', 'intermediate', 'advanced'
    content_type = Column(String(50), nullable=False)  # 'video', 'interactive', 'text', 'mixed'
    video_url = Column(String(500))  # URL to video file or streaming service
    thumbnail_url = Column(String(500))  # Thumbnail image URL
    content = Column(JSON)  # Structured content for interactive tutorials
    estimated_duration = Column(Integer, default=300)  # Estimated seconds
    tags = Column(JSON, default=list)  # Searchable tags
    is_active = Column(Boolean, default=True)
    view_count = Column(Integer, default=0)
    completion_count = Column(Integer, default=0)
    average_rating = Column(Float, default=0.0)
    created_by = Column(Integer, ForeignKey("users.id"), nullable=True)  # Admin who created it
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    # Relationships
    creator = relationship("User", foreign_keys=[created_by])


class TutorialProgress(Base):
    """Tracks user's progress through tutorials"""
    __tablename__ = "tutorial_progress"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    tutorial_id = Column(Integer, ForeignKey("tutorials.id"), nullable=False)
    status = Column(String(20), default="not_started")  # 'not_started', 'in_progress', 'completed', 'paused'
    progress_percentage = Column(Float, default=0.0)  # 0-100
    current_position = Column(JSON)  # Current position in interactive tutorial
    time_spent = Column(Integer, default=0)  # Total seconds spent
    completed_at = Column(DateTime)
    last_activity_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    rating = Column(Integer)  # 1-5 star rating
    feedback = Column(Text)  # User feedback
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    # Relationships
    user = relationship("User", backref="tutorial_progress")
    tutorial = relationship("Tutorial", backref="user_progress")


class UserTutorialAnalytics(Base):
    """Analytics for tutorial usage and effectiveness"""
    __tablename__ = "user_tutorial_analytics"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    tutorial_id = Column(Integer, ForeignKey("tutorials.id"), nullable=False)
    event_type = Column(String(50), nullable=False)  # 'started', 'completed', 'paused', 'seeked', 'interacted'
    event_data = Column(JSON)  # Additional event data
    timestamp = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    session_id = Column(String(100))  # For grouping related events

    # Relationships
    user = relationship("User", backref="tutorial_analytics")
    tutorial = relationship("Tutorial", backref="analytics")

    __table_args__ = (
        Index('idx_tutorial_analytics_user', 'user_id', 'timestamp'),
        Index('idx_tutorial_analytics_tutorial', 'tutorial_id', 'event_type'),
    )

class HelpCategory(Base):
    """Categories for organizing help articles"""
    __tablename__ = "help_categories"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False)
    display_name = Column(String(200), nullable=False)
    description = Column(Text)
    icon = Column(String(50))  # Icon identifier
    parent_id = Column(Integer, ForeignKey("help_categories.id"), nullable=True)  # For subcategories
    sort_order = Column(Integer, default=0)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    # Relationships
    parent = relationship("HelpCategory", remote_side=[id], backref="subcategories")
    articles = relationship("HelpArticle", back_populates="category")

class HelpArticle(Base):
    """Help center articles and documentation"""
    __tablename__ = "help_articles"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(200), nullable=False)
    slug = Column(String(200), unique=True, nullable=False)  # URL-friendly identifier
    content = Column(Text, nullable=False)
    summary = Column(Text)  # Short summary for search results
    category_id = Column(Integer, ForeignKey("help_categories.id"), nullable=False)
    tags = Column(JSON, default=list)  # Searchable tags
    difficulty_level = Column(String(20), default="beginner")  # 'beginner', 'intermediate', 'advanced'
    view_count = Column(Integer, default=0)
    helpful_votes = Column(Integer, default=0)
    total_votes = Column(Integer, default=0)
    is_featured = Column(Boolean, default=False)
    is_active = Column(Boolean, default=True)
    created_by = Column(Integer, ForeignKey("users.id"), nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    # Relationships
    category = relationship("HelpCategory", back_populates="articles")
    creator = relationship("User", foreign_keys=[created_by])

    __table_args__ = (
        Index('idx_help_article_category', 'category_id', 'is_active'),
        Index('idx_help_article_tags', 'tags', postgresql_using='gin'),
        Index('idx_help_article_search', 'title', 'summary', 'content'),
    )

class Tooltip(Base):
    """Contextual help tooltips and hints"""
    __tablename__ = "tooltips"

    id = Column(Integer, primary_key=True, index=True)
    identifier = Column(String(100), unique=True, nullable=False)  # Unique identifier for the tooltip
    title = Column(String(200), nullable=False)
    content = Column(Text, nullable=False)
    target_element = Column(String(255), nullable=False)  # CSS selector
    trigger_event = Column(String(50), default="hover")  # 'hover', 'click', 'focus', 'auto'
    position = Column(String(20), default="top")  # 'top', 'bottom', 'left', 'right', 'auto'
    show_once = Column(Boolean, default=False)  # Show only once per user
    user_type_restrictions = Column(JSON, default=list)  # List of user types that can see this tooltip
    conditions = Column(JSON)  # Conditions for showing (e.g., first visit, feature not used)
    priority = Column(Integer, default=0)  # Higher priority tooltips show first
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

class UserTooltipInteraction(Base):
    """Tracks user interactions with tooltips"""
    __tablename__ = "user_tooltip_interactions"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    tooltip_id = Column(Integer, ForeignKey("tooltips.id"), nullable=False)
    interaction_type = Column(String(20), nullable=False)  # 'viewed', 'dismissed', 'clicked', 'followed_link'
    interaction_data = Column(JSON)  # Additional interaction data
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    # Relationships
    user = relationship("User", backref="tooltip_interactions")
    tooltip = relationship("Tooltip", backref="interactions")

    __table_args__ = (
        Index('idx_tooltip_interaction_user', 'user_id', 'tooltip_id'),
    )

class SupportChat(Base):
    """In-app support chat conversations"""
    __tablename__ = "support_chats"

    id = Column(String, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    subject = Column(String(200))
    status = Column(String(20), default="open")  # 'open', 'in_progress', 'resolved', 'closed'
    priority = Column(String(20), default="normal")  # 'low', 'normal', 'high', 'urgent'
    category = Column(String(100))  # Support category
    assigned_to = Column(Integer, ForeignKey("users.id"), nullable=True)  # Support agent
    is_live_chat = Column(Boolean, default=False)  # Whether it's a live chat session
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))
    resolved_at = Column(DateTime)
    satisfaction_rating = Column(Integer)  # 1-5 satisfaction rating

    # Relationships
    user = relationship("User", foreign_keys=[user_id], backref="support_chats")
    agent = relationship("User", foreign_keys=[assigned_to], backref="assigned_chats")
    messages = relationship("SupportMessage", back_populates="chat", cascade="all, delete-orphan")

class SupportMessage(Base):
    """Individual messages in support chat conversations"""
    __tablename__ = "support_messages"

    id = Column(Integer, primary_key=True, index=True)
    chat_id = Column(String, ForeignKey("support_chats.id"), nullable=False)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True)  # Null for system/agent messages
    message_type = Column(String(20), default="text")  # 'text', 'file', 'system'
    content = Column(Text, nullable=False)
    attachments = Column(JSON, default=list)  # File attachments
    is_from_user = Column(Boolean, default=True)  # True for user messages, False for agent/system
    is_read = Column(Boolean, default=False)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    # Relationships
    chat = relationship("SupportChat", back_populates="messages")
    user = relationship("User", foreign_keys=[user_id])

    __table_args__ = (
        Index('idx_support_message_chat', 'chat_id', 'created_at'),
    )

class ExportOperation(Base):
    """Tracks data export operations"""
    __tablename__ = "export_operations"

    id = Column(String, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    schedule_id = Column(Integer, ForeignKey("export_schedules.id"), nullable=True)  # For scheduled exports
    export_type = Column(String, nullable=False)  # "user_data", "conversations", "bulk_admin", "system_backup"
    format = Column(String, nullable=False)  # "json", "csv", "pdf", "html"
    status = Column(String, default="pending")  # "pending", "running", "completed", "failed", "cancelled"
    data_scope = Column(JSON)  # What data to export (user_ids, conversation_ids, date_range, etc.)
    filters = Column(JSON)  # Additional filters (date_range, content_types, etc.)
    file_path = Column(String)  # Path to exported file
    file_size = Column(Integer)  # Size in bytes
    checksum = Column(String)  # File checksum for integrity
    encryption_key = Column(String)  # Encryption key if encrypted
    download_url = Column(String)  # Temporary download URL
    expires_at = Column(DateTime)  # When download URL expires
    progress = Column(Float, default=0.0)  # Progress percentage (0-100)
    total_records = Column(Integer, default=0)  # Total records to export
    processed_records = Column(Integer, default=0)  # Records processed so far
    error_message = Column(Text)  # Error details if failed
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    started_at = Column(DateTime)
    completed_at = Column(DateTime)
    requested_by_ip = Column(String)
    user_agent = Column(String)

    # Relationships
    user = relationship("User", backref="export_operations")

    # Indexes
    __table_args__ = (
        Index('idx_export_user_status', 'user_id', 'status'),
        Index('idx_export_type_status', 'export_type', 'status'),
        Index('idx_export_created_at', 'created_at'),
    )

class ImportOperation(Base):
    """Tracks data import operations"""
    __tablename__ = "import_operations"

    id = Column(String, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    import_type = Column(String, nullable=False)  # "user_data", "conversations", "bulk_admin"
    source_format = Column(String, nullable=False)  # "json", "csv"
    status = Column(String, default="pending")  # "pending", "running", "completed", "failed", "cancelled"
    source_file_path = Column(String)  # Path to source file
    data_validation = Column(JSON)  # Validation results
    import_summary = Column(JSON)  # Summary of imported data
    progress = Column(Float, default=0.0)  # Progress percentage (0-100)
    total_records = Column(Integer, default=0)  # Total records to import
    processed_records = Column(Integer, default=0)  # Records processed so far
    successful_records = Column(Integer, default=0)  # Successfully imported records
    failed_records = Column(Integer, default=0)  # Failed records
    skipped_records = Column(Integer, default=0)  # Skipped records (duplicates, etc.)
    error_message = Column(Text)  # Error details if failed
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    started_at = Column(DateTime)
    completed_at = Column(DateTime)
    requested_by_ip = Column(String)
    user_agent = Column(String)

    # Relationships
    user = relationship("User", backref="import_operations")

    # Indexes
    __table_args__ = (
        Index('idx_import_user_status', 'user_id', 'status'),
        Index('idx_import_type_status', 'import_type', 'status'),
        Index('idx_import_created_at', 'created_at'),
    )

class ExportSchedule(Base):
    """Scheduled export operations"""
    __tablename__ = "export_schedules"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    description = Column(Text)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)  # Who created the schedule
    export_type = Column(String, nullable=False)  # "user_data", "conversations", "bulk_admin"
    format = Column(String, nullable=False)  # "json", "csv", "pdf", "html"
    schedule_type = Column(String, nullable=False)  # "daily", "weekly", "monthly", "custom"
    schedule_config = Column(JSON)  # Cron expression or schedule details
    data_scope = Column(JSON)  # What data to export
    filters = Column(JSON)  # Additional filters
    is_active = Column(Boolean, default=True)
    last_run_at = Column(DateTime)
    next_run_at = Column(DateTime)
    retention_days = Column(Integer, default=30)  # How long to keep exported files
    notification_email = Column(String)  # Email to notify when export completes
    encryption_enabled = Column(Boolean, default=False)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    # Relationships
    user = relationship("User", backref="export_schedules")
    operations = relationship("ExportOperation", backref="schedule", cascade="all, delete-orphan")

    # Indexes
    __table_args__ = (
        Index('idx_schedule_user_active', 'user_id', 'is_active'),
        Index('idx_schedule_next_run', 'next_run_at'),
        Index('idx_schedule_type', 'schedule_type'),
    )

class DataValidationRule(Base):
    """Validation rules for data import/export"""
    __tablename__ = "data_validation_rules"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    rule_type = Column(String, nullable=False)  # "export", "import", "both"
    data_type = Column(String, nullable=False)  # "user", "conversation", "message", "file"
    validation_function = Column(String, nullable=False)  # Python function name
    parameters = Column(JSON)  # Parameters for validation function
    error_message = Column(String, nullable=False)
    is_active = Column(Boolean, default=True)
    severity = Column(String, default="error")  # "error", "warning", "info"
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    # Indexes
    __table_args__ = (
        Index('idx_validation_rule_type', 'rule_type', 'data_type'),
        Index('idx_validation_active', 'is_active'),
    )

# Notification System Models

class NotificationTemplate(Base):
    """Templates for different notification types with multi-language support"""
    __tablename__ = "notification_templates"

    id = Column(Integer, primary_key=True, index=True)
    template_key = Column(String(100), unique=True, nullable=False)  # e.g., 'chat_message', 'system_update'
    name = Column(String(200), nullable=False)
    description = Column(Text)
    category = Column(String(50), nullable=False)  # 'chat', 'system', 'security', 'marketing', 'admin'
    priority = Column(String(20), default="normal")  # 'low', 'normal', 'high', 'urgent'
    channels = Column(JSON, default=list)  # ['in_app', 'email', 'push', 'websocket']
    is_active = Column(Boolean, default=True)
    requires_opt_in = Column(Boolean, default=False)  # GDPR compliance
    created_by = Column(Integer, ForeignKey("users.id"), nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    # Relationships
    creator = relationship("User", foreign_keys=[created_by])
    translations = relationship("NotificationTemplateTranslation", back_populates="template", cascade="all, delete-orphan")

    # Indexes
    __table_args__ = (
        Index('idx_template_key_active', 'template_key', 'is_active'),
        Index('idx_template_category', 'category'),
    )

class NotificationTemplateTranslation(Base):
    """Multi-language translations for notification templates"""
    __tablename__ = "notification_template_translations"

    id = Column(Integer, primary_key=True, index=True)
    template_id = Column(Integer, ForeignKey("notification_templates.id"), nullable=False)
    language_code = Column(String(10), nullable=False)
    subject = Column(String(500))  # For email notifications
    title = Column(String(200), nullable=False)  # For in-app notifications
    body = Column(Text, nullable=False)
    action_url = Column(String(500))  # Optional action URL
    action_text = Column(String(100))  # Action button text
    variables = Column(JSON)  # Available template variables
    is_approved = Column(Boolean, default=False)
    created_by = Column(Integer, ForeignKey("users.id"), nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    # Relationships
    template = relationship("NotificationTemplate", back_populates="translations")
    creator = relationship("User", foreign_keys=[created_by])

    # Indexes
    __table_args__ = (
        UniqueConstraint('template_id', 'language_code', name='unique_template_language'),
        Index('idx_translation_template_lang', 'template_id', 'language_code'),
    )

class Notification(Base):
    """Individual notification instances"""
    __tablename__ = "notifications"

    id = Column(String, primary_key=True, index=True)
    template_id = Column(Integer, ForeignKey("notification_templates.id"), nullable=False)
    recipient_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    sender_id = Column(Integer, ForeignKey("users.id"), nullable=True)  # For user-to-user notifications
    title = Column(String(200), nullable=False)
    message = Column(Text, nullable=False)
    data = Column(JSON)  # Additional notification data
    priority = Column(String(20), default="normal")  # 'low', 'normal', 'high', 'urgent'
    category = Column(String(50), nullable=False)
    is_read = Column(Boolean, default=False)
    read_at = Column(DateTime)
    expires_at = Column(DateTime)  # Auto-expire old notifications
    action_url = Column(String(500))  # Optional action URL
    action_text = Column(String(100))  # Action button text
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    # Relationships
    template = relationship("NotificationTemplate")
    recipient = relationship("User", foreign_keys=[recipient_id])
    sender = relationship("User", foreign_keys=[sender_id])
    deliveries = relationship("NotificationDelivery", back_populates="notification", cascade="all, delete-orphan")

    # Indexes
    __table_args__ = (
        Index('idx_notification_recipient', 'recipient_id', 'is_read', 'created_at'),
        Index('idx_notification_category', 'category', 'created_at'),
        Index('idx_notification_expires', 'expires_at'),
    )

class NotificationDelivery(Base):
    """Tracks delivery attempts and status for notifications"""
    __tablename__ = "notification_deliveries"

    id = Column(Integer, primary_key=True, index=True)
    notification_id = Column(String, ForeignKey("notifications.id"), nullable=False)
    channel = Column(String(20), nullable=False)  # 'in_app', 'email', 'push', 'websocket'
    status = Column(String(20), default="pending")  # 'pending', 'sent', 'delivered', 'failed', 'retry'
    provider = Column(String(50))  # 'smtp', 'firebase', 'websocket', etc.
    provider_message_id = Column(String(255))  # External provider's message ID
    recipient_address = Column(String(255))  # email, device token, etc.
    attempt_count = Column(Integer, default=0)
    max_attempts = Column(Integer, default=3)
    last_attempt_at = Column(DateTime)
    delivered_at = Column(DateTime)
    failed_at = Column(DateTime)
    error_message = Column(Text)
    retry_after = Column(DateTime)  # When to retry failed deliveries
    delivery_metadata = Column(JSON)  # Additional delivery metadata
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    # Relationships
    notification = relationship("Notification", back_populates="deliveries")

    # Indexes
    __table_args__ = (
        Index('idx_delivery_notification', 'notification_id', 'channel'),
        Index('idx_delivery_status', 'status', 'retry_after'),
        Index('idx_delivery_provider', 'provider', 'provider_message_id'),
    )

class NotificationPreference(Base):
    """User preferences for notification types and channels"""
    __tablename__ = "notification_preferences"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    template_key = Column(String(100), nullable=True)  # Specific template or None for category
    category = Column(String(50), nullable=True)  # Category preference if template_key is None
    channel = Column(String(20), nullable=False)  # 'in_app', 'email', 'push', 'websocket'
    enabled = Column(Boolean, default=True)
    frequency = Column(String(20), default="immediate")  # 'immediate', 'daily', 'weekly', 'never'
    quiet_hours_start = Column(String(5))  # HH:MM format, e.g., '22:00'
    quiet_hours_end = Column(String(5))  # HH:MM format, e.g., '08:00'
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    # Relationships
    user = relationship("User", backref="notification_preferences")

    # Indexes
    __table_args__ = (
        UniqueConstraint('user_id', 'template_key', 'channel', name='unique_user_template_channel'),
        Index('idx_preference_user', 'user_id', 'enabled'),
        Index('idx_preference_category', 'category', 'channel'),
    )

class NotificationHistory(Base):
    """Archived notification history for analytics and compliance"""
    __tablename__ = "notification_history"

    id = Column(Integer, primary_key=True, index=True)
    notification_id = Column(String, nullable=False)  # Original notification ID (may be deleted)
    template_key = Column(String(100), nullable=False)
    recipient_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    sender_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    title = Column(String(200), nullable=False)
    message = Column(Text, nullable=False)
    category = Column(String(50), nullable=False)
    priority = Column(String(20), default="normal")
    channels_sent = Column(JSON, default=list)  # List of channels used
    delivery_status = Column(JSON)  # Delivery status per channel
    user_interaction = Column(String(20))  # 'read', 'clicked', 'dismissed', 'ignored'
    interaction_timestamp = Column(DateTime)
    archived_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    # Relationships
    recipient = relationship("User", foreign_keys=[recipient_id])
    sender = relationship("User", foreign_keys=[sender_id])

    # Indexes
    __table_args__ = (
        Index('idx_history_recipient', 'recipient_id', 'archived_at'),
        Index('idx_history_template', 'template_key', 'archived_at'),
        Index('idx_history_category', 'category', 'archived_at'),
        Index('idx_history_interaction', 'user_interaction', 'interaction_timestamp'),
    )

class NotificationAnalytics(Base):
    """Analytics data for notification system performance"""
    __tablename__ = "notification_analytics"

    id = Column(Integer, primary_key=True, index=True)
    date = Column(Date, nullable=False)  # Date for aggregation
    template_key = Column(String(100), nullable=True)  # Null for global stats
    category = Column(String(50), nullable=True)
    channel = Column(String(20), nullable=True)
    metric_type = Column(String(50), nullable=False)  # 'sent', 'delivered', 'read', 'clicked', 'failed'
    count = Column(Integer, default=0)
    average_delivery_time = Column(Float)  # In seconds
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    # Indexes
    __table_args__ = (
        UniqueConstraint('date', 'template_key', 'category', 'channel', 'metric_type', name='unique_analytics_entry'),
        Index('idx_analytics_date', 'date'),
        Index('idx_analytics_template', 'template_key', 'date'),
        Index('idx_analytics_category', 'category', 'date'),
    )

def get_db():
    """Dependency to get database session"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def init_database():
    """Initialize database and create tables"""
    try:
        Base.metadata.create_all(bind=engine)
        logger.info("Database initialized successfully")

        # Create default data after tables are created
        db = SessionLocal()
        try:
            # Create supported languages if they don't exist
            supported_languages = [
                {"code": "en", "name": "English", "native_name": "English", "is_rtl": False},
                {"code": "es", "name": "Spanish", "native_name": "Español", "is_rtl": False},
                {"code": "fr", "name": "French", "native_name": "Français", "is_rtl": False},
                {"code": "de", "name": "German", "native_name": "Deutsch", "is_rtl": False},
                {"code": "ar", "name": "Arabic", "native_name": "العربية", "is_rtl": True},
                {"code": "zh", "name": "Chinese", "native_name": "中文", "is_rtl": False},
            ]

            for lang_data in supported_languages:
                existing_lang = db.query(SupportedLanguage).filter(SupportedLanguage.code == lang_data["code"]).first()
                if not existing_lang:
                    lang = SupportedLanguage(**lang_data)
                    db.add(lang)
                    logger.info(f"Created supported language: {lang_data['name']}")

            # Create default user types if they don't exist
            user_types = [
                {"name": "free", "display_name": "Free Tier", "description": "Basic access with limited requests"},
                {"name": "premium", "display_name": "Premium Tier", "description": "Enhanced access with higher limits"},
                {"name": "enterprise", "display_name": "Enterprise Tier", "description": "Unlimited access for organizations"},
            ]

            for type_data in user_types:
                existing_type = db.query(UserType).filter(UserType.name == type_data["name"]).first()
                if not existing_type:
                    user_type = UserType(**type_data)
                    db.add(user_type)
                    logger.info(f"Created user type: {type_data['name']}")

            # Create default rate limit configurations
            default_configs = [
                {
                    "name": "free_tier_limits",
                    "user_type_id": 1,  # free
                    "requests_per_minute": 30,
                    "requests_per_hour": 500,
                    "requests_per_day": 2000,
                    "burst_limit": 5,
                    "description": "Default limits for free tier users"
                },
                {
                    "name": "premium_tier_limits",
                    "user_type_id": 2,  # premium
                    "requests_per_minute": 120,
                    "requests_per_hour": 2000,
                    "requests_per_day": 10000,
                    "burst_limit": 20,
                    "description": "Enhanced limits for premium tier users"
                },
                {
                    "name": "enterprise_tier_limits",
                    "user_type_id": 3,  # enterprise
                    "requests_per_minute": 500,
                    "requests_per_hour": 10000,
                    "requests_per_day": 50000,
                    "burst_limit": 100,
                    "description": "High limits for enterprise tier users"
                },
            ]

            for config_data in default_configs:
                existing_config = db.query(RateLimitConfig).filter(RateLimitConfig.name == config_data["name"]).first()
                if not existing_config:
                    config = RateLimitConfig(**config_data)
                    db.add(config)
                    logger.info(f"Created rate limit config: {config_data['name']}")

            # Create default endpoint-specific limits
            endpoint_limits = [
                {
                    "endpoint_pattern": "/api/chat",
                    "method": "POST",
                    "requests_per_minute": 20,
                    "requests_per_hour": 300,
                    "burst_limit": 3,
                    "description": "Chat endpoint rate limits"
                },
                {
                    "endpoint_pattern": "/api/models/*",
                    "method": "GET",
                    "requests_per_minute": 60,
                    "requests_per_hour": 1000,
                    "burst_limit": 10,
                    "description": "Model listing endpoints"
                },
                {
                    "endpoint_pattern": "/auth/login",
                    "method": "POST",
                    "requests_per_minute": 5,
                    "requests_per_hour": 20,
                    "burst_limit": 1,
                    "description": "Login endpoint strict limits"
                },
            ]

            for limit_data in endpoint_limits:
                existing_limit = db.query(EndpointRateLimit).filter(
                    EndpointRateLimit.endpoint_pattern == limit_data["endpoint_pattern"],
                    EndpointRateLimit.method == limit_data["method"]
                ).first()
                if not existing_limit:
                    limit = EndpointRateLimit(**limit_data)
                    db.add(limit)
                    logger.info(f"Created endpoint rate limit: {limit_data['endpoint_pattern']}")

            # Create default roles
            default_roles = [
                {"name": "admin", "display_name": "Administrator", "description": "Full system access and management"},
                {"name": "moderator", "display_name": "Moderator", "description": "Content moderation and user management"},
                {"name": "premium", "display_name": "Premium User", "description": "Enhanced features and higher limits"},
                {"name": "user", "display_name": "Regular User", "description": "Standard user access"}
            ]

            for role_data in default_roles:
                existing_role = db.query(Role).filter(Role.name == role_data["name"]).first()
                if not existing_role:
                    role = Role(**role_data)
                    db.add(role)
                    logger.info(f"Created role: {role_data['name']}")

            # Create default permissions
            default_permissions = [
                # User management
                {"name": "create_user", "display_name": "Create Users", "resource": "user", "action": "create"},
                {"name": "read_user", "display_name": "View Users", "resource": "user", "action": "read"},
                {"name": "update_user", "display_name": "Update Users", "resource": "user", "action": "update"},
                {"name": "delete_user", "display_name": "Delete Users", "resource": "user", "action": "delete"},
                {"name": "manage_user_roles", "display_name": "Manage User Roles", "resource": "user", "action": "manage"},

                # Content management
                {"name": "create_content", "display_name": "Create Content", "resource": "content", "action": "create"},
                {"name": "read_content", "display_name": "View Content", "resource": "content", "action": "read"},
                {"name": "update_content", "display_name": "Update Content", "resource": "content", "action": "update"},
                {"name": "delete_content", "display_name": "Delete Content", "resource": "content", "action": "delete"},
                {"name": "moderate_content", "display_name": "Moderate Content", "resource": "content", "action": "moderate"},

                # System management
                {"name": "manage_system", "display_name": "Manage System", "resource": "system", "action": "manage"},
                {"name": "view_analytics", "display_name": "View Analytics", "resource": "analytics", "action": "read"},
                {"name": "manage_security", "display_name": "Manage Security", "resource": "security", "action": "manage"},
            ]

            for perm_data in default_permissions:
                existing_perm = db.query(Permission).filter(Permission.name == perm_data["name"]).first()
                if not existing_perm:
                    permission = Permission(**perm_data)
                    db.add(permission)
                    logger.info(f"Created permission: {perm_data['name']}")

            # Assign permissions to roles
            role_permissions = {
                "admin": ["create_user", "read_user", "update_user", "delete_user", "manage_user_roles",
                         "create_content", "read_content", "update_content", "delete_content", "moderate_content",
                         "manage_system", "view_analytics", "manage_security"],
                "moderator": ["read_user", "update_user", "read_content", "update_content", "delete_content", "moderate_content"],
                "premium": ["create_content", "read_content", "update_content"],
                "user": ["create_content", "read_content", "update_content"]
            }

            for role_name, perm_names in role_permissions.items():
                role = db.query(Role).filter(Role.name == role_name).first()
                if role:
                    for perm_name in perm_names:
                        permission = db.query(Permission).filter(Permission.name == perm_name).first()
                        if permission:
                            # Check if already assigned
                            existing = db.query(RolePermission).filter(
                                RolePermission.role_id == role.id,
                                RolePermission.permission_id == permission.id
                            ).first()
                            if not existing:
                                role_perm = RolePermission(role_id=role.id, permission_id=permission.id)
                                db.add(role_perm)
                                logger.info(f"Assigned permission {perm_name} to role {role_name}")

            # Create demo user for testing
            demo_user = db.query(User).filter(User.username == "demo").first()
            if not demo_user:
                # Import here to avoid circular import
                import bcrypt
                def get_password_hash(password: str) -> str:
                    return bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')

                demo_user = User(
                    username="demo",
                    email="demo@example.com",
                    full_name="Demo User",
                    hashed_password=get_password_hash("demo123"),
                    is_active=True,
                    is_superuser=True
                )
                db.add(demo_user)
                db.commit()
                db.refresh(demo_user)

                # Assign admin role to demo user
                admin_role = db.query(Role).filter(Role.name == "admin").first()
                if admin_role:
                    user_role = UserRole(user_id=demo_user.id, role_id=admin_role.id)
                    db.add(user_role)
                    db.commit()

                logger.info("Created demo user: demo/demo123")

            db.commit()

            # Migrate existing conversations to new collaborative schema
            migrate_conversations_to_collaborative(db)

        finally:
            db.close()

    except Exception as e:
        logger.error(f"Failed to initialize database: {e}")
        raise

def migrate_conversations_to_collaborative(db):
    """Migrate existing conversations to collaborative schema"""
    try:
        # Check if migration already done by checking if any ConversationParticipant exists
        existing_participants = db.query(ConversationParticipant).first()

        if existing_participants:
            logger.info("Conversations migration already completed")
            return

        # Get all existing conversations
        conversations = db.query(Conversation).all()
        migrated_count = 0

        for conv in conversations:
            # Skip if already migrated (has participants)
            if db.query(ConversationParticipant).filter(
                ConversationParticipant.conversation_id == conv.id
            ).first():
                continue

            # Create participant entry for the creator/owner
            participant = ConversationParticipant(
                conversation_id=conv.id,
                user_id=conv.created_by,
                permission_level="owner",
                joined_at=conv.created_at,
                last_active_at=conv.updated_at
            )
            db.add(participant)
            migrated_count += 1

        if migrated_count > 0:
            db.commit()
            logger.info(f"Migrated {migrated_count} conversations to collaborative schema")

    except Exception as e:
        logger.error(f"Error migrating conversations to collaborative schema: {e}")
        db.rollback()

# Initialize database on import
init_database()