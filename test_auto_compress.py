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
