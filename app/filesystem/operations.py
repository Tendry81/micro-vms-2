"""
Filesystem operations with safe path resolution and validation.
"""

import os
import shutil
import logging
from pathlib import Path
from datetime import datetime
from typing import Optional, List

from fastapi import HTTPException

from app.core.models import (
    FileEntry, DirectoryListResponse, FileReadResponse, 
    FileCreateResponse, FileUploadResponse
)
from app.filesystem.gitignore_handler import GitignoreHandler
from app.core.config import (
    MAX_FILE_READ_SIZE, MAX_FILE_PREVIEW_SIZE
)

logger = logging.getLogger(__name__)


class SafePathResolver:
    """
    Resolver for safe filesystem paths within project boundaries.
    Prevents path traversal attacks and symlink escapes.
    """
    
    def __init__(self, project_root: Path):
        """
        Initialize resolver with project root.
        
        Args:
            project_root: Root directory of the project
        """
        self.project_root = project_root.resolve()
        if not self.project_root.exists():
            raise ValueError(f"Project root does not exist: {self.project_root}")
    
    def resolve(self, relative_path: str) -> Path:
        """
        Safely resolve a path relative to project root.
        
        Validates:
        - Path is within project root
        - No absolute paths allowed
        - No .. traversal escapes
        - No symlink escapes
        
        Args:
            relative_path: Path relative to project root
            
        Returns:
            Resolved absolute path
            
        Raises:
            HTTPException: If path is unsafe
        """
        # Reject absolute paths
        if os.path.isabs(relative_path):
            logger.warning(f"Absolute path rejected: {relative_path}")
            raise HTTPException(
                status_code=400,
                detail=f"Absolute paths not allowed. Use relative paths."
            )
        
        # Resolve the path - important: resolve the combined path, not separately
        resolved = (self.project_root / relative_path).resolve()
        
        # Ensure both paths use consistent case (important for Windows)
        try:
            # Try to get relative path - this validates containment
            resolved.relative_to(self.project_root.resolve())
        except ValueError:
            # Handle case where relative_to fails due to path normalization
            # Convert to string and compare paths case-insensitively on Windows
            resolved_str = str(resolved).lower() if os.name == 'nt' else str(resolved)
            root_str = str(self.project_root.resolve()).lower() if os.name == 'nt' else str(self.project_root.resolve())
            
            if not resolved_str.startswith(root_str):
                logger.warning(f"Path traversal attempt: {relative_path} -> {resolved}")
                raise HTTPException(
                    status_code=403,
                    detail="Path traversal detected. Path must be within project root."
                )
        
        return resolved


