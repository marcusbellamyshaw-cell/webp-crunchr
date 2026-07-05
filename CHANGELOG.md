# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [1.1.0] - 2026-07-04

### Added
- Windows Explorer right-click "Compress to WebP" — convert selected image(s) to WebP in place, no app window needed
- "Add/Remove from right-click menu" button to install or remove the Explorer integration (per-user, no admin required)
- Headless `--auto-compress` CLI mode backing the Explorer action (fixed quality 75, Best encoder, skip-if-larger; original file always kept; failures logged to `%LOCALAPPDATA%\WebPCrunchr\errors.log`)

### Fixed
- Conversion worker/thread references now reset after each run, preventing stale state from carrying into the next batch

## [1.0.0] - 2026-06-07

### Added
- Drag-and-drop and click-to-browse batch image import, including whole folders with a subfolder option
- Support for JPG, JPEG, PNG, GIF (first frame), BMP, TIFF, HEIC, and WebP input formats
- Pillow-based WebP encoding with `method=6` for maximum compression
- Encoder choice — Pillow, bundled `cwebp`, or Best (tries both, keeps the smaller result)
- Quality slider (range 50–95, default 75)
- Lossless mode for pixel-perfect output
- Skip-if-larger — never writes a WebP bigger than the source
- Alpha channel preservation for PNG and other transparent sources
- EXIF/metadata stripping from all output files
- Per-file output folder selector with per-source default fallback
- File queue table showing filename, original size, output size, compression %, and status icon
- Non-blocking QThread conversion worker — UI remains responsive during batch processing
- Per-file error handling with red status icons and tooltip messages
- Completion summary showing total size before → after and % saved
- Open Folder button to jump to the output location after conversion
- Delete Originals button to remove source files after a confirmed conversion
- "Clear List" button to reset the queue
- Progress bar during batch conversion
- Dark-themed PyQt6 UI with dashed drop zone icon, 700×500 minimum size, fully resizable
- Bundled `cwebp` 1.6.0 (Google libwebp) executable — no separate install required
- Attribution link to Every Bit Texas
- `build.bat` for PyInstaller single-file Windows executable
- MIT License
