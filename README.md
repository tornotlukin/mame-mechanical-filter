# mame-mechanical-filter

Two small Python CLI tools for curating a MAME romset and exposing it to RetroArch with proper game titles. Pure stdlib, no third-party dependencies.

## Why this exists

A full MAME romset is enormous and full of machines you'll never play — mechanical fruit machines, gambling cabinets, ROMs flagged unrunnable, NAOMI/Dreamcast units that need their own core, touchscreen-only games, and so on. RetroArch makes it worse: since MAME 0.280, its bundled CRC32 database (`MAME.rdb`) doesn't recognise newer ROMs, so scanning the romset shows raw filenames like `sf2.zip` instead of `Street Fighter II`.

This repo solves both problems with two pipeline stages:

1. **`distill/`** — filter a MAME romset, copying only what you actually want to a clean folder.
2. **`lpl-builder/`** — build a RetroArch playlist for that folder with proper game titles in the `label` field, bypassing the broken scan entirely.

---

## Tool 1: `distill`

Walks a folder of MAME ROM zips and copies a filtered subset to a destination, dropping anything that matches the exclusion categories.

### What it filters by default

| Category | Source | Why excluded |
|---|---|---|
| `mechanical` | `lists/mechanical_only.xml` + catver `Electromechanical` | Physical reel/coin machines that don't play meaningfully in software emulation. |
| `fruit` | catver `Casino / Slot Machine` and `Electromechanical / Reels` | Slot machines. |
| `gambling` | catver `Casino/*` | Casino card/table games. |
| `touch` | `lists/touch_only.xml` | Touchscreen-only games, unusable without a touchscreen. |
| `nonrunnable` | `lists/nonrunnable_only.xml` | Machines MAME flags `runnable="no"`. |
| `naomi` | `lists/naomi_only.xml` | NAOMI / Dreamcast ROMs — these belong to a different core. |
| `computer` | catver `Computer / *` and `Computer Graphic Workstation` | Home computers (Apple II, C64, Atari ST, etc.) — not arcade games. |
| `console` | catver `Game Console / *` and `Game Console/Computer` | Home consoles (NES, SNES, Genesis, etc.) — belong in their own emulator. |
| `chd` | `lists/chd_only.xml` + filesystem scan | CHD-requiring games. Skipped unless `-chd` is passed (then the `.zip` and its sibling `.chd` folder are treated as a unit). |

### BIOS preservation

ROMs flagged `isbios="yes"` in MAME's XML (e.g. `neogeo.zip`, `decocass.zip`, `naomi.zip`, `pgm.zip`) are **always copied** even when they also match another exclusion category. This prevents the `nonrunnable` filter from accidentally dropping a BIOS that arcade games depend on. The BIOS list lives in `lists/bios_only.xml`; regenerate it with `python distill/build_lists.py --xml lpl-builder/mamegames.xml` after MAME updates. Pass `--exclude-bios` to opt out of preservation.

### Usage

```
python distill/distill.py --source X:\Arcade\roms\MAME287_ROMS --dest ./clean
```

### Flags

| Flag | Effect |
|---|---|
| `--source PATH` | Source ROM folder. Default: current directory. |
| `--dest PATH` | Destination folder. Default: `<source>/_distilled/`. |
| `-chd`, `--chd` | Include CHD-requiring games. Each game's `.zip` plus its matching `.chd` subfolder is copied together. |
| `-dl`, `--download` | Download the latest `catver.ini` from progettoSNAPS and exit. Run this once before your first distill so genre matching works. |
| `--keep-mechanical` | Don't exclude mechanical games. |
| `--keep-fruit` | Don't exclude fruit / slot games. |
| `--keep-gambling` | Don't exclude `Casino/*` games. |
| `--keep-touch` | Don't exclude touchscreen games. |
| `--keep-nonrunnable` | Don't exclude `runnable=no` machines. |
| `--keep-naomi` | Don't exclude NAOMI / Dreamcast ROMs. |
| `--keep-computer` | Don't exclude home computer ROMs. |
| `--keep-console` | Don't exclude home console ROMs. |
| `--exclude-bios` | Drop the BIOS-preservation override; BIOSes can then be filtered by any active category. |
| `--prune` | Destructive mode: walk `--source` and DELETE files that match active exclusions, instead of copying. Use after the filter rules change to clean a previously-distilled folder. Defaults to dry-run; pair with `--yes` to actually delete. `--dest` is rejected in this mode. |
| `--yes` | Confirm destructive prune deletions. Required alongside `--prune`. |
| `-v`, `--verbose` | Debug logging. |

