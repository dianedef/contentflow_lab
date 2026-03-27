"""
Internal Linking Configuration System

Provides flexible configuration management for the Internal Linking Specialist agent
including scope settings, personalization levels, and business objective weights.
"""
from typing import Dict, Any, List, Optional
from dataclasses import dataclass, field
from enum import Enum


class ScopeSetting(str, Enum):
    """Analysis scope settings for internal linking."""
    NEW_CONTENT_ONLY = "new_content_only"
    INCLUDE_EXISTING = "include_existing"
    FULL_SITE_ANALYSIS = "full_site"


class PersonalizationLevel(str, Enum):
    """Personalization maturity levels."""
    BASIC = "basic"           # Simple segmentation
    INTERMEDIATE = "intermediate"  # Behavioral targeting
    ADVANCED = "advanced"     # Predictive personalization
    FULL = "full"             # Real-time AI personalization


@dataclass
class InternalLinkingConfiguration:
    """Configuration for internal linking specialist."""
    
    # Core Balance Settings
    new_vs_existing_split: float = 0.5  # 50% new, 50% existing
    seo_conversion_balance: float = 0.7  # 70% conversion, 30% SEO
    
    # Scope and Analysis
    analysis_scope: ScopeSetting = ScopeSetting.INCLUDE_EXISTING
    personalization_level: PersonalizationLevel = PersonalizationLevel.INTERMEDIATE
    
    # Business Objective Integration (Hybrid Approach)
    business_objective_weights: Dict[str, float] = field(default_factory=lambda: {
        "lead_generation": 0.4,
        "demo_request": 0.3,
        "trial_signup": 0.2,
        "purchase": 0.1
    })
    
    # Quality Thresholds
    min_seo_value: float = 3.0
    min_conversion_value: float = 5.0
    min_personalization_score: float = 0.6
    
    # Link Density Settings
    max_links_per_page: int = 25
    min_link_distance: int = 100  # characters between links
    
    # Anchor Text Settings
    min_anchor_words: int = 2
    max_anchor_words: int = 8
    avoid_generic_anchors: bool = True
    
    # Conversion Settings
    conversion_focus: float = 0.7  # 70% conversion focus
    enable_cta_integration: bool = True
    track_conversion_attribution: bool = True
    
    # Personalization Settings
    enable_progressive_profiling: bool = True
    enable_behavioral_targeting: bool = True
    enable_predictive_personalization: bool = False
    
    # Automation Settings
    auto_insert_links: bool = False  # Requires approval by default
    generate_reports: bool = True
    notify_on_completion: bool = True


