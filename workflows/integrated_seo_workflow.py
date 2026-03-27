"""
Integration complète: Advertools + STORM + CrewAI

Pipeline SEO optimisé pour générer du contenu avec recherche de keywords,
deep research STORM, et génération d'articles avec topical mesh.
"""

import os
from pathlib import Path
from typing import List, Dict, Optional
import json
from datetime import datetime

# Import our SEO tools
import sys
sys.path.append(str(Path(__file__).parent.parent))

from agents.seo_research_tools import SEOResearchTools, EnhancedResearchAnalyst


class IntegratedSEOWorkflow:
    """
    Workflow complet: Advertools → STORM → Content Generation
    
    Pipeline:
    1. Advertools: Keyword research + competitor analysis
    2. STORM: Deep research avec citations (optionnel)
    3. Content brief generation avec topical mesh
    """
    
    def __init__(self, output_dir: str = "./output/seo_campaigns"):
        """
        Initialize integrated workflow
        
        Args:
            output_dir: Directory pour sauvegarder les campagnes
        """
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        # Initialize tools
        self.seo_tools = SEOResearchTools()
        self.analyst = EnhancedResearchAnalyst()
        
        print("🚀 Integrated SEO Workflow initialized")
        print(f"   Output: {self.output_dir}")
    
    def run_campaign(
        self,
        topic: str,
        generate_variations: bool = True,
        max_keywords: int = 50,
        create_brief: bool = True
    ) -> Dict:
        """
        Execute complete SEO campaign
        
        Args:
            topic: Le topic principal
            generate_variations: Générer variations de keywords
            max_keywords: Nombre max de keywords à générer
            create_brief: Créer le content brief
        
        Returns:
            Dict avec résultats complets de la campagne
        """
        campaign_name = topic.replace(' ', '_').lower()
        campaign_dir = self.output_dir / campaign_name
        campaign_dir.mkdir(exist_ok=True)
        
        print(f"\n{'='*70}")
        print(f"🎯 STARTING SEO CAMPAIGN: {topic}")
        print(f"{'='*70}\n")
        
        results = {
            'topic': topic,
            'campaign_dir': str(campaign_dir),
            'timestamp': datetime.now().isoformat(),
            'keywords': [],
            'variations': {},
            'articles': [],
            'status': 'started'
        }
        
        # Phase 1: Keyword Research (Advertools)
        print("📝 PHASE 1: KEYWORD RESEARCH")
        print("-" * 70)
        
        seed_keywords = topic.lower().split()[:3]
        
        keywords = self.seo_tools.generate_keywords(
            seed_keywords=seed_keywords,
            max_len=2,
            save=True
        )
        
        # Limiter le nombre de keywords
        keywords = keywords[:max_keywords]
        results['keywords'] = keywords
        
        print(f"✅ Generated {len(keywords)} keywords\n")
        
        # Phase 2: Keyword Variations
        if generate_variations:
            print("📝 PHASE 2: KEYWORD VARIATIONS")
            print("-" * 70)
            
            variations = self.seo_tools.generate_keyword_variations(
                base_keyword=topic,
                include_questions=True,
                include_modifiers=True
            )
            
            results['variations'] = variations
            print(f"✅ Generated variations\n")
        
        # Phase 3: Content Brief Generation
        if create_brief:
            print("📝 PHASE 3: CONTENT BRIEF GENERATION")
            print("-" * 70)
            
            brief = self._generate_content_brief(
                topic=topic,
                keywords=keywords[:20],
                variations=results.get('variations', {})
            )
            
            # Save brief
            brief_file = campaign_dir / 'content_brief.json'
            with open(brief_file, 'w') as f:
                json.dump(brief, f, indent=2)
            
            results['content_brief_file'] = str(brief_file)
            
            print(f"✅ Content brief saved to: {brief_file}\n")
        
        # Save campaign results
        results_file = campaign_dir / 'campaign_results.json'
        with open(results_file, 'w') as f:
            json.dump(results, f, indent=2)
        
        # Summary
        results['status'] = 'completed'
        
        print(f"\n{'='*70}")
        print(f"✅ CAMPAIGN COMPLETED: {topic}")
        print(f"{'='*70}")
        print(f"📊 Summary:")
        print(f"   Keywords generated: {len(results['keywords'])}")
        if 'variations' in results:
            print(f"   Question keywords: {len(results['variations'].get('questions', []))}")
            print(f"   Modifier keywords: {len(results['variations'].get('modifiers', []))}")
        print(f"   Output directory: {campaign_dir}")
        print(f"   Results saved: {results_file}")
        print(f"\n💡 Next steps:")
        print(f"   1. Review content brief: {results.get('content_brief_file', 'N/A')}")
        print(f"   2. Use keywords for STORM research")
        print(f"   3. Generate articles with CrewAI")
        print(f"   4. Implement topical mesh structure")
        print()
        
        return results
    
    def _generate_content_brief(
        self,
        topic: str,
        keywords: List[str],
        variations: Dict
    ) -> Dict:
        """
        Generate comprehensive content brief
        
        Args:
            topic: Main topic
            keywords: List of keywords
            variations: Keyword variations
        
        Returns:
            Complete content brief dict
        """
        brief = {
            'campaign': {
                'topic': topic,
                'date_created': datetime.now().isoformat(),
                'status': 'ready'
            },
            'keywords': {
                'primary': keywords[:5],
                'secondary': keywords[5:20] if len(keywords) > 5 else [],
                'long_tail': keywords[20:] if len(keywords) > 20 else [],
                'total': len(keywords)
            },
            'content_structure': {
                'pillar_article': {
                    'title': f"Complete Guide to {topic}",
                    'target_length': 7500,
                    'keywords': keywords[:10],
                    'sections': self._generate_sections(topic, variations)
                },
                'cluster_articles': [
                    {
                        'title': q,
                        'target_length': 2000,
                        'type': 'question',
                        'pillar_link': True
                    }
                    for q in variations.get('questions', [])[:5]
                ]
            },
            'seo_optimization': {
                'answer_block': f"Create a 60-word answer block explaining {topic} for AI Overview optimization (GEO)",
                'meta_title': f"{topic} - Complete Guide 2026",
                'meta_description': f"Everything you need to know about {topic}. Expert guide with {len(keywords)} keywords researched.",
                'target_keywords': keywords[:5],
                'internal_linking': 'topical_mesh_strategy',
                'schema_types': ['Article', 'HowTo', 'FAQ']
            },
            'topical_mesh': {
                'pillar_topic': topic,
                'cluster_topics': variations.get('questions', [])[:5],
                'supporting_topics': variations.get('modifiers', [])[:10],
                'internal_link_strategy': 'hub_and_spoke',
                'recommended_structure': {
                    '1_pillar': f"/{topic.lower().replace(' ', '-')}",
                    '2_clusters': [
                        f"/{topic.lower().replace(' ', '-')}/{q.lower().replace(' ', '-')[:50]}"
                        for q in variations.get('questions', [])[:5]
                    ]
                }
            },
            'next_steps': {
                '1_storm_research': 'Use STORM framework for deep research with citations',
                '2_crewai_generation': 'Generate articles with 6-agent CrewAI pipeline',
                '3_e_e_a_t': 'Add expertise signals, author bios, citations',
                '4_schema': 'Implement Article, FAQ, and HowTo schema',
                '5_internal_links': 'Connect articles in topical mesh structure'
            }
        }
        
        return brief
    
    def _generate_sections(self, topic: str, variations: Dict) -> List[Dict]:
        """
        Generate article sections based on keyword variations
        
        Args:
            topic: Main topic
            variations: Keyword variations
        
        Returns:
            List of section structures
        """
        sections = [
            {
                'h2': f"What is {topic}?",
                'type': 'introduction',
                'keywords': ['definition', 'overview', 'basics'],
                'target_length': 500,
                'include_answer_block': True
            },
            {
                'h2': f"Why {topic} Matters in 2026",
                'type': 'importance',
                'keywords': ['benefits', 'importance', 'trends', '2026'],
                'target_length': 700
            },
            {
                'h2': f"How {topic} Works",
                'type': 'explanation',
                'keywords': ['process', 'how to', 'steps'],
                'target_length': 1000
            }
        ]
        
        # Add sections from question keywords
        for question in variations.get('questions', [])[:3]:
            sections.append({
                'h2': question.title(),
                'type': 'question',
                'keywords': question.split()[:3],
                'target_length': 800
            })
        
        # Best practices section
        sections.append({
            'h2': f"Best {topic} Practices",
            'type': 'best_practices',
            'keywords': ['best', 'tips', 'strategies'],
            'target_length': 1200
        })
        
        # Tools/Resources section
        sections.append({
            'h2': f"Top {topic} Tools and Resources",
            'type': 'resources',
            'keywords': ['tools', 'software', 'platforms'],
            'target_length': 900
        })
        
        # FAQ section
        sections.append({
            'h2': f"Frequently Asked Questions",
            'type': 'faq',
            'keywords': ['faq', 'questions', 'answers'],
            'target_length': 600,
            'schema': 'FAQPage'
        })
        
        # Conclusion
        sections.append({
            'h2': 'Conclusion and Next Steps',
            'type': 'conclusion',
            'keywords': ['summary', 'next steps', 'action'],
            'target_length': 400
        })
        
        return sections


# Quick test/demo function
def run_demo_campaign():
    """
    Demo campaign pour tester le workflow
    """
    print("🧪 DEMO: Running sample SEO campaign\n")
    
    workflow = IntegratedSEOWorkflow()
    
    # Run campaign
    results = workflow.run_campaign(
        topic="AI Content Marketing Automation",
        generate_variations=True,
        max_keywords=30,
        create_brief=True
    )
    
    print("\n" + "="*70)
    print("📊 DEMO COMPLETED - RESULTS SUMMARY")
    print("="*70)
    print(json.dumps({
        'topic': results['topic'],
        'keywords_count': len(results['keywords']),
        'variations_count': len(results.get('variations', {}).get('all', [])),
        'output_dir': results['campaign_dir'],
        'content_brief': results.get('content_brief_file', 'N/A'),
        'status': results['status'],
        'timestamp': results['timestamp']
    }, indent=2))
    
    print("\n✅ Check output in:", results['campaign_dir'])
    print()
    
    return results


if __name__ == "__main__":
    # Run demo
    run_demo_campaign()
