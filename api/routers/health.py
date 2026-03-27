"""Health check and monitoring endpoints"""

from fastapi import APIRouter
from datetime import datetime
import sys
import os
from pathlib import Path

router = APIRouter(tags=["Health & Monitoring"])


@router.get(
    "/",
    summary="API info",
    description="Basic API information and status"
)
async def root():
    """Root endpoint with API info"""
    return {
        "service": "SEO Robots API",
        "version": "1.0.0",
        "status": "operational",
        "docs": "/docs",
        "redoc": "/redoc",
        "timestamp": datetime.utcnow().isoformat()
    }


@router.get(
    "/health",
    summary="Health check",
    description="Detailed health status of all components"
)
async def health_check():
    """Health check endpoint for monitoring"""
    
    # Check Python agents availability
    agents_status = {}
    
    # NOTE: We DON'T import agents here to avoid slow startup
    # Instead, we just check that the modules exist and can be imported
    import importlib
    
    agents_to_check = [
        ("mesh_architect", "agents.seo.topical_mesh_architect"),
        ("research_analyst", "agents.seo.research_analyst"),
        ("content_strategist", "agents.seo.content_strategist"),
        ("internal_linking", "agents.seo.internal_linking_specialist"),
    ]

    import os
    for name, module_path in agents_to_check:
        module_file = module_path.replace('.', '/') + '.py'
        if not os.path.exists(module_file):
            agents_status[name] = "not_found"
            continue
        try:
            import importlib
            importlib.import_module(module_path)
            agents_status[name] = "available"
        except ImportError as e:
            agents_status[name] = f"import_error: {str(e)[:120]}"
        except Exception as e:
            agents_status[name] = f"error: {str(e)[:120]}"
    
    # Overall status
    all_available = all(
        status in ["available", "operational"] 
        for status in agents_status.values()
    )
    
    return {
        "status": "healthy" if all_available else "degraded",
        "timestamp": datetime.utcnow().isoformat(),
        "python_version": sys.version,
        "agents": agents_status,
        "components": {
            "api": "operational",
            "database": "not_configured",  # TODO: Add when DB ready
            "cache": "not_configured"
        }
    }


@router.get(
    "/version",
    summary="API version",
    description="Get API version and build info"
)
async def version():
    """Version information"""
    return {
        "version": "1.0.0",
        "build_date": "2026-01-14",
        "python_version": sys.version.split()[0],
        "fastapi_version": "0.128.0"
    }
