from fastapi import FastAPI, HTTPException, Depends, File, UploadFile, Form
from fastapi.responses import JSONResponse
from pydantic import BaseModel, validator
from typing import Optional, List, Dict, Any
import os
import json
import uuid
from pathlib import Path
from datetime import datetime, timedelta
from contextlib import asynccontextmanager
import aiofiles
from .logging_config import logger
from .auth import create_access_token, get_current_user, get_current_active_user, User, authenticate_user, fake_users_db
from .models import ModelManager
from .workers import WorkerManager

# Load configuration
with open("config.json", "r") as f:
    config = json.load(f)

app = FastAPI(
    title=config["app"]["name"],
    version=config["app"]["version"],
    description="Offline AI Studio with integrated encyclopedia and development tools"
)

# Initialize managers
model_manager = ModelManager(config)
worker_manager = WorkerManager(config)

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

app = FastAPI(lifespan=lifespan)

# Authentication endpoints
@app.post("/auth/login")
async def login(request: LoginRequest):
    """Login endpoint"""
    user = authenticate_user(fake_users_db, request.username, request.password)
    if not user:
        raise HTTPException(status_code=401, detail="Invalid credentials")

    access_token = create_access_token(data={"sub": user.username})
    logger.info(f"User {user.username} logged in")
    return {"access_token": access_token, "token_type": "bearer"}

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
    """Health check endpoint"""
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "models_loaded": len(model_manager.list_models()),
        "active_tasks": len([t for t in worker_manager.tasks.values() if t["status"] == "running"])
    }

@app.get("/models")
async def list_models():
    """List available models"""
    return {"models": model_manager.list_models()}

@app.get("/workers")
async def list_workers():
    """List available workers"""
    return {"workers": worker_manager.list_workers()}

# AI endpoints
@app.post("/enhance_prompt")
async def enhance_prompt(request: PromptRequest, current_user: User = Depends(get_current_active_user)):
    """Enhance a prompt using AI"""
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

@app.post("/chat")
async def chat(request: ChatRequest, current_user: User = Depends(get_current_active_user)):
    """Chat with AI model"""
    try:
        model_name = request.model or config["models"]["default_model"]
        response = model_manager.generate_text(
            model_name,
            request.message,
            max_tokens=256
        )
        logger.info(f"Chat response for user {current_user.username}")
        return {
            "response": response,
            "conversation_id": request.conversation_id or str(uuid.uuid4())
        }
    except Exception as e:
        logger.error(f"Error in chat: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/code/{task}")
async def code_task(task: str, request: CodeRequest, current_user: User = Depends(get_current_active_user)):
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
        topics = [f.replace('.md', '') for f in os.listdir('encyclopedia') if f.endswith('.md')]
        return {"topics": topics}
    except Exception as e:
        logger.error(f"Error listing encyclopedia: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/encyclopedia/{topic}")
async def get_topic(topic: str):
    """Get content of a specific encyclopedia topic"""
    try:
        file_path = f"encyclopedia/{topic}.md"
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
async def search_encyclopedia(request: SearchRequest):
    """Search encyclopedia for a query"""
    try:
        query = request.query.lower()
        results = []
        for file in os.listdir('encyclopedia'):
            if file.endswith('.md'):
                topic = file.replace('.md', '')
                with open(f"encyclopedia/{file}", 'r') as f:
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
