import re
import json
import requests
from urllib.parse import urlparse, unquote

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
}
HISTORY_POINTS = 300


def parse_url(url: str) -> tuple:
    """Extract (appid, market_hash_name) from a Steam market URL."""
    path = urlparse(url).path
    match = re.match(r"/market/listings/(\d+)/(.+)", path)
    if not match:
        raise ValueError(
            "Invalid Steam market URL.\n"
            "Expected: https://steamcommunity.com/market/listings/{appid}/{item_name}"
        )
    return match.group(1), unquote(match.group(2))


def fetch_listing(url: str) -> dict:
    """
    Fetch the Steam market listing page and parse:
      - name
      - image_url
      - price_history  (last 336 hourly points: [[date, price, volume], ...])
      - current_price  (latest price from history)
    """
    r = requests.get(url, headers=HEADERS, timeout=15)
    r.raise_for_status()
    html = r.text

    # Name
    name = None
    m = re.search(r'<a[^>]+market/listings/\d+/[^"]*">([^<]+)</a>', html)
    if m:
        name = m.group(1).strip()

    # Image URL — id pattern varies (mypurchase_0_image, listing_..._image, etc.)
    image_url = None
    m = re.search(r'<img[^>]+id="[^"]+_image"[^>]+src="([^"]+)"', html)
    if m:
        image_url = m.group(1)


    # Price history
    price_history = []
    m = re.search(r'var line1=(\[.*?\]);', html, re.DOTALL)
    if m:
        data = json.loads(m.group(1))
        price_history = data[-HISTORY_POINTS:]

    current_price = price_history[-1][1] if price_history else None

    return {
        "name": name,
        "image_url": image_url,
        "price_history": price_history,
        "current_price": current_price,
    }


def fetch_image_bytes(image_url: str) -> bytes:
    """Download image bytes from URL."""
    try:
        r = requests.get(image_url, headers=HEADERS, timeout=10)
        r.raise_for_status()
        return r.content
    except Exception:
        return None
