"""distill — copy a MAME ROM source folder to a destination, excluding flagged ROMs.

Run:
    python distill/distill.py --source C:\\roms
    python distill/distill.py --source C:\\roms --dest D:\\clean -chd
    python distill/distill.py -dl

See `python distill/distill.py --help` for the full flag surface.
"""

from __future__ import annotations

import argparse
import logging
import sys
import time
from pathlib import Path

# Make sibling modules importable when run as `python distill/distill.py`.
sys.path.insert(0, str(Path(__file__).resolve().parent))

from config import (  # noqa: E402  (sys.path tweak above)
    CATEGORY_BIOS,
    CATEGORY_CHD,
    CATEGORY_COMPUTER,
    CATEGORY_CONSOLE,
    CATEGORY_FRUIT,
    CATEGORY_GAMBLING,
    CATEGORY_MECHANICAL,
    CATEGORY_NAOMI,
    CATEGORY_NONRUNNABLE,
    CATEGORY_TOUCH,
    DEFAULT_DEST_SUBDIR,
    DEFAULT_EXCLUDED_CATEGORIES,
    LISTS_DIR,
)
from copier import (  # noqa: E402
    FAILED_COPIES,
    chd_subfolder_for,
    copy_chd_folder,
    copy_zip,
    find_rom_zips,
)
from downloader import download_latest_catver  # noqa: E402
from exclusions import build_exclusion_sets, classify  # noqa: E402

logger = logging.getLogger("distill")


def _build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="distill",
        description=(
            "Copy a MAME ROM folder to a destination, excluding mechanical, "
            "fruit, gambling, touchscreen, nonrunnable, and NAOMI/Dreamcast "
            "games by default."
        ),
    )
    p.add_argument(
        "--source",
        type=Path,
        default=Path.cwd(),
        help="Source ROM folder (default: current directory).",
    )
    p.add_argument(
        "--dest",
        type=Path,
        default=None,
        help=f"Destination folder (default: <source>/{DEFAULT_DEST_SUBDIR}/).",
    )
    p.add_argument(
        "-chd",
        "--chd",
        dest="include_chd",
        action="store_true",
        help=(
            "Include CHD-requiring games. Their .zip and matching .chd "
            "subfolder are treated as a unit and run through the same "
            "exclusion filters."
        ),
    )
    p.add_argument(
        "-dl",
        "--download",
        action="store_true",
        help="Download the latest catver.ini package from progettoSNAPS and exit.",
    )
    p.add_argument(
        "--keep-mechanical", action="store_true", help="Do not exclude mechanical games."
    )
    p.add_argument(
        "--keep-fruit", action="store_true", help="Do not exclude fruit/slot games."
    )
    p.add_argument(
        "--keep-gambling", action="store_true", help="Do not exclude Casino/* games."
    )
    p.add_argument(
        "--keep-touch", action="store_true", help="Do not exclude touchscreen games."
    )
    p.add_argument(
        "--keep-nonrunnable",
        action="store_true",
        help="Do not exclude machines MAME marks runnable=no.",
    )
    p.add_argument(
        "--keep-naomi",
        action="store_true",
        help="Do not exclude NAOMI/Dreamcast ROMs.",
    )
    p.add_argument(
        "--keep-computer",
        action="store_true",
        help="Do not exclude home computer ROMs (catver 'Computer / *').",
    )
    p.add_argument(
        "--keep-console",
        action="store_true",
        help="Do not exclude home console ROMs (catver 'Game Console / *').",
    )
    p.add_argument(
        "--exclude-bios",
        action="store_true",
        help=(
            "Exclude BIOS ROMs. By default BIOSes are always copied even "
            "when they also match another exclusion category (e.g. qsound "
            "is flagged nonrunnable but required by CPS-2 games)."
        ),
    )
    p.add_argument(
        "--prune",
        action="store_true",
        help=(
            "DELETE files in --source that match active exclusions, instead "
            "of copying. Use this to clean a previously-distilled folder "
            "after the filter rules change. Defaults to dry-run; pass --yes "
            "to actually delete."
        ),
    )
    p.add_argument(
        "--yes",
        action="store_true",
        help="Confirm destructive prune deletions. Required alongside --prune.",
    )
    p.add_argument(
        "-v", "--verbose", action="store_true", help="Enable debug logging."
    )
    return p


def _active_categories(args: argparse.Namespace) -> list[str]:
    """Return the ordered list of categories to exclude this run."""
    keep_map = {
        CATEGORY_MECHANICAL: args.keep_mechanical,
        CATEGORY_FRUIT: args.keep_fruit,
        CATEGORY_GAMBLING: args.keep_gambling,
        CATEGORY_TOUCH: args.keep_touch,
        CATEGORY_NONRUNNABLE: args.keep_nonrunnable,
        CATEGORY_NAOMI: args.keep_naomi,
        CATEGORY_COMPUTER: args.keep_computer,
        CATEGORY_CONSOLE: args.keep_console,
    }
    active = [cat for cat in DEFAULT_EXCLUDED_CATEGORIES if not keep_map.get(cat, False)]
    if args.exclude_bios:
        active.append(CATEGORY_BIOS)
    return active


