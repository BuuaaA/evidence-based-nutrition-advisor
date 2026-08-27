#!/usr/bin/env python3
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "build_consumer_answer.py"
FIXTURE = ROOT / "tests" / "fixtures" / "consumer-answer.json"
MANIFEST = ROOT / "examples" / "neuriva-pubmed-search-manifest.json"
RIS = ROOT / "examples" / "neuriva-pubmed-search.ris"
SCREENING = ROOT / "examples" / "neuriva-pubmed-screening.csv"
FISH_FIXTURE = ROOT / "examples" / "cases" / "fish-oil" / "answer.json"
FISH_MANIFEST = ROOT / "examples" / "cases" / "fish-oil" / "pubmed-search-manifest.json"
FISH_RIS = ROOT / "examples" / "cases" / "fish-oil" / "pubmed-search.ris"
FISH_SCREENING = ROOT / "examples" / "cases" / "fish-oil" / "screening.csv"


class ConsumerAnswerTests(unittest.TestCase):
    def run_builder(self, payload, with_svg=False, manifest=MANIFEST, ris=RIS, screening=SCREENING):
        temp = tempfile.TemporaryDirectory(prefix="consumer-answer-")
        base = Path(temp.name)
        source = base / "input.json"
        source.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
        command = [
            sys.executable,
            str(SCRIPT),
            str(source),
            "--html", str(base / "answer.html"),
            "--pubmed-manifest", str(manifest),
            "--pubmed-ris", str(ris),
            "--screening-log", str(screening),
        ]
        if with_svg:
            command += ["--svg", str(base / "answer.svg")]
        result = subprocess.run(command, cwd=ROOT, capture_output=True, text=True)
        return temp, base, result

    def test_builds_three_layer_html_and_optional_image(self):
        payload = json.loads(FIXTURE.read_text(encoding="utf-8"))
        temp, base, result = self.run_builder(payload, with_svg=True)
        self.addCleanup(temp.cleanup)
        self.assertEqual(result.returncode, 0, result.stderr)
        report = json.loads(result.stdout)
        self.assertLessEqual(report["first_screen_chars"], 150)
        self.assertTrue(report["evidence_bundle_verified"])
        page = (base / "answer.html").read_text(encoding="utf-8")
        self.assertEqual(page.count("<summary>"), 8)
        for marker in ('data-testid="why"', 'data-testid="suitability"', 'data-testid="research"'):
            self.assertIn(marker, page)
        self.assertIn("不太值得买。", page)
        self.assertIn("PICOS 与随访", page)
        self.assertIn("证据怎么裁决", page)
        self.assertIn("来源为何看似矛盾", page)
        self.assertIn("按关键结局综合判断", page)
        self.assertIn("与研究人群的匹配度", page)
        self.assertIn("基于快速证据综合的 GRADE 评级", page)
        self.assertIn("范围与流程简化", page)
        self.assertIn("可复现的 PubMed 检索", page)
        self.assertIn("完整检索式", page)
        self.assertIn("PubMed Query Translation", page)
        self.assertIn("筛选流程", page)
        self.assertIn("PICOS 纳入与排除", page)
        self.assertIn("GRADE 五域与理由", page)
        svg = (base / "answer.svg").read_text(encoding="utf-8")
        self.assertIn('width="1080" height="1350"', svg)
        self.assertIn("安全红线", svg)

    def test_rejects_first_screen_over_150_characters(self):
        payload = json.loads(FIXTURE.read_text(encoding="utf-8"))
        payload["effect_ceiling"] = "很长" * 80
        temp, _, result = self.run_builder(payload)
        self.addCleanup(temp.cleanup)
        self.assertEqual(result.returncode, 2)
        self.assertIn("maximum is 150", result.stderr)

    def test_escapes_content_and_drops_unsafe_source_url(self):
        payload = json.loads(FIXTURE.read_text(encoding="utf-8"))
        payload["title"] = "<script>alert(1)</script>"
        payload["research"]["sources"][0]["url"] = "javascript:alert(1)"
        payload["research"]["adjudication"][0]["source"] = "<img src=x onerror=alert(1)>"
        temp, base, result = self.run_builder(payload)
        self.addCleanup(temp.cleanup)
        self.assertEqual(result.returncode, 0, result.stderr)
        page = (base / "answer.html").read_text(encoding="utf-8")
        self.assertNotIn("<script>alert(1)</script>", page)
        self.assertNotIn('href="javascript:', page)
        self.assertIn("&lt;script&gt;alert(1)&lt;/script&gt;", page)
        self.assertNotIn("<img src=x", page)
        self.assertIn("&lt;img src=x onerror=alert(1)&gt;", page)

    def test_accepts_legacy_pico_field(self):
        payload = json.loads(FIXTURE.read_text(encoding="utf-8"))
        payload["research"]["pico"] = payload["research"].pop("picos")
        temp, base, result = self.run_builder(payload)
        self.addCleanup(temp.cleanup)
        self.assertEqual(result.returncode, 0, result.stderr)
        page = (base / "answer.html").read_text(encoding="utf-8")
        self.assertIn("PICOS 与随访", page)

    def test_renders_pre_evidence_intake_and_accepts_legacy_questions(self):
        payload = json.loads(FIXTURE.read_text(encoding="utf-8"))
        temp, base, result = self.run_builder(payload)
        self.addCleanup(temp.cleanup)
        self.assertEqual(result.returncode, 0, result.stderr)
        page = (base / "answer.html").read_text(encoding="utf-8")
        self.assertIn("本次已采用的信息", page)
        self.assertIn("用户选择跳过", page)
        self.assertIn("仍可能改变建议的信息", page)

        payload["suitability"]["questions"] = payload["suitability"].pop("remaining_uncertainties")
        temp, base, result = self.run_builder(payload)
        self.addCleanup(temp.cleanup)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("仍可能改变建议的信息", (base / "answer.html").read_text(encoding="utf-8"))

    def test_accepts_legacy_conflicts_field_and_optional_adjudication(self):
        payload = json.loads(FIXTURE.read_text(encoding="utf-8"))
        payload["research"]["conflicts"] = payload["research"].pop("funding")
        payload["research"].pop("adjudication")
        payload["research"].pop("what_would_change")
        temp, base, result = self.run_builder(payload)
        self.addCleanup(temp.cleanup)
        self.assertEqual(result.returncode, 0, result.stderr)
        page = (base / "answer.html").read_text(encoding="utf-8")
        self.assertIn("资金与利益冲突", page)
        self.assertNotIn("来源为何看似矛盾", page)

    def test_rejects_payload_without_certainty_method(self):
        payload = json.loads(FIXTURE.read_text(encoding="utf-8"))
        payload["research"].pop("certainty_method")
        payload["research"].pop("certainty_scope")
        temp, base, result = self.run_builder(payload)
        self.addCleanup(temp.cleanup)
        self.assertEqual(result.returncode, 2)
        self.assertIn("certainty_method must be a non-empty string", result.stderr)

    def test_renders_source_grade_path(self):
        payload = json.loads(FIXTURE.read_text(encoding="utf-8"))
        payload["research"]["certainty_method"] = "source_grade"
        payload["research"]["certainty_scope"] = "引用可信综述的结局级 GRADE，并完成 PubMed 更新检索。"
        temp, base, result = self.run_builder(payload)
        self.addCleanup(temp.cleanup)
        self.assertEqual(result.returncode, 0, result.stderr)
        page = (base / "answer.html").read_text(encoding="utf-8")
        self.assertIn("引用来源已有 GRADE", page)

    def test_rejects_unknown_certainty_method_or_missing_scope(self):
        payload = json.loads(FIXTURE.read_text(encoding="utf-8"))
        payload["research"]["certainty_method"] = "instant_grade"
        temp, _, result = self.run_builder(payload)
        self.addCleanup(temp.cleanup)
        self.assertEqual(result.returncode, 2)
        self.assertIn("certainty_method must be one of", result.stderr)

        payload = json.loads(FIXTURE.read_text(encoding="utf-8"))
        payload["research"]["certainty_scope"] = ""
        temp, _, result = self.run_builder(payload)
        self.addCleanup(temp.cleanup)
        self.assertEqual(result.returncode, 2)
        self.assertIn("certainty_scope must be a non-empty string", result.stderr)

    def test_rejects_missing_search_audit_or_grade_domains(self):
        payload = json.loads(FIXTURE.read_text(encoding="utf-8"))
        payload["research"].pop("search")
        temp, _, result = self.run_builder(payload)
        self.addCleanup(temp.cleanup)
        self.assertEqual(result.returncode, 2)
        self.assertIn("research.search must be an object", result.stderr)

        payload = json.loads(FIXTURE.read_text(encoding="utf-8"))
        payload["research"]["outcomes"][0].pop("grade_domains")
        temp, _, result = self.run_builder(payload)
        self.addCleanup(temp.cleanup)
        self.assertEqual(result.returncode, 2)
        self.assertIn("grade_domains must be an object", result.stderr)

    def test_rejects_false_complete_counts_and_incomplete_definitive_verdict(self):
        payload = json.loads(FIXTURE.read_text(encoding="utf-8"))
        payload["research"]["search"]["records_exported"] = 1
        payload["research"]["search"]["records_screened"] = 1
        payload["research"]["search"]["full_text_assessed"] = 1
        payload["research"]["search"]["reports_included"] = 1
        payload["research"]["search"]["studies_included"] = 1
        temp, _, result = self.run_builder(payload)
        self.addCleanup(temp.cleanup)
        self.assertEqual(result.returncode, 2)
        self.assertIn("complete_retrieval requires", result.stderr)

        payload = json.loads(FIXTURE.read_text(encoding="utf-8"))
        payload["research"]["search"]["complete_retrieval"] = False
        payload["research"]["search"]["records_exported"] = 1
        payload["research"]["search"]["records_screened"] = 1
        payload["research"]["search"]["full_text_assessed"] = 1
        payload["research"]["search"]["reports_included"] = 1
        payload["research"]["search"]["studies_included"] = 1
        temp, _, result = self.run_builder(payload)
        self.addCleanup(temp.cleanup)
        self.assertEqual(result.returncode, 2)
        self.assertIn("requires verdict insufficient or avoid", result.stderr)

    def test_grade_informed_cannot_masquerade_as_formal_grade(self):
        payload = json.loads(FIXTURE.read_text(encoding="utf-8"))
        payload["research"]["certainty_method"] = "grade_informed"
        payload["research"]["certainty"] = "低"
        temp, _, result = self.run_builder(payload)
        self.addCleanup(temp.cleanup)
        self.assertEqual(result.returncode, 2)
        self.assertIn("must say it is not formally rated", result.stderr)

    def test_provisional_grade_shows_verified_full_text_prompt(self):
        payload = json.loads(FISH_FIXTURE.read_text(encoding="utf-8"))
        temp, base, result = self.run_builder(
            payload,
            manifest=FISH_MANIFEST,
            ris=FISH_RIS,
            screening=FISH_SCREENING,
        )
        self.addCleanup(temp.cleanup)
        self.assertEqual(result.returncode, 0, result.stderr)
        page = (base / "answer.html").read_text(encoding="utf-8")
        self.assertIn('data-testid="full-text-dialog"', page)
        self.assertIn("还有 13 篇候选文献未取得全文", page)
        self.assertIn("暂定中等", page)
        self.assertIn("上传", page)

    def test_provisional_grade_rejects_unverified_missing_count(self):
        payload = json.loads(FISH_FIXTURE.read_text(encoding="utf-8"))
        payload["research"]["evidence_access"]["full_text_unavailable"] = 12
        temp, _, result = self.run_builder(
            payload,
            manifest=FISH_MANIFEST,
            ris=FISH_RIS,
            screening=FISH_SCREENING,
        )
        self.addCleanup(temp.cleanup)
        self.assertEqual(result.returncode, 2)
        self.assertIn("abstract-only count", result.stderr)

    def test_rejects_evidence_bundle_mismatch(self):
        payload = json.loads(FIXTURE.read_text(encoding="utf-8"))
        with tempfile.TemporaryDirectory(prefix="evidence-bundle-") as temp_dir:
            bad_manifest = Path(temp_dir) / "manifest.json"
            manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
            manifest["total_hits"] = 999
            bad_manifest.write_text(json.dumps(manifest, ensure_ascii=False), encoding="utf-8")
            temp, _, result = self.run_builder(payload, manifest=bad_manifest)
            self.addCleanup(temp.cleanup)
            self.assertEqual(result.returncode, 2)
            self.assertIn("total_hits does not match", result.stderr)


if __name__ == "__main__":
    unittest.main()
