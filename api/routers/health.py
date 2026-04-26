"""Health check and monitoring endpoints"""

from fastapi import APIRouter
from datetime import datetime
import sys
import os
from pathlib import Path
import subprocess

router = APIRouter(tags=["Health & Monitoring"])

def _normalize_git_sha(value: str | None) -> str | None:
    if value is None:
        return None
    normalized = value.strip()
    if not normalized:
        return None
    return normalized[:7]


def _detect_git_sha() -> str | None:
    sha = (
        os.getenv("BACKEND_GIT_SHA")
        or os.getenv("RENDER_GIT_COMMIT")
        or os.getenv("GIT_SHA")
    )
    if sha:
        return _normalize_git_sha(sha)

    try:
        repo_root = Path(__file__).resolve().parents[2]
        result = subprocess.run(
            ["git", "rev-parse", "--short", "HEAD"],
            cwd=str(repo_root),
            capture_output=True,
            text=True,
            timeout=1,
            check=False,
        )
        if result.returncode != 0:
            return None
        return _normalize_git_sha(result.stdout)
    except Exception:
        return None


_GIT_SHA = _detect_git_sha()


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
        "git_sha": _GIT_SHA,
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
        "git_sha": _GIT_SHA,
        "agents": agents_status,
        "components": {
            "api": "operational",
            "database": await _check_db(),
            "cache": "not_configured"
        }
    }


async def _check_db() -> str:
    """Check database connectivity."""
    try:
        from api.services.user_data_store import user_data_store
        if not user_data_store.db_client:
            return "not_configured"
        await user_data_store.db_client.execute("SELECT 1")
        return "operational"
    except Exception:
        return "unreachable"


@router.get(
    "/version",
    summary="API version",
    description="Get API version and build info"
)
async def version():
    """Version information"""
    return {
        "version": "1.0.0",
        "git_sha": _GIT_SHA,
        "build_date": "2026-01-14",
        "python_version": sys.version.split()[0],
        "fastapi_version": "0.128.0"
    }
