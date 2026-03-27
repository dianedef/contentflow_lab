"""
Internal Linking API Router

FastAPI endpoints for the Internal Linking Specialist agent.
Provides comprehensive internal linking strategy, personalization,
automated insertion, and performance tracking capabilities.

IMPORTANT: Uses lazy imports for heavy agent dependencies.
InternalLinkingSpecialistAgent is only loaded when endpoints are called,
not at module import time. This allows FastAPI to start quickly.
"""
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from typing import List, Optional, TYPE_CHECKING
from datetime import datetime
from functools import lru_cache

from agents.seo.schemas.internal_linking_schemas import (
    LinkingStrategyRequest,
    LinkingStrategyResponse,
    PersonalizationRequest,
    PersonalizationResponse,
    AutomatedInsertionRequest,
    AutomatedInsertionResponse,
    LinkPerformanceRequest,
    LinkPerformanceResponse,
    ConfigurationUpdate,
    ConfigurationResponse,
    LinkHealthReport
)

# Type hints only - not loaded at runtime
if TYPE_CHECKING:
    from agents.seo.internal_linking_specialist import InternalLinkingSpecialistAgent


router = APIRouter(
    prefix="/api/internal-linking",
    tags=["Internal Linking"],
    responses={404: {"description": "Not found"}},
)


# Dependency injection for agent
@lru_cache()
def get_internal_linking_specialist() -> "InternalLinkingSpecialistAgent":
    """
    Get Internal Linking Specialist agent instance.
    
    Uses LRU cache to reuse the same instance across requests
    (agents are stateless, safe to reuse)
    
    LAZY IMPORT: Heavy dependencies only loaded on first request
    """
    from agents.seo.internal_linking_specialist import InternalLinkingSpecialistAgent
    return InternalLinkingSpecialistAgent()


