"""
Agent tools package.
All tools for the SEO multi-agent system.
"""

# Research tools
from agents.seo.tools.research_tools import (
    SERPAnalyzer,
    TrendMonitor,
    KeywordGapFinder,
    RankingPatternExtractor
)

# Strategy tools
from agents.seo.tools.strategy_tools import (
    TopicClusterBuilder,
    OutlineGenerator,
    TopicalFlowOptimizer,
    EditorialCalendarPlanner,
    TopicalMeshBuilder
)

# Mesh analysis tools
from agents.seo.tools.mesh_analyzer import (
    ExistingMeshAnalyzer
)

# Repository analysis tools
from agents.seo.tools.repo_analyzer import (
    GitHubRepoAnalyzer
)

# Local-first link validation
from agents.seo.tools.local_link_checker import (
    LocalLinkChecker
)

# Writing tools
from agents.seo.tools.writing_tools import (
    ContentWriter,
    MetadataGenerator,
    KeywordIntegrator,
    ToneAdapter
)

# Technical tools
from agents.seo.tools.technical_tools import (
    SchemaGenerator,
    MetadataValidator,
    InternalLinkingAnalyzer,
    OnPageOptimizer
)

# Marketing tools
from agents.seo.tools.marketing_tools import (
    PrioritizationMatrix,
    ROIAnalyzer,
    CompetitivePositioning,
    MarketingValidator
)

# Editing tools
from agents.seo.tools.editing_tools import (
    QualityChecker,
    ConsistencyValidator,
    MarkdownFormatter,
    PublicationPreparer
)

__all__ = [
    # Research
    'SERPAnalyzer',
    'TrendMonitor',
    'KeywordGapFinder',
    'RankingPatternExtractor',
    # Strategy
    'TopicClusterBuilder',
    'OutlineGenerator',
    'TopicalFlowOptimizer',
    'EditorialCalendarPlanner',
    'TopicalMeshBuilder',
    # Mesh Analysis
    'ExistingMeshAnalyzer',
    'GitHubRepoAnalyzer',
    'LocalLinkChecker',
    # Writing
    'ContentWriter',
    'MetadataGenerator',
    'KeywordIntegrator',
    'ToneAdapter',
    # Technical
    'SchemaGenerator',
    'MetadataValidator',
    'InternalLinkingAnalyzer',
    'OnPageOptimizer',
    # Marketing
    'PrioritizationMatrix',
    'ROIAnalyzer',
    'CompetitivePositioning',
    'MarketingValidator',
    # Editing
    'QualityChecker',
    'ConsistencyValidator',
    'MarkdownFormatter',
    'PublicationPreparer',
]
