"""Context builder for creating LLM prompts from repository and issue data."""

from pathlib import Path
from typing import List, Dict, Any, Set
import structlog

logger = structlog.get_logger()


class ContextBuilder:
    """Build context for LLM from repository and issue information."""
    
    def __init__(self):
        """Initialize context builder."""
        self.log = logger.bind(component="context_builder")
        
        # File extensions to consider as code
        self.code_extensions = {
            '.py', '.js', '.ts', '.tsx', '.jsx', '.java', '.go',
            '.rs', '.cpp', '.c', '.h', '.hpp', '.cs', '.rb',
            '.php', '.swift', '.kt', '.scala', '.sh', '.sql'
        }
        
        # Directories to ignore
        self.ignored_dirs = {
            '.git', '__pycache__', 'node_modules', '.venv', 'venv',
            'dist', 'build', '.pytest_cache', '.mypy_cache', '.tox'
        }
    
    def build_issue_context(self, issue_data: Dict[str, Any]) -> str:
        """
        Build formatted issue context.
        
        Args:
            issue_data: Issue data dictionary
            
        Returns:
            Formatted issue context string
        """
        context = f"""
# Issue Information

**Issue #{issue_data['number']}: {issue_data['title']}**

**Status:** {issue_data['state']}
**Author:** {issue_data['author']}
**Labels:** {', '.join(issue_data['labels']) if issue_data['labels'] else 'None'}

## Description

{issue_data['body']}

---
"""
        return context
    
    def identify_relevant_files(
        self,
        repo_path: Path,
        issue_data: Dict[str, Any],
        max_files: int = 10
    ) -> List[Path]:
        """
        Identify files relevant to the issue.
        
        Args:
            repo_path: Path to repository
            issue_data: Issue data
            max_files: Maximum number of files to return
            
        Returns:
            List of relevant file paths
        """
        self.log.info("identifying_files", msg="Searching for relevant files")
        
        # Extract keywords from issue
        keywords = self._extract_keywords(issue_data)
        
        # Find all code files
        code_files = []
        for file_path in repo_path.rglob('*'):
            if file_path.is_dir():
                continue
            if any(ignored in file_path.parts for ignored in self.ignored_dirs):
                continue
            if file_path.suffix not in self.code_extensions:
                continue
            
            code_files.append(file_path)
        
        # Score files based on keyword matches
        scored_files = []
        for file_path in code_files:
            score = self._score_file(file_path, keywords)
            if score > 0:
                scored_files.append((score, file_path))
        
        # Sort by score and return top N
        scored_files.sort(reverse=True, key=lambda x: x[0])
        relevant_files = [f[1] for f in scored_files[:max_files]]
        
        self.log.info(
            "files_identified",
            msg="Found relevant files",
            count=len(relevant_files)
        )
        
        return relevant_files
    
    def _extract_keywords(self, issue_data: Dict[str, Any]) -> Set[str]:
        """Extract keywords from issue title and body."""
        text = f"{issue_data['title']} {issue_data['body']}".lower()
        
        # Simple keyword extraction
        stop_words = {'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for'}
        
        words = text.split()
        keywords = {w.strip('.,!?;:') for w in words if len(w) > 3 and w not in stop_words}
        
        return keywords
    
    def _score_file(self, file_path: Path, keywords: Set[str]) -> int:
        """Score a file based on keyword matches."""
        score = 0
        
        # Score based on filename
        filename = file_path.name.lower()
        for keyword in keywords:
            if keyword in filename:
                score += 5
        
        # Score based on path
        path_str = str(file_path).lower()
        for keyword in keywords:
            if keyword in path_str:
                score += 2
        
        # Score based on content
        try:
            content = file_path.read_text(encoding='utf-8', errors='ignore')
            content_sample = content[:10000].lower()
            
            for keyword in keywords:
                if keyword in content_sample:
                    score += 1
        except Exception:
            pass
        
        return score
    
    def read_file_contents(
        self,
        files: List[Path],
        max_lines_per_file: int = 100
    ) -> Dict[str, str]:
        """
        Read contents of files.
        
        Args:
            files: List of file paths
            max_lines_per_file: Maximum lines to read per file
            
        Returns:
            Dictionary mapping file paths to contents
        """
        contents = {}
        
        for file_path in files:
            try:
                with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                    lines = f.readlines()
                    
                    if len(lines) > max_lines_per_file:
                        lines = lines[:max_lines_per_file]
                        lines.append(f"\n... (file truncated)")
                    
                    contents[str(file_path)] = ''.join(lines)
                    
            except Exception as e:
                self.log.warning(
                    "file_read_failed",
                    msg="Could not read file",
                    file=str(file_path),
                    error=str(e)
                )
                contents[str(file_path)] = f"[Error reading file: {e}]"
        
        return contents
    
    def build_full_context(
        self,
        issue_data: Dict[str, Any],
        file_tree: str,
        file_contents: Dict[str, str]
    ) -> str:
        """
        Build complete context for LLM.
        
        Args:
            issue_data: Issue information
            file_tree: Repository file tree
            file_contents: Dictionary of file paths to contents
            
        Returns:
            Complete formatted context
        """
        context_parts = []
        
        # Issue context
        context_parts.append(self.build_issue_context(issue_data))
        
        # File tree
        context_parts.append(f"""
# Repository Structure

```
{file_tree}
```

---
""")
        
        # File contents
        if file_contents:
            context_parts.append("# Relevant Files\n\n")
            
            for file_path, content in file_contents.items():
                file_ext = Path(file_path).suffix.lstrip('.')
                context_parts.append(f"""
## {file_path}

```{file_ext}
{content}
```

---
""")
        
        return '\n'.join(context_parts)

