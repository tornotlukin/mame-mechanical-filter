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
NAOMI_XML: str = "naomi_only.xml"
CHD_XML: str = "chd_only.xml"
CHD_TXT: str = "chdlist.txt"
BIOS_XML: str = "bios_only.xml"
DEVICE_XML: str = "devices_only.xml"
CLONES_JSON: str = "clones.json"

CATVER_INDEX_URL: str = "https://www.progettosnaps.net/catver/"
CATVER_DOWNLOAD_URL: str = (
    "https://www.progettosnaps.net/download/?tipo=catver&file={filename}"
)

CATVER_PREFIX_ELECTROMECHANICAL: str = "Electromechanical"
CATVER_PREFIX_CASINO: str = "Casino"
CATVER_PREFIX_COMPUTER: str = "Computer"
CATVER_PREFIX_CONSOLE: str = "Game Console"
CATVER_FRUIT_SUBSTRINGS: tuple[str, ...] = (
    "Casino / Slot Machine",
    "Electromechanical / Reels",
)

# MAME -listxml sourcefiles that identify NAOMI / Atomiswave (Dreamcast-derived)
# hardware. Machines from these drivers belong to a different core and are
# excluded by the `naomi` category. Used by build_lists.py to derive
# naomi_only.xml.
NAOMI_SOURCEFILES: frozenset[str] = frozenset(
    {
        "sega/naomi.cpp",
        "sega/naomigd.cpp",
        "sega/naomim1.cpp",
        "sega/naomim2.cpp",
        "sega/naomim4.cpp",
        "sega/naomirom.cpp",
        "sega/dc_atomiswave.cpp",
    }
)

DEFAULT_DEST_SUBDIR: str = "_distilled"

# Romset pack types. Determines how clone ROMs and dependency ROMs are stored,
# which dictates what must travel with a kept game so it still runs:
#   merged      — clone ROMs live inside the parent zip; BIOS/device separate.
#   split       — clone zip holds only diffs and needs the parent zip present.
#   non-merged  — every zip is fully self-contained.
# "auto" detects merged vs split/non-merged from the source folder.
SET_TYPE_AUTO: str = "auto"
SET_TYPE_MERGED: str = "merged"
SET_TYPE_SPLIT: str = "split"
SET_TYPE_NONMERGED: str = "non-merged"
SET_TYPES: tuple[str, ...] = (
    SET_TYPE_AUTO,
    SET_TYPE_MERGED,
    SET_TYPE_SPLIT,
    SET_TYPE_NONMERGED,
)

CATEGORY_MECHANICAL: str = "mechanical"
CATEGORY_FRUIT: str = "fruit"
CATEGORY_GAMBLING: str = "gambling"
CATEGORY_TOUCH: str = "touch"
CATEGORY_NAOMI: str = "naomi"
CATEGORY_CHD: str = "chd"
CATEGORY_COMPUTER: str = "computer"
CATEGORY_CONSOLE: str = "console"
# Special "preservation" categories: ROMs in these sets are always copied,
# overriding any other exclusion, because games depend on them. BIOS and
# device ROMs live in separate zips in merged/split sets; deleting them
# breaks every game that references them (e.g. qsound for CPS-2 titles).
# Use --exclude-bios / --exclude-devices to opt out.
#
# Note: there is intentionally no "nonrunnable" category. The original tool's
# nonrunnable_only.xml turned out to be 100% devices (isdevice=yes), so it was
# really deleting device ROMs that games depend on — the cause of "many games
# don't work after distilling". Devices are now preserved, not excluded.
CATEGORY_BIOS: str = "bios"
CATEGORY_DEVICE: str = "device"

DEFAULT_EXCLUDED_CATEGORIES: tuple[str, ...] = (
    CATEGORY_MECHANICAL,
    CATEGORY_FRUIT,
    CATEGORY_GAMBLING,
    CATEGORY_TOUCH,
    CATEGORY_NAOMI,
    CATEGORY_COMPUTER,
    CATEGORY_CONSOLE,
)
