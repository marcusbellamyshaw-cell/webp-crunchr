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
