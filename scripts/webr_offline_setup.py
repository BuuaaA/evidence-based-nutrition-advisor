#!/usr/bin/env python3
"""方案B：一次性下载 WebR 离线运行环境（需一次可访问外网/挂代理，之后完全离线）

下载内容到 skill 目录的 webr-offline/：
  1. WebR 运行时自托管包（webr-x.y.z.zip，来自 GitHub Releases，含 sha256 校验）
  2. metafor 及其全部非基础依赖的 Wasm 二进制包（来自 repo.r-wasm.org）

用法：
  python webr_offline_setup.py                 # 下载全部
  python webr_offline_setup.py --repo-only     # 只下载 R 包（运行时已有时）
  python webr_offline_setup.py --check         # 只解析依赖闭包、列清单，不下载

下载完成后按 webr-offline/README-offline.md 用本地 HTTP 服务打开交互版报告。
"""
import argparse
import hashlib
import os
import re
import sys
import urllib.request
import zipfile

HERE = os.path.dirname(os.path.abspath(__file__))
DEST = os.path.normpath(os.path.join(HERE, "..", "webr-offline"))

# 与现有交互模板 metafor-runner.template.html 使用的 WebR 版本保持一致
WEBR_VERSION = "0.6.0"
WEBR_ZIP = f"webr-{WEBR_VERSION}.zip"
WEBR_URL = f"https://github.com/r-wasm/webr/releases/download/v{WEBR_VERSION}/{WEBR_ZIP}"
WEBR_SHA256 = "d476e1d6e23cd6572450e2cf3b5faf93d8bd0c0284f4f8bb7b7f8aa4cd01aaf1"

# WebR 0.6.0 对应 R 4.6.x 的 wasm 包仓库
REPO_BASE = "https://repo.r-wasm.org/bin/emscripten/contrib/4.6"
ROOT_PKG = "metafor"

# 本地仓库必须复刻 repo.r-wasm.org 的目录结构：
# webr::install 会在 repos 后自动拼接 /bin/emscripten/contrib/<R版本> 去找 PACKAGES 索引
CONTRIB_SUB = os.path.join("repo", "bin", "emscripten", "contrib", "4.6")

# R 基础包（随 R 内核自带，无需下载）
BASE_PKGS = {
    "base", "compiler", "datasets", "graphics", "grDevices", "grid",
    "methods", "parallel", "splines", "stats", "stats4", "tcltk",
    "tools", "utils", "translations",
}

HEADERS = {"User-Agent": "ebn-skill-offline-setup/1.0"}


def http_get(url, timeout=120):
    req = urllib.request.Request(url, headers=HEADERS)
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.read()


def parse_packages(text):
    """解析 PACKAGES 索引 -> {包名: {version,file,depends,imports}}"""
    idx = {}
    for block in re.split(r"(?m)^Package:\s*", text):
        if not block.strip():
            continue
        lines = block.splitlines()
        name = lines[0].strip()
        fields = {}
        cur = None
        for ln in lines[1:]:
            m = re.match(r"^([A-Za-z0-9._-]+):\s*(.*)$", ln)
            if m:
                cur = m.group(1)
                fields[cur] = m.group(2)
            elif cur and ln.strip():
                fields[cur] += " " + ln.strip()
        def deps(key):
            out = []
            for part in re.split(r",", fields.get(key, "")):
                p = re.sub(r"\(.*?\)", "", part).strip()
                if p and p != "R":
                    out.append(p)
            return out
        idx[name] = {
            "version": fields.get("Version", ""),
            "file": fields.get("File", f"{name}_{fields.get('Version','')}.tgz"),
            "depends": deps("Depends"),
            "imports": deps("Imports"),
        }
    return idx


def closure(idx, root):
    """递归解析 Depends+Imports 依赖闭包（排除基础包）"""
    need, stack = set(), [root]
    while stack:
        p = stack.pop()
        if p in need or p in BASE_PKGS or p not in idx:
            continue
        need.add(p)
        stack.extend(idx[p]["depends"] + idx[p]["imports"])
    return sorted(need)


