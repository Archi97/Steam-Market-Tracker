import time
from datetime import datetime, timedelta
from PySide6.QtCore import QObject, Signal, Slot
from . import steam_api


class AddItemWorker(QObject):
    finished = Signal(object, object)   # (Item, bytes | None)
    error = Signal(str)
    done = Signal()                     # always emitted last — triggers thread.quit

    def __init__(self, item):
        super().__init__()
        self.item = item

    @Slot()
    def run(self):
        try:
            result = steam_api.fetch_listing(self.item.url)
            self.item.name = result["name"] or self.item.name
            self.item.image_url = result["image_url"]
            self.item.price_history = result["price_history"]
            self.item.current_price = result["current_price"]

            image_bytes = None
            if result["image_url"]:
                image_bytes = steam_api.fetch_image_bytes(result["image_url"])

            self.finished.emit(self.item, image_bytes)
        except Exception as e:
            self.error.emit(str(e))
        finally:
            self.done.emit()


class ImageLoader(QObject):
    loaded = Signal(str, object)    # (item_id, bytes | None)
    done = Signal()

    def __init__(self, item_id, image_url):
        super().__init__()
        self.item_id = item_id
        self.image_url = image_url

    @Slot()
    def run(self):
        data = steam_api.fetch_image_bytes(self.image_url)
        self.loaded.emit(self.item_id, data)
        self.done.emit()


class PriceFetcher(QObject):
    item_updated = Signal(str, object, object, object)  # item_id, price, price_history, image_url
    done = Signal()

    def __init__(self, items, delay=3.0):
        super().__init__()
        self.items = items
        self.delay = delay

    @Slot()
    def run(self):
        for item in self.items:
            try:
                result = steam_api.fetch_listing(item.url)
                if result["current_price"] is not None:
                    self.item_updated.emit(
                        item.id,
                        result["current_price"],
                        result["price_history"],
                        result["image_url"],
                    )
            except Exception:
                pass
            time.sleep(self.delay)
        self.done.emit()


def seconds_until_next_hour() -> float:
    now = datetime.now()
    next_hour = (now + timedelta(hours=1)).replace(minute=0, second=0, microsecond=0)
    return max((next_hour - now).total_seconds(), 1.0)
