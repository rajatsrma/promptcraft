"""
Smart file filtering system for PromptCraft CLI.

This module provides intelligent file filtering capabilities including:
- .gitignore pattern matching
- File type detection and prioritization
- Size limits and binary file detection
- Common ignore patterns for development projects
"""

import fnmatch
import os
import mimetypes
from pathlib import Path
from typing import List, Set, Dict, Optional, Tuple
from dataclasses import dataclass
from enum import Enum


class FileType(Enum):
    """Categorizes files by their type and priority for inclusion."""
    SOURCE_CODE = "source_code"
    CONFIG = "config"
    DOCUMENTATION = "documentation"
    TEST = "test"
    BUILD = "build"
    DEPENDENCY = "dependency"
    BINARY = "binary"
    UNKNOWN = "unknown"


@dataclass
class FileInfo:
    """Contains metadata about a file for filtering decisions."""
    path: Path
    relative_path: str
    size_bytes: int
    file_type: FileType
    is_text: bool
    last_modified: float


class GitIgnoreFilter:
    """Handles .gitignore pattern matching for file filtering."""
    
    def __init__(self, root_path: Path):
        """Initialize with project root path to find .gitignore files."""
        self.root_path = Path(root_path)
        self.patterns: List[str] = []
        self._load_gitignore_patterns()
    
    def _load_gitignore_patterns(self) -> None:
        """Load patterns from .gitignore files in the project."""
        gitignore_path = self.root_path / ".gitignore"
        if gitignore_path.exists():
            try:
                with open(gitignore_path, 'r', encoding='utf-8') as f:
                    for line in f:
                        line = line.strip()
                        # Skip empty lines and comments
                        if line and not line.startswith('#'):
                            self.patterns.append(line)
            except (IOError, UnicodeDecodeError):
                # If we can't read .gitignore, continue without it
                pass
    
    def should_ignore(self, file_path: str) -> bool:
        """Check if a file should be ignored based on .gitignore patterns."""
        relative_path = str(Path(file_path).relative_to(self.root_path))
        
        for pattern in self.patterns:
            # Handle directory patterns
            if pattern.endswith('/'):
                if fnmatch.fnmatch(relative_path + '/', pattern) or \
                   fnmatch.fnmatch(relative_path, pattern[:-1]):
                    return True
            # Handle file patterns
            elif fnmatch.fnmatch(relative_path, pattern) or \
                 fnmatch.fnmatch(Path(relative_path).name, pattern):
                return True
        
        return False


