#!/usr/bin/env python3
import csv
import json
import struct
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
CASE = ROOT / "examples" / "cases" / "nac-traework"
IMAGE = ROOT / "assets" / "nac-traework-before-after.png"
SCRIPT = ROOT / "scripts" / "build_before_after_image.py"
README = ROOT / "README.md"
NOTE = ROOT / "examples" / "nac-traework-before-after.md"


class BeforeAfterComparisonTests(unittest.TestCase):
    def test_test_environment_and_prompt_are_explicit(self):
        data = json.loads((CASE / "comparison.json").read_text(encoding="utf-8"))
        self.assertEqual(data["platform"], "TraeWork")
        self.assertEqual(data["model"], "Qwen 3.8 Max")
        self.assertIn("NAC", data["question"])
        self.assertIn("10 个网页", data["before"]["search"])

    def test_after_skill_search_and_screening_counts_are_consistent(self):
        manifest = json.loads((CASE / "pubmed-search-manifest.json").read_text(encoding="utf-8"))
        self.assertEqual(manifest["total_hits"], 225)
        self.assertEqual(manifest["exported_records"], 225)
        self.assertTrue(manifest["retrieved_all_hits"])

        with (CASE / "screening.csv").open(encoding="utf-8", newline="") as handle:
            rows = list(csv.DictReader(handle))
        self.assertEqual(len(rows), 225)
        full_text = [row for row in rows if row["full_text_status"] == "retrieved"]
        included = [row for row in full_text if row["full_text_decision"] == "include"]
        excluded = [row for row in full_text if row["full_text_decision"] == "exclude"]
        self.assertEqual(len(full_text), 17)
        self.assertEqual(len(included), 16)
        self.assertEqual(len(excluded), 1)

    def test_homepage_image_is_regenerable_and_has_expected_size(self):
        self.assertTrue(IMAGE.is_file())
        with IMAGE.open("rb") as handle:
            self.assertEqual(handle.read(8), b"\x89PNG\r\n\x1a\n")
            handle.read(8)
            width, height = struct.unpack(">II", handle.read(8))
        self.assertEqual((width, height), (1800, 1180))
        script = SCRIPT.read_text(encoding="utf-8")
        self.assertIn("nac-traework-before-after.png", script)
        self.assertNotIn("D:\\测试skill", script)

    def test_homepage_and_method_note_link_the_saved_evidence(self):
        readme = README.read_text(encoding="utf-8")
        note = NOTE.read_text(encoding="utf-8")
        after_html = (CASE / "after-skill.html").read_text(encoding="utf-8")
        self.assertIn("assets/nac-traework-before-after.png", readme)
        self.assertIn("Qwen 3.8 Max", readme)
        self.assertIn("share.traecontent.cn", note)
        self.assertIn(
            "https://buuaaa.github.io/evidence-based-nutrition-advisor/examples/cases/nac-traework/after-skill.html",
            note,
        )
        self.assertNotIn("](cases/nac-traework/after-skill.html)", note)
        self.assertNotIn("D:\\测试skill", after_html)
        self.assertIn('href="screening.csv"', after_html)
        for name in (
            "after-skill.html",
            "pubmed-search-manifest.json",
            "pubmed-search.ris",
            "query.txt",
            "screening.csv",
        ):
            self.assertTrue((CASE / name).is_file(), name)


if __name__ == "__main__":
    unittest.main()
