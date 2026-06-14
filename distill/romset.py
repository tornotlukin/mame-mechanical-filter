"""Romset pack-type detection and clone dependency resolution.

A MAME game zip is rarely self-contained. How its clone and dependency ROMs
are packed determines what must travel with a kept game so it still runs:

- **merged**     — clone ROMs live inside the parent zip; clones have no zip.
- **split**      — clone zip holds only its diffs and needs the parent zip.
- **non-merged** — every zip is fully self-contained.

This module loads the ``{clone: parent}`` map produced by ``build_lists.py``,
detects the pack type from what zips actually exist in the source folder, and
computes the set of parent zips a collection of kept clones depends on.
"""

from __future__ import annotations

import json
import logging
from pathlib import Path

from config import (
    CLONES_JSON,
    LISTS_DIR,
    SET_TYPE_MERGED,
    SET_TYPE_NONMERGED,
    SET_TYPE_SPLIT,
)

logger = logging.getLogger(__name__)

# How many clones to sample when sniffing the pack type. Existence checks are
# cheap locally but add up over SMB, so keep the sample modest.
_DETECT_SAMPLE: int = 400
# Below this fraction of sampled clones present as standalone zips, the set is
# treated as merged (clones folded into parents).
_MERGED_RATIO_CEILING: float = 0.05


def load_clone_map(path: Path | None = None) -> dict[str, str]:
    """Return the ``{clone: parent}`` map, or empty if the list is missing."""
    target = path if path is not None else LISTS_DIR / CLONES_JSON
    if not target.exists():
        logger.warning("Clone map missing, treating as empty: %s", target)
        return {}
    try:
        data = json.loads(target.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        logger.error("Failed to read clone map %s: %s", target, exc)
        return {}
    return {str(k): str(v) for k, v in data.items()}


def detect_set_type(source: Path, clone_map: dict[str, str]) -> str:
    """Sniff the pack type from which clone zips exist in ``source``.

    Returns ``merged`` when clones are folded into parents (their standalone
    zips are absent). Otherwise returns ``split`` — the safe superset, since
    pulling parents on a genuinely non-merged set is harmless redundancy.
    Pass an explicit ``--set-type`` to override.
    """
    clones = list(clone_map)
    if not clones:
        logger.warning("No clone data; assuming non-merged.")
        return SET_TYPE_NONMERGED

    step = max(1, len(clones) // _DETECT_SAMPLE)
    sample = clones[::step][:_DETECT_SAMPLE]
    present = sum(1 for c in sample if (source / f"{c}.zip").is_file())
    ratio = present / len(sample)
    logger.debug(
        "Set-type sniff: %d/%d sampled clone zips present (%.1f%%)",
        present,
        len(sample),
        ratio * 100,
    )
    return SET_TYPE_MERGED if ratio < _MERGED_RATIO_CEILING else SET_TYPE_SPLIT


def parent_closure(kept: set[str], clone_map: dict[str, str]) -> set[str]:
    """Return parent zips required by kept clones that aren't kept already.

    Walks each kept clone up its ``cloneof`` chain (clones are normally one
    level deep, but the loop tolerates deeper chains and guards against cycles)
    and collects every ancestor not already in ``kept``.
    """
    required: set[str] = set()
    for name in kept:
        parent = clone_map.get(name)
        seen: set[str] = set()
        while parent and parent not in kept and parent not in seen:
            required.add(parent)
            seen.add(parent)
            parent = clone_map.get(parent)
    return required