def download(url, path, sha256=None):
    if os.path.exists(path):
        print(f"  已存在，跳过：{os.path.basename(path)}")
        return True
    print(f"  下载 {url}")
    try:
        data = http_get(url)
    except Exception as e:
        print(f"  !! 下载失败：{e}")
        return False
    if sha256 and hashlib.sha256(data).hexdigest() != sha256:
        print("  !! sha256 校验不通过，已丢弃")
        return False
    with open(path, "wb") as f:
        f.write(data)
    print(f"  完成：{os.path.basename(path)}（{len(data)/1e6:.1f} MB）")
    return True


def extract_webr(zip_path, dest_dir):
    """解压 WebR 自托管包，并返回 webr.mjs 相对 dest 目录的路径。"""
    marker = os.path.join(dest_dir, "webr", ".extracted")
    if os.path.exists(marker):
        print("  已解压过，跳过")
    else:
        print("  解压 WebR 运行时 ...")
        with zipfile.ZipFile(zip_path) as z:
            z.extractall(dest_dir)
        os.makedirs(os.path.join(dest_dir, "webr"), exist_ok=True)
        open(marker, "w").write("ok")
    # 定位 webr.mjs（可能在顶层或 dist/ 子目录）
    for root, _, files in os.walk(dest_dir):
        if "webr.mjs" in files:
            rel = os.path.relpath(os.path.join(root, "webr.mjs"), dest_dir)
            return rel.replace(os.sep, "/")
    return None


