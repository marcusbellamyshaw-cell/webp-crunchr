# Explorer Right-Click "Compress to WebP" Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Let a user right-click one or more images in Windows Explorer and get a WebP copy saved next to the original, with no GUI involved.

**Architecture:** A headless CLI mode (`--auto-compress`) added to `main.py` reuses the existing `core/converter.py` conversion logic. A new `core/shell_integration.py` module writes/removes per-user (HKCU) registry keys that make Explorer's context menu invoke that CLI mode. A button in `ui/main_window.py`'s Settings area installs/uninstalls those registry keys.

**Tech Stack:** Python 3, PyQt6, `winreg` (stdlib, Windows-only), Pillow, cwebp.exe (already vendored). No test framework in this repo — tests are plain assert-based scripts run directly with `python <file>.py`, matching existing repo convention (zero prior test suite).

## Global Constraints

- Registry writes are HKCU only (`Software\Classes\SystemFileAssociations\<ext>\shell\...`) — no admin/UAC prompt, ever.
- Auto-compress settings are fixed: quality 75, encoder `ENCODER_BEST`, lossy (not lossless), `skip_if_larger=True`. Not user-configurable from the context menu.
- Auto-compress never deletes the original file.
- Auto-compress never shows a dialog or console window; failures are appended to `%LOCALAPPDATA%\WebPCrunchr\errors.log` only.
- The Settings button's install/uninstall action (GUI-triggered) *does* show a `QMessageBox` on success/failure — this is intentional, only the headless path is silent.
- Registered extensions = `core.file_utils.SUPPORTED_EXTENSIONS - {".webp"}`.

---

### Task 1: `core/shell_integration.py` — registry install/uninstall

**Files:**
- Create: `core/shell_integration.py`
- Test: `test_shell_integration.py` (repo root, plain script — no framework, matches repo convention)

**Interfaces:**
- Consumes: `core.file_utils.SUPPORTED_EXTENSIONS` (already defined, a `set[str]`)
- Produces: `install_context_menu() -> None`, `uninstall_context_menu() -> None`, `is_installed() -> bool` — these three names/signatures are consumed by Task 3.

- [ ] **Step 1: Write the failing test**

Create `test_shell_integration.py`:

```python
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from core import shell_integration


def demo():
    # Start clean regardless of prior state.
    shell_integration.uninstall_context_menu()
    assert shell_integration.is_installed() is False, "expected not installed after uninstall"

    shell_integration.install_context_menu()
    assert shell_integration.is_installed() is True, "expected installed after install"

    shell_integration.uninstall_context_menu()
    assert shell_integration.is_installed() is False, "expected not installed after second uninstall"

    print("shell_integration self-check passed")


if __name__ == "__main__":
    demo()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python test_shell_integration.py`
Expected: `ModuleNotFoundError: No module named 'core.shell_integration'`

- [ ] **Step 3: Write the implementation**

Create `core/shell_integration.py`:

```python
import sys
import winreg
from pathlib import Path

from core.file_utils import SUPPORTED_EXTENSIONS

_KEY_NAME = "WebPCrunchr"
_MENU_LABEL = "Compress to WebP"
_EXTENSIONS = sorted(SUPPORTED_EXTENSIONS - {".webp"})


def _pythonw_path() -> str:
    exe = Path(sys.executable)
    candidate = exe.with_name("pythonw.exe")
    return str(candidate) if candidate.exists() else str(exe)


def _command_line() -> str:
    if hasattr(sys, "_MEIPASS"):
        target = f'"{sys.executable}"'
    else:
        main_py = Path(__file__).resolve().parent.parent / "main.py"
        target = f'"{_pythonw_path()}" "{main_py}"'
    return f'{target} --auto-compress "%1"'


def _shell_key_path(ext: str) -> str:
    return f"Software\\Classes\\SystemFileAssociations\\{ext}\\shell\\{_KEY_NAME}"


def install_context_menu() -> None:
    command = _command_line()
    for ext in _EXTENSIONS:
        key_path = _shell_key_path(ext)
        with winreg.CreateKeyEx(winreg.HKEY_CURRENT_USER, key_path) as key:
            winreg.SetValueEx(key, "", 0, winreg.REG_SZ, _MENU_LABEL)
        with winreg.CreateKeyEx(winreg.HKEY_CURRENT_USER, f"{key_path}\\command") as key:
            winreg.SetValueEx(key, "", 0, winreg.REG_SZ, command)


def uninstall_context_menu() -> None:
    for ext in _EXTENSIONS:
        key_path = _shell_key_path(ext)
        try:
            winreg.DeleteKey(winreg.HKEY_CURRENT_USER, f"{key_path}\\command")
        except FileNotFoundError:
            pass
        try:
            winreg.DeleteKey(winreg.HKEY_CURRENT_USER, key_path)
        except FileNotFoundError:
            pass


def is_installed() -> bool:
    key_path = _shell_key_path(_EXTENSIONS[0])
    try:
        winreg.OpenKey(winreg.HKEY_CURRENT_USER, key_path).Close()
        return True
    except FileNotFoundError:
        return False
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python test_shell_integration.py`
Expected: prints `shell_integration self-check passed`, exits 0

