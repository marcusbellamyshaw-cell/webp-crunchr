import os
import subprocess
from pathlib import Path

from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QPushButton, QLabel, QSlider, QLineEdit, QFileDialog,
    QProgressBar, QCheckBox, QSizePolicy, QMessageBox, QRadioButton, QButtonGroup,
)
from PyQt6.QtCore import Qt, QThread, pyqtSignal, QObject, QUrl
from PyQt6.QtGui import QDragEnterEvent, QDropEvent, QDesktopServices

from ui.drop_zone import DropZone
from ui.file_list import FileListWidget, FileEntry
from core.file_utils import format_size, output_path, collect_files
from core.converter import convert, cwebp_available, HEIC_SUPPORTED, ENCODER_PILLOW, ENCODER_CWEBP, ENCODER_BEST


DARK_STYLE = """
QMainWindow, QWidget {
    background: #121212;
    color: #ddd;
    font-family: Segoe UI, sans-serif;
    font-size: 13px;
}
QPushButton {
    background: #2a2a2a;
    color: #ddd;
    border: 1px solid #444;
    border-radius: 5px;
    padding: 6px 14px;
}
QPushButton:hover { background: #333; }
QPushButton:pressed { background: #1a1a1a; }
QPushButton#crunch_btn {
    background: #00838f;
    color: white;
    font-weight: bold;
    font-size: 14px;
    padding: 8px 24px;
}
QPushButton#crunch_btn:hover { background: #00acc1; }
QPushButton#crunch_btn:disabled { background: #2a2a2a; color: #555; }
QLineEdit {
    background: #1e1e1e;
    border: 1px solid #444;
    border-radius: 4px;
    padding: 4px 8px;
    color: #ddd;
}
QSlider::groove:horizontal {
    height: 4px;
    background: #444;
    border-radius: 2px;
}
QSlider::handle:horizontal {
    background: #00bcd4;
    width: 14px;
    height: 14px;
    margin: -5px 0;
    border-radius: 7px;
}
QSlider::sub-page:horizontal { background: #00bcd4; border-radius: 2px; }
QProgressBar {
    background: #1e1e1e;
    border: 1px solid #444;
    border-radius: 4px;
    text-align: center;
    color: #ddd;
}
QProgressBar::chunk { background: #00bcd4; border-radius: 3px; }
QCheckBox { color: #aaa; }
QCheckBox::indicator { width: 14px; height: 14px; }
QRadioButton {
    color: #ddd;
    spacing: 6px;
}
QRadioButton::indicator {
    width: 16px;
    height: 16px;
    border-radius: 8px;
    border: 2px solid #666;
    background: #1e1e1e;
}
QRadioButton::indicator:hover {
    border-color: #00bcd4;
}
QRadioButton::indicator:checked {
    border: 2px solid #00bcd4;
    background: #00bcd4;
}
QRadioButton::indicator:disabled {
    border-color: #3a3a3a;
    background: #1a1a1a;
}
QRadioButton:disabled { color: #555; }
"""


