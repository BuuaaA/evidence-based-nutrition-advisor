#!/usr/bin/env python3
import argparse
import importlib.util
import tempfile
import unittest
import json
from datetime import date
from pathlib import Path
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "pubmed_search.py"
SPEC = importlib.util.spec_from_file_location("pubmed_search", SCRIPT)
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC and SPEC.loader
SPEC.loader.exec_module(MODULE)


class PubMedSearchTests(unittest.TestCase):
    def test_exports_pmcid_and_publication_type_for_full_text_triage(self):
        xml = b"""<PubmedArticleSet><PubmedArticle><MedlineCitation><PMID>42</PMID>
        <Article><ArticleTitle>Example trial</ArticleTitle><PublicationTypeList>
        <PublicationType>Randomized Controlled Trial</PublicationType></PublicationTypeList></Article>
        </MedlineCitation><PubmedData><ArticleIdList><ArticleId IdType="pmc">PMC123</ArticleId>
        </ArticleIdList></PubmedData></PubmedArticle></PubmedArticleSet>"""
        ris = MODULE.to_ris(MODULE.parse_pubmed_xml(xml))
        self.assertIn("M3  - Randomized Controlled Trial", ris)
        self.assertIn("N1  - PMCID:PMC123", ris)

    def test_query_mode_defaults_to_exporting_all_hits(self):
        args = MODULE.build_parser().parse_args(
            ["--query", "fish oil[tiab]", "--manifest", "search.json"]
        )
        self.assertIsNone(args.retmax)
        self.assertFalse(args.allow_truncated)

    def test_query_mode_defaults_to_latest_ten_years(self):
        args = MODULE.build_parser().parse_args(
            ["--query", "fish oil[tiab]", "--manifest", "search.json"]
        )
        params, scope = MODULE._date_scope(args, today=date(2026, 9, 1))
        self.assertEqual(
            params,
            {"datetype": "pdat", "mindate": "2016/09/01", "maxdate": "2026/09/01"},
        )
        self.assertEqual(scope["mode"], "recent_years")
        self.assertEqual(scope["years"], 10)

    def test_all_years_disables_publication_date_filter(self):
        args = MODULE.build_parser().parse_args(
            ["--query", "fish oil[tiab]", "--manifest", "search.json", "--all-years"]
        )
        params, scope = MODULE._date_scope(args, today=date(2026, 9, 1))
        self.assertEqual(params, {})
        self.assertEqual(scope["mode"], "all_years")

    def test_rejects_silent_truncation(self):
        with tempfile.TemporaryDirectory(prefix="pubmed-search-") as temp:
            base = Path(temp)
            args = argparse.Namespace(
                query="fish oil[tiab]",
                out=str(base / "hits.ris"),
                manifest=str(base / "search.json"),
                retmax=200,
                allow_truncated=False,
                batch_size=200,
                sort="pub date",
                email=None,
                api_key=None,
            )
            fake_search = {
                "esearchresult": {
                    "count": "650",
                    "querytranslation": '"fish oil"[Title/Abstract]',
                    "querykey": "1",
                    "webenv": "fake",
                }
            }
            with patch.object(MODULE, "_request", return_value=fake_search):
                with self.assertRaisesRegex(ValueError, "不得静默截断"):
                    MODULE.cmd_search(args)

    def test_exports_650_records_in_four_batches(self):
        with tempfile.TemporaryDirectory(prefix="pubmed-search-") as temp:
            base = Path(temp)
            args = argparse.Namespace(
                query="fish oil[tiab]",
                out=str(base / "hits.ris"),
                manifest=str(base / "search.json"),
                retmax=None,
                allow_truncated=False,
                batch_size=200,
                sort="pub date",
                email=None,
                api_key=None,
            )
            starts = []

            def fake_request(endpoint, params, *, as_json=False):
                if endpoint == "esearch.fcgi":
                    return {
                        "esearchresult": {
                            "count": "650",
                            "querytranslation": '"fish oil"[Title/Abstract]',
                            "querykey": "1",
                            "webenv": "fake",
                        }
                    }
                self.assertEqual(endpoint, "efetch.fcgi")
                start = int(params["retstart"])
                size = int(params["retmax"])
                starts.append((start, size))
                records = "".join(
                    "<PubmedArticle><MedlineCitation>"
                    f"<PMID>{index + 1}</PMID><Article><ArticleTitle>Study {index + 1}</ArticleTitle></Article>"
                    "</MedlineCitation></PubmedArticle>"
                    for index in range(start, start + size)
                )
                return f"<PubmedArticleSet>{records}</PubmedArticleSet>".encode("utf-8")

            with patch.object(MODULE, "_request", side_effect=fake_request), patch.object(
                MODULE, "_pause", return_value=None
            ):
                MODULE.cmd_search(args)

            self.assertEqual(starts, [(0, 200), (200, 200), (400, 200), (600, 50)])
            manifest = json.loads((base / "search.json").read_text(encoding="utf-8"))
            self.assertEqual(manifest["total_hits"], 650)
            self.assertEqual(manifest["exported_records"], 650)
            self.assertTrue(manifest["retrieved_all_hits"])
            self.assertEqual(manifest["time_scope"], "recent_years")
            self.assertEqual(manifest["recent_years"], 10)
            self.assertTrue(manifest["date_from"])
            self.assertTrue(manifest["date_to"])
            ris = (base / "hits.ris").read_text(encoding="utf-8")
            self.assertEqual(ris.count("ID  - PMID:"), 650)

    def test_rejects_pubmed_sets_over_esearch_limit(self):
        with tempfile.TemporaryDirectory(prefix="pubmed-search-") as temp:
            base = Path(temp)
            args = argparse.Namespace(
                query="nutrition[tiab]",
                out=str(base / "hits.ris"),
                manifest=str(base / "search.json"),
                retmax=None,
                allow_truncated=False,
                batch_size=200,
                sort="pub date",
                email=None,
                api_key=None,
            )
            fake_search = {
                "esearchresult": {
                    "count": "10001",
                    "querytranslation": '"nutrition"[Title/Abstract]',
                    "querykey": "1",
                    "webenv": "fake",
                }
            }
            with patch.object(MODULE, "_request", return_value=fake_search):
                with self.assertRaisesRegex(ValueError, "EDirect"):
                    MODULE.cmd_search(args)


if __name__ == "__main__":
    unittest.main()