class FileTypeDetector:
    """Detects and categorizes file types for intelligent filtering."""
    
    # File extensions mapped to file types
    TYPE_MAPPINGS = {
        # Source code files (highest priority)
        FileType.SOURCE_CODE: {
            '.py', '.js', '.ts', '.tsx', '.jsx', '.java', '.cpp', '.c', '.h',
            '.cs', '.php', '.rb', '.go', '.rs', '.swift', '.kt', '.scala',
            '.clj', '.hs', '.ml', '.r', '.m', '.mm', '.dart', '.vue', '.svelte'
        },
        
        # Configuration files
        FileType.CONFIG: {
            '.json', '.yaml', '.yml', '.toml', '.ini', '.cfg', '.conf',
            '.env', '.properties', '.xml', '.plist', '.config'
        },
        
        # Documentation files
        FileType.DOCUMENTATION: {
            '.md', '.rst', '.txt', '.adoc', '.org', '.tex'
        },
        
        # Test files (detected by naming patterns)
        FileType.TEST: {
            '.test.js', '.test.ts', '.spec.js', '.spec.ts',
            '_test.py', 'test_*.py'
        },
        
        # Build and dependency files
        FileType.BUILD: {
            '.dockerfile', '.dockerignore', '.makefile'
        },
        
        # Binary files (should be excluded)
        FileType.BINARY: {
            '.exe', '.dll', '.so', '.dylib', '.a', '.lib', '.bin',
            '.img', '.iso', '.dmg', '.pkg', '.deb', '.rpm',
            '.zip', '.tar', '.gz', '.bz2', '.xz', '.7z', '.rar',
            '.pdf', '.doc', '.docx', '.xls', '.xlsx', '.ppt', '.pptx',
            '.jpg', '.jpeg', '.png', '.gif', '.bmp', '.tiff', '.svg',
            '.mp3', '.mp4', '.avi', '.mov', '.wmv', '.flv',
            '.ttf', '.otf', '.woff', '.woff2', '.eot'
        }
    }
    
    # Special filename patterns
    SPECIAL_FILES = {
        FileType.CONFIG: {
            'package.json', 'package-lock.json', 'yarn.lock', 'pnpm-lock.yaml',
            'requirements.txt', 'pyproject.toml', 'setup.py', 'setup.cfg',
            'cargo.toml', 'cargo.lock', 'go.mod', 'go.sum',
            'gemfile', 'gemfile.lock', 'composer.json', 'composer.lock',
            'dockerfile', 'docker-compose.yml', 'docker-compose.yaml',
            'makefile', '.gitignore', '.gitattributes', '.editorconfig',
            'tsconfig.json', 'jsconfig.json', '.eslintrc', '.prettierrc',
            'webpack.config.js', 'vite.config.js', 'rollup.config.js'
        },
        
        FileType.DOCUMENTATION: {
            'readme.md', 'readme.txt', 'readme.rst', 'readme',
            'changelog.md', 'changelog.txt', 'changelog',
            'license', 'license.md', 'license.txt',
            'contributing.md', 'code_of_conduct.md'
        }
    }
    
    def detect_file_type(self, file_path: Path) -> FileType:
        """Detect the type of a file based on extension and name patterns."""
        filename = file_path.name.lower()
        extension = file_path.suffix.lower()
        
        # Check special filenames first
        for file_type, filenames in self.SPECIAL_FILES.items():
            if filename in filenames:
                return file_type
        
        # Check test file patterns
        if any(pattern in filename for pattern in ['test', 'spec', '__test__']):
            if extension in {'.py', '.js', '.ts', '.jsx', '.tsx'}:
                return FileType.TEST
        
        # Check extensions
        for file_type, extensions in self.TYPE_MAPPINGS.items():
            if extension in extensions:
                return file_type
            # Also check compound extensions like .test.js
            if any(filename.endswith(ext) for ext in extensions if '.' in ext):
                return file_type
        
        return FileType.UNKNOWN
    
    def is_text_file(self, file_path: Path) -> bool:
        """Determine if a file is likely to be text-based."""
        # First check by file type
        file_type = self.detect_file_type(file_path)
        if file_type == FileType.BINARY:
            return False
        
        # Use mimetypes for additional detection
        mime_type, _ = mimetypes.guess_type(str(file_path))
        if mime_type:
            return mime_type.startswith('text/') or \
                   mime_type in {'application/json', 'application/xml', 
                                'application/yaml', 'application/toml'}
        
        # If we can't determine, assume text for known source types
        return file_type in {FileType.SOURCE_CODE, FileType.CONFIG, 
                           FileType.DOCUMENTATION, FileType.TEST}


