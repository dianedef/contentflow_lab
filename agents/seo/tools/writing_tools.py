"""
Writing Tools for Copywriter Agent
Tools for content writing, metadata generation, keyword integration, and tone adaptation.
"""
from typing import Dict, List, Any, Optional
import re


class ContentWriter:
    """Write SEO-optimized content."""
    
    def write_content(
        self,
        outline: str,
        target_word_count: int = 2000,
        style: str = "engaging"
    ) -> Dict[str, Any]:
        """
        Write content based on outline (this is a framework - LLM does actual writing).
        
        Args:
            outline: Content outline
            target_word_count: Target word count
            style: Writing style (engaging, technical, simple, persuasive)
            
        Returns:
            Writing guidelines and structure
        """
        return {
            "outline_received": True,
            "target_word_count": target_word_count,
            "style": style,
            "sections_identified": self._parse_outline_sections(outline),
            "writing_guidelines": {
                "sentence_variety": "Mix short (5-10 words) and medium (15-20 words) sentences",
                "paragraph_length": "3-4 sentences maximum per paragraph",
                "readability_target": "Flesch Reading Ease: 60-70 (8th-9th grade)",
                "active_voice": "Use active voice in 80%+ of sentences",
                "transitions": "Use transitional phrases between sections",
                "examples": "Include at least one concrete example per major section",
                "data_points": "Add statistics or data every 300-400 words"
            },
            "engagement_techniques": [
                "Start with compelling hook (question, statistic, or story)",
                "Use 'you' language to connect with reader",
                "Break up text with subheadings every 300-400 words",
                "Add bullet points for scannable content",
                "Include actionable takeaways",
                "End with clear next steps or CTA"
            ]
        }
    
    def _parse_outline_sections(self, outline: str) -> List[Dict[str, str]]:
        """Parse outline into structured sections."""
        sections = []
        lines = outline.split('\n')
        
        for line in lines:
            line = line.strip()
            if line.startswith('##'):
                sections.append({
                    "level": "h2",
                    "text": line.replace('##', '').strip()
                })
            elif line.startswith('###'):
                sections.append({
                    "level": "h3",
                    "text": line.replace('###', '').strip()
                })
        
        return sections


