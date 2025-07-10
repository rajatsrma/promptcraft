"""
Enhanced file browser with preview, metadata, and selection capabilities.

This module provides an interactive file browser that integrates with the
smart file filtering and chunking systems to provide comprehensive file
exploration and selection functionality.
"""

import os
import mimetypes
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Optional, Tuple, Any
from dataclasses import dataclass, field
from enum import Enum

from .file_filter import SmartFileFilter, FileInfo, FileType
from .file_chunker import SmartFileChunker, CodeChunk, ChunkType


class SortOrder(Enum):
    """File sorting options."""
    NAME_ASC = "name_asc"
    NAME_DESC = "name_desc"
    SIZE_ASC = "size_asc"
    SIZE_DESC = "size_desc"
    MODIFIED_ASC = "modified_asc"
    MODIFIED_DESC = "modified_desc"
    TYPE_ASC = "type_asc"
    TYPE_DESC = "type_desc"


@dataclass
class FileMetadata:
    """Extended file metadata for display."""
    path: Path
    relative_path: str
    size_bytes: int
    size_human: str
    last_modified: datetime
    file_type: FileType
    mime_type: Optional[str]
    is_binary: bool
    is_text: bool
    line_count: Optional[int] = None
    encoding: Optional[str] = None
    preview: Optional[str] = None
    chunks: List[CodeChunk] = field(default_factory=list)


@dataclass
class LineRange:
    """Represents a range of lines in a file."""
    start: int
    end: int
    
    def __post_init__(self):
        if self.start < 1:
            raise ValueError("Line numbers must start from 1")
        if self.end < self.start:
            raise ValueError("End line must be >= start line")
    
    def __str__(self) -> str:
        if self.start == self.end:
            return f"line {self.start}"
        return f"lines {self.start}-{self.end}"


@dataclass
class FileSelection:
    """Represents a file selection with optional line range or chunks."""
    file_info: FileMetadata
    line_range: Optional[LineRange] = None
    selected_chunks: List[CodeChunk] = field(default_factory=list)
    include_whole_file: bool = True
    
    def get_content(self) -> str:
        """Get the selected content from the file."""
        if self.selected_chunks:
            return '\n\n'.join(chunk.content for chunk in self.selected_chunks)
        
        try:
            with open(self.file_info.path, 'r', encoding='utf-8') as f:
                if self.line_range:
                    lines = f.readlines()
                    start_idx = self.line_range.start - 1
                    end_idx = self.line_range.end
                    return ''.join(lines[start_idx:end_idx])
                else:
                    return f.read()
        except Exception:
            return "# Unable to read file content"


