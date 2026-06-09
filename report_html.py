"""
Interactive HTML report generator using Plotly.
Produces a fully self-contained single-file dashboard.
"""

import json
from datetime import datetime
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import plotly.io as pio


# ── colour palette ─────────────────────────────────────────────────
C_ACTIVE  = "#27AE60"
C_DELIST  = "#E74C3C"
C_BLUE    = "#2980B9"
C_ORANGE  = "#E67E22"
C_GRAY    = "#95A5A6"
C_GOLD    = "#F39C12"
C_PURPLE  = "#8E44AD"
C_TEAL    = "#1ABC9C"
C_GREEN2  = "#2ECC71"

CAT_COLORS = {
    "Chinese Baijiu":   "#E74C3C",
    "Chinese Rice Wine":"#E67E22",
    "Italian Wine":     "#F39C12",
    "French Wine":      "#8E44AD",
    "Spanish Wine":     "#2980B9",
    "US Wine":          "#1ABC9C",
    "Varietal Wine":    "#27AE60",
    "Collectible Wine": "#9B59B6",
    "Spirits / Other":  "#95A5A6",
}

STATUS_COLOR = {
    "Active":        C_ACTIVE,
    "Pending Delist":C_DELIST,
    "Inactive":      C_GRAY,
}


def _price_positioning_chart(products: list) -> str:
    """Grouped bar: Your price vs BCL Min / Median / Max (wine only)."""
    wine = [p for p in products
            if p.get("wine_type") and p.get("bcl_stats", {}).get("count", 0) > 0]
    if not wine:
        return ""

    labels  = [p["description"][:30] for p in wine]
    my_ret  = [p["final_retail"]            for p in wine]
    bcl_min = [p["bcl_stats"]["min"]        for p in wine]
    bcl_med = [p["bcl_stats"]["median"]     for p in wine]
    bcl_max = [p["bcl_stats"]["max"]        for p in wine]

    bar_colors = []
    for p in wine:
        if p["vs_median"] is not None and p["vs_median"] < 0:
            bar_colors.append(C_ACTIVE)
        elif p["vs_median"] is not None and p["vs_median"] > 0:
            bar_colors.append(C_DELIST)
        else:
            bar_colors.append(C_BLUE)

    fig = go.Figure()
    fig.add_bar(name="BCL Min",   x=labels, y=bcl_min, marker_color="#AED6F1", opacity=0.7)
    fig.add_bar(name="BCL Median",x=labels, y=bcl_med, marker_color=C_BLUE,    opacity=0.85)
    fig.add_bar(name="Your Price",x=labels, y=my_ret,  marker_color=bar_colors, opacity=0.95,
                text=[f"${v:.2f}" for v in my_ret], textposition="outside")
    fig.add_bar(name="BCL Max",   x=labels, y=bcl_max, marker_color="#D5D8DC",  opacity=0.6)

    fig.update_layout(
        barmode="group",
        title="Wine Price Positioning vs BC Liquor Market",
        yaxis_title="Price (CAD $)",
        xaxis_tickangle=-30,
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
        plot_bgcolor="#FAFAFA",
        paper_bgcolor="#FFFFFF",
        height=450,
        margin=dict(t=80, b=120),
        font=dict(family="Calibri, sans-serif"),
    )
    return pio.to_json(fig)


def _markup_chart(products: list) -> str:
    """Sorted horizontal bar: Markup % per SKU."""
    prods = sorted(
        [p for p in products if p.get("markup_pct") is not None],
        key=lambda x: x["markup_pct"],
    )
    labels  = [f"{p['description'][:28]} ({p['sku']})" for p in prods]
    markups = [p["markup_pct"] / 100 for p in prods]
    colors  = [
        C_DELIST  if p["markup_pct"] > 35
        else C_GRAY if "Delist" in p.get("status", "")
        else C_BLUE
        for p in prods
    ]

    avg = sum(p["markup_pct"] for p in prods) / len(prods) / 100

    fig = go.Figure()
    fig.add_bar(
        x=markups, y=labels, orientation="h",
        marker_color=colors,
        text=[f"{m*100:.1f}%" for m in markups],
        textposition="outside",
    )
    fig.add_vline(
        x=avg, line_dash="dash", line_color=C_ORANGE,
        annotation_text=f"Avg {avg*100:.1f}%",
        annotation_position="top right",
    )
    fig.update_layout(
        title="BCLDB Markup % by Product  (🔴 > 35% outlier  |  gray = Pending Delist)",
        xaxis_title="Markup %",
        xaxis_tickformat=".0%",
        plot_bgcolor="#FAFAFA",
        paper_bgcolor="#FFFFFF",
        height=max(350, len(prods) * 28 + 120),
        margin=dict(t=70, b=60, l=260, r=100),
        font=dict(family="Calibri, sans-serif"),
    )
    return pio.to_json(fig)


