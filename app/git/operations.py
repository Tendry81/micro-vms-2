"""
Git operations module for repository management.
"""

import datetime
import logging
import re
from pathlib import Path
import subprocess
from typing import Optional, Dict, Any

from fastapi import HTTPException

from app.core.audit import AuditLogger

logger = logging.getLogger(__name__)


class GitOperations:
    """Git repository operations."""
    
    def __init__(self, project_root: Path, token: Optional[str] = None):
        """
        Initialize Git operations.
        
        Args:
            project_root: Root directory of the project
            token: Optional GitHub token for authentication
        """
        self.project_root = project_root
        self.token = token
    
    def _run_git_command(
        self,
        args: list[str],
        capture_output: bool = True,
        timeout: int = 60
    ) -> tuple[int, str, str]:
        """
        Execute a git command safely.
        
        Args:
            args: Git command arguments
            capture_output: Capture stdout/stderr
            timeout: Command timeout in seconds
            
        Returns:
            Tuple of (exit_code, stdout, stderr)
        """
        try:
            env = {}
            if self.token:
                # Inject token for git authentication
                env = {"GIT_ASKPASS_OVERRIDE": "echo " + self.token}
            
            result = subprocess.run(
                ["git"] + args,
                cwd=self.project_root,
                capture_output=capture_output,
                text=True,
                timeout=timeout,
                env={**subprocess.os.environ, **env} if env else None
            )
            return result.returncode, result.stdout, result.stderr
        except subprocess.TimeoutExpired:
            logger.error(f"Git command timeout: {args}")
            raise HTTPException(status_code=408, detail="Git operation timed out")
        except Exception as e:
            logger.error(f"Git command failed: {str(e)}")
            raise HTTPException(status_code=500, detail=f"Git operation failed: {str(e)}")
    
    def clone_repository(
        self,
        repo_url: str,
        target_path: Path,
        branch: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Clone a repository.
        
        Args:
            repo_url: Repository URL (HTTPS only)
            target_path: Target directory
            branch: Optional branch to checkout
            
        Returns:
            Response dict
        """
        # Validate URL format
        if not repo_url.startswith("https://"):
            raise HTTPException(status_code=400, detail="Only HTTPS URLs allowed")
        
        # Build clone command
        args = ["clone"]
        if branch:
            args.extend(["--branch", branch])
        args.extend([repo_url, str(target_path)])
        
        exit_code, stdout, stderr = self._run_git_command(args)
        
        if exit_code != 0:
            raise HTTPException(
                status_code=400,
                detail=f"Clone failed: {stderr}"
            )
        
        logger.info(f"Repository cloned: {repo_url} -> {target_path}")
        return {"status": "cloned", "url": repo_url, "path": str(target_path)}
    
    def get_status(self) -> Dict[str, Any]:
        """
        Get repository status.
        
        Returns:
            Status dict
        """
        if not (self.project_root / ".git").exists():
            raise HTTPException(status_code=400, detail="Not a git repository")
        
        # Get current branch
        exit_code, branch, _ = self._run_git_command(["rev-parse", "--abbrev-ref", "HEAD"])
        if exit_code != 0:
            branch = "unknown"
        else:
            branch = branch.strip()
        
        # Get modified files
        exit_code, modified, _ = self._run_git_command(["diff", "--name-only"])
        modified_files = modified.strip().split("\n") if modified.strip() else []
        
        # Get untracked files
        exit_code, untracked, _ = self._run_git_command(["ls-files", "--others", "--exclude-standard"])
        untracked_files = untracked.strip().split("\n") if untracked.strip() else []
        
        # Get commits ahead/behind
        ahead, behind = 0, 0
        exit_code, ahead_output, _ = self._run_git_command(["rev-list", "--count", "HEAD@{u}..HEAD"])
        if exit_code == 0:
            try:
                ahead = int(ahead_output.strip())
            except ValueError:
                pass
        
        return {
            "branch": branch,
            "modified_files": modified_files,
            "untracked_files": untracked_files,
            "commits_ahead": ahead,
            "commits_behind": behind
        }
    
    def pull(
        self,
        remote: str = "origin",
        branch: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Pull from remote.
        
        Args:
            remote: Remote name
            branch: Optional branch
            
        Returns:
            Pull response
        """
        if not (self.project_root / ".git").exists():
            raise HTTPException(status_code=400, detail="Not a git repository")
        
        args = ["pull", remote]
        if branch:
            args.append(branch)
        
        exit_code, stdout, stderr = self._run_git_command(args)
        
        if exit_code != 0:
            raise HTTPException(status_code=400, detail=f"Pull failed: {stderr}")
        
        # Parse output for stats
        files_changed = self._parse_pull_stats(stdout)
        
        return {
            "status": "success",
            "files_changed": files_changed,
            "insertions": 0,
            "deletions": 0,
            "output": stdout
        }
    
    def commit(
        self,
        message: str,
        author_name: Optional[str] = None,
        author_email: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Commit staged changes.
        
        Args:
            message: Commit message
            author_name: Optional author name
            author_email: Optional author email
            
        Returns:
            Commit response
        """
        if not (self.project_root / ".git").exists():
            raise HTTPException(status_code=400, detail="Not a git repository")
        
        args = ["commit", "-m", message]
        
        # Add author if provided
        if author_name or author_email:
            author = f"{author_name or 'User'} <{author_email or 'user@example.com'}>"
            args.extend(["--author", author])
        
        exit_code, stdout, stderr = self._run_git_command(args)
        
        if exit_code != 0:
            # Check if nothing to commit
            if "nothing to commit" in stderr or "no changes added" in stderr:
                return {"status": "no_changes", "message": "Nothing to commit"}
            raise HTTPException(status_code=400, detail=f"Commit failed: {stderr}")
        
        return {"status": "success", "output": stdout}
    
    def push(
        self,
        remote: str = "origin",
        branch: Optional[str] = None,
        force: bool = False
    ) -> Dict[str, Any]:
        """
        Push to remote.
        
        Args:
            remote: Remote name
            branch: Optional branch
            force: Force push (dangerous)
            
        Returns:
            Push response
        """
        if not (self.project_root / ".git").exists():
            raise HTTPException(status_code=400, detail="Not a git repository")
        
        args = ["push"]
        if force:
            args.append("-f")
        args.extend([remote])
        if branch:
            args.append(branch)
        
        exit_code, stdout, stderr = self._run_git_command(args)
        
        if exit_code != 0:
            raise HTTPException(status_code=400, detail=f"Push failed: {stderr}")
        
        return {"status": "success", "output": stdout}
    
    def checkout(self, ref: str) -> Dict[str, Any]:
        """
        Checkout a branch or tag.
        
        Args:
            ref: Branch or tag name
            
        Returns:
            Checkout response
        """
        if not (self.project_root / ".git").exists():
            raise HTTPException(status_code=400, detail="Not a git repository")
        
        # Validate ref name (basic check)
        if ".." in ref or ref.startswith("-"):
            raise HTTPException(status_code=400, detail="Invalid ref name")
        
        exit_code, stdout, stderr = self._run_git_command(["checkout", ref])
        
        if exit_code != 0:
            raise HTTPException(status_code=400, detail=f"Checkout failed: {stderr}")
        
        return {"status": "success", "ref": ref, "output": stdout}
    
    def add_files(self, pattern: str = ".") -> Dict[str, Any]:
        """
        Stage files for commit.
        
        Args:
            pattern: File pattern (default: all)
            
        Returns:
            Response dict
        """
        if not (self.project_root / ".git").exists():
            raise HTTPException(status_code=400, detail="Not a git repository")
        
        exit_code, stdout, stderr = self._run_git_command(["add", pattern])
        
        if exit_code != 0:
            raise HTTPException(status_code=400, detail=f"Add failed: {stderr}")
        
        return {"status": "success"}
    
    @staticmethod
    def _parse_pull_stats(output: str) -> int:
        """
        Parse git pull output for file change count.
        
        Args:
            output: Git pull output
            
        Returns:
            Number of files changed
        """
        # Simple regex to extract file count
        match = re.search(r'(\d+)\s+files?\s+changed', output)
        return int(match.group(1)) if match else 0
    
    def get_modified_files(
        self,
        include_staged: bool = True,
        include_unstaged: bool = True
    ) -> Dict[str, Any]:
        """
        Get list of modified files in repository.
        
        Args:
            include_staged: Include staged files
            include_unstaged: Include unstaged files
            
        Returns:
            Dict with modified files information
        """
        if not (self.project_root / ".git").exists():
            raise HTTPException(status_code=400, detail="Not a git repository")
        
        modified_files = []
        
        try:
            # Fichiers staged (ajoutés avec git add)
            if include_staged:
                exit_code, staged_output, _ = self._run_git_command(["diff", "--name-only", "--cached"])
                if exit_code == 0 and staged_output.strip():
                    staged_files = [f.strip() for f in staged_output.strip().split("\n") if f.strip()]
                    for file in staged_files:
                        modified_files.append({
                            "path": file,
                            "status": "staged",
                            "full_path": str(self.project_root / file)
                        })
            
            # Fichiers unstaged (modifiés mais non ajoutés)
            if include_unstaged:
                exit_code, unstaged_output, _ = self._run_git_command(["diff", "--name-only"])
                if exit_code == 0 and unstaged_output.strip():
                    unstaged_files = [f.strip() for f in unstaged_output.strip().split("\n") if f.strip()]
                    for file in unstaged_files:
                        # Éviter les doublons si déjà staged
                        if not any(f["path"] == file for f in modified_files):
                            modified_files.append({
                                "path": file,
                                "status": "unstaged",
                                "full_path": str(self.project_root / file)
                            })
            
            # Fichiers untracked (nouveaux)
            exit_code, untracked_output, _ = self._run_git_command(["ls-files", "--others", "--exclude-standard"])
            if exit_code == 0 and untracked_output.strip():
                untracked_files = [f.strip() for f in untracked_output.strip().split("\n") if f.strip()]
                for file in untracked_files:
                    modified_files.append({
                        "path": file,
                        "status": "untracked",
                        "full_path": str(self.project_root / file)
                    })
            
            # Pour chaque fichier, obtenir plus d'informations
            for file_info in modified_files:
                file_path = self.project_root / file_info["path"]
                if file_path.exists():
                    stat = file_path.stat()
                    file_info.update({
                        "size_bytes": stat.st_size if file_path.is_file() else None,
                        "modified": datetime.fromtimestamp(stat.st_mtime).isoformat(),
                        "type": "directory" if file_path.is_dir() else "file"
                    })
                    
                    # Pour les fichiers textes, optionnellement ajouter un preview
                    if file_path.is_file() and file_path.stat().st_size < 10000:  # < 10KB
                        try:
                            with open(file_path, 'r', encoding='utf-8') as f:
                                preview = f.read(500)  # Premier 500 caractères
                                file_info["preview"] = preview
                        except:
                            pass
            
            return {
                "modified_files": modified_files,
                "count": len(modified_files),
                "staged_count": len([f for f in modified_files if f["status"] == "staged"]),
                "unstaged_count": len([f for f in modified_files if f["status"] == "unstaged"]),
                "untracked_count": len([f for f in modified_files if f["status"] == "untracked"])
            }
            
        except Exception as e:
            logger.error(f"Failed to get modified files: {str(e)}")
            raise HTTPException(status_code=500, detail=f"Failed to get modified files: {str(e)}")