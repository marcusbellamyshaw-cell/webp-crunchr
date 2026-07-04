# Windows Explorer right-click "Compress to WebP"

## Purpose

Let user select one or more image files in Windows Explorer, right-click, and
convert them to WebP in place (same directory), without opening the app's GUI.

## Scope

- New right-click context menu entry, per-user install (HKCU, no admin/UAC).
- New headless CLI mode in the existing app for the entry to invoke.
- New Settings button to install/uninstall the context menu entry.
- Out of scope: COM shell extension (single-process batch handling), deleting
  originals, configurable quality/encoder for the auto-compress action,
  toast notifications.

## Design

### 1. Headless CLI mode (`main.py`)

Before constructing `QApplication`, check `sys.argv` for
`--auto-compress <path> [<path> ...]`. If present:

- For each path, call:
  `core.converter.convert(src, output_path(src, None), quality=75, encoder=ENCODER_BEST, lossless=False, skip_if_larger=True)`
- Wrap each file's conversion in try/except; on failure append a line to
  `%LOCALAPPDATA%\WebPCrunchr\errors.log` (path, error). Never raise, never
  show a dialog.
- Exit 0 after processing all paths in argv. Normal (no-flag) launch is
  unchanged.
- This path must not import/construct anything Qt-related before the flag
  check, so a right-click on one file doesn't pay for a full Qt init.

### 2. Registry integration (`core/shell_integration.py`, new file)

Constants: `SUPPORTED_EXTENSIONS - {".webp"}` (from `core/file_utils.py`) is
the set of extensions to register.

- `_command_line() -> str`: if `hasattr(sys, "_MEIPASS")` (frozen), use
  `f'"{sys.executable}" --auto-compress'`; else use
  `f'"{pythonw_path}" "{abspath to main.py}" --auto-compress'` where
  `pythonw_path` is `sys.executable` with `python.exe` swapped for
  `pythonw.exe` (falls back to `sys.executable` if `pythonw.exe` isn't found
  next to it).
- `install_context_menu() -> None`: for each extension, create
  `HKEY_CURRENT_USER\Software\Classes\SystemFileAssociations\<ext>\shell\WebPCrunchr`
  with default value "Compress to WebP", and
  `...\WebPCrunchr\command` default value `f'{_command_line()} "%1"'`.
- `uninstall_context_menu() -> None`: delete the `WebPCrunchr` key (and
  children) under each extension's `shell` key.
- `is_installed() -> bool`: True if the key exists for at least one
  registered extension.
- All operations use `winreg`, HKCU only — no elevation required.

### 3. Settings button (`ui/main_window.py`)

- One button, near the existing "Open folder" / attribution row.
- Label reflects current state via `shell_integration.is_installed()`:
  "Add to right-click menu" / "Remove from right-click menu".
- On click: call install/uninstall, refresh label, show a `QMessageBox` on
  success or on exception. This is a GUI-triggered action so a dialog is
  appropriate here (unlike the silent headless path in part 1).

## Data flow

```
Explorer right-click (1+ files, e.g. .jpg)
  -> Windows spawns one process per selected file:
     "<exe or pythonw+main.py>" --auto-compress "<file>"
  -> main.py detects --auto-compress before QApplication
  -> core.converter.convert(..., quality=75, encoder=Best, skip_if_larger=True)
  -> <file>.webp written next to <file>; original untouched
  -> process exits silently (errors go to errors.log only)
```

## Error handling

- Per-file try/except in headless mode; one bad file doesn't stop the rest
  (irrelevant here since each file is its own process, but keeps the log
  correct if convert() itself has an internal multi-step failure).
- Registry writes in `shell_integration.py` let `winreg` exceptions propagate
  to the caller (the Settings button), which shows them in a `QMessageBox`.

## Testing

- `test_shell_integration.py` (assert-based, no framework, mirrors the rest
  of the repo which has no test suite): install -> `is_installed()` is True
  -> uninstall -> `is_installed()` is False. Runs against the real HKCU hive
  (per-user, self-cleaning, safe).
- Headless conversion reuses `core/converter.py` as-is; no new conversion
  logic to test.
- Manual check: build/run from source, click "Add to right-click menu",
  right-click a .jpg in Explorer, confirm `.webp` appears alongside it.
