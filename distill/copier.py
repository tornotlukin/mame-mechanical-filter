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
import shutil
from pathlib import Path

logger = logging.getLogger(__name__)


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


def copy_zip(src: Path, dest_dir: Path) -> None:
    """Copy a single ROM zip into dest_dir, overwriting if present."""
    dest_dir.mkdir(parents=True, exist_ok=True)
    shutil.copy2(src, dest_dir / src.name)


def copy_chd_folder(src_folder: Path, dest_dir: Path) -> None:
    """Copy a CHD subfolder (and its .chd files) into dest_dir/<name>/."""
    dest = dest_dir / src_folder.name
    if dest.exists():
        shutil.rmtree(dest)
    shutil.copytree(src_folder, dest)
