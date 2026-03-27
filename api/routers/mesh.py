"""Topical Mesh API endpoints

IMPORTANT: Uses lazy imports for heavy agent dependencies.
TopicalMeshArchitect is only loaded when endpoints are called,
not at module import time. This allows FastAPI to start quickly.
"""

from fastapi import APIRouter, Depends, Request, WebSocket, WebSocketDisconnect, BackgroundTasks
from datetime import datetime
import asyncio
import time
from typing import Any, TYPE_CHECKING

from api.models.mesh import (
    AnalyzeRequest,
    AnalyzeResponse,
    BuildMeshRequest,
    BuildMeshResponse,
    ImproveMeshRequest,
    ImproveMeshResponse,
    CompareRequest,
    CompareResponse,
    PageInfo,
    MeshIssue,
    Recommendation,
    ImprovementPhase,
)
from api.dependencies import get_mesh_architect

# Type hint only - not loaded at runtime
if TYPE_CHECKING:
    from agents.seo.topical_mesh_architect import TopicalMeshArchitect

router = APIRouter(
    prefix="/api/mesh",
    tags=["Topical Mesh"],
    responses={404: {"description": "Not found"}},
)


def convert_to_response(result: dict, start_time: float) -> dict:
    """Convert raw agent result to API response format"""
    processing_time = time.time() - start_time

    # Flatten the nested structure to match frontend expectations
    existing_mesh = result.get("existing_mesh", {})

    # Build flattened response
    response = {
        "authority_score": result.get("authority_score", 0),
        "grade": result.get("authority_grade", "F"),
        "total_pages": existing_mesh.get("total_pages", 0),
        "total_links": existing_mesh.get("total_links", 0),
        "mesh_density": existing_mesh.get("mesh_density", 0.0),
        "pillar": existing_mesh.get("pillar_page"),
        "clusters": existing_mesh.get("cluster_pages", []),
        "orphans": existing_mesh.get("orphan_pages", []),
        "issues": result.get("issues", {}).get("orphans", []) + [
            {
                "severity": "high" if issue.get("severity") == "HIGH" else "medium" if issue.get("severity") == "MEDIUM" else "low",
                "category": "orphan" if "orphan" in str(issue).lower() else "weak_pillar" if "pillar" in str(issue).lower() else "low_density",
                "description": issue.get("description", str(issue)),
                "affected_pages": issue.get("affected_pages", []),
                "impact": issue.get("impact", "Unknown impact")
            } for issue in result.get("issues", {}).values() if isinstance(issue, dict)
        ],
        "recommendations": [
            {
                "priority": rec.get("priority", "medium").lower(),
                "action": rec.get("action", rec.get("title", "Unknown action")),
                "description": rec.get("description", rec.get("details", "")),
                "estimated_effort": rec.get("effort", "Unknown effort"),
                "estimated_impact": int(rec.get("impact", "0").split()[0]) if rec.get("impact") and rec.get("impact").split()[0].isdigit() else 0,
                "affected_pages": rec.get("affected_pages", [])
            } for rec in result.get("recommendations", [])
        ],
        "analysis_timestamp": datetime.utcnow().isoformat(),
        "processing_time_seconds": round(processing_time, 2)
    }

    return response


@router.post(
    "/analyze",
    response_model=AnalyzeResponse,
    summary="Analyze existing website mesh",
    description="""
    Analyze an existing website's topical mesh structure.
    
    **What it does:**
    - Clones GitHub repository
    - Extracts pages and links
    - Calculates topical authority (0-100)
    - Identifies issues (orphans, weak pillar, low density)
    - Generates recommendations
    
    **Returns:**
    - Authority score with grade (A-F)
    - Pillar and cluster pages
    - Detected issues with severity
    - Prioritized recommendations
    - Optional visualization (PNG/Mermaid)
    
    **Example:**
    ```json
    {
      "repo_url": "https://github.com/user/site",
      "include_visualization": true
    }
    ```
    """
)
async def analyze_mesh(
    request: AnalyzeRequest,
    raw_request: Request,
    architect: "TopicalMeshArchitect" = Depends(get_mesh_architect)
) -> Any:
    """Analyze existing website topical mesh"""
    start_time = time.time()

    # GitHub token forwarded by the Next.js proxy from Clerk OAuth
    github_token = raw_request.headers.get("X-GitHub-Token")

    result = architect.analyze_existing_website(
        repo_url=str(request.repo_url),
        local_repo_path=request.local_repo_path,
        github_token=github_token,
    )

    # Convert to response format
    response = convert_to_response(result, start_time)

    return response


@router.post(
    "/build",
    response_model=BuildMeshResponse,
    summary="Build new topical mesh",
    description="""
    Build a new topical mesh from scratch using French SEO "Cocon Sémantique" methodology.
    
    **What it does:**
    - Creates pillar page (page mère)
    - Generates cluster pages (pages filles)
    - Calculates PageRank-based authority
    - Optimizes internal linking
    - Generates visualization
    
    **Returns:**
    - Complete mesh structure
    - Authority score (target: 85+/100)
    - Linking strategy (20+ recommendations)
    - Visualizations (Text/Mermaid/PNG/JSON)
    
    **Example:**
    ```json
    {
      "main_topic": "Digital Marketing",
      "subtopics": ["SEO", "Social Media", "Email"],
      "target_pages": 10
    }
    ```
    """
)
async def build_mesh(
    request: BuildMeshRequest,
    architect: "TopicalMeshArchitect" = Depends(get_mesh_architect)
) -> Any:
    """Build new topical mesh from scratch"""
    start_time = time.time()
    
    # Call Python agent
    result = architect.design_mesh_from_scratch(
        main_topic=request.main_topic,
        business_goals=request.business_goals,
        target_pages=request.target_pages
    )
    
    # Add metadata
    result["created_at"] = datetime.utcnow().isoformat()
    result["processing_time_seconds"] = round(time.time() - start_time, 2)
    
    return result


