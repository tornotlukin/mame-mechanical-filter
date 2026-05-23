# Workshop: MAME ROM Distiller (Python)

**Started:** 2026-05-22
**Status:** In Progress (intent clarified — design revised)

---

## The Idea

A Python CLI tool that produces a **distilled MAME ROM set** by copying every ROM from a source folder to a destination folder **except** those on exclusion lists (mechanical, fruit, gambling, touchscreen, and optionally CHD-requiring games). The end result is a clean "normal arcade games only" set the user can drop into a frontend.

The tool will eventually be compiled to a standalone `.exe`.

**Inversion from earlier design:** earlier rounds assumed the tool would bucket ROMs into per-profile folders (fruit/, mechanical/, etc.). That was wrong. The lists exist to **exclude**, not to **collect**. Output is one flat folder of "the good stuff."

---

## Confirmed Decisions

### Behavior
- **Copy** is the default and only meaningful action — we are duplicating the keep-set into a clean destination folder.
- **Default exclusion lists, all enabled:** mechanical, fruit, gambling, touchscreen.
- **NAOMI / Dreamcast ROMs** excluded by default (they don't run in current MAME). Uses existing `naomi_only.xml`. Opt-out with `--keep-naomi`.
- **`-chd` flag** is an **inclusion** toggle, not an exclusion one. Without `-chd`, CHDs and CHD-requiring games are ignored entirely — the tool only processes standalone .zip ROMs. With `-chd`, each CHD-requiring game is treated as a unit (its .zip **plus** its matching CHD subfolder) and run through the same exclusion logic as everything else: if the game passes, both copy; if it's on an exclusion list, both are skipped.
- **`--source <path>`** to set source ROM folder. Default: current directory.
- **`--dest <path>`** to set destination folder. Default: `<source>/_distilled/` (sibling, or inside source — TBD in next round).
- **Apply by default** — no dry-run-first requirement.
- **No undo manifest** — user can just delete the destination folder and re-run.

### Distribution
- Pure Python CLI, plan to compile to `.exe` later (PyInstaller).

### Data sources
- **catver.ini** from progettoSNAPS via `-dl` flag (downloads latest `pS_CatVer_<ver>.zip` from `https://www.progettosnaps.net/download/?tipo=catver&file=pS_CatVer_<ver>.zip`, unzips into `lists/`).
- **MAME XML data** reused from the existing XML files in this repo, relocated to `lists/`.

### Project folder layout
```
mame-mechanical-filter/
  distill/
    distill.py            # main CLI script
  lists/
    mechanical_only.xml
    touch_only.xml        # to be regenerated strict-touch
    nonrunnable_only.xml
    chd_only.xml
    chdlist.txt
    naomi_only.xml
    naomilist.txt
    catver.ini            # populated by -dl
```

### Exclusion category definitions
- **Mechanical:** MAME XML `ismechanical=yes` (from `mechanical_only.xml`) **OR** catver category starts with `Electromechanical`.
- **Fruit:** catver matches `Casino / Slot Machine` **OR** `Electromechanical / Reels`.
- **Gambling:** TBD — likely catver `Casino / *` (overlaps with fruit, that's fine, the union is what we exclude).
- **Touchscreen:** TBD — likely XML `<control type="...">` matching `touch`/`positional` (the existing `touch_only.xml` already has this list).

---

## Open Questions

_All resolved — see the locked decisions table below._

### Followup notes (not blockers)

- The existing `touch_only.xml` was generated with `touch OR positional` controls. To honor the "touchscreen only" decision (Q16), the tool needs to either:
  - regenerate the touch list with a strict `type=touch` filter, or
  - re-derive at runtime from a current MAME `-listxml`, or
  - ship a script alongside the tool to regenerate `touch_only.xml` strictly.
  Easiest: write a small one-time helper to regenerate `touch_only.xml` strict, then the distiller reads the file. Decide at build time.

---

## Answered & Locked

| # | Question | Decision |
|---|---|---|
| 1 | Mechanical definition | XML `ismechanical=yes` OR catver `Electromechanical / *` |
| 2 | Fruit definition | catver `Casino / Slot Machine` OR `Electromechanical / Reels` |
| 3 | Default action | **Copy** (only action) |
| 4 | Apply vs dry-run default | **Apply by default** |
| 5 | Undo manifest | **No** |
| 6 | Output layout | Single flat destination folder (no per-profile subfolders) |
| 7 | MAME XML source | Reuse `mechanical_only.xml` / `touch_only.xml` in this repo |
| 8 | Source/dest folder args | `--source`, `--dest` |
| 9 | `-chd` flag meaning | **Inclusion** toggle: off = CHD games ignored entirely; on = CHD .zip + .chd subfolder treated as a unit and run through the normal exclusion filters |
| 10 | `-dl` flag | Download latest `pS_CatVer_<ver>.zip` from progettoSNAPS, unzip into `support/` |
| 11 | CLI flag style | **Per-category opt-out** — default all four excluded, `--keep-mechanical`, `--keep-fruit`, `--keep-gambling`, `--keep-touch` to disable individually |
| 12 | Extra default exclusions | **Nonrunnable machines** added (uses existing `nonrunnable_only.xml`). Mature and clones **not** excluded by default. |
| 13 | Unknown ROMs (no catver entry) | **Keep** — only exclude when an explicit list flags them |
| 14 | Default dest folder | `<source>/_distilled/` (inside source folder). Override with `--dest`. |
| 15 | Gambling definition | All `Casino / *` (overlaps with fruit, which is fine — union is excluded) |
| 16 | Touch definition | **Touchscreen only** — `control type=touch`. Positional games are **not** excluded. Lightgun is **not** excluded. |
| 17 | CHD-required list source | **Union** of repo `chdlist.txt` / `chd_only.xml` **and** filesystem auto-detection (any source subfolder containing a `.chd` is treated as CHD-requiring) |
| 18 | Console output | Summary counts only at end of run. No per-file noise. |
| 19 | NAOMI/Dreamcast exclusion | **Default on** (don't run in current MAME). Uses `naomi_only.xml`. Opt-out: `--keep-naomi`. |
| 20 | Project folder layout | `distill/` holds the Python script; `lists/` holds all XML / ini / txt data files (including downloaded `catver.ini`). |

---

## Conversation Log

> **User:** ok check the internet about creating game filters or if a filter just gets created by a 3rd party every mame version.

> **Claude:** Confirmed: progettoSNAPS (AntoPISA) maintains catver/genre/series per MAME version; nplayers.ini maintained separately at arcadebelgium.be.

> **User:** so can we create a python tool to organize a folder of roms based on these filters? especially mechanical/fruit games?

> **Claude:** Proposed sorter tool. Asked clarifying questions.

> **User:** Reorganize ROMs by filter; -dl downloads ini; -chd for CHDs.

> **Claude:** Surfaced design tradeoffs (action, layout, CHD destination, mechanical def, etc.).

> **User:** Use progettoSNAPS zip (option B) for downloads.

> **Claude:** Verified URL pattern (`pS_CatVer_287.zip` current).

> **User:** Let's workshop this before coding.

> **Claude:** Created workshop file, ran two rounds of structured questions.

> **User (Round 1):** Mechanical = XML OR catver electromechanical. Fruit = Casino/Slot + Electromechanical/Reels. Default action = copy. CHD = separate chd/ subfolder.

> **User (Round 2):** Flat per-profile output. Named profiles + raw catver. Reuse mechanical_only.xml. Hardlink/copy into each profile on multi-match.

> **User (Round 3, partial):** Apply by default. No undo. Then clarification.

> **User (clarification):** "The point of copying files is to **exclude** the ROMs on the lists and copy the rest to a new place so the user gets a distilled ROM set without mechanical, fruit, gambling, touchscreen games. Default behavior is to include all lists. Add an arg to include CHDs and their ROMs to the list."

> **Claude:** Understood — distillation, not sorting. Revising workshop file to reflect that the lists drive exclusion and the output is one clean destination folder.

---

## Key Insights

- Tool is a **distiller**, not a sorter. Source → Destination, excluding all flagged categories. Single output folder, no per-profile buckets.
- Default-on exclusions: mechanical, fruit, gambling, touchscreen. `-chd` adds CHD-requiring to that list.
- "Fruit" and "Gambling" likely overlap in catver — the union is fine since we're excluding either way.
- Several earlier answers (output layout per-profile, CHD subfolder layout, multi-match behavior) are obsolete under the corrected intent.
- Reusing existing `mechanical_only.xml` / `touch_only.xml` keeps the tool dependency-free at runtime (no `mame.exe` call).
- Will compile to `.exe` later via PyInstaller — no exotic Python features that PyInstaller can't bundle.

---

## Next Steps

1. Answer the 8 revised open questions (granularity of flags, gambling scope, touch scope, unknown-ROM behavior, other exclusions, default dest path, CHD source data, logging output).
2. Lock final CLI surface and write usage examples.
3. Sketch project layout (`rom_distiller.py`, `support/`, etc.).
4. Build, test on a sample folder, then plan PyInstaller bundling.

---

## Resources & Links

- progettoSNAPS catver: https://www.progettosnaps.net/catver/
- Download URL: `https://www.progettosnaps.net/download/?tipo=catver&file=pS_CatVer_<ver>.zip`
- nplayers (if needed later): https://nplayers.arcadebelgium.be/files/nplayers.txt
- Existing repo files: `mechanical_only.xml`, `touch_only.xml`, `nonrunnable_only.xml`, `chdlist.txt`, `chd_only.xml`, `naomi_only.xml`, `del_mech_xml.js`, `del_mech_files.ps1`
- PyInstaller (for later .exe build): https://pyinstaller.org/
