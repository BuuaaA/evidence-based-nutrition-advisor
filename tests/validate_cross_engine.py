#!/usr/bin/env python3
"""Cross-check the Python fallback against native metafor on a locked fixture."""
import argparse
import json
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
CASES = [
    ("GEN", ROOT / "tests" / "fixtures" / "generic-effects.csv"),
    ("OR", ROOT / "tests" / "fixtures" / "binary-or.csv"),
    ("SMD", ROOT / "tests" / "fixtures" / "continuous-smd.csv"),
]
GOLDEN = ROOT / "tests" / "golden"


def call(cmd):
    p = subprocess.run(cmd, cwd=ROOT, text=True, capture_output=True)
    if p.returncode:
        raise RuntimeError(f"command failed ({p.returncode}): {' '.join(map(str, cmd))}\n{p.stdout}\n{p.stderr}")
    return p


def close(a, b, atol, rtol):
    return abs(a - b) <= atol + rtol * abs(b)


def result_pairs(result, ref, python_result=False):
    pairs = {
        "estimate": (result["re_est"] if python_result else result["estimate"], ref["estimate"]),
        "ci_lo": ((result["re_ci"] if python_result else result["ci"])[0], ref["ci"][0]),
        "ci_hi": ((result["re_ci"] if python_result else result["ci"])[1], ref["ci"][1]),
        "tau2": (result["tau2"], ref["tau2"]),
        "I2": (result["I2"], ref["I2"]),
    }
    for i, (a, b) in enumerate(zip(result["yi"], ref["yi"])):
        pairs[f"yi[{i}]"] = (a, b)
    for i, (a, b) in enumerate(zip(result["vi"], ref["vi"])):
        pairs[f"vi[{i}]"] = (a, b)
    return pairs


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--rscript", default=shutil.which("Rscript"))
    ap.add_argument("--atol", type=float, default=2e-5)
    ap.add_argument("--rtol", type=float, default=2e-5)
    args = ap.parse_args()
    with tempfile.TemporaryDirectory(prefix="meta-engine-check-") as td:
        out = Path(td)
        has_native = bool(args.rscript)
        if has_native:
            pkg = subprocess.run([args.rscript, "-e", "quit(status=if(requireNamespace('metafor',quietly=TRUE))0 else 2)"],
                                 capture_output=True)
            has_native = pkg.returncode == 0
        reports = []
        for measure, fixture in CASES:
            case = out / measure.lower(); case.mkdir()
            py_json, forest = case / "python.json", case / "forest.svg"
            call([sys.executable, str(ROOT / "scripts" / "meta_compute.py"), str(fixture),
                  "--measure", measure, "--test", "knha", "--json", str(py_json),
                  "--forest-svg", str(forest), "--out", str(case / "python.html")])
            py = json.loads(py_json.read_text(encoding="utf-8"))
            svg = forest.read_text(encoding="utf-8")
            for marker in ('data-role="null-line"', 'data-role="pooled-diamond"'):
                if marker not in svg:
                    raise AssertionError(f"{measure} forest structural marker missing: {marker}")
            if py["tau2"] > 0 and 'data-role="prediction-interval"' not in svg:
                raise AssertionError(f"{measure} prediction interval is missing")
            if measure == "OR" and 'data-null-internal="0" data-null-display="1"' not in svg:
                raise AssertionError("OR null line is not log(1)=0")
            ref = json.loads((GOLDEN / f"metafor-4.8.0-{measure.lower()}.json").read_text(encoding="utf-8"))
            pairs = result_pairs(py, ref, python_result=True)
            bad = {k: v for k, v in pairs.items() if not close(v[0], v[1], args.atol, args.rtol)}
            if bad:
                raise AssertionError(f"{measure} Python/golden mismatch: " + json.dumps(bad, indent=2))
            native_status = "skipped"
            if has_native:
                r_out = case / "r"
                call([args.rscript, str(ROOT / "scripts" / "meta_analysis.R"), "--csv", str(fixture),
                      "--measure", measure, "--test", "knha", "--outdir", str(r_out)])
                rr = json.loads((r_out / "results.json").read_text(encoding="utf-8"))
                r_pairs = result_pairs(rr, ref)
                r_bad = {k: v for k, v in r_pairs.items() if not close(v[0], v[1], args.atol, args.rtol)}
                if r_bad:
                    raise AssertionError(f"{measure} native/golden mismatch: " + json.dumps(r_bad, indent=2))
                native_status = "pass"
            reports.append({"measure": measure, "fixture": str(fixture),
                            "python_vs_metafor_golden": "pass", "native_metafor_vs_golden": native_status})
        print(json.dumps({"status": "pass", "tolerances": {"atol": args.atol, "rtol": args.rtol},
                          "cases": reports}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
