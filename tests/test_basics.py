import os, sys, unittest
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))
from tax import income_tax, saving, marginal_rate
from bank_ing import read_ing_csv

SAMPLE = os.path.join(os.path.dirname(__file__), "..", "samples", "FAKE_ING_Umsatzanzeige_2026Q3.csv")


class TaxTest(unittest.TestCase):
    def test_grundfreibetrag(self):
        self.assertEqual(income_tax(12348), 0)

    def test_brackets_join_up(self):
        # §32a constants are built so each bracket starts where the previous ends
        self.assertAlmostEqual(income_tax(17799), 1034, delta=1)
        self.assertAlmostEqual(income_tax(69878), income_tax(69879), delta=1)
        self.assertAlmostEqual(income_tax(277825), income_tax(277826), delta=1)

    def test_under_pauschbetrag_no_effect(self):
        self.assertEqual(saving(38000, 1000), 0)

    def test_above_pauschbetrag_has_effect(self):
        self.assertGreater(saving(38000, 1330), 0)
        self.assertLess(saving(38000, 1330), 100 * 0.42)

    def test_marginal_rate_range(self):
        self.assertEqual(marginal_rate(10000), 0)
        self.assertAlmostEqual(marginal_rate(150000), 0.42, places=2)


class BankTest(unittest.TestCase):
    def test_reads_fake_ing(self):
        rows = read_ing_csv(SAMPLE)
        self.assertEqual(len(rows), 21)
        self.assertEqual(rows[0]["amount"], -950.0)
        self.assertEqual(sum(r["amount"] > 0 for r in rows), 3)


if __name__ == "__main__":
    unittest.main()


class MatchTest(unittest.TestCase):
    def test_fake_quarter(self):
        import json
        from match import match
        tx = read_ing_csv(SAMPLE)
        receipts = json.load(open(os.path.join(os.path.dirname(SAMPLE), "FAKE_receipts_extracted.json"), encoding="utf-8"))
        m = match(tx, receipts)
        self.assertEqual(len(m["matched"]), 4)          # Lesezeichen, Versandhaus (1 day apart), Lernplattform, Elektro Funke
        self.assertEqual(len(m["missing_receipt"]), 14)  # 18 spending lines - 4
        self.assertEqual([r["vendor"] for r in m["no_bank_entry"]], ["Cafe Muster"])


class CheckTest(unittest.TestCase):
    def test_check(self):
        from extract import check
        self.assertEqual(check({"date": "2026-07-08", "vendor": "X", "total": 10, "vat": [{"rate": 19, "amount": 1.6}],
                                "category": "Privat"}), [])
        self.assertIn("unusual VAT rate 16", check({"date": "d", "vendor": "X", "total": 10, "vat": [{"rate": 16, "amount": 1}]}))
        self.assertIn("missing total", check({"date": "d", "vendor": "X"}))
        # the café receipt Gemma 4 misread in the demo: 17.84 with 3.34 VAT
        self.assertTrue(any("VAT" in p for p in check({"date": "2026-09-03", "vendor": "Cafe", "total": 17.84,
                                                         "vat": [{"rate": 19, "amount": 3.34}], "category": "Privat"})))


class InvoicePaidLaterTest(unittest.TestCase):
    def test_transfer_after_invoice_date(self):
        from datetime import date
        from match import match
        tx = [{"date": date(2026, 8, 10), "amount": -120.0, "counterparty": "Muster Haushaltsservice", "purpose": ""}]
        receipts = [{"date": "2026-08-05", "total": 120.0}]
        self.assertEqual(len(match(tx, receipts)["matched"]), 1)
        self.assertEqual(len(match(tx, receipts, before=3, after=3)["matched"]), 0)
