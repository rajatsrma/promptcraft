"""Project type detection for PromptCraft."""

import os
import json
from typing import List, Dict, Optional, Set
from pathlib import Path


# Framework detection patterns
FRAMEWORK_PATTERNS = {
    "react": [
        "package.json",
        "src/App.jsx", 
        "src/App.tsx",
        "public/index.html",
        "src/index.js",
        "src/index.tsx"
    ],
    "node": [
        "package.json",
        "server.js",
        "app.js",
        "index.js",
        "src/server.js"
    ],
    "python": [
        "requirements.txt",
        "pyproject.toml", 
        "setup.py",
        "main.py",
        "app.py"
    ],
    "django": [
        "manage.py",
        "settings.py",
        "requirements.txt",
        "pyproject.toml"
    ],
    "fastapi": [
        "main.py",
        "app.py", 
        "requirements.txt",
        "pyproject.toml"
    ],
    "java": [
        "pom.xml",
        "build.gradle",
        "src/main/java",
        "build.gradle.kts"
    ],
    "spring": [
        "pom.xml",
        "src/main/java",
        "application.properties",
        "application.yml"
    ],
    "go": [
        "go.mod",
        "main.go",
        "go.sum"
    ],
    "rust": [
        "Cargo.toml",
        "src/main.rs",
        "Cargo.lock"
    ],
    "flutter": [
        "pubspec.yaml",
        "lib/main.dart",
        "android/",
        "ios/"
    ],
    "vue": [
        "package.json",
        "vue.config.js",
        "src/App.vue",
        "src/main.js"
    ],
    "angular": [
        "package.json",
        "angular.json",
        "src/app/app.module.ts",
        "src/main.ts"
    ],
    "nextjs": [
        "package.json",
        "next.config.js",
        "pages/",
        "app/"
    ]
}

# Template suggestions based on detected frameworks
FRAMEWORK_TEMPLATE_MAPPING = {
    "react": ["code-review", "testing", "refactoring"],
    "node": ["code-review", "debugging", "testing"],
    "python": ["debugging", "refactoring", "testing"],
    "django": ["code-review", "feature-planning", "refactoring"],
    "fastapi": ["code-review", "testing", "feature-planning"],
    "java": ["code-review", "refactoring", "testing"],
    "spring": ["feature-planning", "code-review", "refactoring"],
    "go": ["code-review", "testing", "debugging"],
    "rust": ["code-review", "refactoring", "debugging"],
    "flutter": ["feature-planning", "testing", "code-review"],
    "vue": ["code-review", "testing", "refactoring"],
    "angular": ["feature-planning", "code-review", "testing"],
    "nextjs": ["code-review", "feature-planning", "testing"]
}

# Default template suggestions for unknown projects
DEFAULT_TEMPLATE_SUGGESTIONS = ["code-review", "debugging", "testing"]


