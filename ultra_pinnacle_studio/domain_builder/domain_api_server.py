#!/usr/bin/env python3
"""
Ultra Pinnacle Studio - Domain Builder API Server
REST API for domain generation, registration, and management
"""

import os
import json
import asyncio
from pathlib import Path
from typing import Dict, List, Optional
from datetime import datetime

from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.responses import HTMLResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, EmailStr

from .domain_generator import DomainGenerator, DomainConfig, GeneratedDomain

class DomainGenerationRequest(BaseModel):
    count: int = 10
    domain_type: str = "mixed"  # mixed, brand, international
    brand_name: str = "pinnacle"
    include_numbers: bool = True
    include_hyphens: bool = True

class DomainRegistrationRequest(BaseModel):
    domain_name: str
    user_email: EmailStr

class DomainResponse(BaseModel):
    domain_name: str
    tld: str
    full_domain: str
    status: str
    availability_score: float
    is_international: bool = False

app = FastAPI(title="Ultra Pinnacle Studio - Domain Builder API")

# Global domain generator instance
domain_generator = DomainGenerator()

@app.get("/", response_class=HTMLResponse)
async def domain_builder_page():
    """Serve the domain builder interface"""
    ui_file = Path(__file__).parent / "domain_builder_ui.html"
    if ui_file.exists():
        return ui_file.read_text()
    return "<h1>Domain Builder interface not found</h1>"

@app.post("/api/domains/generate")
async def generate_domains(request: DomainGenerationRequest):
    """Generate domain options"""
    try:
        # Create domain configuration
        config = DomainConfig(
            name_length=10,
            use_numbers=request.include_numbers,
            use_hyphens=request.include_hyphens,
            include_brand=True,
            brand_name=request.brand_name,
            international_tlds=True
        )

        # Update generator config
        domain_generator.config = config

        # Generate domains
        domains = await domain_generator.generate_domains(request.count)

        # Convert to response format
        response_domains = []
        for domain in domains:
            response_domains.append(DomainResponse(
                domain_name=domain.domain_name,
                tld=domain.tld,
                full_domain=domain.full_domain,
                status=domain.status.value,
                availability_score=domain.availability_score,
                is_international=domain.is_international
            ))

        return {
            "domains": response_domains,
            "generated_at": datetime.now().isoformat(),
            "total_options": len(response_domains),
            "request_config": request.dict()
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/domains/register")
async def register_domain(request: DomainRegistrationRequest, background_tasks: BackgroundTasks):
    """Register a selected domain"""
    try:
        # Find the domain in our generated options or create it
        domain_parts = request.domain_name.split('.')
        if len(domain_parts) >= 2:
            name = domain_parts[0]
            tld = '.' + '.'.join(domain_parts[1:])
        else:
            name = request.domain_name
            tld = '.com'

        # Create domain object
        from .domain_generator import GeneratedDomain, DomainStatus
        from datetime import timedelta

        domain = GeneratedDomain(
            domain_name=name,
            tld=tld,
            full_domain=request.domain_name,
            status=DomainStatus.AVAILABLE,
            registration_date=datetime.now(),
            expiry_date=datetime.now() + timedelta(days=365)
        )

        # Register domain in background
        background_tasks.add_task(
            domain_generator.register_domain,
            domain,
            request.user_email
        )

        return {
            "success": True,
            "domain": request.domain_name,
            "message": "Domain registration initiated",
            "estimated_completion": (datetime.now() + timedelta(minutes=2)).isoformat()
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/domains/registered")
async def get_registered_domains():
    """Get list of registered domains"""
    try:
        domains_file = Path(__file__).parent.parent / 'config' / 'registered_domains.json'

        if not domains_file.exists():
            return {"domains": [], "total": 0}

        with open(domains_file, 'r') as f:
            domains = json.load(f)

        return {
            "domains": domains,
            "total": len(domains)
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/domains/tlds")
async def get_available_tlds():
    """Get available TLD categories"""
    return {
        "free_tlds": [
            '.tk', '.ml', '.ga', '.cf', '.gq', '.xyz', '.top', '.club',
            '.online', '.store', '.tech', '.space', '.website', '.fun'
        ],
        "premium_tlds": [
            '.com', '.net', '.org', '.io', '.ai', '.app', '.dev', '.co',
            '.info', '.biz', '.pro', '.tech', '.online', '.store', '.shop'
        ],
        "international_tlds": [
            '.fr', '.de', '.es', '.it', '.nl', '.be', '.at', '.ch',
            '.se', '.no', '.dk', '.fi', '.pl', '.cz', '.hu', '.ro',
            '.pt', '.gr', '.ru', '.ua', '.br', '.mx', '.ar', '.co',
            '.in', '.jp', '.kr', '.cn', '.au', '.nz', '.za', '.eg'
        ]
    }

@app.get("/api/domains/subdomain/{main_domain}")
async def generate_subdomain(main_domain: str, prefix: str = None):
    """Generate a subdomain for a main domain"""
    try:
        subdomain = await domain_generator.generate_subdomain(main_domain, prefix)

        return {
            "subdomain": subdomain,
            "main_domain": main_domain,
            "generated_at": datetime.now().isoformat()
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/domains/dns/{domain_name}")
async def setup_dns_records(domain_name: str, target_ip: str = "127.0.0.1"):
    """Set up DNS records for a domain"""
    try:
        dns_records = await domain_generator.setup_dns_records(domain_name, target_ip)

        return {
            "domain": domain_name,
            "target_ip": target_ip,
            "dns_records": dns_records,
            "configured_at": datetime.now().isoformat()
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "service": "domain-builder",
        "timestamp": datetime.now().isoformat()
    }

@app.get("/api/stats")
async def get_domain_stats():
    """Get domain generation statistics"""
    try:
        domains_file = Path(__file__).parent.parent / 'config' / 'registered_domains.json'

        total_registered = 0
        if domains_file.exists():
            with open(domains_file, 'r') as f:
                domains = json.load(f)
                total_registered = len(domains)

        return {
            "total_registered_domains": total_registered,
            "available_tlds": {
                "free": len(domain_generator.free_tlds),
                "premium": len(domain_generator.premium_tlds),
                "international": len(domain_generator.international_tlds)
            },
            "generation_capabilities": {
                "brand_enhanced": True,
                "international": True,
                "custom_length": True,
                "availability_scoring": True
            }
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8002)