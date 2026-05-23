"""lpl-builder — build a RetroArch ``MAME.lpl`` playlist from a folder of ROMs.

Reads MAME's ``-listxml`` output to translate ROM filenames into game titles,
then writes a RetroArch playlist where every item's ``label`` is already the
proper game title. Bypasses the CRC32 scan that fails for MAME 0.280+ ROMs.

Run:
    python lpl-builder/build.py --source ./clean
    python lpl-builder/build.py --source ./clean \\
        --device-prefix "/storage/emulated/0/RetroArch/roms/mame" \\
        --output MAME.lpl

See ``python lpl-builder/build.py --help`` for the full flag surface.
"""

from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path

# Make sibling modules importable when run as `python lpl-builder/build.py`.
sys.path.insert(0, str(Path(__file__).resolve().parent))

from config import (  # noqa: E402  (sys.path tweak above)
    DEFAULT_OUTPUT_FILENAME,
    DEFAULT_XML_FILENAME,
    PACKAGE_ROOT,
    ROM_EXTENSION,
)
from writer import build_item, build_playlist, write_playlist  # noqa: E402
from xml_reader import load_descriptions  # noqa: E402

logger = logging.getLogger("lpl-builder")


def _build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="lpl-builder",
        description=(
            "Build a RetroArch MAME.lpl playlist from a folder of ROMs. "
            "Each item's label comes from the MAME -listxml description, so "
            "RetroArch shows proper game titles even for ROMs newer than its "
            "bundled MAME.rdb."
        ),
    )
    p.add_argument(
        "--source",
        type=Path,
        required=True,
        help="Folder containing the MAME ROM .zip files to enumerate.",
    )
    p.add_argument(
        "--xml",
        type=Path,
        default=PACKAGE_ROOT / DEFAULT_XML_FILENAME,
        help=(
            f"Path to MAME -listxml output (default: {DEFAULT_XML_FILENAME} "
            "alongside this script). Generate with "
            "`mame.exe -listxml > mamegames.xml`."
        ),
    )
    p.add_argument(
        "--device-prefix",
        type=str,
        default=None,
        help=(
            "Path prefix to use for each item's `path` field, joined with "
            "forward slashes. Example: "
            "`/storage/emulated/0/RetroArch/roms/mame`. When unset, the "
            "actual PC path of each ROM is used (handy for desktop testing)."
        ),
    )
    p.add_argument(
        "--output",
        "-o",
        type=Path,
        default=None,
        help=(
            f"Where to write the .lpl (default: {DEFAULT_OUTPUT_FILENAME} "
            "alongside this script)."
        ),
    )
    p.add_argument(
        "-v", "--verbose", action="store_true", help="Enable debug logging."
    )
    return p


def _enumerate_roms(source: Path) -> list[str]:
    """Return sorted stems of all ROM zips at the top level of ``source``."""
    return sorted(
        p.stem for p in source.glob(f"*{ROM_EXTENSION}") if p.is_file()
    )


def _resolve_output(output: Path | None) -> Path:
    if output is not None:
        return output.resolve()
    return (PACKAGE_ROOT / DEFAULT_OUTPUT_FILENAME).resolve()


def run(args: argparse.Namespace) -> int:
    source: Path = args.source.resolve()
    if not source.is_dir():
        logger.error("Source folder does not exist: %s", source)
        return 2

    xml_path: Path = args.xml.resolve()
    if not xml_path.is_file():
        logger.error("MAME XML not found: %s", xml_path)
        return 2

    output: Path = _resolve_output(args.output)

    rom_stems = _enumerate_roms(source)
    if not rom_stems:
        logger.error("No %s files found in %s", ROM_EXTENSION, source)
        return 2
    logger.info("Found %d ROMs in %s", len(rom_stems), source)

    logger.info("Reading descriptions from %s", xml_path)
    descriptions = load_descriptions(xml_path, set(rom_stems))
    logger.info(
        "Matched %d/%d descriptions in XML",
        len(descriptions),
        len(rom_stems),
    )

    items: list[dict[str, str]] = []
    missing: list[str] = []
    for stem in rom_stems:
        label = descriptions.get(stem)
        if label is None:
            missing.append(stem)
            label = stem
        items.append(build_item(stem, label, source, args.device_prefix))

    playlist = build_playlist(items)
    write_playlist(playlist, output)

    logger.info("Wrote %d items to %s", len(items), output)
    if missing:
        logger.warning(
            "%d ROMs had no XML match; labels fell back to the zip stem.",
            len(missing),
        )
        for name in missing[:10]:
            logger.warning("  no XML entry: %s", name)
        if len(missing) > 10:
            logger.warning("  ... and %d more", len(missing) - 10)
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