### Behaviour notes

- **Source is never modified.** Files are copied with `shutil` (or `robocopy` on Windows when the network share misbehaves). The original folder is read-only as far as the script is concerned.
- **Resumable.** If a destination file already exists with the same size, it's skipped — so re-running after a crash or interruption picks up where it left off without re-reading hundreds of GB.
- **SMB-tolerant.** Reads use a chunked loop instead of `shutil.copy2`'s `readinto` path (which throws `OSError 22` on some shares). When even that fails, the copy falls back to Windows `robocopy`. If both fail for a specific file it's logged in the final summary and the run continues instead of aborting.

### Pruning an existing distilled folder

When filter rules change (e.g. you add `computer`/`console` exclusions after an earlier distill), `/clean` won't auto-update — distill only copies, it doesn't delete. Use `--prune` to clean it up in place:

```
python distill/distill.py --source ./clean --prune          # dry-run, shows counts
python distill/distill.py --source ./clean --prune --yes    # actually delete
```

Source folders at the real ROM location (e.g. `X:\Arcade\roms\...`) are never touched by anything else — `--prune` only deletes from whatever you pass as `--source`.

### Layout

```
distill/
  distill.py       # CLI entry
  config.py        # constants
  loaders.py       # parse lists/*.xml and *.txt
  catver.py        # parse catver.ini
  exclusions.py    # build per-category exclusion sets, classify a ROM
  copier.py        # enumerate ROMs, copy zips + CHD subfolders
  downloader.py    # fetch latest catver.ini from progettoSNAPS
  build_lists.py   # regenerate lists/bios_only.xml from mamegames.xml
```

---

## Tool 2: `lpl-builder`

Builds a RetroArch `MAME.lpl` playlist directly from a folder of ROMs plus MAME's `-listxml` output. Each playlist item gets the proper game title pre-populated in its `label` field, so RetroArch shows real names without doing any CRC matching.

### Why a hand-built playlist?

RetroArch's normal flow is: scan a ROM, hash it, look up the hash in `MAME.rdb` (a bundled snapshot of an older MAME `-listxml`), and use the database's name as the label. Post-MAME 0.280 the bundled database lags behind, so any newer ROM scans as the raw filename. Since `label` is just a regular JSON field, the simplest fix is to skip the scan entirely and write the playlist with correct labels from the start.

The schema, including the top-level envelope and item field order, was verified against `playlist_write_file()` in `libretro/RetroArch` master — see `docs/learned_retroarch-playlist-format.md` for the full crib sheet.

### Prerequisite: generate the MAME XML

```
H:\mame\mame.exe -listxml > lpl-builder\mamegames.xml
```

The XML is large (~300 MB) and gitignored. The script streams it with `xml.etree.iterparse` so memory stays flat.

### Usage

```
python lpl-builder/build.py --source ./clean ^
    --device-prefix "/storage/emulated/0/RetroArch/roms/mame"
```

### Flags

| Flag | Effect |
|---|---|
| `--source PATH` | Folder of ROM `.zip` files to enumerate. Required. |
| `--xml PATH` | Path to MAME `-listxml` output. Default: `lpl-builder/mamegames.xml`. |
| `--device-prefix STR` | Path prefix written into each item's `path` field, joined with forward slashes. Use the Android (or other target) ROM path. When unset, the actual PC path of each ROM is used — handy for testing on desktop RetroArch. |
| `--output PATH`, `-o` | Where to write the `.lpl`. Default: `lpl-builder/MAME.lpl`. |
| `-v`, `--verbose` | Debug logging. |

