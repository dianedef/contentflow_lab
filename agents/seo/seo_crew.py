"""
SEO Content Generation Crew - Hierarchical Multi-Agent Workflow
Orchestrates all 6 SEO agents in a sequential pipeline.

Pipeline: Research → Strategy → Writing → Technical → Marketing → Editing
"""
from typing import List, Optional, Dict, Any
from crewai import Agent, Task, Crew, Process
from dotenv import load_dotenv
import os
from datetime import datetime

# Import all agents
from agents.seo.research_analyst import ResearchAnalystAgent
from agents.seo.content_strategist import ContentStrategistAgent
from agents.seo.copywriter import CopywriterAgent
from agents.seo.technical_seo import TechnicalSEOAgent
from agents.seo.marketing_strategist import MarketingStrategistAgent
from agents.seo.editor import EditorAgent

load_dotenv()

# Conditional status tracking (graceful degradation)
try:
    from status import get_status_service
    STATUS_AVAILABLE = True
except ImportError:
    STATUS_AVAILABLE = False


class SEOContentCrew:
    """
    Hierarchical multi-agent system for SEO content generation.
    Coordinates 6 specialized agents to produce publication-ready content.
    """
    
    def __init__(self, llm_model: str = "mixtral-8x7b-32768", use_consensus_ai: bool = False):
        """
        Initialize SEO Content Crew with all agents.
        
        Args:
            llm_model: Groq model to use for all agents
            use_consensus_ai: Whether to use Consensus AI for research
        """
        self.llm_model = llm_model
        
        # Initialize all agents
        print("Initializing SEO Content Crew...")
        self.research_agent = ResearchAnalystAgent(llm_model, use_consensus_ai=use_consensus_ai)
        self.strategy_agent = ContentStrategistAgent(llm_model)
        self.copywriter_agent = CopywriterAgent(llm_model)
        self.technical_agent = TechnicalSEOAgent(llm_model)
        self.marketing_agent = MarketingStrategistAgent(llm_model)
        self.editor_agent = EditorAgent(llm_model)
        
        print("✅ All 6 agents initialized")
    
    def generate_content(
        self,
        target_keyword: str,
        competitor_domains: Optional[List[str]] = None,
        sector: Optional[str] = None,
        business_goals: Optional[List[str]] = None,
        brand_voice: Optional[str] = None,
        target_audience: Optional[str] = None,
        word_count: int = 2500,
        tone: str = "professional",
        existing_content: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """
        Generate complete SEO-optimized content through multi-agent workflow.
        
        Args:
            target_keyword: Primary keyword to target
            competitor_domains: Competitor domains for analysis
            sector: Industry sector
            business_goals: Business objectives
            brand_voice: Brand voice description
            target_audience: Target audience description
            word_count: Target word count
            tone: Writing tone
            existing_content: Existing content for internal linking
            
        Returns:
            Dictionary with all outputs from each agent
        """
        print("\n" + "="*60)
        print("SEO CONTENT GENERATION PIPELINE")
        print("="*60)
        print(f"Target Keyword: {target_keyword}")
        print(f"Word Count: {word_count}")
        print(f"Tone: {tone}")
        print(f"Start Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print("="*60 + "\n")

        # Status tracking: create content record
        status_record_id = None
        if STATUS_AVAILABLE:
            try:
                status_svc = get_status_service()
                record = status_svc.create_content(
                    title=f"SEO: {target_keyword}",
                    content_type="seo-content",
                    source_robot="seo",
                    status="in_progress",
                    tags=[target_keyword] + (business_goals or []),
                    metadata={
                        "target_keyword": target_keyword,
                        "word_count": word_count,
                        "tone": tone,
                        "sector": sector,
                        "competitor_domains": competitor_domains or [],
                    },
                )
                status_record_id = record.id
                print(f"📊 Status tracking: record {record.id} created (in_progress)")
            except Exception as e:
                print(f"⚠ Status tracking init failed (non-critical): {e}")

        results = {
            "input": {
                "target_keyword": target_keyword,
                "competitor_domains": competitor_domains,
                "sector": sector,
                "business_goals": business_goals,
                "word_count": word_count
            },
            "outputs": {}
        }
        
        # STAGE 1: Research & Analysis
        print("\n📊 STAGE 1: RESEARCH & COMPETITIVE ANALYSIS")
        print("-" * 60)
        
        research_task = self.research_agent.create_analysis_task(
            target_keyword=target_keyword,
            competitor_domains=competitor_domains,
            sector=sector,
            target_domain=existing_content[0] if existing_content else None
        )
        
        research_crew = Crew(
            agents=[self.research_agent.agent],
            tasks=[research_task],
            verbose=True,
            process=Process.sequential
        )
        
        research_output = research_crew.kickoff()
        results["outputs"]["research"] = str(research_output)
        print(f"\n✅ Research complete: {len(str(research_output))} characters\n")
        
        # STAGE 2: Content Strategy
        print("\n📋 STAGE 2: CONTENT STRATEGY & PLANNING")
        print("-" * 60)
        
        strategy_task = self.strategy_agent.create_strategy_task(
            research_insights=str(research_output),
            target_keyword=target_keyword,
            existing_content=existing_content,
            business_goals=business_goals,
            content_count=5
        )
        
        strategy_crew = Crew(
            agents=[self.strategy_agent.agent],
            tasks=[strategy_task],
            verbose=True,
            process=Process.sequential
        )
        
        strategy_output = strategy_crew.kickoff()
        results["outputs"]["strategy"] = str(strategy_output)
        print(f"\n✅ Strategy complete: {len(str(strategy_output))} characters\n")
        
        # Extract outline from strategy (simplified - in production would parse markdown)
        outline = str(strategy_output)[:2000]  # Use first 2000 chars as outline
        
        # STAGE 3: Content Writing
        print("\n✍️  STAGE 3: CONTENT WRITING")
        print("-" * 60)
        
        # Extract keywords (primary + variations)
        keywords = [target_keyword]
        if sector:
            keywords.append(f"{target_keyword} {sector}")
        
        writing_task = self.copywriter_agent.create_writing_task(
            content_outline=outline,
            target_keywords=keywords,
            tone=tone,
            brand_voice=brand_voice,
            target_audience=target_audience,
            word_count=word_count
        )
        
        writing_crew = Crew(
            agents=[self.copywriter_agent.agent],
            tasks=[writing_task],
            verbose=True,
            process=Process.sequential
        )
        
        article_output = writing_crew.kickoff()
        results["outputs"]["article"] = str(article_output)
        print(f"\n✅ Article complete: {len(str(article_output))} characters\n")
        
        # STAGE 4: Technical SEO
        print("\n🔧 STAGE 4: TECHNICAL SEO OPTIMIZATION")
        print("-" * 60)
        
        metadata = {
            "title": f"{target_keyword} - Complete Guide",
            "description": f"Learn everything about {target_keyword}",
            "keywords": keywords
        }
        
        technical_task = self.technical_agent.create_technical_task(
            article_content=str(article_output),
            article_metadata=metadata,
            existing_pages=existing_content
        )
        
        technical_crew = Crew(
            agents=[self.technical_agent.agent],
            tasks=[technical_task],
            verbose=True,
            process=Process.sequential
        )
        
        technical_output = technical_crew.kickoff()
        results["outputs"]["technical_seo"] = str(technical_output)
        print(f"\n✅ Technical SEO complete: {len(str(technical_output))} characters\n")
        
        # STAGE 5: Marketing Strategy & Business Validation
        print("\n💼 STAGE 5: MARKETING STRATEGY & BUSINESS VALIDATION")
        print("-" * 60)
        
        marketing_task = self.marketing_agent.create_strategy_task(
            content_strategy=str(strategy_output),
            article_content=str(article_output),
            technical_seo=str(technical_output),
            business_goals=business_goals,
            target_audience=target_audience
        )
        
        marketing_crew = Crew(
            agents=[self.marketing_agent.agent],
            tasks=[marketing_task],
            verbose=True,
            process=Process.sequential
        )
        
        marketing_output = marketing_crew.kickoff()
        results["outputs"]["marketing_strategy"] = str(marketing_output)
        print(f"\n✅ Marketing strategy complete: {len(str(marketing_output))} characters\n")
        
        # STAGE 6: Final Editing & QA
        print("\n📝 STAGE 6: EDITORIAL REVIEW & FINALIZATION")
        print("-" * 60)
        
        brand_guidelines = None
        if brand_voice:
            brand_guidelines = {
                "voice": brand_voice,
                "tone": tone,
                "values": business_goals if business_goals else []
            }
        
        quality_standards = {
            "min_words": word_count,
            "uniqueness": 90,
            "readability_target": "Flesch 60-70",
            "error_tolerance": "Zero"
        }
        
        editing_task = self.editor_agent.create_editing_task(
            article_content=str(article_output),
            technical_seo_report=str(technical_output),
            brand_guidelines=brand_guidelines,
            quality_standards=quality_standards
        )
        
        editing_crew = Crew(
            agents=[self.editor_agent.agent],
            tasks=[editing_task],
            verbose=True,
            process=Process.sequential
        )
        
        final_output = editing_crew.kickoff()
        results["outputs"]["final_article"] = str(final_output)
        print(f"\n✅ Editorial review complete: {len(str(final_output))} characters\n")
        
        # Status tracking: mark as generated → pending_review
        if STATUS_AVAILABLE and status_record_id:
            try:
                status_svc = get_status_service()
                final_content = results["outputs"].get("final_article", "")
                status_svc.update_content(
                    status_record_id,
                    content_preview=final_content[:500] if final_content else None,
                    metadata={
                        "target_keyword": target_keyword,
                        "final_article_length": len(final_content),
                        "stages_completed": list(results["outputs"].keys()),
                    },
                )
                status_svc.transition(status_record_id, "generated", "seo_robot")
                status_svc.transition(status_record_id, "pending_review", "seo_robot")
                results["status_record_id"] = status_record_id
                print(f"📊 Status tracking: marked as pending_review")
            except Exception as e:
                print(f"⚠ Status tracking completion failed (non-critical): {e}")

        # Summary
        print("\n" + "="*60)
        print("CONTENT GENERATION COMPLETE")
        print("="*60)
        print(f"End Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"\nOutputs generated:")
        print(f"  ✅ Research Analysis: {len(results['outputs']['research'])} chars")
        print(f"  ✅ Content Strategy: {len(results['outputs']['strategy'])} chars")
        print(f"  ✅ Article Draft: {len(results['outputs']['article'])} chars")
        print(f"  ✅ Technical SEO: {len(results['outputs']['technical_seo'])} chars")
        print(f"  ✅ Marketing Strategy: {len(results['outputs']['marketing_strategy'])} chars")
        print(f"  ✅ Final Article: {len(results['outputs']['final_article'])} chars")
        print("="*60 + "\n")

        return results
    
    def save_results(self, results: Dict[str, Any], output_dir: str = "output"):
        """
        Save all results to files.
        
        Args:
            results: Results dictionary from generate_content
            output_dir: Output directory path
        """
        import os
        from pathlib import Path
        
        # Create output directory
        Path(output_dir).mkdir(parents=True, exist_ok=True)
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        keyword_slug = results["input"]["target_keyword"].lower().replace(" ", "-")
        
        # Save each output
        for stage, content in results["outputs"].items():
            filename = f"{timestamp}_{keyword_slug}_{stage}.md"
            filepath = os.path.join(output_dir, filename)
            
            with open(filepath, "w", encoding="utf-8") as f:
                f.write(f"# {stage.upper()}\n\n")
                f.write(f"**Keyword:** {results['input']['target_keyword']}\n")
                f.write(f"**Generated:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
                f.write("-" * 60 + "\n\n")
                f.write(content)
            
            print(f"  📄 Saved: {filename}")
        
        print(f"\n✅ All results saved to {output_dir}/")


# Convenience function for quick usage
def generate_seo_article(
    keyword: str,
    competitors: Optional[List[str]] = None,
    word_count: int = 2500
) -> Dict[str, Any]:
    """
    Quick function to generate SEO article with all agents.
    
    Args:
        keyword: Target keyword
        competitors: Competitor domains
        word_count: Target word count
        
    Returns:
        Complete results from all agents
    """
    crew = SEOContentCrew()
    return crew.generate_content(
        target_keyword=keyword,
        competitor_domains=competitors,
        word_count=word_count
    )


if __name__ == "__main__":
    # Example: Generate complete SEO article
    print("=== SEO Content Crew - Full Pipeline Test ===\n")
    
    results = generate_seo_article(
        keyword="content marketing strategy",
        competitors=["hubspot.com", "contentmarketinginstitute.com"],
        word_count=2500
    )
    
    # Save results
    crew = SEOContentCrew()
    crew.save_results(results, output_dir="output/seo_content")
    
    print("\n=== PIPELINE TEST COMPLETE ===")
