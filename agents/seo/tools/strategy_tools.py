"""
Content Strategy Tools for Content Strategist Agent
Tools for building topic clusters, generating outlines, optimizing topical flow, and planning calendars.
Includes topical mesh builder for French SEO methodology (Cocon Sémantique).
"""
from typing import Dict, List, Any, Optional, Tuple
from crewai.tools import tool
from datetime import datetime, timedelta
import json
import hashlib

try:
    import networkx as nx
    import matplotlib
    matplotlib.use('Agg')  # Non-interactive backend
    import matplotlib.pyplot as plt
    NETWORKX_AVAILABLE = True
except ImportError:
    NETWORKX_AVAILABLE = False
    print("Warning: NetworkX/Matplotlib not available. Topical mesh visualization disabled.")

try:
    import spacy
    SPACY_AVAILABLE = True
except ImportError:
    SPACY_AVAILABLE = False
    print("Warning: SpaCy not available. Entity extraction disabled.")


class TopicClusterBuilder:
    """Build topic clusters with pillar pages and supporting content."""

    def build_topic_cluster(
        self,
        pillar_topic: str,
        keyword_list: Optional[List[str]] = None,
        depth: int = 3
    ) -> Dict[str, Any]:
        """
        Build a topic cluster structure with pillar and supporting topics.
        
        Args:
            pillar_topic: Main pillar page topic
            keyword_list: Related keywords to cluster
            depth: Depth of cluster hierarchy (default: 3 levels)
            
        Returns:
            Dictionary with cluster structure and relationships
        """
        # Simulate topic clustering (in production, would use semantic analysis)
        cluster = {
            "pillar_topic": pillar_topic,
            "pillar_page": {
                "title": f"Complete Guide to {pillar_topic}",
                "target_keywords": [pillar_topic] + (keyword_list[:3] if keyword_list else []),
                "estimated_word_count": 3500,
                "content_type": "Comprehensive Guide"
            },
            "cluster_topics": [],
            "relationships": [],
            "topical_coverage": 0.0
        }
        
        # Generate cluster topics based on common content patterns
        if "marketing" in pillar_topic.lower():
            cluster["cluster_topics"] = [
                {
                    "title": f"{pillar_topic} Strategy Framework",
                    "intent": "Informational",
                    "depth_level": 1,
                    "estimated_word_count": 2000,
                    "relationship_to_pillar": "Strategic foundation"
                },
                {
                    "title": f"Best {pillar_topic} Tools and Software",
                    "intent": "Commercial",
                    "depth_level": 1,
                    "estimated_word_count": 2500,
                    "relationship_to_pillar": "Implementation tools"
                },
                {
                    "title": f"How to Implement {pillar_topic}",
                    "intent": "Informational/Transactional",
                    "depth_level": 2,
                    "estimated_word_count": 1800,
                    "relationship_to_pillar": "Tactical execution"
                },
                {
                    "title": f"{pillar_topic} Metrics and KPIs",
                    "intent": "Informational",
                    "depth_level": 2,
                    "estimated_word_count": 1500,
                    "relationship_to_pillar": "Performance measurement"
                },
                {
                    "title": f"{pillar_topic} Examples and Case Studies",
                    "intent": "Informational",
                    "depth_level": 3,
                    "estimated_word_count": 2200,
                    "relationship_to_pillar": "Proof and inspiration"
                }
            ]
        else:
            # Generic cluster structure
            cluster["cluster_topics"] = [
                {
                    "title": f"Introduction to {pillar_topic}",
                    "intent": "Informational",
                    "depth_level": 1,
                    "estimated_word_count": 1500,
                    "relationship_to_pillar": "Foundation concepts"
                },
                {
                    "title": f"{pillar_topic} Best Practices",
                    "intent": "Informational",
                    "depth_level": 2,
                    "estimated_word_count": 2000,
                    "relationship_to_pillar": "Implementation guidance"
                },
                {
                    "title": f"Common {pillar_topic} Mistakes to Avoid",
                    "intent": "Informational",
                    "depth_level": 2,
                    "estimated_word_count": 1800,
                    "relationship_to_pillar": "Problem prevention"
                },
                {
                    "title": f"Advanced {pillar_topic} Techniques",
                    "intent": "Informational",
                    "depth_level": 3,
                    "estimated_word_count": 2500,
                    "relationship_to_pillar": "Expert-level content"
                }
            ]
        
        # Calculate relationships
        cluster["relationships"] = [
            {
                "from": "pillar_page",
                "to": topic["title"],
                "link_type": "contextual_internal",
                "strength": "high" if topic["depth_level"] == 1 else "medium"
            }
            for topic in cluster["cluster_topics"]
        ]
        
        # Estimate topical coverage
        cluster["topical_coverage"] = min(len(cluster["cluster_topics"]) * 0.15, 1.0)
        
        cluster["recommendations"] = [
            "Link pillar page to all cluster topics in first 500 words",
            "Ensure cluster topics link back to pillar with relevant anchor text",
            "Create internal links between related cluster topics",
            f"Target minimum {len(cluster['cluster_topics'])} supporting articles for complete coverage"
        ]
        
        return cluster


