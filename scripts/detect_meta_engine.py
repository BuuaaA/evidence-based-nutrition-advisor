#!/usr/bin/env python3
"""Detect the highest-priority executable Meta-analysis engine.

This helper is advisory. When Python itself is unavailable, the agent follows
references/statistical-engine-routing.md and selects browser webR directly.
"""
import argparse
import hashlib
import json
import os
import platform
import shutil
import subprocess
from pathlib import Path


def run(cmd):
    try:
        p = subprocess.run(cmd, capture_output=True, text=True, timeout=20)
        return p.returncode == 0, p.stdout.strip(), p.stderr.strip()
    except Exception as exc:
        return False, "", str(exc)


def sha256_file(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--online-webr-reachable", action="store_true",
                    help="Set only after the official locked webR resources were actually reached")
    ap.add_argument("--skill-root", default=str(Path(__file__).resolve().parents[1]))
    args = ap.parse_args()
    root = Path(args.skill_root).resolve()
    reasons = []

    rscript = shutil.which("Rscript")
    r_version = None
    metafor_version = None
    if rscript:
        ok, out, err = run([rscript, "--version"])
        version_text = out or err
        r_version = version_text.splitlines()[0] if version_text else None
        ok_pkg, pkg_out, pkg_err = run([rscript, "-e",
            "if(!requireNamespace('metafor',quietly=TRUE)) quit(status=2); cat(as.character(packageVersion('metafor')))"])
        if ok_pkg:
            metafor_version = pkg_out.strip()
            selected = "native_r_metafor"
        else:
            reasons.append("native R found but metafor is unavailable or failed self-check")
            selected = None
    else:
        reasons.append("Rscript not found")
        selected = None

    py = shutil.which("python") or shutil.which("python3") or shutil.which("py")
    if selected is None and py:
        selected = "native_python"
    elif selected is None:
        reasons.append("Python launcher not found")

    if selected is None and args.online_webr_reachable:
        selected = "online_webr_metafor"
    elif selected is None:
        reasons.append("official online webR reachability not confirmed")

    manifest = root / "webr-offline" / "manifest.json"
    offline_ok = False
    missing = []
    hash_mismatches = []
    manifest_data = None
    if manifest.exists():
        try:
            manifest_data = json.loads(manifest.read_text(encoding="utf-8"))
            dist = root / "webr-offline" / manifest_data["webr_base_rel"] / "webr.mjs"
            repo = root / "webr-offline" / manifest_data["repo_rel"] / "bin" / "emscripten" / "contrib" / "4.6"
            check = [dist] + [repo / name for name in manifest_data.get("packages", [])]
            missing = [str(p) for p in check if not p.exists()]
            expected_hashes = manifest_data.get("sha256", {})
            hash_paths = {name: repo / name for name in manifest_data.get("packages", [])}
            hash_paths[f"webr-{manifest_data['webr_version']}.zip"] = root / "webr-offline" / f"webr-{manifest_data['webr_version']}.zip"
            for name, expected in expected_hashes.items():
                path = hash_paths.get(name)
                if path is None or not path.exists() or sha256_file(path).lower() != expected.lower():
                    hash_mismatches.append(name)
            offline_ok = not missing and not hash_mismatches
        except Exception as exc:
            reasons.append(f"offline webR manifest invalid: {exc}")
    else:
        reasons.append("offline webR manifest not found")
    if selected is None and offline_ok:
        selected = "offline_webr_metafor"
    elif selected is None:
        reasons.append("offline webR bundle is incomplete")

    result = {
        "selected_engine": selected or "none",
        "routing_order": ["native_r_metafor", "native_python", "online_webr_metafor", "offline_webr_metafor"],
        "native_r": {"path": rscript, "version": r_version, "metafor_version": metafor_version},
        "native_python": {"path": py, "version": platform.python_version() if py else None},
        "online_webr_reachable": args.online_webr_reachable,
        "offline_webr": {"ready": offline_ok, "manifest": str(manifest), "missing": missing,
                          "hash_mismatches": hash_mismatches,
                          "webr_version": (manifest_data or {}).get("webr_version")},
        "fallback_reasons": reasons,
        "host": {"system": platform.system(), "release": platform.release()},
    }
    print(json.dumps(result, ensure_ascii=False, indent=2))
    raise SystemExit(0 if selected else 2)


if __name__ == "__main__":
    main()
