"""Run with:  python -m pytest -q   (or: python -m unittest discover tests)"""

import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from intake.evaluate import evaluate  # noqa: E402
from intake.extractor import RuleExtractor  # noqa: E402
from intake.pipeline import load_inquiries, process, write_outputs  # noqa: E402
from intake.scoring import score  # noqa: E402

SAMPLE = ROOT / "sample_data" / "inquiries.json"
LABELS = ROOT / "sample_data" / "labels.json"


def make(body, **kw):
    return {"id": "T-1", "channel": "email", "received_at": "", "body": body, **kw}


class ExtractionTests(unittest.TestCase):
    def setUp(self):
        self.x = RuleExtractor()

    def test_contact_details(self):
        r = self.x.extract(make("My name is Ana Ruiz, call 941.555.0100", **{"from": "ana@example.com"}))
        self.assertEqual(r.contact_name, "Ana Ruiz")
        self.assertEqual(r.email, "ana@example.com")
        self.assertEqual(r.phone, "(941) 555-0100")

    def test_units_and_type(self):
        r = self.x.extract(make("We have 48 units in an apartment complex"))
        self.assertEqual(r.unit_count, 48)
        self.assertEqual(r.property_type, "multifamily")

    def test_urgency(self):
        self.assertEqual(self.x.extract(make("Leak, need help ASAP")).urgency, "high")
        self.assertEqual(self.x.extract(make("No rush, just budgeting")).urgency, "low")

    def test_tenants_is_not_pest_control(self):
        r = self.x.extract(make("cleaning between tenants for my apartment"))
        self.assertNotIn("pest_control", r.services)


class ScoringTests(unittest.TestCase):
    def test_big_urgent_portfolio_is_enterprise_and_reviewed(self):
        r = RuleExtractor().extract(make(
            "I'm with Harbor Point Property Management. 64 units, apartment complex, turnover cleaning ASAP. 941-555-0182"
        ))
        r = score(r)
        self.assertEqual(r.priority_tier, "enterprise")
        self.assertIn("high_value_lead", r.review_reasons)

    def test_no_contact_info_is_flagged(self):
        r = score(RuleExtractor().extract(make("do u guys do lawns")))
        self.assertTrue(r.needs_human_review)
        self.assertIn("no_contact_info", r.review_reasons)


class PipelineTests(unittest.TestCase):
    def test_end_to_end(self):
        records = process(load_inquiries(SAMPLE), force_rules=True)
        self.assertEqual(len(records), 15)
        scores = [r.priority_score for r in records]
        self.assertEqual(scores, sorted(scores, reverse=True))
        with tempfile.TemporaryDirectory() as d:
            stats = write_outputs(records, d)
            self.assertTrue((Path(d) / "leads.csv").exists())
            self.assertEqual(len(list((Path(d) / "drafts").glob("*.txt"))), 15)
            self.assertGreater(stats["minutes_saved"], 0)

    def test_accuracy_floor(self):
        """Regression guard: rule changes must not drop accuracy below 90%."""
        records = process(load_inquiries(SAMPLE), force_rules=True)
        self.assertGreaterEqual(evaluate(records, LABELS)["overall_accuracy"], 90)


if __name__ == "__main__":
    unittest.main()
