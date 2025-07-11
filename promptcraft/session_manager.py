"""
Enhanced session management system for PromptCraft CLI.

This module provides comprehensive session storage, search, filtering, and management
capabilities with metadata tracking, favorites, and import/export functionality.
"""

import json
import os
import uuid
from datetime import datetime, timedelta
from pathlib import Path
from typing import List, Dict, Optional, Any, Union
from dataclasses import dataclass, asdict, field
from enum import Enum
import re
import shutil

from .models import PromptData


class SessionStatus(Enum):
    """Session status options."""
    ACTIVE = "active"
    COMPLETED = "completed"
    ARCHIVED = "archived"
    DRAFT = "draft"


@dataclass
class SessionMetadata:
    """Enhanced session metadata."""
    id: str
    name: str
    created_at: datetime
    last_used: datetime
    tags: List[str] = field(default_factory=list)
    favorite: bool = False
    success_rating: Optional[int] = None  # 1-5 scale
    status: SessionStatus = SessionStatus.ACTIVE
    description: Optional[str] = None
    project_path: Optional[str] = None
    data: Optional[PromptData] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        result = {
            'id': self.id,
            'name': self.name,
            'created_at': self.created_at.isoformat(),
            'last_used': self.last_used.isoformat(),
            'tags': self.tags,
            'favorite': self.favorite,
            'success_rating': self.success_rating,
            'status': self.status.value,
            'description': self.description,
            'project_path': self.project_path,
            'data': asdict(self.data) if self.data else None
        }
        return result
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'SessionMetadata':
        """Create from dictionary (JSON deserialization)."""
        # Convert datetime strings back to datetime objects
        created_at = datetime.fromisoformat(data['created_at'])
        last_used = datetime.fromisoformat(data['last_used'])
        
        # Convert status string back to enum
        status = SessionStatus(data.get('status', SessionStatus.ACTIVE.value))
        
        # Convert data dict back to PromptData
        prompt_data = None
        if data.get('data'):
            prompt_data = PromptData(**data['data'])
        
        return cls(
            id=data['id'],
            name=data['name'],
            created_at=created_at,
            last_used=last_used,
            tags=data.get('tags', []),
            favorite=data.get('favorite', False),
            success_rating=data.get('success_rating'),
            status=status,
            description=data.get('description'),
            project_path=data.get('project_path'),
            data=prompt_data
        )


@dataclass
class SessionSearchFilter:
    """Filter criteria for session search."""
    query: Optional[str] = None
    tags: Optional[List[str]] = None
    favorite: Optional[bool] = None
    status: Optional[SessionStatus] = None
    success_rating_min: Optional[int] = None
    success_rating_max: Optional[int] = None
    date_from: Optional[datetime] = None
    date_to: Optional[datetime] = None
    limit: Optional[int] = None


