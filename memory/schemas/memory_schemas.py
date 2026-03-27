"""
Memory Schemas - Pydantic models for the Mem0 memory layer.

Defines structured types for storing and retrieving project knowledge,
generation records, and brand context.
"""

from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field
from datetime import datetime
from enum import Enum


class MemoryType(str, Enum):
    """Categories of memories stored in the project brain."""
    BRAND_VOICE = "brand_voice"
    CONTENT_INVENTORY = "content_inventory"
    GENERATION_RECORD = "generation_record"
    TOPIC_CLUSTER = "topic_cluster"
    AUDIENCE = "audience"
    STRATEGY = "strategy"


class MemoryEntry(BaseModel):
    """A single memory entry retrieved from Mem0."""

    id: Optional[str] = Field(None, description="Mem0 memory ID")
    memory: str = Field(..., description="The memory content text")
    metadata: Dict[str, Any] = Field(default_factory=dict)
    score: Optional[float] = Field(None, description="Relevance score from search")
    created_at: Optional[str] = Field(None, description="Creation timestamp")

    def __str__(self) -> str:
        return self.memory


class MemoryContext(BaseModel):
    """Collection of memories formatted for prompt injection."""

    memories: List[MemoryEntry] = Field(default_factory=list)
    query: str = Field(default="", description="Original search query")
    agent_id: Optional[str] = Field(None, description="Agent that requested context")

    def to_prompt_context(self) -> str:
        """Format memories as a string suitable for injection into agent prompts."""
        if not self.memories:
            return ""

        lines = [f"=== Project Memory ({len(self.memories)} entries) ==="]
        for i, entry in enumerate(self.memories, 1):
            mem_type = entry.metadata.get("type", "general")
            lines.append(f"\n[{i}] ({mem_type}) {entry.memory}")
        lines.append("\n=== End Project Memory ===")
        return "\n".join(lines)

    @property
    def is_empty(self) -> bool:
        return len(self.memories) == 0


class SeedKnowledge(BaseModel):
    """Knowledge to seed into the project brain."""

    content: str = Field(..., description="Knowledge content to store")
    memory_type: MemoryType = Field(..., description="Category of knowledge")
    metadata: Dict[str, Any] = Field(default_factory=dict)

    def to_storage_content(self) -> str:
        """Format content for storage with type prefix."""
        return f"[{self.memory_type.value}] {self.content}"


class GenerationRecord(BaseModel):
    """Record of a content generation run for deduplication."""

    content_type: str = Field(..., description="Type: newsletter, article, etc.")
    title: str = Field(..., description="Title or subject line")
    topics: List[str] = Field(default_factory=list, description="Topics covered")
    summary: str = Field(default="", description="Brief summary of content")
    generated_at: datetime = Field(default_factory=datetime.now)

    def to_memory_content(self) -> str:
        """Format as memory content for storage."""
        topics_str = ", ".join(self.topics) if self.topics else "general"
        date_str = self.generated_at.strftime("%Y-%m-%d")
        return (
            f"[{self.content_type}] Generated on {date_str}: "
            f'"{self.title}" covering topics: {topics_str}. '
            f"{self.summary}"
        )

    def to_metadata(self) -> Dict[str, Any]:
        """Build metadata dict for storage."""
        return {
            "type": MemoryType.GENERATION_RECORD.value,
            "content_type": self.content_type,
            "title": self.title,
            "topics": self.topics,
            "generated_at": self.generated_at.isoformat(),
        }
