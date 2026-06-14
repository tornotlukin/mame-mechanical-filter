"""Combine the various data sources into one exclusion map.

Output is a `dict[category_name, set[machine_name]]` where each set lists ROMs
that belong to that exclusion category. The CLI then unions whichever
categories are active for the run.
"""

from __future__ import annotations

import logging
from pathlib import Path

from catver import (
    casino_names,
    computer_names,
    console_names,
    electromechanical_names,
    fruit_names,
    parse_catver,
)
from config import (
    BIOS_XML,
    CATEGORY_BIOS,
    CATEGORY_CHD,
    CATEGORY_COMPUTER,
    CATEGORY_CONSOLE,
    CATEGORY_DEVICE,
    CATEGORY_FRUIT,
    CATEGORY_GAMBLING,
    CATEGORY_MECHANICAL,
    CATEGORY_NAOMI,
    CATEGORY_TOUCH,
    CATVER_FILENAME,
    CHD_TXT,
    CHD_XML,
    DEVICE_XML,
    LISTS_DIR,
    MECHANICAL_XML,
    NAOMI_XML,
    TOUCH_XML,
)
from copier import filesystem_chd_names
from loaders import load_machine_names_txt, load_machine_names_xml

logger = logging.getLogger(__name__)


def build_exclusion_sets(source: Path) -> dict[str, set[str]]:
    """Build the per-category exclusion sets from XML lists, catver, and the FS.

    The CHD category is the union of three sources: chdlist.txt, chd_only.xml,
    and any subfolder of `source` that already contains a .chd file.
    """
    catver_path = LISTS_DIR / CATVER_FILENAME
    catver = parse_catver(catver_path)

    xml_mech = load_machine_names_xml(LISTS_DIR / MECHANICAL_XML)
    xml_touch = load_machine_names_xml(LISTS_DIR / TOUCH_XML)
    xml_naomi = load_machine_names_xml(LISTS_DIR / NAOMI_XML)
    xml_chd = load_machine_names_xml(LISTS_DIR / CHD_XML)
    txt_chd = load_machine_names_txt(LISTS_DIR / CHD_TXT)
    fs_chd = filesystem_chd_names(source) if source.is_dir() else set()

    xml_bios = load_machine_names_xml(LISTS_DIR / BIOS_XML)
    xml_device = load_machine_names_xml(LISTS_DIR / DEVICE_XML)

    return {
        CATEGORY_MECHANICAL: xml_mech | electromechanical_names(catver),
        CATEGORY_FRUIT: fruit_names(catver),
        CATEGORY_GAMBLING: casino_names(catver),
        CATEGORY_TOUCH: xml_touch,
        CATEGORY_NAOMI: xml_naomi,
        CATEGORY_CHD: xml_chd | txt_chd | fs_chd,
        CATEGORY_COMPUTER: computer_names(catver),
        CATEGORY_CONSOLE: console_names(catver),
        CATEGORY_BIOS: xml_bios,
        CATEGORY_DEVICE: xml_device,
    }


# Categories whose members are always preserved (copied) unless the matching
# category is explicitly activated via --exclude-bios / --exclude-devices.
# Games reference these external zips, so dropping them breaks the games.
PRESERVATION_CATEGORIES: tuple[str, ...] = (CATEGORY_BIOS, CATEGORY_DEVICE)


def classify(
    name: str, exclusion_sets: dict[str, set[str]], active_categories: set[str]
) -> str | None:
    """Return the first active category that contains `name`, else None.

    Preservation: if `name` belongs to a preservation category (BIOS or
    device) and that category is not active (i.e. the corresponding
    --exclude-* flag was not passed), the ROM passes through even when it
    also matches another active exclusion category. This keeps the external
    dependency zips that games rely on (e.g. qsound is flagged nonrunnable
    but every CPS-2 game needs it).

    Iteration order is the active-categories set order — for tally purposes
    we want a stable category attribution; the caller passes a list to control
    priority.
    """
    for preserve in PRESERVATION_CATEGORIES:
        if preserve in active_categories:
            continue
        if name in exclusion_sets.get(preserve, set()):
            return None
    for cat in active_categories:
        if name in exclusion_sets.get(cat, set()):
            return cat
    return None
