# BCL Price Agent

Automatically analyses **BCLDB wholesale price lists** (WHS RTL `.xlsx` files) against the **live BC Liquor Stores product catalogue** and generates an interactive HTML + Excel dashboard.

## What it does

1. **Reads** any WHS RTL xlsx file (auto-detected by filename pattern)
2. **Fetches** the live BCL wine catalogue via the BCLDB search API (~3,500 products, cached 24h)
3. **Matches** each product to BCL market comparables by wine type (Barolo, Barbaresco, Chianti, etc.)
4. **Generates**:
   - **Interactive HTML dashboard** (open in any browser, no server needed)
   - **Excel workbook** with charts, tables, and recommendations

## Output Dashboard Sections

| Tab | Content |
|-----|---------|
| Overview | KPI cards, category mix pie, portfolio risk scatter |
| Price Positioning | Your price vs BCL min/median/max per wine type |
| Markup Analysis | Markup % per SKU sorted bar, outlier highlights |
| Portfolio Mix | Category value donut + risk matrix |
| Product Table | Searchable/sortable full product table |
| Recommendations | Prioritised action items (Urgent / Review / Maintain / Monitor) |

## Installation

```bash
pip install -r requirements.txt
```

## Usage

### One-shot (single file)
```bash
python agent.py --file "Copy of WHS RTL.xlsx"
```

### Watch a folder (daemon mode)
Drop any WHS RTL file into the folder — the report is auto-generated and opened in your browser.
```bash
python agent.py --watch ./pricing
```

### Force refresh BCL catalogue cache
```bash
python agent.py --file "..." --refresh-cache
```

### Suppress browser auto-open
```bash
python agent.py --file "..." --no-browser
```

### Custom output folder
```bash
python agent.py --file "..." --output ./my-reports
```

## File detection

The agent recognises files whose name matches any of:
- `Copy of WHS RTL.xlsx`
- `WHS RTL.xlsx`
- `RetailPriceList*.xlsx`
- Any file containing `whs rtl` or `retail price list` (case-insensitive)

## BCL API

Prices are fetched from the public BC Liquor Stores search API:
```
POST https://www.bcliquorstores.com/ajax/browse?category=wine&sort=name.raw:asc&page=N
```
The catalogue (~3,500 wines) is cached locally for 24 hours in `.bcl_wines_cache.json`.

## Project Structure

```
bcl-price-agent/
├── agent.py          # CLI entry point + folder watcher
├── bcl_api.py        # BCL Liquor Stores API client
├── parser.py         # WHS RTL xlsx file parser
├── analysis.py       # Business logic + market comparison
├── report_html.py    # Interactive HTML/Plotly dashboard generator
├── report_excel.py   # Excel workbook generator
├── requirements.txt
└── reports/          # Generated reports land here
```

## Output files

Reports are saved to `./reports/` with timestamp:
```
reports/
  Copy_of_WHS_RTL_20260609_143022.html   ← open in browser
  Copy_of_WHS_RTL_20260609_143022.xlsx   ← Excel dashboard
```
