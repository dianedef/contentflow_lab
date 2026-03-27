"""
Newsletter Schemas - Pydantic models for newsletter generation.
"""

from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field, EmailStr
from datetime import datetime
from enum import Enum


class NewsletterTone(str, Enum):
    """Newsletter writing tone."""
    PROFESSIONAL = "professional"
    CASUAL = "casual"
    FRIENDLY = "friendly"
    EDUCATIONAL = "educational"
    PROMOTIONAL = "promotional"


class EmailMessage(BaseModel):
    """
    Email message retrieved from IMAP.

    Used by IMAP tools to represent fetched newsletter emails.
    """

    uid: str = Field(..., description="Email unique identifier for archiving")
    subject: str = Field(default="", description="Email subject line")
    from_email: str = Field(default="", description="Sender email address")
    from_name: str = Field(default="", description="Sender display name")
    date: datetime = Field(default_factory=datetime.now, description="Email date")
    html: str = Field(default="", description="HTML content")
    text: str = Field(default="", description="Plain text content")
    is_newsletter: bool = Field(
        default=False,
        description="Whether email was detected as a newsletter"
    )


class NewsletterSection(BaseModel):
    """A section within a newsletter."""

    title: str = Field(..., description="Section heading")
    content: str = Field(..., description="Section content in markdown")
    order: int = Field(default=0, description="Display order")
    section_type: str = Field(
        default="article",
        description="Type: article, highlight, tip, cta, intro, outro"
    )
    source_url: Optional[str] = Field(None, description="Source reference URL")


class NewsletterConfig(BaseModel):
    """Configuration for newsletter generation."""

    name: str = Field(..., description="Newsletter name/title")
    topics: List[str] = Field(..., description="Topics to cover")
    tone: NewsletterTone = Field(default=NewsletterTone.PROFESSIONAL)
    target_audience: str = Field(..., description="Target audience description")

    # Content sources
    include_email_insights: bool = Field(
        default=True,
        description="Read and incorporate insights from Gmail"
    )
    competitor_emails: List[str] = Field(
        default_factory=list,
        description="Competitor newsletter email addresses to monitor"
    )

    # Structure
    max_sections: int = Field(default=5, description="Maximum content sections")
    include_intro: bool = Field(default=True)
    include_outro: bool = Field(default=True)
    include_cta: bool = Field(default=True)
    cta_text: Optional[str] = Field(None, description="Call-to-action text")
    cta_url: Optional[str] = Field(None, description="Call-to-action URL")

    # Branding
    header_image_url: Optional[str] = None
    footer_text: Optional[str] = None
    social_links: Dict[str, str] = Field(default_factory=dict)


class NewsletterDraft(BaseModel):
    """A complete newsletter draft ready for review/sending."""

    config: NewsletterConfig
    subject_line: str = Field(..., description="Email subject line")
    preview_text: str = Field(..., description="Email preview text (preheader)")

    sections: List[NewsletterSection] = Field(default_factory=list)

    # Rendered content
    html_content: Optional[str] = Field(None, description="Rendered HTML")
    plain_text: Optional[str] = Field(None, description="Plain text version")

    # Metadata
    created_at: datetime = Field(default_factory=datetime.now)
    word_count: int = Field(default=0)
    estimated_read_time: int = Field(default=0, description="Minutes")

    # Sources used
    email_sources: List[str] = Field(
        default_factory=list,
        description="Email IDs used as sources"
    )
    web_sources: List[str] = Field(
        default_factory=list,
        description="URLs used as sources"
    )

    def calculate_read_time(self) -> int:
        """Calculate estimated read time based on word count."""
        # Average reading speed: 200-250 words per minute
        return max(1, self.word_count // 200)


class EmailRecipient(BaseModel):
    """Newsletter recipient."""

    email: EmailStr
    name: Optional[str] = None
    segments: List[str] = Field(default_factory=list)
    unsubscribed: bool = False


class SendResult(BaseModel):
    """Result of sending a newsletter."""

    success: bool
    newsletter_id: str
    recipients_count: int
    sent_at: datetime = Field(default_factory=datetime.now)

    # Delivery stats
    delivered: int = 0
    bounced: int = 0
    errors: List[str] = Field(default_factory=list)

    # If created as draft
    gmail_draft_id: Optional[str] = None
    sendgrid_batch_id: Optional[str] = None
