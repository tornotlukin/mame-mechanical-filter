"""Project-wide constants for lpl-builder.

All tunable values live here so other modules stay free of magic literals.
"""

from __future__ import annotations

from pathlib import Path

PACKAGE_ROOT: Path = Path(__file__).resolve().parent
PROJECT_ROOT: Path = PACKAGE_ROOT.parent

DEFAULT_XML_FILENAME: str = "mamegames.xml"
DEFAULT_OUTPUT_FILENAME: str = "MAME.lpl"

PLAYLIST_VERSION: str = "1.5"
PLAYLIST_DB_NAME: str = "MAME.lpl"

CORE_DETECT: str = "DETECT"
CRC32_PLACEHOLDER: str = "00000000|crc"

ROM_EXTENSION: str = ".zip"
