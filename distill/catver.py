"""Parse catver.ini and derive category-based exclusion sets.

catver.ini is a Windows-style INI with a `[Category]` section whose entries
look like:

    pacman=Maze / Collect
    smb=Platform / Run Jump
    areafgt=Casino / Slot Machine * Mature *

We tolerate the trailing ` * Mature *` marker and use the substring before it
as the category string.
"""

from __future__ import annotations

import logging
from pathlib import Path

from config import (
    CATVER_FRUIT_SUBSTRINGS,
    CATVER_PREFIX_CASINO,
    CATVER_PREFIX_ELECTROMECHANICAL,
)

logger = logging.getLogger(__name__)

CATEGORY_SECTION: str = "[Category]"
MATURE_MARKER: str = "* Mature *"


def parse_catver(path: Path) -> dict[str, str]:
    """Return a mapping of machine name -> catver category string.

    The Mature marker is stripped so the returned value is just the category.
    Lines outside the `[Category]` section are ignored.
    """
    if not path.exists():
        logger.warning("catver.ini missing: %s (use -dl to download)", path)
        return {}

    mapping: dict[str, str] = {}
    in_category = False

    with path.open("r", encoding="utf-8", errors="replace") as fh:
        for raw in fh:
            line = raw.strip()
            if not line or line.startswith(";"):
                continue
            if line.startswith("["):
                in_category = line == CATEGORY_SECTION
                continue
            if not in_category or "=" not in line:
                continue

            name, _, category = line.partition("=")
            name = name.strip()
            category = category.strip()
            if category.endswith(MATURE_MARKER):
                category = category[: -len(MATURE_MARKER)].strip()
            if name:
                mapping[name] = category

    logger.info("Loaded %d catver entries from %s", len(mapping), path)
    return mapping


def names_matching_prefix(catver: dict[str, str], prefix: str) -> set[str]:
    """Return names whose catver category starts with the given prefix."""
    return {name for name, cat in catver.items() if cat.startswith(prefix)}


def names_matching_any_substring(
    catver: dict[str, str], substrings: tuple[str, ...]
) -> set[str]:
    """Return names whose catver category contains any of the substrings."""
    return {
        name
        for name, cat in catver.items()
        if any(sub in cat for sub in substrings)
    }


def electromechanical_names(catver: dict[str, str]) -> set[str]:
    """Names categorized as Electromechanical / *."""
    return names_matching_prefix(catver, CATVER_PREFIX_ELECTROMECHANICAL)


def casino_names(catver: dict[str, str]) -> set[str]:
    """Names categorized as Casino / * (used for the gambling exclusion)."""
    return names_matching_prefix(catver, CATVER_PREFIX_CASINO)


def fruit_names(catver: dict[str, str]) -> set[str]:
    """Names matching the configured 'fruit' substrings."""
    return names_matching_any_substring(catver, CATVER_FRUIT_SUBSTRINGS)
