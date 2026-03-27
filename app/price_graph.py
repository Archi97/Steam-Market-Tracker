from PySide6.QtWidgets import QWidget
from PySide6.QtGui import QPainter, QPen, QColor, QPainterPath, QLinearGradient, QFont
from PySide6.QtCore import Qt, QPointF


class PriceGraph(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("priceGraph")
        self.setMouseTracking(True)
        self._history = []
        self._prices = []
        self._hover_idx = -1

    def set_data(self, price_history):
        self._history = price_history or []
        self._prices = [row[1] for row in self._history]
        self._hover_idx = -1
        self.update()

    def mouseMoveEvent(self, event):
        if len(self._prices) < 2:
            self._hover_idx = -1
            self.update()
            return
        pad_x = 4
        w = self.width()
        mouse_x = event.position().x()
        step = (w - 2 * pad_x) / (len(self._prices) - 1)
        idx = round((mouse_x - pad_x) / step)
        idx = max(0, min(idx, len(self._prices) - 1))
        if idx != self._hover_idx:
            self._hover_idx = idx
            self.update()

    def leaveEvent(self, event):
        self._hover_idx = -1
        self.update()

    def paintEvent(self, event):
        if len(self._prices) < 2:
            painter = QPainter(self)
            painter.setPen(QColor("#333333"))
            painter.drawText(self.rect(), Qt.AlignmentFlag.AlignCenter, "No data")
            return

        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        w, h = self.width(), self.height()
        pad_x, pad_y = 4, 6
        data = self._prices
        n = len(data)
        min_p, max_p = min(data), max(data)
        if max_p == min_p:
            max_p += 0.01

        def px(i):
            return pad_x + i / (n - 1) * (w - 2 * pad_x)

        def py(p):
            return h - pad_y - (p - min_p) / (max_p - min_p) * (h - 2 * pad_y)

        # Fill
        fill = QPainterPath()
        fill.moveTo(px(0), h)
        for i, p in enumerate(data):
            fill.lineTo(px(i), py(p))
        fill.lineTo(px(n - 1), h)
        fill.closeSubpath()
        grad = QLinearGradient(0, 0, 0, h)
        grad.setColorAt(0, QColor(91, 138, 244, 60))
        grad.setColorAt(1, QColor(91, 138, 244, 0))
        painter.fillPath(fill, grad)

        # Line
        path = QPainterPath()
        path.moveTo(px(0), py(data[0]))
        for i in range(1, n):
            path.lineTo(px(i), py(data[i]))
        painter.setPen(QPen(QColor("#5b8af4"), 1.5, Qt.PenStyle.SolidLine,
                            Qt.PenCapStyle.RoundCap, Qt.PenJoinStyle.RoundJoin))
        painter.drawPath(path)

        # Last price dot
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QColor("#5b8af4"))
        painter.drawEllipse(QPointF(px(n - 1), py(data[-1])), 3, 3)

        # Hover indicator
        if 0 <= self._hover_idx < n:
            hx = px(self._hover_idx)
            hy = py(data[self._hover_idx])
            price = data[self._hover_idx]
            date_str = self._history[self._hover_idx][0][:12].strip() if self._history else ""

            # Vertical line
            painter.setPen(QPen(QColor("#ffffff40"), 1, Qt.PenStyle.DashLine))
            painter.drawLine(QPointF(hx, pad_y), QPointF(hx, h - pad_y))

            # Dot
            painter.setPen(QPen(QColor("#ffffff"), 1.5))
            painter.setBrush(QColor("#1a1a1a"))
            painter.drawEllipse(QPointF(hx, hy), 4, 4)

            # Tooltip box
            label = f"${price:.2f}"
            if date_str:
                label = f"{date_str}\n{label}"

            font = QFont("Segoe UI", 8)
            painter.setFont(font)
            fm = painter.fontMetrics()
            lines = label.split("\n")
            box_w = max(fm.horizontalAdvance(l) for l in lines) + 10
            box_h = fm.height() * len(lines) + 6
            box_x = hx - box_w / 2
            box_y = pad_y - box_h - 2

            # keep inside widget
            box_x = max(2, min(box_x, w - box_w - 2))
            box_y = max(2, box_y)

            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(QColor("#2a2a2a"))
            painter.drawRoundedRect(int(box_x), int(box_y), int(box_w), int(box_h), 4, 4)

            painter.setPen(QColor("#e8e8e8"))
            for i, line in enumerate(lines):
                painter.drawText(
                    int(box_x + 5),
                    int(box_y + fm.ascent() + 3 + i * fm.height()),
                    line
                )
