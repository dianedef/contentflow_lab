"""
GitHub Integration Tools for SEO Agents
Handles content deployment to GitHub repository and website
"""
from typing import Optional, Dict, Any, List
from pathlib import Path
import subprocess
import os
from datetime import datetime
import json


class GitHubContentDeployer:
    """Deploy SEO-generated content to GitHub repository."""
    
    def __init__(self, repo_path: Optional[str] = None):
        """
        Initialize GitHub deployer.
        
        Args:
            repo_path: Path to git repository (default: auto-detect)
        """
        if repo_path:
            self.repo_path = Path(repo_path)
        else:
            # Auto-detect repo root
            self.repo_path = self._find_repo_root()
        
        self.website_path = self.repo_path / "website"
        self.content_path = self.website_path / "src" / "pages"
        
    def _find_repo_root(self) -> Path:
        """Find git repository root."""
        current = Path.cwd()
        while current != current.parent:
            if (current / ".git").exists():
                return current
            current = current.parent
        raise ValueError("Not in a git repository")
    
    def create_markdown_file(
        self,
        content: str,
        filename: str,
        frontmatter: Optional[Dict[str, Any]] = None,
        subdirectory: Optional[str] = None
    ) -> Path:
        """
        Create a markdown file with frontmatter.
        
        Args:
            content: Markdown content body
            filename: Filename (without .md extension)
            frontmatter: YAML frontmatter metadata
            subdirectory: Optional subdirectory within pages/
            
        Returns:
            Path to created file
        """
        # Determine target directory
        if subdirectory:
            target_dir = self.content_path / subdirectory
        else:
            target_dir = self.content_path
        
        target_dir.mkdir(parents=True, exist_ok=True)
        
        # Ensure .md extension
        if not filename.endswith('.md'):
            filename = f"{filename}.md"
        
        filepath = target_dir / filename
        
        # Build frontmatter
        fm_lines = []
        if frontmatter:
            fm_lines.append("---")
            for key, value in frontmatter.items():
                if isinstance(value, (list, dict)):
                    fm_lines.append(f"{key}: {json.dumps(value)}")
                elif isinstance(value, str):
                    # Escape quotes in strings
                    escaped = value.replace('"', '\\"')
                    fm_lines.append(f'{key}: "{escaped}"')
                else:
                    fm_lines.append(f"{key}: {value}")
            fm_lines.append("---")
            fm_lines.append("")
        
        # Write file
        with open(filepath, 'w', encoding='utf-8') as f:
            if fm_lines:
                f.write('\n'.join(fm_lines))
            f.write(content)
        
        print(f"✅ Created: {filepath.relative_to(self.repo_path)}")
        return filepath
    
    def update_markdown_file(
        self,
        filepath: str,
        content: Optional[str] = None,
        frontmatter: Optional[Dict[str, Any]] = None
    ) -> Path:
        """
        Update existing markdown file.
        
        Args:
            filepath: Path to file (relative or absolute)
            content: New content (None to keep existing)
            frontmatter: New/updated frontmatter (None to keep existing)
            
        Returns:
            Path to updated file
        """
        path = Path(filepath)
        if not path.is_absolute():
            path = self.content_path / filepath
        
        if not path.exists():
            raise FileNotFoundError(f"File not found: {path}")
        
        # Read existing file
        with open(path, 'r', encoding='utf-8') as f:
            existing_content = f.read()
        
        # Parse existing frontmatter and content
        existing_fm = {}
        existing_body = existing_content
        
        if existing_content.startswith('---'):
            parts = existing_content.split('---', 2)
            if len(parts) >= 3:
                # Parse YAML frontmatter (simple key: value parser)
                fm_text = parts[1].strip()
                for line in fm_text.split('\n'):
                    if ':' in line:
                        key, value = line.split(':', 1)
                        existing_fm[key.strip()] = value.strip().strip('"')
                existing_body = parts[2].strip()
        
        # Merge frontmatter
        if frontmatter:
            existing_fm.update(frontmatter)
        
        # Update lastModified
        existing_fm['lastModified'] = datetime.now().isoformat()
        
        # Build new file content
        fm_lines = ["---"]
        for key, value in existing_fm.items():
            if isinstance(value, str):
                escaped = value.replace('"', '\\"')
                fm_lines.append(f'{key}: "{escaped}"')
            else:
                fm_lines.append(f"{key}: {value}")
        fm_lines.append("---")
        fm_lines.append("")
        
        # Use new content or keep existing
        new_body = content if content is not None else existing_body
        
        # Write updated file
        with open(path, 'w', encoding='utf-8') as f:
            f.write('\n'.join(fm_lines))
            f.write(new_body)
        
        print(f"✅ Updated: {path.relative_to(self.repo_path)}")
        return path
    
    def git_commit_and_push(
        self,
        files: List[str],
        commit_message: str,
        branch: str = "master"
    ) -> Dict[str, Any]:
        """
        Commit and push files to GitHub.
        
        Args:
            files: List of file paths to commit (relative to repo root)
            commit_message: Git commit message
            branch: Git branch (default: master)
            
        Returns:
            Dict with status and output
        """
        result = {
            "success": False,
            "message": "",
            "branch": branch,
            "files_committed": [],
            "commit_hash": None
        }
        
        try:
            os.chdir(self.repo_path)
            
            # Stage files
            for file in files:
                subprocess.run(
                    ["git", "add", file],
                    check=True,
                    capture_output=True,
                    text=True
                )
                result["files_committed"].append(file)
            
            # Commit
            commit_result = subprocess.run(
                ["git", "commit", "-m", commit_message],
                check=True,
                capture_output=True,
                text=True
            )
            
            # Extract commit hash
            hash_result = subprocess.run(
                ["git", "rev-parse", "HEAD"],
                check=True,
                capture_output=True,
                text=True
            )
            result["commit_hash"] = hash_result.stdout.strip()
            
            # Push
            push_result = subprocess.run(
                ["git", "push", "origin", branch],
                check=True,
                capture_output=True,
                text=True
            )
            
            result["success"] = True
            result["message"] = f"✅ Committed and pushed {len(files)} files to {branch}"
            
            print(result["message"])
            print(f"Commit: {result['commit_hash'][:7]}")
            
        except subprocess.CalledProcessError as e:
            result["message"] = f"❌ Git error: {e.stderr}"
            print(result["message"])
        
        return result
    
    def deploy_seo_content(
        self,
        content: str,
        title: str,
        metadata: Dict[str, Any],
        slug: Optional[str] = None,
        subdirectory: Optional[str] = None,
        auto_commit: bool = True
    ) -> Dict[str, Any]:
        """
        Complete deployment workflow for SEO-generated content.
        
        Args:
            content: Markdown content
            title: Page title
            metadata: SEO metadata (description, keywords, etc.)
            slug: URL slug (default: derived from title)
            subdirectory: Optional subdirectory
            auto_commit: Automatically commit and push (default: True)
            
        Returns:
            Dict with deployment status
        """
        # Generate slug from title if not provided
        if not slug:
            slug = title.lower().replace(' ', '-').replace('_', '-')
            # Remove special characters
            slug = ''.join(c for c in slug if c.isalnum() or c == '-')
        
        # Build frontmatter
        frontmatter = {
            "layout": "../../layouts/Layout.astro",
            "title": title,
            "description": metadata.get("description", ""),
            "publishDate": datetime.now().isoformat(),
            "lastModified": datetime.now().isoformat(),
        }
        
        # Add optional metadata
        if "keywords" in metadata:
            frontmatter["keywords"] = metadata["keywords"]
        if "author" in metadata:
            frontmatter["author"] = metadata["author"]
        
        # Create file
        filepath = self.create_markdown_file(
            content=content,
            filename=slug,
            frontmatter=frontmatter,
            subdirectory=subdirectory
        )
        
        # Commit and push
        if auto_commit:
            relative_path = filepath.relative_to(self.repo_path)
            commit_result = self.git_commit_and_push(
                files=[str(relative_path)],
                commit_message=f"SEO: Add {title}"
            )
            
            return {
                "success": True,
                "filepath": str(filepath),
                "url_slug": slug,
                "git_commit": commit_result
            }
        
        return {
            "success": True,
            "filepath": str(filepath),
            "url_slug": slug,
            "git_commit": None
        }