class SmartFileFilter:
    """Main file filtering class that combines all filtering logic."""
    
    # Default ignore patterns for common development files/directories
    DEFAULT_IGNORE_PATTERNS = [
        # Dependencies and build artifacts
        "node_modules/", ".git/", "__pycache__/", ".venv/", "venv/",
        "env/", ".env/", "build/", "dist/", "target/", ".next/", 
        ".nuxt/", "coverage/", ".coverage/", ".pytest_cache/",
        ".mypy_cache/", ".tox/", ".cache/", "tmp/", "temp/",
        
        # IDE and editor files
        ".vscode/", ".idea/", "*.swp", "*.swo", "*~", ".DS_Store",
        "thumbs.db", "desktop.ini",
        
        # Compiled and temporary files
        "*.pyc", "*.pyo", "*.pyd", "*.class", "*.o", "*.obj",
        "*.log", "*.tmp", "*.temp", "*.min.js", "*.min.css",
        "*.map", "*.bundle.js", "*.chunk.js",
        
        # Package files
        "*.tar.gz", "*.zip", "*.rar", "*.7z", "*.deb", "*.rpm",
        "*.dmg", "*.pkg", "*.msi",
        
        # Media files
        "*.jpg", "*.jpeg", "*.png", "*.gif", "*.bmp", "*.ico",
        "*.mp3", "*.mp4", "*.avi", "*.mov", "*.pdf"
    ]
    
    def __init__(self, 
                 root_path: Path,
                 max_file_size_mb: float = 1.0,
                 use_gitignore: bool = True,
                 custom_ignore_patterns: Optional[List[str]] = None):
        """Initialize the smart file filter.
        
        Args:
            root_path: Root directory for file filtering
            max_file_size_mb: Maximum file size in MB to include
            use_gitignore: Whether to respect .gitignore patterns
            custom_ignore_patterns: Additional patterns to ignore
        """
        self.root_path = Path(root_path)
        self.max_file_size_bytes = int(max_file_size_mb * 1024 * 1024)
        
        # Initialize components
        self.gitignore_filter = GitIgnoreFilter(root_path) if use_gitignore else None
        self.type_detector = FileTypeDetector()
        
        # Combine ignore patterns
        self.ignore_patterns = self.DEFAULT_IGNORE_PATTERNS.copy()
        if custom_ignore_patterns:
            self.ignore_patterns.extend(custom_ignore_patterns)
    
    def _matches_ignore_pattern(self, file_path: Path) -> bool:
        """Check if file matches any ignore patterns."""
        relative_path = str(file_path.relative_to(self.root_path))
        
        for pattern in self.ignore_patterns:
            # Handle directory patterns
            if pattern.endswith('/'):
                if any(part == pattern[:-1] for part in file_path.parts):
                    return True
            # Handle file patterns
            elif fnmatch.fnmatch(relative_path, pattern) or \
                 fnmatch.fnmatch(file_path.name, pattern):
                return True
        
        return False
    
    def get_file_info(self, file_path: Path) -> Optional[FileInfo]:
        """Get comprehensive information about a file."""
        try:
            if not file_path.exists() or not file_path.is_file():
                return None
            
            stat = file_path.stat()
            relative_path = str(file_path.relative_to(self.root_path))
            
            file_type = self.type_detector.detect_file_type(file_path)
            is_text = self.type_detector.is_text_file(file_path)
            
            return FileInfo(
                path=file_path,
                relative_path=relative_path,
                size_bytes=stat.st_size,
                file_type=file_type,
                is_text=is_text,
                last_modified=stat.st_mtime
            )
        except (OSError, ValueError):
            return None
    
    def should_include_file(self, file_path: Path) -> Tuple[bool, str]:
        """Determine if a file should be included in filtering results.
        
        Returns:
            Tuple of (should_include, reason_if_excluded)
        """
        # Get file info
        file_info = self.get_file_info(file_path)
        if not file_info:
            return False, "file_not_accessible"
        
        # Check if it's a binary file
        if file_info.file_type == FileType.BINARY:
            return False, "binary_file"
        
        # Check if it's too large
        if file_info.size_bytes > self.max_file_size_bytes:
            return False, f"file_too_large_{file_info.size_bytes}_bytes"
        
        # Check gitignore patterns
        if self.gitignore_filter and self.gitignore_filter.should_ignore(file_path):
            return False, "gitignore_pattern"
        
        # Check default ignore patterns
        if self._matches_ignore_pattern(file_path):
            return False, "ignore_pattern"
        
        # Check if it's a text file
        if not file_info.is_text:
            return False, "not_text_file"
        
        return True, ""
    
    def filter_files(self, file_paths: List[Path]) -> Dict[str, List[FileInfo]]:
        """Filter a list of files and categorize them by type.
        
        Returns:
            Dictionary mapping file types to lists of FileInfo objects
        """
        results = {
            'included': [],
            'excluded': [],
            'by_type': {file_type.value: [] for file_type in FileType}
        }
        
        for file_path in file_paths:
            file_info = self.get_file_info(file_path)
            if not file_info:
                continue
            
            should_include, reason = self.should_include_file(file_path)
            
            if should_include:
                results['included'].append(file_info)
                results['by_type'][file_info.file_type.value].append(file_info)
            else:
                file_info.exclusion_reason = reason
                results['excluded'].append(file_info)
        
        return results
    
    def get_priority_files(self, file_infos: List[FileInfo], limit: int = 20) -> List[FileInfo]:
        """Get the highest priority files for inclusion in prompts.
        
        Prioritizes by:
        1. Source code files
        2. Configuration files
        3. Test files
        4. Documentation files
        """
        priority_order = [
            FileType.SOURCE_CODE,
            FileType.CONFIG,
            FileType.TEST,
            FileType.DOCUMENTATION,
            FileType.BUILD,
            FileType.UNKNOWN
        ]
        
        prioritized = []
        for file_type in priority_order:
            type_files = [f for f in file_infos if f.file_type == file_type]
            # Sort by size (smaller first) and last modified (newer first)
            type_files.sort(key=lambda f: (f.size_bytes, -f.last_modified))
            prioritized.extend(type_files)
        
        return prioritized[:limit]
    
    def scan_directory(self, max_files: int = 100) -> Dict[str, List[FileInfo]]:
        """Scan the root directory and return filtered file results."""
        all_files = []
        
        try:
            for file_path in self.root_path.rglob('*'):
                if file_path.is_file():
                    all_files.append(file_path)
                    # Limit total files scanned for performance
                    if len(all_files) >= max_files * 3:
                        break
        except (OSError, PermissionError):
            pass
        
        return self.filter_files(all_files)