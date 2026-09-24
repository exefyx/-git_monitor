import json
import tempfile
import unittest
from pathlib import Path

from scripts.validate_crawl_outputs import BRAND_PAGE, compact_text, validate_source


class ValidationTests(unittest.TestCase):
    def test_compact_brand_matching(self):
        self.assertEqual(compact_text("National Express"), "nationalexpress")
        self.assertEqual(compact_text("Trip.com"), "tripcom")

    def test_valid_brand_page_output_passes(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            rows = [{"source_type": BRAND_PAGE, "brand": "TrainPal", "offer": f"Offer {index}"} for index in range(3)]
            (root / "clean_offers_2026-09-24.json").write_text(json.dumps(rows), encoding="utf-8")
            self.assertTrue(validate_source("Example", {"folder": root, "brands": ["TrainPal"], "min_brand_page_offers": 3}))

    def test_block_page_fails_even_with_rows(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            rows = [{"source_type": BRAND_PAGE, "brand": "TrainPal"}]
            (root / "clean_offers_2026-09-24.json").write_text(json.dumps(rows), encoding="utf-8")
            debug = root / "debug_2026-09-24"
            debug.mkdir()
            (debug / "page_body.txt").write_text("403 ERROR: Request blocked", encoding="utf-8")
            self.assertFalse(validate_source("Example", {"folder": root, "brands": ["TrainPal"], "min_brand_page_offers": 1}))


if __name__ == "__main__":
    unittest.main()
