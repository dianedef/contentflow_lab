from datetime import datetime

from api.models.psychology import PersonaRefinementRequest
from api.models.user_data import PersonaCreateRequest, PersonaResponse


def test_persona_create_accepts_camel_and_snake_case_equally():
    camel = PersonaCreateRequest.model_validate(
        {
            "projectId": "project-1",
            "name": "Founder Persona",
            "painPoints": ["No pipeline"],
            "contentPreferences": {"formats": ["article"]},
        }
    )
    snake = PersonaCreateRequest.model_validate(
        {
            "project_id": "project-1",
            "name": "Founder Persona",
            "pain_points": ["No pipeline"],
            "content_preferences": {"formats": ["article"]},
        }
    )

    assert camel.to_canonical_dict() == snake.to_canonical_dict()
    assert camel.to_canonical_dict()["pain_points"] == ["No pipeline"]


def test_persona_response_serializes_to_legacy_camel_case():
    payload = {
        "id": "persona-1",
        "userId": "user-1",
        "project_id": "project-1",
        "name": "Founder Persona",
        "pain_points": ["No pipeline"],
        "goals": ["Steady demand"],
        "content_preferences": {"formats": ["article"]},
        "confidence": 77,
        "created_at": datetime.now(),
        "updated_at": datetime.now(),
    }
    response = PersonaResponse(**payload)
    data = response.model_dump(by_alias=True)

    assert "projectId" in data
    assert "painPoints" in data
    assert "contentPreferences" in data
    assert data["painPoints"] == ["No pipeline"]


def test_persona_refinement_request_accepts_legacy_persona_alias():
    request = PersonaRefinementRequest.model_validate(
        {
            "persona_id": "persona-1",
            "persona": {
                "name": "Founder Persona",
                "pain_points": ["No pipeline"],
            },
        }
    )

    assert request.current_persona.to_canonical_dict()["pain_points"] == ["No pipeline"]
