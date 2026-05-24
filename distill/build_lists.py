"""Generate the precomputed exclusion XML lists in ``lists/`` from a MAME
``-listxml`` dump.

Currently emits ``bios_only.xml`` (machines with ``isbios="yes"``). The other
list XMLs were generated previously by a sibling tool and are committed; this
script focuses on the BIOS list because it must be regenerated each time MAME
adds or removes BIOS machines.

Run:
    python distill/build_lists.py --xml lpl-builder/mamegames.xml
"""

from __future__ import annotations

import argparse
import logging
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from config import BIOS_XML, LISTS_DIR  # noqa: E402

logger = logging.getLogger("build_lists")


def _build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="build_lists",
        description=(
            "Generate exclusion XML lists from a MAME -listxml dump. "
            "Currently writes lists/bios_only.xml."
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


def collect_bios_names(xml_path: Path) -> list[str]:
    """Return sorted machine names where ``isbios="yes"``.

    Streams the XML with ``iterparse`` and clears each element to keep memory
    flat regardless of file size.
    """
    names: list[str] = []
    for _, elem in ET.iterparse(xml_path, events=("end",)):
        if elem.tag != "machine":
            continue
        if elem.get("isbios") == "yes":
            name = elem.get("name")
            if name:
                names.append(name)
        elem.clear()
    names.sort()
    return names


def write_bios_xml(names: list[str], output: Path) -> None:
    """Write a ``<machines>`` document with one ``<machine name="..."/>`` per BIOS."""
    output.parent.mkdir(parents=True, exist_ok=True)
    lines: list[str] = ['<?xml version="1.0" encoding="UTF-8"?>', "<machines>"]
    for name in names:
        lines.append(f'    <machine name="{name}"/>')
    lines.append("</machines>")
    lines.append("")
    output.write_text("\n".join(lines), encoding="utf-8")


def run(args: argparse.Namespace) -> int:
    xml_path: Path = args.xml.resolve()
    if not xml_path.is_file():
        logger.error("MAME XML not found: %s", xml_path)
        return 2

    logger.info("Scanning %s for BIOS machines", xml_path)
    names = collect_bios_names(xml_path)
    logger.info("Found %d BIOS machines", len(names))

    output = LISTS_DIR / BIOS_XML
    write_bios_xml(names, output)
    logger.info("Wrote %s", output)
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