def _resolve_dest(source: Path, dest: Path | None) -> Path:
    return dest if dest is not None else source / DEFAULT_DEST_SUBDIR


def _print_summary(
    total: int,
    copied: int,
    excluded_counts: dict[str, int],
    dest: Path,
    elapsed: float,
) -> None:
    print()
    print(f"Found {total} ROMs.")
    if excluded_counts:
        print("Excluded:")
        width = max(len(c) for c in excluded_counts)
        for cat in sorted(excluded_counts):
            print(f"  {cat:<{width}}  {excluded_counts[cat]}")
        print("  " + "-" * (width + 6))
    print(f"Copied {copied} to {dest}.")
    print(f"Done in {elapsed:.1f}s.")


def _print_prune_summary(
    total: int,
    excluded_counts: dict[str, int],
    deleted: int,
    dry_run: bool,
    source: Path,
    elapsed: float,
) -> None:
    print()
    print(f"Scanned {total} ROMs in {source}.")
    if excluded_counts:
        action = "Would delete" if dry_run else "Deleted"
        print(f"{action}:")
        width = max(len(c) for c in excluded_counts)
        for cat in sorted(excluded_counts):
            print(f"  {cat:<{width}}  {excluded_counts[cat]}")
        print("  " + "-" * (width + 6))
        total_action = sum(excluded_counts.values())
        print(f"  {'total':<{width}}  {total_action}")
    if dry_run:
        print()
        print("Dry-run only. Re-run with --yes to actually delete.")
    else:
        print(f"Deleted {deleted} files.")
    print(f"Done in {elapsed:.1f}s.")


def _run_prune(args: argparse.Namespace, source: Path) -> int:
    """Walk ``source`` and delete (or list) ROMs matching active exclusions."""
    active = _active_categories(args)
    logger.info("Active exclusions: %s", ", ".join(active) if active else "(none)")
    logger.info("Source: %s", source)
    logger.info("Mode:   %s", "DELETE" if args.yes else "dry-run")

    exclusion_sets = build_exclusion_sets(source)
    chd_set = exclusion_sets[CATEGORY_CHD]

    start = time.perf_counter()
    zips = find_rom_zips(source)
    excluded_counts: dict[str, int] = {}
    deleted = 0

    for zip_path in zips:
        name = zip_path.stem

        hit: str | None = None
        if name in chd_set and not args.include_chd:
            hit = CATEGORY_CHD
        else:
            hit = classify(name, exclusion_sets, set(active))

        if hit is None:
            continue

        excluded_counts[hit] = excluded_counts.get(hit, 0) + 1
        if args.yes:
            try:
                zip_path.unlink()
                deleted += 1
            except OSError as exc:
                logger.error("Failed to delete %s: %s", zip_path, exc)

    elapsed = time.perf_counter() - start
    _print_prune_summary(
        len(zips), excluded_counts, deleted, not args.yes, source, elapsed
    )
    return 0


def run(args: argparse.Namespace) -> int:
    if args.download:
        try:
            path = download_latest_catver(LISTS_DIR)
        except Exception as exc:
            logger.error("Download failed: %s", exc)
            return 1
        print(f"catver.ini saved to {path}")
        return 0

    source: Path = args.source.resolve()
    if not source.is_dir():
        logger.error("Source folder does not exist: %s", source)
        return 2

    if args.prune:
        if args.dest is not None:
            logger.error("--dest is incompatible with --prune (prune operates on --source).")
            return 2
        return _run_prune(args, source)

    dest = _resolve_dest(source, args.dest).resolve()
    if dest == source:
        logger.error("Destination cannot equal source: %s", dest)
        return 2

    active = _active_categories(args)
    logger.info("Active exclusions: %s", ", ".join(active) if active else "(none)")
    logger.info("Source: %s", source)
    logger.info("Dest:   %s", dest)

    exclusion_sets = build_exclusion_sets(source)
    chd_set = exclusion_sets[CATEGORY_CHD]

    start = time.perf_counter()
    zips = find_rom_zips(source)
    excluded_counts: dict[str, int] = {}
    copied = 0
    chd_skipped = 0

    for zip_path in zips:
        # Skip the destination if it lives inside the source folder.
        if dest in zip_path.parents:
            continue

        name = zip_path.stem

        if name in chd_set and not args.include_chd:
            chd_skipped += 1
            continue

        hit = classify(name, exclusion_sets, set(active))
        if hit is not None:
            excluded_counts[hit] = excluded_counts.get(hit, 0) + 1
            continue

        if not copy_zip(zip_path, dest):
            continue
        if args.include_chd:
            sub = chd_subfolder_for(source, name)
            if sub is not None:
                copy_chd_folder(sub, dest)
        copied += 1

    if chd_skipped:
        excluded_counts[CATEGORY_CHD] = chd_skipped

    elapsed = time.perf_counter() - start
    _print_summary(len(zips), copied, excluded_counts, dest, elapsed)
    if FAILED_COPIES:
        print()
        print(f"Failed to copy {len(FAILED_COPIES)} file(s):")
        for name, reason in FAILED_COPIES:
            print(f"  {name}  ({reason})")
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
