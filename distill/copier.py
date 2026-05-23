"""Walk the source ROM folder and copy non-excluded ROMs to the destination.

Scope rules:
- Only `*.zip` files at the top level of the source folder are considered ROMs.
- A ROM has a "CHD payload" if a sibling folder of the same stem contains any
  `*.chd` files. Such ROMs are skipped entirely unless `--chd` is set, in which
  case the zip and the CHD subfolder both copy together.
- An excluded ROM is skipped silently; counts per category are tallied for the
  final summary.
"""

from __future__ import annotations

import logging
import os
import shutil
import subprocess
from pathlib import Path

logger = logging.getLogger(__name__)

FAILED_COPIES: list[tuple[str, str]] = []


def find_rom_zips(source: Path) -> list[Path]:
    """Return all top-level *.zip files in the source folder."""
    return sorted(p for p in source.glob("*.zip") if p.is_file())


def chd_subfolder_for(source: Path, rom_stem: str) -> Path | None:
    """Return the matching CHD subfolder if it exists AND contains at least one .chd."""
    candidate = source / rom_stem
    if not candidate.is_dir():
        return None
    has_chd = any(candidate.glob("*.chd"))
    return candidate if has_chd else None


def filesystem_chd_names(source: Path) -> set[str]:
    """Return ROM stems for which the source filesystem holds a CHD payload."""
    names: set[str] = set()
    for child in source.iterdir():
        if child.is_dir() and any(child.glob("*.chd")):
            names.add(child.name)
    return names


_COPY_CHUNK: int = 1024 * 1024  # 1 MiB — safe over SMB; shutil's default readinto path can fail with OSError 22 on some shares.


def _chunked_copyfile(src: Path, dst: Path) -> None:
    """Copy src to dst with an explicit chunked read/write loop.

    Why: shutil.copy2 uses _copyfileobj_readinto with a large memoryview, which
    raises OSError(22) on some SMB shares for certain file sizes. A plain
    read()/write() loop avoids the readinto path entirely.
    """
    with open(src, "rb") as fsrc, open(dst, "wb") as fdst:
        while True:
            buf = fsrc.read(_COPY_CHUNK)
            if not buf:
                break
            fdst.write(buf)


def _robocopy_single(src: Path, dest_dir: Path) -> bool:
    """Fallback: use Windows robocopy for a single file. Returns True on success.

    Robocopy handles SMB quirks (transient OSError 22, retries, large files)
    better than Python's file IO. Exit codes 0/1 mean success.
    """
    if os.name != "nt":
        return False
    try:
        result = subprocess.run(
            [
                "robocopy",
                str(src.parent),
                str(dest_dir),
                src.name,
                "/R:3",
                "/W:2",
                "/NP",
                "/NJH",
                "/NJS",
                "/NDL",
                "/NFL",
            ],
            capture_output=True,
            text=True,
        )
    except FileNotFoundError:
        logger.warning("robocopy not found on PATH; cannot fall back")
        return False
    # Robocopy exit codes: 0 = nothing copied (already up-to-date), 1 = files copied.
    # 2/3 = extra/mismatched but still OK. >=8 = real failure.
    if result.returncode < 8:
        return True
    logger.error("robocopy failed for %s (rc=%d): %s", src.name, result.returncode, result.stdout.strip())
    return False


def copy_zip(src: Path, dest_dir: Path) -> bool:
    """Copy a single ROM zip into dest_dir. Returns True if dest now has the file.

    Skips when the destination already exists with the same size — makes the
    distill resumable after a crash without re-reading every file.

    On OSError (common with SMB shares), falls back to Windows robocopy. If
    that also fails, records the failure and returns False so the caller can
    continue with the rest of the run instead of aborting.
    """
    dest_dir.mkdir(parents=True, exist_ok=True)
    dst = dest_dir / src.name
    try:
        if dst.exists() and dst.stat().st_size == src.stat().st_size:
            return True
    except OSError:
        pass

    try:
        _chunked_copyfile(src, dst)
    except OSError as exc:
        logger.warning("Python copy failed for %s (%s); falling back to robocopy", src.name, exc)
        if dst.exists():
            try:
                dst.unlink()
            except OSError:
                pass
        if not _robocopy_single(src, dest_dir):
            FAILED_COPIES.append((src.name, str(exc)))
            return False
    else:
        try:
            shutil.copystat(src, dst)
        except OSError as exc:
            logger.debug("copystat failed for %s: %s", dst, exc)
    return True


def copy_chd_folder(src_folder: Path, dest_dir: Path) -> None:
    """Copy a CHD subfolder (and its .chd files) into dest_dir/<name>/."""
    dest = dest_dir / src_folder.name
    if dest.exists():
        shutil.rmtree(dest)
    shutil.copytree(src_folder, dest)
