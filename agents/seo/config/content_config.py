"""
Content Configuration System

Provides a decoupled configuration management system for content robots, focusing on 
frontmatter validation, branding guidelines, and SEO rules. This system is designed 
to be autonomous and not coupled with the internal linking configuration.
"""
from typing import Dict, Any, List, Optional
from dataclasses import dataclass, field
from enum import Enum

class FieldType(str, Enum):
    """Data types for frontmatter fields."""
    STRING = "string"
    NUMBER = "number"
    DATE = "date"
    LIST = "list"
    BOOLEAN = "boolean"

@dataclass
class ValidationRule:
    """A single validation rule for a frontmatter field."""
    rule_type: str  # e.g., "required", "minLength", "maxLength", "allowed"
    value: Any = None
    error_message: Optional[str] = None

@dataclass
class FrontmatterField:
    """Schema for a single frontmatter field."""
    field_type: FieldType
    rules: List[ValidationRule] = field(default_factory=list)

@dataclass
class FrontmatterValidationConfig:
    """Configuration for frontmatter validation rules."""
    fields: Dict[str, FrontmatterField] = field(default_factory=dict)
    strict_mode: bool = True  # If true, unknown fields are not allowed

@dataclass
class ContentConfiguration:
    """Top-level configuration for content robots."""
    frontmatter_validation: FrontmatterValidationConfig = field(default_factory=FrontmatterValidationConfig)
    # Future configs can be added here, e.g.:
    # branding_guidelines: BrandingConfig = field(default_factory=BrandingConfig)
    # seo_rules: SEORulesConfig = field(default_factory=SEORulesConfig)

import os
import json
import libsql_client

class ContentConfigurationManager:
    """Manages content configuration with precedence, fetching from Turso DB."""

    def __init__(self):
        self.default_config = ContentConfiguration()
        self.db_client = None
        if os.getenv("TURSO_DATABASE_URL") and os.getenv("TURSO_AUTH_TOKEN"):
            self.db_client = libsql_client.create_client(
                url=os.getenv("TURSO_DATABASE_URL"),
                auth_token=os.getenv("TURSO_AUTH_TOKEN")
            )

    async def get_user_config_from_db(self, user_id: str) -> Optional[ContentConfiguration]:
        if not self.db_client: return None
        try:
            # Use parameterized queries to prevent SQL injection
            rs = await self.db_client.execute("SELECT config FROM UserContentConfig WHERE userId = ?", [user_id])
            if rs.rows:
                config_json = json.loads(rs.rows[0][0])
                # NOTE: This is a simplification. A production implementation should handle nested dataclass deserialization.
                return ContentConfiguration(**config_json)
        except Exception as e:
            print(f"Error fetching user config from DB: {e}")
        return None

    async def get_project_config_from_db(self, project_id: str) -> Optional[ContentConfiguration]:
        if not self.db_client: return None
        try:
            # Use parameterized queries to prevent SQL injection
            rs = await self.db_client.execute("SELECT config FROM ProjectContentConfig WHERE projectId = ?", [project_id])
            if rs.rows:
                config_json = json.loads(rs.rows[0][0])
                # NOTE: This is a simplification. A production implementation should handle nested dataclass deserialization.
                return ContentConfiguration(**config_json)
        except Exception as e:
            print(f"Error fetching project config from DB: {e}")
        return None

    async def get_config(
        self,
        user_id: Optional[str] = None,
        project_id: Optional[str] = None,
        session_id: Optional[str] = None,
        custom_settings: Optional[Dict[str, Any]] = None
    ) -> ContentConfiguration:
        """
        Get configuration with appropriate precedence.
        Precedence order (highest to lowest):
        1. Custom settings (runtime overrides)
        2. Session config (Note: session config is not yet implemented)
        3. User config (from DB)
        4. Project config (from DB)
        5. Default config
        """
        config = self._copy_config(self.default_config)

        if project_id:
            project_config = await self.get_project_config_from_db(project_id)
            if project_config:
                config = self._merge_configs(config, project_config)
        
        if user_id:
            user_config = await self.get_user_config_from_db(user_id)
            if user_config:
                config = self._merge_configs(config, user_config)

        if custom_settings:
            config = self._apply_custom_settings(config, custom_settings)
            
        return config

    def _copy_config(self, config: ContentConfiguration) -> ContentConfiguration:
        """Create a deep copy of configuration."""
        # A more robust solution would use deepcopy, but this is fine for now
        return ContentConfiguration(
            frontmatter_validation=FrontmatterValidationConfig(
                fields=config.frontmatter_validation.fields.copy(),
                strict_mode=config.frontmatter_validation.strict_mode
            )
        )

    def _merge_configs(self, base: ContentConfiguration, override: ContentConfiguration) -> ContentConfiguration:
        """Merge two configurations with override taking precedence."""
        merged = self._copy_config(base)
        
        # Merge frontmatter validation fields
        if override.frontmatter_validation.fields:
            merged.frontmatter_validation.fields.update(override.frontmatter_validation.fields)
            
        if override.frontmatter_validation.strict_mode != self.default_config.frontmatter_validation.strict_mode:
             merged.frontmatter_validation.strict_mode = override.frontmatter_validation.strict_mode

        return merged

    def _apply_custom_settings(self, config: ContentConfiguration, custom_settings: Dict[str, Any]) -> ContentConfiguration:
        """Apply custom settings to configuration."""
        updated = self._copy_config(config)

        if "frontmatter_validation" in custom_settings:
            custom_fm_val = custom_settings["frontmatter_validation"]
            if "fields" in custom_fm_val:
                updated.frontmatter_validation.fields.update(custom_fm_val["fields"])
            if "strict_mode" in custom_fm_val:
                updated.frontmatter_validation.strict_mode = custom_fm_val["strict_mode"]

        return updated

