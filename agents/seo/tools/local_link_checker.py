"""
Local-first Markdown Link Checker
Validates internal links directly in source files (pre-deployment).
No HTTP required — resolves links against the local filesystem.

Uses ProjectSettings (local_repo_path + content_directory) from BizFlows project store
so the user's configured content directory is always respected.
"""
from typing import Dict, Any, Optional, List
from pathlib import Path
import re

from crewai.tools import tool

from api.models.project import Project, ProjectSettings


class LocalLinkChecker:
    """
    Vérifie les liens internes markdown directement dans les fichiers source.

    Stratégie local-first :
    - Résout les liens relatifs et root-relative depuis le filesystem
    - Utilise ContentDirectoryConfig de ProjectSettings (chemin + extensions configurés par l'user)
    - Ne nécessite pas que le site soit déployé
    """

    # Répertoires à exclure systématiquement du scan
    EXCLUDE_DIRS = {'node_modules', '.git', 'dist', '.astro', 'build', '.cache', '__pycache__'}

    # Extensions par défaut si le projet n'a pas de ContentDirectoryConfig
    DEFAULT_EXTENSIONS = ['.md', '.mdx', '.astro']

    # Réutilise le même pattern que repo_analyzer.py:412
    LINK_PATTERN = re.compile(r'\[([^\]]+)\]\(([^)]+)\)')

    def _strip_fragment(self, url: str) -> str:
        """Supprime le fragment (#section) d'un lien."""
        return url.split('#')[0]

    def _resolve_link(
        self,
        source_file: Path,
        link_url: str,
        content_root: Path
    ) -> Optional[Path]:
        """
        Résout un lien relatif vers un chemin absolu sur le filesystem.

        Returns:
            Path si le fichier existe, None si cassé ou si le lien doit être ignoré.
        """
        # Fragment-only → toujours valide (pas vérifiable sans rendu HTML)
        if link_url.startswith('#'):
            return None  # signal skip

        # Supprimer le fragment avant de résoudre
        clean_url = self._strip_fragment(link_url)

        if not clean_url:
            return None  # lien "#section" après strip

        # Liens externes → hors scope (y compris les URLs entre chevrons <https://...>)
        if clean_url.startswith(('http://', 'https://', 'mailto:', '<http', '//')):
            return None  # signal skip

        # Lien root-relative (/foo/bar) → depuis content_root
        if clean_url.startswith('/'):
            bare = clean_url.lstrip('/')
            candidates = [
                content_root / bare,
                content_root / (bare + '.md'),
                content_root / bare / 'index.md',
            ]
            # Ajouter les variantes avec extensions alternatives
            for ext in ('.mdx', '.astro'):
                candidates.append(content_root / (bare + ext))
        else:
            # Lien relatif (../foo/bar ou ./foo)
            base = source_file.parent
            candidates = [
                (base / clean_url).resolve(),
                (base / (clean_url + '.md')).resolve(),
                (base / clean_url / 'index.md').resolve(),
            ]
            for ext in ('.mdx', '.astro'):
                candidates.append((base / (clean_url + ext)).resolve())

        for candidate in candidates:
            if candidate.exists():
                return candidate

        return None  # broken

    def check_from_project(self, project: Project) -> Dict[str, Any]:
        """
        Point d'entrée principal pour usage programmatique.
        Itère sur tous les content_directories configurés et fusionne les résultats.

        Args:
            project: Objet Project complet depuis le project store

        Returns:
            Résultats fusionnés de tous les dossiers de contenu
        """
        settings = project.settings
        if not settings:
            return {
                "success": False,
                "reason": "no_settings",
                "message": f"Projet '{project.name}' n'a pas de settings configurés."
            }

        if not settings.local_repo_path:
            return {
                "success": False,
                "reason": "no_local_repo",
                "message": f"Projet '{project.name}' n'a pas de repo cloné localement."
            }

        if not settings.content_directories:
            return {
                "success": False,
                "reason": "no_content_directory",
                "message": (
                    f"Projet '{project.name}' n'a pas de répertoire de contenu configuré. "
                    "Configurez-le dans les settings du projet."
                )
            }

        # Itérer sur tous les dossiers et fusionner les résultats
        all_broken: list = []
        seen_broken: set = set()
        total_valid = 0
        total_skipped = 0
        total_files = 0
        dirs_checked = []
        dirs_failed = []

        for content_dir_config in settings.content_directories:
            result = self.check_local_links(
                repo_path=settings.local_repo_path,
                content_dir=content_dir_config.path,
                file_extensions=content_dir_config.file_extensions,
            )

            if not result.get("success"):
                dirs_failed.append({
                    "dir": content_dir_config.path,
                    "reason": result.get("reason"),
                    "message": result.get("message"),
                })
                continue

            dirs_checked.append(content_dir_config.path)
            total_files += result["files_analyzed"]
            total_valid += result["valid_links_count"]
            total_skipped += result["skipped_count"]

            # Dédupliquer les broken links cross-dossiers
            for link in result["broken_links"]:
                key = (link["source"], link["target"])
                if key not in seen_broken:
                    seen_broken.add(key)
                    all_broken.append(link)

        if not dirs_checked:
            return {
                "success": False,
                "reason": "all_dirs_failed",
                "dirs_failed": dirs_failed,
                "message": "Aucun répertoire de contenu accessible.",
            }

        total_checked = len(all_broken) + total_valid
        return {
            "success": True,
            "source": "local_filesystem",
            "repo_path": settings.local_repo_path,
            "dirs_checked": dirs_checked,
            "dirs_failed": dirs_failed,
            "files_analyzed": total_files,
            "broken_links_count": len(all_broken),
            "broken_links": all_broken,
            "valid_links_count": total_valid,
            "skipped_count": total_skipped,
            "stats": {
                "total_links_checked": total_checked,
                "broken_rate": len(all_broken) / total_checked if total_checked else 0.0,
            },
        }

    @tool("Check Local Markdown Links")
    def check_local_links(
        self,
        repo_path: str,
        content_dir: str = "src/content",
        file_extensions: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """
        Vérifie tous les liens internes dans les fichiers markdown d'un repo local.
        Local-first : ne nécessite pas que le site soit déployé.

        Préférer check_from_project() pour usage programmatique (utilise ContentDirectoryConfig).

        Args:
            repo_path: Chemin absolu vers le repo cloné localement
            content_dir: Répertoire de contenu relatif au repo (ex: "src/content")
            file_extensions: Extensions à scanner (ex: [".md", ".mdx"]). Utilise DEFAULT_EXTENSIONS si absent.

        Returns:
            Dict avec broken_links, valid_count, skip_count, stats
        """
        extensions = file_extensions or self.DEFAULT_EXTENSIONS

        try:
            root = Path(repo_path)
            if not root.exists():
                return {
                    "success": False,
                    "reason": "no_local_repo",
                    "message": f"Repo introuvable : {repo_path}"
                }

            content_root = root / content_dir
            if not content_root.exists():
                return {
                    "success": False,
                    "reason": "content_dir_not_found",
                    "message": (
                        f"Répertoire de contenu '{content_dir}' introuvable dans {repo_path}. "
                        "Vérifiez la configuration du projet dans BizFlows."
                    )
                }

            broken_links = []
            seen_broken: set = set()  # (source, target) pour dédupliquer
            valid_count = 0
            skip_count = 0
            files_analyzed = 0

            # Découverte des fichiers — même pattern que repo_analyzer.py (rglob)
            # avec exclusion des répertoires non-content (node_modules, dist, etc.)
            for ext in extensions:
                for source_file in content_root.rglob(f'*{ext}'):
                    # Ignorer les fichiers dans les répertoires exclus
                    if any(part in self.EXCLUDE_DIRS for part in source_file.parts):
                        continue
                    files_analyzed += 1
                    try:
                        content = source_file.read_text(encoding='utf-8')
                    except (OSError, UnicodeDecodeError):
                        continue

                    for line_num, line in enumerate(content.splitlines(), start=1):
                        for match in self.LINK_PATTERN.finditer(line):
                            link_text = match.group(1)
                            link_url = match.group(2)

                            # Fragment-only, externe, ou angle-bracket URL → skip
                            if (
                                link_url.startswith('#')
                                or link_url.startswith(('http://', 'https://', 'mailto:', '//', '<http'))
                            ):
                                skip_count += 1
                                continue

                            resolved = self._resolve_link(source_file, link_url, content_root)

                            if resolved is None:
                                source_rel = str(source_file.relative_to(root))
                                key = (source_rel, link_url)
                                if key not in seen_broken:
                                    seen_broken.add(key)
                                    broken_links.append({
                                        "source": source_rel,
                                        "target": link_url,
                                        "link_text": link_text,
                                        "line": line_num
                                    })
                            else:
                                valid_count += 1

            return {
                "success": True,
                "source": "local_filesystem",
                "repo_path": repo_path,
                "content_dir": content_dir,
                "file_extensions": extensions,
                "files_analyzed": files_analyzed,
                "broken_links_count": len(broken_links),
                "broken_links": broken_links,
                "valid_links_count": valid_count,
                "skipped_count": skip_count,
                "stats": {
                    "total_links_checked": len(broken_links) + valid_count,
                    "broken_rate": (
                        len(broken_links) / (len(broken_links) + valid_count)
                        if (len(broken_links) + valid_count) > 0
                        else 0.0
                    )
                }
            }

        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }
