"""Build and write a RetroArch ``.lpl`` playlist file.

Field order matches ``playlist_write_file()`` in ``libretro/RetroArch``'s
``playlist.c`` (RetroArch tolerates other orderings but we mirror its own
output for parity with auto-generated playlists).
"""

from __future__ import annotations

import json
import logging
from pathlib import Path

from config import (
    CORE_DETECT,
    CRC32_PLACEHOLDER,
    PLAYLIST_DB_NAME,
    PLAYLIST_VERSION,
    ROM_EXTENSION,
)

logger = logging.getLogger(__name__)


def build_path(rom_filename: str, source: Path, device_prefix: str | None) -> str:
    """Return the value for an item's ``path`` field.

    When ``device_prefix`` is set, it is joined with the ROM filename using a
    forward slash (Android paths). When unset, the actual PC path of the ROM
    file is returned (useful for testing on a desktop RetroArch install).
    """
    if device_prefix:
        prefix = device_prefix.rstrip("/").rstrip("\\")
        return f"{prefix}/{rom_filename}"
    return str(source / rom_filename)


def build_item(
    rom_stem: str,
    label: str,
    source: Path,
    device_prefix: str | None,
    core_path: str = CORE_DETECT,
    core_name: str = CORE_DETECT,
) -> dict[str, str]:
    """Build a single playlist entry.

    ``core_path``/``core_name`` default to ``"DETECT"`` (RetroArch picks the
    active core at runtime). Pass explicit values to hard-bind every entry to a
    specific core's ``.so``.
    """
    return {
        "path": build_path(f"{rom_stem}{ROM_EXTENSION}", source, device_prefix),
        "label": label,
        "core_path": core_path,
        "core_name": core_name,
        "crc32": CRC32_PLACEHOLDER,
        "db_name": PLAYLIST_DB_NAME,
    }


def build_playlist(
    items: list[dict[str, str]],
    default_core_path: str = "",
    default_core_name: str = "",
) -> dict[str, object]:
    """Return the top-level playlist dict, ordered as RetroArch writes it.

    ``default_core_path``/``default_core_name`` are written verbatim; leave
    them empty (the default) for a ``DETECT`` playlist.
    """
    return {
        "version": PLAYLIST_VERSION,
        "default_core_path": default_core_path,
        "default_core_name": default_core_name,
        "label_display_mode": 0,
        "right_thumbnail_mode": 0,
        "left_thumbnail_mode": 0,
        "thumbnail_match_mode": 0,
        "sort_mode": 0,
        "items": items,
    }


def write_playlist(playlist: dict[str, object], output: Path) -> None:
    """Write the playlist to ``output`` as UTF-8 JSON, indent=2."""
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(
        json.dumps(playlist, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
