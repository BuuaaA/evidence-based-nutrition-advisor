import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "evidence_cache.py"


def example_pack():
    return {
        "schema_version": "nutrition-evidence-pack-v1",
        "topic_id": "test-topic",
        "title": "Test topic",
        "aliases": ["test"],
        "scope": {"population": "adults", "intervention": "test", "outcomes": ["outcome"]},
        "freshness_days": 180,
        "searched_at": "2026-08-31",
        "valid_until": "2027-02-27",
        "evidence_passport": {
            "audit_level": "L1-Audited",
            "database": "PubMed",
            "historical_base": "Completed historical review base",
            "records_found": 3,
            "records_exported": 3,
            "records_screened": 3,
            "full_text_unavailable": 0,
            "certainty_method": "rapid_grade",
            "certainty_summary": "moderate",
            "coverage_limits": "PubMed-only single-reviewer audit",
            "sources": [{"label": "Test source", "url": "https://example.org/source"}],
        },
        "pubmed": {"base_query": "test[Title/Abstract]", "last_search_end": "2026-08-31"},
        "safety_rules": [],
        "decision_matrix": [{"match": "test", "verdict": "conditional"}],
        "product_boundaries": ["test boundary"],
    }


def call(index, *args):
    return subprocess.run(
        [sys.executable, str(SCRIPT), "--index", str(index), *args],
        text=True,
        encoding="utf-8",
        capture_output=True,
        check=False,
    )


class EvidenceCacheTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.index = self.root / "index.local.json"
        self.source = self.root / "source-pack.json"
        self.source.write_text(json.dumps(example_pack(), ensure_ascii=False), encoding="utf-8")

    def tearDown(self):
        self.temp.cleanup()

    def register(self):
        result = call(self.index, "register", "--pack", str(self.source))
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_empty_runtime_cache_is_a_clean_miss(self):
        result = call(self.index, "lookup", "--topic", "test-topic", "--as-of", "2026-08-31")
        self.assertEqual(result.returncode, 3)
        self.assertEqual(json.loads(result.stdout)["route"], "quick_l1")

    def test_register_validate_and_fresh_lookup(self):
        self.register()
        validated = call(self.index, "validate")
        self.assertEqual(validated.returncode, 0, validated.stdout + validated.stderr)
        result = call(self.index, "lookup", "--topic", "test-topic", "--as-of", "2026-08-31")
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        payload = json.loads(result.stdout)
        self.assertEqual(payload["status"], "fresh")
        self.assertEqual(payload["route"], "cached_audited_l1")
        self.assertEqual(payload["evidence_passport"]["records_screened"], 3)

    def test_stale_pack_routes_to_incremental_update(self):
        self.register()
        result = call(self.index, "lookup", "--topic", "test-topic", "--as-of", "2027-03-01")
        self.assertEqual(result.returncode, 2)
        payload = json.loads(result.stdout)
        self.assertEqual(payload["status"], "stale")
        self.assertIn("2026-09-01", payload["incremental_update"]["query"])
        self.assertIn("2027-03-01", payload["incremental_update"]["query"])

    def test_missing_topic_routes_to_quick_l1(self):
        self.register()
        result = call(self.index, "lookup", "--topic", "unknown-topic", "--as-of", "2026-08-31")
        self.assertEqual(result.returncode, 3)
        self.assertEqual(json.loads(result.stdout)["route"], "quick_l1")

    def test_incomplete_screening_is_rejected(self):
        pack = example_pack()
        pack["evidence_passport"]["records_screened"] = 2
        self.source.write_text(json.dumps(pack), encoding="utf-8")
        result = call(self.index, "register", "--pack", str(self.source))
        self.assertEqual(result.returncode, 4)
        self.assertIn("complete export and screening", result.stdout)

    def test_personal_answer_fields_are_rejected(self):
        pack = example_pack()
        pack["intake_summary"] = ["personal health data"]
        self.source.write_text(json.dumps(pack), encoding="utf-8")
        result = call(self.index, "register", "--pack", str(self.source))
        self.assertEqual(result.returncode, 4)
        self.assertIn("unsupported top-level fields", result.stdout)


if __name__ == "__main__":
    unittest.main()
