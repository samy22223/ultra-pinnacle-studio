from fastapi import FastAPI, HTTPException, Depends, File, UploadFile, Form, Query
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
import os
import json
import uuid
import subprocess
import re
from pathlib import Path
from datetime import datetime, timedelta, timezone
from contextlib import asynccontextmanager
import aiofiles
from .logging_config import logger
from .auth import create_access_token, get_current_user, get_current_active_user, authenticate_user
from .database import User, Conversation, Message
from .database import get_db
from sqlalchemy.orm import Session
from .models_safe import ModelManager
from .workers import WorkerManager
from .middleware import setup_middleware
from .metrics import router as metrics_router
from .validation import (
    ValidatedPromptRequest, ValidatedChatRequest, ValidatedCodeRequest,
    ValidatedSearchRequest, ValidatedLoginRequest, validate_file_upload,
    ValidatedUserProfileUpdate, ValidatedPasswordChange, ValidatedModelSwitch,
    ValidatedConversationCreate
)

from .config import config

# Initialize managers
logger.debug("Initializing ModelManager and WorkerManager")
model_manager = ModelManager(config)
worker_manager = WorkerManager(config)
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

# Response Models
class LoginResponse(BaseModel):
    access_token: str = Field(..., description="JWT access token")
    token_type: str = Field("bearer", description="Token type")

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
    yield
    # Shutdown
    logger.info("Shutting down Ultra Pinnacle AI Studio")

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

# Setup middleware
setup_middleware(app, config)

# Include metrics router
app.include_router(metrics_router)

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
async def login(request: ValidatedLoginRequest, db: Session = Depends(get_db)):
    """
    Authenticate user and return access token.

    - **username**: User's username (3-50 characters, alphanumeric + hyphens/underscores)
    - **password**: User's password (6-128 characters)
    """
    user = authenticate_user(db, request.username, request.password)
    if not user:
        raise HTTPException(status_code=401, detail="Invalid credentials")

    access_token = create_access_token(data={"sub": user.username})
    logger.info(f"User {user.username} logged in")
    return {"access_token": access_token, "token_type": "bearer"}

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
        user_id=current_user.id,
        title=request.title,
        model=config["models"]["default_model"]
    )

    db.add(conversation)
    db.commit()

    logger.info(f"User {current_user.username} created conversation {conversation_id}")
    return {"conversation_id": conversation_id, "title": conversation.title}

@app.get(
    "/conversations",
    response_model=List[Dict[str, Any]],
    summary="List Conversations",
    description="Get a list of the current user's conversations",
    tags=["conversations"]
)
async def list_conversations(
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """List user's conversations"""
    conversations = db.query(Conversation).filter(
        Conversation.user_id == current_user.id
    ).order_by(Conversation.updated_at.desc()).all()

    result = []
    for conv in conversations:
        # Get message count
        message_count = db.query(Message).filter(
            Message.conversation_id == conv.id
        ).count()

        result.append({
            "id": conv.id,
            "title": conv.title,
            "model": conv.model,
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
    conversation = db.query(Conversation).filter(
        Conversation.id == conversation_id,
        Conversation.user_id == current_user.id
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
            "created_at": msg.created_at.isoformat()
        })

    return {
        "id": conversation.id,
        "title": conversation.title,
        "model": conversation.model,
        "messages": message_list,
        "created_at": conversation.created_at.isoformat(),
        "updated_at": conversation.updated_at.isoformat()
    }

@app.delete(
    "/conversations/{conversation_id}",
    response_model=Dict[str, str],
    summary="Delete Conversation",
    description="Delete a conversation and all its messages",
    tags=["conversations"]
)
async def delete_conversation(
    conversation_id: str,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Delete a conversation"""
    conversation = db.query(Conversation).filter(
        Conversation.id == conversation_id,
        Conversation.user_id == current_user.id
    ).first()

    if not conversation:
        raise HTTPException(status_code=404, detail="Conversation not found")

    # Delete will cascade to messages due to relationship
    db.delete(conversation)
    db.commit()

    logger.info(f"User {current_user.username} deleted conversation {conversation_id}")
    return {"message": "Conversation deleted successfully"}

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
                user_id=current_user.id,
                title=f"Chat {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M')}",
                model=model_name
            )
            db.add(conversation)
            logger.debug(f"Created new conversation {conversation_id} for user {current_user.username}")
        else:
            conversation = db.query(Conversation).filter(
                Conversation.id == conversation_id,
                Conversation.user_id == current_user.id
            ).first()
            if not conversation:
                raise HTTPException(status_code=404, detail="Conversation not found")

        # Save user message
        user_message = Message(
            conversation_id=conversation_id,
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