class ConversionWorker(QObject):
    progress = pyqtSignal(int, int)               # current, total
    file_done = pyqtSignal(str, int, str, str)    # path, output_size, error, status
    finished = pyqtSignal()

    def __init__(self, entries: list[FileEntry], quality: int, encoder: str,
                 lossless: bool = False, skip_if_larger: bool = False):
        super().__init__()
        self._entries = entries
        self._quality = quality
        self._encoder = encoder
        self._lossless = lossless
        self._skip_if_larger = skip_if_larger
        self._cancelled = False

    def cancel(self):
        self._cancelled = True

    def run(self):
        total = len(self._entries)
        for i, entry in enumerate(self._entries):
            if self._cancelled:
                break
            dest = output_path(entry.path, entry.output_dir)
            try:
                result = convert(
                    entry.path, dest, self._quality,
                    encoder=self._encoder,
                    lossless=self._lossless,
                    skip_if_larger=self._skip_if_larger,
                )
                if result == "skipped":
                    self.file_done.emit(entry.path, 0, "", "skipped")
                else:
                    size = Path(dest).stat().st_size
                    self.file_done.emit(entry.path, size, "", "done")
            except Exception as exc:
                self.file_done.emit(entry.path, -1, str(exc), "error")
            self.progress.emit(i + 1, total)
        self.finished.emit()


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("WebP Crunchr")
        self.setMinimumSize(700, 500)
        self._thread: QThread | None = None
        self._worker: ConversionWorker | None = None
        self._output_dir: str | None = None
        self._build_ui()

    def _build_ui(self):
        self.setStyleSheet(DARK_STYLE)
        root = QWidget()
        self.setCentralWidget(root)
        layout = QVBoxLayout(root)
        layout.setSpacing(10)
        layout.setContentsMargins(16, 16, 16, 16)

        # Drop zone
        self.drop_zone = DropZone()
        self.drop_zone.files_dropped.connect(self._on_paths_received)
        layout.addWidget(self.drop_zone)

        # File list
        self.file_list = FileListWidget()
        layout.addWidget(self.file_list, stretch=1)

        # Output folder row
        out_row = QHBoxLayout()
        out_row.addWidget(QLabel("Output folder:"))
        self.out_dir_edit = QLineEdit()
        self.out_dir_edit.setPlaceholderText("Same folder as source (default)")
        self.out_dir_edit.setReadOnly(True)
        out_row.addWidget(self.out_dir_edit, stretch=1)
        browse_btn = QPushButton("Browse…")
        browse_btn.clicked.connect(self._pick_output_dir)
        out_row.addWidget(browse_btn)
        clear_out_btn = QPushButton("Reset")
        clear_out_btn.clicked.connect(self._clear_output_dir)
        out_row.addWidget(clear_out_btn)
        layout.addLayout(out_row)

        # Add folder + subfolder row
        folder_row = QHBoxLayout()
        add_folder_btn = QPushButton("Add Folder…")
        add_folder_btn.clicked.connect(self._pick_input_folder)
        folder_row.addWidget(add_folder_btn)
        self.subfolder_check = QCheckBox("Include subfolders")
        self.subfolder_check.setChecked(True)
        folder_row.addWidget(self.subfolder_check)
        folder_row.addStretch()
        layout.addLayout(folder_row)

        # Quality + encoder row
        opts_row = QHBoxLayout()
        opts_row.addWidget(QLabel("Quality:"))
        self.quality_slider = QSlider(Qt.Orientation.Horizontal)
        self.quality_slider.setRange(50, 95)
        self.quality_slider.setValue(75)
        self.quality_slider.setFixedWidth(160)
        self.quality_slider.valueChanged.connect(self._on_quality_change)
        opts_row.addWidget(self.quality_slider)
        self.quality_label = QLabel("75")
        self.quality_label.setFixedWidth(28)
        opts_row.addWidget(self.quality_label)
        opts_row.addSpacing(20)
        opts_row.addWidget(QLabel("Encoder:"))
        self._encoder_group = QButtonGroup(self)
        self._radio_pillow = QRadioButton("Pillow")
        self._radio_cwebp  = QRadioButton("cwebp")
        self._radio_best   = QRadioButton("Best (try both)")
        if not cwebp_available():
            for r in (self._radio_cwebp, self._radio_best):
                r.setEnabled(False)
                r.setToolTip("cwebp not found")
        self._encoder_group.addButton(self._radio_pillow)
        self._encoder_group.addButton(self._radio_cwebp)
        self._encoder_group.addButton(self._radio_best)
        self._radio_cwebp.setChecked(True)
        opts_row.addWidget(self._radio_pillow)
        opts_row.addWidget(self._radio_cwebp)
        opts_row.addWidget(self._radio_best)
        if not HEIC_SUPPORTED:
            heic_label = QLabel("⚠ HEIC support unavailable (install pillow-heif)")
            heic_label.setStyleSheet("color: #f9a825; font-size: 11px;")
            opts_row.addSpacing(16)
            opts_row.addWidget(heic_label)
        opts_row.addStretch()
        layout.addLayout(opts_row)

        # Extra options row — radio pairs for lossless and skip-if-larger
        extra_row = QHBoxLayout()
        extra_row.addWidget(QLabel("Mode:"))
        self._mode_group = QButtonGroup(self)
        self._radio_lossy    = QRadioButton("Lossy")
        self._radio_lossless = QRadioButton("Lossless")
        self._radio_lossy.setToolTip("Standard lossy WebP — smallest files, tuned by the quality slider")
        self._radio_lossless.setToolTip("Lossless WebP — pixel-perfect, best for logos and text. Quality slider is ignored.")
        self._mode_group.addButton(self._radio_lossy)
        self._mode_group.addButton(self._radio_lossless)
        self._radio_lossy.setChecked(True)
        extra_row.addWidget(self._radio_lossy)
        extra_row.addWidget(self._radio_lossless)
        extra_row.addSpacing(24)
        extra_row.addWidget(QLabel("If larger:"))
        self._size_group = QButtonGroup(self)
        self._radio_skip  = QRadioButton("Skip")
        self._radio_write = QRadioButton("Write anyway")
        self._radio_skip.setToolTip("Don't write the .webp if it ends up bigger than the source")
        self._radio_write.setToolTip("Always write the output even if it's larger than the source")
        self._size_group.addButton(self._radio_skip)
        self._size_group.addButton(self._radio_write)
        self._radio_skip.setChecked(True)
        extra_row.addWidget(self._radio_skip)
        extra_row.addWidget(self._radio_write)
        extra_row.addStretch()
        layout.addLayout(extra_row)

        # Progress bar
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        layout.addWidget(self.progress_bar)

        # Summary + open folder row
        summary_row = QHBoxLayout()
        self.summary_label = QLabel("")
        self.summary_label.setAlignment(Qt.AlignmentFlag.AlignVCenter)
        self.summary_label.setStyleSheet("color: #4caf50; font-size: 13px;")
        self.summary_label.setVisible(False)
        summary_row.addWidget(self.summary_label, stretch=1)
        self.open_folder_btn = QPushButton("Open Folder")
        self.open_folder_btn.setVisible(False)
        self.open_folder_btn.clicked.connect(self._open_output_folder)
        summary_row.addWidget(self.open_folder_btn)
        self.delete_originals_btn = QPushButton("Delete Originals")
        self.delete_originals_btn.setVisible(False)
        self.delete_originals_btn.setStyleSheet(
            "QPushButton { color: #ef5350; border-color: #ef5350; }"
            "QPushButton:hover { background: #2a1515; border-color: #ef5350; }"
        )
        self.delete_originals_btn.clicked.connect(self._delete_originals)
        summary_row.addWidget(self.delete_originals_btn)
        layout.addLayout(summary_row)

        # Action buttons row
        btn_row = QHBoxLayout()
        self.clear_btn = QPushButton("Clear List")
        self.clear_btn.clicked.connect(self._clear_list)
        btn_row.addWidget(self.clear_btn)
        btn_row.addStretch()
        # Attribution link
        attr_label = QLabel('<a href="https://everybittexas.com/" style="color:#29b6f6; text-decoration:none;">Brought to you by Every Bit Texas</a>')
        attr_label.setOpenExternalLinks(True)
        attr_label.setAlignment(Qt.AlignmentFlag.AlignVCenter)
        btn_row.addWidget(attr_label)
        btn_row.addSpacing(16)
        self.crunch_btn = QPushButton("Crunch 'em")
        self.crunch_btn.setObjectName("crunch_btn")
        self.crunch_btn.clicked.connect(self._start_conversion)
        btn_row.addWidget(self.crunch_btn)
        layout.addLayout(btn_row)

    def _on_quality_change(self, value: int):
        self.quality_label.setText(str(value))

    def _on_paths_received(self, paths: list[str]):
        """Expand directories into individual files, then add to queue."""
        recursive = self.subfolder_check.isChecked()
        file_paths = []
        for p in paths:
            file_paths.extend(collect_files(p, recursive=recursive))
        self._add_files(file_paths)

    def _add_files(self, paths: list[str]):
        entries = []
        for p in paths:
            try:
                size = Path(p).stat().st_size
            except OSError:
                size = 0
            entries.append(FileEntry(path=p, original_size=size, output_dir=self._output_dir))
        self.file_list.add_entries(entries)
        self.summary_label.setVisible(False)

    def _pick_input_folder(self):
        d = QFileDialog.getExistingDirectory(self, "Select Input Folder")
        if d:
            self._on_paths_received([d])

    def _pick_output_dir(self):
        d = QFileDialog.getExistingDirectory(self, "Select Output Folder")
        if d:
            self._output_dir = d
            self.out_dir_edit.setText(d)
            for e in self.file_list.entries():
                if e.status == "queued":
                    e.output_dir = d

    def _clear_output_dir(self):
        self._output_dir = None
        self.out_dir_edit.clear()
        for e in self.file_list.entries():
            if e.status == "queued":
                e.output_dir = None

    def _clear_list(self):
        if self._thread and self._thread.isRunning():
            return
        self.file_list.clear_entries()
        self.summary_label.setVisible(False)
        self.progress_bar.setVisible(False)
        self.open_folder_btn.setVisible(False)
        self.delete_originals_btn.setVisible(False)

    def _start_conversion(self):
        entries = [e for e in self.file_list.entries() if e.status == "queued"]
        if not entries:
            QMessageBox.information(self, "Nothing to do", "No queued files to convert.")
            return

        quality = self.quality_slider.value()
        if self._radio_best.isChecked():
            encoder = ENCODER_BEST
        elif self._radio_cwebp.isChecked():
            encoder = ENCODER_CWEBP
        else:
            encoder = ENCODER_PILLOW

        lossless = self._radio_lossless.isChecked()
        skip_if_larger = self._radio_skip.isChecked()

        self.crunch_btn.setEnabled(False)
        self.open_folder_btn.setVisible(False)
        self.progress_bar.setRange(0, len(entries))
        self.progress_bar.setValue(0)
        self.progress_bar.setVisible(True)
        self.summary_label.setVisible(False)

        for e in entries:
            self.file_list.update_entry(e.path, status="processing")

        self._worker = ConversionWorker(entries, quality, encoder, lossless, skip_if_larger)
        self._thread = QThread()
        self._worker.moveToThread(self._thread)
        self._thread.started.connect(self._worker.run)
        self._worker.progress.connect(self._on_progress)
        self._worker.file_done.connect(self._on_file_done)
        self._worker.finished.connect(self._on_finished)
        self._worker.finished.connect(self._thread.quit)
        self._worker.finished.connect(self._worker.deleteLater)
        self._thread.finished.connect(self._thread.deleteLater)
        self._thread.start()

    def _on_progress(self, current: int, total: int):
        self.progress_bar.setValue(current)

    def _on_file_done(self, path: str, output_size: int, error: str, status: str):
        if status == "error":
            self.file_list.update_entry(path, status="error", error_msg=error)
        elif status == "skipped":
            self.file_list.update_entry(path, status="skipped")
        else:
            self.file_list.update_entry(path, status="done", output_size=output_size)

    def _on_finished(self):
        self.crunch_btn.setEnabled(True)
        self.progress_bar.setVisible(False)
        self._show_summary()

    def _delete_originals(self):
        done = [e for e in self.file_list.entries() if e.status == "done"]
        if not done:
            return
        reply = QMessageBox.warning(
            self,
            "Delete Originals",
            f"Permanently delete {len(done)} original file(s)?\nThis cannot be undone.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.Cancel,
            QMessageBox.StandardButton.Cancel,
        )
        if reply != QMessageBox.StandardButton.Yes:
            return
        failed = []
        for e in done:
            try:
                Path(e.path).unlink()
            except OSError as ex:
                failed.append(f"{Path(e.path).name}: {ex}")
        if failed:
            QMessageBox.warning(self, "Some files could not be deleted",
                                "\n".join(failed))
        self.delete_originals_btn.setVisible(False)

    def _open_output_folder(self):
        entries = self.file_list.entries()
        done = [e for e in entries if e.status in ("done", "skipped")]
        if not done:
            return
        # Use the first done entry's output dir (or source dir if default)
        e = done[0]
        folder = e.output_dir if e.output_dir else str(Path(e.path).parent)
        QDesktopServices.openUrl(QUrl.fromLocalFile(folder))

    def _show_summary(self):
        entries = self.file_list.entries()
        done    = [e for e in entries if e.status == "done" and e.output_size is not None]
        skipped = [e for e in entries if e.status == "skipped"]
        errors  = [e for e in entries if e.status == "error"]
        if not done and not skipped:
            return
        parts = []
        if done:
            total_in  = sum(e.original_size for e in done)
            total_out = sum(e.output_size for e in done)
            pct = (1 - total_out / total_in) * 100 if total_in else 0
            parts.append(
                f"✅ {len(done)} converted  —  "
                f"{format_size(total_in)} → {format_size(total_out)} ({pct:.1f}% saved)"
            )
        if skipped:
            parts.append(f"⏭ {len(skipped)} skipped (already smallest)")
        if errors:
            parts.append(f"⚠ {len(errors)} error(s)")
        self.summary_label.setText("   ".join(parts))
        self.summary_label.setVisible(True)
        self.open_folder_btn.setVisible(True)
        self.delete_originals_btn.setVisible(bool(done))
