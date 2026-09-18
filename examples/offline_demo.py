"""Synthetic offline report example; no private data or live API requests."""
import sys,json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from analysis import enrich
import report_html,report_excel
products=json.loads((ROOT/'examples/synthetic_products.json').read_text())
market=[{'name':'DEMO BAROLO','currentPrice':25.0},{'name':'DEMO BAROLO','currentPrice':35.0}]
result=enrich(products,market);out=ROOT/'reports';out.mkdir(exist_ok=True)
report_html.generate(result,str(out/'synthetic_demo.html'))
report_excel.generate(result,str(out/'synthetic_demo.xlsx'))
print('reports/synthetic_demo.html');print('reports/synthetic_demo.xlsx')
