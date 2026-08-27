"""Run the reproducible PubMed update searches used by the behavior case gallery."""

from __future__ import annotations

import subprocess
import sys
import argparse
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SEARCH_SCRIPT = ROOT / "scripts" / "pubmed_search.py"

SEARCHES = {
    "fish-oil": (
        '(("Fatty Acids, Omega-3"[Mesh] OR omega-3[tiab] OR omega 3[tiab] '
        'OR fish oil[tiab] OR eicosapentaenoic acid[tiab] OR '
        'docosahexaenoic acid[tiab]) AND ("Triglycerides"[Mesh] OR '
        'triglyceride*[tiab]) AND (hypertriglyceridemi*[tiab] OR '
        'dyslipidemi*[tiab]) AND (random*[tiab] OR trial[tiab] OR '
        '"Systematic Review"[pt] OR systematic review[tiab] OR '
        'meta-analy*[tiab])) AND ("2022/07/01"[Date - Publication] : '
        '"3000"[Date - Publication])'
    ),
    "glucosamine-chondroitin": (
        '(("Glucosamine"[Mesh] OR glucosamine[tiab] OR "Chondroitin '
        'Sulfates"[Mesh] OR chondroitin[tiab]) AND ("Osteoarthritis, '
        'Knee"[Mesh] OR knee osteoarthriti*[tiab]) AND (pain[tiab] OR '
        'function[tiab]) AND (random*[tiab] OR trial[tiab] OR '
        '"Systematic Review"[pt] OR systematic review[tiab] OR '
        'meta-analy*[tiab])) AND ("2025/11/26"[Date - Publication] : '
        '"3000"[Date - Publication])'
    ),
    "calcium-older-adults": (
        '(("Calcium, Dietary"[Mesh] OR calcium supplement*[tiab] OR '
        'calcium supplementation[tiab]) AND ("Fractures, Bone"[Mesh] OR '
        'fracture*[tiab]) AND (random*[tiab] OR trial[tiab] OR '
        '"Systematic Review"[pt] OR systematic review[tiab] OR '
        'meta-analy*[tiab])) AND ("2025/02/20"[Date - Publication] : '
        '"3000"[Date - Publication])'
    ),
}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("cases", nargs="*", choices=sorted(SEARCHES), help="Optional case slugs; default is all")
    args = parser.parse_args()
    selected = args.cases or list(SEARCHES)
    for slug in selected:
        query = SEARCHES[slug]
        case_dir = ROOT / "examples" / "cases" / slug
        case_dir.mkdir(parents=True, exist_ok=True)
        command = [
            sys.executable,
            str(SEARCH_SCRIPT),
            "--query",
            query,
            "--out",
            str(case_dir / "pubmed-search.ris"),
            "--manifest",
            str(case_dir / "pubmed-search-manifest.json"),
        ]
        subprocess.run(command, check=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
