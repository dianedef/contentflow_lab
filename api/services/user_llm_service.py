"""Runtime resolver for user-scoped LLM credentials (OpenRouter V1)."""

from __future__ import annotations

import json

from openai import OpenAI

from api.services.user_key_store import user_key_store


class UserLLMService:
    """Resolve user-managed OpenRouter key and build OpenAI-compatible client."""

    async def get_openrouter_key(self, user_id: str) -> str:
        key = await user_key_store.get_secret(user_id, provider="openrouter")
        if not key:
            raise RuntimeError(
                "OpenRouter credential missing. Configure it via /api/settings/integrations/openrouter."
            )
        status = await user_key_store.get_credential_status(user_id, provider="openrouter")
        if status and status.get("validation_status") == "invalid":
            raise RuntimeError(
                "OpenRouter credential is marked invalid. Re-validate or update the key."
            )
        return key

    async def get_openrouter_client(self, user_id: str) -> OpenAI:
        key = await self.get_openrouter_key(user_id)
        return OpenAI(
            api_key=key,
            base_url="https://openrouter.ai/api/v1",
        )

    async def generate_json(
        self,
        user_id: str,
        *,
        system_prompt: str,
        user_prompt: str,
        model: str = "openai/gpt-4o-mini",
    ) -> dict:
        client = await self.get_openrouter_client(user_id)
        response = client.chat.completions.create(
            model=model,
            temperature=0.2,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            response_format={"type": "json_object"},
        )
        content = response.choices[0].message.content if response.choices else None
        if not content:
            raise RuntimeError("OpenRouter returned an empty response.")
        try:
            return json.loads(content)
        except json.JSONDecodeError as exc:
            raise RuntimeError("OpenRouter did not return valid JSON.") from exc


user_llm_service = UserLLMService()
