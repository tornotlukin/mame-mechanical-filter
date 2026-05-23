# Code Rules — mame-mechanical-filter

Active language: **Python 3.10+**. Project is a single-purpose CLI tool that will be bundled to a standalone `.exe` via PyInstaller.

## Hard constraints

- **Pure-Python only.** No third-party dependencies. Stdlib only. PyInstaller bundles must remain small and have no native extensions.
- **Target Python 3.10+** for `from __future__ import annotations` and `list[str]` / `dict[str, int]` built-in generics.
- **No `print()` for operational output.** Use stdlib `logging` with `logger = logging.getLogger(__name__)`.
- **Type-annotate all public functions and methods** (parameters + return).
- **No wildcard imports.**
- **No buried magic values.** Paths, URLs, category names, list filenames all live in `config.py`.
- **snake_case** functions/vars, **PascalCase** classes, **UPPER_SNAKE** constants.
- **Imports grouped:** stdlib, then local — separated by blank lines.
- **Double quotes** for strings.

## Toolchain

- `pip + venv` only. No poetry, pipenv, conda.
- `.venv/` lives in project root, must be in `.gitignore`.
- `ruff` for lint/format (when added later).

## CLI

- Use `argparse` (stdlib). See `docs/OVERRIDES.md` for why click is not used here.
