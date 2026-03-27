import json
import os
import hashlib
from dataclasses import dataclass, asdict, field
from typing import Optional
from datetime import datetime

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_FILE = os.path.join(BASE_DIR, "data", "items.json")


def _ensure_dirs():
    os.makedirs(os.path.dirname(DATA_FILE), exist_ok=True)


@dataclass
class Item:
    id: str
    url: str
    name: str
    purchase_price: Optional[float]
    current_price: Optional[float]
    image_url: Optional[str]
    added_at: str
    last_fetched: Optional[str] = None
    price_history: list = field(default_factory=list)

    def to_dict(self) -> dict:
        return asdict(self)

    @staticmethod
    def from_dict(d: dict) -> "Item":
        d = dict(d)
        d.setdefault("price_history", [])
        return Item(**d)


def make_item_id(appid: str, hash_name: str) -> str:
    h = hashlib.md5(hash_name.encode()).hexdigest()[:8]
    return f"{appid}_{h}"


def load_items() -> list:
    _ensure_dirs()
    if not os.path.exists(DATA_FILE):
        return []
    with open(DATA_FILE, "r", encoding="utf-8") as f:
        data = json.load(f)
    return [Item.from_dict(d) for d in data]


def save_items(items: list) -> None:
    _ensure_dirs()
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump([item.to_dict() for item in items], f, indent=2, ensure_ascii=False)
