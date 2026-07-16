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
            winreg.SetValueEx(key, "Position", 0, winreg.REG_SZ, "Top")
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
    for ext in _EXTENSIONS:
        key_path = _shell_key_path(ext)
        try:
            winreg.OpenKey(winreg.HKEY_CURRENT_USER, key_path).Close()
        except FileNotFoundError:
            return False
    return True
