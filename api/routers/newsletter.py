"""Newsletter generation and management endpoints."""

from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks, Query
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from datetime import datetime

from api.dependencies.auth import require_current_user

router = APIRouter(
    prefix="/api/newsletter",
    tags=["Newsletter"],
    dependencies=[Depends(require_current_user)],
)


class NewsletterRequest(BaseModel):
    """Request to generate a newsletter."""

    name: str = Field(..., description="Newsletter name/title")
    topics: List[str] = Field(..., description="Topics to cover")
    target_audience: str = Field(..., description="Target audience description")
    tone: str = Field(default="professional", description="Writing tone")
    competitor_emails: List[str] = Field(
        default_factory=list,
        description="Competitor newsletter emails to analyze"
    )
    include_email_insights: bool = Field(
        default=True,
        description="Read Gmail for insights"
    )
    max_sections: int = Field(default=5, description="Max content sections")


class NewsletterResponse(BaseModel):
    """Response with generated newsletter."""

    success: bool
    newsletter_id: str
    subject_line: str
    preview_text: str
    word_count: int
    read_time_minutes: int
    content: str
    sections: List[Dict[str, Any]]
    sources: Dict[str, List[str]]
    created_at: datetime


class NewsletterStatus(BaseModel):
    """Status of newsletter generation job."""

    job_id: str
    status: str  # pending, running, completed, failed
    progress: int  # 0-100
    message: Optional[str] = None
    result: Optional[NewsletterResponse] = None


# In-memory job storage (replace with Redis/DB in production)
_jobs: Dict[str, NewsletterStatus] = {}


@router.post(
    "/generate",
    response_model=NewsletterResponse,
    summary="Generate newsletter",
    description="Generate a newsletter using AI agents with Gmail and web research"
)
async def generate_newsletter(request: NewsletterRequest):
    """
    Generate a newsletter synchronously.

    This endpoint:
    1. Reads recent emails via Composio Gmail integration
    2. Analyzes competitor newsletters
    3. Researches trending topics via Exa AI
    4. Generates newsletter content

    Requires:
    - Composio Gmail authentication: `composio add gmail`
    - EXA_API_KEY environment variable
    """
    try:
        from agents.newsletter.newsletter_crew import NewsletterCrew
        from agents.newsletter.schemas.newsletter_schemas import (
            NewsletterConfig,
            NewsletterTone,
        )

        # Create config
        config = NewsletterConfig(
            name=request.name,
            topics=request.topics,
            target_audience=request.target_audience,
            tone=NewsletterTone(request.tone),
            competitor_emails=request.competitor_emails,
            include_email_insights=request.include_email_insights,
            max_sections=request.max_sections,
        )

        # Generate newsletter
        crew = NewsletterCrew(use_gmail=request.include_email_insights)
        result = crew.generate_newsletter(config)

        draft = result.get("draft", {})

        return NewsletterResponse(
            success=True,
            newsletter_id=f"nl_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
            subject_line=draft.get("subject_line", "Newsletter"),
            preview_text=draft.get("preview_text", ""),
            word_count=draft.get("word_count", 0),
            read_time_minutes=draft.get("estimated_read_time", 1),
            content=draft.get("plain_text", ""),
            sections=draft.get("sections", []),
            sources={
                "emails": draft.get("email_sources", []),
                "web": draft.get("web_sources", []),
            },
            created_at=datetime.now(),
        )

    except ImportError as e:
        raise HTTPException(
            status_code=500,
            detail=f"Newsletter agents not available: {str(e)}. "
                   f"Install with: pip install composio-crewai"
        )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Newsletter generation failed: {str(e)}"
        )


