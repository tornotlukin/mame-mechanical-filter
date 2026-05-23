# Workshop: RetroArch MAME Metadata Maker

**Started:** 2026-05-23
**Status:** Design finalized + .lpl schema verified against RetroArch source — ready to implement

---

## The Idea

Build a script that takes a folder of MAME ROM zips + a MAME `-listxml` dump, and emits a RetroArch `.lpl` playlist with the **proper game titles already baked into the `label` field**. This sidesteps RetroArch's broken CRC32 lookup for MAME 0.280+ ROMs, which currently falls back to showing raw zip filenames because the bundled `MAME.rdb` is out of date.

User points at a ROM folder → tool reads each zip's stem → looks it up in the MAME XML → writes a complete playlist where every entry already has the correct label. RetroArch consumes the playlist as-is, no scanning, no DB lookups.

---

## Open Questions

- [ ] **Exact Android path on the Retroid 3+ where the MAME ROMs will be copied.** Need this for the `path` field of each playlist item. Common candidates:
  - `/storage/emulated/0/RetroArch/roms/mame/` (sideload builds)
  - `/storage/emulated/0/Android/data/com.retroarch.aarch64/files/downloads/MAME/`
  - SD card path like `/storage/XXXX-XXXX/RetroArch/roms/mame/`
- [ ] **Where on PC does the .lpl get written?** Project root, `/clean/`, or a dedicated `/retroarch-out/`?
- [ ] **MAME XML caching:** regenerate every run (slow, ~30s+) or cache `mamegames.xml` in project root and reuse with a `--refresh-xml` flag?
- [ ] Should we also generate a stub `MAME.lpl` for the `/clean` distilled set only, or include all ROMs found in whatever folder the user points at?
- [ ] CHD games: the playlist points to `.zip` regardless; the `.chd` subfolder needs to live alongside the `.zip` on the device for the core to find it. The tool should warn if `--chd` mode is on but no CHD payload was copied. (Out of scope for v1?)

---

## Answers & Decisions

### Confirmed from research (docs/learned_retroarch-playlist-format.md)

- **Format:** JSON; same on all platforms including Android.
- **Display name source:** the `label` field of each playlist item is the authoritative display name. RetroArch will use it directly if we pre-populate it; no DAT lookup needed.
- **Why post-0.280 is broken:** RetroArch's bundled `MAME.rdb` is a snapshot of an older MAME -listxml. CRC32 lookup misses any ROM added since the snapshot, so the label falls back to the filename.
- **Android playlist path:** depends on which build (Play Store vs. sideload vs. aarch64). Authoritative path is shown in-app at Settings → Directory → Playlists. Tool should accept the path as a parameter or write to a configurable output dir.
- **`db_name` should be `"MAME.lpl"`** so existing thumbnail packs at `thumbnails/MAME/Named_Boxarts/...` match.
- **`crc32` field** can be `"00000000|crc"` for manually-built playlists; the `|crc` suffix is required.
- **`label_display_mode`** should be `0` (show label as-is). Don't use mode 4/5 to strip parens — many MAME titles have meaningful region info in parens that we want visible.

### User-stated requirements

- Script accepts a folder of ROMs as input.
- Reads MAME XML to translate zip stem → real game name.
- Outputs the file RetroArch needs.
- Must work for Android RetroArch installs (path question above).

### Decisions (round 2, 2026-05-23)

- **MAME source:** `H:\mame\mame.exe`. Tool will run `mame.exe -listxml` to produce the XML (or accept a pre-built file). Confirmed `H:\mame\mame.exe` exists.
- **Workflow:** PC builds the `.lpl` → user copies to Retroid 3+ (Android). So `path` field must be the **Android device path**, not the PC path. PC path is only used to enumerate which ROMs exist; it's not written into the playlist.
- **Output filename:** `MAME.lpl` (matches existing thumbnail pack convention at `thumbnails/MAME/`).
- **Single playlist:** one `MAME.lpl` for everything; no splitting by category.
- **Core binding:** use `"DETECT"` for both `core_path` and `core_name`. The user's tentative `"mame"` isn't a valid core_path — that field needs the full filesystem path to the `.so` on Android, which varies by build. `DETECT` lets RetroArch pick at runtime, which is the most portable choice.
- **PC output path for the .lpl:** CLI arg `--output` / `-o`. Default: same folder as the script.
- **Android device path (the `path` field in each playlist entry):** CLI arg `--device-prefix`. Default: use the actual PC path of each ROM (useful for local testing on a desktop RetroArch install).
- **MAME XML:** user supplies a pre-built `mamegames.xml` via `--xml`. The tool will *not* shell out to `mame.exe -listxml`; that's the user's job. (User can run `H:\mame\mame.exe -listxml > mamegames.xml` separately.)