@router.post(
    "/improve",
    response_model=ImproveMeshResponse,
    summary="Generate improvement plan",
    description="""
    Generate a phased improvement plan for existing mesh.
    
    **What it does:**
    - Analyzes current mesh state
    - Identifies quick wins (Phase 1)
    - Plans content improvements (Phase 2)
    - Suggests optimization (Phase 3)
    - Projects final authority score
    
    **Returns:**
    - Current vs target authority
    - 3-phase improvement plan
    - Effort/impact estimates
    - Success probability
    
    **Example:**
    ```json
    {
      "repo_url": "https://github.com/user/site",
      "new_topics": ["AI Tools", "Analytics"],
      "target_authority": 85
    }
    ```
    """
)
async def improve_mesh(
    request: ImproveMeshRequest,
    architect: "TopicalMeshArchitect" = Depends(get_mesh_architect)
) -> Any:
    """Generate improvement plan for existing mesh"""
    start_time = time.time()
    
    # First analyze current state
    current = architect.analyze_existing_website(str(request.repo_url))
    
    # Generate improvement plan
    result = architect.improve_existing_mesh(
        current_analysis=current,
        new_topics=request.new_topics,
        competitor_topics=request.competitor_topics
    )
    
    result["processing_time_seconds"] = round(time.time() - start_time, 2)
    
    return result


@router.post(
    "/compare",
    response_model=CompareResponse,
    summary="Compare current vs ideal",
    description="""
    Compare current mesh with ideal structure.
    
    **What it does:**
    - Analyzes current mesh
    - Builds ideal mesh
    - Calculates authority gap
    - Identifies missing topics
    - Recommends specific actions
    
    **Returns:**
    - Side-by-side comparison
    - Content gaps
    - Underperforming pages
    - Actionable recommendations
    """
)
async def compare_mesh(
    request: CompareRequest,
    architect: "TopicalMeshArchitect" = Depends(get_mesh_architect)
) -> Any:
    """Compare current mesh with ideal structure"""
    start_time = time.time()
    
    result = architect.compare_with_ideal(
        repo_url=str(request.repo_url),
        ideal_main_topic=request.ideal_main_topic,
        ideal_subtopics=request.ideal_subtopics
    )
    
    result["processing_time_seconds"] = round(time.time() - start_time, 2)
    
    return result


@router.websocket("/analyze-stream")
async def analyze_mesh_stream(websocket: WebSocket):
    """
    Real-time streaming analysis with progress updates
    
    **WebSocket Protocol:**
    
    Client sends:
    ```json
    {
      "repo_url": "https://github.com/user/repo",
      "include_visualization": true
    }
    ```
    
    Server streams:
    ```json
    {"stage": "cloning", "message": "...", "percent": 20}
    {"stage": "analyzing", "message": "...", "percent": 40}
    {"stage": "calculating", "message": "...", "percent": 60}
    {"stage": "recommending", "message": "...", "percent": 80}
    {"stage": "complete", "result": {...}, "percent": 100}
    ```
    """
    await websocket.accept()
    
    try:
        # Receive request
        data = await websocket.receive_json()
        repo_url = data.get("repo_url")
        
        architect = get_mesh_architect()
        
        # Stage 1: Cloning
        await websocket.send_json({
            "stage": "cloning",
            "message": "🔄 Cloning repository...",
            "percent": 20
        })
        await asyncio.sleep(0.5)
        
        # Stage 2: Analyzing
        await websocket.send_json({
            "stage": "analyzing",
            "message": "📊 Analyzing content structure...",
            "percent": 40
        })
        await asyncio.sleep(0.5)
        
        # Stage 3: Calculating
        await websocket.send_json({
            "stage": "calculating",
            "message": "🧮 Calculating topical authority...",
            "percent": 60
        })
        
        # Run analysis
        result = architect.analyze_existing_website(repo_url)
        
        # Stage 4: Recommending
        await websocket.send_json({
            "stage": "recommending",
            "message": "💡 Generating recommendations...",
            "percent": 80
        })
        await asyncio.sleep(0.3)
        
        # Stage 5: Complete
        await websocket.send_json({
            "stage": "complete",
            "message": f"✅ Analysis complete! Authority: {result.get('authority_score', 0)}/100",
            "percent": 100,
            "result": result
        })
        
    except WebSocketDisconnect:
        pass
    except Exception as e:
        await websocket.send_json({
            "stage": "error",
            "message": f"❌ Error: {str(e)}",
            "error": str(e)
        })
    finally:
        await websocket.close()


# Background task example for report generation
def generate_pdf_report(analysis: dict, user_email: str):
    """Generate PDF report in background (placeholder)"""
    # TODO: Implement PDF generation
    pass


@router.post(
    "/analyze-with-report",
    response_model=AnalyzeResponse,
    summary="Analyze with PDF report",
    description="Analyze mesh and generate PDF report asynchronously"
)
async def analyze_with_report(
    request: AnalyzeRequest,
    background_tasks: BackgroundTasks,
    architect: "TopicalMeshArchitect" = Depends(get_mesh_architect)
) -> Any:
    """Analyze mesh and generate PDF report in background"""
    start_time = time.time()
    
    result = architect.analyze_existing_website(str(request.repo_url))
    response = convert_to_response(result, start_time)
    
    # Generate report asynchronously
    # background_tasks.add_task(generate_pdf_report, result, "user@example.com")
    
    return response
