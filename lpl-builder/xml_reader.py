"""Stream-parse a MAME ``-listxml`` dump for machine descriptions.

``ElementTree.iterparse`` is used so the 300+ MB XML never lands in memory whole.
Each ``<machine>`` element is cleared after inspection to keep memory flat.
"""

from __future__ import annotations

import logging
import xml.etree.ElementTree as ET
from pathlib import Path

logger = logging.getLogger(__name__)


def load_descriptions(xml_path: Path, wanted: set[str]) -> dict[str, str]:
    """Return ``{machine_name: <description> text}`` for every name in ``wanted``.

    Streams through the file with ``iterparse`` and clears each processed
    element so memory usage stays flat regardless of XML size. Returns early
    once every wanted name has been resolved.
    """
    result: dict[str, str] = {}
    remaining: set[str] = set(wanted)

    for _, elem in ET.iterparse(xml_path, events=("end",)):
        if elem.tag != "machine":
            continue
        name = elem.get("name")
        if name in remaining:
            desc_elem = elem.find("description")
            if desc_elem is not None and desc_elem.text:
                result[name] = desc_elem.text
            remaining.discard(name)
            if not remaining:
                elem.clear()
                break
        elem.clear()

    return result
