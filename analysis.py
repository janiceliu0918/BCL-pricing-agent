"""
Portfolio analysis engine.
Takes parsed WHS products + BCL wine catalogue → produces enriched analysis.
"""

import statistics
from bcl_api import detect_wine_type, is_non_wine, filter_by_keyword, market_stats


def _status_label(raw: str) -> str:
    raw = raw.lower()
    if "active" in raw and "pending" not in raw:
        return "Active"
    if "pending" in raw or "delist" in raw:
        return "Pending Delist"
    if "inactive" in raw or "deleted" in raw:
        return "Inactive"
    return raw.title() or "Unknown"


def _category_label(description: str) -> str:
    desc = description.upper()
    if any(k in desc for k in ["LANGJIU", "HONGHUA", "MAOTAI"]):
        return "Chinese Baijiu"
    if any(k in desc for k in ["SHAOXING", "HUANGJIU"]):
        return "Chinese Rice Wine"
    if any(k in desc for k in ["WHISKY", "WHISKEY", "BOURBON", "SCOTCH"]):
        return "Whisky"
    if any(k in desc for k in ["VODKA"]):
        return "Vodka"
    if any(k in desc for k in ["GIN"]):
        return "Gin"
    if any(k in desc for k in ["SAKE"]):
        return "Sake"
    if any(k in desc for k in ["BAROLO", "BARBARESCO", "CHIANTI",
                                "TOSCANA", "TUSCAN", "BRUNELLO",
                                "AMARONE", "SANGIOVESE"]):
        return "Italian Wine"
    if any(k in desc for k in ["BORDEAUX", "BURGUNDY", "RHONE", "RHÔNE",
                                "CHAMPAGNE", "PROVENCE", "ALSACE",
                                "COTES", "CÔTES"]):
        return "French Wine"
    if any(k in desc for k in ["RIOJA", "RIBERA DEL DUERO", "PRIORAT",
                                "NAVARRA", "CAMPO DE BORJA"]):
        return "Spanish Wine"
    if any(k in desc for k in ["NAPA", "SONOMA", "CALIFORNIA", "OREGON",
                                "WASHINGTON"]):
        return "US Wine"
    if any(k in desc for k in ["CABERNET", "MERLOT", "CHARDONNAY",
                                "PINOT NOIR", "SAUVIGNON BLANC",
                                "PINOT GRIGIO", "RIESLING", "MALBEC",
                                "SHIRAZ", "SYRAH", "GRENACHE"]):
        return "Varietal Wine"
    return "Spirits / Other"


def _vs_label(diff: object) -> str:
    if diff is None:
        return "N/A — no comparables"
    if diff < -15:
        return "✅ Well below market"
    if diff < 0:
        return "✅ Below median"
    if diff == 0:
        return "= At median"
    if diff < 15:
        return "⚠️ Above median"
    return "🔴 Significantly above"


def enrich(products: list, bcl_wines: list) -> dict:
    """
    Enrich WHS product list with BCL market comparables and stats.

    Returns:
    {
        "products": [ enriched product dicts ],
        "summary": { portfolio-level stats },
        "by_category": { cat_name: [products] },
    }
    """
    enriched = []

    for p in products:
        desc     = p["description"]
        status   = _status_label(p.get("status", ""))
        category = _category_label(desc)
        final    = p.get("final_retail")
        whs      = p.get("wholesale")
        markup   = p.get("markup")

        # Normalise markup to percentage
        if markup is not None and markup < 1:
            markup = round(markup * 100, 2)

        # Margin = (retail - wholesale) / retail
        margin = None
        if final and whs and final > 0:
            margin = round((final - whs) / final * 100, 2)

        # BCL market comparables
        wine_type  = None
        bcl_stats  = {"min": None, "max": None, "median": None,
                      "mean": None, "count": 0, "prices": []}
        comparables = []
        vs_med     = None
        vs_pct     = None

        if not is_non_wine(desc):
            wine_type = detect_wine_type(desc)
            if wine_type:
                comparables = filter_by_keyword(bcl_wines, wine_type)
                bcl_stats   = market_stats(comparables)
                if bcl_stats["median"] and final:
                    vs_med = round(final - bcl_stats["median"], 2)
                    vs_pct = round(vs_med / bcl_stats["median"] * 100, 2)

        enriched.append({
            **p,
            "status":       status,
            "category":     category,
            "markup_pct":   markup,
            "margin_pct":   margin,
            "wine_type":    wine_type,
            "bcl_stats":    bcl_stats,
            "comparables":  comparables[:10],  # top 10 for table display
            "vs_median":    vs_med,
            "vs_pct":       vs_pct,
            "position":     _vs_label(vs_med),
        })

    # Portfolio-level summary
    all_finals  = [p["final_retail"] for p in enriched if p["final_retail"]]
    all_whs     = [p["wholesale"]    for p in enriched if p["wholesale"]]
    all_markups = [p["markup_pct"]   for p in enriched if p["markup_pct"] is not None]

    total_retail = sum(all_finals)
    total_whs    = sum(all_whs)

    by_status = {}
    for p in enriched:
        by_status.setdefault(p["status"], []).append(p)

    by_cat = {}
    for p in enriched:
        by_cat.setdefault(p["category"], []).append(p)

    cat_value = {
        cat: sum(p["final_retail"] for p in prods if p["final_retail"])
        for cat, prods in by_cat.items()
    }

    summary = {
        "total_skus":    len(enriched),
        "active":        len(by_status.get("Active", [])),
        "pending_delist":len(by_status.get("Pending Delist", [])),
        "total_retail":  round(total_retail, 2),
        "total_whs":     round(total_whs, 2),
        "bcldb_margin":  round((total_retail - total_whs) / total_retail * 100, 2) if total_retail else 0,
        "avg_markup":    round(statistics.mean(all_markups), 2) if all_markups else 0,
        "markup_range":  (round(min(all_markups), 2), round(max(all_markups), 2)) if all_markups else (0, 0),
        "outlier_markup":[p for p in enriched if p["markup_pct"] and p["markup_pct"] > 35],
        "cat_value":     cat_value,
    }

    return {
        "products":    enriched,
        "summary":     summary,
        "by_category": by_cat,
        "by_status":   by_status,
    }
