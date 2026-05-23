# RetroArch Playlist (.lpl) Format & MAME Naming
> Sources: docs.libretro.com (guides/roms-playlists-thumbnails, library/mame2003_plus, import-content, libretro.com 1.12.0 release notes); RetroArch source `playlist.c::playlist_write_file()` on master (libretro/RetroArch)
> Created: 2026-05-23 (top-level schema verified against source 2026-05-23)

## File format

`.lpl` files are **JSON**, stored in RetroArch's `playlists/` directory. Same format across all platforms (Windows / Linux / Android).

## Top-level schema (verified against `playlist.c::playlist_write_file()`)

Field write order (RetroArch is consistent here, and although JSON is order-agnostic, matching is safest):

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
  "items": [ /* one entry per ROM */ ]
}
```

**Conditional top-level fields** (only emitted when relevant — omit unless you need them):
- `base_content_directory` — only if non-empty.
- Scan-record block — only written if RetroArch built the playlist via auto-scan and recorded the scan parameters. For a hand-built playlist, *omit the entire block*. Fields in this block: `scan_content_dir`, `scan_file_exts`, `scan_dat_file_path`, `scan_database_name`, `scan_search_recursively`, `scan_search_archives`, `scan_filter_dat_content`, `scan_omit_db_ref`, `scan_overwrite_playlist`, `scan_db_usage`.

## Item schema (per ROM, verified against source)

Field write order:

```json
{
  "path": "/storage/emulated/0/RetroArch/roms/mame/sf2.zip",
  "label": "Street Fighter II: The World Warrior (World 910522)",
  "core_path": "DETECT",
  "core_name": "DETECT",
  "crc32": "00000000|crc",
  "db_name": "MAME.lpl"
}
```

**Conditional item fields** (omit unless needed):
- `entry_slot` — for save-state slot binding.
- `subsystem_ident`, `subsystem_name`, `subsystem_roms` (array) — only for cores that load via subsystem (e.g. SuperGrafx, Mega-CD). Not applicable to MAME.

- `path` — absolute path to the ROM (zip).
- `label` — **what's displayed in the UI**. If we put the proper title here, RetroArch shows it. No DAT lookup needed.
- `core_path` / `core_name` — `"DETECT"` lets RetroArch pick at runtime. Use the actual core path for explicit binding (e.g. `/data/data/com.retroarch/cores/mame_libretro_android.so`).
- `crc32` — `"00000000|crc"` is acceptable for manual playlists; the suffix `|crc` is required even if the value is zeros.
- `db_name` — should be `"MAME.lpl"` for the MAME database. RetroArch uses this to match thumbnails (`thumbnails/MAME/Named_Boxarts/<label>.png`, etc.).

## How RetroArch names games (and why it breaks post-MAME 0.280)

1. **Scan-time path:** RetroArch scans a ROM → computes CRC32 → looks up in bundled `libretro-database` (`MAME.rdb`) → if match, uses the DB's name as `label`.
2. **The bundled `MAME.rdb` is generated from a snapshot of MAME's -listxml.** When MAME ships new ROMs in 0.280+, the bundled DB doesn't include them, so the CRC lookup fails and RetroArch falls back to the raw filename as the label.
3. **Workaround for this tool:** Skip the scan + RDB entirely. Generate the `.lpl` directly with the `label` already correct from MAME's own `-listxml` output.

## `label_display_mode` values (purely cosmetic post-processing of the label)

| Value | Effect |
|---|---|
| 0 | Show label as-is (default) |
| 1 | Strip region tags `(USA)`, `(Europe)`, etc. |
| 2 | Strip disc index `(Disc 1)` |
| 3 | Strip region + disc |
| 4 | Strip everything in `(parens)` |
| 5 | Strip everything in `[brackets]` |
| 6 | Strip parens + brackets |
| 7 | Show only `(parens)` content |
| 8 | Show only `[brackets]` content |

For MAME, set `label_display_mode = 0` and put the clean title directly in `label`. Don't fight it with display-mode stripping.

## Playlist directory on Android

Path depends on RetroArch build:

| Build | Playlists path |
|---|---|
| Play Store (`com.retroarch`) | `/storage/emulated/0/Android/data/com.retroarch/files/playlists/` |
| Play Store 64-bit (`com.retroarch.aarch64`) | `/storage/emulated/0/Android/data/com.retroarch.aarch64/files/playlists/` |
| GitHub/sideloaded "RetroArch Plus" or older builds | `/storage/emulated/0/RetroArch/playlists/` (the app uses external storage root) |

**Authoritative way to find it:** in RetroArch → Settings → Directory → Playlists. The tool should let the user paste this path.

## Thumbnails (downstream of this tool, but related)

If `label` is set correctly, RetroArch looks for thumbnails at:
```
thumbnails/<db_name without .lpl>/Named_Boxarts/<label>.png
thumbnails/<db_name>/Named_Snaps/<label>.png
thumbnails/<db_name>/Named_Titles/<label>.png
```
i.e. `thumbnails/MAME/Named_Boxarts/Street Fighter II.png`. Filenames must match `label` exactly (with characters like `&` `/` `:` replaced per RetroArch's escaping rules — `&` → `_`, `:` → `_`, etc.).

## See Also
- TOC for libretro-database `.rdb` format (not yet created) — only needed if we want to generate a custom MAME.rdb instead of a pre-baked .lpl
