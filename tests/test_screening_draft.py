import csv
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "ris_screening_draft.py"


class ScreeningDraftTests(unittest.TestCase):
    def test_adds_non_decisional_triage_hints_and_abstract(self):
        ris = """TY  - JOUR
TI  - A randomized controlled trial
AB  - Adults were randomized to supplement or placebo.
M3  - Randomized Controlled Trial
ID  - PMID:42
DO  - 10.1000/example
N1  - PMCID:PMC123
ER  - 
"""
        with tempfile.TemporaryDirectory(prefix="screening-draft-") as temp:
            base = Path(temp)
            source = base / "hits.ris"
            output = base / "screening.csv"
            inspection = base / "inspection.md"
            source.write_text(ris, encoding="utf-8")
            result = subprocess.run(
                [sys.executable, str(SCRIPT), str(source), "--csv", str(output), "--inspection", str(inspection)],
                cwd=ROOT, capture_output=True, text=True,
            )
            self.assertEqual(result.returncode, 0, result.stderr)
            with output.open(encoding="utf-8-sig") as handle:
                row = next(csv.DictReader(handle))
            self.assertEqual(row["screening_priority"], "high")
            self.assertIn("人体对照试验", row["triage_hints"])
            self.assertIn("Adults were randomized", row["abstract"])
            self.assertEqual(row["title_abstract_decision"], "")
            self.assertEqual(row["pmcid"], "PMC123")
            self.assertIn("https://pmc.ncbi.nlm.nih.gov/articles/PMC123/", row["access_candidates"])
            self.assertIn("https://doi.org/10.1000/example", row["access_candidates"])
            self.assertEqual(row["full_text_access_attempts"], "")
            self.assertEqual(row["access_checked_at"], "")


if __name__ == "__main__":
    unittest.main()
