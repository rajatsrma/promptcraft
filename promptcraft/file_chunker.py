"""
Smart file chunking system for PromptCraft CLI.

This module provides intelligent file chunking capabilities including:
- Function-level parsing for Python files
- Component-level parsing for JavaScript/TypeScript files
- Smart content extraction and preview
- Selective inclusion of specific functions/classes
"""

import ast
import re
from pathlib import Path
from typing import List, Dict, Optional, Tuple, Union
from dataclasses import dataclass
from enum import Enum


class ChunkType(Enum):
    """Types of code chunks that can be extracted."""
    FUNCTION = "function"
    CLASS = "class"
    METHOD = "method"
    COMPONENT = "component"
    HOOK = "hook"
    INTERFACE = "interface"
    TYPE = "type"
    IMPORT = "import"
    VARIABLE = "variable"
    COMMENT = "comment"


@dataclass
class CodeChunk:
    """Represents a chunk of code with metadata."""
    name: str
    chunk_type: ChunkType
    content: str
    start_line: int
    end_line: int
    file_path: str
    parent: Optional[str] = None  # For methods inside classes
    docstring: Optional[str] = None
    signature: Optional[str] = None
    complexity_score: int = 0  # Simple metric for code complexity


class PythonChunker:
    """Handles Python file parsing and chunking."""
    
    def __init__(self):
        self.chunks: List[CodeChunk] = []
    
    def parse_file(self, file_path: Path) -> List[CodeChunk]:
        """Parse a Python file and extract all functions, classes, and methods."""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Parse the AST
            tree = ast.parse(content)
            
            # Extract chunks
            chunks = []
            lines = content.splitlines()
            
            # Add imports as a single chunk
            import_lines = []
            for node in ast.walk(tree):
                if isinstance(node, (ast.Import, ast.ImportFrom)):
                    import_lines.extend(range(node.lineno - 1, node.end_lineno if node.end_lineno else node.lineno))
            
            if import_lines:
                import_content = '\n'.join(lines[min(import_lines):max(import_lines) + 1])
                chunks.append(CodeChunk(
                    name="imports",
                    chunk_type=ChunkType.IMPORT,
                    content=import_content,
                    start_line=min(import_lines) + 1,
                    end_line=max(import_lines) + 1,
                    file_path=str(file_path)
                ))
            
            # Extract classes and functions
            for node in ast.walk(tree):
                if isinstance(node, ast.ClassDef):
                    chunks.extend(self._extract_class(node, lines, str(file_path)))
                elif isinstance(node, ast.FunctionDef):
                    # Only top-level functions (not methods)
                    if not any(isinstance(parent, ast.ClassDef) for parent in ast.walk(tree) 
                             if hasattr(parent, 'body') and node in getattr(parent, 'body', [])):
                        chunks.append(self._extract_function(node, lines, str(file_path)))
            
            return chunks
            
        except Exception as e:
            # If parsing fails, return the whole file as one chunk
            return [self._create_fallback_chunk(file_path)]
    
    def _extract_class(self, node: ast.ClassDef, lines: List[str], file_path: str) -> List[CodeChunk]:
        """Extract a class and its methods as separate chunks."""
        chunks = []
        
        # Extract class definition
        class_content = self._get_node_content(node, lines)
        docstring = self._extract_docstring(node)
        
        # Calculate complexity based on methods and lines
        complexity = len(node.body) + (node.end_lineno - node.lineno)
        
        chunks.append(CodeChunk(
            name=node.name,
            chunk_type=ChunkType.CLASS,
            content=class_content,
            start_line=node.lineno,
            end_line=node.end_lineno or node.lineno,
            file_path=file_path,
            docstring=docstring,
            signature=f"class {node.name}",
            complexity_score=complexity
        ))
        
        # Extract methods
        for item in node.body:
            if isinstance(item, ast.FunctionDef):
                method_chunk = self._extract_function(item, lines, file_path, parent=node.name)
                chunks.append(method_chunk)
        
        return chunks
    
    def _extract_function(self, node: ast.FunctionDef, lines: List[str], file_path: str, parent: Optional[str] = None) -> CodeChunk:
        """Extract a function or method as a chunk."""
        content = self._get_node_content(node, lines)
        docstring = self._extract_docstring(node)
        
        # Build signature
        args = []
        for arg in node.args.args:
            args.append(arg.arg)
        signature = f"def {node.name}({', '.join(args)})"
        
        # Calculate complexity
        complexity = len(node.body) + (node.end_lineno - node.lineno)
        
        chunk_type = ChunkType.METHOD if parent else ChunkType.FUNCTION
        
        return CodeChunk(
            name=node.name,
            chunk_type=chunk_type,
            content=content,
            start_line=node.lineno,
            end_line=node.end_lineno or node.lineno,
            file_path=file_path,
            parent=parent,
            docstring=docstring,
            signature=signature,
            complexity_score=complexity
        )
    
    def _get_node_content(self, node: ast.AST, lines: List[str]) -> str:
        """Get the source code content for an AST node."""
        start_line = node.lineno - 1
        end_line = (node.end_lineno or node.lineno) - 1
        return '\n'.join(lines[start_line:end_line + 1])
    
    def _extract_docstring(self, node: Union[ast.ClassDef, ast.FunctionDef]) -> Optional[str]:
        """Extract docstring from a class or function node."""
        if (node.body and 
            isinstance(node.body[0], ast.Expr) and 
            isinstance(node.body[0].value, ast.Str)):
            return node.body[0].value.s
        elif (node.body and 
              isinstance(node.body[0], ast.Expr) and 
              isinstance(node.body[0].value, ast.Constant) and 
              isinstance(node.body[0].value.value, str)):
            return node.body[0].value.value
        return None
    
    def _create_fallback_chunk(self, file_path: Path) -> CodeChunk:
        """Create a fallback chunk when parsing fails."""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            return CodeChunk(
                name=file_path.stem,
                chunk_type=ChunkType.VARIABLE,
                content=content,
                start_line=1,
                end_line=len(content.splitlines()),
                file_path=str(file_path)
            )
        except Exception:
            return CodeChunk(
                name=file_path.stem,
                chunk_type=ChunkType.VARIABLE,
                content="# Unable to read file",
                start_line=1,
                end_line=1,
                file_path=str(file_path)
            )


class JavaScriptChunker:
    """Handles JavaScript/TypeScript file parsing and chunking."""
    
    def __init__(self):
        self.chunks: List[CodeChunk] = []
    
    def parse_file(self, file_path: Path) -> List[CodeChunk]:
        """Parse a JavaScript/TypeScript file and extract components, functions, etc."""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            chunks = []
            lines = content.splitlines()
            
            # Extract imports
            import_chunk = self._extract_imports(content, lines, str(file_path))
            if import_chunk:
                chunks.append(import_chunk)
            
            # Extract various JS/TS constructs
            chunks.extend(self._extract_functions(content, lines, str(file_path)))
            chunks.extend(self._extract_classes(content, lines, str(file_path)))
            chunks.extend(self._extract_components(content, lines, str(file_path)))
            chunks.extend(self._extract_hooks(content, lines, str(file_path)))
            chunks.extend(self._extract_interfaces_types(content, lines, str(file_path)))
            
            return chunks if chunks else [self._create_fallback_chunk(file_path)]
            
        except Exception:
            return [self._create_fallback_chunk(file_path)]
    
    def _extract_imports(self, content: str, lines: List[str], file_path: str) -> Optional[CodeChunk]:
        """Extract import statements."""
        import_pattern = r'^(import|export).*?(?:from\s+[\'"][^\'"]*[\'"]|[\'"][^\'"]*[\'"])?;?$'
        import_lines = []
        
        for i, line in enumerate(lines):
            if re.match(import_pattern, line.strip()):
                import_lines.append(i)
        
        if not import_lines:
            return None
        
        # Group consecutive import lines
        import_content = '\n'.join(lines[min(import_lines):max(import_lines) + 1])
        
        return CodeChunk(
            name="imports",
            chunk_type=ChunkType.IMPORT,
            content=import_content,
            start_line=min(import_lines) + 1,
            end_line=max(import_lines) + 1,
            file_path=file_path
        )
    
    def _extract_functions(self, content: str, lines: List[str], file_path: str) -> List[CodeChunk]:
        """Extract function declarations and arrow functions."""
        chunks = []
        
        # Regular function declarations
        function_pattern = r'^(?:export\s+)?(?:async\s+)?function\s+(\w+)\s*\([^)]*\)\s*\{'
        arrow_pattern = r'^(?:export\s+)?(?:const|let|var)\s+(\w+)\s*=\s*(?:async\s+)?\([^)]*\)\s*=>\s*\{'
        
        chunks.extend(self._extract_by_pattern(content, lines, file_path, function_pattern, ChunkType.FUNCTION))
        chunks.extend(self._extract_by_pattern(content, lines, file_path, arrow_pattern, ChunkType.FUNCTION))
        
        return chunks
    
    def _extract_classes(self, content: str, lines: List[str], file_path: str) -> List[CodeChunk]:
        """Extract class declarations."""
        class_pattern = r'^(?:export\s+)?(?:abstract\s+)?class\s+(\w+)(?:\s+extends\s+\w+)?(?:\s+implements\s+[\w,\s]+)?\s*\{'
        return self._extract_by_pattern(content, lines, file_path, class_pattern, ChunkType.CLASS)
    
    def _extract_components(self, content: str, lines: List[str], file_path: str) -> List[CodeChunk]:
        """Extract React components."""
        chunks = []
        
        # Function components
        component_patterns = [
            r'^(?:export\s+)?(?:const|function)\s+([A-Z]\w*)\s*(?:\([^)]*\))?\s*(?::\s*React\.FC)?(?:<[^>]*>)?\s*[=\{]',
            r'^(?:export\s+)?(?:const|let)\s+([A-Z]\w*)\s*:\s*React\.FC(?:<[^>]*>)?\s*=',
        ]
        
        for pattern in component_patterns:
            chunks.extend(self._extract_by_pattern(content, lines, file_path, pattern, ChunkType.COMPONENT))
        
        return chunks
    
    def _extract_hooks(self, content: str, lines: List[str], file_path: str) -> List[CodeChunk]:
        """Extract React hooks (functions starting with 'use')."""
        hook_pattern = r'^(?:export\s+)?(?:const|function)\s+(use[A-Z]\w*)\s*[=\(]'
        return self._extract_by_pattern(content, lines, file_path, hook_pattern, ChunkType.HOOK)
    
    def _extract_interfaces_types(self, content: str, lines: List[str], file_path: str) -> List[CodeChunk]:
        """Extract TypeScript interfaces and type definitions."""
        chunks = []
        
        interface_pattern = r'^(?:export\s+)?interface\s+(\w+)(?:\s+extends\s+[\w,\s]+)?\s*\{'
        type_pattern = r'^(?:export\s+)?type\s+(\w+)(?:<[^>]*>)?\s*='
        
        chunks.extend(self._extract_by_pattern(content, lines, file_path, interface_pattern, ChunkType.INTERFACE))
        chunks.extend(self._extract_by_pattern(content, lines, file_path, type_pattern, ChunkType.TYPE))
        
        return chunks
    
    def _extract_by_pattern(self, content: str, lines: List[str], file_path: str, 
                           pattern: str, chunk_type: ChunkType) -> List[CodeChunk]:
        """Extract code chunks based on regex pattern."""
        chunks = []
        
        for i, line in enumerate(lines):
            match = re.match(pattern, line.strip())
            if match:
                name = match.group(1)
                start_line = i + 1
                end_line = self._find_block_end(lines, i)
                
                content_lines = lines[i:end_line]
                chunk_content = '\n'.join(content_lines)
                
                # Calculate complexity
                complexity = len(content_lines) + chunk_content.count('{') + chunk_content.count('if') + chunk_content.count('for')
                
                chunks.append(CodeChunk(
                    name=name,
                    chunk_type=chunk_type,
                    content=chunk_content,
                    start_line=start_line,
                    end_line=end_line,
                    file_path=file_path,
                    signature=line.strip(),
                    complexity_score=complexity
                ))
        
        return chunks
    
    def _find_block_end(self, lines: List[str], start_idx: int) -> int:
        """Find the end of a code block starting from start_idx."""
        brace_count = 0
        in_string = False
        string_char = None
        
        for i in range(start_idx, len(lines)):
            line = lines[i]
            
            j = 0
            while j < len(line):
                char = line[j]
                
                # Handle string literals
                if not in_string and char in ['"', "'", '`']:
                    in_string = True
                    string_char = char
                elif in_string and char == string_char:
                    # Check if it's escaped
                    if j == 0 or line[j-1] != '\\':
                        in_string = False
                        string_char = None
                
                # Count braces outside strings
                if not in_string:
                    if char == '{':
                        brace_count += 1
                    elif char == '}':
                        brace_count -= 1
                        if brace_count == 0:
                            return i + 1
                
                j += 1
        
        return len(lines)
    
    def _create_fallback_chunk(self, file_path: Path) -> CodeChunk:
        """Create a fallback chunk when parsing fails."""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            return CodeChunk(
                name=file_path.stem,
                chunk_type=ChunkType.VARIABLE,
                content=content,
                start_line=1,
                end_line=len(content.splitlines()),
                file_path=str(file_path)
            )
        except Exception:
            return CodeChunk(
                name=file_path.stem,
                chunk_type=ChunkType.VARIABLE,
                content="// Unable to read file",
                start_line=1,
                end_line=1,
                file_path=str(file_path)
            )


