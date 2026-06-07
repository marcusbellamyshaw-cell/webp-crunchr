import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

from PIL import Image

try:
    import pillow_heif
    pillow_heif.register_heif_opener()
    HEIC_SUPPORTED = True
except ImportError:
    HEIC_SUPPORTED = False

ENCODER_PILLOW = "pillow"
ENCODER_CWEBP  = "cwebp"
ENCODER_BEST   = "best"


def _cwebp_path() -> str | None:
    """Return path to cwebp: bundled copy first, then system PATH."""
    if hasattr(sys, "_MEIPASS"):
        bundled = Path(sys._MEIPASS) / "cwebp.exe"
        if bundled.exists():
            return str(bundled)
    vendor = Path(__file__).parent.parent / "vendor" / "cwebp.exe"
    if vendor.exists():
        return str(vendor)
    return shutil.which("cwebp")


def cwebp_available() -> bool:
    return _cwebp_path() is not None


def convert_with_pillow(src: str, dest: str, quality: int) -> None:
    with Image.open(src) as img:
        if getattr(img, "is_animated", False):
            img.seek(0)
        if img.mode in ("RGBA", "LA"):
            out = img.convert("RGBA")
        elif img.mode == "P" and "transparency" in img.info:
            out = img.convert("RGBA")
        else:
            out = img.convert("RGB")
        out.save(dest, format="WEBP", quality=quality, method=6, lossless=False, exif=b"")


def convert_with_cwebp(src: str, dest: str, quality: int) -> None:
    exe = _cwebp_path()
    cmd = [exe, "-q", str(quality), "-m", "6", "-metadata", "none", src, "-o", dest]
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        raise RuntimeError(f"cwebp failed: {result.stderr.strip()}")


def convert_best(src: str, dest: str, quality: int) -> None:
    """Encode with both Pillow and cwebp, write whichever is smaller."""
    with tempfile.TemporaryDirectory() as tmp:
        p_out = str(Path(tmp) / "pillow.webp")
        c_out = str(Path(tmp) / "cwebp.webp")

        convert_with_pillow(src, p_out, quality)
        convert_with_cwebp(src, c_out, quality)

        p_size = Path(p_out).stat().st_size
        c_size = Path(c_out).stat().st_size
        winner = c_out if c_size <= p_size else p_out
        Path(dest).write_bytes(Path(winner).read_bytes())


def convert(src: str, dest: str, quality: int, encoder: str = ENCODER_CWEBP) -> None:
    Path(dest).parent.mkdir(parents=True, exist_ok=True)
    if encoder == ENCODER_BEST and cwebp_available():
        convert_best(src, dest, quality)
    elif encoder == ENCODER_CWEBP and cwebp_available():
        convert_with_cwebp(src, dest, quality)
    else:
        convert_with_pillow(src, dest, quality)
