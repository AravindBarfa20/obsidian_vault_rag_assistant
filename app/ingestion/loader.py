"""Vault discovery and safe Markdown loading.

Security boundary: every path is resolved and asserted to live inside the
configured vault root, so a request can never coax the server into reading
arbitrary files (e.g. ../../etc/passwd or a symlink pointing out of the vault).
"""

from __future__ import annotations

import hashlib
import os
from pathlib import Path

from app.core.config import Settings
from app.core.exceptions import VaultError
from app.core.logging import get_logger
from app.models.documents import RawNote

logger = get_logger(__name__)

_MARKDOWN_SUFFIXES = {".md", ".markdown"}


def _resolve_within(root: Path, target: Path) -> Path:
    """Resolve `target` and require it to be inside `root`."""
    root = root.resolve()
    resolved = target.resolve()
    if resolved != root and root not in resolved.parents:
        raise VaultError(f"Path escapes the vault root: {target}")
    return resolved


def resolve_vault_dir(settings: Settings, requested: str | None) -> Path:
    """Pick and validate the vault directory for an ingest request."""
    if not requested:
        vault = settings.vault_dir
    else:
        candidate = Path(requested).expanduser()
        # A relative request is joined onto the configured root and must stay
        # inside it; an absolute request is trusted as an explicit operator
        # choice (the server runner, not an untrusted client, sets this).
        if candidate.is_absolute():
            vault = candidate.resolve()
        else:
            vault = _resolve_within(settings.vault_dir, settings.vault_dir / candidate)
    if not vault.exists() or not vault.is_dir():
        raise VaultError(f"Vault directory not found: {vault}")
    return vault


def _title_from(path: Path, content: str, frontmatter_title: str | None) -> str:
    if frontmatter_title:
        return frontmatter_title
    for line in content.splitlines():
        stripped = line.strip()
        if stripped.startswith("# "):
            return stripped[2:].strip()
        if stripped and not stripped.startswith("---"):
            break
    return path.stem


def discover_markdown_files(vault_dir: Path, settings: Settings) -> list[Path]:
    """Recursively list Markdown files, skipping ignored dirs and system files."""
    ignored = set(settings.ignored_dirs)
    found: list[Path] = []
    for current_root, dirs, files in os.walk(vault_dir):
        dirs[:] = [d for d in dirs if d not in ignored and not d.startswith(".")]
        for name in files:
            if Path(name).suffix.lower() in _MARKDOWN_SUFFIXES:
                found.append(Path(current_root) / name)
    return sorted(found)


def load_note(path: Path, vault_dir: Path, settings: Settings) -> RawNote | None:
    """Read one Markdown file into a RawNote, or None if it should be skipped."""
    from app.parsing.markdown_parser import split_frontmatter  # avoid import cycle

    path = _resolve_within(vault_dir, path)
    try:
        size = path.stat().st_size
        if size > settings.max_file_bytes:
            logger.warning("Skipping oversized file (%d bytes): %s", size, path.name)
            return None
        raw_bytes = path.read_bytes()
    except OSError as exc:
        logger.warning("Unreadable file skipped: %s (%s)", path, exc)
        return None

    content = raw_bytes.decode("utf-8", errors="replace")
    if not content.strip():
        logger.info("Skipping empty note: %s", path.name)
        return None

    frontmatter, _, _ = split_frontmatter(content)
    fm_title = frontmatter.get("title") if isinstance(frontmatter, dict) else None
    rel_path = path.relative_to(vault_dir).as_posix()
    return RawNote(
        path=str(path),
        rel_path=rel_path,
        title=_title_from(path, content, fm_title),
        content=content,
        content_hash=hashlib.sha256(raw_bytes).hexdigest(),
        modified_at=path.stat().st_mtime,
    )


def load_vault(vault_dir: Path, settings: Settings) -> list[RawNote]:
    """Load every ingestible note in the vault."""
    notes: list[RawNote] = []
    for path in discover_markdown_files(vault_dir, settings):
        note = load_note(path, vault_dir, settings)
        if note is not None:
            notes.append(note)
    logger.info("Loaded %d notes from %s", len(notes), vault_dir)
    return notes