class EnhancedFileBrowser:
    """Enhanced file browser with preview, metadata, and selection capabilities."""
    
    def __init__(self, 
                 root_path: Path,
                 max_preview_lines: int = 20,
                 max_file_size_mb: float = 1.0):
        """Initialize the enhanced file browser.
        
        Args:
            root_path: Root directory for file browsing
            max_preview_lines: Maximum lines to show in preview
            max_file_size_mb: Maximum file size for processing
        """
        self.root_path = Path(root_path)
        self.max_preview_lines = max_preview_lines
        self.max_file_size_mb = max_file_size_mb
        
        # Initialize components
        self.file_filter = SmartFileFilter(root_path, max_file_size_mb)
        self.file_chunker = SmartFileChunker()
        
        # Cache for file metadata
        self._metadata_cache: Dict[str, FileMetadata] = {}
    
    def get_file_metadata(self, file_path: Path, include_chunks: bool = True) -> Optional[FileMetadata]:
        """Get comprehensive metadata for a file."""
        cache_key = str(file_path)
        
        # Check cache first
        if cache_key in self._metadata_cache and not include_chunks:
            return self._metadata_cache[cache_key]
        
        try:
            if not file_path.exists() or not file_path.is_file():
                return None
            
            stat = file_path.stat()
            relative_path = str(file_path.relative_to(self.root_path))
            
            # Get file type and basic info
            file_info = self.file_filter.get_file_info(file_path)
            if not file_info:
                return None
            
            # Get MIME type
            mime_type, _ = mimetypes.guess_type(str(file_path))
            
            # Determine if file is binary
            is_binary = file_info.file_type == FileType.BINARY
            is_text = file_info.is_text
            
            # Get encoding and line count for text files
            line_count = None
            encoding = None
            preview = None
            
            if is_text and not is_binary:
                try:
                    with open(file_path, 'r', encoding='utf-8') as f:
                        lines = f.readlines()
                        line_count = len(lines)
                        encoding = 'utf-8'
                        
                        # Generate preview
                        preview_lines = lines[:self.max_preview_lines]
                        preview = ''.join(preview_lines)
                        
                        if len(lines) > self.max_preview_lines:
                            remaining = len(lines) - self.max_preview_lines
                            preview += f'\n... ({remaining} more lines)'
                            
                except UnicodeDecodeError:
                    # Try other encodings
                    for enc in ['latin-1', 'cp1252', 'utf-16']:
                        try:
                            with open(file_path, 'r', encoding=enc) as f:
                                lines = f.readlines()
                                line_count = len(lines)
                                encoding = enc
                                preview_lines = lines[:self.max_preview_lines]
                                preview = ''.join(preview_lines)
                                break
                        except UnicodeDecodeError:
                            continue
                    else:
                        # If all encodings fail, treat as binary
                        is_binary = True
                        is_text = False
                except Exception:
                    pass
            
            # Get chunks if requested
            chunks = []
            if include_chunks and is_text and not is_binary:
                try:
                    chunks = self.file_chunker.chunk_file(file_path)
                except Exception:
                    pass
            
            # Create metadata object
            metadata = FileMetadata(
                path=file_path,
                relative_path=relative_path,
                size_bytes=stat.st_size,
                size_human=self._format_file_size(stat.st_size),
                last_modified=datetime.fromtimestamp(stat.st_mtime),
                file_type=file_info.file_type,
                mime_type=mime_type,
                is_binary=is_binary,
                is_text=is_text,
                line_count=line_count,
                encoding=encoding,
                preview=preview,
                chunks=chunks
            )
            
            # Cache metadata (without chunks to save memory)
            if not include_chunks:
                self._metadata_cache[cache_key] = metadata
            
            return metadata
            
        except Exception:
            return None
    
    def _format_file_size(self, size_bytes: int) -> str:
        """Format file size in human-readable format."""
        for unit in ['B', 'KB', 'MB', 'GB']:
            if size_bytes < 1024.0:
                return f"{size_bytes:.1f} {unit}"
            size_bytes /= 1024.0
        return f"{size_bytes:.1f} TB"
    
    def scan_directory(self, 
                      include_subdirs: bool = True,
                      max_files: int = 500,
                      file_types: Optional[List[FileType]] = None) -> List[FileMetadata]:
        """Scan directory and return file metadata."""
        results = []
        
        try:
            pattern = "**/*" if include_subdirs else "*"
            
            for file_path in self.root_path.glob(pattern):
                if file_path.is_file():
                    # Check if we should include this file
                    should_include, _ = self.file_filter.should_include_file(file_path)
                    if not should_include:
                        continue
                    
                    # Get metadata
                    metadata = self.get_file_metadata(file_path, include_chunks=False)
                    if metadata:
                        # Filter by file type if specified
                        if file_types and metadata.file_type not in file_types:
                            continue
                        
                        results.append(metadata)
                    
                    # Limit results for performance
                    if len(results) >= max_files:
                        break
                        
        except Exception:
            pass
        
        return results
    
    def sort_files(self, files: List[FileMetadata], sort_order: SortOrder) -> List[FileMetadata]:
        """Sort files by specified criteria."""
        if sort_order == SortOrder.NAME_ASC:
            return sorted(files, key=lambda f: f.path.name.lower())
        elif sort_order == SortOrder.NAME_DESC:
            return sorted(files, key=lambda f: f.path.name.lower(), reverse=True)
        elif sort_order == SortOrder.SIZE_ASC:
            return sorted(files, key=lambda f: f.size_bytes)
        elif sort_order == SortOrder.SIZE_DESC:
            return sorted(files, key=lambda f: f.size_bytes, reverse=True)
        elif sort_order == SortOrder.MODIFIED_ASC:
            return sorted(files, key=lambda f: f.last_modified)
        elif sort_order == SortOrder.MODIFIED_DESC:
            return sorted(files, key=lambda f: f.last_modified, reverse=True)
        elif sort_order == SortOrder.TYPE_ASC:
            return sorted(files, key=lambda f: f.file_type.value)
        elif sort_order == SortOrder.TYPE_DESC:
            return sorted(files, key=lambda f: f.file_type.value, reverse=True)
        else:
            return files
    
    def search_files(self, files: List[FileMetadata], query: str) -> List[FileMetadata]:
        """Search files by name or content."""
        query = query.lower()
        results = []
        
        for file_metadata in files:
            # Search by filename
            if query in file_metadata.path.name.lower():
                results.append(file_metadata)
                continue
            
            # Search by file content preview
            if file_metadata.preview and query in file_metadata.preview.lower():
                results.append(file_metadata)
                continue
        
        return results
    
    def get_file_preview(self, file_path: Path, max_lines: Optional[int] = None) -> str:
        """Get a preview of file content."""
        max_lines = max_lines or self.max_preview_lines
        
        metadata = self.get_file_metadata(file_path, include_chunks=False)
        if not metadata:
            return "# Unable to read file"
        
        if metadata.is_binary:
            return f"# Binary file ({metadata.size_human})\n# MIME type: {metadata.mime_type or 'unknown'}"
        
        if metadata.preview:
            lines = metadata.preview.splitlines()
            if len(lines) > max_lines:
                preview_lines = lines[:max_lines]
                remaining = len(lines) - max_lines
                return '\n'.join(preview_lines) + f'\n... ({remaining} more lines)'
            return metadata.preview
        
        return "# Unable to generate preview"
    
    def get_file_chunks(self, file_path: Path) -> List[CodeChunk]:
        """Get code chunks for a file."""
        metadata = self.get_file_metadata(file_path, include_chunks=True)
        if metadata:
            return metadata.chunks
        return []
    
    def create_line_range_selection(self, 
                                   file_path: Path, 
                                   start_line: int, 
                                   end_line: int) -> Optional[FileSelection]:
        """Create a file selection with specific line range."""
        metadata = self.get_file_metadata(file_path, include_chunks=False)
        if not metadata:
            return None
        
        try:
            line_range = LineRange(start_line, end_line)
            
            # Validate line range against file
            if metadata.line_count and end_line > metadata.line_count:
                raise ValueError(f"End line {end_line} exceeds file length {metadata.line_count}")
            
            return FileSelection(
                file_info=metadata,
                line_range=line_range,
                include_whole_file=False
            )
            
        except ValueError as e:
            return None
    
    def create_chunk_selection(self, 
                              file_path: Path, 
                              chunk_names: List[str]) -> Optional[FileSelection]:
        """Create a file selection with specific code chunks."""
        metadata = self.get_file_metadata(file_path, include_chunks=True)
        if not metadata:
            return None
        
        # Find matching chunks
        selected_chunks = []
        for chunk in metadata.chunks:
            if chunk.name in chunk_names:
                selected_chunks.append(chunk)
        
        if not selected_chunks:
            return None
        
        return FileSelection(
            file_info=metadata,
            selected_chunks=selected_chunks,
            include_whole_file=False
        )
    
    def get_selection_summary(self, selection: FileSelection) -> str:
        """Get a summary of what's included in a file selection."""
        if selection.selected_chunks:
            chunk_names = [chunk.name for chunk in selection.selected_chunks]
            return f"Selected chunks: {', '.join(chunk_names)}"
        elif selection.line_range:
            return f"Selected {selection.line_range}"
        else:
            return f"Whole file ({selection.file_info.size_human})"
    
    def export_selection_metadata(self, selections: List[FileSelection]) -> Dict[str, Any]:
        """Export metadata about file selections."""
        metadata = {
            'timestamp': datetime.now().isoformat(),
            'root_path': str(self.root_path),
            'total_files': len(selections),
            'total_size_bytes': sum(s.file_info.size_bytes for s in selections),
            'files': []
        }
        
        for selection in selections:
            file_meta = {
                'path': selection.file_info.relative_path,
                'size_bytes': selection.file_info.size_bytes,
                'file_type': selection.file_info.file_type.value,
                'last_modified': selection.file_info.last_modified.isoformat(),
                'selection_type': 'whole_file' if selection.include_whole_file else 'partial'
            }
            
            if selection.line_range:
                file_meta['line_range'] = {
                    'start': selection.line_range.start,
                    'end': selection.line_range.end
                }
            
            if selection.selected_chunks:
                file_meta['chunks'] = [
                    {
                        'name': chunk.name,
                        'type': chunk.chunk_type.value,
                        'lines': f"{chunk.start_line}-{chunk.end_line}",
                        'complexity': chunk.complexity_score
                    }
                    for chunk in selection.selected_chunks
                ]
            
            metadata['files'].append(file_meta)
        
        return metadata