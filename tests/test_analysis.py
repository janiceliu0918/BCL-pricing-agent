import unittest,json,tempfile
from pathlib import Path
import openpyxl
from analysis import _status_label,enrich
from parser import parse_whs_file
class AnalysisTests(unittest.TestCase):
    def test_statuses(self):
        for raw,want in [('Active','Active'),('Inactive','Inactive'),('pending active','Pending Delist'),('delisted','Pending Delist'),('deleted','Inactive'),('','Unknown'),('review','Review')]:
            with self.subTest(raw=raw):self.assertEqual(_status_label(raw),want)
    def test_margin_markup_and_comparables(self):
        products=json.loads(Path('examples/synthetic_products.json').read_text())
        out=enrich(products,[{'name':'DEMO BAROLO','currentPrice':25},{'name':'DEMO BAROLO','currentPrice':35}])
        p=out['products'][0];self.assertEqual(p['margin_pct'],40);self.assertEqual(p['markup_pct'],25);self.assertEqual(p['bcl_stats']['median'],30);self.assertEqual(out['summary']['active'],1)
    def test_zero_price_and_no_comparables(self):
        out=enrich([{'description':'DEMO','status':'Inactive','final_retail':0,'wholesale':10}],[])
        self.assertIsNone(out['products'][0]['margin_pct']);self.assertEqual(out['summary']['active'],0)
    def test_synthetic_xlsx_parser(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/'WHS RTL.xlsx';w=openpyxl.Workbook();s=w.active;s.append(['SKU','STATUS','DESCRIPTION','FINAL RETAIL PRICE PER SELLING UNIT','Wholesale','Markup']);s.append([1001,'Inactive','DEMO',20,12,0.25]);w.save(p)
            result=parse_whs_file(str(p));self.assertEqual(result[0]['status'],'Inactive');self.assertEqual(result[0]['final_retail'],20)
if __name__=='__main__':unittest.main()
