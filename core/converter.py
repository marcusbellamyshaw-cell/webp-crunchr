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


def convert_with_pillow(src: str, dest: str, quality: int, lossless: bool = False) -> None:
    with Image.open(src) as img:
        if getattr(img, "is_animated", False):
            img.seek(0)
        if img.mode in ("RGBA", "LA"):
            out = img.convert("RGBA")
        elif img.mode == "P" and "transparency" in img.info:
            out = img.convert("RGBA")
        else:
            out = img.convert("RGB")
        if lossless:
            out.save(dest, format="WEBP", lossless=True, method=6, exif=b"")
        else:
            out.save(dest, format="WEBP", quality=quality, method=6, lossless=False, exif=b"")


def convert_with_cwebp(src: str, dest: str, quality: int, lossless: bool = False) -> None:
    exe = _cwebp_path()
    if lossless:
        cmd = [exe, "-lossless", "-z", "9", "-metadata", "none", src, "-o", dest]
    else:
        cmd = [exe, "-q", str(quality), "-m", "6", "-metadata", "none", src, "-o", dest]
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        raise RuntimeError(f"cwebp failed: {result.stderr.strip()}")


def convert_best(src: str, dest: str, quality: int, lossless: bool = False) -> None:
    """Encode with both Pillow and cwebp, write whichever is smaller."""
    with tempfile.TemporaryDirectory() as tmp:
        p_out = str(Path(tmp) / "pillow.webp")
        c_out = str(Path(tmp) / "cwebp.webp")
        convert_with_pillow(src, p_out, quality, lossless)
        convert_with_cwebp(src, c_out, quality, lossless)
        winner = c_out if Path(c_out).stat().st_size <= Path(p_out).stat().st_size else p_out
        Path(dest).write_bytes(Path(winner).read_bytes())


def convert(
    src: str,
    dest: str,
    quality: int,
    encoder: str = ENCODER_CWEBP,
    lossless: bool = False,
    skip_if_larger: bool = False,
) -> str:
    """
    Convert src to WebP at dest. Returns 'converted', 'skipped', or raises on error.
    'skipped' means the output would have been larger than the source.
    """
    Path(dest).parent.mkdir(parents=True, exist_ok=True)

    if encoder == ENCODER_BEST and cwebp_available():
        convert_best(src, dest, quality, lossless)
    elif encoder == ENCODER_CWEBP and cwebp_available():
        convert_with_cwebp(src, dest, quality, lossless)
    else:
        convert_with_pillow(src, dest, quality, lossless)

    if skip_if_larger:
        src_size = Path(src).stat().st_size
        out_size = Path(dest).stat().st_size
        if out_size >= src_size:
            Path(dest).unlink(missing_ok=True)
            return "skipped"

    return "converted"
