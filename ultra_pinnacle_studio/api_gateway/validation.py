"""
Input validation and sanitization utilities for Ultra Pinnacle AI Studio
"""
import re
import html
from typing import Any, Dict, List, Optional, Union
from pydantic import BaseModel, field_validator, Field, ConfigDict
from fastapi import HTTPException
import bleach

# Content security
ALLOWED_HTML_TAGS = ['p', 'br', 'strong', 'em', 'u', 'h1', 'h2', 'h3', 'h4', 'h5', 'h6', 'ul', 'ol', 'li', 'blockquote', 'code', 'pre']
ALLOWED_HTML_ATTRS = {'*': ['class'], 'a': ['href', 'title'], 'img': ['src', 'alt', 'title']}

# File upload constraints
MAX_FILE_SIZE = 10 * 1024 * 1024  # 10MB
ALLOWED_EXTENSIONS = {'.txt', '.md', '.py', '.js', '.json', '.csv', '.xml', '.yaml', '.yml'}
ALLOWED_MIME_TYPES = {
    'text/plain', 'text/markdown', 'text/x-python', 'application/json',
    'text/csv', 'application/xml', 'application/x-yaml', 'text/yaml'
}

class SanitizedString(str):
    """A string that has been sanitized"""

    @classmethod
    def __get_validators__(cls):
        yield cls.validate

    @classmethod
    def validate(cls, v):
        if not isinstance(v, str):
            raise ValueError('String required')
        return cls(sanitize_text(v))

    def __new__(cls, value):
        return str.__new__(cls, sanitize_text(value))

class ValidatedPromptRequest(BaseModel):
    """Validated prompt enhancement request"""
    prompt: str = Field(..., min_length=1, max_length=10000)
    model: Optional[str] = Field(None, pattern=r'^[a-zA-Z0-9_-]+$')
    temperature: Optional[float] = Field(0.7, ge=0.0, le=2.0)
    max_tokens: Optional[int] = Field(512, ge=1, le=4096)

    @field_validator('prompt')
    def validate_prompt(cls, v):
        if not v or not v.strip():
            raise ValueError('Prompt cannot be empty')
        if len(v.strip()) < 3:
            raise ValueError('Prompt must be at least 3 characters long')
        return sanitize_text(v)

class ValidatedChatRequest(BaseModel):
    """Validated chat request"""
    message: str = Field("", min_length=0, max_length=5000)
    conversation_id: Optional[str] = Field(None, pattern=r'^[a-f0-9]{32}$')
    model: Optional[str] = Field(None, pattern=r'^[a-zA-Z0-9_-]+$')

    @field_validator('message')
    def validate_message(cls, v):
        return sanitize_text(v) if v else ""

class ValidatedCodeRequest(BaseModel):
    """Validated code analysis request"""
    code: str = Field(..., min_length=1, max_length=50000)
    language: str = Field(..., pattern=r'^[a-zA-Z0-9+#_-]+$')
    task: str = Field(..., pattern=r'^(analyze|generate|refactor|debug)$')

    @field_validator('code')
    def validate_code(cls, v):
        if not v or not v.strip():
            raise ValueError('Code cannot be empty')
        # Basic syntax check for Python
        if 'language' in cls.__dict__ and cls.__dict__['language'] == 'python':
            # Check for obviously dangerous patterns
            dangerous_patterns = [
                r'import\s+os\s*$',
                r'import\s+subprocess',
                r'import\s+sys',
                r'exec\s*\(',
                r'eval\s*\(',
                r'__import__\s*\('
            ]
            for pattern in dangerous_patterns:
                if re.search(pattern, v, re.MULTILINE):
                    raise ValueError('Potentially dangerous code detected')
        return v

class ValidatedSearchRequest(BaseModel):
    """Validated encyclopedia search request"""
    query: str = Field("", min_length=0, max_length=200)
    limit: Optional[int] = Field(10, ge=1, le=50)

    @field_validator('query')
    def validate_query(cls, v):
        if v and len(v.strip()) < 2:
            raise ValueError('Search query must be at least 2 characters long if provided')
        return sanitize_text(v) if v else ""

class ValidatedLoginRequest(BaseModel):
    """Validated login request"""
    username: str = Field(..., min_length=3, max_length=50, pattern=r'^[a-zA-Z0-9_-]+$')
    password: str = Field(..., min_length=6, max_length=128)

