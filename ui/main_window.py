import os
from pathlib import Path

from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QPushButton, QLabel, QSlider, QLineEdit, QFileDialog,
    QProgressBar, QCheckBox, QSizePolicy, QMessageBox,
)
from PyQt6.QtCore import Qt, QThread, pyqtSignal, QObject
from PyQt6.QtGui import QDragEnterEvent, QDropEvent

from ui.drop_zone import DropZone
from ui.file_list import FileListWidget, FileEntry
from core.file_utils import format_size, output_path, collect_files
from core.converter import convert, cwebp_available, HEIC_SUPPORTED


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
"""


class ConversionWorker(QObject):
    progress = pyqtSignal(int, int)           # current, total
    file_done = pyqtSignal(str, int, str)     # path, output_size, error
    finished = pyqtSignal()

    def __init__(self, entries: list[FileEntry], quality: int, use_cwebp: bool):
        super().__init__()
        self._entries = entries
        self._quality = quality
        self._use_cwebp = use_cwebp
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
                convert(entry.path, dest, self._quality, self._use_cwebp)
                size = Path(dest).stat().st_size
                self.file_done.emit(entry.path, size, "")
            except Exception as exc:
                self.file_done.emit(entry.path, -1, str(exc))
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

        # Add folder row
        folder_row = QHBoxLayout()
        add_folder_btn = QPushButton("Add Folder…")
        add_folder_btn.clicked.connect(self._pick_input_folder)
        folder_row.addWidget(add_folder_btn)
        self.subfolder_check = QCheckBox("Include subfolders")
        self.subfolder_check.setChecked(True)
        folder_row.addWidget(self.subfolder_check)
        folder_row.addStretch()
        layout.addLayout(folder_row)

        # Quality + cwebp row
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
        self.cwebp_check = QCheckBox("Use cwebp (if available)")
        self.cwebp_check.setEnabled(cwebp_available())
        if not cwebp_available():
            self.cwebp_check.setToolTip("cwebp not found on PATH")
        opts_row.addWidget(self.cwebp_check)
        if not HEIC_SUPPORTED:
            heic_label = QLabel("⚠ HEIC support unavailable (install pillow-heif)")
            heic_label.setStyleSheet("color: #f9a825; font-size: 11px;")
            opts_row.addSpacing(16)
            opts_row.addWidget(heic_label)
        opts_row.addStretch()
        layout.addLayout(opts_row)

        # Progress bar
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        layout.addWidget(self.progress_bar)

        # Summary label
        self.summary_label = QLabel("")
        self.summary_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.summary_label.setStyleSheet("color: #4caf50; font-size: 13px;")
        self.summary_label.setVisible(False)
        layout.addWidget(self.summary_label)

        # Action buttons row
        btn_row = QHBoxLayout()
        self.clear_btn = QPushButton("Clear List")
        self.clear_btn.clicked.connect(self._clear_list)
        btn_row.addWidget(self.clear_btn)
        btn_row.addStretch()
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

    def _start_conversion(self):
        entries = [e for e in self.file_list.entries() if e.status == "queued"]
        if not entries:
            QMessageBox.information(self, "Nothing to do", "No queued files to convert.")
            return

        quality = self.quality_slider.value()
        use_cwebp = self.cwebp_check.isChecked()

        self.crunch_btn.setEnabled(False)
        self.progress_bar.setRange(0, len(entries))
        self.progress_bar.setValue(0)
        self.progress_bar.setVisible(True)
        self.summary_label.setVisible(False)

        for e in entries:
            self.file_list.update_entry(e.path, status="processing")

        self._worker = ConversionWorker(entries, quality, use_cwebp)
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

    def _on_file_done(self, path: str, output_size: int, error: str):
        if error:
            self.file_list.update_entry(path, status="error", error_msg=error)
        else:
            self.file_list.update_entry(path, status="done", output_size=output_size)

    def _on_finished(self):
        self.crunch_btn.setEnabled(True)
        self._show_summary()

    def _show_summary(self):
        entries = self.file_list.entries()
        done = [e for e in entries if e.status == "done" and e.output_size is not None]
        errors = [e for e in entries if e.status == "error"]
        if not done:
            return
        total_in = sum(e.original_size for e in done)
        total_out = sum(e.output_size for e in done)
        saved = total_in - total_out
        pct = (saved / total_in * 100) if total_in else 0
        msg = (
            f"✅ {len(done)} file(s) converted  —  "
            f"{format_size(total_in)} → {format_size(total_out)}  "
            f"({pct:.1f}% saved)"
        )
        if errors:
            msg += f"  ⚠ {len(errors)} error(s)"
        self.summary_label.setText(msg)
        self.summary_label.setVisible(True)
