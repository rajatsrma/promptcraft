"""Template management functionality for PromptCraft."""

import json
import os
from typing import List, Optional, Dict, Any
from pathlib import Path

from .models import Template


def get_templates_directory() -> Path:
    """Get the templates directory path."""
    return Path(__file__).parent / "templates"


def load_template(name: str) -> Optional[Template]:
    """Load a specific template by name.
    
    Args:
        name: Template name (without .json extension)
        
    Returns:
        Template object or None if not found
    """
    templates_dir = get_templates_directory()
    template_path = templates_dir / f"{name}.json"
    
    if not template_path.exists():
        return None
    
    try:
        with open(template_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        return Template(
            name=data.get("name", name),
            description=data.get("description", ""),
            persona=data.get("persona"),
            task=data.get("task"),
            context=data.get("context"),
            constraints=data.get("constraints"),
            tags=data.get("tags", [])
        )
    except (json.JSONDecodeError, KeyError, IOError) as e:
        print(f"Error loading template '{name}': {e}")
        return None


def load_templates() -> List[Template]:
    """Load all available templates.
    
    Returns:
        List of Template objects
    """
    templates_dir = get_templates_directory()
    templates = []
    
    if not templates_dir.exists():
        return templates
    
    for template_file in templates_dir.glob("*.json"):
        template_name = template_file.stem
        template = load_template(template_name)
        if template:
            templates.append(template)
    
    return sorted(templates, key=lambda t: t.name)


def save_template(template: Template) -> bool:
    """Save a template to the templates directory.
    
    Args:
        template: Template object to save
        
    Returns:
        True if saved successfully, False otherwise
    """
    templates_dir = get_templates_directory()
    templates_dir.mkdir(parents=True, exist_ok=True)
    
    template_path = templates_dir / f"{template.name}.json"
    
    try:
        template_data = {
            "name": template.name,
            "description": template.description,
            "persona": template.persona,
            "task": template.task,
            "context": template.context,
            "constraints": template.constraints,
            "tags": template.tags
        }
        
        with open(template_path, 'w', encoding='utf-8') as f:
            json.dump(template_data, f, indent=2, ensure_ascii=False)
        
        return True
    except IOError as e:
        print(f"Error saving template '{template.name}': {e}")
        return False


def get_template_names() -> List[str]:
    """Get list of available template names.
    
    Returns:
        List of template names (without .json extension)
    """
    templates_dir = get_templates_directory()
    
    if not templates_dir.exists():
        return []
    
    return [f.stem for f in templates_dir.glob("*.json")]


def template_exists(name: str) -> bool:
    """Check if a template exists.
    
    Args:
        name: Template name to check
        
    Returns:
        True if template exists, False otherwise
    """
    templates_dir = get_templates_directory()
    template_path = templates_dir / f"{name}.json"
    return template_path.exists()


def delete_template(name: str) -> bool:
    """Delete a template.
    
    Args:
        name: Template name to delete
        
    Returns:
        True if deleted successfully, False otherwise
    """
    templates_dir = get_templates_directory()
    template_path = templates_dir / f"{name}.json"
    
    if not template_path.exists():
        return False
    
    try:
        template_path.unlink()
        return True
    except IOError as e:
        print(f"Error deleting template '{name}': {e}")
        return False