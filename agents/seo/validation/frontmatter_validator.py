"""
Frontmatter Validation Engine

This module provides a `FrontmatterValidator` class that validates the frontmatter
of a markdown file against a given `ContentConfiguration`.
"""
from typing import Dict, Any, List
from agents.seo.config.content_config import ContentConfiguration, FieldType, ValidationRule
import datetime

class FrontmatterValidator:
    """Validates frontmatter against a configuration."""

    def __init__(self, config: ContentConfiguration):
        self.config = config.frontmatter_validation

    def validate(self, frontmatter: Dict[str, Any]) -> List[str]:
        """Validates the given frontmatter and returns a list of errors."""
        errors: List[str] = []

        # Strict mode: Check for unknown fields
        if self.config.strict_mode:
            for key in frontmatter.keys():
                if key not in self.config.fields:
                    errors.append(f"Unknown field '{key}' not allowed in strict mode.")

        # Validate each field defined in the schema
        for field_name, field_schema in self.config.fields.items():
            value = frontmatter.get(field_name)
            
            # Check for required fields
            is_required = any(rule.rule_type == 'required' for rule in field_schema.rules)
            if is_required and value is None:
                errors.append(f"Required field '{field_name}' is missing.")
                continue

            if value is None:
                continue

            # Check field type
            self._validate_type(field_name, value, field_schema.field_type, errors)

            # Apply other validation rules
            for rule in field_schema.rules:
                self._apply_rule(field_name, value, rule, errors)
        
        return errors

    def _validate_type(self, name: str, value: Any, expected_type: FieldType, errors: List[str]):
        """Validates the data type of a field."""
        type_valid = True
        if expected_type == FieldType.STRING and not isinstance(value, str):
            type_valid = False
        elif expected_type == FieldType.NUMBER and not isinstance(value, (int, float)):
            type_valid = False
        elif expected_type == FieldType.BOOLEAN and not isinstance(value, bool):
            type_valid = False
        elif expected_type == FieldType.LIST and not isinstance(value, list):
            type_valid = False
        elif expected_type == FieldType.DATE:
            if isinstance(value, datetime.date):
                pass
            elif isinstance(value, str):
                try:
                    datetime.datetime.strptime(value, '%Y-%m-%d')
                except ValueError:
                    type_valid = False
            else:
                type_valid = False

        if not type_valid:
            errors.append(f"Field '{name}' has incorrect type. Expected {expected_type.value}, got {type(value).__name__}.")

    def _apply_rule(self, name: str, value: Any, rule: ValidationRule, errors: List[str]):
        """Applies a single validation rule to a field."""
        if rule.rule_type == "minLength":
            if isinstance(value, str) and len(value) < rule.value:
                errors.append(rule.error_message or f"Field '{name}' must be at least {rule.value} characters long.")
        elif rule.rule_type == "maxLength":
            if isinstance(value, str) and len(value) > rule.value:
                errors.append(rule.error_message or f"Field '{name}' must not exceed {rule.value} characters.")
        elif rule.rule_type == "allowed":
            if isinstance(value, str) and value not in rule.value:
                errors.append(rule.error_message or f"Field '{name}' has an invalid value. Allowed values are: {rule.value}")
