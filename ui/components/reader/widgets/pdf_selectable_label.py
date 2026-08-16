import pymupdf as fitz
from PySide6.QtWidgets import QLabel
from PySide6.QtGui import QPainter, QPen, QColor
from PySide6.QtCore import Qt, QPoint, QRect, Signal

from ui.components.reader.utils import flatten_chars, nearest_char_flat_index, build_selection_segments

class PDFSelectableLabel(QLabel):
    area_selected = Signal(list, str)
    point_clicked = Signal(QPoint)

    def __init__(self, text=""):
        super().__init__(text)
        self.selection_start = None
        self.selection_end = None
        self.is_selecting = False
        self.selected_color = "#FFFF00"
        
        self.char_lines = []
        self.flat_chars = []
        self.zoom = 1.0
        self.anchor_idx = None
        self.focus_idx = None
        self.preview_segments = []

    def set_selection_color(self, hex_color: str):
        self.selected_color = hex_color

    def set_char_layout(self, lines, zoom):
        self.char_lines = lines
        self.flat_chars = flatten_chars(lines)
        self.zoom = zoom if zoom > 0 else 1.0

    def _screen_to_pdf(self, pt: QPoint):
        return fitz.Point(pt.x() / self.zoom, pt.y() / self.zoom)

    def keyPressEvent(self, event):
        if event.key() == Qt.Key_Escape:
            self.setCursor(Qt.IBeamCursor)
            event.accept()
        else:
            super().keyPressEvent(event)

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.selection_start = event.position().toPoint()
            self.selection_end = self.selection_start
            self.is_selecting = True
            self.anchor_idx = nearest_char_flat_index(
                self.flat_chars, self._screen_to_pdf(self.selection_start)
            )
            self.focus_idx = self.anchor_idx
            self.preview_segments = []
            self.update()

    def mouseMoveEvent(self, event):
        if self.is_selecting and self.flat_chars:
            self.selection_end = event.position().toPoint()
            self.focus_idx = nearest_char_flat_index(
                self.flat_chars, self._screen_to_pdf(self.selection_end)
            )
            segments_pdf, _ = build_selection_segments(
                self.flat_chars, self.anchor_idx, self.focus_idx
            )
            self.preview_segments = [
                QRect(
                    int(r.x0 * self.zoom),
                    int(r.y0 * self.zoom),
                    int((r.x1 - r.x0) * self.zoom),
                    int((r.y1 - r.y0) * self.zoom)
                ) for r in segments_pdf
            ]
            self.update()

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.LeftButton and self.is_selecting:
            self.is_selecting = False
            self.selection_end = event.position().toPoint()
            
            self.focus_idx = nearest_char_flat_index(
                self.flat_chars, self._screen_to_pdf(self.selection_end)
            )
            segments_pdf, text = build_selection_segments(
                self.flat_chars, self.anchor_idx, self.focus_idx
            )
            
            if segments_pdf and text.strip():
                self.area_selected.emit(segments_pdf, text)
            elif self.anchor_idx == self.focus_idx and (self.selection_start - self.selection_end).manhattanLength() <= 2:
                self.point_clicked.emit(self.selection_start)

            self.selection_start = None
            self.selection_end = None
            self.anchor_idx = None
            self.focus_idx = None
            self.preview_segments = []
            self.update()

    def paintEvent(self, event):
        super().paintEvent(event)
        if self.is_selecting and self.preview_segments:
            painter = QPainter(self)
            fill_color = QColor(self.selected_color)
            fill_color.setAlpha(80)
            painter.setPen(QPen(fill_color.darker(120), 1, Qt.PenStyle.SolidLine))
            painter.setBrush(fill_color)
            for seg in self.preview_segments:
                painter.drawRect(seg)