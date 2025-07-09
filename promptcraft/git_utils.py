"""Git utilities for PromptCraft."""

import subprocess
import os
from typing import Dict, List, Optional
from pathlib import Path


def is_git_repo() -> bool:
    """Check if the current directory is a git repository."""
    try:
        result = subprocess.run(
            ["git", "rev-parse", "--git-dir"],
            capture_output=True,
            text=True,
            cwd="."
        )
        return result.returncode == 0
    except (subprocess.SubprocessError, FileNotFoundError):
        return False


def get_git_status() -> Dict[str, List[str]]:
    """Get git status information categorized by file state."""
    if not is_git_repo():
        return {}
    
    try:
        result = subprocess.run(
            ["git", "status", "--porcelain"],
            capture_output=True,
            text=True,
            cwd="."
        )
        
        if result.returncode != 0:
            return {}
        
        status = {
            "modified": [],
            "added": [],
            "deleted": [],
            "renamed": [],
            "untracked": []
        }
        
        for line in result.stdout.strip().split('\n'):
            if not line:
                continue
                
            status_code = line[:2]
            file_path = line[3:]
            
            # Parse git status codes
            if status_code == "??":
                status["untracked"].append(file_path)
            elif status_code[0] == "A" or status_code[1] == "A":
                status["added"].append(file_path)
            elif status_code[0] == "M" or status_code[1] == "M":
                status["modified"].append(file_path)
            elif status_code[0] == "D" or status_code[1] == "D":
                status["deleted"].append(file_path)
            elif status_code[0] == "R" or status_code[1] == "R":
                status["renamed"].append(file_path)
        
        return status
        
    except (subprocess.SubprocessError, FileNotFoundError):
        return {}


def get_git_diff(staged: bool = False) -> str:
    """Get git diff output."""
    if not is_git_repo():
        return ""
    
    try:
        cmd = ["git", "diff"]
        if staged:
            cmd.append("--staged")
        
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            cwd="."
        )
        
        if result.returncode == 0:
            return result.stdout
        return ""
        
    except (subprocess.SubprocessError, FileNotFoundError):
        return ""


def get_recent_commits(count: int = 5) -> List[Dict]:
    """Get recent commit information."""
    if not is_git_repo():
        return []
    
    try:
        result = subprocess.run([
            "git", "log", 
            f"--max-count={count}",
            "--pretty=format:%H|%an|%ad|%s",
            "--date=short"
        ], capture_output=True, text=True, cwd=".")
        
        if result.returncode != 0:
            return []
        
        commits = []
        for line in result.stdout.strip().split('\n'):
            if not line:
                continue
                
            parts = line.split('|', 3)
            if len(parts) == 4:
                commits.append({
                    "hash": parts[0][:8],  # Short hash
                    "author": parts[1],
                    "date": parts[2],
                    "message": parts[3]
                })
        
        return commits
        
    except (subprocess.SubprocessError, FileNotFoundError):
        return []


def get_current_branch() -> str:
    """Get the current git branch name."""
    if not is_git_repo():
        return ""
    
    try:
        result = subprocess.run(
            ["git", "branch", "--show-current"],
            capture_output=True,
            text=True,
            cwd="."
        )
        
        if result.returncode == 0:
            return result.stdout.strip()
        return ""
        
    except (subprocess.SubprocessError, FileNotFoundError):
        return ""


def get_git_root() -> Optional[str]:
    """Get the root directory of the git repository."""
    if not is_git_repo():
        return None
    
    try:
        result = subprocess.run(
            ["git", "rev-parse", "--show-toplevel"],
            capture_output=True,
            text=True,
            cwd="."
        )
        
        if result.returncode == 0:
            return result.stdout.strip()
        return None
        
    except (subprocess.SubprocessError, FileNotFoundError):
        return None


def get_git_remote_url() -> str:
    """Get the remote URL of the git repository."""
    if not is_git_repo():
        return ""
    
    try:
        result = subprocess.run(
            ["git", "remote", "get-url", "origin"],
            capture_output=True,
            text=True,
            cwd="."
        )
        
        if result.returncode == 0:
            return result.stdout.strip()
        return ""
        
    except (subprocess.SubprocessError, FileNotFoundError):
        return ""