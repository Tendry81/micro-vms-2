"""
Gitignore file handling with caching support.
"""

import logging
from pathlib import Path
from typing import Optional
from functools import lru_cache

try:
    import pathspec
except ImportError:
    pathspec = None

logger = logging.getLogger(__name__)


class GitignoreHandler:
    """Handle .gitignore parsing and caching."""
    
    def __init__(self, project_root: Path):
        """Initialize handler with project root."""
        self.project_root = Path(project_root).resolve()
        self._cache: Optional[pathspec.PathSpec] = None
        self._cache_time: Optional[float] = None
    
    def is_ignored(self, path: Path) -> bool:
        """
        Check if path should be ignored.
        
        Args:
            path: Path relative to project root
            
        Returns:
            True if path matches .gitignore patterns
        """
        if not pathspec:
            logger.warning("pathspec not installed, skipping gitignore check")
            return False
        
        gitignore_path = self.project_root / ".gitignore"
        
        # Invalidate cache if .gitignore changed
        if gitignore_path.exists():
            mtime = gitignore_path.stat().st_mtime
            if self._cache_time != mtime:
                self._cache = None
                self._cache_time = mtime
        else:
            self._cache = None
        
        # Load from cache or parse
        if self._cache is None:
            self._load_patterns()
        
        if self._cache is None:
            return False
        
        # Check if path is ignored
        try:
            rel_path = path.relative_to(self.project_root)
            return self._cache.match_file(str(rel_path))
        except ValueError:
            return False
    
    def _load_patterns(self) -> None:
        """Load patterns from .gitignore."""
        gitignore_path = self.project_root / ".gitignore"
        
        if not gitignore_path.exists():
            self._cache = pathspec.PathSpec([])
            return
        
        try:
            with open(gitignore_path, 'r', encoding='utf-8') as f:
                patterns = f.readlines()
            
            # Filter empty lines and comments
            patterns = [p.rstrip() for p in patterns if p.strip() and not p.startswith("#")]
            
            if pathspec:
                self._cache = pathspec.PathSpec.from_lines("gitwildmatch", patterns)
            logger.info(f"Loaded {len(patterns)} patterns from .gitignore")
        except Exception as e:
            logger.error(f"Failed to load .gitignore: {str(e)}")
            self._cache = pathspec.PathSpec([])
    
    def get_ignored_patterns(self) -> list[str]:
        """Get list of ignore patterns."""
        gitignore_path = self.project_root / ".gitignore"
        
        if not gitignore_path.exists():
            return []
        
        try:
            with open(gitignore_path, 'r', encoding='utf-8') as f:
                patterns = f.readlines()
            return [p.rstrip() for p in patterns if p.strip() and not p.startswith("#")]
        except Exception as e:
            logger.error(f"Failed to read .gitignore: {str(e)}")
            return []
    
    def clear_cache(self) -> None:
        """Manually clear pattern cache."""
        self._cache = None
        self._cache_time = None