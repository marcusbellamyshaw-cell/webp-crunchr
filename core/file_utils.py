import os
from pathlib import Path

SUPPORTED_EXTENSIONS = {".jpg", ".jpeg", ".png", ".gif", ".bmp", ".tiff", ".tif", ".heic"}


def is_supported(path: str) -> bool:
    return Path(path).suffix.lower() in SUPPORTED_EXTENSIONS


def collect_files(path: str, recursive: bool = True) -> list[str]:
    """Return supported image files under path. If path is a file, return it (if supported)."""
    p = Path(path)
    if p.is_file():
        return [str(p)] if is_supported(str(p)) else []
    if p.is_dir():
        pattern = "**/*" if recursive else "*"
        return sorted(
            str(f) for f in p.glob(pattern)
            if f.is_file() and is_supported(str(f))
        )
    return []


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
