import os
import shutil
import subprocess
import sys
from pathlib import Path

from PIL import Image

try:
    import pillow_heif
    pillow_heif.register_heif_opener()
    HEIC_SUPPORTED = True
except ImportError:
    HEIC_SUPPORTED = False


def _cwebp_path() -> str | None:
    """Return path to cwebp: bundled copy first, then system PATH."""
    # PyInstaller sets sys._MEIPASS when running from a compiled .exe
    if hasattr(sys, "_MEIPASS"):
        bundled = Path(sys._MEIPASS) / "cwebp.exe"
        if bundled.exists():
            return str(bundled)
    # Development: check vendor/ relative to this file
    vendor = Path(__file__).parent.parent / "vendor" / "cwebp.exe"
    if vendor.exists():
        return str(vendor)
    # Fall back to system PATH
    return shutil.which("cwebp")


def cwebp_available() -> bool:
    return _cwebp_path() is not None


def convert_with_pillow(src: str, dest: str, quality: int) -> None:
    with Image.open(src) as img:
        # GIF: use first frame only
        if getattr(img, "is_animated", False):
            img.seek(0)

        # Preserve alpha for formats that support it
        if img.mode in ("RGBA", "LA"):
            out = img.convert("RGBA")
        elif img.mode == "P" and "transparency" in img.info:
            out = img.convert("RGBA")
        else:
            out = img.convert("RGB")

        out.save(
            dest,
            format="WEBP",
            quality=quality,
            method=6,
            lossless=False,
            exif=b"",       # strip EXIF
        )


def convert_with_cwebp(src: str, dest: str, quality: int) -> None:
    exe = _cwebp_path()
    cmd = [
        exe,
        "-q", str(quality),
        "-m", "6",
        "-metadata", "none",
        src,
        "-o", dest,
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        raise RuntimeError(f"cwebp failed: {result.stderr.strip()}")


def convert(src: str, dest: str, quality: int, use_cwebp: bool = False) -> None:
    Path(dest).parent.mkdir(parents=True, exist_ok=True)
    if use_cwebp and cwebp_available():
        convert_with_cwebp(src, dest, quality)
    else:
        convert_with_pillow(src, dest, quality)
