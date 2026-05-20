"""Local filesystem object storage.

Provides a thin abstraction over local file I/O so that the storage backend
(S3 / MinIO) can be swapped later by changing only this module.
"""

import os
import hashlib
from pathlib import Path

STORAGE_ROOT = os.getenv("STORAGE_ROOT", "./data")


def _ensure_dir(path: Path) -> None:
    path.mkdir(parents=True, exist_ok=True)


def save_snapshot(source_id: str, item_id: str, content: str | bytes, suffix: str = "html") -> str:
    """Save raw snapshot content and return its relative URI."""
    rel_path = f"snapshots/{source_id}/{item_id}/raw.{suffix}"
    full_path = Path(STORAGE_ROOT) / rel_path
    _ensure_dir(full_path.parent)
    mode = "wb" if isinstance(content, bytes) else "w"
    encoding = "utf-8" if isinstance(content, str) else None
    with open(full_path, mode, encoding=encoding) as f:
        f.write(content)
    return rel_path


def save_media(source_id: str, item_id: str, filename: str, content: bytes) -> str:
    """Save a media file (audio/video/image) and return its relative URI."""
    rel_path = f"media/{source_id}/{item_id}/{filename}"
    full_path = Path(STORAGE_ROOT) / rel_path
    _ensure_dir(full_path.parent)
    with open(full_path, "wb") as f:
        f.write(content)
    return rel_path


def read_bytes(rel_path: str) -> bytes:
    """Read file content as bytes."""
    full_path = Path(STORAGE_ROOT) / rel_path
    if not full_path.exists():
        raise FileNotFoundError(f"File not found: {rel_path}")
    return full_path.read_bytes()


def read_text(rel_path: str) -> str:
    """Read file content as UTF-8 text."""
    full_path = Path(STORAGE_ROOT) / rel_path
    if not full_path.exists():
        raise FileNotFoundError(f"File not found: {rel_path}")
    return full_path.read_text(encoding="utf-8")


def content_hash(text: str) -> str:
    """Compute SHA-256 hash of normalized text content for deduplication."""
    normalized = text.strip().lower()
    return hashlib.sha256(normalized.encode("utf-8")).hexdigest()
