"""
Configuration for Research Analyst Agent.
"""

# Groq LLM Models
GROQ_MODELS = {
    "fast": "mixtral-8x7b-32768",  # Fast, good for most tasks
    "powerful": "llama2-70b-4096",  # More powerful, slower
    "balanced": "mixtral-8x7b-32768"  # Default
}

# DataForSEO API Settings
DFS_CONFIG = {
    "default_location": "us",       # Country code: us, fr, uk, de, ca, au
    "default_language": "en",       # Language code: en, fr, de, es
    "serp_depth": 10,               # Number of SERP results
    "max_keywords_per_analysis": 10,
    "keyword_limit": 1000,          # Max keywords per overview call
    "trends_time_range": "past_12_months",
    "domain_intersection_limit": 100,
    "competitor_analysis_depth": 10,
}

# Trend Monitoring Settings
TREND_CONFIG = {
    "default_time_period": "12m",
    "min_trend_score": 60.0,
    "min_confidence": 0.7,
    "max_keywords_to_monitor": 20
}

# Keyword Gap Settings
GAP_CONFIG = {
    "min_opportunity_score": 3.0,
    "max_keyword_difficulty": 80.0,
    "min_search_volume": 100,
    "priority_keywords_limit": 10
}

# Ranking Pattern Settings
PATTERN_CONFIG = {
    "word_count_variance": 0.3,  # ±30% of average
    "min_success_probability": 0.3,
    "content_length_multiplier": 1.1  # Aim for 10% above average
}

# Quality Thresholds
QUALITY_THRESHOLDS = {
    "min_relevance_score": 0.85,
    "min_data_completeness": 0.80,
    "max_analysis_time_minutes": 5
}

# AI Tool Settings
AI_TOOL_SETTINGS = {
    "use_consensus_ai": False
}

# Content Type Mapping
CONTENT_TYPES = {
    "Informational": ["guide", "tutorial", "blog"],
    "Commercial": ["comparison", "review", "listicle"],
    "Transactional": ["tool", "calculator", "template"],
    "Navigational": ["landing-page", "product-page"]
}

# Schema Recommendations
SCHEMA_TYPES = {
    "guide": ["HowTo", "Article"],
    "tutorial": ["HowTo", "VideoObject"],
    "comparison": ["Review", "Product"],
    "review": ["Review", "AggregateRating"],
    "blog": ["BlogPosting", "Article"],
    "tool": ["SoftwareApplication", "WebApplication"]
}