- [ ] **Step 5: Commit**

```bash
git add core/shell_integration.py test_shell_integration.py
git commit -m "feat: add HKCU registry install/uninstall for Explorer context menu"
```

---

### Task 2: Headless `--auto-compress` CLI mode in `main.py`

**Files:**
- Modify: `main.py` (full rewrite, file is only 19 lines)
- Test: `test_auto_compress.py` (repo root, plain script)

**Interfaces:**
- Consumes: `core.converter.convert(src, dest, quality, encoder=..., lossless=..., skip_if_larger=...)`, `core.converter.ENCODER_BEST`, `core.file_utils.output_path(source, output_dir)` — all already exist (see `core/converter.py:75-103`, `core/file_utils.py:34-41`).
- Produces: `run_auto_compress(paths: list[str]) -> None` in `main.py` — consumed by `core/shell_integration.py`'s generated command line (`--auto-compress` flag routes to this) and by Task 2's own test.

- [ ] **Step 1: Write the failing test**

Create `test_auto_compress.py`:

```python
import sys
import tempfile
from pathlib import Path

from PIL import Image

sys.path.insert(0, str(Path(__file__).resolve().parent))
import main as app_main


def demo():
    with tempfile.TemporaryDirectory() as tmp:
        src = Path(tmp) / "photo.jpg"
        Image.new("RGB", (64, 64), color=(200, 50, 50)).save(src, "JPEG")

        app_main.run_auto_compress([str(src)])

        dest = src.with_suffix(".webp")
        assert dest.exists(), "expected .webp output next to source"
        assert src.exists(), "original must not be deleted"

        print("auto-compress self-check passed")


if __name__ == "__main__":
    demo()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python test_auto_compress.py`
Expected: `AttributeError: module 'main' has no attribute 'run_auto_compress'`

- [ ] **Step 3: Write the implementation**

Replace all of `main.py` with:

```python
import os
import sys
from pathlib import Path


def _log_error(path: str, error: str) -> None:
    log_dir = Path(os.environ["LOCALAPPDATA"]) / "WebPCrunchr"
    log_dir.mkdir(parents=True, exist_ok=True)
    with open(log_dir / "errors.log", "a", encoding="utf-8") as f:
        f.write(f"{path}: {error}\n")


def run_auto_compress(paths: list[str]) -> None:
    from core.converter import convert, ENCODER_BEST
    from core.file_utils import output_path

    for src in paths:
        dest = output_path(src, None)
        try:
            convert(src, dest, quality=75, encoder=ENCODER_BEST,
                    lossless=False, skip_if_larger=True)
        except Exception as exc:
            _log_error(src, str(exc))


def main():
    if len(sys.argv) > 1 and sys.argv[1] == "--auto-compress":
        run_auto_compress(sys.argv[2:])
        return

    from PyQt6.QtWidgets import QApplication
    from ui.main_window import MainWindow

    app = QApplication(sys.argv)
    app.setApplicationName("WebP Crunchr")
    app.setApplicationVersion("1.0.0")
    window = MainWindow()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
```