#<TEMPLATES>
# Predefined configuration templates for different content strategies
CONFIGURATION_TEMPLATES = {
    "strict_seo": ContentConfiguration(
        frontmatter_validation=FrontmatterValidationConfig(
            strict_mode=True,
            fields={
                "title": FrontmatterField(
                    field_type=FieldType.STRING,
                    rules=[
                        ValidationRule(rule_type="required"),
                        ValidationRule(rule_type="minLength", value=20),
                        ValidationRule(rule_type="maxLength", value=70)
                    ]
                ),
                "description": FrontmatterField(
                    field_type=FieldType.STRING,
                    rules=[
                        ValidationRule(rule_type="required"),
                        ValidationRule(rule_type="minLength", value=50),
                        ValidationRule(rule_type="maxLength", value=160)
                    ]
                ),
                "slug": FrontmatterField(
                    field_type=FieldType.STRING,
                    rules=[
                        ValidationRule(rule_type="required")
                    ]
                ),
                "publish_date": FrontmatterField(
                    field_type=FieldType.DATE,
                    rules=[
                        ValidationRule(rule_type="required")
                    ]
                ),
                "tags": FrontmatterField(
                    field_type=FieldType.LIST,
                    rules=[
                        ValidationRule(rule_type="required")
                    ]
                )
            }
        )
    ),
    "flexible_draft": ContentConfiguration(
        frontmatter_validation=FrontmatterValidationConfig(
            strict_mode=False,
            fields={
                "title": FrontmatterField(
                    field_type=FieldType.STRING,
                    rules=[
                        ValidationRule(rule_type="required")
                    ]
                )
            }
        )
    )
}
#</TEMPLATES>

#<HELPERS>
# Global configuration manager instance
config_manager = ContentConfigurationManager()

# Helper functions for common operations
def get_default_config() -> ContentConfiguration:
    """Get default content configuration."""
    return config_manager.default_config

def load_template_config(template_name: str) -> ContentConfiguration:
    """Load content configuration template by name."""
    return CONFIGURATION_TEMPLATES.get(template_name, config_manager.default_config)

async def create_custom_config(custom_settings: Dict[str, Any]) -> ContentConfiguration:
    """Create custom content configuration with specific settings."""
    return await config_manager.get_config(custom_settings=custom_settings)
#</HELPERS>
