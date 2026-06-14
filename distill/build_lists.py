"""Derive the category and preservation lists in ``lists/`` from a MAME
``-listxml`` dump. This is the single source of truth for every list the
distiller consumes that can be computed from MAME's own data — rerun it after
each MAME version bump.

Emitted in one streaming pass:

- ``bios_only.xml``       — ``isbios="yes"``.
- ``devices_only.xml``    — ``isdevice="yes"`` with at least one ``<rom>``
  (ROM-bearing devices ship a zip; ROM-less ones don't and are irrelevant).
- ``clones.json``         — ``{clone: parent}`` from ``cloneof``.
- ``mechanical_only.xml`` — ``ismechanical="yes"``.
- ``naomi_only.xml``      — ``sourcefile`` in ``config.NAOMI_SOURCEFILES``.
- ``chd_only.xml``        — has an own (non-merge) ``<disk>`` that isn't
  ``status="nodump"`` (i.e. genuinely requires a CHD).

Not derived here: ``touch_only.xml`` (no clean MAME flag for touchscreen) and
``catver.ini`` (downloaded separately via ``distill.py -dl``).

Run:
    python distill/build_lists.py --xml lpl-builder/mamegames.xml
"""

from __future__ import annotations

import argparse
import json
import logging
import sys
import xml.etree.ElementTree as ET
from dataclasses import dataclass, field
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from config import (  # noqa: E402
    BIOS_XML,
    CHD_XML,
    CLONES_JSON,
    DEVICE_XML,
    LISTS_DIR,
    MECHANICAL_XML,
    NAOMI_SOURCEFILES,
    NAOMI_XML,
)

logger = logging.getLogger("build_lists")


@dataclass
class Lists:
    """Collected machine-name lists from one pass over the XML."""

    bios: list[str] = field(default_factory=list)
    devices: list[str] = field(default_factory=list)
    mechanical: list[str] = field(default_factory=list)
    naomi: list[str] = field(default_factory=list)
    chd: list[str] = field(default_factory=list)
    clones: dict[str, str] = field(default_factory=dict)

    def sort(self) -> None:
        self.bios.sort()
        self.devices.sort()
        self.mechanical.sort()
        self.naomi.sort()
        self.chd.sort()


def _requires_chd(machine: ET.Element) -> bool:
    """True if the machine ships its own (non-merge) real CHD disk."""
    for disk in machine.findall("disk"):
        if not disk.get("merge") and disk.get("status") != "nodump":
            return True
    return False


def collect(xml_path: Path) -> Lists:
    """Stream the XML once and bucket machines into every derived list."""
    out = Lists()
    for _, elem in ET.iterparse(xml_path, events=("end",)):
        if elem.tag != "machine":
            continue
        name = elem.get("name")
        if not name:
            elem.clear()
            continue

        if elem.get("isbios") == "yes":
            out.bios.append(name)
        elif elem.get("isdevice") == "yes" and elem.find("rom") is not None:
            out.devices.append(name)

        if elem.get("ismechanical") == "yes":
            out.mechanical.append(name)
        if (elem.get("sourcefile") or "") in NAOMI_SOURCEFILES:
            out.naomi.append(name)
        if _requires_chd(elem):
            out.chd.append(name)

        parent = elem.get("cloneof")
        if parent:
            out.clones[name] = parent

        elem.clear()

    out.sort()
    return out


def _build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="build_lists",
        description=(
            "Derive the distiller's category and preservation lists from a "
            "MAME -listxml dump. Rerun after each MAME version bump."
        ),
    )
    p.add_argument(
        "--xml",
        type=Path,
        required=True,
        help=(
            "Path to MAME -listxml output. Generate with "
            "`mame.exe -listxml > mamegames.xml`."
        ),
    )
    p.add_argument(
        "-v", "--verbose", action="store_true", help="Enable debug logging."
    )
    return p


def write_machine_list_xml(names: list[str], output: Path) -> None:
    """Write a ``<machines>`` document with one ``<machine name="..."/>`` per name."""
    output.parent.mkdir(parents=True, exist_ok=True)
    lines: list[str] = ['<?xml version="1.0" encoding="UTF-8"?>', "<machines>"]
    for name in names:
        lines.append(f'    <machine name="{name}"/>')
    lines.append("</machines>")
    lines.append("")
    output.write_text("\n".join(lines), encoding="utf-8")


def write_clone_map_json(clones: dict[str, str], output: Path) -> None:
    """Write the ``{clone: parent}`` map as sorted JSON."""
    output.parent.mkdir(parents=True, exist_ok=True)
    ordered = {name: clones[name] for name in sorted(clones)}
    output.write_text(
        json.dumps(ordered, indent=0, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )


def run(args: argparse.Namespace) -> int:
    xml_path: Path = args.xml.resolve()
    if not xml_path.is_file():
        logger.error("MAME XML not found: %s", xml_path)
        return 2

    logger.info("Scanning %s", xml_path)
    lists = collect(xml_path)
    logger.info(
        "bios=%d devices=%d mechanical=%d naomi=%d chd=%d clones=%d",
        len(lists.bios),
        len(lists.devices),
        len(lists.mechanical),
        len(lists.naomi),
        len(lists.chd),
        len(lists.clones),
    )

    outputs = {
        BIOS_XML: lists.bios,
        DEVICE_XML: lists.devices,
        MECHANICAL_XML: lists.mechanical,
        NAOMI_XML: lists.naomi,
        CHD_XML: lists.chd,
    }
    for filename, names in outputs.items():
        path = LISTS_DIR / filename
        write_machine_list_xml(names, path)
        logger.info("Wrote %s (%d)", path, len(names))

    clones_out = LISTS_DIR / CLONES_JSON
    write_clone_map_json(lists.clones, clones_out)
    logger.info("Wrote %s (%d)", clones_out, len(lists.clones))
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)
    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(levelname)s %(name)s: %(message)s",
    )
    return run(args)


if __name__ == "__main__":
    raise SystemExit(main())