class FilesystemOperations:
    """Filesystem operations with validation and isolation."""
    
    def __init__(self, project_root: Path):
        """Initialize with project root."""
        resolved_root = Path(project_root).resolve()
        self.resolver = SafePathResolver(resolved_root)
        self.project_root = resolved_root
        self.gitignore = GitignoreHandler(resolved_root)
    
    def list_directory(
        self, 
        path: str = ".",
        recursive: bool = False,
        include_ignored: bool = False
    ) -> DirectoryListResponse:
        """
        List directory contents with improved path exclusion.
        
        Args:
            path: Path relative to project root
            recursive: Include subdirectories
            include_ignored: Include .gitignored files
            
        Returns:
            Directory listing response
        """
        safe_path = self.resolver.resolve(path)
        
        if not safe_path.exists():
            raise HTTPException(status_code=404, detail=f"Path not found: {path}")
        
        if not safe_path.is_dir():
            raise HTTPException(status_code=400, detail=f"Path is not a directory: {path}")
        
        entries = []
        
        # Système de patterns d'exclusion amélioré
        exclude_patterns = [
            ".git",           # Répertoire Git complet
            ".git/*",         # Contenu du répertoire Git
            "__pycache__",    # Cache Python
            ".DS_Store",      # Fichiers système macOS
            "Thumbs.db",      # Fichiers système Windows
            "*.pyc",          # Fichiers Python compilés
            ".env",           # Fichiers d'environnement
            "node_modules",   # Dépendances Node.js
        ]
        
        # Convertir les patterns en expressions régulières pour matching
        import re
        exclude_regexes = []
        for pattern in exclude_patterns:
            # Convertir pattern glob en regex
            pattern_regex = re.escape(pattern)
            pattern_regex = pattern_regex.replace(r'\*', '.*')  # * -> .*
            pattern_regex = pattern_regex.replace(r'\?', '.')   # ? -> .
            pattern_regex = pattern_regex.replace(r'\/', '[/\\\\]')  # / -> [/\\] (cross-platform)
            pattern_regex = f"^{pattern_regex}$"
            exclude_regexes.append(re.compile(pattern_regex, re.IGNORECASE))
        
        def should_exclude(file_path: Path) -> bool:
            """Détermine si un fichier doit être exclu."""
            # Chemin relatif par rapport à la racine du projet
            try:
                rel_path = file_path.relative_to(self.project_root)
            except ValueError:
                return False
            
            # Vérifier les patterns d'exclusion
            path_str = str(rel_path)
            for regex in exclude_regexes:
                if regex.match(path_str):
                    return True
            
            # Exclure les fichiers/dossiers cachés (commençant par .)
            # mais garder .gitignore si demandé
            if file_path.name.startswith(".") and file_path.name != ".gitignore":
                return True
            
            # Vérifier gitignore si activé et non override
            if not include_ignored and self.gitignore.is_ignored(file_path):
                return True
            
            return False
        
        # Récupérer les entrées
        if recursive:
            walk_entries = safe_path.rglob("*")
        else:
            walk_entries = safe_path.iterdir()
        
        for entry in walk_entries:
            # Appliquer les exclusions
            if should_exclude(entry):
                continue
            
            # Vérifier si c'est un lien symbolique sécurisé
            try:
                if entry.is_symlink():
                    # Résoudre le lien et vérifier qu'il reste dans le projet
                    resolved = entry.resolve()
                    try:
                        resolved.relative_to(self.project_root)
                    except ValueError:
                        # Lien sortant du projet - l'exclure
                        continue
            except (OSError, PermissionError):
                # Ne pas pouvoir suivre un lien n'est pas une erreur
                pass
            
            # Obtenir le chemin relatif
            rel_path = entry.relative_to(self.project_root)
            
            # Obtenir les métadonnées
            try:
                stat = entry.stat()
                modified = datetime.fromtimestamp(stat.st_mtime).isoformat()
                size_bytes = stat.st_size if entry.is_file() else None
            except (OSError, PermissionError) as e:
                # Si on ne peut pas accéder aux métadonnées
                logger.debug(f"Cannot access metadata for {entry}: {e}")
                modified = datetime.now().isoformat()
                size_bytes = None
            
            # Vérifier si ignoré par gitignore
            is_ignored = self.gitignore.is_ignored(entry) if not include_ignored else False
            
            entries.append(FileEntry(
                name=entry.name,
                path=str(rel_path),
                type="directory" if entry.is_dir() else "file",
                size_bytes=size_bytes,
                modified=modified,
                is_ignored=is_ignored
            ))
        
        # Trier les résultats (dossiers d'abord, puis fichiers)
        entries.sort(key=lambda x: (0 if x.type == "directory" else 1, x.name.lower()))
        
        return DirectoryListResponse(
            entries=entries,
            recursive=recursive,
            count=len(entries)
        )
    
    def read_file(
        self, 
        path: str,
        preview: bool = False
    ) -> FileReadResponse:
        """
        Read file contents.
        
        Args:
            path: Path relative to project root
            preview: If True, only read first 10KB
            
        Returns:
            File content response
            
        Raises:
            HTTPException: If file is too large or unreadable
        """
        safe_path = self.resolver.resolve(path)
        
        if not safe_path.exists():
            raise HTTPException(status_code=404, detail=f"File not found: {path}")
        
        if not safe_path.is_file():
            raise HTTPException(status_code=400, detail=f"Path is not a file: {path}")
        
        file_size = safe_path.stat().st_size
        max_size = MAX_FILE_PREVIEW_SIZE if preview else MAX_FILE_READ_SIZE
        
        if file_size > max_size and not preview:
            raise HTTPException(
                status_code=413,
                detail=f"File too large ({file_size} bytes, max {MAX_FILE_READ_SIZE})"
            )
        
        try:
            # Try to read as text
            if preview:
                with open(safe_path, 'r', encoding='utf-8') as f:
                    content = f.read(MAX_FILE_PREVIEW_SIZE)
                truncated = file_size > MAX_FILE_PREVIEW_SIZE
            else:
                with open(safe_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                truncated = False
        except UnicodeDecodeError:
            # If text read fails, attempt binary
            try:
                with open(safe_path, 'rb') as f:
                    data = f.read(max_size)
                content = data.decode('utf-8', errors='replace')
                truncated = file_size > max_size
            except Exception as e:
                logger.error(f"Failed to read file {path}: {str(e)}")
                raise HTTPException(status_code=500, detail=f"Cannot read file: {str(e)}")
        except Exception as e:
            logger.error(f"Failed to read file {path}: {str(e)}")
            raise HTTPException(status_code=500, detail=f"Cannot read file: {str(e)}")
        
        return FileReadResponse(
            path=path,
            content=content,
            size_bytes=file_size,
            preview=preview,
            truncated=truncated
        )
    
    def create_file(
        self,
        path: str,
        content: Optional[str] = None,
        overwrite: bool = False
    ) -> FileCreateResponse:
        """
        Create a file with optional content.
        
        Args:
            path: Path relative to project root
            content: Optional file content
            overwrite: Allow overwriting existing file
            
        Returns:
            File creation response
        """
        safe_path = self.resolver.resolve(path)
        
        if safe_path.exists() and not overwrite:
            raise HTTPException(
                status_code=409,
                detail=f"File already exists: {path}"
            )
        
        # Create parent directories
        safe_path.parent.mkdir(parents=True, exist_ok=True)
        
        try:
            with open(safe_path, 'w', encoding='utf-8') as f:
                if content:
                    f.write(content)
            
            size = len(content) if content else 0
            return FileCreateResponse(
                path=path,
                created=True,
                size_bytes=size
            )
        except Exception as e:
            logger.error(f"Failed to create file {path}: {str(e)}")
            raise HTTPException(status_code=500, detail=f"Cannot create file: {str(e)}")
    
    def upload_file(
        self,
        path: str,
        file
    ) -> FileUploadResponse:
        """
        Upload a file.
        
        Args:
            path: Path relative to project root
            file: File to upload
            
        Returns:
            File upload response
        """
        safe_path = self.resolver.resolve(path)
        
        # Create parent directories
        safe_path.parent.mkdir(parents=True, exist_ok=True)
        
        try:
            with open(safe_path, 'wb') as f:
                f.write(file.file.read())
            
            size = safe_path.stat().st_size
            return FileUploadResponse(
                path=path,
                uploaded=True,
                size_bytes=size
            )
        except Exception as e:
            logger.error(f"Failed to upload file {path}: {str(e)}")
            raise HTTPException(status_code=500, detail=f"Cannot upload file: {str(e)}")
    
    
    def create_directory(
        self,
        path: str,
        parents: bool = True
    ) -> dict:
        """
        Create a directory.
        
        Args:
            path: Path relative to project root
            parents: Create parent directories
            
        Returns:
            Response dict
        """
        safe_path = self.resolver.resolve(path)
        
        if safe_path.exists():
            if safe_path.is_dir():
                return {"path": path, "created": False, "message": "Directory already exists"}
            else:
                raise HTTPException(status_code=409, detail=f"Path exists but is not a directory: {path}")
        
        try:
            safe_path.mkdir(parents=parents, exist_ok=True)
            return {"path": path, "created": True, "message": "Directory created"}
        except Exception as e:
            logger.error(f"Failed to create directory {path}: {str(e)}")
            raise HTTPException(status_code=500, detail=f"Cannot create directory: {str(e)}")
    
    def delete_path(
        self,
        path: str,
        recursive: bool = False
    ) -> dict:
        """
        Delete a file or directory.
        
        Args:
            path: Path relative to project root
            recursive: Allow recursive deletion
            
        Returns:
            Response dict
        """
        safe_path = self.resolver.resolve(path)
        
        if not safe_path.exists():
            raise HTTPException(status_code=404, detail=f"Path not found: {path}")
        
        try:
            if safe_path.is_file():
                safe_path.unlink()
                return {"path": path, "deleted": True, "type": "file"}
            elif safe_path.is_dir():
                if not recursive and any(safe_path.iterdir()):
                    raise HTTPException(
                        status_code=400,
                        detail="Directory not empty. Use recursive=true to delete."
                    )
                shutil.rmtree(safe_path)
                return {"path": path, "deleted": True, "type": "directory"}
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Failed to delete {path}: {str(e)}")
            raise HTTPException(status_code=500, detail=f"Cannot delete path: {str(e)}")