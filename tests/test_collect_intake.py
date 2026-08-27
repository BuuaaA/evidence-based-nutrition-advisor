#!/usr/bin/env python3
import importlib.util
import json
import subprocess
import sys
import tempfile
import unittest
import urllib.parse
import urllib.request
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "collect_intake.py"
SAMPLE = ROOT / "templates" / "intake-questionnaire.sample.json"
SKILL = ROOT / "SKILL.md"


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
        self.assertIn("通常询问 3–5 项，硬上限 5 项", content)
        self.assertIn("宿主原生选择控件", content)
        self.assertIn("scripts/collect_intake.py", content)
        self.assertIn("紧凑的编号选项", content)

    def test_collects_clickable_answers_on_localhost(self):
        with tempfile.TemporaryDirectory(prefix="nutrition-intake-") as temp_dir:
            process, response, url = self.start_server(Path(temp_dir))
            try:
                page = urllib.request.urlopen(url, timeout=5).read().decode("utf-8")
                self.assertIn("按这些信息生成证据", page)
                self.assertIn("127.0.0.1", page)
                form = urllib.parse.urlencode(
                    {
                        "action": "submit",
                        "lipid_target": "triglycerides",
                        "triglyceride_level": "mild",
                        "current_medicine": "none",
                        "product_type": "supplement",
                    }
                ).encode("utf-8")
                result = urllib.request.urlopen(url + "/submit", data=form, timeout=5)
                self.assertEqual(result.status, 200)
                self.finish_server(process)
                answer = json.loads(response.read_text(encoding="utf-8"))
                self.assertFalse(answer["skipped"])
                self.assertEqual(answer["answers"]["lipid_target"], "triglycerides")
                self.assertEqual(answer["answer_labels"]["product_type"], "普通鱼油保健品")
            finally:
                if process.poll() is None:
                    process.kill()

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


if __name__ == "__main__":
    unittest.main()