def write_manifest_and_readme(webr_mjs_rel, pkg_files):
    """写出 manifest.json（供 Agent 生成离线报告时读取）与 README-offline.md（供人阅读）"""
    import json

    webr_base_rel = os.path.dirname(webr_mjs_rel).replace(os.sep, "/") if webr_mjs_rel else None
    hashes = {}
    zip_path = os.path.join(DEST, WEBR_ZIP)
    if os.path.isfile(zip_path):
        with open(zip_path, "rb") as f:
            hashes[WEBR_ZIP] = hashlib.sha256(f.read()).hexdigest()
    contrib_dir = os.path.join(DEST, CONTRIB_SUB)
    for name in pkg_files:
        path = os.path.join(contrib_dir, name)
        if os.path.isfile(path):
            with open(path, "rb") as f:
                hashes[name] = hashlib.sha256(f.read()).hexdigest()
    manifest = {
        "webr_version": WEBR_VERSION,
        "webr_base_rel": webr_base_rel,      # 相对 webr-offline/ 的运行时目录（含 webr.mjs）
        "repo_rel": "repo",
        "packages": pkg_files,               # repo/ 下的 .tgz 文件名列表（含 metafor 全部依赖）
        "sha256": hashes,
        "serve_port": 8321,
    }
    with open(os.path.join(DEST, "manifest.json"), "w", encoding="utf-8") as f:
        json.dump(manifest, f, ensure_ascii=False, indent=2)

    base_line = (
        f"- WebR {WEBR_VERSION} 运行时：`{webr_base_rel}/`（含 webr.mjs 与 R.wasm）"
        if webr_base_rel else
        "- WebR 运行时：未下载/未解压（重跑本脚本，不带 --repo-only）"
    )
    readme = f"""# WebR 离线运行环境（一次性下载，之后完全离线）

本目录由 `scripts/webr_offline_setup.py` 生成：

{base_line}
- metafor 及全部依赖：`repo/bin/emscripten/contrib/4.6/`（{len(pkg_files)} 个 Wasm 二进制包；
  目录结构必须与 repo.r-wasm.org 一致，webr::install 靠它定位索引）
- `reports/`：存放生成的离线交互版报告
- `manifest.json`：机器可读清单与 SHA-256 完整性值（Agent 生成离线报告和路由自检时读取）

## 使用方法

**方式一（推荐，双击即用）**：双击 skill 根目录下的 `start-offline-server.bat`。
启动器优先使用 Python；没有 Python 时自动使用 Windows PowerShell/.NET，
因此不要求设备预装 R 或 Python。停止服务关闭最小化的
"webr-offline-server" 窗口即可。

**方式二（手动命令行）**：

1. 在 **skill 根目录**（`webr-offline/` 的上一级）启动本地服务：

   ```
   python -m http.server 8321
   ```

2. 把生成的离线交互报告（`metafor-runner-offline.template.html` 填好的 HTML）
   放入 `webr-offline/reports/`。

3. 浏览器打开：`http://localhost:8321/webr-offline/reports/<报告文件名>.html`

## 分发到其他电脑

把整个 skill 目录（含本 `webr-offline/`，约 100MB）一起拷贝即可，
Windows 对方电脑直接双击 `start-offline-server.bat` 即可；有 Python 时使用
`http.server`，否则使用 PowerShell/.NET 静态服务。全程不需要访问境外网站。
若未拷贝本目录，需要在可访问官方 webR 与 R-Wasm 仓库的环境中先运行一次本脚本。

## 注意

- 必须通过 `http://localhost:8321` 地址打开，**双击 file:// 打不开**
  （浏览器安全限制：WebAssembly 模块与 Worker 需要 HTTP 环境）。
- 报告运行期间不要关闭本地服务窗口；用完 Ctrl+C 停止即可。
- Python 静态报告是本机 R 不可用时的第二级回退，不得标成 metafor 原生运行；
  研究级任务仍优先使用本机 R + metafor。
"""
    with open(os.path.join(DEST, "README-offline.md"), "w", encoding="utf-8") as f:
        f.write(readme)
    os.makedirs(os.path.join(DEST, "reports"), exist_ok=True)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--repo-only", action="store_true")
    ap.add_argument("--check", action="store_true")
    args = ap.parse_args()

    contrib_dir = os.path.join(DEST, CONTRIB_SUB)
    os.makedirs(contrib_dir, exist_ok=True)

    print("1/4 拉取包索引 PACKAGES ...")
    try:
        text = http_get(f"{REPO_BASE}/PACKAGES").decode("utf-8", "replace")
    except Exception as e:
        sys.exit(f"无法访问 {REPO_BASE}/PACKAGES ：{e}\n（此步需要一次可访问外网；挂代理后重试）")
    idx = parse_packages(text)
    if ROOT_PKG not in idx:
        sys.exit("索引中未找到 metafor，仓库结构可能已变化")

    need = closure(idx, ROOT_PKG)
    print(f"2/4 metafor 依赖闭包（{len(need)} 个，含自身）：")
    for p in need:
        print(f"    {p} {idx[p]['version']}")
    if args.check:
        return

    ok = True
    pkg_files = []
    for p in need:
        fn = idx[p]["file"]
        if download(f"{REPO_BASE}/{fn}", os.path.join(contrib_dir, fn)):
            pkg_files.append(fn)

    webr_mjs_rel = None
    zip_path = os.path.join(DEST, WEBR_ZIP)
    if not args.repo_only:
        print("3/4 下载 WebR 运行时自托管包 ...")
        if download(WEBR_URL, zip_path, WEBR_SHA256):
            print("4/4 解压 WebR 运行时 ...")
            webr_mjs_rel = extract_webr(zip_path, DEST)
            if webr_mjs_rel:
                print(f"  webr.mjs 位于：webr-offline/{webr_mjs_rel}")
            else:
                print("  !! 解压后未找到 webr.mjs，请检查 zip 内容")
                ok = False
        else:
            ok = False
    else:
        # 仅更新包时，若运行时尚在则沿用
        webr_mjs_rel = extract_webr(zip_path, DEST) if os.path.exists(zip_path) else None

    with open(os.path.join(contrib_dir, "PACKAGES"), "w", encoding="utf-8") as f:
        f.write(text)

    write_manifest_and_readme(webr_mjs_rel, pkg_files)

    print("\n完成。" if ok else "\n部分文件下载失败，请挂代理后重跑（已下载的不会重复下）。")
    print(f"离线环境位于：{DEST}")
    print("下一步：按 webr-offline/README-offline.md 启动本地服务并打开交互版报告。")


if __name__ == "__main__":
    main()