class SmartFileChunker:
    """Main chunker class that handles different file types."""
    
    def __init__(self):
        self.python_chunker = PythonChunker()
        self.js_chunker = JavaScriptChunker()
    
    def chunk_file(self, file_path: Path, max_lines: int = 100) -> List[CodeChunk]:
        """Chunk a file based on its type and content."""
        extension = file_path.suffix.lower()
        
        if extension == '.py':
            chunks = self.python_chunker.parse_file(file_path)
        elif extension in ['.js', '.jsx', '.ts', '.tsx']:
            chunks = self.js_chunker.parse_file(file_path)
        else:
            # For other files, use simple line-based chunking
            chunks = self._chunk_by_lines(file_path, max_lines)
        
        return chunks
    
    def _chunk_by_lines(self, file_path: Path, max_lines: int) -> List[CodeChunk]:
        """Chunk a file by lines when no specific parser is available."""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                lines = f.readlines()
            
            chunks = []
            for i in range(0, len(lines), max_lines):
                chunk_lines = lines[i:i + max_lines]
                chunk_content = ''.join(chunk_lines)
                
                chunks.append(CodeChunk(
                    name=f"{file_path.stem}_chunk_{i//max_lines + 1}",
                    chunk_type=ChunkType.VARIABLE,
                    content=chunk_content,
                    start_line=i + 1,
                    end_line=min(i + max_lines, len(lines)),
                    file_path=str(file_path)
                ))
            
            return chunks
            
        except Exception:
            return [CodeChunk(
                name=file_path.stem,
                chunk_type=ChunkType.VARIABLE,
                content="# Unable to read file",
                start_line=1,
                end_line=1,
                file_path=str(file_path)
            )]
    
    def get_chunk_preview(self, chunk: CodeChunk, max_lines: int = 10) -> str:
        """Get a preview of a chunk's content."""
        lines = chunk.content.splitlines()
        
        if len(lines) <= max_lines:
            return chunk.content
        
        preview_lines = lines[:max_lines]
        remaining = len(lines) - max_lines
        
        preview = '\n'.join(preview_lines)
        preview += f'\n... ({remaining} more lines)'
        
        return preview
    
    def filter_chunks_by_type(self, chunks: List[CodeChunk], chunk_types: List[ChunkType]) -> List[CodeChunk]:
        """Filter chunks by their type."""
        return [chunk for chunk in chunks if chunk.chunk_type in chunk_types]
    
    def get_chunks_by_complexity(self, chunks: List[CodeChunk], max_complexity: int = 50) -> List[CodeChunk]:
        """Get chunks with complexity below threshold."""
        return [chunk for chunk in chunks if chunk.complexity_score <= max_complexity]
    
    def search_chunks_by_name(self, chunks: List[CodeChunk], search_term: str) -> List[CodeChunk]:
        """Search for chunks by name (case-insensitive)."""
        search_term = search_term.lower()
        return [chunk for chunk in chunks if search_term in chunk.name.lower()]
    
    def get_chunk_summary(self, chunks: List[CodeChunk]) -> Dict[str, int]:
        """Get a summary of chunks by type."""
        summary = {}
        for chunk in chunks:
            chunk_type = chunk.chunk_type.value
            summary[chunk_type] = summary.get(chunk_type, 0) + 1
        return summary