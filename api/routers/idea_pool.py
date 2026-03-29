"""Idea Pool API Router — CRUD for content ideas from all sources."""

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from typing import Optional

from api.dependencies.auth import CurrentUser, require_current_user
from api.models.idea_pool import (
    CreateIdeaRequest,
    UpdateIdeaRequest,
    BulkIngestRequest,
    IdeaListResponse,
    IdeaRecord,
)

router = APIRouter(prefix="/api/ideas", tags=["Idea Pool"])


def _get_svc():
    from status import get_status_service
    return get_status_service()


@router.post("", response_model=dict)
async def create_idea(
    request: CreateIdeaRequest,
    current_user: CurrentUser = Depends(require_current_user),
):
    """Create a single idea in the pool."""
    svc = _get_svc()
    idea = svc.create_idea(
        source=request.source,
        title=request.title,
        raw_data=request.raw_data,
        seo_signals=request.seo_signals,
        trending_signals=request.trending_signals,
        tags=request.tags,
        project_id=request.project_id,
        user_id=current_user.user_id,
    )
    return idea


@router.get("", response_model=IdeaListResponse)
async def list_ideas(
    source: Optional[str] = Query(None, description="Filter by source"),
    status: Optional[str] = Query(None, description="Filter by status: raw, enriched, used, dismissed"),
    min_score: Optional[float] = Query(None, description="Minimum priority score"),
    project_id: Optional[str] = Query(None, description="Filter by project"),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    current_user: CurrentUser = Depends(require_current_user),
):
    """List ideas with optional filters, sorted by priority score desc."""
    svc = _get_svc()
    items, total = svc.list_ideas(
        source=source,
        status=status,
        min_score=min_score,
        project_id=project_id,
        user_id=current_user.user_id,
        limit=limit,
        offset=offset,
    )
    return IdeaListResponse(
        items=[IdeaRecord(**i) for i in items],
        total=total,
    )


@router.get("/{idea_id}", response_model=dict)
async def get_idea(
    idea_id: str,
    current_user: CurrentUser = Depends(require_current_user),
):
    """Get a single idea by ID."""
    svc = _get_svc()
    try:
        idea = svc.get_idea(idea_id)
    except Exception:
        raise HTTPException(status_code=404, detail="Idea not found")
    if idea.get("user_id") and idea["user_id"] != current_user.user_id:
        raise HTTPException(status_code=404, detail="Idea not found")
    return idea


@router.patch("/{idea_id}", response_model=dict)
async def update_idea(
    idea_id: str,
    request: UpdateIdeaRequest,
    current_user: CurrentUser = Depends(require_current_user),
):
    """Update an idea (enrich, dismiss, change score, etc.)."""
    svc = _get_svc()
    # Verify ownership
    try:
        idea = svc.get_idea(idea_id)
    except Exception:
        raise HTTPException(status_code=404, detail="Idea not found")
    if idea.get("user_id") and idea["user_id"] != current_user.user_id:
        raise HTTPException(status_code=404, detail="Idea not found")

    updates = request.model_dump(exclude_unset=True)
    if not updates:
        raise HTTPException(status_code=400, detail="No fields to update")
    try:
        return svc.update_idea(idea_id, **updates)
    except Exception:
        raise HTTPException(status_code=404, detail="Idea not found")


@router.delete("/{idea_id}")
async def delete_idea(
    idea_id: str,
    current_user: CurrentUser = Depends(require_current_user),
):
    """Delete an idea from the pool."""
    svc = _get_svc()
    try:
        idea = svc.get_idea(idea_id)
    except Exception:
        raise HTTPException(status_code=404, detail="Idea not found")
    if idea.get("user_id") and idea["user_id"] != current_user.user_id:
        raise HTTPException(status_code=404, detail="Idea not found")
    svc.delete_idea(idea_id)
    return {"deleted": True}


@router.post("/ingest", response_model=dict)
async def bulk_ingest(
    request: BulkIngestRequest,
    current_user: CurrentUser = Depends(require_current_user),
):
    """Bulk ingest ideas from a source."""
    svc = _get_svc()
    count = svc.bulk_create_ideas(
        source=request.source,
        items=request.items,
        project_id=request.project_id,
        user_id=current_user.user_id,
    )
    return {"ingested": count}


# ─── Source triggers (manual or scheduled) ───────────


class IngestNewslettersRequest(BaseModel):
    days_back: int = 7
    folder: str = "Newsletters"
    max_results: int = 20
    project_id: Optional[str] = None


class IngestSeoRequest(BaseModel):
    seed_keywords: list[str]
    max_keywords: int = 50
    location: str = "us"
    language: str = "en"
    project_id: Optional[str] = None


