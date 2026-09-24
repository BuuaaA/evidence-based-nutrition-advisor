#!/usr/bin/env python3
import importlib.util
import json
import subprocess
import sys
import tempfile
import unittest
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "collect_intake.py"
SAMPLE = ROOT / "templates" / "intake-questionnaire.sample.json"
SKILL = ROOT / "SKILL.md"
INTAKE_RULES = ROOT / "references" / "pre-evidence-intake.md"


def load_module():
    spec = importlib.util.spec_from_file_location("collect_intake", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    spec.loader.exec_module(module)
    return module


class CollectIntakeTests(unittest.TestCase):
    def start_server(self, base: Path):
        response = base / "response.json"
        process = subprocess.Popen(
            [
                sys.executable,
                str(SCRIPT),
                str(SAMPLE),
                "--response",
                str(response),
                "--timeout",
                "30",
            ],
            cwd=ROOT,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            encoding="utf-8",
        )
        assert process.stdout
        start = json.loads(process.stdout.readline())
        self.assertEqual(start["status"], "waiting")
        return process, response, start["url"]

    def finish_server(self, process: subprocess.Popen):
        stdout, stderr = process.communicate(timeout=10)
        self.assertEqual(process.returncode, 0, stderr)
        self.assertEqual(json.loads(stdout.strip())["status"], "ok")

    def test_validates_sample_and_rejects_more_than_five_questions(self):
        module = load_module()
        payload = json.loads(SAMPLE.read_text(encoding="utf-8"))
        normalized = module.validate_questionnaire(payload)
        self.assertEqual(len(normalized["questions"]), 4)
        payload["questions"] = payload["questions"] * 2
        with self.assertRaisesRegex(ValueError, "1 to 5"):
            module.validate_questionnaire(payload)

    def test_skill_contract_places_clickable_intake_before_evidence(self):
        content = SKILL.read_text(encoding="utf-8")
        self.assertIn("完整检索和答案生成前完成一次点击式关键信息收集", content)
        self.assertIn("通常询问 1–3 项，最多 5 项", content)
        self.assertIn("宿主原生选择控件", content)
        self.assertIn("scripts/collect_intake.py", content)
        self.assertIn("不得向普通用户展示", content)
        self.assertIn("一次只问一个自然语言问题", content)
        self.assertIn("不得只发链接后结束本轮", content)
        self.assertIn("要求用户再发送“已提交”", content)

    def test_intake_fallback_is_ordered_and_cannot_skip_local_questionnaire(self):
        content = INTAKE_RULES.read_text(encoding="utf-8")
        self.assertIn("优先宿主原生单选/多选；否则可用本地问卷", content)
        self.assertIn("两者都无法回传时才用自然语言追问", content)
        self.assertIn("按当前宿主真正可用的能力选择交互形式", content)
        self.assertIn("不要声称静态页面可启动后台任务", content)
        self.assertIn("问卷提交前允许修改", content)
        self.assertIn("用户已明确要求长任务时按现有授权执行", content)

    def test_collects_clickable_answers_on_localhost(self):
        with tempfile.TemporaryDirectory(prefix="nutrition-intake-") as temp_dir:
            process, response, url = self.start_server(Path(temp_dir))
            try:
                page = urllib.request.urlopen(url, timeout=5).read().decode("utf-8")
                self.assertIn("检查我的选择", page)
                self.assertIn("127.0.0.1", page)
                form = urllib.parse.urlencode(
                    {
                        "action": "review",
                        "lipid_target": "triglycerides",
                        "triglyceride_level": "mild",
                        "current_medicine": "none",
                        "product_type": "supplement",
                    }
                ).encode("utf-8")
                review = urllib.request.urlopen(url + "/review", data=form, timeout=5).read().decode("utf-8")
                self.assertIn("提交前确认", review)
                self.assertIn("普通鱼油保健品", review)
                result = urllib.request.urlopen(url + "/submit", data=form, timeout=5)
                self.assertEqual(result.status, 200)
                success = result.read().decode("utf-8")
                self.assertIn("无需再发送“已提交”", success)
                self.assertIn("3分钟内", success)
                self.finish_server(process)
                answer = json.loads(response.read_text(encoding="utf-8"))
                self.assertFalse(answer["skipped"])
                self.assertEqual(answer["schema_version"], "nutrition-intake-v2")
                self.assertEqual(answer["answers"]["lipid_target"], "triglycerides")
                self.assertEqual(answer["answers"]["current_medicine"], ["none"])
                self.assertEqual(answer["answer_labels"]["product_type"], "普通鱼油保健品")
                self.assertIn("quick_result_deadline_utc", answer)
            finally:
                if process.poll() is None:
                    process.kill()
                    process.communicate(timeout=5)

    def test_skip_returns_empty_answers(self):
        with tempfile.TemporaryDirectory(prefix="nutrition-intake-") as temp_dir:
            process, response, url = self.start_server(Path(temp_dir))
            try:
                form = urllib.parse.urlencode({"action": "skip"}).encode("utf-8")
                urllib.request.urlopen(url + "/submit", data=form, timeout=5).read()
                self.finish_server(process)
                answer = json.loads(response.read_text(encoding="utf-8"))
                self.assertTrue(answer["skipped"])
                self.assertEqual(answer["answers"], {})
            finally:
                if process.poll() is None:
                    process.kill()
                    process.communicate(timeout=5)

    def test_multiselect_review_edit_and_optional_question(self):
        with tempfile.TemporaryDirectory(prefix="nutrition-intake-") as temp_dir:
            process, response, url = self.start_server(Path(temp_dir))
            try:
                form = urllib.parse.urlencode(
                    {
                        "action": "review",
                        "lipid_target": "multiple",
                        "triglyceride_level": "unknown",
                        "current_medicine": ["lipid", "anticoagulant"],
                    },
                    doseq=True,
                ).encode("utf-8")
                review = urllib.request.urlopen(url + "/review", data=form, timeout=5).read().decode("utf-8")
                self.assertIn("正在使用降脂药、正在使用抗凝或抗血小板药", review)
                self.assertIn("未选择（可跳过）", review)
                edited = urllib.request.urlopen(url + "/edit", data=form, timeout=5).read().decode("utf-8")
                self.assertGreaterEqual(edited.count("checked"), 4)
                urllib.request.urlopen(url + "/submit", data=form, timeout=5).read()
                self.finish_server(process)
                answer = json.loads(response.read_text(encoding="utf-8"))
                self.assertEqual(answer["answers"]["current_medicine"], ["lipid", "anticoagulant"])
                self.assertNotIn("product_type", answer["answers"])
            finally:
                if process.poll() is None:
                    process.kill()
                    process.communicate(timeout=5)

    def test_rejects_exclusive_multiselect_combination(self):
        with tempfile.TemporaryDirectory(prefix="nutrition-intake-") as temp_dir:
            process, _, url = self.start_server(Path(temp_dir))
            try:
                form = urllib.parse.urlencode(
                    {
                        "action": "review",
                        "lipid_target": "multiple",
                        "triglyceride_level": "unknown",
                        "current_medicine": ["lipid", "none"],
                    },
                    doseq=True,
                ).encode("utf-8")
                with self.assertRaises(urllib.error.HTTPError) as raised:
                    urllib.request.urlopen(url + "/review", data=form, timeout=5)
                self.assertEqual(raised.exception.code, 400)
            finally:
                if process.poll() is None:
                    process.kill()
                    process.communicate(timeout=5)


if __name__ == "__main__":
    unittest.main()