---

## Conversation Log

> **User:** we may need to make another tool for retroarch. lets workshop it, call it workshop-retroarch-mame-metadata-maker.md

> **Claude:** Asked initial scoping questions (output type, sources, scope, output location).

> **User:** the idea for this tool is to:
> - make whatever retroarch needs so that when the rom files are found they show the proper names
> - since v280 of mame retroarch hasnt been able to "detect" the names of the mame roms
> - look up the retroarch docs, use the skill
>   - what is the format of the name lists?
>   - where should it be placed on Android RetroArch?
> - the script should use the mame xml created by the mame app to get the real names
> - user points to a folder; script uses ROMs in that folder to fill out the file RetroArch needs

> **Claude:** Researched via dev_docs / WebFetch. Confirmed the .lpl JSON format and the MAME 0.280 RDB-snapshot issue. Wrote docs/learned_retroarch-playlist-format.md and this workshop file.

---

## Key Insights

1. **There is no separate "name list" file** in RetroArch — names live inside the playlist (`.lpl`) itself. So this tool's output IS the playlist, not a sidecar.
2. **We can bypass scanning entirely.** A hand-built `.lpl` with correct labels is treated identically to a scanned one. This is the cleanest fix for the post-0.280 issue.
3. **Two paths matter, and they're different:** the PC path where the script runs (`X:\Arcade\...` or `H:\_DEV\...\clean`) and the device path where the ROMs will live (`/storage/emulated/0/...`). The script needs both — or a `--device-path-prefix` option — so the playlist works on the target device.
4. **The script is small and Python-flavored** — fits naturally next to `distill/`. Probably becomes `metadata/` or `playlist/` sibling to `distill/`, sharing nothing but project conventions.
5. **History.dat / mameinfo.dat are out of scope for v1.** They'd be useful for richer per-game info, but RetroArch's playlist format has no fields for them; they'd require a separate metadata sidecar system that RetroArch doesn't natively consume.
6. **Schema verified from `playlist.c::playlist_write_file()` in libretro/RetroArch master** (2026-05-23). Key additions to my initial guess: `thumbnail_match_mode` field (I had missed it); `base_content_directory` and the entire scan-record block are *conditional* and should be omitted for hand-built playlists. Subsystem fields are conditional and not relevant to MAME. See `docs/learned_retroarch-playlist-format.md`.

---

## Next Steps

**Ready to implement.** Final CLI signature:

```
python playlist/build.py \
  --source H:\_DEV\mame-mechanical-filter\clean \
  --xml mamegames.xml \
  [--device-prefix "/storage/emulated/0/RetroArch/roms/mame"] \
  [--output MAME.lpl]
```

- `--source` (required): folder of ROM zips to enumerate.
- `--xml` (required): path to MAME `-listxml` output. User generates this with `H:\mame\mame.exe -listxml > mamegames.xml`.
- `--device-prefix` (optional): path prefix used in the playlist's `path` field. Defaults to each ROM's real PC path. Set this to the Retroid 3+ ROM directory when building for the device.
- `--output` (optional): where to write the .lpl. Defaults to `<script dir>/MAME.lpl`.

**Implementation plan:**
1. Stream-parse `mamegames.xml` with `xml.etree.iterparse` — never load all 200+ MB at once. Build a `{rom_name: description}` dict, but only for ROMs present in `--source`.
2. Enumerate `*.zip` files in `--source`.
3. For each ROM, build a playlist item:
   - `path`: `<device-prefix>/<zip name>` if prefix set, else the actual PC path.
   - `label`: XML `<description>` for that ROM; fall back to the zip stem if not found (log a warning).
   - `core_path`: `"DETECT"`
   - `core_name`: `"DETECT"`
   - `crc32`: `"00000000|crc"`
   - `db_name`: `"MAME.lpl"`
4. Write the top-level JSON envelope with `version: "1.5"`, `label_display_mode: 0`, sensible defaults for the rest.
5. Add tests covering: missing XML entry (fallback), XML present (label populated), device-prefix path joining, output path default.

---

## Resources & Links

- `docs/learned_retroarch-playlist-format.md` — distilled crib sheet on .lpl format and Android paths.
- `lists/catver.ini` — already downloaded, available if we want per-game category metadata.
- `mamegames.xml` — gitignored MAME -listxml output; presence on user's machine TBC.
- Official docs: https://docs.libretro.com/guides/roms-playlists-thumbnails/
- libretro-database (where MAME.rdb lives): https://github.com/libretro/libretro-database
