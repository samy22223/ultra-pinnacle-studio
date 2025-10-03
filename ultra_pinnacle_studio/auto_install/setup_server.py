#!/usr/bin/env python3
"""
Ultra Pinnacle Studio - Auto-Install Web Server
Serves the setup interface and handles deployment requests
"""

import os
import json
import asyncio
import secrets
import subprocess
from pathlib import Path
from typing import Dict, Optional
from datetime import datetime

from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.responses import HTMLResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

class DeploymentRequest(BaseModel):
    mode: str  # quick, custom, enterprise
    domain: Optional[str] = None
    admin_email: Optional[str] = None
    platform: str = "auto"

class DeploymentStatus(BaseModel):
    status: str  # running, completed, failed
    progress: int  # 0-100
    message: str
    log: list[str]
    deployment_id: str

# Global deployment status tracking
deployment_status: Dict[str, DeploymentStatus] = {}

app = FastAPI(title="Ultra Pinnacle Studio - Auto Install")

@app.get("/", response_class=HTMLResponse)
async def setup_page():
    """Serve the main setup interface"""
    setup_file = Path(__file__).parent / "setup_interface.html"
    if setup_file.exists():
        return setup_file.read_text()
    return "<h1>Setup interface not found</h1>"

@app.get("/api/deployment/status/{deployment_id}")
async def get_deployment_status(deployment_id: str):
    """Get deployment status"""
    if deployment_id not in deployment_status:
        raise HTTPException(status_code=404, detail="Deployment not found")

    return deployment_status[deployment_id]

@app.post("/api/deployment/start")
async def start_deployment(request: DeploymentRequest, background_tasks: BackgroundTasks):
    """Start deployment process"""
    deployment_id = secrets.token_hex(16)

    # Initialize deployment status
    deployment_status[deployment_id] = DeploymentStatus(
        status="running",
        progress=0,
        message="Initializing deployment...",
        log=[],
        deployment_id=deployment_id
    )

    # Start deployment in background
    background_tasks.add_task(run_deployment, deployment_id, request)

    return {"deployment_id": deployment_id}

@app.get("/api/deployment/platforms")
async def get_supported_platforms():
    """Get list of supported platforms"""
    return {
        "platforms": [
            {"id": "windows", "name": "Windows", "icon": "🪟"},
            {"id": "macos", "name": "macOS", "icon": "🍎"},
            {"id": "linux", "name": "Linux", "icon": "🐧"},
            {"id": "mobile", "name": "Mobile", "icon": "📱"},
            {"id": "docker", "name": "Docker", "icon": "🐳"}
        ]
    }

async def run_deployment(deployment_id: str, request: DeploymentRequest):
    """Run the deployment process in background"""
    try:
        # Update status
        update_deployment_status(deployment_id, 10, "Starting deployment engine...")

        # Import and run deployment engine
        from .deployment_engine import DeploymentEngine, DeploymentConfig, DeploymentMode, PlatformType

        # Map string modes to enums
        mode_map = {
            "quick": DeploymentMode.QUICK,
            "custom": DeploymentMode.CUSTOM,
            "enterprise": DeploymentMode.ENTERPRISE
        }

        platform_map = {
            "windows": PlatformType.WINDOWS,
            "macos": PlatformType.MACOS,
            "linux": PlatformType.LINUX,
            "mobile": PlatformType.MOBILE,
            "docker": PlatformType.DOCKER,
            "auto": PlatformType.LINUX  # Default fallback
        }

        mode = mode_map.get(request.mode, DeploymentMode.QUICK)
        platform = platform_map.get(request.platform, PlatformType.LINUX)

        config = DeploymentConfig(
            mode=mode,
            platform=platform,
            domain_name=request.domain or "",
            admin_email=request.admin_email or ""
        )

        # Create deployment engine
        engine = DeploymentEngine(config)

        # Override log method to update our status
        original_log = engine.log
        def status_log(message, level="info"):
            original_log(message, level)
            update_deployment_log(deployment_id, message)

        engine.log = status_log

        # Run deployment steps with progress updates
        update_deployment_status(deployment_id, 20, "Running pre-deployment checks...")
        await engine.pre_deployment_checks()

        update_deployment_status(deployment_id, 30, "Setting up directory structure...")
        await engine.setup_directories()

        update_deployment_status(deployment_id, 40, "Installing dependencies...")
        await engine.install_dependencies()

        update_deployment_status(deployment_id, 50, "Generating configuration...")
        await engine.generate_configuration()

        update_deployment_status(deployment_id, 60, "Setting up database...")
        await engine.setup_database()

        update_deployment_status(deployment_id, 70, "Configuring services...")
        await engine.configure_services()

        update_deployment_status(deployment_id, 80, "Setting up security...")
        await engine.setup_security()

        update_deployment_status(deployment_id, 90, "Configuring domain and networking...")
        await engine.setup_domain_networking()

        update_deployment_status(deployment_id, 100, "Finalizing setup...")
        await engine.final_setup()

        # Mark as completed
        deployment_status[deployment_id].status = "completed"
        deployment_status[deployment_id].message = "Deployment completed successfully!"

    except Exception as e:
        # Mark as failed
        deployment_status[deployment_id].status = "failed"
        deployment_status[deployment_id].message = f"Deployment failed: {str(e)}"
        update_deployment_log(deployment_id, f"ERROR: {str(e)}")

def update_deployment_status(deployment_id: str, progress: int, message: str):
    """Update deployment progress"""
    if deployment_id in deployment_status:
        deployment_status[deployment_id].progress = progress
        deployment_status[deployment_id].message = message

def update_deployment_log(deployment_id: str, message: str):
    """Add message to deployment log"""
    if deployment_id in deployment_status:
        deployment_status[deployment_id].log.append(f"[{datetime.now().strftime('%H:%M:%S')}] {message}")

        # Keep only last 50 log entries
        if len(deployment_status[deployment_id].log) > 50:
            deployment_status[deployment_id].log = deployment_status[deployment_id].log[-50:]

@app.get("/api/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy", "service": "auto-install"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8001)