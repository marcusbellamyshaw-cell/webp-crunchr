import os
from pathlib import Path

SUPPORTED_EXTENSIONS = {".jpg", ".jpeg", ".png", ".gif", ".bmp", ".tiff", ".tif", ".heic"}


def is_supported(path: str) -> bool:
    return Path(path).suffix.lower() in SUPPORTED_EXTENSIONS


def format_size(bytes_: int) -> str:
    if bytes_ < 1024:
        return f"{bytes_} B"
    elif bytes_ < 1024 * 1024:
        return f"{bytes_ / 1024:.1f} KB"
    else:
        return f"{bytes_ / (1024 * 1024):.2f} MB"


def output_path(source: str, output_dir: str | None) -> str:
    src = Path(source)
    dest_dir = Path(output_dir) if output_dir else src.parent
    candidate = dest_dir / (src.stem + ".webp")
    # Never overwrite source (edge case: source is already .webp)
    if candidate.resolve() == src.resolve():
        candidate = dest_dir / (src.stem + "_converted.webp")
    return str(candidate)
