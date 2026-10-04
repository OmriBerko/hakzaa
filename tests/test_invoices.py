import os
import tempfile
import unittest

from app import create_app


class HakzaaInvoiceTests(unittest.TestCase):
    def setUp(self):
        handle = tempfile.NamedTemporaryFile(suffix=".sqlite", delete=False)
        self.db_path = handle.name
        handle.close()
        self.app = create_app(self.db_path)
        self.client = self.app.test_client()

    def tearDown(self):
        os.unlink(self.db_path)

    def add(self, **overrides):
        data = {
            "invoice_date": "2026-10-01",
            "customer_name": "לקוח בדיקה",
            "amount_before_vat": "6000",
            "vat_amount": "1080",
            "invoice_number": "100",
            "has_allocation": "no",
            "allocation_number": "",
        }
        data.update(overrides)
        return self.client.post("/invoices", data=data, follow_redirects=True)

    def summary(self, response):
        html = response.get_data(as_text=True)
        start = html.index('class="summary"')
        snippet = html[start:start + 400]
        def attr(name):
            key = f'data-{name}="'
            i = snippet.index(key) + len(key)
            return snippet[i:snippet.index('"', i)]
        return {
            "flagged": int(attr("flagged")),
            "cleared": int(attr("cleared")),
            "sum": float(attr("sum")),
            "html": html,
        }

    def test_6000_without_number_is_flagged(self):
        page = self.summary(self.add(customer_name="אלפא", amount_before_vat="6000"))
        self.assertEqual(page["flagged"], 1)
        self.assertEqual(page["cleared"], 0)
        self.assertEqual(page["sum"], 6000)
        self.assertIn('data-flagged-customer="אלפא"', page["html"])
        self.assertIn("יש להיכנס לאזור האישי באתר רשות המיסים", page["html"])
        self.assertIn("אלפא", page["html"])
        self.assertIn("01.10.2026", page["html"])

    def test_4000_is_not_flagged(self):
        page = self.summary(self.add(customer_name="ביתא", amount_before_vat="4000", vat_amount="720"))
        self.assertEqual(page["flagged"], 0)
        self.assertEqual(page["sum"], 0)
        self.assertNotIn("data-flagged-customer=", page["html"])
        self.assertIn("ביתא", page["html"])

    def test_6000_with_number_is_not_flagged(self):
        page = self.summary(self.add(
            customer_name="גמא",
            amount_before_vat="6000",
            has_allocation="yes",
            allocation_number="987654321",
        ))
        self.assertEqual(page["flagged"], 0)
        self.assertEqual(page["cleared"], 1)
        self.assertIn("987654321", page["html"])
        self.assertNotIn("data-flagged-customer=", page["html"])

    def test_marking_received_clears_flag(self):
        self.add(customer_name="דלתא", amount_before_vat="6000", invoice_number="55")
        before = self.summary(self.client.get("/"))
        self.assertEqual(before["flagged"], 1)
        after = self.summary(self.client.post(
            "/invoices/1/received",
            data={"allocation_number": "112233445"},
            follow_redirects=True,
        ))
        self.assertEqual(after["flagged"], 0)
        self.assertEqual(after["cleared"], 1)
        self.assertEqual(after["sum"], 0)
        self.assertIn("112233445", after["html"])
        self.assertNotIn("data-flagged-customer=", after["html"])

    def test_list_survives_new_process_same_database(self):
        self.add(customer_name="המשכיות", amount_before_vat="6000")
        again = create_app(self.db_path)
        page = self.summary(again.test_client().get("/"))
        self.assertEqual(page["flagged"], 1)
        self.assertIn("המשכיות", page["html"])


if __name__ == "__main__":
    unittest.main()
