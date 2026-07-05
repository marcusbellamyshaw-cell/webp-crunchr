import sys
import winreg
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from core import shell_integration


def demo():
    # Start clean regardless of prior state.
    shell_integration.uninstall_context_menu()
    try:
        assert shell_integration.is_installed() is False, "expected not installed after uninstall"

        shell_integration.install_context_menu()
        assert shell_integration.is_installed() is True, "expected installed after install"

        # Verify hardened behavior: remove ONE extension's key and confirm is_installed() detects partial state.
        # Pick the first extension and delete its registry keys (command first, then the main key).
        test_ext = shell_integration._EXTENSIONS[0]
        key_path = shell_integration._shell_key_path(test_ext)
        try:
            winreg.DeleteKey(winreg.HKEY_CURRENT_USER, f"{key_path}\\command")
        except FileNotFoundError:
            pass
        try:
            winreg.DeleteKey(winreg.HKEY_CURRENT_USER, key_path)
        except FileNotFoundError:
            pass
        assert shell_integration.is_installed() is False, "expected not installed after removing one extension's key"

        shell_integration.uninstall_context_menu()
        assert shell_integration.is_installed() is False, "expected not installed after second uninstall"

        # Flag-string seam: shell_integration builds "--auto-compress" and main.py checks
        # for the same literal. Nothing else ties these together, so assert it directly.
        assert "--auto-compress" in shell_integration._command_line(), \
            "expected _command_line() to contain the --auto-compress flag main.py dispatches on"
    finally:
        shell_integration.uninstall_context_menu()

    print("shell_integration self-check passed")


if __name__ == "__main__":
    demo()
