"""Create source archives in common formats using only the Python standard library."""

from __future__ import annotations

import tarfile
import zipfile
from pathlib import Path
from typing import Iterable

ARCHIVE_FORMATS = {
    "ZIP (.zip)": (".zip", "zip"),
    "TAR.GZ (.tar.gz)": (".tar.gz", "tar.gz"),
    "TAR.BZ2 (.tar.bz2)": (".tar.bz2", "tar.bz2"),
    "TAR.XZ (.tar.xz)": (".tar.xz", "tar.xz"),
}
EXCLUDED_DIRS = {
    ".git", ".hg", ".svn", ".venv", "venv", "env", "build", "dist",
    "__pycache__", ".pytest_cache", ".mypy_cache", ".ruff_cache",
}


def iter_project_files(project: Path, output: Path | None = None) -> Iterable[Path]:
    """Yield regular project files, excluding VCS, virtualenv and build artifacts."""
    root = project.expanduser().resolve()
    if not root.is_dir():
        raise ValueError(f"项目目录不存在：{root}")
    output_path = output.expanduser().resolve() if output else None
    for path in sorted(root.rglob("*")):
        if path.is_symlink() or not path.is_file():
            continue
        relative = path.relative_to(root)
        if any(part in EXCLUDED_DIRS for part in relative.parts[:-1]):
            continue
        if path.suffix in {".pyc", ".pyo"}:
            continue
        if output_path is not None and path.resolve() == output_path:
            continue
        yield path


def create_archive(project: Path, output: Path, archive_format: str) -> Path:
    """Create a project archive and return its absolute path.

    ``output`` is the complete archive filename. The output itself is excluded
    from the file list, so placing it under the project directory is safe.
    """
    if archive_format not in ARCHIVE_FORMATS:
        raise ValueError(f"不支持的压缩格式：{archive_format}")
    root = project.expanduser().resolve()
    if not root.is_dir():
        raise ValueError(f"项目目录不存在：{root}")
    destination = output.expanduser().resolve()
    extension, kind = ARCHIVE_FORMATS[archive_format]
    if not destination.name.lower().endswith(extension):
        raise ValueError(f"输出文件扩展名应为 {extension}")
    destination.parent.mkdir(parents=True, exist_ok=True)
    files = list(iter_project_files(root, destination))
    if kind == "zip":
        with zipfile.ZipFile(destination, "w", compression=zipfile.ZIP_DEFLATED) as archive:
            for path in files:
                archive.write(path, Path(root.name) / path.relative_to(root))
    else:
        mode = {"tar.gz": "w:gz", "tar.bz2": "w:bz2", "tar.xz": "w:xz"}[kind]
        with tarfile.open(destination, mode) as archive:
            for path in files:
                archive.add(path, arcname=Path(root.name) / path.relative_to(root), recursive=False)
    return destination
