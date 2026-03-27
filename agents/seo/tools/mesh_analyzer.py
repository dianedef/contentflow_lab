"""
Existing Mesh Analyzer - Audit and Improve Current Website Topical Structure
Connects GitHubRepoAnalyzer with TopicalMeshBuilder to analyze existing content.

This bridges the gap between:
- GitHubRepoAnalyzer: Extracts existing content and links
- TopicalMeshBuilder: Builds and scores mesh structures
- TopicalMeshArchitect: Orchestrates analysis and recommendations
"""
from typing import Dict, List, Any, Optional, Tuple
from pathlib import Path
import re
from collections import defaultdict

from agents.seo.tools.repo_analyzer import GitHubRepoAnalyzer
from agents.seo.tools.strategy_tools import TopicalMeshBuilder


class ExistingMeshAnalyzer:
    """
    Analyze existing website content as a topical mesh.
    
    Takes real content from a website/repo and:
    1. Identifies existing topical structure
    2. Calculates current mesh authority
    3. Finds weaknesses (orphans, gaps, weak links)
    4. Suggests specific improvements
    5. Predicts impact of changes
    """
    
    def __init__(self, workspace_dir: Optional[str] = None):
        """
        Initialize analyzer with repo and mesh tools.
        
        Args:
            workspace_dir: Directory for cloning repos (default: ./data/repos)
        """
        self.repo_analyzer = GitHubRepoAnalyzer(workspace_dir)
        self.mesh_builder = TopicalMeshBuilder()
    
    def analyze_existing_website(
        self,
        repo_url: str,
        local_repo_path: Optional[str] = None,
        github_token: Optional[str] = None,
        force_update: bool = True,
    ) -> Dict[str, Any]:
        """
        Complete analysis of existing website as topical mesh.

        Args:
            repo_url: GitHub repository URL
            local_repo_path: Optional explicit local path (skips git clone)
            force_update: Pull latest changes when repo already on disk (default: True)

        Returns:
            Complete mesh analysis with current state and recommendations
        """
        # Step 1: Resolve repo — cached workspace first, clone only on first run
        print(f"\n📥 Analyzing existing website: {repo_url}")
        repo_path = self.repo_analyzer.clone_or_update_repo(
            repo_url,
            local_repo_path=local_repo_path,
            github_token=github_token,
            force_update=force_update,
        )
        
        # Step 2: Extract site structure
        print("🔍 Extracting site structure...")
        site_structure = self.repo_analyzer.analyze_site_structure(repo_path)
        
        # Step 3: Get content inventory
        print("📄 Building content inventory...")
        content_files = self.repo_analyzer.find_all_content_files(
            repo_path,
            extensions=['.md', '.mdx', '.html', '.astro'],
            max_files=50  # Limit to 50 files for faster analysis
        )
        
        # Step 4: Map internal links
        print("🔗 Mapping internal links...")
        link_map = self.repo_analyzer.map_internal_links(repo_path, content_files)
        
        # Step 5: Convert to mesh structure
        print("🕸️  Building mesh from existing content...")
        existing_mesh = self._build_mesh_from_content(
            content_files=content_files,
            link_map=link_map,
            site_structure=site_structure
        )
        
        # Step 6: Calculate current authority
        print("📊 Calculating topical authority...")
        authority_score = self.mesh_builder.calculate_topical_authority(existing_mesh)
        existing_mesh['topical_authority_score'] = authority_score
        
        # Step 7: Find issues
        print("🚨 Identifying issues...")
        issues = self._find_mesh_issues(existing_mesh, link_map)
        
        # Step 8: Generate recommendations
        print("💡 Generating recommendations...")
        recommendations = self._generate_recommendations(existing_mesh, issues)
        
        # Step 9: Calculate improvement potential
        improvement_plan = self._create_improvement_plan(
            existing_mesh,
            issues,
            recommendations
        )
        
        print("✅ Analysis complete!")
        
        return {
            "repo_url": repo_url,
            "existing_mesh": existing_mesh,
            "authority_score": authority_score,
            "authority_grade": self._get_grade(authority_score),
            "issues": issues,
            "recommendations": recommendations,
            "improvement_plan": improvement_plan,
            "content_summary": {
                "total_pages": existing_mesh.get("total_pages", 0),
                "total_links": existing_mesh.get("total_links", 0),
                "mesh_density": existing_mesh.get("mesh_density", 0),
                "orphan_pages": len(issues.get("orphans", []))
            }
        }
    
    def _build_mesh_from_content(
        self,
        content_files: List[Path],
        link_map: Dict[str, List[str]],
        site_structure: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Convert existing content into mesh structure.
        
        Identifies:
        - Pillar pages (most links, longest content, central topic)
        - Cluster pages (linked to pillar, supporting content)
        - Orphan pages (no links)
        """
        # Build page inventory
        pages = []
        for file_path in content_files:
            page_data = self._extract_page_data(file_path, link_map)
            pages.append(page_data)
        
        if not pages:
            return self._empty_mesh()
        
        # Sort by authority indicators (inbound links + word count)
        pages.sort(
            key=lambda p: (p['inbound_links'] * 10) + (p['word_count'] / 100),
            reverse=True
        )
        
        # Identify pillar (top page by authority)
        pillar = pages[0]
        pillar['type'] = 'pillar'
        
        # Identify clusters (pages that link to pillar)
        clusters = []
        orphans = []
        
        pillar_url = pillar['url']
        for page in pages[1:]:
            # Check if this page links to pillar
            outbound = link_map.get(page['file_path'], [])
            if pillar_url in outbound or any(pillar_url in link for link in outbound):
                page['type'] = 'cluster'
                clusters.append(page)
            elif page['inbound_links'] == 0 and page['outbound_links'] == 0:
                page['type'] = 'orphan'
                orphans.append(page)
            else:
                page['type'] = 'cluster'  # Has some links, consider it a cluster
                clusters.append(page)
        
        # Calculate basic authority scores
        pillar['authority_score'] = min(85 + (pillar['inbound_links'] * 2), 100)
        
        for i, cluster in enumerate(clusters):
            base_score = 60 - (i * 2)
            link_bonus = cluster['inbound_links'] * 3
            cluster['authority_score'] = min(base_score + link_bonus, 90)
        
        for orphan in orphans:
            orphan['authority_score'] = 0
        
        # Calculate mesh density
        total_pages = len(pages)
        total_links = sum(p['outbound_links'] for p in pages)
        possible_links = total_pages * (total_pages - 1)
        mesh_density = total_links / possible_links if possible_links > 0 else 0
        
        # Extract main topic from pillar
        main_topic = pillar.get('title', 'Unknown Topic')
        
        return {
            "main_topic": main_topic,
            "pillar_page": pillar,
            "cluster_pages": clusters,
            "orphan_pages": orphans,
            "total_pages": total_pages,
            "total_links": total_links,
            "mesh_density": round(mesh_density, 3),
            "average_authority": round(sum(p['authority_score'] for p in pages) / total_pages, 1)
        }
    
    def _extract_page_data(
        self,
        file_path: Path,
        link_map: Dict[str, List[str]]
    ) -> Dict[str, Any]:
        """Extract data for a single page."""
        # Read file
        try:
            content = file_path.read_text(encoding='utf-8', errors='ignore')
        except Exception:
            content = ""
        
        # Extract title (from frontmatter or first heading)
        title = self._extract_title(content, file_path)
        
        # Count words (approximate)
        words = len(re.findall(r'\w+', content))
        
        # Get URL path
        url = str(file_path.stem)
        
        # Count links
        file_str = str(file_path)
        outbound = link_map.get(file_str, [])
        inbound = sum(1 for links in link_map.values() if file_str in links)
        
        return {
            "id": file_path.stem,
            "file_path": file_str,
            "url": url,
            "title": title,
            "word_count": words,
            "outbound_links": len(outbound),
            "inbound_links": inbound,
            "outbound_to": outbound,
            "authority_score": 0  # Calculated later
        }
    
    def _extract_title(self, content: str, file_path: Path) -> str:
        """Extract title from content or filename."""
        # Try frontmatter
        frontmatter_match = re.search(r'^---\s*\ntitle:\s*["\']?(.+?)["\']?\s*\n', content, re.MULTILINE)
        if frontmatter_match:
            return frontmatter_match.group(1)
        
        # Try first H1
        h1_match = re.search(r'^#\s+(.+)$', content, re.MULTILINE)
        if h1_match:
            return h1_match.group(1)
        
        # Use filename
        return file_path.stem.replace('-', ' ').replace('_', ' ').title()
    
    def _find_mesh_issues(
        self,
        mesh: Dict[str, Any],
        link_map: Dict[str, List[str]]
    ) -> Dict[str, Any]:
        """Identify issues in existing mesh."""
        issues = {
            "orphans": [],
            "weak_pillar": False,
            "low_density": False,
            "weak_clusters": [],
            "missing_cross_links": [],
            "severity_counts": {"high": 0, "medium": 0, "low": 0}
        }
        
        # Check for orphan pages
        orphans = mesh.get("orphan_pages", [])
        if orphans:
            issues["orphans"] = orphans
            issues["severity_counts"]["high"] += len(orphans)
        
        # Check pillar strength
        pillar = mesh.get("pillar_page", {})
        if pillar.get("authority_score", 0) < 70:
            issues["weak_pillar"] = True
            issues["severity_counts"]["high"] += 1
        
        # Check mesh density
        density = mesh.get("mesh_density", 0)
        if density < 0.3:
            issues["low_density"] = True
            issues["severity_counts"]["medium"] += 1
        
        # Check weak clusters
        clusters = mesh.get("cluster_pages", [])
        for cluster in clusters:
            if cluster.get("authority_score", 0) < 40:
                issues["weak_clusters"].append(cluster)
                issues["severity_counts"]["medium"] += 1
        
        # Check for missing cross-links
        # (clusters that don't link to each other)
        for i, cluster_a in enumerate(clusters):
            links_to_clusters = 0
            for cluster_b in clusters[i+1:]:
                if cluster_b["file_path"] in cluster_a.get("outbound_to", []):
                    links_to_clusters += 1
            
            if links_to_clusters == 0 and len(clusters) > 2:
                issues["missing_cross_links"].append(cluster_a["title"])
                issues["severity_counts"]["low"] += 1
        
        return issues
    
    def _generate_recommendations(
        self,
        mesh: Dict[str, Any],
        issues: Dict[str, Any]
    ) -> List[Dict[str, str]]:
        """Generate specific recommendations."""
        recommendations = []
        
        # Fix orphan pages
        if issues["orphans"]:
            pillar = mesh["pillar_page"]
            for orphan in issues["orphans"]:
                recommendations.append({
                    "priority": "HIGH",
                    "action": f"Link orphan page to pillar",
                    "details": f"Add link from '{orphan['title']}' to '{pillar['title']}'",
                    "impact": "+10 authority points",
                    "effort": "Low (5 min)"
                })
        
        # Strengthen weak pillar
        if issues["weak_pillar"]:
            pillar = mesh["pillar_page"]
            current_words = pillar.get("word_count", 0)
            target_words = 3500
            recommendations.append({
                "priority": "HIGH",
                "action": "Strengthen pillar page",
                "details": f"Expand '{pillar['title']}' from {current_words} to {target_words} words",
                "impact": "+15 authority points",
                "effort": "High (2-3 hours)"
            })
        
        # Improve mesh density
        if issues["low_density"]:
            recommendations.append({
                "priority": "MEDIUM",
                "action": "Add cross-links between clusters",
                "details": f"Add 5-10 strategic links between related cluster pages",
                "impact": "+10 authority points",
                "effort": "Medium (1 hour)"
            })
        
        # Strengthen weak clusters
        for cluster in issues["weak_clusters"][:3]:  # Top 3
            recommendations.append({
                "priority": "MEDIUM",
                "action": f"Strengthen weak cluster",
                "details": f"Add content and links for '{cluster['title']}'",
                "impact": "+5 authority points",
                "effort": "Medium (1 hour)"
            })
        
        # Add missing cross-links
        if issues["missing_cross_links"]:
            recommendations.append({
                "priority": "LOW",
                "action": "Add cluster cross-links",
                "details": f"Link related clusters: {', '.join(issues['missing_cross_links'][:3])}",
                "impact": "+5 authority points",
                "effort": "Low (30 min)"
            })
        
        return recommendations
    
    def _create_improvement_plan(
        self,
        mesh: Dict[str, Any],
        issues: Dict[str, Any],
        recommendations: List[Dict[str, str]]
    ) -> Dict[str, Any]:
        """Create phased improvement plan with impact predictions."""
        current_authority = mesh.get("topical_authority_score", 0)
        
        # Phase 1: Quick wins (orphans, basic links)
        phase1_recs = [r for r in recommendations if r["priority"] == "HIGH" and "Low" in r["effort"]]
        phase1_impact = sum(int(re.search(r'\d+', r["impact"]).group()) for r in phase1_recs if re.search(r'\d+', r["impact"]))
        
        # Phase 2: Content improvements
        phase2_recs = [r for r in recommendations if r["priority"] in ["HIGH", "MEDIUM"] and "Medium" in r["effort"]]
        phase2_impact = sum(int(re.search(r'\d+', r["impact"]).group()) for r in phase2_recs if re.search(r'\d+', r["impact"]))
        
        # Phase 3: Optimization
        phase3_recs = [r for r in recommendations if r["priority"] == "LOW"]
        phase3_impact = sum(int(re.search(r'\d+', r["impact"]).group()) for r in phase3_recs if re.search(r'\d+', r["impact"]))
        
        return {
            "current_authority": current_authority,
            "phase1": {
                "name": "Quick Wins (Orphans & Links)",
                "duration": "1-2 hours",
                "actions": [r["action"] for r in phase1_recs],
                "impact": f"+{phase1_impact} points",
                "projected_authority": current_authority + phase1_impact
            },
            "phase2": {
                "name": "Content Strengthening",
                "duration": "1 week",
                "actions": [r["action"] for r in phase2_recs],
                "impact": f"+{phase2_impact} points",
                "projected_authority": current_authority + phase1_impact + phase2_impact
            },
            "phase3": {
                "name": "Optimization",
                "duration": "2-3 weeks",
                "actions": [r["action"] for r in phase3_recs],
                "impact": f"+{phase3_impact} points",
                "projected_authority": current_authority + phase1_impact + phase2_impact + phase3_impact
            },
            "total_improvement": phase1_impact + phase2_impact + phase3_impact,
            "final_projected_authority": current_authority + phase1_impact + phase2_impact + phase3_impact
        }
    
    def compare_with_ideal(
        self,
        existing_mesh: Dict[str, Any],
        main_topic: str,
        target_subtopics: List[str]
    ) -> Dict[str, Any]:
        """
        Compare existing mesh with ideal mesh structure.
        
        Args:
            existing_mesh: Current mesh from analyze_existing_website()
            main_topic: Main topic for ideal mesh
            target_subtopics: Desired subtopics for ideal mesh
            
        Returns:
            Comparison analysis with gaps and recommendations
        """
        # Build ideal mesh
        ideal_mesh = self.mesh_builder.build_semantic_cocoon(
            main_topic=main_topic,
            subtopics=target_subtopics,
            business_goals=["rank", "convert"]
        )
        
        ideal_authority = self.mesh_builder.calculate_topical_authority(ideal_mesh)
        current_authority = existing_mesh.get("topical_authority_score", 0)
        
        # Find gaps
        existing_topics = [existing_mesh["pillar_page"]["title"]] + \
                         [c["title"] for c in existing_mesh.get("cluster_pages", [])]
        
        ideal_topics = [ideal_mesh["pillar_page"]["title"]] + \
                      [c["title"] for c in ideal_mesh.get("cluster_pages", [])]
        
        missing_topics = [t for t in ideal_topics if not any(et.lower() in t.lower() for et in existing_topics)]
        
        return {
            "current_authority": current_authority,
            "ideal_authority": ideal_authority,
            "authority_gap": ideal_authority - current_authority,
            "current_pages": existing_mesh.get("total_pages", 0),
            "ideal_pages": ideal_mesh.get("total_pages", 0),
            "current_density": existing_mesh.get("mesh_density", 0),
            "ideal_density": ideal_mesh.get("mesh_density", 0),
            "missing_topics": missing_topics,
            "recommendation": self._get_comparison_recommendation(
                current_authority,
                ideal_authority,
                missing_topics
            )
        }
    
    def _get_comparison_recommendation(
        self,
        current: float,
        ideal: float,
        missing: List[str]
    ) -> str:
        """Generate recommendation from comparison."""
        gap = ideal - current
        
        if gap < 10:
            return f"✅ Excellent! Your mesh is close to ideal. Focus on optimization."
        elif gap < 20:
            return f"👍 Good structure. Add {len(missing)} missing topics to reach ideal."
        elif gap < 30:
            return f"⚠️ Moderate gaps. Create {len(missing)} new pages and strengthen links."
        else:
            return f"🚨 Significant improvement needed. Rebuild mesh with {len(missing)} new topics."
    
    def _empty_mesh(self) -> Dict[str, Any]:
        """Return empty mesh structure."""
        return {
            "main_topic": "Unknown",
            "pillar_page": {},
            "cluster_pages": [],
            "orphan_pages": [],
            "total_pages": 0,
            "total_links": 0,
            "mesh_density": 0,
            "average_authority": 0
        }
    
    def _get_grade(self, score: float) -> str:
        """Convert score to letter grade."""
        if score >= 85:
            return "A (Excellent)"
        elif score >= 70:
            return "B (Good)"
        elif score >= 55:
            return "C (Fair)"
        elif score >= 40:
            return "D (Poor)"
        else:
            return "F (Very Poor)"


# Convenience functions

def analyze_existing_site(repo_url: str) -> Dict[str, Any]:
    """
    Quick function to analyze existing website.
    
    Args:
        repo_url: GitHub repository URL
        
    Returns:
        Complete mesh analysis
    """
    analyzer = ExistingMeshAnalyzer()
    return analyzer.analyze_existing_website(repo_url)


def compare_current_vs_ideal(
    repo_url: str,
    main_topic: str,
    target_subtopics: List[str]
) -> Dict[str, Any]:
    """
    Compare current site with ideal mesh.
    
    Args:
        repo_url: GitHub repository URL
        main_topic: Main topic for ideal mesh
        target_subtopics: Desired subtopics
        
    Returns:
        Comparison analysis
    """
    analyzer = ExistingMeshAnalyzer()
    existing = analyzer.analyze_existing_website(repo_url)
    comparison = analyzer.compare_with_ideal(
        existing["existing_mesh"],
        main_topic,
        target_subtopics
    )
    return {
        "existing_analysis": existing,
        "comparison": comparison
    }
