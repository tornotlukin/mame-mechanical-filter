"""Read MAME machine-name lists from XML and plain-text files in lists/."""

from __future__ import annotations

import logging
import xml.etree.ElementTree as ET
from pathlib import Path

logger = logging.getLogger(__name__)


def load_machine_names_xml(path: Path) -> set[str]:
    """Return the set of machine names from a `<machine name="..."/>` XML file.

    The repo's list XMLs may have a doubly-nested `<machines><machines>` root
    structure; we simply walk for any element tagged `machine` with a `name`
    attribute, which handles both nesting styles.
    """
    if not path.exists():
        logger.warning("List file missing, treating as empty: %s", path)
        return set()

    try:
        tree = ET.parse(path)
    except ET.ParseError as exc:
        logger.error("Failed to parse %s: %s", path, exc)
        return set()

    names: set[str] = set()
    for machine in tree.iter("machine"):
        name = machine.get("name")
        if name:
            names.add(name)
    return names


def load_machine_names_txt(path: Path) -> set[str]:
    """Return the set of machine names from a newline-separated text file."""
    if not path.exists():
        logger.warning("List file missing, treating as empty: %s", path)
        return set()

    with path.open("r", encoding="utf-8") as fh:
        return {line.strip() for line in fh if line.strip()}
