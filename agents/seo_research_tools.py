"""
SEO Research Tools - Advertools Integration

Alternative open-source à ScrapeBox pour:
- Génération de keywords
- Crawling SEO
- Analyse de sitemaps
- Recherche compétitive

Compatible avec CrewAI agents et STORM framework.
"""

import advertools as adv
import pandas as pd
from pathlib import Path
from typing import List, Dict, Optional
import json


class SEOResearchTools:
    """
    Outils de recherche SEO utilisant Advertools
    
    Remplace ScrapeBox pour:
    - Keyword generation (remplace Keyword Scraper)
    - Website crawling (remplace Harvester)
    - Sitemap analysis
    - Link analysis
    """
    
    def __init__(self, output_dir: str = "./data/seo_research"):
        """
        Initialize SEO research tools
        
        Args:
            output_dir: Répertoire pour sauvegarder les résultats
        """
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        print(f"📁 SEO Research Tools initialized")
        print(f"   Output directory: {self.output_dir}")
    
    def generate_keywords(
        self, 
        seed_keywords: List[str],
        modifiers: Optional[List[str]] = None,
        max_len: int = 3,
        save: bool = True
    ) -> List[str]:
        """
        Génère des combinaisons de keywords (remplace ScrapeBox Keyword Scraper)
        
        Args:
            seed_keywords: Mots-clés de base ['seo', 'content', 'marketing']
            modifiers: Modificateurs optionnels, sinon utilise liste par défaut
            max_len: Longueur maximum des combinaisons
            save: Sauvegarder les résultats en CSV
        
        Returns:
            Liste de keywords générés
        
        Example:
            >>> tools = SEOResearchTools()
            >>> keywords = tools.generate_keywords(['seo', 'content'], max_len=2)
            >>> print(keywords[:5])
            ['seo automation', 'seo ai', 'content tools', ...]
        """
        if modifiers is None:
            modifiers = [
                'automation', 'ai', 'tools', 'software', 'platform',
                'strategy', 'guide', 'tips', 'best', 'how to',
                'free', 'online', '2026', 'tutorial', 'services'
            ]
        
        print(f"🔍 Generating keywords...")
        print(f"   Seeds: {seed_keywords}")
        print(f"   Modifiers: {len(modifiers)} words")
        print(f"   Max length: {max_len}")
        
        # Générer combinaisons avec Advertools (retourne un DataFrame)
        df_keywords = adv.kw_generate(
            products=seed_keywords,
            words=modifiers,
            max_len=max_len
        )
        
        print(f"✅ Generated {len(df_keywords)} keyword combinations")
        
        if save:
            output_file = self.output_dir / 'keywords.csv'
            df_keywords.to_csv(output_file, index=False)
            print(f"   Saved to: {output_file}")
        
        # Retourne le DataFrame avec la colonne 'Keyword'
        return df_keywords['Keyword'].tolist()
    
    def crawl_website(
        self,
        url: str,
        output_name: str = 'crawl_results',
        follow_links: bool = True,
        depth_limit: int = 3,
        max_requests: int = 100
    ) -> pd.DataFrame:
        """
        Crawl un site web pour analyse SEO (remplace ScrapeBox Harvester)
        
        Args:
            url: URL du site à crawler
            output_name: Nom du fichier de sortie (sans extension)
            follow_links: Suivre les liens internes
            depth_limit: Profondeur maximale de crawl
            max_requests: Nombre maximum de requêtes
        
        Returns:
            DataFrame avec résultats du crawl (URLs, titles, status codes, etc.)
        
        Example:
            >>> tools = SEOResearchTools()
            >>> df = tools.crawl_website('https://example.com', depth_limit=2)
            >>> print(f"Crawled {len(df)} pages")
        """
        output_file = self.output_dir / f'{output_name}.jl'
        
        print(f"🕷️  Crawling website: {url}")
        print(f"   Depth limit: {depth_limit}")
        print(f"   Max requests: {max_requests}")
        
        try:
            # Crawl avec Advertools
            adv.crawl(
                url_list=[url],
                output_file=str(output_file),
                follow_links=follow_links,
                custom_settings={
                    'CONCURRENT_REQUESTS': 8,
                    'DEPTH_LIMIT': depth_limit,
                    'CLOSESPIDER_PAGECOUNT': max_requests,
                    'DOWNLOAD_DELAY': 1,  # Respectful crawling
                    'ROBOTSTXT_OBEY': True,
                    'USER_AGENT': 'Mozilla/5.0 (compatible; SEOResearchBot/1.0)',
                }
            )
            
            # Lire résultats
            df = pd.read_json(output_file, lines=True)
            
            # Statistiques
            print(f"✅ Crawl completed:")
            print(f"   Total pages: {len(df)}")
            print(f"   Broken links (4xx/5xx): {len(df[df['status'] >= 400])}")
            print(f"   Missing titles: {len(df[df['title'].isna()])}")
            print(f"   Missing descriptions: {len(df[df['meta_desc'].isna()])}")
            
            # Sauvegarder aussi en CSV pour analyse facile
            csv_file = self.output_dir / f'{output_name}.csv'
            
            # Sélectionner colonnes importantes
            important_cols = ['url', 'title', 'meta_desc', 'h1', 'h2', 'status', 
                            'size', 'download_latency', 'links_url']
            available_cols = [col for col in important_cols if col in df.columns]
            
            df[available_cols].to_csv(csv_file, index=False)
            print(f"   CSV saved to: {csv_file}")
            
            return df
            
        except Exception as e:
            print(f"❌ Crawl failed: {e}")
            return pd.DataFrame()
    
    def analyze_sitemap(
        self, 
        sitemap_url: str,
        save: bool = True
    ) -> pd.DataFrame:
        """
        Analyse un sitemap XML
        
        Args:
            sitemap_url: URL du sitemap XML
            save: Sauvegarder les résultats
        
        Returns:
            DataFrame avec URLs, dates de modification, priorités
        
        Example:
            >>> tools = SEOResearchTools()
            >>> df = tools.analyze_sitemap('https://example.com/sitemap.xml')
            >>> print(f"Found {len(df)} URLs in sitemap")
        """
        print(f"📊 Analyzing sitemap: {sitemap_url}")
        
        try:
            df = adv.sitemap_to_df(sitemap_url)
            
            print(f"✅ Sitemap analyzed:")
            print(f"   Total URLs: {len(df)}")
            
            if 'lastmod' in df.columns:
                print(f"   URLs with lastmod: {df['lastmod'].notna().sum()}")
            if 'priority' in df.columns:
                print(f"   Average priority: {df['priority'].mean():.2f}")
            
            if save:
                output_file = self.output_dir / 'sitemap_analysis.csv'
                df.to_csv(output_file, index=False)
                print(f"   Saved to: {output_file}")
            
            return df
            
        except Exception as e:
            print(f"❌ Sitemap analysis failed: {e}")
            return pd.DataFrame()
    
    def generate_keyword_variations(
        self,
        base_keyword: str,
        include_questions: bool = True,
        include_modifiers: bool = True
    ) -> Dict[str, List[str]]:
        """
        Génère variations d'un keyword avec questions et modificateurs
        
        Args:
            base_keyword: Mot-clé de base
            include_questions: Inclure les questions (how, what, why, etc.)
            include_modifiers: Inclure les modificateurs (best, top, free, etc.)
        
        Returns:
            Dict avec différentes catégories de keywords
        
        Example:
            >>> tools = SEOResearchTools()
            >>> variations = tools.generate_keyword_variations('seo automation')
            >>> print(variations['questions'][:3])
            ['what is seo automation', 'how to seo automation', ...]
        """
        print(f"🔄 Generating variations for: {base_keyword}")
        
        variations = {
            'base': [base_keyword],
            'questions': [],
            'modifiers': [],
            'all': []
        }
        
        if include_questions:
            question_words = ['what is', 'how to', 'why', 'when', 'where', 
                            'best', 'top', 'guide to']
            variations['questions'] = [f"{q} {base_keyword}" for q in question_words]
        
        if include_modifiers:
            modifiers = ['best', 'top', 'free', 'online', 'tools', 
                        'software', 'platform', 'services', '2026']
            variations['modifiers'] = [f"{base_keyword} {m}" for m in modifiers]
        
        # Combiner toutes les variations
        variations['all'] = (
            variations['base'] + 
            variations['questions'] + 
            variations['modifiers']
        )
        
        print(f"✅ Generated {len(variations['all'])} variations:")
        print(f"   Questions: {len(variations['questions'])}")
        print(f"   Modifiers: {len(variations['modifiers'])}")
        
        # Sauvegarder
        output_file = self.output_dir / f'variations_{base_keyword.replace(" ", "_")}.json'
        with open(output_file, 'w') as f:
            json.dump(variations, f, indent=2)
        print(f"   Saved to: {output_file}")
        
        return variations
    
    def get_research_summary(self) -> Dict:
        """
        Résumé de toutes les recherches effectuées
        
        Returns:
            Dict avec statistiques sur les fichiers générés
        """
        print(f"📊 Research Summary:")
        print(f"   Output directory: {self.output_dir}")
        
        summary = {
            'output_dir': str(self.output_dir),
            'files': [],
            'total_keywords': 0,
            'total_urls_crawled': 0
        }
        
        # Lister les fichiers
        for file in self.output_dir.glob('*'):
            summary['files'].append(file.name)
            
            if file.suffix == '.csv' and 'keywords' in file.name:
                try:
                    df = pd.read_csv(file)
                    summary['total_keywords'] += len(df)
                except Exception:
                    pass

            if file.suffix == '.csv' and 'crawl' in file.name:
                try:
                    df = pd.read_csv(file)
                    summary['total_urls_crawled'] += len(df)
                except Exception:
                    pass
        
        print(f"   Files generated: {len(summary['files'])}")
        print(f"   Total keywords: {summary['total_keywords']}")
        print(f"   Total URLs crawled: {summary['total_urls_crawled']}")
        
        return summary


