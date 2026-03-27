"""
Newsletter Agent - CrewAI agent for newsletter curation and writing.

Capabilities:
- Read emails via IMAP (free) or Composio Gmail (managed)
- Research trending topics via Exa AI
- Write newsletter content
- Create Gmail drafts for review
"""

from typing import List, Optional
from crewai import Agent
import os

from agents.newsletter.tools.content_tools import (
    research_newsletter_topics,
    find_related_articles,
)
from agents.newsletter.config.newsletter_config import (
    NEWSLETTER_DEFAULTS,
    EMAIL_BACKEND,
)

# Conditional import for memory tools (graceful degradation)
try:
    from agents.newsletter.tools.memory_tools import (
        recall_project_context,
        recall_past_newsletters,
        recall_brand_voice,
    )
    MEMORY_AVAILABLE = True
except ImportError:
    MEMORY_AVAILABLE = False

# Conditional import based on email backend configuration
if EMAIL_BACKEND == "imap":
    from agents.newsletter.tools.imap_tools import (
        read_recent_newsletters,
        read_competitor_newsletters,
        archive_processed_newsletter,
    )
    # IMAP doesn't need additional Gmail tools
    def get_gmail_tools():
        return []
else:
    from agents.newsletter.tools.gmail_tools import (
        get_gmail_tools,
        read_recent_newsletters,
        read_competitor_newsletters,
    )
    # Composio doesn't have archive tool
    archive_processed_newsletter = None


class NewsletterAgent:
    """
    Newsletter curation and writing agent.

    Uses Composio for Gmail access and Exa AI for content research.
    """

    def __init__(
        self,
        llm_model: Optional[str] = None,
        use_gmail: bool = True
    ):
        """
        Initialize Newsletter Agent.

        Args:
            llm_model: LLM model to use (default from config)
            use_gmail: Whether to enable Gmail tools via Composio
        """
        self.llm_model = llm_model or NEWSLETTER_DEFAULTS["llm_model"]
        self.use_gmail = use_gmail
        self.agent = self._create_agent()

    def _get_tools(self) -> List:
        """Assemble tools for the agent."""
        tools = [
            research_newsletter_topics,
            find_related_articles,
        ]

        if self.use_gmail:
            # Add Composio Gmail tools
            gmail_tools = get_gmail_tools()
            tools.extend(gmail_tools)

            # Add custom wrapped tools
            tools.extend([
                read_recent_newsletters,
                read_competitor_newsletters,
            ])

        return tools

    def _create_agent(self) -> Agent:
        """Create the CrewAI agent."""
        return Agent(
            role="Newsletter Curator & Writer",
            goal=(
                "Create engaging, valuable newsletters by reading incoming emails, "
                "analyzing competitor newsletters, researching trending topics, "
                "and crafting compelling content for the target audience."
            ),
            backstory=(
                "You are an experienced newsletter curator with expertise in "
                "content curation, email marketing, and audience engagement. "
                "You have a keen eye for identifying valuable content and "
                "transforming it into engaging newsletter sections. You understand "
                "what makes readers open, read, and act on newsletters."
            ),
            tools=self._get_tools(),
            llm=self.llm_model,
            verbose=True,
            allow_delegation=False,
            max_iter=10,
        )

    def get_agent(self) -> Agent:
        """Return the CrewAI agent instance."""
        return self.agent


class NewsletterResearchAgent:
    """
    Specialized agent for newsletter research and analysis.
    Focuses on reading emails and analyzing competitor content.
    """

    def __init__(self, llm_model: Optional[str] = None):
        self.llm_model = llm_model or NEWSLETTER_DEFAULTS["llm_model"]
        self.agent = self._create_agent()

    def _create_agent(self) -> Agent:
        tools = [
            read_recent_newsletters,
            read_competitor_newsletters,
            research_newsletter_topics,
            find_related_articles,
        ]
        tools.extend(get_gmail_tools())

        # Add memory tools if available
        if MEMORY_AVAILABLE:
            tools.extend([recall_project_context, recall_past_newsletters])

        return Agent(
            role="Newsletter Research Analyst",
            goal=(
                "Analyze incoming emails and competitor newsletters to identify "
                "trends, successful content patterns, and opportunities for "
                "our newsletter content."
            ),
            backstory=(
                "You are a research analyst specializing in email marketing. "
                "You excel at pattern recognition, competitive analysis, and "
                "extracting actionable insights from large volumes of content."
            ),
            tools=tools,
            llm=self.llm_model,
            verbose=True,
            allow_delegation=False,
        )

    def get_agent(self) -> Agent:
        return self.agent


class NewsletterWriterAgent:
    """
    Specialized agent for newsletter content writing.
    Takes research insights and creates polished newsletter content.
    """

    def __init__(self, llm_model: Optional[str] = None):
        self.llm_model = llm_model or NEWSLETTER_DEFAULTS["llm_model"]
        self.agent = self._create_agent()

    def _create_agent(self) -> Agent:
        tools = []

        # Add memory tools if available
        if MEMORY_AVAILABLE:
            tools.append(recall_brand_voice)

        return Agent(
            role="Newsletter Content Writer",
            goal=(
                "Transform research insights and curated content into engaging, "
                "well-structured newsletter sections that drive reader engagement."
            ),
            backstory=(
                "You are a skilled copywriter with expertise in email marketing. "
                "You write compelling subject lines, engaging intros, and content "
                "that keeps readers scrolling. You understand email-specific "
                "formatting and mobile-first reading patterns. When available, "
                "you use brand voice guidelines from memory to maintain consistent "
                "tone and style across all newsletters."
            ),
            tools=tools,
            llm=self.llm_model,
            verbose=True,
            allow_delegation=False,
        )

    def get_agent(self) -> Agent:
        return self.agent
