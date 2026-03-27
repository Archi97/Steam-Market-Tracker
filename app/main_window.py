from datetime import datetime
from version import VERSION
from PySide6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QPushButton, QLabel, QScrollArea, QMessageBox, QDialog, QSizePolicy
)
from PySide6.QtCore import Qt, QThread, QTimer
from PySide6.QtGui import QPixmap, QColor

from . import steam_api
from .models import Item, load_items, save_items, make_item_id
from .fetcher import AddItemWorker, ImageLoader, PriceFetcher, seconds_until_next_hour
from .item_card import ItemCard
from .add_dialog import AddItemDialog


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Steam Market Tracker")
        self.setMinimumSize(1020, 600)
        self.resize(1100, 720)

        self.items = load_items()
        self._cards: dict = {}
        self._image_cache: dict = {}
        self._workers = []          # (thread, worker) — holds references until thread.finished
        self._fetch_thread = None
        self._fetcher = None

        self._hue = 0.0
        self._build_ui()
        self._rebuild_grid()
        self._load_existing_images()
        self._schedule_fetch(immediate=True)

        self._color_timer = QTimer(self)
        self._color_timer.timeout.connect(self._cycle_color)
        self._color_timer.start(50)

    # ── UI ──────────────────────────────────────────────────────────────────

    def _build_ui(self):
        central = QWidget()
        central.setObjectName("centralWidget")
        self.setCentralWidget(central)
        root = QVBoxLayout(central)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        # Toolbar
        toolbar = QWidget()
        toolbar.setObjectName("toolbar")
        toolbar.setFixedHeight(50)
        tbl = QHBoxLayout(toolbar)
        tbl.setContentsMargins(18, 0, 18, 0)
        tbl.setSpacing(12)
        tbl.setAlignment(Qt.AlignmentFlag.AlignVCenter)

        left_bal = QWidget()
        left_bal.setFixedWidth(230)
        tbl.addWidget(left_bal)

        tbl.addStretch()

        btn_add = QPushButton("+ Add Item")
        btn_add.setObjectName("btnPrimary")
        btn_add.clicked.connect(self._on_add)
        tbl.addWidget(btn_add)

        tbl.addStretch()

        self._credit = QLabel(
            f'v{VERSION} · by Tyombo &nbsp;·&nbsp; '
            f'<a href="https://www.buymeacoffee.com/tyombo" '
            f'style="color:#f5a623; text-decoration:none;">☕ Buy me a coffee</a>'
        )
        self._credit.setOpenExternalLinks(True)
        self._credit.setObjectName("creditLabel")
        self._credit.setFixedWidth(230)
        self._credit.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        tbl.addWidget(self._credit)

        # Column headers
        col_header = QWidget()
        col_header.setObjectName("columnHeader")
        col_header.setFixedHeight(34)
        ch = QHBoxLayout(col_header)
        ch.setContentsMargins(12, 0, 12, 0)
        ch.setSpacing(14)

        spc = QWidget()
        spc.setFixedWidth(64)
        ch.addWidget(spc)

        lbl_item = QLabel("ITEM")
        lbl_item.setObjectName("sectionLabel")
        lbl_item.setFixedWidth(190)
        ch.addWidget(lbl_item)

        lbl_paid = QLabel("PAID")
        lbl_paid.setObjectName("sectionLabel")
        lbl_paid.setFixedWidth(130)
        lbl_paid.setAlignment(Qt.AlignmentFlag.AlignCenter)
        ch.addWidget(lbl_paid)

        lbl_graph = QLabel("PRICE HISTORY")
        lbl_graph.setObjectName("sectionLabel")
        lbl_graph.setFixedWidth(360)
        lbl_graph.setAlignment(Qt.AlignmentFlag.AlignCenter)
        ch.addWidget(lbl_graph)

        lbl_cur = QLabel("LAST SOLD")
        lbl_cur.setObjectName("sectionLabel")
        lbl_cur.setFixedWidth(130)
        lbl_cur.setAlignment(Qt.AlignmentFlag.AlignCenter)
        ch.addWidget(lbl_cur)

        spc2 = QWidget()
        spc2.setFixedWidth(26)
        ch.addWidget(spc2)

        root.addWidget(col_header)
        root.addWidget(self._make_sep())

        # Scroll area
        self._scroll = QScrollArea()
        self._scroll.setWidgetResizable(True)
        self._scroll.setObjectName("scrollArea")

        self._list_widget = QWidget()
        self._list_widget.setObjectName("listWidget")
        self._list_layout = QVBoxLayout(self._list_widget)
        self._list_layout.setContentsMargins(0, 0, 0, 0)
        self._list_layout.setSpacing(0)
        self._list_layout.setAlignment(Qt.AlignmentFlag.AlignTop)

        self._scroll.setWidget(self._list_widget)
        root.addWidget(self._scroll)
        root.addWidget(self._make_sep())
        root.addWidget(toolbar)

    def _make_sep(self):
        s = QWidget()
        s.setFixedHeight(1)
        s.setObjectName("separator")
        return s

    def _rebuild_grid(self):
        while self._list_layout.count():
            w = self._list_layout.takeAt(0)
            if w.widget():
                w.widget().setParent(None)
        self._cards.clear()

        if not self.items:
            empty = QLabel('No items tracked yet.\nClick "+ Add Item" to get started.')
            empty.setObjectName("emptyLabel")
            empty.setAlignment(Qt.AlignmentFlag.AlignCenter)
            self._list_layout.addWidget(empty)
            return

        for item in self.items:
            card = ItemCard(item)
            card.deleted.connect(self._on_delete)
            card.purchase_price_set.connect(self._on_purchase_set)
            self._cards[item.id] = card
            self._list_layout.addWidget(card)
            self._list_layout.addWidget(self._make_sep())

        for item_id, pix in self._image_cache.items():
            if item_id in self._cards:
                self._cards[item_id].set_image(pix)


    # ── Thread helpers ───────────────────────────────────────────────────────

    def _start_thread(self, worker, on_finished=None):
        """Start worker in a new QThread.
        - worker.done  → thread.quit      (worker signals it's done)
        - thread.finished → cleanup       (fires after thread truly stops)
        """
        thread = QThread()
        worker.moveToThread(thread)
        thread.started.connect(worker.run)
        worker.done.connect(thread.quit)
        def _cleanup():
            self._workers = [(t, w) for t, w in self._workers if t is not thread]
            if on_finished:
                on_finished()
        thread.finished.connect(_cleanup)
        self._workers.append((thread, worker))
        thread.start()
        return thread

    # ── Add item ─────────────────────────────────────────────────────────────

    def _on_add(self):
        dlg = AddItemDialog(self)
        if dlg.exec() != QDialog.DialogCode.Accepted:
            return

        url = dlg.get_url()
        purchase_price = dlg.get_purchase_price()

        try:
            appid, hash_name = steam_api.parse_url(url)
        except ValueError as e:
            QMessageBox.warning(self, "Invalid URL", str(e))
            return

        item_id = make_item_id(appid, hash_name)
        if any(i.id == item_id for i in self.items):
            QMessageBox.information(self, "Already Tracking", "This item is already in your list.")
            return

        item = Item(
            id=item_id, url=url, name=hash_name,
            purchase_price=purchase_price, current_price=None,
            image_url=None,
            added_at=datetime.now().isoformat(timespec="seconds"),
        )
        self.items.append(item)
        save_items(self.items)
        self._rebuild_grid()
        self._set_status("Fetching item info…")

        worker = AddItemWorker(item)
        worker.finished.connect(self._on_item_fetched)
        worker.error.connect(lambda e: self._set_status(f"Error: {e[:60]}"))
        self._start_thread(worker)

    def _on_item_fetched(self, updated, image_bytes):
        for i, item in enumerate(self.items):
            if item.id == updated.id:
                self.items[i] = updated
                break
        save_items(self.items)
        if updated.id in self._cards:
            self._cards[updated.id].update_item(updated)
            if image_bytes:
                self._set_image_from_bytes(updated.id, image_bytes)
        self._set_status("Ready")

    # ── Delete / purchase price ──────────────────────────────────────────────

    def _on_delete(self, item_id):
        self.items = [i for i in self.items if i.id != item_id]
        save_items(self.items)
        self._rebuild_grid()

    def _on_purchase_set(self, item_id, price):
        for item in self.items:
            if item.id == item_id:
                item.purchase_price = price
                break
        save_items(self.items)
        if item_id in self._cards:
            for item in self.items:
                if item.id == item_id:
                    self._cards[item_id].update_item(item)
                    break

    # ── Price fetching ───────────────────────────────────────────────────────

    def _schedule_fetch(self, immediate=False):
        if immediate:
            QTimer.singleShot(800, self._start_price_fetch)
        secs = seconds_until_next_hour()
        QTimer.singleShot(int(secs * 1000), self._on_hourly_fetch)

    def _on_hourly_fetch(self):
        self._start_price_fetch()
        QTimer.singleShot(3600 * 1000, self._on_hourly_fetch)

    def _start_price_fetch(self):
        if not self.items:
            return
        if self._fetch_thread and self._fetch_thread.isRunning():
            return
        self._set_status("Updating prices…")
        for card in self._cards.values():
            card.set_loading(True)
        fetcher = PriceFetcher(list(self.items), delay=3.0)
        fetcher.item_updated.connect(self._on_price_updated)
        fetcher.done.connect(self._on_all_fetched)

        def _on_done():
            self._fetch_thread = None
            self._fetcher = None

        self._fetcher = fetcher
        self._fetch_thread = self._start_thread(fetcher, on_finished=_on_done)

    def _on_all_fetched(self):
        for card in self._cards.values():
            card.set_loading(False)
        self._set_status(f"Updated at {datetime.now().strftime('%H:%M')}")

    def _on_price_updated(self, item_id, price, price_history, image_url):
        now = datetime.now().isoformat(timespec="seconds")
        for item in self.items:
            if item.id == item_id:
                item.current_price = price
                item.price_history = price_history
                item.last_fetched = now
                if not item.image_url and image_url:
                    item.image_url = image_url
                break
        save_items(self.items)
        if item_id in self._cards:
            for item in self.items:
                if item.id == item_id:
                    self._cards[item_id].update_item(item)
                    self._cards[item_id].set_loading(False)
                    break
        if image_url and item_id not in self._image_cache:
            self._load_image(item_id, image_url)

    # ── Image loading ────────────────────────────────────────────────────────

    def _load_existing_images(self):
        for item in self.items:
            if item.image_url and item.id not in self._image_cache:
                self._load_image(item.id, item.image_url)

    def _load_image(self, item_id, image_url):
        loader = ImageLoader(item_id, image_url)
        loader.loaded.connect(self._on_image_loaded)
        self._start_thread(loader)

    def _on_image_loaded(self, item_id, image_bytes):
        if image_bytes:
            self._set_image_from_bytes(item_id, image_bytes)

    def _set_image_from_bytes(self, item_id, image_bytes):
        pix = QPixmap()
        pix.loadFromData(image_bytes)
        if not pix.isNull():
            self._image_cache[item_id] = pix
            if item_id in self._cards:
                self._cards[item_id].set_image(pix)

    def _cycle_color(self) -> None:
        self._hue = (self._hue + 0.012) % 1.0
        color = QColor.fromHsvF(self._hue, 0.85, 1.0)
        self._credit.setStyleSheet(f"color: {color.name()}; font-weight: 600; font-size: 11px;")

    def _set_status(self, *_):
        pass