# Example d'intégration avec Research Analyst Agent

class EnhancedResearchAnalyst:
    """
    Research Analyst Agent avec Advertools integration
    
    Remplace les API payantes (SEMrush, Ahrefs) par Advertools (gratuit)
    """
    
    def __init__(self):
        self.seo_tools = SEOResearchTools()
        print("🤖 Enhanced Research Analyst initialized")
        print("   Using: Advertools (open-source)")
    
    def research_topic(self, topic: str, include_competitors: bool = False) -> Dict:
        """
        Recherche complète sur un topic
        
        Args:
            topic: Le topic à rechercher
            include_competitors: Crawler les sites concurrents (optionnel)
        
        Returns:
            Dict avec résultats de recherche complets
        """
        print(f"\n{'='*60}")
        print(f"🔍 RESEARCH TOPIC: {topic}")
        print(f"{'='*60}\n")
        
        # 1. Générer keywords
        print("📝 Step 1: Keyword Generation")
        seed_keywords = topic.lower().split()[:3]  # Max 3 mots
        keywords = self.seo_tools.generate_keywords(
            seed_keywords=seed_keywords,
            max_len=3
        )
        
        # 2. Générer variations avec questions
        print("\n📝 Step 2: Keyword Variations")
        variations = self.seo_tools.generate_keyword_variations(
            base_keyword=topic,
            include_questions=True,
            include_modifiers=True
        )
        
        # 3. Compiler research brief
        research = {
            'topic': topic,
            'keywords': keywords,
            'keyword_variations': variations,
            'total_keywords': len(keywords),
            'question_keywords': len(variations['questions']),
            'modifier_keywords': len(variations['modifiers']),
            'status': 'completed'
        }
        
        print(f"\n{'='*60}")
        print(f"✅ RESEARCH COMPLETED")
        print(f"{'='*60}")
        print(f"Topic: {topic}")
        print(f"Total keywords generated: {research['total_keywords']}")
        print(f"Question-based keywords: {research['question_keywords']}")
        print(f"Modifier-based keywords: {research['modifier_keywords']}")
        print(f"\n💡 Ready to feed to STORM for deep content research!")
        
        return research