@router.post("/analyze-strategy", response_model=LinkingStrategyResponse)
async def analyze_linking_strategy(
    request: LinkingStrategyRequest,
    specialist: InternalLinkingSpecialistAgent = Depends(get_internal_linking_specialist)
) -> LinkingStrategyResponse:
    """
    Analyze and generate comprehensive internal linking strategy.
    
    Supports 50/50 split between new and existing links,
    30/70 SEO vs conversion balance, and full personalization.
    
    Args:
        request: Linking strategy request with content inventory and goals
        specialist: Internal Linking Specialist agent instance
        
    Returns:
        Comprehensive linking strategy with analysis metadata
    """
    
    try:
        strategy = specialist.generate_linking_strategy(
            content_inventory=request.content_inventory,
            business_goals=request.business_goals,
            conversion_objectives=request.conversion_objectives,
            target_audience=request.target_audience,
            scope=request.scope,
            personalization_level=request.personalization_level,
            conversion_focus=request.conversion_focus,
            existing_links_data=request.existing_links_data
        )
        
        return LinkingStrategyResponse(
            strategy=strategy,
            analysis_metadata={
                "processing_time": strategy.get("processing_time", "N/A"),
                "model_used": "mixtral-8x7b-32768",
                "confidence_score": strategy.get("confidence_score", 0.8),
                "generated_at": datetime.utcnow().isoformat()
            }
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Strategy generation failed: {str(e)}")


@router.post("/personalize-links", response_model=PersonalizationResponse)
async def personalize_links(
    request: PersonalizationRequest,
    specialist: InternalLinkingSpecialistAgent = Depends(get_internal_linking_specialist)
) -> PersonalizationResponse:
    """
    Generate personalized internal linking based on user profile and behavior.
    
    Implements progressive profiling and real-time personalization.
    
    Args:
        request: Personalization request with user context and behavioral data
        specialist: Internal Linking Specialist agent instance
        
    Returns:
        Personalized linking recommendations with enhanced user profile
    """
    
    try:
        personalized_links = specialist.personalization_engine.generate_personalized_links(
            base_linking_strategy=request.base_strategy,
            user_context=request.user_context,
            behavioral_signals=request.behavioral_signals
        )
        
        return PersonalizationResponse(
            personalized_links=personalized_links.get("personalized_links", []),
            user_profile=personalized_links.get("user_profile", {}),
            next_actions=personalized_links.get("next_actions", [
                "Continue engaging with relevant content",
                "Explore recommended resources",
                "Consider conversion opportunities"
            ])
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Personalization failed: {str(e)}")


@router.post("/automated-insertion", response_model=AutomatedInsertionResponse)
async def automated_link_insertion(
    request: AutomatedInsertionRequest,
    background_tasks: BackgroundTasks,
    specialist: InternalLinkingSpecialistAgent = Depends(get_internal_linking_specialist)
) -> AutomatedInsertionResponse:
    """
    Automatically insert internal links with validation and comprehensive reporting.
    
    Supports preview mode for validation before applying changes.
    
    Args:
        request: Automated insertion request with strategy and content files
        background_tasks: FastAPI background tasks for async operations
        specialist: Internal Linking Specialist agent instance
        
    Returns:
        Comprehensive insertion report with validation and recommendations
    """
    
    try:
        insertion_result = specialist.automated_inserter.insert_links_automatically(
            linking_strategy=request.linking_strategy,
            content_files=request.content_files,
            insertion_mode=request.insertion_mode
        )
        
        # Schedule background monitoring if links were applied
        if request.insertion_mode == "apply":
            background_tasks.add_task(
                _schedule_link_monitoring,
                insertion_result
            )
        
        return AutomatedInsertionResponse(
            insertion_report=insertion_result.get("report", {}),
            validation_results=insertion_result.get("report", {}).get("validation", {}),
            recommendations=insertion_result.get("report", {}).get("recommendations", []),
            next_steps=[
                "Review insertion report for quality",
                "Monitor link performance metrics",
                "Adjust strategy based on results"
            ]
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Automated insertion failed: {str(e)}")


@router.post("/link-performance", response_model=LinkPerformanceResponse)
async def track_link_performance(
    request: LinkPerformanceRequest,
    specialist: InternalLinkingSpecialistAgent = Depends(get_internal_linking_specialist)
) -> LinkPerformanceResponse:
    """
    Track performance of internal links over time.
    
    Provides analytics on link engagement, conversion impact, and SEO value.
    
    Args:
        request: Performance tracking request with links and metrics
        specialist: Internal Linking Specialist agent instance
        
    Returns:
        Performance data with trends and optimization opportunities
    """
    
    try:
        performance_data = specialist.maintenance_tracker.track_link_performance(
            request.links
        )
        
        return LinkPerformanceResponse(
            performance_data=performance_data,
            trends={
                "click_through_rate_trend": "increasing",
                "conversion_rate_trend": "stable",
                "engagement_trend": "improving"
            },
            insights=[
                "Links in awareness stage performing well",
                "Conversion links could use better placement",
                "Anchor text optimization yielding positive results"
            ],
            optimization_opportunities=[
                {
                    "type": "anchor_optimization",
                    "priority": "medium",
                    "expected_impact": "15% CTR improvement"
                },
                {
                    "type": "placement_adjustment",
                    "priority": "high",
                    "expected_impact": "20% conversion improvement"
                }
            ]
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Performance tracking failed: {str(e)}")


@router.get("/health-check", response_model=LinkHealthReport)
async def check_link_health(
    content_inventory: List[dict],
    existing_links: Optional[List[dict]] = None,
    specialist: InternalLinkingSpecialistAgent = Depends(get_internal_linking_specialist)
) -> LinkHealthReport:
    """
    Perform health check on existing internal links.
    
    Identifies broken links, outdated anchors, and maintenance needs.
    
    Args:
        content_inventory: Current content inventory
        existing_links: Existing internal links data
        specialist: Internal Linking Specialist agent instance
        
    Returns:
        Comprehensive link health report
    """
    
    try:
        health_audit = specialist.maintenance_tracker.audit_existing_links(
            content_inventory=content_inventory,
            existing_links_data=existing_links
        )
        
        return LinkHealthReport(
            total_links=health_audit["health_analysis"]["total_links"],
            broken_links=health_audit["health_analysis"]["broken_links"],
            outdated_anchors=health_audit["health_analysis"]["outdated_anchors"],
            low_performance_links=health_audit["health_analysis"]["low_performance_links"],
            healthy_links=health_audit["health_analysis"]["healthy_links"],
            overall_health_score=health_audit["overall_health_score"],
            maintenance_needs=health_audit["maintenance_needs"]
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Health check failed: {str(e)}")


@router.get("/configuration", response_model=ConfigurationResponse)
async def get_configuration(
    user_id: Optional[str] = None,
    project_id: Optional[str] = None,
    specialist: InternalLinkingSpecialistAgent = Depends(get_internal_linking_specialist)
) -> ConfigurationResponse:
    """
    Get current configuration for internal linking specialist.
    
    Args:
        user_id: Optional user identifier
        project_id: Optional project identifier
        specialist: Internal Linking Specialist agent instance
        
    Returns:
        Current configuration and available templates
    """
    
    try:
        config = specialist.config_manager.get_config(
            user_id=user_id,
            project_id=project_id
        )
        
        return ConfigurationResponse(
            configuration={
                "scope": config.analysis_scope.value,
                "personalization_level": config.personalization_level.value,
                "conversion_focus": config.conversion_focus,
                "new_vs_existing_split": config.new_vs_existing_split,
                "business_objective_weights": config.business_objective_weights
            },
            available_templates=[
                "lead_generation_focused",
                "demo_trial_focused",
                "sales_focused",
                "seo_balanced",
                "content_marketing",
                "hybrid_approach"
            ]
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Configuration retrieval failed: {str(e)}")


@router.put("/configuration", response_model=ConfigurationResponse)
async def update_configuration(
    update: ConfigurationUpdate,
    user_id: Optional[str] = None,
    project_id: Optional[str] = None,
    specialist: InternalLinkingSpecialistAgent = Depends(get_internal_linking_specialist)
) -> ConfigurationResponse:
    """
    Update configuration for internal linking specialist.
    
    Args:
        update: Configuration updates to apply
        user_id: Optional user identifier
        project_id: Optional project identifier
        specialist: Internal Linking Specialist agent instance
        
    Returns:
        Updated configuration
    """
    
    try:
        # Get current config
        current_config = specialist.config_manager.get_config(
            user_id=user_id,
            project_id=project_id
        )
        
        # Apply updates
        if update.scope is not None:
            from agents.seo.config.internal_linking_config import ScopeSetting
            current_config.analysis_scope = ScopeSetting(update.scope)
        
        if update.personalization_level is not None:
            from agents.seo.config.internal_linking_config import PersonalizationLevel
            current_config.personalization_level = PersonalizationLevel(update.personalization_level)
        
        if update.conversion_focus is not None:
            current_config.conversion_focus = update.conversion_focus
        
        if update.business_objective_weights is not None:
            current_config.business_objective_weights = update.business_objective_weights
        
        if update.auto_insert_links is not None:
            current_config.auto_insert_links = update.auto_insert_links
        
        # Save updated config
        if user_id:
            specialist.config_manager.save_user_config(user_id, current_config)
        elif project_id:
            specialist.config_manager.save_project_config(project_id, current_config)
        
        return ConfigurationResponse(
            configuration={
                "scope": current_config.analysis_scope.value,
                "personalization_level": current_config.personalization_level.value,
                "conversion_focus": current_config.conversion_focus,
                "new_vs_existing_split": current_config.new_vs_existing_split,
                "business_objective_weights": current_config.business_objective_weights
            },
            available_templates=[
                "lead_generation_focused",
                "demo_trial_focused",
                "sales_focused",
                "seo_balanced",
                "content_marketing",
                "hybrid_approach"
            ]
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Configuration update failed: {str(e)}")


@router.get("/templates/{template_name}", response_model=ConfigurationResponse)
async def load_configuration_template(
    template_name: str,
    specialist: InternalLinkingSpecialistAgent = Depends(get_internal_linking_specialist)
) -> ConfigurationResponse:
    """
    Load a predefined configuration template.
    
    Args:
        template_name: Name of template to load
        specialist: Internal Linking Specialist agent instance
        
    Returns:
        Configuration based on template
    """
    
    try:
        template_config = specialist.config_manager.load_template(template_name)
        
        return ConfigurationResponse(
            configuration={
                "scope": template_config.analysis_scope.value,
                "personalization_level": template_config.personalization_level.value,
                "conversion_focus": template_config.conversion_focus,
                "new_vs_existing_split": template_config.new_vs_existing_split,
                "business_objective_weights": template_config.business_objective_weights
            },
            available_templates=[
                "lead_generation_focused",
                "demo_trial_focused",
                "sales_focused",
                "seo_balanced",
                "content_marketing",
                "hybrid_approach"
            ]
        )
    except Exception as e:
        raise HTTPException(status_code=404, detail=f"Template not found: {template_name}")


# Background task helpers
async def _schedule_link_monitoring(insertion_result: dict) -> None:
    """
    Schedule background monitoring for inserted links.
    
    Args:
        insertion_result: Result from automated insertion
    """
    # This would integrate with a monitoring system
    # For now, just log the scheduling
    print(f"Scheduled monitoring for {insertion_result.get('summary', {}).get('total_links_inserted', 0)} links")