@router.post(
    "/generate/async",
    response_model=NewsletterStatus,
    summary="Generate newsletter (async)",
    description="Start newsletter generation as background job"
)
async def generate_newsletter_async(
    request: NewsletterRequest,
    background_tasks: BackgroundTasks
):
    """
    Start newsletter generation as a background job.

    Returns immediately with a job ID. Poll /newsletter/status/{job_id}
    to check progress and retrieve results.
    """
    import uuid

    job_id = str(uuid.uuid4())[:8]

    _jobs[job_id] = NewsletterStatus(
        job_id=job_id,
        status="pending",
        progress=0,
        message="Job queued"
    )

    async def run_generation():
        try:
            _jobs[job_id].status = "running"
            _jobs[job_id].progress = 10
            _jobs[job_id].message = "Initializing agents..."

            from agents.newsletter.newsletter_crew import NewsletterCrew
            from agents.newsletter.schemas.newsletter_schemas import (
                NewsletterConfig,
                NewsletterTone,
            )

            _jobs[job_id].progress = 20
            _jobs[job_id].message = "Reading emails..."

            config = NewsletterConfig(
                name=request.name,
                topics=request.topics,
                target_audience=request.target_audience,
                tone=NewsletterTone(request.tone),
                competitor_emails=request.competitor_emails,
            )

            _jobs[job_id].progress = 40
            _jobs[job_id].message = "Researching content..."

            crew = NewsletterCrew()
            result = crew.generate_newsletter(config)

            _jobs[job_id].progress = 90
            _jobs[job_id].message = "Finalizing..."

            draft = result.get("draft", {})
            _jobs[job_id].result = NewsletterResponse(
                success=True,
                newsletter_id=f"nl_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
                subject_line=draft.get("subject_line", "Newsletter"),
                preview_text=draft.get("preview_text", ""),
                word_count=draft.get("word_count", 0),
                read_time_minutes=draft.get("estimated_read_time", 1),
                content=draft.get("plain_text", ""),
                sections=draft.get("sections", []),
                sources={
                    "emails": draft.get("email_sources", []),
                    "web": draft.get("web_sources", []),
                },
                created_at=datetime.now(),
            )

            _jobs[job_id].status = "completed"
            _jobs[job_id].progress = 100
            _jobs[job_id].message = "Newsletter generated successfully"

        except Exception as e:
            _jobs[job_id].status = "failed"
            _jobs[job_id].message = str(e)

    background_tasks.add_task(run_generation)

    return _jobs[job_id]


@router.get(
    "/status/{job_id}",
    response_model=NewsletterStatus,
    summary="Get job status",
    description="Check status of async newsletter generation"
)
async def get_job_status(job_id: str):
    """Get the status of a newsletter generation job."""
    if job_id not in _jobs:
        raise HTTPException(status_code=404, detail=f"Job {job_id} not found")

    return _jobs[job_id]


@router.get(
    "/config/check",
    summary="Check configuration",
    description="Verify newsletter dependencies are configured"
)
async def check_config():
    """Check if all newsletter dependencies are configured."""
    from agents.newsletter.config.newsletter_config import validate_config

    checks = validate_config()

    return {
        "ready": all(checks.values()),
        "checks": checks,
        "instructions": {
            "composio": "Run: composio add gmail",
            "exa": "Set EXA_API_KEY in environment",
            "sendgrid": "Set SENDGRID_API_KEY for sending",
        }
    }


class SenderInfo(BaseModel):
    """Information about an email sender found in inbox."""

    from_email: str = Field(..., description="Sender email address")
    from_name: str = Field(default="", description="Sender display name")
    email_count: int = Field(default=1, description="Number of emails from this sender")
    is_newsletter: bool = Field(default=False, description="Detected as newsletter")
    latest_subject: str = Field(default="", description="Most recent email subject")
    latest_date: Optional[str] = Field(default=None, description="Most recent email date")


class SenderListResponse(BaseModel):
    """Response with list of senders from inbox scan."""

    senders: List[SenderInfo]
    total_scanned: int = Field(default=0, description="Total emails scanned")
    scan_days: int = Field(default=30, description="Days back scanned")


@router.get(
    "/senders",
    response_model=SenderListResponse,
    summary="Scan inbox senders",
    description="Scan Gmail inbox and return grouped sender list with newsletter detection"
)
async def get_inbox_senders(
    days_back: int = Query(default=30, ge=1, le=90, description="Days back to scan"),
    max_results: int = Query(default=200, ge=10, le=500, description="Max emails to scan"),
    folder: str = Query(default="INBOX", description="Folder to scan"),
    newsletters_only: bool = Query(default=True, description="Only return newsletter senders"),
):
    """
    Scan Gmail inbox via IMAP and return a list of unique senders.

    Groups by sender email, counts occurrences, detects newsletters.
    Uses headers_only=True for speed (no body download).
    """
    try:
        from agents.newsletter.tools.imap_tools import IMAPNewsletterReader

        reader = IMAPNewsletterReader()
        senders, total_scanned = reader.fetch_senders_from_inbox(
            days_back=days_back,
            max_results=max_results,
            folder=folder,
            newsletters_only=newsletters_only,
        )

        return SenderListResponse(
            senders=[SenderInfo(**s) for s in senders],
            total_scanned=total_scanned,
            scan_days=days_back,
        )

    except ImportError as e:
        raise HTTPException(
            status_code=500,
            detail=f"IMAP tools not available: {str(e)}. Install with: pip install imap-tools"
        )
    except ValueError as e:
        raise HTTPException(
            status_code=400,
            detail=f"Configuration error: {str(e)}"
        )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Inbox scan failed: {str(e)}"
        )
