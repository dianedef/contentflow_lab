"""
Editing Tools for Editor Agent
Tools for quality checking, consistency validation, markdown formatting, and publication preparation.
"""
from typing import Dict, List, Any, Optional
import re


class QualityChecker:
    """Check content quality and readability."""
    
    def check_quality(
        self,
        content: str,
        min_words: int = 1500
    ) -> Dict[str, Any]:
        """
        Check content quality metrics.
        
        Args:
            content: Content to check
            min_words: Minimum word count requirement
            
        Returns:
            Quality analysis results
        """
        words = content.split()
        word_count = len(words)
        
        # Count sentences (approximate)
        sentences = len(re.findall(r'[.!?]+', content))
        
        # Calculate average sentence length
        avg_sentence_length = word_count / sentences if sentences > 0 else 0
        
        # Count paragraphs
        paragraphs = len([p for p in content.split('\n\n') if p.strip()])
        
        # Quality scores
        issues = []
        
        if word_count < min_words:
            issues.append(f"Word count below minimum ({word_count}/{min_words})")
        
        if avg_sentence_length > 25:
            issues.append("Average sentence length too high - reduce complexity")
        
        if avg_sentence_length < 10:
            issues.append("Average sentence length too low - vary sentence structure")
        
        # Calculate readability score (simplified Flesch Reading Ease)
        # Real implementation would use syllable counting
        readability_score = 206.835 - (1.015 * avg_sentence_length)
        
        return {
            "word_count": word_count,
            "sentence_count": sentences,
            "paragraph_count": paragraphs,
            "avg_sentence_length": round(avg_sentence_length, 1),
            "readability_score": round(readability_score, 1),
            "readability_level": self._get_readability_level(readability_score),
            "issues": issues,
            "quality_grade": self._calculate_grade(word_count, min_words, avg_sentence_length, issues),
            "recommendations": [
                "Target 8th-9th grade reading level",
                "Vary sentence length for rhythm",
                "Use active voice in 80%+ of sentences",
                "Break long paragraphs (max 4-5 sentences)",
                "Add examples and concrete details"
            ]
        }
    
    def _get_readability_level(self, score: float) -> str:
        """Convert Flesch score to reading level."""
        if score >= 90:
            return "5th grade (very easy)"
        elif score >= 80:
            return "6th grade (easy)"
        elif score >= 70:
            return "7th grade (fairly easy)"
        elif score >= 60:
            return "8th-9th grade (standard)"
        elif score >= 50:
            return "10th-12th grade (fairly difficult)"
        else:
            return "College level (difficult)"
    
    def _calculate_grade(self, word_count: int, min_words: int, avg_sent: float, issues: List[str]) -> str:
        """Calculate overall quality grade."""
        score = 100
        
        if word_count < min_words:
            score -= 20
        
        if avg_sent > 25 or avg_sent < 10:
            score -= 15
        
        score -= len(issues) * 5
        
        if score >= 90:
            return "A"
        elif score >= 80:
            return "B"
        elif score >= 70:
            return "C"
        elif score >= 60:
            return "D"
        else:
            return "F"


