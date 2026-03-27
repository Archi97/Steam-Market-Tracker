from PySide6.QtWidgets import (
    QWidget, QHBoxLayout, QLabel, QPushButton,
    QMessageBox, QInputDialog, QSizePolicy, QStackedWidget
)
from PySide6.QtGui import QPixmap, QPainter, QPen, QColor
from PySide6.QtCore import Qt, Signal, QTimer, QRect
from .price_graph import PriceGraph



class Spinner(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._angle = 0
        self._timer = QTimer(self)
        self._timer.timeout.connect(self._tick)

    def start(self):
        self._angle = 0
        self._timer.start(40)

    def stop(self):
        self._timer.stop()

    def _tick(self):
        self._angle = (self._angle + 15) % 360
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setPen(QPen(QColor("#5b8af4"), 2.5, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap))
        size = 18
        x = (self.width() - size) // 2
        y = (self.height() - size) // 2
        painter.drawArc(QRect(x, y, size, size), -self._angle * 16, 270 * 16)


class ClickableLabel(QLabel):
    clicked = Signal()

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.clicked.emit()
        super().mousePressEvent(event)


class ItemCard(QWidget):
    deleted = Signal(str)
    purchase_price_set = Signal(str, float)

    def __init__(self, item, parent=None):
        super().__init__(parent)
        self.item = item
        self.setObjectName("itemRow")
        self.setFixedHeight(80)
        self._build_ui()
        self.update_item(item)

    def _build_ui(self):
        layout = QHBoxLayout(self)
        layout.setContentsMargins(12, 8, 12, 8)
        layout.setSpacing(14)

        # Image
        self._img_label = QLabel()
        self._img_label.setFixedSize(64, 64)
        self._img_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._img_label.setObjectName("itemImage")
        self._img_label.setText("…")
        layout.addWidget(self._img_label)

        # Name (fixed width, wraps to 2 lines if long)
        self._name_label = QLabel()
        self._name_label.setObjectName("itemName")
        self._name_label.setWordWrap(True)
        self._name_label.setFixedWidth(190)
        layout.addWidget(self._name_label)

        # Purchase price (next to name)
        self._purchase_label = ClickableLabel()
        self._purchase_label.setFixedWidth(130)
        self._purchase_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._purchase_label.setObjectName("purchasePrice")
        self._purchase_label.clicked.connect(self._on_purchase_click)
        layout.addWidget(self._purchase_label)

        # Graph
        self._graph = PriceGraph()
        self._graph.setFixedSize(360, 56)
        layout.addWidget(self._graph)

        # Last sold price / spinner
        self._price_stack = QStackedWidget()
        self._price_stack.setFixedWidth(130)

        self._current_label = QLabel()
        self._current_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._current_label.setObjectName("currentPrice")
        self._price_stack.addWidget(self._current_label)   # index 0

        self._spinner = Spinner()
        self._price_stack.addWidget(self._spinner)          # index 1

        layout.addWidget(self._price_stack)

        # Delete button
        self._btn_delete = QPushButton("✕")
        self._btn_delete.setObjectName("btnDanger")
        self._btn_delete.setFixedSize(26, 26)
        self._btn_delete.clicked.connect(self._on_delete)
        layout.addWidget(self._btn_delete)

    def set_loading(self, loading: bool):
        if loading:
            self._price_stack.setCurrentIndex(1)
            self._spinner.start()
        else:
            self._spinner.stop()
            self._price_stack.setCurrentIndex(0)

    def set_image(self, pixmap):
        if pixmap and not pixmap.isNull():
            self._img_label.setPixmap(
                pixmap.scaled(64, 64, Qt.AspectRatioMode.KeepAspectRatio,
                              Qt.TransformationMode.SmoothTransformation)
            )

    def update_item(self, item):
        self.item = item

        self._name_label.setText(item.name or "Loading…")
        self._name_label.setToolTip(item.name or "")

        if item.purchase_price is not None:
            self._purchase_label.setText(f"${item.purchase_price:.2f} USD")
            self._purchase_label.setToolTip("Purchase price (cannot be changed)")
            self._purchase_label.setCursor(Qt.CursorShape.ArrowCursor)
            self._purchase_label.setStyleSheet("color: #aaaaaa;")
        else:
            self._purchase_label.setText("Set price")
            self._purchase_label.setToolTip("Click to set your purchase price")
            self._purchase_label.setCursor(Qt.CursorShape.PointingHandCursor)
            self._purchase_label.setStyleSheet("color: #5b8af4; text-decoration: underline;")

        if item.current_price is not None:
            if item.purchase_price is None:
                color = "#e8e8e8"
            elif item.current_price >= item.purchase_price:
                color = "#4caf50"
            else:
                color = "#f45b5b"
            self._current_label.setText(f"${item.current_price:.2f} USD")
            self._current_label.setStyleSheet(f"color: {color}; font-weight: 600;")
        else:
            self._current_label.setText("Loading…")
            self._current_label.setStyleSheet("color: #666666;")

        self._graph.set_data(item.price_history)

    def _on_delete(self):
        msg = QMessageBox(self)
        msg.setWindowTitle("Remove Item")
        msg.setText(f'Remove "{self.item.name}" from tracking?')
        msg.setStandardButtons(
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.Cancel
        )
        msg.setDefaultButton(QMessageBox.StandardButton.Cancel)
        if msg.exec() == QMessageBox.StandardButton.Yes:
            self.deleted.emit(self.item.id)

    def _on_purchase_click(self):
        if self.item.purchase_price is not None:
            return
        val, ok = QInputDialog.getDouble(
            self, "Set Purchase Price",
            "Enter the price you paid (USD):\n\n"
            "⚠  This cannot be changed once saved.",
            value=0.0, min=0.01, max=99999.99, decimals=2
        )
        if ok and val > 0:
            self.purchase_price_set.emit(self.item.id, val)