class GitHubStatusChecker:
    """Check GitHub repository status and website deployment."""
    
    def __init__(self, repo_path: Optional[str] = None):
        if repo_path:
            self.repo_path = Path(repo_path)
        else:
            self.repo_path = self._find_repo_root()
    
    def _find_repo_root(self) -> Path:
        """Find git repository root."""
        current = Path.cwd()
        while current != current.parent:
            if (current / ".git").exists():
                return current
            current = current.parent
        raise ValueError("Not in a git repository")
    
    def check_git_status(self) -> Dict[str, Any]:
        """
        Check current git status.
        
        Returns:
            Dict with git status information
        """
        os.chdir(self.repo_path)
        
        # Get branch
        branch_result = subprocess.run(
            ["git", "branch", "--show-current"],
            capture_output=True,
            text=True
        )
        branch = branch_result.stdout.strip()
        
        # Get status
        status_result = subprocess.run(
            ["git", "status", "--porcelain"],
            capture_output=True,
            text=True
        )
        
        # Parse status
        modified = []
        untracked = []
        staged = []
        
        for line in status_result.stdout.strip().split('\n'):
            if not line:
                continue
            status = line[:2]
            filepath = line[3:]
            
            if status[0] in ['M', 'A', 'D']:
                staged.append(filepath)
            if status[1] == 'M':
                modified.append(filepath)
            if status == '??':
                untracked.append(filepath)
        
        return {
            "branch": branch,
            "is_clean": len(modified) == 0 and len(untracked) == 0 and len(staged) == 0,
            "staged_files": staged,
            "modified_files": modified,
            "untracked_files": untracked
        }
    
    def list_website_pages(self) -> List[Dict[str, str]]:
        """
        List all markdown pages in website.
        
        Returns:
            List of pages with metadata
        """
        pages_dir = self.repo_path / "website" / "src" / "pages"
        if not pages_dir.exists():
            return []
        
        pages = []
        for md_file in pages_dir.rglob("*.md"):
            relative_path = md_file.relative_to(pages_dir)
            pages.append({
                "path": str(relative_path),
                "filename": md_file.name,
                "size_kb": md_file.stat().st_size / 1024,
                "modified": datetime.fromtimestamp(md_file.stat().st_mtime).isoformat()
            })
        
        return pages


