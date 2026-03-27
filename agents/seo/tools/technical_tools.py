"""
Technical SEO Tools
Tools for schema generation, metadata validation, internal linking, and on-page optimization.
"""
from typing import Dict, List, Any, Optional
import json
from datetime import datetime


class SchemaGenerator:
    """Generate schema.org structured data markup."""
    
    def generate_schema(
        self,
        content_type: str,
        title: str,
        description: str,
        author: Optional[str] = None,
        date_published: Optional[str] = None,
        image_url: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Generate schema.org JSON-LD markup.
        
        Args:
            content_type: Type (Article, BlogPosting, NewsArticle)
            title: Article title
            description: Article description
            author: Author name
            date_published: Publication date
            image_url: Featured image URL
            
        Returns:
            Schema.org JSON-LD markup
        """
        schema = {
            "@context": "https://schema.org",
            "@type": content_type or "Article",
            "headline": title,
            "description": description,
            "datePublished": date_published or datetime.now().isoformat(),
            "dateModified": datetime.now().isoformat()
        }
        
        if author:
            schema["author"] = {
                "@type": "Person",
                "name": author
            }
        else:
            schema["author"] = {
                "@type": "Organization",
                "name": "Your Company Name"
            }
        
        schema["publisher"] = {
            "@type": "Organization",
            "name": "Your Company Name",
            "logo": {
                "@type": "ImageObject",
                "url": "https://yoursite.com/logo.png"
            }
        }
        
        if image_url:
            schema["image"] = image_url
        else:
            schema["image"] = "https://yoursite.com/default-image.jpg"
        
        return {
            "json_ld": json.dumps(schema, indent=2),
            "schema_type": content_type,
            "validation_notes": [
                "Test with Google Rich Results Test",
                "Update publisher name and logo",
                "Add actual image URL",
                "Verify all required fields are present"
            ]
        }


class MetadataValidator:
    """Validate SEO metadata."""
    
    def validate_metadata(
        self,
        title: str,
        description: str,
        keywords: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """
        Validate SEO metadata elements.
        
        Args:
            title: Title tag
            description: Meta description
            keywords: Target keywords
            
        Returns:
            Validation results with recommendations
        """
        issues = []
        recommendations = []
        
        # Title validation
        title_length = len(title)
        if title_length < 30:
            issues.append({"severity": "high", "element": "title", "issue": "Title too short"})
        elif title_length > 60:
            issues.append({"severity": "medium", "element": "title", "issue": "Title may be truncated in SERPs"})
        else:
            recommendations.append("Title length is optimal (30-60 chars)")
        
        # Description validation
        desc_length = len(description)
        if desc_length < 120:
            issues.append({"severity": "high", "element": "description", "issue": "Description too short"})
        elif desc_length > 160:
            issues.append({"severity": "medium", "element": "description", "issue": "Description may be truncated"})
        else:
            recommendations.append("Meta description length is optimal")
        
        # Keyword validation
        if keywords:
            primary_keyword = keywords[0].lower()
            if primary_keyword not in title.lower():
                issues.append({"severity": "high", "element": "title", "issue": "Primary keyword not in title"})
            if primary_keyword not in description.lower():
                issues.append({"severity": "medium", "element": "description", "issue": "Primary keyword not in description"})
        
        return {
            "title": {"text": title, "length": title_length, "status": "valid" if 30 <= title_length <= 60 else "needs_review"},
            "description": {"text": description, "length": desc_length, "status": "valid" if 120 <= desc_length <= 160 else "needs_review"},
            "issues": issues,
            "recommendations": recommendations,
            "overall_score": max(0, 100 - (len(issues) * 10))
        }


class InternalLinkingAnalyzer:
    """Analyze and recommend internal linking."""
    
    def analyze_internal_links(
        self,
        article_content: str,
        existing_pages: Optional[List[str]] = None,
        topic_cluster: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Analyze internal linking opportunities.
        
        Args:
            article_content: Article content
            existing_pages: List of existing pages
            topic_cluster: Topic cluster information
            
        Returns:
            Internal linking recommendations
        """
        recommendations = []
        
        if existing_pages:
            for i, page in enumerate(existing_pages[:5]):
                recommendations.append({
                    "target_page": page,
                    "anchor_text": f"Learn more about {page.split('/')[-1].replace('-', ' ')}",
                    "context": f"Contextual link in section {i+2}",
                    "priority": "high" if i < 2 else "medium",
                    "link_type": "contextual"
                })
        
        return {
            "total_recommendations": len(recommendations),
            "internal_links": recommendations,
            "best_practices": [
                "Use descriptive anchor text (not 'click here')",
                "Link to relevant, related content",
                "Distribute links throughout content naturally",
                "Link to both pillar pages and cluster content",
                "Use 2-5 internal links per 1000 words"
            ],
            "link_equity_notes": "Prioritize links to strategic pages (pillar content, conversion pages)"
        }


class OnPageOptimizer:
    """Optimize on-page SEO elements."""
    
    def optimize_onpage(
        self,
        content: str,
        primary_keyword: str,
        target_word_count: int = 2000
    ) -> Dict[str, Any]:
        """
        Analyze on-page optimization.
        
        Args:
            content: Article content
            primary_keyword: Primary target keyword
            target_word_count: Target word count
            
        Returns:
            On-page optimization analysis
        """
        word_count = len(content.split())
        
        # Heading analysis
        h1_count = content.count('\n# ')
        h2_count = content.count('\n## ')
        
        issues = []
        optimizations = []
        
        # Word count check
        if word_count < target_word_count * 0.8:
            issues.append({"type": "content_length", "severity": "medium", "detail": f"Content is {word_count} words, target is {target_word_count}"})
        elif word_count > target_word_count * 1.2:
            optimizations.append("Consider condensing - content exceeds target significantly")
        else:
            optimizations.append("Content length is appropriate")
        
        # Heading structure
        if h1_count != 1:
            issues.append({"type": "heading_structure", "severity": "high", "detail": f"Should have exactly 1 H1, found {h1_count}"})
        else:
            optimizations.append("H1 structure is correct")
        
        if h2_count < 3:
            issues.append({"type": "heading_structure", "severity": "low", "detail": "Consider adding more H2 sections for better structure"})
        
        return {
            "word_count": word_count,
            "target_word_count": target_word_count,
            "heading_structure": {
                "h1_count": h1_count,
                "h2_count": h2_count,
                "status": "valid" if h1_count == 1 else "invalid"
            },
            "issues": issues,
            "optimizations": optimizations,
            "seo_score": max(0, 100 - (len(issues) * 15)),
            "recommendations": [
                "Ensure single H1 with primary keyword",
                "Use H2-H6 for logical content hierarchy",
                "Include keyword variations in headings naturally",
                "Add alt text to all images",
                "Use semantic HTML5 elements"
            ]
        }