class EnhancedSessionManager:
    """Enhanced session manager with metadata, search, and favorites."""
    
    def __init__(self, session_dir: str = ".promptcraft"):
        """Initialize the session manager.
        
        Args:
            session_dir: Directory to store session files
        """
        self.session_dir = Path(session_dir)
        self.session_dir.mkdir(exist_ok=True)
        
        # File paths
        self.sessions_index_path = self.session_dir / "sessions_index.json"
        self.sessions_data_dir = self.session_dir / "sessions"
        self.sessions_data_dir.mkdir(exist_ok=True)
        
        # Load existing sessions index
        self._sessions_index: Dict[str, SessionMetadata] = {}
        self._load_sessions_index()
        
        # Migrate legacy sessions if they exist
        self._migrate_legacy_sessions()
    
    def _load_sessions_index(self) -> None:
        """Load sessions index from disk."""
        if self.sessions_index_path.exists():
            try:
                with open(self.sessions_index_path, 'r', encoding='utf-8') as f:
                    index_data = json.load(f)
                
                for session_id, session_data in index_data.items():
                    self._sessions_index[session_id] = SessionMetadata.from_dict(session_data)
            except (json.JSONDecodeError, KeyError, ValueError):
                # If index is corrupted, rebuild it
                self._rebuild_sessions_index()
    
    def _save_sessions_index(self) -> None:
        """Save sessions index to disk."""
        index_data = {}
        for session_id, session_meta in self._sessions_index.items():
            index_data[session_id] = session_meta.to_dict()
        
        with open(self.sessions_index_path, 'w', encoding='utf-8') as f:
            json.dump(index_data, f, indent=2, ensure_ascii=False)
    
    def _rebuild_sessions_index(self) -> None:
        """Rebuild sessions index from session files."""
        self._sessions_index = {}
        
        # Scan sessions data directory
        for session_file in self.sessions_data_dir.glob("*.json"):
            try:
                session_id = session_file.stem
                session_meta = self._load_session_metadata(session_id)
                if session_meta:
                    self._sessions_index[session_id] = session_meta
            except Exception:
                continue
    
    def _load_session_metadata(self, session_id: str) -> Optional[SessionMetadata]:
        """Load session metadata from file."""
        session_file = self.sessions_data_dir / f"{session_id}.json"
        
        if not session_file.exists():
            return None
        
        try:
            with open(session_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            return SessionMetadata.from_dict(data)
        except (json.JSONDecodeError, KeyError, ValueError):
            return None
    
    def _save_session_metadata(self, session_meta: SessionMetadata) -> None:
        """Save session metadata to file."""
        session_file = self.sessions_data_dir / f"{session_meta.id}.json"
        
        with open(session_file, 'w', encoding='utf-8') as f:
            json.dump(session_meta.to_dict(), f, indent=2, ensure_ascii=False)
    
    def _migrate_legacy_sessions(self) -> None:
        """Migrate legacy session files to new format."""
        # Look for legacy .json files in the session directory
        legacy_files = [f for f in self.session_dir.glob("*.json") 
                       if f.name != "sessions_index.json"]
        
        for legacy_file in legacy_files:
            try:
                with open(legacy_file, 'r', encoding='utf-8') as f:
                    legacy_data = json.load(f)
                
                # Check if this is a legacy session (has PromptData structure)
                if self._is_legacy_session(legacy_data):
                    # Create new session metadata
                    session_name = legacy_file.stem.replace('_', ' ')
                    session_id = str(uuid.uuid4())
                    
                    # Get file timestamps
                    stat = legacy_file.stat()
                    created_at = datetime.fromtimestamp(stat.st_ctime)
                    last_used = datetime.fromtimestamp(stat.st_mtime)
                    
                    # Create PromptData from legacy data
                    prompt_data = PromptData(
                        persona=legacy_data.get('persona'),
                        task=legacy_data.get('task'),
                        context=legacy_data.get('context'),
                        schemas=legacy_data.get('schemas', []),
                        examples=legacy_data.get('examples', []),
                        constraints=legacy_data.get('constraints')
                    )
                    
                    # Create session metadata
                    session_meta = SessionMetadata(
                        id=session_id,
                        name=session_name,
                        created_at=created_at,
                        last_used=last_used,
                        data=prompt_data,
                        status=SessionStatus.ACTIVE
                    )
                    
                    # Save new session
                    self._save_session_metadata(session_meta)
                    self._sessions_index[session_id] = session_meta
                    
                    # Move legacy file to backup
                    backup_dir = self.session_dir / "legacy_backup"
                    backup_dir.mkdir(exist_ok=True)
                    shutil.move(str(legacy_file), str(backup_dir / legacy_file.name))
                    
            except Exception:
                continue
        
        # Save updated index
        if legacy_files:
            self._save_sessions_index()
    
    def _is_legacy_session(self, data: Dict[str, Any]) -> bool:
        """Check if data represents a legacy session."""
        # Legacy sessions have PromptData structure without metadata
        legacy_keys = {'persona', 'task', 'context', 'schemas', 'examples', 'constraints'}
        return any(key in data for key in legacy_keys) and 'id' not in data
    
    def create_session(self, 
                      name: str, 
                      data: PromptData,
                      tags: Optional[List[str]] = None,
                      description: Optional[str] = None) -> SessionMetadata:
        """Create a new session with metadata."""
        session_id = str(uuid.uuid4())
        now = datetime.now()
        
        # Get current project path
        project_path = str(Path.cwd())
        
        session_meta = SessionMetadata(
            id=session_id,
            name=name,
            created_at=now,
            last_used=now,
            tags=tags or [],
            description=description,
            project_path=project_path,
            data=data,
            status=SessionStatus.ACTIVE
        )
        
        # Save session
        self._save_session_metadata(session_meta)
        self._sessions_index[session_id] = session_meta
        self._save_sessions_index()
        
        return session_meta
    
    def get_session(self, session_id: str) -> Optional[SessionMetadata]:
        """Get a session by ID."""
        return self._sessions_index.get(session_id)
    
    def get_session_by_name(self, name: str) -> Optional[SessionMetadata]:
        """Get a session by name (returns first match)."""
        for session_meta in self._sessions_index.values():
            if session_meta.name == name:
                return session_meta
        return None
    
    def update_session(self, session_meta: SessionMetadata) -> None:
        """Update an existing session."""
        session_meta.last_used = datetime.now()
        
        self._save_session_metadata(session_meta)
        self._sessions_index[session_meta.id] = session_meta
        self._save_sessions_index()
    
    def delete_session(self, session_id: str) -> bool:
        """Delete a session."""
        if session_id not in self._sessions_index:
            return False
        
        # Remove from index
        del self._sessions_index[session_id]
        
        # Remove file
        session_file = self.sessions_data_dir / f"{session_id}.json"
        if session_file.exists():
            session_file.unlink()
        
        # Update index
        self._save_sessions_index()
        
        return True
    
    def search_sessions(self, filter_criteria: SessionSearchFilter) -> List[SessionMetadata]:
        """Search sessions based on filter criteria."""
        results = list(self._sessions_index.values())
        
        # Apply filters
        if filter_criteria.query:
            query_lower = filter_criteria.query.lower()
            results = [s for s in results if 
                      query_lower in s.name.lower() or 
                      (s.description and query_lower in s.description.lower()) or
                      any(query_lower in tag.lower() for tag in s.tags)]
        
        if filter_criteria.tags:
            results = [s for s in results if 
                      any(tag in s.tags for tag in filter_criteria.tags)]
        
        if filter_criteria.favorite is not None:
            results = [s for s in results if s.favorite == filter_criteria.favorite]
        
        if filter_criteria.status:
            results = [s for s in results if s.status == filter_criteria.status]
        
        if filter_criteria.success_rating_min is not None:
            results = [s for s in results if 
                      s.success_rating is not None and 
                      s.success_rating >= filter_criteria.success_rating_min]
        
        if filter_criteria.success_rating_max is not None:
            results = [s for s in results if 
                      s.success_rating is not None and 
                      s.success_rating <= filter_criteria.success_rating_max]
        
        if filter_criteria.date_from:
            results = [s for s in results if s.created_at >= filter_criteria.date_from]
        
        if filter_criteria.date_to:
            results = [s for s in results if s.created_at <= filter_criteria.date_to]
        
        # Sort by last used (most recent first)
        results.sort(key=lambda s: s.last_used, reverse=True)
        
        # Apply limit
        if filter_criteria.limit:
            results = results[:filter_criteria.limit]
        
        return results
    
    def get_all_sessions(self) -> List[SessionMetadata]:
        """Get all sessions sorted by last used."""
        sessions = list(self._sessions_index.values())
        sessions.sort(key=lambda s: s.last_used, reverse=True)
        return sessions
    
    def get_favorites(self) -> List[SessionMetadata]:
        """Get all favorite sessions."""
        return self.search_sessions(SessionSearchFilter(favorite=True))
    
    def toggle_favorite(self, session_id: str) -> bool:
        """Toggle favorite status of a session."""
        if session_id not in self._sessions_index:
            return False
        
        session_meta = self._sessions_index[session_id]
        session_meta.favorite = not session_meta.favorite
        self.update_session(session_meta)
        
        return True
    
    def rate_session(self, session_id: str, rating: int) -> bool:
        """Rate a session (1-5 scale)."""
        if session_id not in self._sessions_index:
            return False
        
        if not 1 <= rating <= 5:
            return False
        
        session_meta = self._sessions_index[session_id]
        session_meta.success_rating = rating
        self.update_session(session_meta)
        
        return True
    
    def add_tags(self, session_id: str, tags: List[str]) -> bool:
        """Add tags to a session."""
        if session_id not in self._sessions_index:
            return False
        
        session_meta = self._sessions_index[session_id]
        for tag in tags:
            if tag not in session_meta.tags:
                session_meta.tags.append(tag)
        
        self.update_session(session_meta)
        return True
    
    def remove_tags(self, session_id: str, tags: List[str]) -> bool:
        """Remove tags from a session."""
        if session_id not in self._sessions_index:
            return False
        
        session_meta = self._sessions_index[session_id]
        for tag in tags:
            if tag in session_meta.tags:
                session_meta.tags.remove(tag)
        
        self.update_session(session_meta)
        return True
    
    def get_all_tags(self) -> List[str]:
        """Get all unique tags across all sessions."""
        tags = set()
        for session_meta in self._sessions_index.values():
            tags.update(session_meta.tags)
        return sorted(list(tags))
    
    def export_sessions(self, 
                       session_ids: Optional[List[str]] = None,
                       export_path: Optional[str] = None) -> str:
        """Export sessions to JSON file."""
        if session_ids is None:
            sessions_to_export = list(self._sessions_index.values())
        else:
            sessions_to_export = [self._sessions_index[sid] for sid in session_ids 
                                if sid in self._sessions_index]
        
        export_data = {
            'export_version': '1.0',
            'export_timestamp': datetime.now().isoformat(),
            'sessions': [session.to_dict() for session in sessions_to_export]
        }
        
        if export_path is None:
            export_path = f"promptcraft_sessions_export_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        
        with open(export_path, 'w', encoding='utf-8') as f:
            json.dump(export_data, f, indent=2, ensure_ascii=False)
        
        return export_path
    
    def import_sessions(self, import_path: str, overwrite: bool = False) -> int:
        """Import sessions from JSON file."""
        with open(import_path, 'r', encoding='utf-8') as f:
            import_data = json.load(f)
        
        if 'sessions' not in import_data:
            raise ValueError("Invalid import file format")
        
        imported_count = 0
        
        for session_data in import_data['sessions']:
            session_meta = SessionMetadata.from_dict(session_data)
            
            # Check if session already exists
            if session_meta.id in self._sessions_index:
                if not overwrite:
                    continue
            
            # Save imported session
            self._save_session_metadata(session_meta)
            self._sessions_index[session_meta.id] = session_meta
            imported_count += 1
        
        # Save updated index
        self._save_sessions_index()
        
        return imported_count
    
    def cleanup_old_sessions(self, days: int = 30) -> int:
        """Delete sessions older than specified days."""
        cutoff_date = datetime.now() - timedelta(days=days)
        sessions_to_delete = []
        
        for session_id, session_meta in self._sessions_index.items():
            if session_meta.last_used < cutoff_date and not session_meta.favorite:
                sessions_to_delete.append(session_id)
        
        for session_id in sessions_to_delete:
            self.delete_session(session_id)
        
        return len(sessions_to_delete)
    
    def get_session_stats(self) -> Dict[str, Any]:
        """Get statistics about sessions."""
        sessions = list(self._sessions_index.values())
        
        stats = {
            'total_sessions': len(sessions),
            'favorite_sessions': sum(1 for s in sessions if s.favorite),
            'sessions_by_status': {},
            'sessions_by_rating': {},
            'most_used_tags': {},
            'sessions_this_week': 0,
            'sessions_this_month': 0
        }
        
        now = datetime.now()
        week_ago = now - timedelta(days=7)
        month_ago = now - timedelta(days=30)
        
        for session in sessions:
            # Count by status
            status = session.status.value
            stats['sessions_by_status'][status] = stats['sessions_by_status'].get(status, 0) + 1
            
            # Count by rating
            if session.success_rating:
                rating = str(session.success_rating)
                stats['sessions_by_rating'][rating] = stats['sessions_by_rating'].get(rating, 0) + 1
            
            # Count tags
            for tag in session.tags:
                stats['most_used_tags'][tag] = stats['most_used_tags'].get(tag, 0) + 1
            
            # Count recent sessions
            if session.created_at >= week_ago:
                stats['sessions_this_week'] += 1
            if session.created_at >= month_ago:
                stats['sessions_this_month'] += 1
        
        return stats