class ConfigurationManager:
    """Manages internal linking configuration with precedence and templates."""
    
    def __init__(self):
        self.default_config = InternalLinkingConfiguration()
        self.user_configs: Dict[str, InternalLinkingConfiguration] = {}
        self.project_configs: Dict[str, InternalLinkingConfiguration] = {}
        self.session_configs: Dict[str, InternalLinkingConfiguration] = {}
    
    def get_config(
        self, 
        user_id: Optional[str] = None,
        project_id: Optional[str] = None,
        session_id: Optional[str] = None,
        custom_settings: Optional[Dict[str, Any]] = None
    ) -> InternalLinkingConfiguration:
        """
        Get configuration with appropriate precedence.
        
        Precedence order (highest to lowest):
        1. Custom settings (runtime overrides)
        2. Session config
        3. User config
        4. Project config
        5. Default config
        
        Args:
            user_id: User identifier
            project_id: Project identifier
            session_id: Session identifier
            custom_settings: Runtime configuration overrides
            
        Returns:
            Merged configuration with appropriate precedence
        """
        
        # Start with default
        config = self._copy_config(self.default_config)
        
        # Apply project config if available
        if project_id and project_id in self.project_configs:
            config = self._merge_configs(config, self.project_configs[project_id])
        
        # Apply user config if available
        if user_id and user_id in self.user_configs:
            config = self._merge_configs(config, self.user_configs[user_id])
        
        # Apply session config if available
        if session_id and session_id in self.session_configs:
            config = self._merge_configs(config, self.session_configs[session_id])
        
        # Apply custom settings
        if custom_settings:
            config = self._apply_custom_settings(config, custom_settings)
        
        return config
    
    def save_user_config(
        self,
        user_id: str,
        config: InternalLinkingConfiguration
    ) -> None:
        """Save user-specific configuration."""
        self.user_configs[user_id] = config
    
    def save_project_config(
        self,
        project_id: str,
        config: InternalLinkingConfiguration
    ) -> None:
        """Save project-specific configuration."""
        self.project_configs[project_id] = config
    
    def save_session_config(
        self,
        session_id: str,
        config: InternalLinkingConfiguration
    ) -> None:
        """Save session-specific configuration."""
        self.session_configs[session_id] = config
    
    def load_template(self, template_name: str) -> InternalLinkingConfiguration:
        """
        Load predefined configuration template.
        
        Args:
            template_name: Name of template to load
            
        Returns:
            Configuration based on template
        """
        return CONFIGURATION_TEMPLATES.get(
            template_name,
            self.default_config
        )
    
    def _copy_config(
        self,
        config: InternalLinkingConfiguration
    ) -> InternalLinkingConfiguration:
        """Create a copy of configuration."""
        
        return InternalLinkingConfiguration(
            new_vs_existing_split=config.new_vs_existing_split,
            seo_conversion_balance=config.seo_conversion_balance,
            analysis_scope=config.analysis_scope,
            personalization_level=config.personalization_level,
            business_objective_weights=config.business_objective_weights.copy(),
            min_seo_value=config.min_seo_value,
            min_conversion_value=config.min_conversion_value,
            min_personalization_score=config.min_personalization_score,
            max_links_per_page=config.max_links_per_page,
            min_link_distance=config.min_link_distance,
            min_anchor_words=config.min_anchor_words,
            max_anchor_words=config.max_anchor_words,
            avoid_generic_anchors=config.avoid_generic_anchors,
            conversion_focus=config.conversion_focus,
            enable_cta_integration=config.enable_cta_integration,
            track_conversion_attribution=config.track_conversion_attribution,
            enable_progressive_profiling=config.enable_progressive_profiling,
            enable_behavioral_targeting=config.enable_behavioral_targeting,
            enable_predictive_personalization=config.enable_predictive_personalization,
            auto_insert_links=config.auto_insert_links,
            generate_reports=config.generate_reports,
            notify_on_completion=config.notify_on_completion
        )
    
    def _merge_configs(
        self,
        base: InternalLinkingConfiguration,
        override: InternalLinkingConfiguration
    ) -> InternalLinkingConfiguration:
        """Merge two configurations with override taking precedence."""
        
        merged = self._copy_config(base)
        
        # Override each field if different from default
        if override.new_vs_existing_split != self.default_config.new_vs_existing_split:
            merged.new_vs_existing_split = override.new_vs_existing_split
        
        if override.seo_conversion_balance != self.default_config.seo_conversion_balance:
            merged.seo_conversion_balance = override.seo_conversion_balance
        
        if override.analysis_scope != self.default_config.analysis_scope:
            merged.analysis_scope = override.analysis_scope
        
        if override.personalization_level != self.default_config.personalization_level:
            merged.personalization_level = override.personalization_level
        
        if override.business_objective_weights != self.default_config.business_objective_weights:
            merged.business_objective_weights = override.business_objective_weights.copy()
        
        if override.conversion_focus != self.default_config.conversion_focus:
            merged.conversion_focus = override.conversion_focus
        
        return merged
    
    def _apply_custom_settings(
        self,
        config: InternalLinkingConfiguration,
        custom_settings: Dict[str, Any]
    ) -> InternalLinkingConfiguration:
        """Apply custom settings to configuration."""
        
        # Create copy
        updated = self._copy_config(config)
        
        # Apply each custom setting
        for key, value in custom_settings.items():
            if key == "new_vs_existing_split":
                updated.new_vs_existing_split = float(value)
            elif key == "seo_conversion_balance":
                updated.seo_conversion_balance = float(value)
            elif key == "analysis_scope":
                if isinstance(value, str):
                    updated.analysis_scope = ScopeSetting(value)
                else:
                    updated.analysis_scope = value
            elif key == "personalization_level":
                if isinstance(value, str):
                    updated.personalization_level = PersonalizationLevel(value)
                else:
                    updated.personalization_level = value
            elif key == "business_objective_weights":
                updated.business_objective_weights = value
            elif key == "conversion_focus":
                updated.conversion_focus = float(value)
            elif key == "min_seo_value":
                updated.min_seo_value = float(value)
            elif key == "min_conversion_value":
                updated.min_conversion_value = float(value)
            elif key == "auto_insert_links":
                updated.auto_insert_links = bool(value)
        
        return updated