# Convenience functions
def deploy_content(
    content: str,
    title: str,
    description: str,
    keywords: Optional[List[str]] = None,
    auto_commit: bool = True
) -> Dict[str, Any]:
    """
    Quick function to deploy SEO content.
    
    Args:
        content: Markdown content
        title: Page title
        description: Meta description
        keywords: SEO keywords
        auto_commit: Auto commit and push
        
    Returns:
        Deployment status
    """
    deployer = GitHubContentDeployer()
    metadata = {"description": description}
    if keywords:
        metadata["keywords"] = keywords
    
    return deployer.deploy_seo_content(
        content=content,
        title=title,
        metadata=metadata,
        auto_commit=auto_commit
    )


def check_deployment_status() -> Dict[str, Any]:
    """
    Check current deployment status.
    
    Returns:
        Status information
    """
    checker = GitHubStatusChecker()
    git_status = checker.check_git_status()
    pages = checker.list_website_pages()
    
    return {
        "git": git_status,
        "website_pages_count": len(pages),
        "website_pages": pages[:10]  # First 10 pages
    }


if __name__ == "__main__":
    # Test deployment
    print("=== GitHub Tools Test ===\n")
    
    # Check status
    print("1. Checking status...")
    status = check_deployment_status()
    print(f"Branch: {status['git']['branch']}")
    print(f"Clean: {status['git']['is_clean']}")
    print(f"Website pages: {status['website_pages_count']}")
    
    # Test content creation (without commit)
    print("\n2. Testing content creation...")
    test_content = """
# Test SEO Article

This is a test article generated by SEO agents.

## Key Points

- Automated content generation
- SEO optimization
- GitHub integration

## Conclusion

This demonstrates the automated deployment workflow.
"""
    
    result = deploy_content(
        content=test_content,
        title="Test SEO Article",
        description="A test article demonstrating automated SEO content deployment",
        keywords=["seo", "automation", "test"],
        auto_commit=False  # Set to True to actually commit
    )
    
    print(f"\n✅ Test complete: {result['filepath']}")
    print(f"URL slug: {result['url_slug']}")
