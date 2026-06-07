import os
import shutil
import subprocess
from pathlib import Path

from PIL import Image

try:
    import pillow_heif
    pillow_heif.register_heif_opener()
    HEIC_SUPPORTED = True
except ImportError:
    HEIC_SUPPORTED = False


def cwebp_available() -> bool:
    return shutil.which("cwebp") is not None


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
    cmd = [
        "cwebp",
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
