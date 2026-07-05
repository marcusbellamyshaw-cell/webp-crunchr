import sys
import tempfile
from pathlib import Path

from PIL import Image

sys.path.insert(0, str(Path(__file__).resolve().parent))
import main as app_main


def demo():
    with tempfile.TemporaryDirectory() as tmp:
        # Solid color fixture: compresses reliably smaller under WebP, so skip_if_larger
        # never deletes the output here and dest.exists() stays a valid assertion.
        src = Path(tmp) / "photo.jpg"
        Image.new("RGB", (64, 64), color=(200, 50, 50)).save(src, "JPEG")

        app_main.run_auto_compress([str(src)])

        dest = src.with_suffix(".webp")
        assert dest.exists(), "expected .webp output next to source"
        assert src.exists(), "original must not be deleted"

        print("auto-compress self-check passed")

    with tempfile.TemporaryDirectory() as tmp:
        # Flag-string seam: drive main.main() through the actual --auto-compress
        # dispatch (patched sys.argv), not just run_auto_compress() directly, so a
        # rename of the flag literal in either main.py or shell_integration.py fails here.
        src = Path(tmp) / "photo2.jpg"
        Image.new("RGB", (64, 64), color=(50, 200, 50)).save(src, "JPEG")

        old_argv = sys.argv
        sys.argv = ["main.py", "--auto-compress", str(src)]
        try:
            app_main.main()
        finally:
            sys.argv = old_argv

        dest = src.with_suffix(".webp")
        assert dest.exists(), "expected .webp output via --auto-compress dispatch"
        assert src.exists(), "original must not be deleted"

        print("auto-compress flag dispatch self-check passed")


if __name__ == "__main__":
    demo()
