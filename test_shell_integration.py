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