# Predefined configuration templates for different business objectives
CONFIGURATION_TEMPLATES = {
    "lead_generation_focused": InternalLinkingConfiguration(
        conversion_focus=0.8,  # Higher conversion focus
        business_objective_weights={
            "lead_generation": 0.7,
            "demo_request": 0.2,
            "trial_signup": 0.1,
            "purchase": 0.0
        },
        enable_cta_integration=True,
        enable_progressive_profiling=True,
        personalization_level=PersonalizationLevel.ADVANCED
    ),
    
    "demo_trial_focused": InternalLinkingConfiguration(
        conversion_focus=0.7,
        business_objective_weights={
            "demo_request": 0.5,
            "trial_signup": 0.4,
            "lead_generation": 0.1,
            "purchase": 0.0
        },
        enable_cta_integration=True,
        personalization_level=PersonalizationLevel.INTERMEDIATE
    ),
    
    "sales_focused": InternalLinkingConfiguration(
        conversion_focus=0.8,
        business_objective_weights={
            "purchase": 0.6,
            "trial_signup": 0.3,
            "lead_generation": 0.1,
            "demo_request": 0.0
        },
        enable_cta_integration=True,
        track_conversion_attribution=True,
        personalization_level=PersonalizationLevel.FULL
    ),
    
    "seo_balanced": InternalLinkingConfiguration(
        conversion_focus=0.5,  # More balanced
        seo_conversion_balance=0.5,
        business_objective_weights={
            "lead_generation": 0.3,
            "demo_request": 0.2,
            "trial_signup": 0.2,
            "purchase": 0.3
        },
        personalization_level=PersonalizationLevel.INTERMEDIATE
    ),
    
    "content_marketing": InternalLinkingConfiguration(
        conversion_focus=0.4,  # Lower conversion focus, higher SEO
        seo_conversion_balance=0.4,
        business_objective_weights={
            "lead_generation": 0.5,
            "demo_request": 0.2,
            "trial_signup": 0.2,
            "purchase": 0.1
        },
        enable_progressive_profiling=True,
        personalization_level=PersonalizationLevel.ADVANCED
    ),
    
    "hybrid_approach": InternalLinkingConfiguration(
        conversion_focus=0.7,
        new_vs_existing_split=0.5,
        business_objective_weights={
            "lead_generation": 0.4,
            "demo_request": 0.3,
            "trial_signup": 0.2,
            "purchase": 0.1
        },
        enable_cta_integration=True,
        enable_progressive_profiling=True,
        personalization_level=PersonalizationLevel.FULL
    )
}


# Global configuration manager instance
config_manager = ConfigurationManager()


# Helper functions for common operations
def get_default_config() -> InternalLinkingConfiguration:
    """Get default configuration."""
    return config_manager.default_config


def load_template_config(template_name: str) -> InternalLinkingConfiguration:
    """Load configuration template by name."""
    return config_manager.load_template(template_name)


def create_custom_config(
    scope: str = "include_existing",
    personalization: str = "intermediate",
    conversion_focus: float = 0.7,
    **kwargs
) -> InternalLinkingConfiguration:
    """
    Create custom configuration with specific settings.
    
    Args:
        scope: Analysis scope setting
        personalization: Personalization level
        conversion_focus: Conversion vs SEO balance
        **kwargs: Additional configuration options
        
    Returns:
        Custom configuration instance
    """
    
    config = InternalLinkingConfiguration(
        analysis_scope=ScopeSetting(scope),
        personalization_level=PersonalizationLevel(personalization),
        conversion_focus=conversion_focus
    )
    
    # Apply additional kwargs
    for key, value in kwargs.items():
        if hasattr(config, key):
            setattr(config, key, value)
    
    return config