def detect_project_type(project_path: str = ".") -> List[str]:
    """Detect project type based on files and directories present.
    
    Args:
        project_path: Path to the project directory to analyze
        
    Returns:
        List of detected framework/project types
    """
    detected_frameworks = []
    project_path = Path(project_path).resolve()
    
    for framework, patterns in FRAMEWORK_PATTERNS.items():
        matches = 0
        total_patterns = len(patterns)
        
        for pattern in patterns:
            pattern_path = project_path / pattern
            
            # Check if it's a file or directory
            if pattern.endswith('/'):
                # Directory pattern
                if pattern_path.is_dir():
                    matches += 1
            else:
                # File pattern
                if pattern_path.is_file():
                    matches += 1
        
        # Determine threshold based on framework
        if framework in ["go", "rust", "flutter"]:
            threshold = 1  # These have strong unique indicators
        elif framework in ["python", "node", "java"]:
            threshold = 1  # Allow single strong indicators like pyproject.toml, package.json, pom.xml
        else:
            threshold = max(1, total_patterns // 2)
        if matches >= threshold:
            detected_frameworks.append(framework)
    
    return detected_frameworks


def detect_package_json_framework(project_path: str = ".") -> Optional[str]:
    """Detect specific JavaScript framework from package.json dependencies.
    
    Args:
        project_path: Path to the project directory
        
    Returns:
        Detected framework name or None
    """
    package_json_path = Path(project_path) / "package.json"
    
    if not package_json_path.is_file():
        return None
    
    try:
        with open(package_json_path, 'r', encoding='utf-8') as f:
            package_data = json.load(f)
        
        dependencies = {}
        dependencies.update(package_data.get("dependencies", {}))
        dependencies.update(package_data.get("devDependencies", {}))
        
        # Check for specific frameworks
        if "react" in dependencies:
            if "next" in dependencies:
                return "nextjs"
            return "react"
        elif "vue" in dependencies:
            return "vue"
        elif "@angular/core" in dependencies:
            return "angular"
        elif "express" in dependencies:
            return "node"
            
    except (json.JSONDecodeError, IOError):
        pass
    
    return None


def detect_python_framework(project_path: str = ".") -> Optional[str]:
    """Detect specific Python framework from requirements or project structure.
    
    Args:
        project_path: Path to the project directory
        
    Returns:
        Detected framework name or None
    """
    project_path = Path(project_path)
    
    # Check for Django
    if (project_path / "manage.py").is_file():
        return "django"
    
    # Check for FastAPI in requirements.txt or pyproject.toml
    requirements_files = ["requirements.txt", "pyproject.toml"]
    
    for req_file in requirements_files:
        req_path = project_path / req_file
        if req_path.is_file():
            try:
                with open(req_path, 'r', encoding='utf-8') as f:
                    content = f.read().lower()
                    if "fastapi" in content:
                        return "fastapi"
                    elif "django" in content:
                        return "django"
            except IOError:
                continue
    
    return "python"


def get_enhanced_detection(project_path: str = ".") -> List[str]:
    """Get enhanced project detection with framework-specific analysis.
    
    Args:
        project_path: Path to the project directory
        
    Returns:
        List of detected frameworks with enhanced detection
    """
    detected = detect_project_type(project_path)
    enhanced = set(detected)
    
    # Enhanced JavaScript framework detection
    js_framework = detect_package_json_framework(project_path)
    if js_framework:
        enhanced.add(js_framework)
        # Remove generic "node" if we found a specific framework
        if js_framework in ["react", "vue", "angular", "nextjs"] and "node" in enhanced:
            enhanced.remove("node")
    
    # Enhanced Python framework detection
    if "python" in enhanced:
        python_framework = detect_python_framework(project_path)
        if python_framework and python_framework != "python":
            enhanced.add(python_framework)
            # Remove generic "python" if we found a specific framework
            if python_framework in ["django", "fastapi"]:
                enhanced.remove("python")
    
    return list(enhanced)


def get_suggested_templates(project_path: str = ".") -> List[str]:
    """Get template suggestions based on detected project type.
    
    Args:
        project_path: Path to the project directory
        
    Returns:
        List of suggested template names
    """
    detected_frameworks = get_enhanced_detection(project_path)
    
    if not detected_frameworks:
        return DEFAULT_TEMPLATE_SUGGESTIONS
    
    # Collect suggestions from all detected frameworks
    suggestions = set()
    for framework in detected_frameworks:
        if framework in FRAMEWORK_TEMPLATE_MAPPING:
            suggestions.update(FRAMEWORK_TEMPLATE_MAPPING[framework])
    
    # If no specific suggestions found, use defaults
    if not suggestions:
        return DEFAULT_TEMPLATE_SUGGESTIONS
    
    # Return suggestions in priority order
    priority_order = ["code-review", "debugging", "testing", "feature-planning", "refactoring"]
    ordered_suggestions = []
    
    for template in priority_order:
        if template in suggestions:
            ordered_suggestions.append(template)
    
    # Add any remaining suggestions
    for template in suggestions:
        if template not in ordered_suggestions:
            ordered_suggestions.append(template)
    
    return ordered_suggestions[:3]  # Return top 3 suggestions


def get_project_description(project_path: str = ".") -> str:
    """Get a human-readable description of the detected project type.
    
    Args:
        project_path: Path to the project directory
        
    Returns:
        Human-readable project description
    """
    detected_frameworks = get_enhanced_detection(project_path)
    
    if not detected_frameworks:
        return "Unknown project type"
    
    # Format the description nicely
    if len(detected_frameworks) == 1:
        return f"{detected_frameworks[0].title()} project"
    elif len(detected_frameworks) == 2:
        return f"{detected_frameworks[0].title()} and {detected_frameworks[1].title()} project"
    else:
        frameworks_str = ", ".join(f.title() for f in detected_frameworks[:-1])
        return f"{frameworks_str}, and {detected_frameworks[-1].title()} project"