"""Authenticated personas endpoints."""

from __future__ import annotations

import uuid
import asyncio

from fastapi import APIRouter, Depends, HTTPException, Query

from api.dependencies.auth import CurrentUser, require_current_user
from api.models.persona_draft import (
    ExistingCreatorProfile,
    PersonaDraftJobResponse,
    PersonaDraftRequest,
    PersonaDraftResult,
)
from api.models.user_data import (
    PersonaCreateRequest,
    PersonaResponse,
    PersonaUpdateRequest,
)
from api.services.job_store import job_store
from api.services.repo_understanding_service import repo_understanding_service
from api.services.user_llm_service import user_llm_service
from api.services.user_data_store import user_data_store

router = APIRouter(prefix="/api/personas", tags=["Personas"])


@router.get("", response_model=list[PersonaResponse], summary="List personas")
async def list_personas(
    projectId: str | None = Query(default=None),
    current_user: CurrentUser = Depends(require_current_user),
) -> list[PersonaResponse]:
    personas = await user_data_store.list_personas(current_user.user_id, projectId)
    return [PersonaResponse(**persona) for persona in personas]


@router.post("", response_model=PersonaResponse, summary="Create persona")
async def create_persona(
    request: PersonaCreateRequest,
    current_user: CurrentUser = Depends(require_current_user),
) -> PersonaResponse:
    persona = await user_data_store.create_persona(
        current_user.user_id,
        request.to_canonical_dict(),
    )
    return PersonaResponse(**persona)


@router.put("/{persona_id}", response_model=PersonaResponse, summary="Update persona")
async def update_persona(
    persona_id: str,
    request: PersonaUpdateRequest,
    current_user: CurrentUser = Depends(require_current_user),
) -> PersonaResponse:
    persona = await user_data_store.update_persona(
        current_user.user_id,
        persona_id,
        request.to_canonical_dict(),
    )
    if not persona:
        raise HTTPException(status_code=404, detail="Persona not found")
    return PersonaResponse(**persona)


@router.delete("/{persona_id}", summary="Delete persona")
async def delete_persona(
    persona_id: str,
    current_user: CurrentUser = Depends(require_current_user),
) -> dict:
    deleted = await user_data_store.delete_persona(
        current_user.user_id,
        persona_id,
    )
    if not deleted:
        raise HTTPException(status_code=404, detail="Persona not found")
    return {"success": True, "id": persona_id}


async def _run_persona_draft_job(
    *,
    job_id: str,
    user_id: str,
    request: PersonaDraftRequest,
) -> None:
    try:
        await job_store.update(
            job_id,
            status="running",
            progress=20,
            message="Collecting repository understanding.",
        )
        understanding = await repo_understanding_service.understand(user_id, request)
        await job_store.update(
            job_id,
            progress=65,
            message="Synthesizing persona draft.",
        )

        if request.mode != "blank_form":
            await user_llm_service.get_openrouter_key(user_id)

        creator_profile = request.existing_creator_profile
        if creator_profile is None and request.project_id:
            stored = await user_data_store.get_creator_profile(user_id, request.project_id)
            if stored:
                creator_profile = ExistingCreatorProfile(
                    display_name=stored.get("displayName"),
                    voice=stored.get("voice"),
                    positioning=stored.get("positioning"),
                    values=stored.get("values") or [],
                )

        draft = repo_understanding_service.build_persona_draft(
            understanding,
            creator_profile=creator_profile,
        )
        if request.project_id:
            draft["project_id"] = request.project_id

        result = PersonaDraftResult(
            persona_draft=draft,
            repo_understanding=understanding,
            evidence=understanding.evidence,
            confidence=int(draft.get("confidence") or 50),
        )
        await job_store.update(
            job_id,
            status="completed",
            progress=100,
            message="Persona draft completed.",
            result=result.model_dump(mode="json"),
            error=None,
        )
    except Exception as exc:
        await job_store.update(
            job_id,
            status="failed",
            progress=100,
            message="Persona draft failed.",
            error=str(exc),
        )


@router.post(
    "/draft",
    response_model=PersonaDraftJobResponse,
    summary="Generate a non-persisted persona draft",
)
async def create_persona_draft(
    request: PersonaDraftRequest,
    current_user: CurrentUser = Depends(require_current_user),
) -> PersonaDraftJobResponse:
    if request.mode != "blank_form":
        try:
            await user_llm_service.get_openrouter_key(current_user.user_id)
        except RuntimeError as exc:
            raise HTTPException(status_code=409, detail=str(exc)) from exc

    job_id = str(uuid.uuid4())
    await job_store.upsert(
        job_id=job_id,
        job_type="personas.draft",
        status="pending",
        progress=0,
        message="Queued persona draft job.",
        user_id=current_user.user_id,
        result=None,
        error=None,
    )
    asyncio.create_task(
        _run_persona_draft_job(
            job_id=job_id,
            user_id=current_user.user_id,
            request=request,
        )
    )
    return PersonaDraftJobResponse(
        job_id=job_id,
        status="pending",
        progress=0,
        message="Queued persona draft job.",
        user_id=current_user.user_id,
    )


@router.get(
    "/draft-jobs/{job_id}",
    response_model=PersonaDraftJobResponse,
    summary="Get persona draft job status",
)
async def get_persona_draft_job(
    job_id: str,
    current_user: CurrentUser = Depends(require_current_user),
) -> PersonaDraftJobResponse:
    job = await job_store.get(job_id)
    if not job or job.get("job_type") != "personas.draft":
        raise HTTPException(status_code=404, detail="Draft job not found")
    if job.get("user_id") != current_user.user_id:
        raise HTTPException(status_code=404, detail="Draft job not found")
    return PersonaDraftJobResponse(**job)
