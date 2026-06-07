# WebP Crunchr

> Drag-and-drop batch image compressor that converts photos to WebP with maximum compression and minimal quality loss.

![Python](https://img.shields.io/badge/python-3.11%2B-blue)
![License](https://img.shields.io/badge/license-MIT-green)
![Platform](https://img.shields.io/badge/platform-Windows-lightgrey)

---

## Screenshots

> _Replace this section with actual screenshots after first run._
>
> Drag a screenshot into the `screenshots/` folder and reference it here:
> ```
> ![WebP Crunchr main window](screenshots/main_window.png)
> ```

---

## Features

- **Drag-and-drop** or click-to-browse batch file import
- Converts **JPEG, PNG, GIF (first frame), BMP, TIFF, HEIC** → WebP
- **Quality slider** (50–95, default 75) for fine-grained size/quality tradeoff
- **Pillow** encoding with `method=6` for maximum compression
- Optional **cwebp** backend (auto-detected on PATH) for potentially better output
- Strips all EXIF/metadata from output files
- Preserves **alpha channel** (transparency) from PNG/WebP sources
- **Per-file output folder** support; defaults to same directory as source
- Never overwrites the original file
- Non-blocking processing via **QThread** — UI stays responsive
- Per-file status icons (queued / processing / done / error) with error tooltips
- **Completion summary**: total size before → after with % saved
- Dark-themed PyQt6 UI, 700×500 minimum, fully resizable

---

## Requirements

- Python 3.11+
- PyQt6
- Pillow
- pillow-heif _(optional — required for HEIC support)_
- cwebp _(optional — install from [developers.google.com/speed/webp](https://developers.google.com/speed/webp/docs/prebuilt) and add to PATH)_

---

## Installation

```bash
# 1. Clone the repo
git clone https://github.com/marcusbellamyshaw/webp-crunchr.git
cd webp-crunchr

# 2. Create and activate a virtual environment
python -m venv .venv
.venv\Scripts\activate

# 3. Install dependencies
pip install -r requirements.txt
```

---

## Usage

```bash
python main.py
```

1. Drag image files onto the drop zone, or click it to open a file browser.
2. Optionally set a custom output folder (defaults to the source file's folder).
3. Adjust the quality slider (lower = smaller file, higher = better quality).
4. Click **Crunch 'em** to start batch conversion.
5. Monitor per-file progress and the summary row at the bottom.

---

## Building a standalone .exe

Requires [PyInstaller](https://pyinstaller.org):

```bash
pip install pyinstaller
build.bat
```

The compiled executable will be placed in `dist\WebP Crunchr.exe`. No Python installation required on the target machine.

---

## Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/my-feature`)
3. Commit your changes following [Conventional Commits](https://www.conventionalcommits.org/)
4. Open a Pull Request describing what changed and why

Please keep PRs focused — one feature or fix per PR.

---

## License

[MIT](LICENSE) — free to use, modify, and distribute.
