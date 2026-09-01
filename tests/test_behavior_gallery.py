#!/usr/bin/env python3
import json
import re
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "examples" / "behavior-case-results.json"
GALLERY = ROOT / "examples" / "consumer-answer-demo.html"
README = ROOT / "README.md"


class BehaviorGalleryTests(unittest.TestCase):
    def setUp(self):
        self.payload = json.loads(DATA.read_text(encoding="utf-8"))
        self.cases = self.payload["cases"]

    def test_contains_all_fourteen_acceptance_cases(self):
        self.assertEqual([case["id"] for case in self.cases], list(range(1, 15)))
        self.assertEqual(len({case["slug"] for case in self.cases}), 14)

    def test_each_case_has_png_and_svg(self):
        for case in self.cases:
            self.assertEqual(len(case["trace"]), 4)
            stem = f"case-{case['id']:02d}-{case['slug']}"
            for suffix in (".png", ".svg"):
                self.assertTrue((ROOT / "assets" / "behavior-cases" / f"{stem}{suffix}").is_file())

    def test_gallery_links_only_to_existing_local_files(self):
        page = GALLERY.read_text(encoding="utf-8")
        self.assertEqual(page.count('<article class="case"'), 14)
        for href in re.findall(r'href="([^"]+)"', page):
            if href.startswith(("http://", "https://", "#")):
                continue
            target = (GALLERY.parent / href).resolve()
            self.assertTrue(target.exists(), f"broken gallery link: {href}")

    def test_homepage_uses_glucosamine_and_keeps_neuriva_in_gallery(self):
        readme = README.read_text(encoding="utf-8")
        gallery = GALLERY.read_text(encoding="utf-8")
        self.assertIn("assets/glucosamine-chondroitin-before-after.png", readme)
        self.assertNotIn("assets/neuriva-before-after.png", readme)
        self.assertNotIn("assets/behavior-acceptance-neuriva.png", readme)
        self.assertIn("Neuriva 脑活素有用吗？", gallery)

    def test_guardrail_cases_do_not_claim_false_certainty(self):
        by_id = {case["id"]: case for case in self.cases}
        self.assertIn("暂定 GRADE", by_id[5]["verdict"])
        self.assertIn("暂不能可靠判断", by_id[6]["verdict"])
        self.assertIn("一个预先指定的数据库", by_id[7]["result"])
        self.assertIn("200 是每批获取数量", by_id[6]["result"])
        self.assertIn("不冒充发表级系统综述", by_id[8]["trace"][3][1])
        self.assertIn("四道门", by_id[10]["verdict"])
        self.assertIn("不能包装", by_id[11]["verdict"])
        self.assertIn("专业评估", by_id[12]["verdict"])
        self.assertIn("不是 N-of-1", by_id[13]["verdict"])
        self.assertIn("Shoden® 280 mg", by_id[14]["verdict"])

    def test_ordinary_personal_cases_collect_clickable_information_first(self):
        by_id = {case["id"]: case for case in self.cases}
        for case_id in (1, 2, 3):
            self.assertEqual(case_id, by_id[case_id]["id"])
            self.assertEqual(by_id[case_id]["trace"][0][0], "证据前点击收集")
        self.assertIn("4 项", by_id[1]["trace"][0][1])
        self.assertIn("首次关键问题不藏", by_id[1]["checks"][0])
        self.assertIn("跳过", by_id[1]["boundary"])


if __name__ == "__main__":
    unittest.main()