class EnrichIdeasRequest(BaseModel):
    batch_size: int = 50
    location: str = "us"
    language: str = "en"
    project_id: Optional[str] = None


class IngestCompetitorsRequest(BaseModel):
    target_domain: str
    competitor_domains: list[str]
    max_gaps: int = 50
    location: str = "us"
    language: str = "en"
    project_id: Optional[str] = None


class IngestSocialRequest(BaseModel):
    topics: list[str]
    days_back: int = 30
    max_ideas: int = 50
    project_id: Optional[str] = None


class TrackSerpRequest(BaseModel):
    location: str = "us"
    language: str = "en"
    project_id: Optional[str] = None


@router.post("/ingest/newsletters", response_model=dict)
async def ingest_newsletters(
    request: IngestNewslettersRequest,
    current_user: CurrentUser = Depends(require_current_user),
):
    """Pull newsletters from IMAP inbox, extract ideas with LLM, and archive."""
    from agents.sources.ingest import ingest_newsletter_inbox

    persona_context = ""
    if request.project_id:
        try:
            from api.services.user_data_store import user_data_store
            from agents.sources.newsletter_extractor import format_persona_context

            personas = await user_data_store.list_personas(current_user.user_id, request.project_id)
            creator = await user_data_store.get_creator_profile(current_user.user_id, request.project_id)
            persona_context = format_persona_context(personas, creator)
        except Exception:
            pass

    count = ingest_newsletter_inbox(
        days_back=request.days_back,
        folder=request.folder,
        max_results=request.max_results,
        project_id=request.project_id,
        persona_context=persona_context,
        user_id=current_user.user_id,
    )
    return {"source": "newsletter_inbox", "ingested": count}


@router.post("/ingest/seo-keywords", response_model=dict)
async def ingest_seo(
    request: IngestSeoRequest,
    current_user: CurrentUser = Depends(require_current_user),
):
    """Discover SEO keyword opportunities via DataForSEO and create ideas."""
    from agents.sources.ingest import ingest_seo_keywords

    count = ingest_seo_keywords(
        seed_keywords=request.seed_keywords,
        max_keywords=request.max_keywords,
        location=request.location,
        language=request.language,
        project_id=request.project_id,
        user_id=current_user.user_id,
    )
    return {"source": "seo_keywords", "ingested": count}


@router.post("/enrich", response_model=dict)
async def enrich(
    request: EnrichIdeasRequest,
    current_user: CurrentUser = Depends(require_current_user),
):
    """Enrich raw ideas with DataForSEO keyword metrics (volume, difficulty, CPC)."""
    from agents.sources.ingest import enrich_ideas

    count = enrich_ideas(
        batch_size=request.batch_size,
        location=request.location,
        language=request.language,
        project_id=request.project_id,
        user_id=current_user.user_id,
    )
    return {"enriched": count}


@router.post("/ingest/competitors", response_model=dict)
async def ingest_competitors(
    request: IngestCompetitorsRequest,
    current_user: CurrentUser = Depends(require_current_user),
):
    """Analyze competitor domains and ingest content gaps as ideas."""
    from agents.sources.ingest import ingest_competitor_watch

    count = ingest_competitor_watch(
        target_domain=request.target_domain,
        competitor_domains=request.competitor_domains,
        max_gaps=request.max_gaps,
        location=request.location,
        language=request.language,
        project_id=request.project_id,
        user_id=current_user.user_id,
    )
    return {"source": "competitor_watch", "ingested": count}


@router.post("/ingest/social", response_model=dict, summary="Social listening: Reddit, X, HN, YouTube")
async def ingest_social(
    request: IngestSocialRequest,
    current_user: CurrentUser = Depends(require_current_user),
):
    """Scan Reddit, X, Hacker News, and YouTube for trending topics and inject ideas."""
    import asyncio
    from agents.sources.social_listener import ingest_social_listening

    result = await asyncio.to_thread(
        ingest_social_listening,
        topics=request.topics,
        days_back=request.days_back,
        max_ideas=request.max_ideas,
        project_id=request.project_id,
        user_id=current_user.user_id,
    )
    return {"source": "social_listening", "ingested": result["count"], "sources": result["sources"]}


@router.post("/track-serp", response_model=dict)
async def track_serp(
    request: TrackSerpRequest,
    current_user: CurrentUser = Depends(require_current_user),
):
    """Track SERP positions for published content with SEO keywords."""
    from agents.sources.ingest import track_serp_positions

    count = track_serp_positions(
        location=request.location,
        language=request.language,
        project_id=request.project_id,
        user_id=current_user.user_id,
    )
    return {"tracked": count}