Note: `QApplication`/`MainWindow` imports moved inside `main()` so the `--auto-compress` path never imports PyQt6 — keeps each right-click-spawned process fast. The pre-existing unused `QIcon` import from the old file is dropped as part of this rewrite (it was never used).

- [ ] **Step 4: Run test to verify it passes**

Run: `python test_auto_compress.py`
Expected: prints `auto-compress self-check passed`, exits 0

- [ ] **Step 5: Manually verify normal GUI launch still works**

Run: `python main.py`
Expected: the app window opens exactly as before (no argv, so it falls through to the GUI branch).

- [ ] **Step 6: Commit**

```bash
git add main.py test_auto_compress.py
git commit -m "feat: add headless --auto-compress CLI mode for Explorer integration"
```

---

### Task 3: Settings button in `ui/main_window.py`

**Files:**
- Modify: `ui/main_window.py:1-17` (imports), `ui/main_window.py:286-302` (`btn_row` in `_build_ui`), add two new methods near the other private handlers (after `_clear_list`, `ui/main_window.py:347-354`)

**Interfaces:**
- Consumes: `core.shell_integration.install_context_menu()`, `uninstall_context_menu()`, `is_installed()` (from Task 1).
- Produces: nothing consumed by later tasks — this is the last task.

- [ ] **Step 1: Add the import**

In `ui/main_window.py`, after line 16 (`from core.converter import ...`), add:

```python
from core import shell_integration
```

- [ ] **Step 2: Add the button to `btn_row`**

In `_build_ui`, `btn_row` currently reads (`ui/main_window.py:287-302`):

```python
        btn_row = QHBoxLayout()
        self.clear_btn = QPushButton("Clear List")
        self.clear_btn.clicked.connect(self._clear_list)
        btn_row.addWidget(self.clear_btn)
        btn_row.addStretch()
```

Change to:

```python
        btn_row = QHBoxLayout()
        self.clear_btn = QPushButton("Clear List")
        self.clear_btn.clicked.connect(self._clear_list)
        btn_row.addWidget(self.clear_btn)
        self.context_menu_btn = QPushButton()
        self.context_menu_btn.clicked.connect(self._toggle_context_menu)
        btn_row.addWidget(self.context_menu_btn)
        self._refresh_context_menu_btn_label()
        btn_row.addStretch()
```

(The rest of `btn_row` — attribution label, `crunch_btn` — is unchanged.)

- [ ] **Step 3: Add the two handler methods**

After `_clear_list` (`ui/main_window.py:347-354`), add:

```python
    def _refresh_context_menu_btn_label(self):
        if shell_integration.is_installed():
            self.context_menu_btn.setText("Remove from right-click menu")
        else:
            self.context_menu_btn.setText("Add to right-click menu")

    def _toggle_context_menu(self):
        try:
            if shell_integration.is_installed():
                shell_integration.uninstall_context_menu()
                QMessageBox.information(
                    self, "Context menu removed",
                    '"Compress to WebP" removed from the right-click menu.',
                )
            else:
                shell_integration.install_context_menu()
                QMessageBox.information(
                    self, "Context menu added",
                    'Right-click an image in File Explorer and choose "Compress to WebP".',
                )
        except OSError as exc:
            QMessageBox.warning(self, "Error", str(exc))
        self._refresh_context_menu_btn_label()
```

- [ ] **Step 4: Manual test**

Run: `python main.py`
Expected: button reads "Add to right-click menu" (assuming Task 1's test left things uninstalled). Click it → `QMessageBox` confirms addition, button flips to "Remove from right-click menu". Right-click a `.jpg` in Explorer → "Compress to WebP" entry appears; clicking it produces a `.webp` next to the file with no window flashing. Click the button again → confirms removal, entry disappears from Explorer's menu, button flips back.

- [ ] **Step 5: Commit**

```bash
git add ui/main_window.py
git commit -m "feat: add Settings button to install/uninstall Explorer context menu"
```

---

## Post-plan check

- [ ] Run `python test_shell_integration.py` and `python test_auto_compress.py` once more back-to-back to confirm no leftover registry state from manual testing in Task 3 Step 4 (if you left the context menu installed while testing, either leave it — it's a real feature the user now has — or click the button once more to remove it before considering the branch done).