def _category_pie(summary: dict) -> str:
    """Pie chart of portfolio value by category."""
    cat_val = summary.get("cat_value", {})
    if not cat_val:
        return ""

    labels = list(cat_val.keys())
    values = [round(v, 2) for v in cat_val.values()]
    colors = [CAT_COLORS.get(l, C_GRAY) for l in labels]

    fig = go.Figure(go.Pie(
        labels=labels,
        values=values,
        marker_colors=colors,
        textinfo="label+percent",
        hovertemplate="<b>%{label}</b><br>$%{value:,.2f}<br>%{percent}<extra></extra>",
        hole=0.35,
    ))
    fig.update_layout(
        title=f"Portfolio Value by Category  (Total ${summary['total_retail']:,.2f})",
        plot_bgcolor="#FFFFFF",
        paper_bgcolor="#FFFFFF",
        height=420,
        legend=dict(orientation="v", x=1, y=0.5),
        font=dict(family="Calibri, sans-serif"),
    )
    return pio.to_json(fig)


def _risk_scatter(products: list) -> str:
    """Scatter: Retail price (log) vs Markup %, sized by wholesale value, coloured by status."""
    traces = {}
    for p in products:
        if p.get("final_retail") is None or p.get("markup_pct") is None:
            continue
        status = p.get("status", "Unknown")
        color  = STATUS_COLOR.get(status, C_GRAY)
        if status not in traces:
            traces[status] = {"x":[], "y":[], "text":[], "size":[], "color": color}
        traces[status]["x"].append(p["final_retail"])
        traces[status]["y"].append(p["markup_pct"])
        traces[status]["text"].append(
            f"{p['description']}<br>Retail: ${p['final_retail']:.2f}<br>"
            f"WHS: ${p.get('wholesale',0):.2f}<br>Markup: {p['markup_pct']:.1f}%"
        )
        whs = p.get("wholesale") or 10
        traces[status]["size"].append(max(10, min(60, whs ** 0.35)))

    fig = go.Figure()
    for status, d in traces.items():
        fig.add_scatter(
            name=status, x=d["x"], y=d["y"],
            mode="markers",
            marker=dict(color=d["color"], size=d["size"], opacity=0.8,
                        line=dict(width=1, color="white")),
            text=d["text"],
            hovertemplate="%{text}<extra></extra>",
        )

    fig.update_layout(
        title="Portfolio Risk Matrix  (X = Retail price log scale, Y = Markup %, bubble = Wholesale value)",
        xaxis_title="Final Retail Price (CAD $) — log scale",
        yaxis_title="Markup %",
        xaxis_type="log",
        plot_bgcolor="#FAFAFA",
        paper_bgcolor="#FFFFFF",
        height=440,
        legend=dict(orientation="h", yanchor="bottom", y=1.02),
        font=dict(family="Calibri, sans-serif"),
    )
    return pio.to_json(fig)


def _product_table_data(products: list) -> str:
    """Return JSON array for the interactive JS data table."""
    rows = []
    for p in products:
        rows.append({
            "sku":       p.get("sku", ""),
            "desc":      p.get("description", ""),
            "cat":       p.get("category", ""),
            "status":    p.get("status", ""),
            "whs":       p.get("wholesale"),
            "retail":    p.get("final_retail"),
            "markup":    p.get("markup_pct"),
            "margin":    p.get("margin_pct"),
            "bcl_min":   p.get("bcl_stats", {}).get("min"),
            "bcl_med":   p.get("bcl_stats", {}).get("median"),
            "bcl_max":   p.get("bcl_stats", {}).get("max"),
            "bcl_count": p.get("bcl_stats", {}).get("count", 0),
            "vs_med":    p.get("vs_median"),
            "vs_pct":    p.get("vs_pct"),
            "position":  p.get("position", ""),
        })
    return json.dumps(rows)


