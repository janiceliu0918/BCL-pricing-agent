"""
BCL Liquor Stores – Price API Client
Endpoint: POST https://www.bcliquorstores.com/ajax/browse
"""

import json
import time
import urllib.request
import urllib.parse
from typing import Optional

BASE_URL  = "https://www.bcliquorstores.com/ajax/browse"
PAGE_SIZE = 24

# Maps keywords found in WHS product descriptions → BCL search terms
WINE_TYPE_MAP = {
    "BARBARESCO":         "BARBARESCO",
    "BAROLO":             "BAROLO",
    "CHIANTI":            "CHIANTI",
    "TOSCANA":            "TOSCANA",
    "TUSCAN":             "TOSCANA",
    "BRUNELLO":           "BRUNELLO",
    "AMARONE":            "AMARONE",
    "COTES DU RHONE":     "COTES DU RHONE",
    "CÔTES DU RHÔNE":     "COTES DU RHONE",
    "RIBERA DEL DUERO":   "RIBERA DEL DUERO",
    "RIOJA":              "RIOJA",
    "PRIORAT":            "PRIORAT",
    "CHAMPAGNE":          "CHAMPAGNE",
    "PROSECCO":           "PROSECCO",
    "BORDEAUX":           "BORDEAUX",
    "BURGUNDY":           "BURGUNDY",
    "CHARDONNAY":         "CHARDONNAY",
    "PINOT NOIR":         "PINOT NOIR",
    "CABERNET SAUVIGNON": "CABERNET SAUVIGNON",
    "CABERNET SAU":       "CABERNET SAUVIGNON",
    "MALBEC":             "MALBEC",
    "SAUVIGNON BLANC":    "SAUVIGNON BLANC",
    "PINOT GRIGIO":       "PINOT GRIGIO",
    "PINOT GRIS":         "PINOT GRIS",
    "RIESLING":           "RIESLING",
    "SANGIOVESE":         "SANGIOVESE",
    "NEBBIOLO":           "NEBBIOLO",
    "SYRAH":              "SYRAH",
    "SHIRAZ":             "SHIRAZ",
    "GRENACHE":           "GRENACHE",
    "GARNACHA":           "GRENACHE",
}

# Categories not matchable to BCL wine catalog
NON_WINE_KEYWORDS = [
    "LANGJIU", "HONGHUA", "SHAOXING", "MAOTAI", "BAIJIU",
    "WHISKY", "WHISKEY", "VODKA", "GIN", "RUM", "TEQUILA",
    "SAKE", "MIRIN", "LIQUEUR",
]


def _post(params: dict, body: dict = None, timeout: int = 20) -> dict:
    qs  = urllib.parse.urlencode(params)
    url = f"{BASE_URL}?{qs}"
    req = urllib.request.Request(
        url,
        data=json.dumps(body or {}).encode(),
        headers={
            "Content-Type":     "application/json",
            "X-Requested-With": "XMLHttpRequest",
            "User-Agent":       "Mozilla/5.0 BCLPriceAgent/1.0",
        },
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.loads(r.read())


def fetch_all_wines(page_delay: float = 0.15,
                    progress_cb=None) -> list:
    """
    Fetch the complete BCL wine catalogue.
    Returns a flat list of product dicts (_source objects).
    """
    first = _post({"category": "wine", "sort": "name.raw:asc", "page": 1})
    total = first["hits"]["total"]
    hits  = list(first["hits"]["hits"])
    pages = (total + PAGE_SIZE - 1) // PAGE_SIZE

    if progress_cb:
        progress_cb(1, pages, len(hits))

    for page in range(2, pages + 1):
        data = _post({"category": "wine", "sort": "name.raw:asc", "page": page})
        hits.extend(data["hits"]["hits"])
        time.sleep(page_delay)
        if progress_cb:
            progress_cb(page, pages, len(hits))

    return [h["_source"] for h in hits]


def detect_wine_type(description: str) -> Optional[str]:
    """Return the BCL search keyword for a product description, or None."""
    desc_up = description.upper()
    for kw, bcl_term in WINE_TYPE_MAP.items():
        if kw in desc_up:
            return bcl_term
    return None


def is_non_wine(description: str) -> bool:
    desc_up = description.upper()
    return any(kw in desc_up for kw in NON_WINE_KEYWORDS)


def filter_by_keyword(wines: list, keyword: str) -> list:
    """Filter wine list where keyword appears in product name."""
    kw = keyword.upper()
    return [w for w in wines if kw in w.get("name", "").upper()]


def market_stats(wines: list) -> dict:
    """Compute min/max/median/mean for a list of product dicts."""
    prices = []
    for w in wines:
        try:
            p = float(w.get("currentPrice") or w.get("regularPrice") or 0)
            if p > 0:
                prices.append(p)
        except (TypeError, ValueError):
            pass
    if not prices:
        return {"min": None, "max": None, "median": None,
                "mean": None, "count": 0, "prices": []}
    prices.sort()
    n      = len(prices)
    med    = (prices[n // 2] + prices[(n - 1) // 2]) / 2
    return {
        "min":    round(prices[0], 2),
        "max":    round(prices[-1], 2),
        "median": round(med, 2),
        "mean":   round(sum(prices) / n, 2),
        "count":  n,
        "prices": prices,
    }
