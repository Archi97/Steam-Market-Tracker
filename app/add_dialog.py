from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
    QPushButton, QDoubleSpinBox, QWidget
)
from PySide6.QtCore import Qt


class AddItemDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Add Item")
        self.setModal(True)
        self.setMinimumWidth(440)
        self._build_ui()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(10)
        layout.setContentsMargins(24, 24, 24, 24)

        # URL
        lbl_url = QLabel("STEAM MARKET URL")
        lbl_url.setObjectName("sectionLabel")
        layout.addWidget(lbl_url)

        self._url_input = QLineEdit()
        self._url_input.setPlaceholderText(
            "https://steamcommunity.com/market/listings/730/..."
        )
        layout.addWidget(self._url_input)

        hint = QLabel(
            "Paste the full URL from a Steam Community Market listing page."
        )
        hint.setObjectName("hintLabel")
        hint.setWordWrap(True)
        layout.addWidget(hint)

        # Spacer
        layout.addSpacing(8)

        # Purchase price
        lbl_price = QLabel("BOUGHT FOR (USD)")
        lbl_price.setObjectName("sectionLabel")
        layout.addWidget(lbl_price)

        self._price_input = QDoubleSpinBox()
        self._price_input.setPrefix("$ ")
        self._price_input.setDecimals(2)
        self._price_input.setMinimum(0.0)
        self._price_input.setMaximum(99999.99)
        self._price_input.setValue(0.0)
        self._price_input.setSpecialValueText("Not specified")
        layout.addWidget(self._price_input)

        price_warn = QLabel(
            "⚠  Once saved, the purchase price cannot be changed."
        )
        price_warn.setObjectName("hintLabel")
        price_warn.setWordWrap(True)
        layout.addWidget(price_warn)

        layout.addSpacing(12)

        # Buttons
        btn_row = QHBoxLayout()
        btn_row.addStretch()

        self._btn_cancel = QPushButton("Cancel")
        self._btn_cancel.setObjectName("btnGhost")
        self._btn_cancel.clicked.connect(self.reject)
        btn_row.addWidget(self._btn_cancel)

        self._btn_add = QPushButton("Add Item")
        self._btn_add.setObjectName("btnPrimary")
        self._btn_add.clicked.connect(self._on_add)
        btn_row.addWidget(self._btn_add)

        layout.addLayout(btn_row)

    def _on_add(self):
        if not self._url_input.text().strip():
            self._url_input.setFocus()
            return
        self.accept()

    def get_url(self) -> str:
        return self._url_input.text().strip()

    def get_purchase_price(self):
        val = self._price_input.value()
        return val if val > 0.0 else None