class MetadataGenerator:
    """Generate SEO metadata."""
    
    def generate_metadata(
        self,
        article_title: str,
        primary_keyword: str,
        article_summary: Optional[str] = None,
        brand_name: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Generate SEO metadata (title tags, meta descriptions).
        
        Args:
            article_title: Main article title
            primary_keyword: Primary target keyword
            article_summary: Brief summary of article
            brand_name: Brand/company name
            
        Returns:
            Dictionary with metadata elements
        """
        # Generate title tag variations
        title_templates = [
            f"{article_title} | {brand_name}" if brand_name else article_title,
            f"{primary_keyword}: {article_title}",
            f"{article_title} - Complete Guide",
            f"How to {article_title}" if not article_title.lower().startswith('how') else article_title
        ]
        
        # Keep best titles under 60 chars
        title_tags = [t for t in title_templates if len(t) <= 60]
        if not title_tags:
            title_tags = [title_templates[0][:57] + "..."]
        
        # Generate meta description
        if article_summary:
            meta_desc = article_summary[:157] + "..." if len(article_summary) > 160 else article_summary
        else:
            meta_desc = (
                f"Learn everything about {primary_keyword}. "
                f"Complete guide with examples, best practices, and actionable tips. "
                f"Read now to master {primary_keyword}."
            )
            if len(meta_desc) > 160:
                meta_desc = meta_desc[:157] + "..."
        
        return {
            "title_tag_options": title_tags,
            "recommended_title": title_tags[0],
            "title_length": len(title_tags[0]),
            "meta_description": meta_desc,
            "meta_description_length": len(meta_desc),
            "og_tags": {
                "og:title": title_tags[0],
                "og:description": meta_desc,
                "og:type": "article"
            },
            "twitter_card": {
                "twitter:card": "summary_large_image",
                "twitter:title": title_tags[0],
                "twitter:description": meta_desc
            },
            "structured_data_type": "Article",
            "recommendations": [
                "Keep title under 60 characters for full display",
                "Keep meta description under 160 characters",
                "Include primary keyword in both title and description",
                "Make description compelling - it's your SERP ad copy",
                "Add schema.org Article markup for rich results"
            ]
        }


class KeywordIntegrator:
    """Integrate keywords naturally into content."""
    
    def integrate_keywords(
        self,
        content: str,
        primary_keyword: str,
        secondary_keywords: Optional[List[str]] = None,
        target_density: float = 1.5
    ) -> Dict[str, Any]:
        """
        Analyze and provide keyword integration guidance.
        
        Args:
            content: Content text to analyze
            primary_keyword: Primary target keyword
            secondary_keywords: Secondary keywords list
            target_density: Target keyword density (percentage)
            
        Returns:
            Analysis and recommendations for keyword usage
        """
        word_count = len(content.split())
        
        # Count primary keyword occurrences
        primary_count = len(re.findall(
            r'\b' + re.escape(primary_keyword.lower()) + r'\b',
            content.lower()
        ))
        primary_density = (primary_count / word_count * 100) if word_count > 0 else 0
        
        # Analyze secondary keywords
        secondary_analysis = []
        if secondary_keywords:
            for kw in secondary_keywords:
                count = len(re.findall(
                    r'\b' + re.escape(kw.lower()) + r'\b',
                    content.lower()
                ))
                secondary_analysis.append({
                    "keyword": kw,
                    "count": count,
                    "density": (count / word_count * 100) if word_count > 0 else 0
                })
        
        # Detect keyword positions
        keyword_positions = self._detect_keyword_positions(content, primary_keyword)
        
        return {
            "word_count": word_count,
            "primary_keyword": primary_keyword,
            "primary_keyword_count": primary_count,
            "primary_keyword_density": round(primary_density, 2),
            "target_density": target_density,
            "density_status": self._evaluate_density(primary_density, target_density),
            "keyword_positions": keyword_positions,
            "secondary_keywords": secondary_analysis,
            "recommendations": self._generate_keyword_recommendations(
                primary_density,
                target_density,
                keyword_positions,
                secondary_analysis
            ),
            "natural_variations": self._suggest_variations(primary_keyword)
        }
    
    def _detect_keyword_positions(self, content: str, keyword: str) -> Dict[str, bool]:
        """Detect where keyword appears in content."""
        content_lower = content.lower()
        keyword_lower = keyword.lower()
        
        # Split into sections
        first_100_words = ' '.join(content.split()[:100])
        last_100_words = ' '.join(content.split()[-100:])
        
        return {
            "in_first_100_words": keyword_lower in first_100_words.lower(),
            "in_last_100_words": keyword_lower in last_100_words.lower(),
            "in_headings": bool(re.search(r'#+.*' + re.escape(keyword_lower), content_lower)),
            "well_distributed": True  # Simplified - would need more analysis
        }
    
    def _evaluate_density(self, actual: float, target: float) -> str:
        """Evaluate if keyword density is appropriate."""
        if actual < target * 0.5:
            return "too_low"
        elif actual > target * 1.5:
            return "too_high"
        else:
            return "optimal"
    
    def _generate_keyword_recommendations(
        self,
        density: float,
        target: float,
        positions: Dict[str, bool],
        secondary: List[Dict[str, Any]]
    ) -> List[str]:
        """Generate keyword integration recommendations."""
        recommendations = []
        
        if density < target * 0.5:
            recommendations.append(f"Increase primary keyword usage - current density {density:.1f}% is below target {target}%")
        elif density > target * 1.5:
            recommendations.append(f"Reduce primary keyword usage - {density:.1f}% density may appear over-optimized")
        else:
            recommendations.append(f"Keyword density is optimal at {density:.1f}%")
        
        if not positions["in_first_100_words"]:
            recommendations.append("Add primary keyword in first 100 words")
        
        if not positions["in_headings"]:
            recommendations.append("Include primary keyword in at least one H2 or H3 heading")
        
        if not positions["in_last_100_words"]:
            recommendations.append("Mention primary keyword in conclusion")
        
        if secondary:
            low_usage = [s for s in secondary if s["count"] < 2]
            if low_usage:
                recommendations.append(f"Consider using secondary keywords more: {', '.join([s['keyword'] for s in low_usage[:3]])}")
        
        recommendations.append("Use semantic variations and related terms naturally")
        recommendations.append("Prioritize natural language over keyword frequency")
        
        return recommendations
    
    def _suggest_variations(self, keyword: str) -> List[str]:
        """Suggest natural keyword variations."""
        # Simple variation suggestions (in production, would use NLP)
        words = keyword.split()
        variations = [
            keyword,
            f"{keyword}s" if not keyword.endswith('s') else keyword,
            f"best {keyword}",
            f"{keyword} guide",
            f"how to {keyword}" if len(words) < 4 else keyword
        ]
        return list(set(variations))[:5]


class ToneAdapter:
    """Adapt content tone to audience and brand."""
    
    def adapt_tone(
        self,
        target_tone: str,
        target_audience: Optional[str] = None,
        brand_values: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """
        Provide tone adaptation guidelines.
        
        Args:
            target_tone: Desired tone (professional, casual, technical, friendly, authoritative)
            target_audience: Target audience description
            brand_values: Brand values list
            
        Returns:
            Tone guidelines and examples
        """
        tone_guides = {
            "professional": {
                "characteristics": ["Formal but accessible", "Credible", "Polished"],
                "vocabulary": "Industry standard terminology",
                "sentence_structure": "Complete sentences, proper grammar",
                "voice": "Third person or inclusive first person ('we')",
                "avoid": ["Slang", "Excessive casual language", "Overly complex jargon"],
                "example": "Our comprehensive analysis demonstrates that content marketing strategies significantly impact ROI when properly executed."
            },
            "casual": {
                "characteristics": ["Conversational", "Relatable", "Friendly"],
                "vocabulary": "Everyday language, simple words",
                "sentence_structure": "Mix of short and medium sentences, fragments OK",
                "voice": "Second person ('you'), first person ('I', 'we')",
                "avoid": ["Overly formal language", "Complex terminology", "Corporate speak"],
                "example": "Here's the thing about content marketing - it works best when you're real with your audience."
            },
            "technical": {
                "characteristics": ["Precise", "Detailed", "Analytical"],
                "vocabulary": "Technical terminology, specific jargon",
                "sentence_structure": "Clear, detailed explanations",
                "voice": "Third person, objective",
                "avoid": ["Oversimplification", "Vague terms", "Marketing speak"],
                "example": "The algorithm processes semantic relationships using vectorized embeddings to optimize content clustering."
            },
            "friendly": {
                "characteristics": ["Warm", "Approachable", "Encouraging"],
                "vocabulary": "Positive language, inclusive terms",
                "sentence_structure": "Conversational flow, varied length",
                "voice": "Second person ('you'), warm first person",
                "avoid": ["Cold corporate language", "Negative framing", "Intimidating terms"],
                "example": "Great question! Let's walk through this together and I'll show you exactly how it works."
            },
            "authoritative": {
                "characteristics": ["Expert", "Confident", "Trustworthy"],
                "vocabulary": "Precise, industry-standard terms",
                "sentence_structure": "Clear, declarative statements",
                "voice": "First person plural ('we'), confident tone",
                "avoid": ["Hedging language", "Uncertainty", "Overly casual tone"],
                "example": "Based on our 15 years of experience, we've identified three critical factors that determine content success."
            }
        }
        
        guide = tone_guides.get(target_tone, tone_guides["professional"])
        
        result = {
            "target_tone": target_tone,
            "guidelines": guide,
            "target_audience": target_audience,
            "writing_checklist": [
                f"Maintain {target_tone} tone throughout",
                "Stay consistent with brand voice",
                "Match reader's sophistication level",
                "Use appropriate vocabulary for audience",
                "Keep perspective consistent (you/we/they)"
            ]
        }
        
        if target_audience:
            result["audience_adaptation"] = self._get_audience_guidance(target_audience)
        
        if brand_values:
            result["brand_alignment"] = {
                "values": brand_values,
                "guidance": f"Ensure content reflects: {', '.join(brand_values)}"
            }
        
        return result
    
    def _get_audience_guidance(self, audience: str) -> Dict[str, str]:
        """Get audience-specific writing guidance."""
        audience_lower = audience.lower()
        
        if "executive" in audience_lower or "c-level" in audience_lower:
            return {
                "focus": "Business impact and ROI",
                "language": "Strategic, high-level",
                "length": "Concise - executives value their time"
            }
        elif "technical" in audience_lower or "developer" in audience_lower:
            return {
                "focus": "Implementation details and technical accuracy",
                "language": "Precise technical terminology",
                "length": "Detailed with code examples"
            }
        elif "beginner" in audience_lower or "novice" in audience_lower:
            return {
                "focus": "Clear explanations and step-by-step guidance",
                "language": "Simple, define terminology",
                "length": "Comprehensive with examples"
            }
        else:
            return {
                "focus": "Practical value and actionability",
                "language": "Clear and accessible",
                "length": "Balanced - thorough but scannable"
            }
