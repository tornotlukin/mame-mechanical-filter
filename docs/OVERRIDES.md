# Project Overrides — mame-mechanical-filter

Deviations from the global `code-production` skill defaults. Only differences are noted; everything else inherits from the skill's `SKILL.md`.

## Folder layout

**Standard:** `src/package_name/` with `__main__.py`, `tests/`, etc.

**This project:** flat `distill/` package next to `lists/` (XML/ini/txt data) and `docs/`. No `src/` layer.

```
mame-mechanical-filter/
  distill/                # Python code
    distill.py            # CLI entry: python distill/distill.py ...
    config.py
    loaders.py
    catver.py
    downloader.py
    copier.py
  lists/                  # XML / ini / txt data consumed at runtime
  docs/                   # CODE-RULES.md, OVERRIDES.md
  workshop-rom-organizer.md
```

Justification: explicit user requirement captured in `workshop-rom-organizer.md` (decision Q20). The tool is a single-purpose CLI, not an installable package — `src/` layout adds nothing here.

## CLI library

**Standard:** `click` + `__main__.py`.

**This project:** `argparse` (stdlib).

Justification: tool will be bundled to a standalone `.exe` via PyInstaller. Stdlib-only dependency footprint keeps the bundled binary smaller and avoids any third-party install step. `argparse` is sufficient for the flat flag surface this tool needs.

## Entry point

**Standard:** `python -m package_name` via `__main__.py`.

**This project:** `python distill/distill.py` directly. Reflects the script-not-package nature.

## Config

**Standard:** env vars + `python-dotenv` in `config.py`.

**This project:** `config.py` holds constants (paths, category definitions, URLs). No env vars, no `.env` file — this is a local CLI tool with no secrets or per-environment toggles.
