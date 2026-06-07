from PyQt6.QtWidgets import QWidget, QLabel, QVBoxLayout, QFileDialog
from PyQt6.QtCore import Qt, pyqtSignal, QByteArray
from PyQt6.QtGui import QDragEnterEvent, QDropEvent, QMouseEvent, QPixmap, QPainter
from PyQt6.QtSvg import QSvgRenderer


# Simple "image + up-arrow" icon — clean, scalable, no external files
_ICON_SVG = b"""
<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 64 64">
  <!-- image frame -->
  <rect x="6" y="12" width="52" height="38" rx="4" ry="4"
        fill="none" stroke="#555" stroke-width="3.5"/>
  <!-- sun -->
  <circle cx="20" cy="24" r="5" fill="#555"/>
  <!-- mountains -->
  <polyline points="6,50 22,30 34,42 44,34 58,50"
            fill="none" stroke="#555" stroke-width="3" stroke-linejoin="round"/>
  <!-- upload arrow -->
  <line x1="32" y1="58" x2="32" y2="44" stroke="#555" stroke-width="3.5" stroke-linecap="round"/>
  <polyline points="25,51 32,44 39,51"
            fill="none" stroke="#555" stroke-width="3.5"
            stroke-linecap="round" stroke-linejoin="round"/>
</svg>
"""

_ICON_SVG_ACTIVE = _ICON_SVG.replace(b'stroke="#555"', b'stroke="#00bcd4"').replace(b'fill="#555"', b'fill="#00bcd4"')


def _render_svg(svg_bytes: bytes, size: int) -> QPixmap:
    renderer = QSvgRenderer(QByteArray(svg_bytes))
    pm = QPixmap(size, size)
    pm.fill(Qt.GlobalColor.transparent)
    painter = QPainter(pm)
    renderer.render(painter)
    painter.end()
    return pm


class DropZone(QWidget):
    files_dropped = pyqtSignal(list)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAcceptDrops(True)
        self.setMinimumHeight(160)

        layout = QVBoxLayout(self)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.setSpacing(8)

        self._icon_label = QLabel()
        self._icon_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._icon_label.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        layout.addWidget(self._icon_label)

        self._text_label = QLabel("Drop images or folders here\nor click to browse")
        self._text_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._text_label.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        layout.addWidget(self._text_label)

        self._pm_normal = _render_svg(_ICON_SVG, 64)
        self._pm_active = _render_svg(_ICON_SVG_ACTIVE, 64)
        self._apply_style(False)

    def _apply_style(self, active: bool):
        border_color = "#00bcd4" if active else "#555"
        self.setStyleSheet(f"""
            DropZone {{
                border: 2px dashed {border_color};
                border-radius: 10px;
                background: #1e1e1e;
            }}
            QLabel {{
                border: none;
                background: transparent;
                color: {'#00bcd4' if active else '#aaa'};
                font-size: 15px;
            }}
        """)
        self._icon_label.setPixmap(self._pm_active if active else self._pm_normal)

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
                "Images (*.jpg *.jpeg *.png *.gif *.bmp *.tiff *.tif *.heic *.webp)",
            )
            if paths:
                self.files_dropped.emit(paths)
