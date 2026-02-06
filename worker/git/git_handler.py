"""Git operations handler for cloning and managing repositories."""

import os
import shutil
import subprocess
from pathlib import Path
from typing import Optional
import structlog

from config import settings

logger = structlog.get_logger()


class GitHandler:
    """Handle Git operations for repository cloning and branching."""

    def __init__(self, workspace_dir: Optional[str] = None):
        """
        Initialize Git handler.

        Args:
            workspace_dir: Directory for git operations. Uses settings default if not provided.
        """
        self.workspace_dir = Path(workspace_dir or settings.workspace_dir)
        self.workspace_dir.mkdir(parents=True, exist_ok=True)
        self.log = logger.bind(workspace=str(self.workspace_dir))

    def shallow_clone(
        self,
        repo_url: str,
        target_dir: str,
        branch: str = "main",
        token: Optional[str] = None,
    ) -> Path:
        """
        Perform shallow clone of a repository.

        Args:
            repo_url: Git repository URL
            target_dir: Target directory name (relative to workspace)
            branch: Branch to clone (default: main)
            token: GitHub token for authentication

        Returns:
            Path to cloned repository

        Raises:
            subprocess.CalledProcessError: If git clone fails
        """
        repo_path = self.workspace_dir / target_dir

        # Clean up if exists
        if repo_path.exists():
            self.log.warning(
                "repo_exists", msg="Removing existing repo", path=str(repo_path)
            )
            shutil.rmtree(repo_path)

        # Build clone URL with token if provided
        clone_url = repo_url
        if token and "github.com" in repo_url:
            # Insert token into URL: https://TOKEN@github.com/user/repo.git
            clone_url = repo_url.replace("https://", f"https://{token}@")

        self.log.info(
            "cloning_repo",
            msg="Starting shallow clone",
            url=repo_url,
            branch=branch,
            depth=settings.git_clone_depth,
        )

        try:
            # Perform shallow clone
            subprocess.run(
                [
                    "git",
                    "clone",
                    "--depth",
                    str(settings.git_clone_depth),
                    "--branch",
                    branch,
                    "--single-branch",
                    clone_url,
                    str(repo_path),
                ],
                check=True,
                capture_output=True,
                text=True,
                timeout=300,  # 5 minute timeout
            )

            self.log.info("clone_success", msg="Repository cloned", path=str(repo_path))
            return repo_path

        except subprocess.CalledProcessError as e:
            self.log.error(
                "clone_failed",
                msg="Git clone failed",
                error=e.stderr,
                returncode=e.returncode,
            )
            raise
        except subprocess.TimeoutExpired:
            self.log.error("clone_timeout", msg="Git clone timed out after 5 minutes")
            raise

    def create_branch(self, repo_path: Path, branch_name: str) -> None:
        """
        Create and checkout a new branch.

        Args:
            repo_path: Path to git repository
            branch_name: Name of branch to create

        Raises:
            subprocess.CalledProcessError: If git checkout fails
        """
        self.log.info("creating_branch", msg="Creating new branch", branch=branch_name)

        try:
            subprocess.run(
                ["git", "checkout", "-b", branch_name],
                cwd=repo_path,
                check=True,
                capture_output=True,
                text=True,
            )
            self.log.info("branch_created", msg="Branch created", branch=branch_name)
        except subprocess.CalledProcessError as e:
            self.log.error(
                "branch_failed", msg="Failed to create branch", error=e.stderr
            )
            raise

    def commit_changes(
        self, repo_path: Path, message: str, allow_empty: bool = False
    ) -> None:
        """
        Stage all changes and commit.

        Args:
            repo_path: Path to git repository
            message: Commit message
            allow_empty: Allow empty commits (no changes)

        Raises:
            subprocess.CalledProcessError: If git commit fails
        """
        self.log.info("committing", msg="Committing changes", allow_empty=allow_empty)

        try:
            # Configure git user (required for commits)
            subprocess.run(
                ["git", "config", "user.name", "AI Coding Agent"],
                cwd=repo_path,
                check=True,
                capture_output=True,
            )
            subprocess.run(
                ["git", "config", "user.email", "ai-agent@example.com"],
                cwd=repo_path,
                check=True,
                capture_output=True,
            )

            # Stage all changes
            subprocess.run(
                ["git", "add", "-A"], cwd=repo_path, check=True, capture_output=True
            )

            # Commit
            commit_cmd = ["git", "commit", "-m", message]
            if allow_empty:
                commit_cmd.append("--allow-empty")

            subprocess.run(
                commit_cmd, cwd=repo_path, check=True, capture_output=True, text=True
            )

            self.log.info("commit_success", msg="Changes committed")
        except subprocess.CalledProcessError as e:
            self.log.error("commit_failed", msg="Git commit failed", error=e.stderr)
            raise

    def push_branch(
        self, repo_path: Path, branch_name: str, remote: str = "origin"
    ) -> None:
        """
        Push branch to remote.

        Args:
            repo_path: Path to git repository
            branch_name: Branch to push
            remote: Remote name (default: origin)

        Raises:
            subprocess.CalledProcessError: If git push fails
        """
        self.log.info("pushing_branch", msg="Pushing to remote", branch=branch_name)

        try:
            subprocess.run(
                ["git", "push", "-u", remote, branch_name],
                cwd=repo_path,
                check=True,
                capture_output=True,
                text=True,
            )
            self.log.info("push_success", msg="Branch pushed")
        except subprocess.CalledProcessError as e:
            self.log.error("push_failed", msg="Git push failed", error=e.stderr)
            raise

    def cleanup(self, target_dir: str) -> None:
        """
        Remove cloned repository directory.

        Args:
            target_dir: Directory name to remove (relative to workspace)
        """
        repo_path = self.workspace_dir / target_dir

        if repo_path.exists():
            self.log.info("cleaning_up", msg="Removing repository", path=str(repo_path))
            shutil.rmtree(repo_path)
            self.log.info("cleanup_done", msg="Repository removed")
        else:
            self.log.warning(
                "cleanup_skip", msg="Repository not found", path=str(repo_path)
            )

    def get_file_tree(self, repo_path: Path, max_depth: int = 3) -> str:
        """
        Generate a tree representation of repository files.

        Args:
            repo_path: Path to repository
            max_depth: Maximum depth to traverse

        Returns:
            String representation of file tree
        """
        tree_lines = []

        def _walk_tree(path: Path, prefix: str = "", depth: int = 0):
            if depth > max_depth:
                return

            try:
                entries = sorted(path.iterdir(), key=lambda x: (not x.is_dir(), x.name))

                # Filter out common ignored directories
                ignored = {
                    ".git",
                    "__pycache__",
                    "node_modules",
                    ".venv",
                    "venv",
                    ".pytest_cache",
                }
                entries = [e for e in entries if e.name not in ignored]

                for i, entry in enumerate(entries):
                    is_last = i == len(entries) - 1
                    current_prefix = "└── " if is_last else "├── "
                    next_prefix = "    " if is_last else "│   "

                    tree_lines.append(f"{prefix}{current_prefix}{entry.name}")

                    if entry.is_dir():
                        _walk_tree(entry, prefix + next_prefix, depth + 1)
            except PermissionError:
                pass

        tree_lines.append(repo_path.name + "/")
        _walk_tree(repo_path)

        return "\n".join(tree_lines)
