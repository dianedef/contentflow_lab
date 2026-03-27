from crewai import Agent, Task
from langchain.tools import tool
import networkx as nx
import matplotlib.pyplot as plt
import spacy

class SEOTopicAgent:
    def __init__(self):
        self.topic_graph = nx.Graph()
        # Load SpaCy NLP model for text processing
        try:
            self.nlp = spacy.load("en_core_web_lg")
        except OSError:
            # Download model if not available
            from spacy.cli import download
            download("en_core_web_lg")
            self.nlp = spacy.load("en_core_web_lg")
        
    @tool
    def analyze_topical_flow(self, content: str) -> dict:
        """Analyzes topical flow progression using NLP"""
        doc = self.nlp(content)
        
        # Extract sentences and entities
        sentences = [sent.text for sent in doc.sents]
        entities = {ent.text: ent.label_ for ent in doc.ents}
        
        # Calculate topic diversity
        unique_entities = set(entities.keys())
        diversity_score = len(unique_entities) / max(1, len(sentences))
        
        return {
            "flow_score": diversity_score,
            "transitions": len(sentences),
            "entities": entities,
            "sentences": sentences
        }
    
    @tool
    def generate_topic_mesh(self, topics: list) -> str:
        """Creates topic mesh visualization"""
        self.topic_graph.add_nodes_from(topics)
        
        # Create relationships between topics
        for i in range(len(topics)):
            for j in range(i+1, len(topics)):
                if topics[i][0] == topics[j][0]:  # Simple relationship heuristic
                    self.topic_graph.add_edge(topics[i], topics[j], weight=0.8)
        
        # Generate visualization
        plt.figure(figsize=(10, 8))
        pos = nx.spring_layout(self.topic_graph)
        nx.draw(self.topic_graph, pos, with_labels=True, node_size=2000)
        plt.savefig('/tmp/topic_mesh.png')
        return "Topic mesh visualization saved to /tmp/topic_mesh.png"
    
    @tool
    def identify_content_gaps(self, content: str, competitors: list) -> list:
        """Identifies content gaps compared to competitors"""
        # Implementation would analyze content vs competitors
        return ["Topic A coverage", "Topic B depth", "Topic C recency"]
    
    @tool
    def map_entity_relationships(self, content: str) -> dict:
        """Maps semantic relationships between entities using dependency parsing"""
        doc = self.nlp(content)
        
        # Extract entities and their dependencies
        entity_relations = []
        for token in doc:
            if token.dep_ in ("attr", "dobj", "nsubj", "prep"):
                # Get subject-verb-object relationships
                subject = token.head.text
                relation = token.dep_
                obj = token.text
                entity_relations.append(f"{subject} → {relation} → {obj}")
        
        # Group entities by type
        entities = {}
        for ent in doc.ents:
            entities.setdefault(ent.label_, []).append(ent.text)
        
        return {
            "entities": entities,
            "relationships": entity_relations
        }

# CrewAI agent setup
topic_agent = Agent(
    role='SEO Topic Analyst',
    goal='Analyze and optimize topical flow and mesh architecture',
    backstory='Expert in semantic SEO and content architecture',
    tools=[
        SEOTopicAgent().analyze_topical_flow,
        SEOTopicAgent().generate_topic_mesh,
        SEOTopicAgent().identify_content_gaps,
        SEOTopicAgent().map_entity_relationships
    ]
)

# Example task
topic_task = Task(
    description='Analyze topical flow and create mesh for AI content strategy',
    agent=topic_agent,
    expected_output='Topic mesh visualization and gap analysis report'
)