class ValidatedUserProfileUpdate(BaseModel):
    """Validated user profile update request"""
    email: Optional[str] = Field(None, pattern=r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$')
    full_name: Optional[str] = Field(None, min_length=1, max_length=100)

    @field_validator('full_name')
    def validate_full_name(cls, v):
        if v and not v.strip():
            raise ValueError('Full name cannot be empty if provided')
        return sanitize_text(v) if v else v

class ValidatedPasswordChange(BaseModel):
    """Validated password change request"""
    current_password: str = Field(..., min_length=1)
    new_password: str = Field(..., min_length=8, max_length=128)

    @field_validator('new_password')
    def validate_new_password(cls, v):
        if len(v) < 8:
            raise ValueError('New password must be at least 8 characters')
        if not re.search(r'[A-Z]', v):
            raise ValueError('New password must contain uppercase letter')
        if not re.search(r'[a-z]', v):
            raise ValueError('New password must contain lowercase letter')
        if not re.search(r'\d', v):
            raise ValueError('New password must contain number')
        return v

class ValidatedModelSwitch(BaseModel):
    """Validated model switching request"""
    model_config = ConfigDict(protected_namespaces=())

    model_name: str = Field(..., pattern=r'^[a-zA-Z0-9_-]+$')

class ValidatedConversationCreate(BaseModel):
    """Validated conversation creation request"""
    title: Optional[str] = Field(None, min_length=1, max_length=200)
    model: Optional[str] = Field(None, pattern=r'^[a-zA-Z0-9_-]+$')

    @field_validator('title')
    def validate_title(cls, v):
        return sanitize_text(v) if v else "New Conversation"

class ValidatedImageGenerationRequest(BaseModel):
    """Validated image generation request"""
    prompt: str = Field(..., min_length=1, max_length=1000)
    model: Optional[str] = Field(None, pattern=r'^[a-zA-Z0-9_-]+$')
    width: Optional[int] = Field(512, ge=64, le=2048)
    height: Optional[int] = Field(512, ge=64, le=2048)
    steps: Optional[int] = Field(20, ge=1, le=100)
    guidance_scale: Optional[float] = Field(7.5, ge=1.0, le=20.0)
    negative_prompt: Optional[str] = Field("", max_length=500)

    @field_validator('prompt', 'negative_prompt')
    def validate_prompts(cls, v):
        return sanitize_text(v) if v else ""

class ValidatedCodeCompletionRequest(BaseModel):
    """Validated code completion request"""
    code: str = Field(..., min_length=1, max_length=10000)
    language: str = Field(..., pattern=r'^[a-zA-Z0-9+#_-]+$')
    cursor_position: int = Field(0, ge=0)
    context: Optional[str] = Field("", max_length=5000)
    model: Optional[str] = Field(None, pattern=r'^[a-zA-Z0-9_-]+$')

    @field_validator('code', 'context')
    def validate_code_content(cls, v):
        return v  # Code content doesn't need HTML sanitization

class ValidatedPromptEngineeringRequest(BaseModel):
    """Validated prompt engineering request"""
    base_prompt: str = Field(..., min_length=1, max_length=2000)
    task_type: str = Field(..., pattern=r'^(creative|technical|business|educational|other)$')
    style: Optional[str] = Field("balanced", pattern=r'^(creative|formal|casual|technical|balanced)$')
    length: Optional[str] = Field("medium", pattern=r'^(short|medium|long|detailed)$')
    model: Optional[str] = Field(None, pattern=r'^[a-zA-Z0-9_-]+$')

    @field_validator('base_prompt')
    def validate_base_prompt(cls, v):
        return sanitize_text(v)

class ValidatedMultiModalRequest(BaseModel):
    """Validated multi-modal interaction request"""
    text_prompt: str = Field("", max_length=2000)
    image_data: Optional[str] = Field(None, pattern=r'^data:image/(png|jpeg|jpg|gif|webp);base64,')
    code_content: Optional[str] = Field("", max_length=10000)
    task: str = Field(..., pattern=r'^(analyze|generate|convert|describe|combine)$')
    model: Optional[str] = Field(None, pattern=r'^[a-zA-Z0-9_-]+$')

    @field_validator('text_prompt')
    def validate_text_prompt(cls, v):
        return sanitize_text(v) if v else ""

class ValidatedCodeRefactoringRequest(BaseModel):
    """Validated code refactoring request"""
    code: str = Field(..., min_length=1, max_length=50000)
    language: str = Field(..., pattern=r'^[a-zA-Z0-9+#_-]+$')
    refactoring_type: str = Field(..., pattern=r'^(optimize|simplify|modernize|security|performance)$')
    model: Optional[str] = Field(None, pattern=r'^[a-zA-Z0-9_-]+$')

class ValidatedConversionRequest(BaseModel):
    """Validated conversion request"""
    input_type: str = Field(..., pattern=r'^(text|image)$')
    output_type: str = Field(..., pattern=r'^(text|image)$')
    content: str = Field(..., min_length=1, max_length=10000)
    model: Optional[str] = Field(None, pattern=r'^[a-zA-Z0-9_-]+$')

class ValidatedCodeExplanationRequest(BaseModel):
    """Validated code explanation request"""
    code: str = Field(..., min_length=1, max_length=50000)
    language: str = Field(..., pattern=r'^[a-zA-Z0-9+#_-]+$')
    explanation_level: str = Field("intermediate", pattern=r'^(beginner|intermediate|advanced)$')
    include_examples: Optional[bool] = Field(True)
    model: Optional[str] = Field(None, pattern=r'^[a-zA-Z0-9_-]+$')

class ValidatedDebugRequest(BaseModel):
    """Validated debugging request"""
    code: str = Field(..., min_length=1, max_length=50000)
    language: str = Field(..., pattern=r'^[a-zA-Z0-9+#_-]+$')
    error_message: Optional[str] = Field("", max_length=2000)
    stack_trace: Optional[str] = Field("", max_length=10000)
    model: Optional[str] = Field(None, pattern=r'^[a-zA-Z0-9_-]+$')

    @field_validator('error_message', 'stack_trace')
    def validate_debug_info(cls, v):
        return v  # Debug info doesn't need HTML sanitization

def sanitize_text(text: str) -> str:
    """Sanitize text input to prevent XSS and injection attacks"""
    if not text:
        return text

    # HTML escape
    text = html.escape(text)

    # Remove potentially dangerous characters
    text = re.sub(r'[<>\"\'`]', '', text)

    # Normalize whitespace
    text = ' '.join(text.split())

    return text.strip()

def sanitize_html(html_content: str) -> str:
    """Sanitize HTML content"""
    return bleach.clean(html_content, tags=ALLOWED_HTML_TAGS, attributes=ALLOWED_HTML_ATTRS, strip=True)

def validate_file_upload(file, filename: str, content_type: str) -> None:
    """Validate file upload"""
    # Check file size
    file_content = file.read()
    file.seek(0)  # Reset file pointer

    if len(file_content) > MAX_FILE_SIZE:
        raise HTTPException(status_code=413, detail=f"File too large. Maximum size is {MAX_FILE_SIZE} bytes")

    # Check file extension
    import os
    _, ext = os.path.splitext(filename.lower())
    if ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(status_code=400, detail=f"File type not allowed. Allowed extensions: {', '.join(ALLOWED_EXTENSIONS)}")

    # Check MIME type
    if content_type not in ALLOWED_MIME_TYPES:
        raise HTTPException(status_code=400, detail=f"Content type not allowed: {content_type}")

    # Check for malicious content
    if b'<?php' in file_content.lower() or b'<script' in file_content.lower():
        raise HTTPException(status_code=400, detail="Potentially malicious file content detected")

def validate_topic_name(topic: str) -> str:
    """Validate encyclopedia topic name"""
    if not topic or not topic.strip():
        raise HTTPException(status_code=400, detail="Topic name cannot be empty")

    # Allow only alphanumeric, hyphens, and underscores
    if not re.match(r'^[a-zA-Z0-9_-]+$', topic):
        raise HTTPException(status_code=400, detail="Invalid topic name format")

    return topic.strip()

def validate_conversation_id(conversation_id: Optional[str]) -> Optional[str]:
    """Validate conversation ID format"""
    if conversation_id and not re.match(r'^[a-f0-9]{32}$', conversation_id):
        raise HTTPException(status_code=400, detail="Invalid conversation ID format")
    return conversation_id

def validate_model_name(model: Optional[str]) -> Optional[str]:
    """Validate model name"""
    if model and not re.match(r'^[a-zA-Z0-9_-]+$', model):
        raise HTTPException(status_code=400, detail="Invalid model name format")
    return model

def rate_limit_check(client_ip: str, max_requests: int = 60, window_seconds: int = 60) -> bool:
    """Check if client has exceeded rate limit"""
    # This is a simple in-memory check
    # In production, use Redis or similar
    current_time = __import__('time').time()
    window_start = current_time - window_seconds

    # This would need to be implemented with persistent storage
    # For now, return True (allow)
    return True

def log_security_event(event_type: str, details: Dict[str, Any], ip_address: Optional[str] = None):
    """Log security-related events"""
    from .logging_config import logger
    logger.warning(f"Security event: {event_type} - {details} - IP: {ip_address}")

# Input sanitization middleware
class InputSanitizationMiddleware:
    """Middleware to sanitize all input data"""

    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope["type"] == "http":
            # Sanitize query parameters
            query_string = scope.get("query_string", b"").decode()
            if query_string:
                # Basic sanitization of query params
                sanitized_query = sanitize_text(query_string)
                scope["query_string"] = sanitized_query.encode()

        await self.app(scope, receive, send)