class OutlineGenerator:
    """Generate detailed content outlines."""

    def generate_outline(
        self,
        topic: str,
        content_type: str = "blog_post",
        target_word_count: int = 2000,
        search_intent: str = "informational"
    ) -> Dict[str, Any]:
        """
        Generate a detailed content outline.
        
        Args:
            topic: Content topic
            content_type: Type of content (blog_post, guide, listicle, etc.)
            target_word_count: Target word count
            search_intent: Search intent (informational, commercial, transactional, navigational)
            
        Returns:
            Dictionary with structured outline
        """
        outline = {
            "topic": topic,
            "content_type": content_type,
            "target_word_count": target_word_count,
            "search_intent": search_intent,
            "structure": {
                "introduction": {
                    "word_count": int(target_word_count * 0.1),
                    "key_elements": [
                        "Hook that addresses reader pain point",
                        "Brief overview of what will be covered",
                        "Value proposition (what reader will learn)",
                        "Target keyword in first 100 words"
                    ]
                },
                "main_sections": [],
                "conclusion": {
                    "word_count": int(target_word_count * 0.08),
                    "key_elements": [
                        "Recap main points",
                        "Call to action",
                        "Next steps or related resources"
                    ]
                }
            },
            "seo_elements": {
                "title_tag": f"{topic} - Complete Guide",
                "meta_description": f"Learn everything about {topic}. Comprehensive guide with examples and best practices.",
                "target_keywords": [topic],
                "h1": f"The Complete Guide to {topic}",
                "internal_linking_opportunities": 3
            }
        }
        
        # Generate main sections based on content type
        sections_count = max(3, min(7, target_word_count // 400))
        words_per_section = int((target_word_count * 0.82) / sections_count)
        
        if content_type == "guide":
            outline["structure"]["main_sections"] = [
                {
                    "heading": f"What is {topic}?",
                    "h_level": "h2",
                    "word_count": words_per_section,
                    "subsections": [
                        {"heading": "Definition and key concepts", "h_level": "h3"},
                        {"heading": "Why it matters", "h_level": "h3"}
                    ]
                },
                {
                    "heading": f"How {topic} Works",
                    "h_level": "h2",
                    "word_count": words_per_section,
                    "subsections": [
                        {"heading": "Core principles", "h_level": "h3"},
                        {"heading": "Step-by-step process", "h_level": "h3"}
                    ]
                },
                {
                    "heading": f"Benefits of {topic}",
                    "h_level": "h2",
                    "word_count": words_per_section,
                    "subsections": [
                        {"heading": "Key advantages", "h_level": "h3"},
                        {"heading": "Real-world impact", "h_level": "h3"}
                    ]
                },
                {
                    "heading": f"Best Practices for {topic}",
                    "h_level": "h2",
                    "word_count": words_per_section,
                    "subsections": [
                        {"heading": "Getting started", "h_level": "h3"},
                        {"heading": "Advanced techniques", "h_level": "h3"}
                    ]
                },
                {
                    "heading": f"Common Challenges with {topic}",
                    "h_level": "h2",
                    "word_count": words_per_section,
                    "subsections": [
                        {"heading": "Typical obstacles", "h_level": "h3"},
                        {"heading": "How to overcome them", "h_level": "h3"}
                    ]
                }
            ]
        elif content_type == "listicle":
            outline["structure"]["main_sections"] = [
                {
                    "heading": f"{i+1}. {topic} Point {i+1}",
                    "h_level": "h2",
                    "word_count": words_per_section,
                    "subsections": []
                }
                for i in range(sections_count)
            ]
        else:  # Default blog post
            outline["structure"]["main_sections"] = [
                {
                    "heading": f"Section {i+1}: Key Aspect of {topic}",
                    "h_level": "h2",
                    "word_count": words_per_section,
                    "subsections": [
                        {"heading": "Detailed explanation", "h_level": "h3"}
                    ]
                }
                for i in range(sections_count)
            ]
        
        outline["writing_guidelines"] = [
            "Use conversational but professional tone",
            "Include examples and case studies where relevant",
            "Add data and statistics to support claims",
            "Use bullet points for easy scanning",
            "Include images/diagrams for visual sections",
            f"Target readability: 8th grade level (Flesch-Kincaid)",
            "Add internal links to related content (2-3 minimum)",
            "Include FAQ section if appropriate for search intent"
        ]
        
        return outline


class TopicalFlowOptimizer:
    """Optimize topical flow and content progression."""

    def optimize_topical_flow(
        self,
        content_pieces: List[Dict[str, str]],
        user_journey: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Optimize topical flow across content pieces.
        
        Args:
            content_pieces: List of content pieces with titles and topics
            user_journey: User journey stage (awareness, consideration, decision)
            
        Returns:
            Optimized flow with linking strategy
        """
        flow = {
            "content_count": len(content_pieces),
            "user_journey": user_journey or "awareness",
            "flow_structure": [],
            "internal_linking_map": [],
            "topical_depth_score": 0.0,
            "recommendations": []
        }
        
        # Organize content by depth level
        awareness_content = []
        consideration_content = []
        decision_content = []
        
        for piece in content_pieces:
            title = piece.get("title", "")
            if any(word in title.lower() for word in ["what is", "introduction", "guide", "basics"]):
                awareness_content.append(piece)
            elif any(word in title.lower() for word in ["how to", "best practices", "tips", "strategy"]):
                consideration_content.append(piece)
            elif any(word in title.lower() for word in ["vs", "comparison", "review", "tools"]):
                decision_content.append(piece)
            else:
                awareness_content.append(piece)
        
        # Build flow structure
        if awareness_content:
            flow["flow_structure"].append({
                "stage": "Awareness",
                "content": awareness_content,
                "purpose": "Introduce concepts and build understanding"
            })
        
        if consideration_content:
            flow["flow_structure"].append({
                "stage": "Consideration",
                "content": consideration_content,
                "purpose": "Provide actionable guidance and strategies"
            })
        
        if decision_content:
            flow["flow_structure"].append({
                "stage": "Decision",
                "content": decision_content,
                "purpose": "Help with tool selection and implementation"
            })
        
        # Create internal linking map
        for i, stage in enumerate(flow["flow_structure"]):
            for content in stage["content"]:
                # Link to next stage content
                if i < len(flow["flow_structure"]) - 1:
                    next_stage = flow["flow_structure"][i + 1]
                    if next_stage["content"]:
                        flow["internal_linking_map"].append({
                            "from": content.get("title"),
                            "to": next_stage["content"][0].get("title"),
                            "context": f"Link from {stage['stage']} to {next_stage['stage']}",
                            "anchor_text_suggestion": f"Learn more about [specific topic]"
                        })
        
        # Calculate topical depth score
        flow["topical_depth_score"] = min(
            (len(awareness_content) * 0.3 + 
             len(consideration_content) * 0.5 + 
             len(decision_content) * 0.2) / 5,
            1.0
        )
        
        flow["recommendations"] = [
            "Create pillar content linking to all cluster pieces",
            "Ensure each cluster piece links back to pillar",
            "Add contextual links between related cluster content",
            f"Current topical depth: {flow['topical_depth_score']:.0%} - aim for 80%+",
            "Consider adding FAQ content for featured snippet opportunities"
        ]
        
        return flow


class EditorialCalendarPlanner:
    """Plan editorial calendar and publication schedule."""

    def plan_editorial_calendar(
        self,
        content_pieces: List[Dict[str, Any]],
        start_date: Optional[str] = None,
        frequency: str = "weekly",
        priority_keywords: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """
        Create an editorial calendar with publication schedule.
        
        Args:
            content_pieces: List of content to schedule
            start_date: Start date (YYYY-MM-DD) or None for today
            frequency: Publishing frequency (daily, weekly, biweekly, monthly)
            priority_keywords: Keywords to prioritize
            
        Returns:
            Editorial calendar with scheduled dates and priorities
        """
        if start_date:
            current_date = datetime.strptime(start_date, "%Y-%m-%d")
        else:
            current_date = datetime.now()
        
        # Define frequency intervals
        intervals = {
            "daily": timedelta(days=1),
            "weekly": timedelta(weeks=1),
            "biweekly": timedelta(weeks=2),
            "monthly": timedelta(days=30)
        }
        interval = intervals.get(frequency, timedelta(weeks=1))
        
        calendar = {
            "start_date": current_date.strftime("%Y-%m-%d"),
            "frequency": frequency,
            "total_pieces": len(content_pieces),
            "estimated_completion": (current_date + interval * len(content_pieces)).strftime("%Y-%m-%d"),
            "schedule": [],
            "milestones": []
        }
        
        # Prioritize content
        prioritized_content = sorted(
            content_pieces,
            key=lambda x: self._calculate_priority(x, priority_keywords),
            reverse=True
        )
        
        # Schedule content
        for i, piece in enumerate(prioritized_content):
            publish_date = current_date + (interval * i)
            
            calendar["schedule"].append({
                "date": publish_date.strftime("%Y-%m-%d"),
                "week": publish_date.strftime("Week %U"),
                "title": piece.get("title", f"Content Piece {i+1}"),
                "priority": self._get_priority_label(
                    self._calculate_priority(piece, priority_keywords)
                ),
                "estimated_word_count": piece.get("estimated_word_count", 2000),
                "content_type": piece.get("content_type", "blog_post"),
                "status": "scheduled"
            })
        
        # Add milestones
        quarter_point = len(prioritized_content) // 4
        calendar["milestones"] = [
            {
                "date": (current_date + interval * quarter_point).strftime("%Y-%m-%d"),
                "milestone": "25% Content Complete",
                "description": "First quarter of content published"
            },
            {
                "date": (current_date + interval * (quarter_point * 2)).strftime("%Y-%m-%d"),
                "milestone": "50% Content Complete",
                "description": "Half of content strategy executed"
            },
            {
                "date": (current_date + interval * (quarter_point * 3)).strftime("%Y-%m-%d"),
                "milestone": "75% Content Complete",
                "description": "Three quarters complete - assess performance"
            },
            {
                "date": (current_date + interval * len(prioritized_content)).strftime("%Y-%m-%d"),
                "milestone": "Content Strategy Complete",
                "description": "All planned content published - begin performance review"
            }
        ]
        
        calendar["recommendations"] = [
            f"Publish {frequency} to maintain consistent presence",
            "Monitor performance after first 25% and adjust strategy if needed",
            "Prioritize high-value keywords first for quick wins",
            "Update existing content alongside new content creation",
            "Track rankings and traffic for each published piece"
        ]
        
        return calendar
    
    def _calculate_priority(self, piece: Dict[str, Any], priority_keywords: Optional[List[str]]) -> float:
        """Calculate content priority score."""
        score = 0.5  # Base score
        
        # Boost for priority keywords
        if priority_keywords:
            title = piece.get("title", "").lower()
            if any(kw.lower() in title for kw in priority_keywords):
                score += 0.3
        
        # Boost for pillar content
        if piece.get("content_type") == "pillar" or "guide" in piece.get("title", "").lower():
            score += 0.2
        
        # Adjust by depth level
        depth = piece.get("depth_level", 2)
        if depth == 1:
            score += 0.1
        
        return min(score, 1.0)
    
    def _get_priority_label(self, score: float) -> str:
        """Convert priority score to label."""
        if score >= 0.8:
            return "High"
        elif score >= 0.5:
            return "Medium"
        else:
            return "Low"


class TopicalMeshBuilder:
    """
    Build and visualize topical mesh architecture (French SEO Cocon Sémantique method).
    
    Creates semantic cocoon structures with:
    - Pillar pages (page mère)
    - Cluster pages (pages filles)
    - Strategic internal linking
    - Authority flow optimization
    - Visual NetworkX graph representations
    """
    
    def __init__(self):
        """Initialize topical mesh builder."""
        self.graph = None
        if NETWORKX_AVAILABLE:
            self.graph = nx.DiGraph()  # Directed graph for authority flow
        
        self.nlp = None
        if SPACY_AVAILABLE:
            try:
                self.nlp = spacy.load("en_core_web_sm")
            except OSError:
                print("Warning: SpaCy model 'en_core_web_sm' not found. Entity extraction disabled.")
    
    def build_semantic_cocoon(
        self,
        main_topic: str,
        subtopics: List[str],
        business_goals: Optional[List[str]] = None,
        existing_content: Optional[List[Dict[str, str]]] = None
    ) -> Dict[str, Any]:
        """
        Create semantic cocoon (cocon sémantique) structure.
        
        Args:
            main_topic: Central pillar topic
            subtopics: Related cluster topics
            business_goals: Business objectives (e.g., ["rank", "convert", "inform"])
            existing_content: List of existing pages with titles and URLs
            
        Returns:
            Complete mesh structure with pillar, clusters, linking strategy
        """
        if not NETWORKX_AVAILABLE:
            return self._build_simple_cocoon(main_topic, subtopics)
        
        # Initialize graph
        self.graph.clear()
        
        # Create pillar page (center of mesh)
        pillar_id = self._create_page_id(main_topic)
        self.graph.add_node(
            pillar_id,
            title=f"Complete Guide to {main_topic}",
            type="pillar",
            topic=main_topic,
            authority_goal=business_goals[0] if business_goals else "rank",
            word_count=3500,
            priority=1.0
        )
        
        # Create cluster pages
        cluster_nodes = []
        for i, subtopic in enumerate(subtopics[:10]):  # Limit to 10 clusters
            cluster_id = self._create_page_id(subtopic)
            goal = business_goals[i % len(business_goals)] if business_goals else "inform"
            
            self.graph.add_node(
                cluster_id,
                title=subtopic,
                type="cluster",
                topic=subtopic,
                authority_goal=goal,
                word_count=2000,
                priority=0.7 - (i * 0.05)  # Decreasing priority
            )
            cluster_nodes.append(cluster_id)
            
            # Link cluster to pillar (authority flows up)
            self.graph.add_edge(
                cluster_id,
                pillar_id,
                anchor=main_topic,
                weight=0.8,
                link_type="topical"
            )
            
            # Link pillar to cluster (contextual)
            self.graph.add_edge(
                pillar_id,
                cluster_id,
                anchor=subtopic,
                weight=0.6,
                link_type="contextual"
            )
        
        # Add cross-linking between related clusters (creates mesh density)
        for i, cluster_a in enumerate(cluster_nodes):
            for j, cluster_b in enumerate(cluster_nodes[i+1:i+3]):  # Link to 2 nearest neighbors
                if cluster_a != cluster_b:
                    self.graph.add_edge(
                        cluster_a,
                        cluster_b,
                        anchor="related topic",
                        weight=0.4,
                        link_type="supporting"
                    )
        
        # Calculate PageRank (authority distribution)
        pagerank = nx.pagerank(self.graph, weight='weight')
        
        # Build mesh structure
        mesh_structure = {
            "main_topic": main_topic,
            "pillar_page": {
                "id": pillar_id,
                "title": self.graph.nodes[pillar_id]['title'],
                "type": "pillar",
                "authority_score": round(pagerank[pillar_id] * 100, 2),
                "word_count": 3500,
                "outbound_links": len(list(self.graph.successors(pillar_id))),
                "inbound_links": len(list(self.graph.predecessors(pillar_id)))
            },
            "cluster_pages": [],
            "total_pages": len(self.graph.nodes),
            "total_links": len(self.graph.edges),
            "mesh_density": round(nx.density(self.graph), 3),
            "average_authority": round(sum(pagerank.values()) / len(pagerank) * 100, 2)
        }
        
        # Add cluster page details
        for cluster_id in cluster_nodes:
            node_data = self.graph.nodes[cluster_id]
            mesh_structure["cluster_pages"].append({
                "id": cluster_id,
                "title": node_data['title'],
                "type": "cluster",
                "authority_score": round(pagerank[cluster_id] * 100, 2),
                "word_count": node_data['word_count'],
                "outbound_links": len(list(self.graph.successors(cluster_id))),
                "inbound_links": len(list(self.graph.predecessors(cluster_id))),
                "authority_goal": node_data['authority_goal']
            })
        
        return mesh_structure
    
    def _build_simple_cocoon(self, main_topic: str, subtopics: List[str]) -> Dict[str, Any]:
        """Fallback mesh structure when NetworkX unavailable."""
        return {
            "main_topic": main_topic,
            "pillar_page": {
                "id": "pillar_1",
                "title": f"Complete Guide to {main_topic}",
                "type": "pillar",
                "authority_score": 85.0,
                "word_count": 3500,
                "outbound_links": len(subtopics[:10]),
                "inbound_links": len(subtopics[:10])
            },
            "cluster_pages": [
                {
                    "id": f"cluster_{i+1}",
                    "title": subtopic,
                    "type": "cluster",
                    "authority_score": 60.0 - (i * 3),
                    "word_count": 2000,
                    "outbound_links": 2,  # To pillar + 1 other cluster
                    "inbound_links": 2,   # From pillar + 1 other cluster
                    "authority_goal": ["rank", "convert", "inform"][i % 3]
                }
                for i, subtopic in enumerate(subtopics[:10])
            ],
            "total_pages": 1 + len(subtopics[:10]),
            "total_links": len(subtopics[:10]) * 2,  # Bidirectional
            "mesh_density": 0.45,
            "average_authority": 70.0,
            "note": "Simplified structure (NetworkX not available)"
        }
    
    def calculate_topical_authority(
        self,
        mesh_structure: Dict[str, Any],
        content_inventory: Optional[List[Dict]] = None
    ) -> float:
        """
        Calculate topical authority score (0-100).
        
        Based on:
        - Mesh density (internal linking)
        - Content depth (word counts)
        - Content breadth (topic coverage)
        - Entity coverage (semantic richness)
        
        Args:
            mesh_structure: Output from build_semantic_cocoon
            content_inventory: Optional existing content for analysis
            
        Returns:
            Authority score 0-100
        """
        score = 0.0
        
        # Mesh density (0-30 points)
        density = mesh_structure.get("mesh_density", 0)
        score += min(density * 60, 30)
        
        # Content depth (0-25 points)
        total_pages = mesh_structure.get("total_pages", 0)
        if total_pages >= 10:
            score += 25
        elif total_pages >= 5:
            score += 20
        elif total_pages >= 3:
            score += 15
        else:
            score += total_pages * 5
        
        # Content breadth (0-25 points)
        pillar = mesh_structure.get("pillar_page", {})
        clusters = mesh_structure.get("cluster_pages", [])
        
        avg_word_count = (pillar.get("word_count", 0) + 
                         sum(c.get("word_count", 0) for c in clusters)) / (1 + len(clusters))
        
        if avg_word_count >= 2500:
            score += 25
        elif avg_word_count >= 2000:
            score += 20
        elif avg_word_count >= 1500:
            score += 15
        else:
            score += (avg_word_count / 1500) * 15
        
        # Internal linking (0-20 points)
        total_links = mesh_structure.get("total_links", 0)
        if total_links >= 20:
            score += 20
        else:
            score += (total_links / 20) * 20
        
        return min(round(score, 1), 100.0)
    
    def generate_mesh_visualization(
        self,
        mesh_structure: Dict[str, Any],
        output_path: str = "topical_mesh.png",
        output_format: str = "png"
    ) -> str:
        """
        Generate visual representation of topical mesh.
        
        Args:
            mesh_structure: Output from build_semantic_cocoon
            output_path: File path for output
            output_format: "png", "svg", "json", or "mermaid"
            
        Returns:
            Path to generated file or visualization string
        """
        if not NETWORKX_AVAILABLE or self.graph is None:
            return self._generate_text_visualization(mesh_structure)
        
        if output_format == "mermaid":
            return self._generate_mermaid_diagram(mesh_structure)
        elif output_format == "json":
            return json.dumps(nx.node_link_data(self.graph), indent=2)
        
        # Generate NetworkX visualization (png/svg)
        try:
            plt.figure(figsize=(14, 10))
            
            # Calculate layout
            pos = nx.spring_layout(self.graph, k=2, iterations=50, seed=42)
            
            # Separate pillar and cluster nodes
            pillar_nodes = [n for n, d in self.graph.nodes(data=True) if d.get('type') == 'pillar']
            cluster_nodes = [n for n, d in self.graph.nodes(data=True) if d.get('type') == 'cluster']
            
            # Draw edges with varying thickness
            edges = self.graph.edges(data=True)
            weights = [e[2].get('weight', 0.5) for e in edges]
            
            nx.draw_networkx_edges(
                self.graph, pos,
                width=[w * 2 for w in weights],
                alpha=0.4,
                edge_color='gray',
                arrows=True,
                arrowsize=15
            )
            
            # Draw pillar nodes (larger, red)
            nx.draw_networkx_nodes(
                self.graph, pos,
                nodelist=pillar_nodes,
                node_color='#FF6B6B',
                node_size=2000,
                alpha=0.9
            )
            
            # Draw cluster nodes (smaller, blue)
            nx.draw_networkx_nodes(
                self.graph, pos,
                nodelist=cluster_nodes,
                node_color='#4ECDC4',
                node_size=1000,
                alpha=0.8
            )
            
            # Draw labels
            labels = {n: d.get('topic', n)[:30] for n, d in self.graph.nodes(data=True)}
            nx.draw_networkx_labels(
                self.graph, pos,
                labels,
                font_size=8,
                font_weight='bold'
            )
            
            plt.title(
                f"Topical Mesh: {mesh_structure['main_topic']}\n"
                f"Authority Score: {self.calculate_topical_authority(mesh_structure)}/100",
                fontsize=16,
                fontweight='bold'
            )
            plt.axis('off')
            plt.tight_layout()
            
            # Save
            plt.savefig(output_path, format=output_format, dpi=150, bbox_inches='tight')
            plt.close()
            
            return output_path
            
        except Exception as e:
            return f"Visualization error: {str(e)}\n{self._generate_text_visualization(mesh_structure)}"
    
    def _generate_text_visualization(self, mesh_structure: Dict[str, Any]) -> str:
        """Generate text-based mesh visualization."""
        viz = f"\n🕸️ TOPICAL MESH: {mesh_structure['main_topic']}\n"
        viz += "=" * 60 + "\n\n"
        
        pillar = mesh_structure.get("pillar_page", {})
        viz += f"📌 PILLAR PAGE (Authority: {pillar.get('authority_score', 0)}/100)\n"
        viz += f"   {pillar.get('title', 'Untitled')}\n"
        viz += f"   └─ {pillar.get('word_count', 0)} words\n\n"
        
        viz += "🔗 CLUSTER PAGES:\n"
        for i, cluster in enumerate(mesh_structure.get("cluster_pages", [])[:5], 1):
            viz += f"   {i}. {cluster.get('title', 'Untitled')} "
            viz += f"(Authority: {cluster.get('authority_score', 0)}/100)\n"
        
        viz += f"\n📊 MESH STATS:\n"
        viz += f"   • Total Pages: {mesh_structure.get('total_pages', 0)}\n"
        viz += f"   • Internal Links: {mesh_structure.get('total_links', 0)}\n"
        viz += f"   • Mesh Density: {mesh_structure.get('mesh_density', 0)}\n"
        viz += f"   • Overall Authority: {self.calculate_topical_authority(mesh_structure)}/100\n"
        
        return viz
    
    def _generate_mermaid_diagram(self, mesh_structure: Dict[str, Any]) -> str:
        """Generate Mermaid.js diagram syntax."""
        mermaid = "graph TD\n"
        
        pillar = mesh_structure.get("pillar_page", {})
        pillar_id = "P1"
        mermaid += f"    {pillar_id}[\"{pillar.get('title', 'Pillar')}\"]\n"
        mermaid += f"    style {pillar_id} fill:#FF6B6B,stroke:#333,stroke-width:3px\n\n"
        
        for i, cluster in enumerate(mesh_structure.get("cluster_pages", []), 1):
            cluster_id = f"C{i}"
            mermaid += f"    {cluster_id}[\"{cluster.get('title', 'Cluster')}\"]\n"
            mermaid += f"    {cluster_id} --> {pillar_id}\n"
            mermaid += f"    {pillar_id} --> {cluster_id}\n"
        
        mermaid += f"\n    style P1 fill:#FF6B6B,stroke:#333,stroke-width:3px\n"
        
        return mermaid
    
    def optimize_internal_linking(
        self,
        mesh_structure: Dict[str, Any],
        authority_goals: Optional[Dict[str, str]] = None
    ) -> List[Dict[str, Any]]:
        """
        Design strategic internal linking for PageRank flow.
        
        Args:
            mesh_structure: Output from build_semantic_cocoon
            authority_goals: Page goals {"page_id": "rank"|"convert"|"inform"}
            
        Returns:
            List of linking recommendations with priority
        """
        recommendations = []
        
        pillar = mesh_structure.get("pillar_page", {})
        clusters = mesh_structure.get("cluster_pages", [])
        
        # Primary strategy: All clusters link to pillar
        for cluster in clusters:
            recommendations.append({
                "from_page": cluster.get("title", ""),
                "to_page": pillar.get("title", ""),
                "anchor_text": mesh_structure["main_topic"],
                "link_type": "topical_authority",
                "priority": "HIGH",
                "reason": "Cluster → Pillar (authority flow)",
                "position": "Introduction or Conclusion"
            })
        
        # Secondary strategy: Pillar links to all clusters
        for cluster in clusters:
            recommendations.append({
                "from_page": pillar.get("title", ""),
                "to_page": cluster.get("title", ""),
                "anchor_text": cluster.get("title", "")[:50],
                "link_type": "contextual",
                "priority": "MEDIUM",
                "reason": "Pillar → Cluster (user navigation)",
                "position": "Relevant section"
            })
        
        # Tertiary strategy: Cross-link related clusters
        for i, cluster_a in enumerate(clusters):
            for cluster_b in clusters[i+1:i+3]:  # Link to 2 neighbors
                if cluster_a != cluster_b:
                    recommendations.append({
                        "from_page": cluster_a.get("title", ""),
                        "to_page": cluster_b.get("title", ""),
                        "anchor_text": "related topic",
                        "link_type": "supporting",
                        "priority": "LOW",
                        "reason": "Cluster cross-linking (mesh density)",
                        "position": "Related content section"
                    })
        
        return recommendations[:20]  # Return top 20 recommendations
    
    def _create_page_id(self, title: str) -> str:
        """Create unique page ID from title."""
        return hashlib.md5(title.lower().encode()).hexdigest()[:8]
