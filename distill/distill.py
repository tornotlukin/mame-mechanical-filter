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
    CATEGORY_DEVICE,
    CATEGORY_FRUIT,
    CATEGORY_GAMBLING,
    CATEGORY_MECHANICAL,
    CATEGORY_NAOMI,
    CATEGORY_TOUCH,
    DEFAULT_DEST_SUBDIR,
    DEFAULT_EXCLUDED_CATEGORIES,
    LISTS_DIR,
    SET_TYPE_AUTO,
    SET_TYPE_SPLIT,
    SET_TYPES,
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
from romset import detect_set_type, load_clone_map, parent_closure  # noqa: E402

logger = logging.getLogger("distill")


def _build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="distill",
        description=(
            "Copy a MAME ROM folder to a destination, excluding mechanical, "
            "fruit, gambling, touchscreen, computer, console, and "
            "NAOMI/Dreamcast games by default. BIOS and device ROMs are "
            "preserved."
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
            "when they also match another exclusion category (e.g. neogeo "
            "is required by every Neo Geo game)."
        ),
    )
    p.add_argument(
        "--exclude-devices",
        action="store_true",
        help=(
            "Exclude device ROMs. By default ROM-bearing devices are always "
            "copied (e.g. qsound is required by CPS-2 games). Dropping them "
            "breaks games in merged/split sets."
        ),
    )
    p.add_argument(
        "--set-type",
        choices=SET_TYPES,
        default=SET_TYPE_AUTO,
        help=(
            "Romset pack type. 'split' pulls each kept clone's parent zip "
            "along with it (and protects parents from prune). 'merged' and "
            "'non-merged' need no parent handling. 'auto' (default) detects "
            "merged vs split from the source folder."
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
        CATEGORY_NAOMI: args.keep_naomi,
        CATEGORY_COMPUTER: args.keep_computer,
        CATEGORY_CONSOLE: args.keep_console,
    }
    active = [cat for cat in DEFAULT_EXCLUDED_CATEGORIES if not keep_map.get(cat, False)]
    if args.exclude_bios:
        active.append(CATEGORY_BIOS)
    if args.exclude_devices:
        active.append(CATEGORY_DEVICE)
    return active


def _resolve_dest(source: Path, dest: Path | None) -> Path:
    return dest if dest is not None else source / DEFAULT_DEST_SUBDIR


def _resolve_set_type(
    requested: str, source: Path, clone_map: dict[str, str]
) -> str:
    """Return the effective set type, auto-detecting when requested == 'auto'."""
    if requested != SET_TYPE_AUTO:
        return requested
    detected = detect_set_type(source, clone_map)
    logger.info("Auto-detected romset type: %s", detected)
    return detected


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
    clone_map = load_clone_map()
    set_type = _resolve_set_type(args.set_type, source, clone_map)
    logger.info("Active exclusions: %s", ", ".join(active) if active else "(none)")
    logger.info("Set type: %s", set_type)
    logger.info("Source: %s", source)
    logger.info("Mode:   %s", "DELETE" if args.yes else "dry-run")

    exclusion_sets = build_exclusion_sets(source)
    chd_set = exclusion_sets[CATEGORY_CHD]

    start = time.perf_counter()
    zips = find_rom_zips(source)

    # Pass 1: classify every zip into kept vs excluded(category).
    kept: set[str] = set()
    flagged: list[tuple[Path, str]] = []
    for zip_path in zips:
        name = zip_path.stem
        if name in chd_set and not args.include_chd:
            flagged.append((zip_path, CATEGORY_CHD))
            continue
        hit = classify(name, exclusion_sets, set(active))
        if hit is None:
            kept.add(name)
        else:
            flagged.append((zip_path, hit))

    # Split sets: protect parents that kept clones still depend on, so pruning
    # an excluded parent doesn't break a kept clone.
    protected: set[str] = (
        parent_closure(kept, clone_map) if set_type == SET_TYPE_SPLIT else set()
    )

    excluded_counts: dict[str, int] = {}
    deleted = 0
    protected_kept = 0
    for zip_path, hit in flagged:
        if zip_path.stem in protected:
            protected_kept += 1
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
    if protected_kept:
        print(f"Kept {protected_kept} excluded parent(s) needed by split-set clones.")
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
    clone_map = load_clone_map()
    set_type = _resolve_set_type(args.set_type, source, clone_map)
    logger.info("Active exclusions: %s", ", ".join(active) if active else "(none)")
    logger.info("Set type: %s", set_type)
    logger.info("Source: %s", source)
    logger.info("Dest:   %s", dest)

    exclusion_sets = build_exclusion_sets(source)
    chd_set = exclusion_sets[CATEGORY_CHD]

    start = time.perf_counter()
    zips = find_rom_zips(source)
    excluded_counts: dict[str, int] = {}
    copied = 0
    chd_skipped = 0
    kept: set[str] = set()
    name_to_path: dict[str, Path] = {}

    for zip_path in zips:
        # Skip the destination if it lives inside the source folder.
        if dest in zip_path.parents:
            continue

        name = zip_path.stem
        name_to_path[name] = zip_path

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
        kept.add(name)
        copied += 1

    # Split sets: each kept clone needs its parent zip present to run, even if
    # the parent matches an excluded category. Pull those parents in.
    parents_pulled = 0
    if set_type == SET_TYPE_SPLIT:
        for parent in sorted(parent_closure(kept, clone_map)):
            parent_path = name_to_path.get(parent)
            if parent_path is None:
                continue  # parent zip not in source (unexpected for a split set)
            if copy_zip(parent_path, dest):
                parents_pulled += 1

    if chd_skipped:
        excluded_counts[CATEGORY_CHD] = chd_skipped

    elapsed = time.perf_counter() - start
    _print_summary(len(zips), copied, excluded_counts, dest, elapsed)
    if parents_pulled:
        print(f"Pulled {parents_pulled} parent zip(s) for split-set clones.")
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
