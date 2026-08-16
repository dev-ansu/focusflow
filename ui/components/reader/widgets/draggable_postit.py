from PySide6.QtWidgets import QFrame
from PySide6.QtCore import Qt, QPoint

class DraggablePostIt(QFrame):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.drag_position = QPoint()
        self.resizing = False
        self.resize_edge = None
        self.margin = 8

        self.setMinimumSize(200, 150)
        self.setMaximumSize(500, 400)
        self.setMouseTracking(True)

    def keyPressEvent(self, event):
        if event.key() == Qt.Key_Escape:
            self.hide()
            event.accept()
        else:
            super().keyPressEvent(event)

    def _get_edge(self, pos):
        edge = 0
        rect = self.rect()

        if pos.x() <= self.margin:
            edge |= 1
        elif pos.x() >= rect.width() - self.margin:
            edge |= 2

        if pos.y() <= self.margin:
            edge |= 4
        elif pos.y() >= rect.height() - self.margin:
            edge |= 8

        return edge

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            edge = self._get_edge(event.position().toPoint())
            if edge != 0:
                self.resizing = True
                self.resize_edge = edge
            else:
                self.resizing = False
                self.drag_position = event.globalPosition().toPoint() - self.frameGeometry().topLeft()
            event.accept()

    def mouseMoveEvent(self, event):
        pos = event.position().toPoint()

        if not self.resizing and not (event.buttons() & Qt.LeftButton):
            edge = self._get_edge(pos)
            if edge in (3, 12):
                self.setCursor(Qt.SizeHorCursor)
            elif edge in (5, 10):
                self.setCursor(Qt.SizeFDiagCursor)
            elif edge in (6, 9):
                self.setCursor(Qt.SizeBDiagCursor)
            elif edge & (4 | 8):
                self.setCursor(Qt.SizeVerCursor)
            else:
                self.setCursor(Qt.OpenHandCursor)
            return

        if self.resizing and (event.buttons() & Qt.LeftButton):
            global_pos = event.globalPosition().toPoint()
            geom = self.geometry()

            if self.resize_edge & 2:
                new_w = max(self.minimumWidth(), min(global_pos.x() - geom.left(), self.maximumWidth()))
                geom.setWidth(new_w)

            if self.resize_edge & 8:
                new_h = max(self.minimumHeight(), min(global_pos.y() - geom.top(), self.maximumHeight()))
                geom.setHeight(new_h)

            self.setGeometry(geom)
            event.accept()

        elif event.buttons() & Qt.LeftButton:
            self.move(event.globalPosition().toPoint() - self.drag_position)
            event.accept()

    def mouseReleaseEvent(self, event):
        self.resizing = False
        self.setCursor(Qt.OpenHandCursor)
        super().mouseReleaseEvent(event)