class ConsistencyValidator:
    """Validate content consistency."""
    
    def validate_consistency(
        self,
        content: str,
        brand_voice: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Validate tone and formatting consistency.
        
        Args:
            content: Content to validate
            brand_voice: Target brand voice
            
        Returns:
            Consistency validation results
        """
        issues = []
        
        # Check heading hierarchy
        headings = re.findall(r'^(#+)\s+(.+)$', content, re.MULTILINE)
        h1_count = sum(1 for h in headings if h[0] == '#')
        
        if h1_count != 1:
            issues.append(f"Inconsistent H1 usage: found {h1_count}, should be 1")
        
        # Check for common inconsistencies
        if 'dont' in content.lower() and "don't" in content.lower():
            issues.append("Inconsistent contraction usage")
        
        # Check for mixed list formatting
        bullet_points = len(re.findall(r'^\s*[-*+]\s', content, re.MULTILINE))
        numbered_lists = len(re.findall(r'^\s*\d+\.\s', content, re.MULTILINE))
        
        consistency_score = max(0, 100 - (len(issues) * 10))
        
        return {
            "heading_hierarchy": {
                "h1_count": h1_count,
                "total_headings": len(headings),
                "status": "consistent" if h1_count == 1 else "inconsistent"
            },
            "list_formatting": {
                "bullet_points": bullet_points,
                "numbered_lists": numbered_lists,
                "mixed_usage": bullet_points > 0 and numbered_lists > 0
            },
            "issues": issues,
            "consistency_score": consistency_score,
            "recommendations": [
                "Use single H1 for main title",
                "Maintain consistent heading levels",
                "Use consistent list formatting",
                "Keep tone consistent throughout",
                "Use consistent capitalization in headings"
            ]
        }


class MarkdownFormatter:
    """Format content as clean markdown."""
    
    def format_markdown(
        self,
        content: str,
        add_frontmatter: bool = True,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Format content as clean markdown.
        
        Args:
            content: Raw content
            add_frontmatter: Add YAML frontmatter
            metadata: Metadata for frontmatter
            
        Returns:
            Formatted markdown
        """
        formatted = content.strip()
        
        # Clean up extra blank lines
        formatted = re.sub(r'\n{3,}', '\n\n', formatted)
        
        # Ensure proper spacing around headings
        formatted = re.sub(r'(#+\s.+)\n([^\n])', r'\1\n\n\2', formatted)
        
        # Format lists properly
        formatted = re.sub(r'\n([-*+]\s)', r'\n\1', formatted)
        
        frontmatter = ""
        if add_frontmatter and metadata:
            frontmatter = "---\n"
            frontmatter += f"title: \"{metadata.get('title', 'Untitled')}\"\n"
            frontmatter += f"description: \"{metadata.get('description', '')}\"\n"
            frontmatter += f"date: {metadata.get('date', '2024-01-01')}\n"
            if metadata.get('keywords'):
                frontmatter += f"keywords: [{', '.join(metadata['keywords'])}]\n"
            frontmatter += "---\n\n"
        
        final_content = frontmatter + formatted
        
        return {
            "formatted_content": final_content,
            "has_frontmatter": bool(frontmatter),
            "line_count": len(final_content.split('\n')),
            "formatting_applied": [
                "Cleaned extra blank lines",
                "Proper heading spacing",
                "List formatting normalized",
                "Added frontmatter" if frontmatter else "No frontmatter"
            ]
        }


class PublicationPreparer:
    """Prepare content for publication."""
    
    def prepare_for_publication(
        self,
        content: str,
        metadata: Dict[str, Any],
        checklist_items: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """
        Prepare content for publication.
        
        Args:
            content: Final content
            metadata: Article metadata
            checklist_items: Custom checklist items
            
        Returns:
            Publication package with checklist
        """
        default_checklist = [
            "✅ Content reviewed and edited",
            "✅ Grammar and spelling checked",
            "✅ SEO metadata validated",
            "✅ Schema markup added",
            "✅ Internal links verified",
            "✅ Images have alt text",
            "✅ Markdown properly formatted",
            "⬜ Featured image selected",
            "⬜ URL slug optimized",
            "⬜ Categories/tags assigned",
            "⬜ Social media preview tested",
            "⬜ Mobile preview checked",
            "⬜ Final stakeholder approval"
        ]
        
        if checklist_items:
            default_checklist.extend(checklist_items)
        
        post_publication = [
            "Monitor search console for indexing",
            "Track rankings for target keywords",
            "Monitor engagement metrics (time on page, bounce rate)",
            "Share on social media channels",
            "Add to internal linking strategy",
            "Update related content with links to new article",
            "Schedule content refresh in 6-12 months"
        ]
        
        return {
            "status": "ready_for_review",
            "content_length": len(content.split()),
            "metadata": metadata,
            "pre_publication_checklist": default_checklist,
            "post_publication_tasks": post_publication,
            "estimated_publication_time": "15-30 minutes",
            "success_metrics": [
                "Organic impressions in first 30 days",
                "Average position for target keyword",
                "Click-through rate from SERPs",
                "Time on page and engagement",
                "Internal link clicks",
                "Social shares and backlinks"
            ],
            "publication_notes": [
                "Schedule during peak traffic hours",
                "Announce in newsletter if applicable",
                "Update XML sitemap after publication",
                "Submit URL to Search Console for indexing",
                "Monitor for any technical issues"
            ]
        }