### Output

A single `MAME.lpl` JSON file. Top-level shape:

```json
{
  "version": "1.5",
  "default_core_path": "",
  "default_core_name": "",
  "label_display_mode": 0,
  "right_thumbnail_mode": 0,
  "left_thumbnail_mode": 0,
  "thumbnail_match_mode": 0,
  "sort_mode": 0,
  "items": [
    {
      "path": "/storage/emulated/0/RetroArch/roms/mame/10yard.zip",
      "label": "10-Yard Fight (World, set 1)",
      "core_path": "DETECT",
      "core_name": "DETECT",
      "crc32": "00000000|crc",
      "db_name": "MAME.lpl"
    }
  ]
}
```

`core_path` / `core_name` are `"DETECT"` so RetroArch picks the active MAME core at runtime — portable across Play Store, sideload, and aarch64 builds. `db_name` is `"MAME.lpl"` so existing thumbnail packs at `thumbnails/MAME/Named_Boxarts/...` match without extra work.

The top-level `default_core_path` and `default_core_name` are emitted as empty strings. If you'd rather hard-bind every entry to a specific core instead of relying on `DETECT`, fill them in by hand after the tool runs:

- **`default_core_path`** — the full filesystem path to the core's `.so` on the target device. There is no portable answer: Android handhelds (Retroid, Anbernic, phones) usually hide the OS root filesystem from the file picker, so you may have to dig in RetroArch's own UI to discover the actual install path. In RetroArch on the device: Settings → Directory → Cores will show you the directory; the `.so` filename you want is whatever shows up under Online Updater → Core Downloader → MAME. Common shapes look like `/data/data/com.retroarch.aarch64/cores/mame_libretro_android.so`, but the exact path depends on which RetroArch build (Play Store / aarch64 / sideload) is installed and may not be reachable through the system file manager.
- **`default_core_name`** — the human-readable core label. For recent MAME builds this is typically `"Arcade (MAME/Arcade)"`. Older or alternate cores use different strings (e.g. `"Arcade (MAME 2003-Plus)"`); check Settings → Core in RetroArch to read off the exact name.

### Layout

```
lpl-builder/
  build.py         # CLI entry
  config.py        # constants
  xml_reader.py    # stream-parse mamegames.xml
  writer.py        # build playlist dict, JSON write
  mamegames.xml    # generated by `mame -listxml`, gitignored
```

### Gotcha: Git Bash on Windows mangles the device prefix

If you pass `--device-prefix "/storage/emulated/0/..."` from Git Bash on Windows, MSYS path translation rewrites the leading `/` to `C:/Program Files/Git/storage/...`. Run from PowerShell or `cmd.exe`, or set `MSYS_NO_PATHCONV=1` if you must use Git Bash.

---

## Typical end-to-end workflow

1. Download the latest catver once: `python distill/distill.py -dl`
2. Generate MAME's XML once: `H:\mame\mame.exe -listxml > lpl-builder\mamegames.xml`
3. Regenerate the BIOS list once: `python distill/build_lists.py --xml lpl-builder/mamegames.xml`
4. Distill the romset: `python distill/distill.py --source X:\Arcade\roms\MAME287_ROMS --dest ./clean`
5. Build the playlist: `python lpl-builder/build.py --source ./clean --device-prefix "/storage/emulated/0/RetroArch/roms/mame"`
6. Copy `./clean/` to the device's MAME ROM folder; copy `lpl-builder/MAME.lpl` to the device's `playlists/` folder.

Re-run any stage in isolation when the inputs change — they're independent. If filter rules change after an initial distill, prune the existing output: `python distill/distill.py --source ./clean --prune --yes`.

---

## Project rules

See `docs/CODE-RULES.md` and `docs/OVERRIDES.md`. Short version: Python 3.10+, stdlib only, `argparse`, `logging` over `print`, type-annotated, snake_case, flat package layout (no `src/`), constants in `config.py`.
