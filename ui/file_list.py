from dataclasses import dataclass, field
from typing import Optional

from PyQt6.QtWidgets import (
    QTableWidget, QTableWidgetItem, QHeaderView, QAbstractItemView,
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QColor

from core.file_utils import format_size


@dataclass
class FileEntry:
    path: str
    original_size: int
    output_dir: Optional[str] = None
    output_size: Optional[int] = None
    status: str = "queued"   # queued | processing | done | error
    error_msg: str = ""


STATUS_ICONS = {
    "queued":     "⏳",
    "processing": "⚙️",
    "done":       "✅",
    "skipped":    "⏭",
    "error":      "❌",
}

STATUS_COLORS = {
    "queued":     QColor("#888888"),
    "processing": QColor("#00bcd4"),
    "done":       QColor("#4caf50"),
    "skipped":    QColor("#f9a825"),
    "error":      QColor("#f44336"),
}


class FileListWidget(QTableWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._entries: list[FileEntry] = []
        self.setColumnCount(5)
        self.setHorizontalHeaderLabels(["File", "Original", "Output", "Saved", "Status"])
        self.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        self.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        self.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        self.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)
        self.horizontalHeader().setSectionResizeMode(4, QHeaderView.ResizeMode.ResizeToContents)
        self.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.verticalHeader().setVisible(False)
        self.setAlternatingRowColors(True)
        self.setStyleSheet("""
            QTableWidget {
                background: #1e1e1e;
                alternate-background-color: #252525;
                color: #ddd;
                gridline-color: #333;
                border: 1px solid #333;
            }
            QHeaderView::section {
                background: #2a2a2a;
                color: #aaa;
                padding: 4px;
                border: none;
                border-bottom: 1px solid #444;
            }
        """)

    def entries(self) -> list[FileEntry]:
        return self._entries

    def add_entries(self, entries: list[FileEntry]):
        existing = {e.path for e in self._entries}
        for e in entries:
            if e.path not in existing:
                self._entries.append(e)
                existing.add(e.path)
        self._rebuild()

    def clear_entries(self):
        self._entries.clear()
        self.setRowCount(0)

    def update_entry(self, path: str, **kwargs):
        for e in self._entries:
            if e.path == path:
                for k, v in kwargs.items():
                    setattr(e, k, v)
                break
        self._rebuild()

    def _rebuild(self):
        self.setRowCount(len(self._entries))
        for row, e in enumerate(self._entries):
            from pathlib import Path
            name = Path(e.path).name
            orig = format_size(e.original_size)
            out = format_size(e.output_size) if e.output_size is not None else "—"
            saved = ""
            if e.output_size is not None and e.original_size > 0:
                pct = (1 - e.output_size / e.original_size) * 100
                saved = f"{pct:.1f}%"
            icon = STATUS_ICONS.get(e.status, "")
            tip = e.error_msg if e.status == "error" else ""

            cols = [name, orig, out, saved, icon]
            for col, text in enumerate(cols):
                item = QTableWidgetItem(text)
                item.setForeground(STATUS_COLORS.get(e.status, QColor("#ddd")))
                if tip and col == 4:
                    item.setToolTip(tip)
                self.setItem(row, col, item)