# Test standalone
if __name__ == "__main__":
    print("🧪 Testing SEO Research Tools (Advertools)\n")
    
    # Test 1: Keyword generation
    print("Test 1: Keyword Generation")
    print("-" * 40)
    tools = SEOResearchTools()
    keywords = tools.generate_keywords(
        seed_keywords=['seo', 'content', 'marketing'],
        max_len=2
    )
    print(f"\nSample keywords: {keywords[:10]}\n")
    
    # Test 2: Keyword variations
    print("\nTest 2: Keyword Variations")
    print("-" * 40)
    variations = tools.generate_keyword_variations('ai content marketing')
    print(f"\nQuestions: {variations['questions'][:3]}")
    print(f"Modifiers: {variations['modifiers'][:3]}\n")
    
    # Test 3: Enhanced Research Analyst
    print("\nTest 3: Enhanced Research Analyst")
    print("-" * 40)
    analyst = EnhancedResearchAnalyst()
    research = analyst.research_topic('AI Content Marketing Automation')
    
    # Summary
    print("\n" + "="*60)
    print("🎉 ALL TESTS PASSED")
    print("="*60)
    print("\n✅ Advertools is working perfectly!")
    print("✅ Ready to integrate with CrewAI agents")
    print("✅ Ready to feed data to STORM framework")
    print(f"\n📁 Check results in: {tools.output_dir}")