def _recommendations_html(analysis: dict) -> str:
    """Generate the recommendations HTML block."""
    summary  = analysis["summary"]
    products = analysis["products"]

    recs = []

    # Delist risk
    delist = analysis["by_status"].get("Pending Delist", [])
    if delist:
        recs.append(("urgent",
            f"🔴 {len(delist)} SKUs Pending Delist ({len(delist)*100//summary['total_skus']}% of portfolio)",
            "Review replacement SKUs or accept category exit. "
            + ", ".join(p["description"][:25] for p in delist[:4])
            + ("..." if len(delist) > 4 else "")
        ))

    # Products significantly above median
    above = [p for p in products if p.get("vs_pct") and p["vs_pct"] > 20]
    for p in above:
        recs.append(("review",
            f"🟡 {p['description'][:35]} priced ${p['final_retail']:.2f} "
            f"({p['vs_pct']:+.0f}% vs BCL median ${p['bcl_stats']['median']:.2f})",
            f"Verify premium positioning justification. BCL has "
            f"{p['bcl_stats']['count']} comparables in this type."
        ))

    # Products well below median (competitive advantage)
    below = [p for p in products if p.get("vs_pct") and p["vs_pct"] < -10]
    for p in below:
        recs.append(("maintain",
            f"🟢 {p['description'][:35]} — {abs(p['vs_pct']):.0f}% BELOW BCL median",
            f"Strong competitive position at ${p['final_retail']:.2f} vs "
            f"market median ${p['bcl_stats']['median']:.2f}. Prioritise in promotions."
        ))

    # Markup outliers
    for p in summary.get("outlier_markup", []):
        recs.append(("monitor",
            f"🔵 {p['description'][:35]} — Markup {p['markup_pct']:.1f}% vs avg {summary['avg_markup']:.1f}%",
            "Significant outlier. Verify if category duty/excise differential applies."
        ))

    # Online visibility
    recs.append(("monitor",
        "🔵 Online Visibility: 0 products appear on BCLiquorstores.com",
        "All products are wholesale/licensee channel only. "
        "Explore BCLDB Consumer channel listing path for active wine SKUs."
    ))

    tag_style = {
        "urgent":  "background:#FADBD8; border-left:4px solid #E74C3C;",
        "review":  "background:#FDEBD0; border-left:4px solid #E67E22;",
        "maintain":"background:#D5F5E3; border-left:4px solid #27AE60;",
        "monitor": "background:#D6EAF8; border-left:4px solid #2980B9;",
    }
    html = '<div class="section-title">Actionable Recommendations</div>'
    for tag, title, detail in recs:
        style = tag_style.get(tag, "")
        html += f"""
        <div class="rec-card" style="{style}">
            <div class="rec-title">{title}</div>
            <div class="rec-detail">{detail}</div>
        </div>"""
    return html


