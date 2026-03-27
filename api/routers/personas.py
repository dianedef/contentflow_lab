"""Authenticated personas endpoints."""

from fastapi import APIRouter, Depends, HTTPException, Query

from api.dependencies.auth import CurrentUser, require_current_user
from api.models.user_data import (
    PersonaCreateRequest,
    PersonaResponse,
    PersonaUpdateRequest,
)
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
        request.model_dump(exclude_unset=True),
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
        request.model_dump(exclude_unset=True),
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
