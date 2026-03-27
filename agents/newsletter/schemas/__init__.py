"""Newsletter schemas - Pydantic models for validation."""

from agents.newsletter.schemas.newsletter_schemas import (
    NewsletterConfig,
    NewsletterSection,
    NewsletterDraft,
    EmailRecipient,
    SendResult,
)

__all__ = [
    "NewsletterConfig",
    "NewsletterSection",
    "NewsletterDraft",
    "EmailRecipient",
    "SendResult",
]