_HTML_TEMPLATE = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>BCL Portfolio Dashboard · {supplier} · {date}</title>
<script src="https://cdn.plot.ly/plotly-2.35.2.min.js" charset="utf-8"></script>
<style>
  :root {{
    --bg:      #F4F6F9;
    --surface: #FFFFFF;
    --accent:  #1A3A5C;
    --text:    #2C3E50;
    --sub:     #7F8C8D;
    --border:  #DDE1E7;
    --green:   #27AE60;
    --red:     #E74C3C;
    --orange:  #E67E22;
    --blue:    #2980B9;
  }}
  * {{ box-sizing: border-box; margin: 0; padding: 0; }}
  body {{
    font-family: "Segoe UI", Calibri, sans-serif;
    background: var(--bg);
    color: var(--text);
    font-size: 14px;
  }}
  /* ── header ── */
  .header {{
    background: linear-gradient(135deg, #1A3A5C 0%, #0F2540 100%);
    color: #fff;
    padding: 24px 36px;
    display: flex;
    justify-content: space-between;
    align-items: center;
    box-shadow: 0 2px 8px rgba(0,0,0,0.25);
  }}
  .header-left h1 {{ font-size: 22px; font-weight: 700; letter-spacing: 0.5px; }}
  .header-left p  {{ font-size: 13px; opacity: 0.75; margin-top: 4px; }}
  .header-right   {{ font-size: 12px; opacity: 0.65; text-align: right; }}
  /* ── nav tabs ── */
  .nav {{
    background: var(--accent);
    display: flex;
    gap: 2px;
    padding: 0 36px;
    position: sticky;
    top: 0;
    z-index: 100;
  }}
  .nav-tab {{
    padding: 12px 20px;
    color: rgba(255,255,255,0.65);
    cursor: pointer;
    font-size: 13px;
    font-weight: 500;
    border-bottom: 3px solid transparent;
    transition: all 0.2s;
  }}
  .nav-tab:hover   {{ color: #fff; }}
  .nav-tab.active  {{ color: #fff; border-bottom-color: #F39C12; }}
  /* ── layout ── */
  .container  {{ max-width: 1400px; margin: 0 auto; padding: 28px 36px; }}
  .tab-content {{ display: none; }}
  .tab-content.active {{ display: block; }}
  /* ── KPI cards ── */
  .kpi-row {{
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
    gap: 16px;
    margin-bottom: 28px;
  }}
  .kpi {{
    background: var(--surface);
    border-radius: 10px;
    padding: 20px 18px;
    box-shadow: 0 1px 4px rgba(0,0,0,0.08);
    border-top: 4px solid var(--blue);
  }}
  .kpi.green  {{ border-top-color: var(--green); }}
  .kpi.red    {{ border-top-color: var(--red);   }}
  .kpi.orange {{ border-top-color: var(--orange);}}
  .kpi.gold   {{ border-top-color: #F39C12;      }}
  .kpi-label  {{ font-size: 11px; color: var(--sub); text-transform: uppercase;
                 letter-spacing: 0.6px; margin-bottom: 8px; }}
  .kpi-value  {{ font-size: 30px; font-weight: 700; line-height: 1.1; }}
  .kpi-sub    {{ font-size: 11px; color: var(--sub); margin-top: 4px; }}
  /* ── chart cards ── */
  .chart-card {{
    background: var(--surface);
    border-radius: 10px;
    padding: 20px 18px;
    box-shadow: 0 1px 4px rgba(0,0,0,0.08);
    margin-bottom: 22px;
  }}
  .section-title {{
    font-size: 16px;
    font-weight: 600;
    color: var(--accent);
    margin-bottom: 16px;
    padding-bottom: 8px;
    border-bottom: 2px solid var(--border);
  }}
  /* ── data table ── */
  .table-controls {{
    display: flex;
    gap: 12px;
    margin-bottom: 14px;
    flex-wrap: wrap;
  }}
  .table-controls input, .table-controls select {{
    padding: 8px 12px;
    border: 1px solid var(--border);
    border-radius: 6px;
    font-size: 13px;
    outline: none;
  }}
  .table-controls input {{ width: 220px; }}
  table {{
    width: 100%;
    border-collapse: collapse;
    font-size: 13px;
  }}
  th {{
    background: #1A3A5C;
    color: #fff;
    padding: 10px 12px;
    text-align: left;
    font-weight: 600;
    font-size: 12px;
    cursor: pointer;
    user-select: none;
    white-space: nowrap;
  }}
  th:hover {{ background: #0F2540; }}
  td {{
    padding: 9px 12px;
    border-bottom: 1px solid var(--border);
    vertical-align: middle;
  }}
  tr:hover td {{ background: #F0F4F9; }}
  .badge {{
    display: inline-block;
    padding: 2px 8px;
    border-radius: 12px;
    font-size: 11px;
    font-weight: 600;
  }}
  .badge-active  {{ background: #D5F5E3; color: #1E8449; }}
  .badge-delist  {{ background: #FADBD8; color: #C0392B; }}
  .badge-other   {{ background: #EBF5FB; color: #1A5276; }}
  .pos-good  {{ color: var(--green); font-weight: 600; }}
  .pos-warn  {{ color: var(--orange); font-weight: 600; }}
  .pos-bad   {{ color: var(--red); font-weight: 600; }}
  /* ── recommendations ── */
  .rec-card {{
    border-radius: 8px;
    padding: 14px 16px;
    margin-bottom: 12px;
  }}
  .rec-title  {{ font-weight: 600; font-size: 14px; margin-bottom: 4px; }}
  .rec-detail {{ font-size: 13px; color: var(--sub); }}
  /* ── two-col grid ── */
  .two-col {{ display: grid; grid-template-columns: 1fr 1fr; gap: 20px; }}
  @media (max-width: 900px) {{ .two-col {{ grid-template-columns: 1fr; }} }}
  /* ── tooltip ── */
  .tooltip {{ position: relative; display: inline-block; cursor: help; }}
  .tooltip .tip {{
    display: none;
    position: absolute;
    bottom: 120%;
    left: 0;
    background: #333;
    color: #fff;
    padding: 6px 10px;
    border-radius: 4px;
    font-size: 11px;
    white-space: nowrap;
    z-index: 999;
  }}
  .tooltip:hover .tip {{ display: block; }}
</style>
</head>
<body>

<!-- ── HEADER ── -->
<div class="header">
  <div class="header-left">
    <h1>BCL Portfolio Pricing Dashboard</h1>
    <p>Supplier: {supplier} &nbsp;·&nbsp; Source: {source_file} &nbsp;·&nbsp; {total_skus} SKUs analysed</p>
  </div>
  <div class="header-right">
    Generated: {date}<br>
    BCL Wine Catalogue: {bcl_count:,} products
  </div>
</div>

<!-- ── NAV TABS ── -->
<div class="nav">
  <div class="nav-tab active" onclick="showTab('overview')">Overview</div>
  <div class="nav-tab"        onclick="showTab('positioning')">Price Positioning</div>
  <div class="nav-tab"        onclick="showTab('markup')">Markup Analysis</div>
  <div class="nav-tab"        onclick="showTab('portfolio')">Portfolio Mix</div>
  <div class="nav-tab"        onclick="showTab('table')">Product Table</div>
  <div class="nav-tab"        onclick="showTab('recommendations')">Recommendations</div>
</div>

<!-- ═══════════════════════════════════════ TAB: OVERVIEW ══ -->
<div class="container">
<div id="tab-overview" class="tab-content active">

  <!-- KPI Cards -->
  <div class="kpi-row">
    <div class="kpi blue">
      <div class="kpi-label">Total SKUs</div>
      <div class="kpi-value">{total_skus}</div>
      <div class="kpi-sub">Full portfolio</div>
    </div>
    <div class="kpi green">
      <div class="kpi-label">Active</div>
      <div class="kpi-value">{active}</div>
      <div class="kpi-sub">{active_pct:.0f}% of portfolio</div>
    </div>
    <div class="kpi red">
      <div class="kpi-label">Pending Delist ⚠️</div>
      <div class="kpi-value">{delist}</div>
      <div class="kpi-sub">{delist_pct:.0f}% at risk</div>
    </div>
    <div class="kpi gold">
      <div class="kpi-label">Avg BCLDB Markup</div>
      <div class="kpi-value">{avg_markup:.1f}%</div>
      <div class="kpi-sub">Range {markup_min:.1f}%–{markup_max:.1f}%</div>
    </div>
    <div class="kpi orange">
      <div class="kpi-label">Portfolio Retail Value</div>
      <div class="kpi-value">${total_retail:,.0f}</div>
      <div class="kpi-sub">WHS: ${total_whs:,.0f}</div>
    </div>
    <div class="kpi blue">
      <div class="kpi-label">BCLDB Gross Margin</div>
      <div class="kpi-value">{bcldb_margin:.1f}%</div>
      <div class="kpi-sub">${margin_dollars:,.0f} on portfolio</div>
    </div>
  </div>

  <!-- Overview charts: pie + risk scatter -->
  <div class="two-col">
    <div class="chart-card">
      <div id="chart-pie-ov"></div>
    </div>
    <div class="chart-card">
      <div id="chart-scatter-ov"></div>
    </div>
  </div>

</div>

<!-- ══════════════════════════════ TAB: PRICE POSITIONING ══ -->
<div id="tab-positioning" class="tab-content">
  <div class="chart-card">
    <div class="section-title">Wine Price Positioning vs BC Liquor Market</div>
    <div id="chart-positioning"></div>
  </div>
  <div class="chart-card">
    <div class="section-title">Positioning Summary</div>
    <table>
      <thead>
        <tr>
          <th>SKU</th><th>Product</th><th>Category</th><th>Status</th>
          <th>Your Retail</th><th>BCL Min</th><th>BCL Median</th>
          <th>BCL Max</th><th>vs Median $</th><th>vs Median %</th><th>Position</th>
        </tr>
      </thead>
      <tbody id="positioning-tbody"></tbody>
    </table>
  </div>
</div>

<!-- ════════════════════════════════ TAB: MARKUP ANALYSIS ══ -->
<div id="tab-markup" class="tab-content">
  <div class="chart-card">
    <div id="chart-markup"></div>
  </div>
</div>

<!-- ══════════════════════════════ TAB: PORTFOLIO MIX ══════ -->
<div id="tab-portfolio" class="tab-content">
  <div class="chart-card">
    <div id="chart-pie-full"></div>
  </div>
  <div class="chart-card">
    <div id="chart-scatter-full"></div>
  </div>
</div>

<!-- ══════════════════════════════ TAB: PRODUCT TABLE ══════ -->
<div id="tab-table" class="tab-content">
  <div class="chart-card">
    <div class="section-title">All Products</div>
    <div class="table-controls">
      <input type="text" id="tbl-search" placeholder="🔍 Search product…" oninput="filterTable()">
      <select id="tbl-status" onchange="filterTable()">
        <option value="">All Statuses</option>
        <option>Active</option>
        <option>Pending Delist</option>
      </select>
      <select id="tbl-cat" onchange="filterTable()">
        <option value="">All Categories</option>
      </select>
    </div>
    <table id="main-table">
      <thead>
        <tr>
          <th onclick="sortTable(0)">SKU ↕</th>
          <th onclick="sortTable(1)">Description ↕</th>
          <th onclick="sortTable(2)">Category ↕</th>
          <th onclick="sortTable(3)">Status ↕</th>
          <th onclick="sortTable(4)">WHS $ ↕</th>
          <th onclick="sortTable(5)">Retail $ ↕</th>
          <th onclick="sortTable(6)">Markup % ↕</th>
          <th onclick="sortTable(7)">Margin % ↕</th>
          <th onclick="sortTable(8)">BCL Min ↕</th>
          <th onclick="sortTable(9)">BCL Median ↕</th>
          <th onclick="sortTable(10)">BCL Max ↕</th>
          <th onclick="sortTable(11)">vs Median $ ↕</th>
          <th onclick="sortTable(12)">Position</th>
        </tr>
      </thead>
      <tbody id="main-tbody"></tbody>
    </table>
    <div id="tbl-count" style="margin-top:10px;font-size:12px;color:#888;"></div>
  </div>
</div>

<!-- ════════════════════════════ TAB: RECOMMENDATIONS ══════ -->
<div id="tab-recommendations" class="tab-content">
  <div class="chart-card">
    {recommendations_html}
  </div>
</div>

</div><!-- /container -->

<!-- ── SCRIPTS ── -->
<script>
// ── Chart data ─────────────────────────────────────────────────────
const PIE_DATA      = {pie_json};
const SCATTER_DATA  = {scatter_json};
const POS_DATA      = {pos_json};
const MARKUP_DATA   = {markup_json};
const TABLE_DATA    = {table_json};

// ── Tab switching ──────────────────────────────────────────────────
let chartsRendered = {{}};
function showTab(name) {{
  document.querySelectorAll('.tab-content').forEach(t => t.classList.remove('active'));
  document.querySelectorAll('.nav-tab').forEach(t => t.classList.remove('active'));
  document.getElementById('tab-' + name).classList.add('active');
  event.target.classList.add('active');
  if (!chartsRendered[name]) {{ renderCharts(name); chartsRendered[name] = true; }}
}}

// ── Chart rendering ────────────────────────────────────────────────
function renderCharts(tab) {{
  const cfg = {{responsive: true, displayModeBar: false}};
  if (tab === 'overview') {{
    if (PIE_DATA)     Plotly.newPlot('chart-pie-ov',     PIE_DATA.data,     PIE_DATA.layout,     cfg);
    if (SCATTER_DATA) Plotly.newPlot('chart-scatter-ov', SCATTER_DATA.data, SCATTER_DATA.layout, cfg);
  }} else if (tab === 'positioning') {{
    if (POS_DATA)     Plotly.newPlot('chart-positioning', POS_DATA.data,    POS_DATA.layout,     cfg);
    buildPositioningTable();
  }} else if (tab === 'markup') {{
    if (MARKUP_DATA)  Plotly.newPlot('chart-markup',     MARKUP_DATA.data,  MARKUP_DATA.layout,  cfg);
  }} else if (tab === 'portfolio') {{
    if (PIE_DATA)     Plotly.newPlot('chart-pie-full',     PIE_DATA.data,     PIE_DATA.layout,     cfg);
    if (SCATTER_DATA) Plotly.newPlot('chart-scatter-full', SCATTER_DATA.data, SCATTER_DATA.layout, cfg);
  }} else if (tab === 'table') {{
    buildTable();
  }}
}}

// ── Positioning summary table ──────────────────────────────────────
function buildPositioningTable() {{
  const tbody = document.getElementById('positioning-tbody');
  const wine  = TABLE_DATA.filter(p => p.bcl_count > 0);
  tbody.innerHTML = wine.map(p => {{
    const vs = p.vs_med != null ? `${{(p.vs_med > 0 ? '+' : '')}}${{p.vs_med.toFixed(2)}}` : '—';
    const vp = p.vs_pct != null ? `${{(p.vs_pct > 0 ? '+' : '')}}${{p.vs_pct.toFixed(1)}}%` : '—';
    const pc = posClass(p.position);
    return `<tr>
      <td>${{p.sku}}</td>
      <td>${{p.desc}}</td>
      <td>${{p.cat}}</td>
      <td>${{statusBadge(p.status)}}</td>
      <td style="text-align:right">${{fmtMoney(p.retail)}}</td>
      <td style="text-align:right">${{fmtMoney(p.bcl_min)}}</td>
      <td style="text-align:right">${{fmtMoney(p.bcl_med)}}</td>
      <td style="text-align:right">${{fmtMoney(p.bcl_max)}}</td>
      <td style="text-align:right">${{vs}}</td>
      <td style="text-align:right">${{vp}}</td>
      <td class="${{pc}}">${{p.position}}</td>
    </tr>`;
  }}).join('');
}}

// ── Main product table ─────────────────────────────────────────────
let tableData  = [];
let sortDir    = 1;
let sortCol    = 5;

function buildTable() {{
  tableData = [...TABLE_DATA];
  // populate category filter
  const cats = [...new Set(TABLE_DATA.map(p => p.cat))].sort();
  const sel  = document.getElementById('tbl-cat');
  cats.forEach(c => {{ const o = document.createElement('option'); o.value = o.text = c; sel.appendChild(o); }});
  renderTableRows(tableData);
}}

function filterTable() {{
  const q   = document.getElementById('tbl-search').value.toLowerCase();
  const st  = document.getElementById('tbl-status').value;
  const cat = document.getElementById('tbl-cat').value;
  const filtered = TABLE_DATA.filter(p =>
    (!q   || p.desc.toLowerCase().includes(q) || p.sku.toString().includes(q)) &&
    (!st  || p.status === st) &&
    (!cat || p.cat    === cat)
  );
  renderTableRows(filtered);
}}

function sortTable(col) {{
  sortDir = (sortCol === col) ? -sortDir : 1;
  sortCol = col;
  const keys = ['sku','desc','cat','status','whs','retail','markup','margin',
                'bcl_min','bcl_med','bcl_max','vs_med','position'];
  const k = keys[col];
  tableData.sort((a,b) => {{
    const av = a[k] ?? -Infinity, bv = b[k] ?? -Infinity;
    return typeof av === 'string' ? av.localeCompare(bv) * sortDir : (av - bv) * sortDir;
  }});
  renderTableRows(tableData);
}}

function renderTableRows(data) {{
  const tbody = document.getElementById('main-tbody');
  tbody.innerHTML = data.map(p => {{
    const pc = posClass(p.position);
    return `<tr>
      <td>${{p.sku}}</td>
      <td>${{p.desc}}</td>
      <td>${{p.cat}}</td>
      <td>${{statusBadge(p.status)}}</td>
      <td style="text-align:right">${{fmtMoney(p.whs)}}</td>
      <td style="text-align:right">${{fmtMoney(p.retail)}}</td>
      <td style="text-align:right">${{p.markup != null ? p.markup.toFixed(1)+'%' : '—'}}</td>
      <td style="text-align:right">${{p.margin != null ? p.margin.toFixed(1)+'%' : '—'}}</td>
      <td style="text-align:right">${{fmtMoney(p.bcl_min)}}</td>
      <td style="text-align:right">${{fmtMoney(p.bcl_med)}}</td>
      <td style="text-align:right">${{fmtMoney(p.bcl_max)}}</td>
      <td style="text-align:right; color: ${{p.vs_med > 0 ? '#E74C3C' : p.vs_med < 0 ? '#27AE60' : '#888'}}">
        ${{p.vs_med != null ? (p.vs_med > 0 ? '+' : '') + '$'+p.vs_med.toFixed(2) : '—'}}
      </td>
      <td class="${{pc}}">${{p.position}}</td>
    </tr>`;
  }}).join('');
  document.getElementById('tbl-count').textContent = `Showing ${{data.length}} of ${{TABLE_DATA.length}} products`;
}}

// ── Helpers ────────────────────────────────────────────────────────
function fmtMoney(v) {{ return v != null ? '$' + v.toFixed(2) : '—'; }}
function statusBadge(s) {{
  if (s === 'Active')        return `<span class="badge badge-active">${{s}}</span>`;
  if (s === 'Pending Delist') return `<span class="badge badge-delist">${{s}}</span>`;
  return `<span class="badge badge-other">${{s}}</span>`;
}}
function posClass(p) {{
  if (!p) return '';
  if (p.includes('✅')) return 'pos-good';
  if (p.includes('⚠️')) return 'pos-warn';
  if (p.includes('🔴')) return 'pos-bad';
  return '';
}}

// ── Init: render overview on load ──────────────────────────────────
window.addEventListener('load', () => {{
  renderCharts('overview');
  chartsRendered['overview'] = true;
}});
</script>
</body>
</html>"""


def generate(analysis: dict, output_path: str,
             source_file: str = "WHS RTL.xlsx",
             supplier: str = "bonvinws2",
             bcl_count: int = 0) -> str:
    """
    Build and write the interactive HTML report.
    Returns the output path.
    """
    summary  = analysis["summary"]
    products = analysis["products"]

    pie_json     = _category_pie(summary)
    scatter_json = _risk_scatter(products)
    pos_json     = _price_positioning_chart(products)
    markup_json  = _markup_chart(products)
    table_json   = _product_table_data(products)
    recs_html    = _recommendations_html(analysis)

    # Parse Plotly JSON to dicts for safe embedding
    def _parse(j): return json.loads(j) if j else {"data": [], "layout": {}}

    delist = summary["pending_delist"]
    total  = summary["total_skus"]
    active = summary["active"]
    mr_lo, mr_hi = summary["markup_range"]

    html = _HTML_TEMPLATE.format(
        supplier        = supplier,
        source_file     = source_file,
        date            = datetime.now().strftime("%Y-%m-%d %H:%M"),
        total_skus      = total,
        bcl_count       = bcl_count,
        active          = active,
        active_pct      = active / total * 100 if total else 0,
        delist          = delist,
        delist_pct      = delist / total * 100 if total else 0,
        avg_markup      = summary["avg_markup"],
        markup_min      = mr_lo,
        markup_max      = mr_hi,
        total_retail    = summary["total_retail"],
        total_whs       = summary["total_whs"],
        bcldb_margin    = summary["bcldb_margin"],
        margin_dollars  = round(summary["total_retail"] - summary["total_whs"], 2),
        pie_json        = json.dumps(_parse(pie_json)),
        scatter_json    = json.dumps(_parse(scatter_json)),
        pos_json        = json.dumps(_parse(pos_json)),
        markup_json     = json.dumps(_parse(markup_json)),
        table_json      = table_json,
        recommendations_html = recs_html,
    )

    with open(output_path, "w", encoding="utf-8") as f:
        f.write(html)

    return output_path
