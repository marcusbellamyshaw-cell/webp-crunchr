from PyQt6.QtWidgets import QLabel, QFileDialog
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QDragEnterEvent, QDropEvent, QMouseEvent


class DropZone(QLabel):
    # Emits raw paths — files AND directories. MainWindow expands directories.
    files_dropped = pyqtSignal(list)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setText("Drop images or folders here\nor click to browse")
        self.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.setAcceptDrops(True)
        self.setMinimumHeight(160)
        self._apply_style(False)

    def _apply_style(self, active: bool):
        border_color = "#00bcd4" if active else "#555"
        self.setStyleSheet(f"""
            QLabel {{
                border: 2px dashed {border_color};
                border-radius: 10px;
                color: #aaa;
                font-size: 16px;
                background: #1e1e1e;
            }}
        """)

    def dragEnterEvent(self, event: QDragEnterEvent):
        if event.mimeData().hasUrls():
            event.acceptProposedAction()
            self._apply_style(True)
        else:
            event.ignore()

    def dragLeaveEvent(self, event):
        self._apply_style(False)

    def dropEvent(self, event: QDropEvent):
        self._apply_style(False)
        paths = [u.toLocalFile() for u in event.mimeData().urls()]
        if paths:
            self.files_dropped.emit(paths)

    def mousePressEvent(self, event: QMouseEvent):
        if event.button() == Qt.MouseButton.LeftButton:
            paths, _ = QFileDialog.getOpenFileNames(
                self,
                "Select Images",
                "",
                "Images (*.jpg *.jpeg *.png *.gif *.bmp *.tiff *.tif *.heic)",
            )
            if paths:
                self.files_dropped.emit(paths)
