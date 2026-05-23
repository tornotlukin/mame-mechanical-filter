"""Project-wide constants for distill.

All tunable values live here so other modules stay free of magic literals.
"""

from __future__ import annotations

from pathlib import Path

PROJECT_ROOT: Path = Path(__file__).resolve().parent.parent
LISTS_DIR: Path = PROJECT_ROOT / "lists"

CATVER_FILENAME: str = "catver.ini"
MECHANICAL_XML: str = "mechanical_only.xml"
TOUCH_XML: str = "touch_only.xml"
NONRUNNABLE_XML: str = "nonrunnable_only.xml"
NAOMI_XML: str = "naomi_only.xml"
CHD_XML: str = "chd_only.xml"
CHD_TXT: str = "chdlist.txt"

CATVER_INDEX_URL: str = "https://www.progettosnaps.net/catver/"
CATVER_DOWNLOAD_URL: str = (
    "https://www.progettosnaps.net/download/?tipo=catver&file={filename}"
)

CATVER_PREFIX_ELECTROMECHANICAL: str = "Electromechanical"
CATVER_PREFIX_CASINO: str = "Casino"
CATVER_FRUIT_SUBSTRINGS: tuple[str, ...] = (
    "Casino / Slot Machine",
    "Electromechanical / Reels",
)

DEFAULT_DEST_SUBDIR: str = "_distilled"

CATEGORY_MECHANICAL: str = "mechanical"
CATEGORY_FRUIT: str = "fruit"
CATEGORY_GAMBLING: str = "gambling"
CATEGORY_TOUCH: str = "touch"
CATEGORY_NONRUNNABLE: str = "nonrunnable"
CATEGORY_NAOMI: str = "naomi"
CATEGORY_CHD: str = "chd"

DEFAULT_EXCLUDED_CATEGORIES: tuple[str, ...] = (
    CATEGORY_MECHANICAL,
    CATEGORY_FRUIT,
    CATEGORY_GAMBLING,
    CATEGORY_TOUCH,
    CATEGORY_NONRUNNABLE,
    CATEGORY_NAOMI,
)
