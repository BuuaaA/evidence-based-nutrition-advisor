#!/usr/bin/env python3
import csv
import json
import struct
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
CASE = ROOT / "examples" / "cases" / "glucosamine-chondroitin"
IMAGE = ROOT / "assets" / "glucosamine-chondroitin-before-after.png"
SCRIPT = ROOT / "scripts" / "build_before_after_image.py"
README = ROOT / "README.md"
NOTE = ROOT / "examples" / "glucosamine-chondroitin-before-after.md"


class BeforeAfterComparisonTests(unittest.TestCase):
    def test_saved_evidence_bundle_counts_are_consistent(self):
        manifest = json.loads((CASE / "pubmed-search-manifest.json").read_text(encoding="utf-8"))
        self.assertEqual(manifest["total_hits"], 7)
        self.assertEqual(manifest["exported_records"], 7)
        self.assertTrue(manifest["retrieved_all_hits"])

        with (CASE / "screening.csv").open(encoding="utf-8", newline="") as handle:
            rows = list(csv.DictReader(handle))
        self.assertEqual(len(rows), manifest["exported_records"])
        self.assertEqual(len([row for row in rows if row["full_text_decision"] == "include"]), 1)

    def test_homepage_image_is_regenerable_and_has_expected_size(self):
        self.assertTrue(IMAGE.is_file())
        with IMAGE.open("rb") as handle:
            self.assertEqual(handle.read(8), b"\x89PNG\r\n\x1a\n")
            handle.read(8)
            width, height = struct.unpack(">II", handle.read(8))
        self.assertEqual((width, height), (1800, 1180))
        script = SCRIPT.read_text(encoding="utf-8")
        self.assertIn("glucosamine-chondroitin-before-after.png", script)
        self.assertNotIn("D:\\测试skill", script)

    def test_homepage_and_method_note_link_the_saved_evidence(self):
        readme = README.read_text(encoding="utf-8")
        note = NOTE.read_text(encoding="utf-8")
        answer = (CASE / "answer.html").read_text(encoding="utf-8")
        self.assertIn("assets/glucosamine-chondroitin-before-after.png", readme)
        self.assertIn("不是一次固定模型、固定版本、固定日期的基准测试", note)
        self.assertIn("cases/glucosamine-chondroitin/answer.html", note)
        self.assertIn('data-testid="next-actions"', answer)
        self.assertNotIn("D:\\测试skill", answer)
        for name in (
            "answer.html",
            "answer.json",
            "pubmed-search-manifest.json",
            "pubmed-search.ris",
            "screening.csv",
        ):
            self.assertTrue((CASE / name).is_file(), name)


if __name__ == "__main__":
    unittest.main()
