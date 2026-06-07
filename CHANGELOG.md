# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [1.0.0] - 2026-06-07

### Added
- Drag-and-drop and click-to-browse batch image import
- Support for JPEG, JPG, PNG, GIF (first frame), BMP, TIFF, and HEIC input formats
- Pillow-based WebP encoding with `method=6` for maximum compression
- Optional `cwebp` backend (auto-detected on PATH) for potentially better output
- Quality slider (range 50–95, default 75)
- Alpha channel preservation for PNG and other transparent sources
- EXIF/metadata stripping from all output files
- Per-file output folder selector with per-source default fallback
- File queue table showing filename, original size, output size, compression %, and status icon
- Non-blocking QThread conversion worker — UI remains responsive during batch processing
- Per-file error handling with red status icons and tooltip messages
- Completion summary showing total size before → after and % saved
- "Clear List" button to reset the queue
- Progress bar during batch conversion
- Dark-themed PyQt6 UI, 700×500 minimum size, fully resizable
- `build.bat` for PyInstaller single-file Windows executable
- MIT License
