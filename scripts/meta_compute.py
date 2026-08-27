#!/usr/bin/env python3
"""纯标准库 meta 分析计算引擎（无需 pip 安装任何包，Python 3.8+ 即可运行）

实现逆方差法 meta 分析的核心数学（开放方法学）：
  - 二分类结局：OR / RR（对数尺度合并后指数还原）、RD（原始尺度）
  - 连续结局：MD、SMD（Hedges g）
  - 固定效应（FE）与随机效应（REML 或 DerSimonian-Laird 估计 tau^2）
  - 随机效应区间：z、Knapp-Hartung 或 modified Knapp-Hartung (adhoc)
  - 异质性：Q、I^2、H^2、tau^2、95% 预测区间（k>=3）
  - Egger 回归检验（仅当 k>=10）
  - 留一法敏感性分析
  - 森林图 / 漏斗图 SVG 生成
  - 静态 HTML 报告生成（零网络依赖，双击即开）

用法：
  python meta_compute.py data.csv --measure OR --title "BCG疫苗与结核风险" --out report.html
  python meta_compute.py data.csv --measure OR --json results.json   # 只输出JSON

CSV 列（二分类，推荐）: study,year,subgroup,ai,ci,n1i,n2i,source
CSV 列（二分类，兼容）: study_id,year,ai,bi,ci,di
CSV 列（连续，推荐）  : study,year,subgroup,m1i,sd1i,n1i,m2i,sd2i,n2i,source
CSV 列（连续，兼容）  : study_id,year,n1,mean1,sd1,n2,mean2,sd2
ai/n1i 组 = 干预组，ci/n2i 组 = 对照组。含 0 单元格的二分类研究自动加 0.5 校正。
"""
import argparse
import csv
import datetime
import hashlib
import html
import json
import math
import os
import platform
import sys

SCRIPT_VERSION = "2.1.0"

Z975 = 1.959963984540054


# ---------------- 分布函数（纯标准库实现） ----------------

def norm_cdf(z):
    return 0.5 * (1.0 + math.erf(z / math.sqrt(2.0)))


def norm_ppf(p):
    lo, hi = -40.0, 40.0
    for _ in range(200):
        mid = (lo + hi) / 2
        if norm_cdf(mid) < p:
            lo = mid
        else:
            hi = mid
    return (lo + hi) / 2


def _gamma_series(a, x, itmax=300, eps=3e-14):
    ap, s, d = a, 1.0 / a, 1.0 / a
    for _ in range(itmax):
        ap += 1
        d *= x / ap
        s += d
        if abs(d) < abs(s) * eps:
            break
    return s * math.exp(-x + a * math.log(x) - math.lgamma(a))


def _gamma_cf(a, x, itmax=300, eps=3e-14):
    tiny, b = 1e-300, x + 1.0 - a
    c, d, h = 1.0 / tiny, 1.0 / b, 1.0 / b
    for i in range(1, itmax + 1):
        an = -i * (i - a)
        b += 2.0
        d = an * d + b
        if abs(d) < tiny:
            d = tiny
        c = b + an / c
        if abs(c) < tiny:
            c = tiny
        d = 1.0 / d
        delta = d * c
        h *= delta
        if abs(delta - 1.0) < eps:
            break
    return h * math.exp(-x + a * math.log(x) - math.lgamma(a))


def chi2_sf(x, df):
    if x <= 0:
        return 1.0
    a = df / 2.0
    xh = x / 2.0
    if xh < a + 1.0:
        return 1.0 - _gamma_series(a, xh)
    return _gamma_cf(a, xh)


def _betacf(a, b, x, itmax=300, eps=3e-14):
    tiny = 1e-300
    qab, qap, qam = a + b, a + 1.0, a - 1.0
    c, d = 1.0, 1.0 - qab * x / qap
    if abs(d) < tiny:
        d = tiny
    d = 1.0 / d
    h = d
    for m in range(1, itmax + 1):
        m2 = 2 * m
        aa = m * (b - m) * x / ((qam + m2) * (a + m2))
        d = 1.0 + aa * d
        if abs(d) < tiny:
            d = tiny
        c = 1.0 + aa / c
        if abs(c) < tiny:
            c = tiny
        d = 1.0 / d
        h *= d * c
        aa = -(a + m) * (qab + m) * x / ((a + m2) * (qap + m2))
        d = 1.0 + aa * d
        if abs(d) < tiny:
            d = tiny
        c = 1.0 + aa / c
        if abs(c) < tiny:
            c = tiny
        d = 1.0 / d
        delta = d * c
        h *= delta
        if abs(delta - 1.0) < eps:
            break
    return h


def betai(a, b, x):
    if x <= 0:
        return 0.0
    if x >= 1:
        return 1.0
    ln_bt = (math.lgamma(a + b) - math.lgamma(a) - math.lgamma(b)
             + a * math.log(x) + b * math.log(1.0 - x))
    bt = math.exp(ln_bt)
    if x < (a + 1.0) / (a + b + 2.0):
        return bt * _betacf(a, b, x) / a
    return 1.0 - bt * _betacf(b, a, 1.0 - x) / b


def t_cdf(t, df):
    x = df / (df + t * t)
    p = 0.5 * betai(df / 2.0, 0.5, x)
    return 1.0 - p if t > 0 else p


def t_sf2(t, df):
    return 2.0 * (1.0 - t_cdf(abs(t), df))


def t_ppf(p, df):
    lo, hi = -60.0, 60.0
    for _ in range(200):
        mid = (lo + hi) / 2
        if t_cdf(mid, df) < p:
            lo = mid
        else:
            hi = mid
    return (lo + hi) / 2


# ---------------- 效应量计算 ----------------

def row_value(row, *names):
    for name in names:
        value = row.get(name)
        if value is not None and str(value).strip() != "":
            return str(value).strip()
    raise ValueError(f"缺少必需列或数值：{' / '.join(names)}")


def study_label(row):
    study = row_value(row, "study", "study_id")
    year = str(row.get("year", "")).strip()
    return f"{study} ({year})" if year else study

def compute_effects(rows, measure):
    """返回 (labels, yi, vi)。二分类对 0 单元格研究整体加 0.5（对齐 metafor 默认 to='only0'）。"""
    labels, yi, vi = [], [], []
    measure = measure.upper()
    if measure == "GEN":
        for r in rows:
            y = float(row_value(r, "yi"))
            if str(r.get("vi", "")).strip():
                v = float(r["vi"])
            else:
                se = float(row_value(r, "sei"))
                v = se * se
            if not math.isfinite(y) or not math.isfinite(v) or v <= 0:
                raise ValueError(f"预计算效应量或方差无效：{study_label(r)}")
            labels.append(study_label(r)); yi.append(y); vi.append(v)
    elif measure in ("OR", "RR", "RD"):
        for r in rows:
            a = float(row_value(r, "ai"))
            c = float(row_value(r, "ci"))
            if str(r.get("bi", "")).strip() and str(r.get("di", "")).strip():
                b, d = float(r["bi"]), float(r["di"])
            else:
                n1 = float(row_value(r, "n1i", "n1"))
                n2 = float(row_value(r, "n2i", "n2"))
                b, d = n1 - a, n2 - c
            if min(a, b, c, d) < 0:
                raise ValueError(f"事件数不能大于组内总数：{study_label(r)}")
            if min(a, b, c, d) == 0:
                a, b, c, d = a + 0.5, b + 0.5, c + 0.5, d + 0.5
            n1, n2 = a + b, c + d
            if measure == "OR":
                y = math.log((a * d) / (b * c))
                v = 1 / a + 1 / b + 1 / c + 1 / d
            elif measure == "RR":
                y = math.log((a / n1) / (c / n2))
                v = 1 / a - 1 / n1 + 1 / c - 1 / n2
            else:  # RD
                p1, p2 = a / n1, c / n2
                y = p1 - p2
                v = p1 * (1 - p1) / n1 + p2 * (1 - p2) / n2
            labels.append(study_label(r))
            yi.append(y)
            vi.append(v)
    elif measure in ("MD", "SMD"):
        for r in rows:
            n1 = float(row_value(r, "n1i", "n1"))
            m1 = float(row_value(r, "m1i", "mean1"))
            s1 = float(row_value(r, "sd1i", "sd1"))
            n2 = float(row_value(r, "n2i", "n2"))
            m2 = float(row_value(r, "m2i", "mean2"))
            s2 = float(row_value(r, "sd2i", "sd2"))
            if n1 <= 1 or n2 <= 1 or s1 < 0 or s2 < 0:
                raise ValueError(f"连续结局的样本量或标准差无效：{study_label(r)}")
            if measure == "MD":
                y = m1 - m2
                v = s1 * s1 / n1 + s2 * s2 / n2
            else:
                df_ = n1 + n2 - 2
                sp = math.sqrt(((n1 - 1) * s1 * s1 + (n2 - 1) * s2 * s2) / df_)
                d = (m1 - m2) / sp
                # Exact small-sample bias correction used by metafor::.cmicalc().
                J = math.exp(math.lgamma(df_ / 2.0) - 0.5 * math.log(df_ / 2.0)
                             - math.lgamma((df_ - 1.0) / 2.0))
                y = J * d
                # metafor escalc(measure="SMD", vtype="LS") default.
                v = 1.0 / n1 + 1.0 / n2 + y * y / (2.0 * (n1 + n2))
            labels.append(study_label(r))
            yi.append(y)
            vi.append(v)
    else:
        raise ValueError(f"不支持的效应量: {measure}（可选 OR/RR/RD/MD/SMD/GEN）")
    return labels, yi, vi


# ---------------- 合并模型 ----------------

def fit_model(yi, vi, tau2=0.0):
    w = [1.0 / (v + tau2) for v in vi]
    sw = sum(w)
    mu = sum(wi * y for wi, y in zip(w, yi)) / sw
    se = math.sqrt(1.0 / sw)
    return mu, se, w


def derSimonian_laird(yi, vi):
    mu_fe, _, w = fit_model(yi, vi, 0.0)
    Q = sum(wi * (y - mu_fe) ** 2 for wi, y in zip(w, yi))
    k = len(yi)
    S1 = sum(w)
    S2 = sum(wi * wi for wi in w)
    tau2 = max(0.0, (Q - (k - 1)) / (S1 - S2 / S1)) if k > 1 else 0.0
    return Q, tau2


def _reml_ll(tau2, yi, vi):
    w = [1.0 / (v + tau2) for v in vi]
    sw = sum(w)
    mu = sum(wi * y for wi, y in zip(w, yi)) / sw
    return -0.5 * (sum(math.log(v + tau2) for v in vi) + math.log(sw)
                   + sum(wi * (y - mu) ** 2 for wi, y in zip(w, yi)))


def reml_tau2(yi, vi, itmax=100, threshold=1e-5):
    """Intercept-only REML using metafor's default Fisher-scoring update."""
    k = len(yi)
    mean_y = sum(yi) / k
    rss = sum((y - mean_y) ** 2 for y in yi)
    tr_pv = (k - 1.0) / k * sum(vi)
    tau2 = max(0.0, (rss - tr_pv) / (k - 1.0))
    for _ in range(itmax):
        old = tau2
        w = [1.0 / (v + tau2) for v in vi]
        sw = sum(w)
        sw2 = sum(x * x for x in w)
        sw3 = sum(x * x * x for x in w)
        mu = sum(x * y for x, y in zip(w, yi)) / sw
        quad_pp = sum(x * x * (y - mu) ** 2 for x, y in zip(w, yi))
        tr_p = sw - sw2 / sw
        tr_pp = sw2 - 2.0 * sw3 / sw + (sw2 * sw2) / (sw * sw)
        adj = (quad_pp - tr_p) / tr_pp
        while tau2 + adj < 0.0:
            adj /= 2.0
        tau2 += adj
        if abs(old - tau2) <= threshold:
            break
    return max(0.0, tau2)


def full_analysis(yi, vi, method="REML", test="knha"):
    k = len(yi)
    mu_fe, se_fe, _ = fit_model(yi, vi, 0.0)
    Q, tau2_dl = derSimonian_laird(yi, vi)
    tau2 = reml_tau2(yi, vi) if method.upper() == "REML" else tau2_dl
    mu_re, se_re_z, w_re = fit_model(yi, vi, tau2)
    test = test.lower()
    if test not in ("z", "knha", "adhoc"):
        raise ValueError("test 必须是 z、knha 或 adhoc")
    q_hk = (sum(w * (y - mu_re) ** 2 for w, y in zip(w_re, yi)) / (k - 1)) if k > 1 else 1.0
    hk_scale = max(1.0, q_hk) if test == "adhoc" else q_hk
    if test == "z" or k < 2:
        se_re = se_re_z
        critical = Z975
        inference = "z"
    else:
        se_re = math.sqrt(hk_scale / sum(w_re))
        critical = t_ppf(0.975, k - 1)
        inference = test
    # Match metafor::rma(): model-based I2/H2 use tau2 and the typical
    # within-study sampling variance, not the Q-only shortcut.
    w_fe = [1.0 / v for v in vi]
    sw_fe = sum(w_fe)
    vt = ((k - 1) * sw_fe / (sw_fe * sw_fe - sum(w * w for w in w_fe))) if k > 1 else math.inf
    I2 = 100.0 * tau2 / (vt + tau2) if math.isfinite(vt) and tau2 > 0 else 0.0
    H2 = tau2 / vt + 1.0 if math.isfinite(vt) and vt > 0 else 1.0
    p_Q = chi2_sf(Q, k - 1) if k > 1 else None
    pi_lo = pi_hi = None
    if k >= 3 and tau2 > 0:
        tq = t_ppf(0.975, k - 2)
        pi_lo = mu_re - tq * math.sqrt(tau2 + se_re * se_re)
        pi_hi = mu_re + tq * math.sqrt(tau2 + se_re * se_re)
    return {
        "k": k,
        "fe": {"est": mu_fe, "se": se_fe,
               "ci_lo": mu_fe - Z975 * se_fe, "ci_hi": mu_fe + Z975 * se_fe},
        "re": {"est": mu_re, "se": se_re,
               "ci_lo": mu_re - critical * se_re, "ci_hi": mu_re + critical * se_re},
        "Q": Q, "p_Q": p_Q, "tau2": tau2, "tau": math.sqrt(tau2),
        "I2": I2, "H2": H2, "pi_lo": pi_lo, "pi_hi": pi_hi,
        "w_re": w_re, "inference": inference, "hk_scale": q_hk,
    }


def egger_test(yi, vi):
    k = len(yi)
    if k < 10:
        return None
    sei = [math.sqrt(v) for v in vi]
    z = [y / s for y, s in zip(yi, sei)]
    x = [1.0 / s for s in sei]
    mx = sum(x) / k
    my = sum(z) / k
    sxx = sum((xi - mx) ** 2 for xi in x)
    sxy = sum((xi - mx) * (zi - my) for xi, zi in zip(x, z))
    slope = sxy / sxx
    intercept = my - slope * mx
    rss = sum((zi - intercept - slope * xi) ** 2 for xi, zi in zip(x, z))
    s2 = rss / (k - 2)
    se_int = math.sqrt(s2 * (1.0 / k + mx * mx / sxx))
    t = intercept / se_int
    return {"intercept": intercept, "se": se_int, "t": t,
            "p": t_sf2(t, k - 2), "df": k - 2}


def leave_one_out(yi, vi, method="REML", test="knha"):
    out = []
    for i in range(len(yi)):
        y2 = yi[:i] + yi[i + 1:]
        v2 = vi[:i] + vi[i + 1:]
        res = full_analysis(y2, v2, method, test)
        out.append(res["re"])
    return out


# ---------------- SVG 图形 ----------------

def forest_svg(labels, yi, vi, res, measure, width=1040, row_h=30):
    """Metafor-style forest plot with pooled diamond exactly spanning its CI."""
    ratio = measure.upper() in ("OR", "RR")
    exp_t = math.exp if ratio else (lambda x: x)
    null_v = 0.0  # OR/RR are fitted on log scale; exp(0) is the displayed null value 1.
    study_lo = [y - Z975 * math.sqrt(v) for y, v in zip(yi, vi)]
    study_hi = [y + Z975 * math.sqrt(v) for y, v in zip(yi, vi)]
    bounds = study_lo + study_hi + [res["re"]["ci_lo"], res["re"]["ci_hi"], null_v]
    if res["pi_lo"] is not None:
        bounds += [res["pi_lo"], res["pi_hi"]]
    lo_x, hi_x = min(bounds), max(bounds)
    pad = max((hi_x - lo_x) * 0.08, 0.05)
    lo_x, hi_x = lo_x - pad, hi_x + pad
    plot_l, plot_r = 285, 665
    value_x, weight_x = 690, 970
    sx = lambda v: plot_l + (v - lo_x) / (hi_x - lo_x) * (plot_r - plot_l)
    k = len(yi)
    row0 = 66
    pooled_y = row0 + k * row_h + 12
    pi_y = pooled_y + (34 if res["pi_lo"] is not None else 0)
    ax_y = pi_y + 38
    height = ax_y + 78
    sw = sum(res["w_re"])
    parts = [f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {width} {height}" '
             f'font-family="Arial,Segoe UI,Microsoft YaHei,sans-serif" font-size="12">',
             f'<rect width="{width}" height="{height}" fill="#fff"/>']
    parts += [
        '<text x="274" y="26" text-anchor="end" font-weight="bold">Study</text>',
        f'<text x="{(plot_l+plot_r)/2}" y="26" text-anchor="middle" font-weight="bold">{html.escape(measure)} and 95% CI</text>',
        f'<text x="{value_x}" y="26" font-weight="bold">Effect [95% CI]</text>',
        f'<text x="{weight_x}" y="26" text-anchor="middle" font-weight="bold">Weight</text>',
        f'<line x1="20" y1="40" x2="{width-20}" y2="40" stroke="#111827" stroke-width="1"/>',
        f'<line data-role="null-line" data-null-internal="0" data-null-display="{1 if ratio else 0}" x1="{sx(null_v)}" y1="44" x2="{sx(null_v)}" y2="{ax_y-8}" stroke="#9ca3af" stroke-width="1" stroke-dasharray="4 4"/>'
    ]
    for i, (lab, y, v) in enumerate(zip(labels, yi, vi)):
        cy = row0 + i * row_h
        lo, hi = study_lo[i], study_hi[i]
        w_pct = res["w_re"][i] / sw * 100
        side = 3.2 + 9.5 * math.sqrt(w_pct / max(100.0, w_pct))
        parts.append(f'<text x="274" y="{cy+4}" text-anchor="end" fill="#111827">{html.escape(lab)}</text>')
        parts.append(f'<line x1="{sx(lo):.2f}" y1="{cy}" x2="{sx(hi):.2f}" y2="{cy}" stroke="#111827" stroke-width="1.2"/>')
        parts.append(f'<line x1="{sx(lo):.2f}" y1="{cy-3}" x2="{sx(lo):.2f}" y2="{cy+3}" stroke="#111827"/>')
        parts.append(f'<line x1="{sx(hi):.2f}" y1="{cy-3}" x2="{sx(hi):.2f}" y2="{cy+3}" stroke="#111827"/>')
        parts.append(f'<rect x="{sx(y)-side:.2f}" y="{cy-side:.2f}" width="{2*side:.2f}" height="{2*side:.2f}" fill="#111827"/>')
        est_s = f'{exp_t(y):.2f} [{exp_t(lo):.2f}, {exp_t(hi):.2f}]' if ratio else f'{y:.2f} [{lo:.2f}, {hi:.2f}]'
        parts.append(f'<text x="{value_x}" y="{cy+4}" fill="#111827">{est_s}</text>')
        parts.append(f'<text x="{weight_x}" y="{cy+4}" text-anchor="middle" fill="#111827">{w_pct:.1f}%</text>')

    r = res["re"]
    lo, hi = r["ci_lo"], r["ci_hi"]
    pts = f'{sx(lo):.2f},{pooled_y} {sx(r["est"]):.2f},{pooled_y-10} {sx(hi):.2f},{pooled_y} {sx(r["est"]):.2f},{pooled_y+10}'
    parts.append(f'<line x1="20" y1="{pooled_y-20}" x2="{width-20}" y2="{pooled_y-20}" stroke="#d1d5db"/>')
    parts.append(f'<polygon data-role="pooled-diamond" data-ci-lo="{lo:.12g}" data-est="{r["est"]:.12g}" data-ci-hi="{hi:.12g}" points="{pts}" fill="#111827"/>')
    est_s = f'{exp_t(r["est"]):.2f} [{exp_t(lo):.2f}, {exp_t(hi):.2f}]' if ratio else f'{r["est"]:.2f} [{lo:.2f}, {hi:.2f}]'
    parts.append(f'<text x="274" y="{pooled_y+4}" text-anchor="end" font-weight="bold">Random-effects model</text>')
    parts.append(f'<text x="{value_x}" y="{pooled_y+4}" font-weight="bold">{est_s}</text>')
    if res["pi_lo"] is not None:
        plo, phi = res["pi_lo"], res["pi_hi"]
        parts.append(f'<text x="274" y="{pi_y+4}" text-anchor="end">Prediction interval</text>')
        parts.append(f'<line data-role="prediction-interval" x1="{sx(plo):.2f}" y1="{pi_y}" x2="{sx(phi):.2f}" y2="{pi_y}" stroke="#111827" stroke-width="2"/>')
        for px in (sx(plo), sx(phi)):
            parts.append(f'<line x1="{px:.2f}" y1="{pi_y-5}" x2="{px:.2f}" y2="{pi_y+5}" stroke="#111827" stroke-width="2"/>')
        pi_s = f'{exp_t(plo):.2f} to {exp_t(phi):.2f}' if ratio else f'{plo:.2f} to {phi:.2f}'
        parts.append(f'<text x="{value_x}" y="{pi_y+4}">{pi_s}</text>')

    parts.append(f'<line x1="{plot_l}" y1="{ax_y}" x2="{plot_r}" y2="{ax_y}" stroke="#111827"/>')
    ticks = [0.1, 0.25, 0.5, 1, 2, 4, 10] if ratio else None
    if ticks:
        for t in ticks:
            lt = math.log(t)
            if lo_x <= lt <= hi_x:
                parts.append(f'<line x1="{sx(lt)}" y1="{ax_y}" x2="{sx(lt)}" y2="{ax_y+5}" stroke="#111827"/>')
                parts.append(f'<text x="{sx(lt)}" y="{ax_y+18}" text-anchor="middle">{t:g}</text>')
    else:
        raw_step = (hi_x - lo_x) / 7.0
        mag = 10 ** math.floor(math.log10(raw_step))
        norm = raw_step / mag
        nice = 1 if norm <= 1 else 2 if norm <= 2 else 2.5 if norm <= 2.5 else 5 if norm <= 5 else 10
        step = nice * mag
        first = math.ceil(lo_x / step) * step
        ticks_linear = []
        tv = first
        while tv <= hi_x + step * 1e-9:
            ticks_linear.append(0.0 if abs(tv) < step * 1e-9 else tv)
            tv += step
        for tv in ticks_linear:
            parts.append(f'<line x1="{sx(tv)}" y1="{ax_y}" x2="{sx(tv)}" y2="{ax_y+5}" stroke="#111827"/>')
            parts.append(f'<text x="{sx(tv)}" y="{ax_y+18}" text-anchor="middle">{tv:g}</text>')
    parts.append(f'<text x="{(plot_l+plot_r)/2}" y="{ax_y+38}" text-anchor="middle">{html.escape(measure)}</text>')
    het = f'REML: tau²={res["tau2"]:.3f}; I²={res["I2"]:.1f}%; Q={res["Q"]:.2f}; inference={res["inference"]}'
    parts.append(f'<text x="20" y="{ax_y+64}" fill="#374151">{html.escape(het)}</text>')
    parts.append('</svg>')
    return '\n'.join(parts)


def funnel_svg(yi, vi, res, measure, width=560, height=420):
    ratio = measure.upper() in ("OR", "RR")
    exp_t = math.exp if ratio else (lambda x: x)
    sei = [math.sqrt(v) for v in vi]
    mu = res["re"]["est"]
    y_lo, y_hi = min(yi), max(yi)
    s_lo = min(y_lo, mu - 1.96 * max(sei)) - 0.1
    s_hi = max(y_hi, mu + 1.96 * max(sei)) + 0.1
    s_max = max(sei) * 1.15
    pl, pr, pt, pb = 70, width - 30, 30, height - 60
    sx = lambda v: pl + (v - s_lo) / (s_hi - s_lo) * (pr - pl)
    sy = lambda s: pt + (s / s_max) * (pb - pt)
    parts = [f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {width} {height}" '
             f'font-family="system-ui,Segoe UI,Microsoft YaHei,sans-serif" font-size="12">',
             f'<rect width="{width}" height="{height}" fill="#fff"/>']
    parts.append(f'<line x1="{sx(mu)}" y1="{sy(0)}" x2="{sx(mu - 1.96*s_max)}" y2="{pb}" stroke="#cbd5e1"/>')
    parts.append(f'<line x1="{sx(mu)}" y1="{sy(0)}" x2="{sx(mu + 1.96*s_max)}" y2="{pb}" stroke="#cbd5e1"/>')
    parts.append(f'<line x1="{sx(mu)}" y1="{pt}" x2="{sx(mu)}" y2="{pb}" stroke="#94a3b8" stroke-dasharray="4 3"/>')
    for y, s in zip(yi, sei):
        parts.append(f'<circle cx="{sx(y)}" cy="{sy(s)}" r="4.5" fill="#2563eb" fill-opacity="0.75"/>')
    parts.append(f'<line x1="{pl}" y1="{pb}" x2="{pr}" y2="{pb}" stroke="#334155"/>')
    parts.append(f'<line x1="{pl}" y1="{pt}" x2="{pl}" y2="{pb}" stroke="#334155"/>')
    for j in range(5):
        tv = s_lo + (s_hi - s_lo) * j / 4
        parts.append(f'<text x="{sx(tv)}" y="{pb+16}" text-anchor="middle" fill="#475569">{exp_t(tv):.2g}</text>' if ratio
                     else f'<text x="{sx(tv)}" y="{pb+16}" text-anchor="middle" fill="#475569">{tv:.2g}</text>')
    for j in range(4):
        sv = s_max * j / 3
        parts.append(f'<text x="{pl-8}" y="{sy(sv)+4}" text-anchor="end" fill="#475569">{sv:.2f}</text>')
    parts.append(f'<text x="{(pl+pr)/2}" y="{height-14}" text-anchor="middle" fill="#475569">效应量</text>')
    parts.append(f'<text x="16" y="{(pt+pb)/2}" text-anchor="middle" fill="#475569" '
                 f'transform="rotate(-90 16 {(pt+pb)/2})">标准误（越小越精确）</text>')
    parts.append('</svg>')
    return '\n'.join(parts)


# ---------------- 报告生成 ----------------

def fmt_p(p):
    if p is None:
        return "—"
    return "<0.001" if p < 0.001 else f"{p:.3f}"


def build_report(template_path, ctx):
    with open(template_path, encoding="utf-8") as f:
        tpl = f.read()
    for key, val in ctx.items():
        tpl = tpl.replace(f"__{key}__", val)
    return tpl


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("csv", help="数据提取CSV")
    ap.add_argument("--measure", required=True, choices=["OR", "RR", "RD", "MD", "SMD", "GEN"])
    ap.add_argument("--method", default="REML", choices=["REML", "DL"],
                    help="tau^2 估计器：REML（默认）或 DL（DerSimonian-Laird）")
    ap.add_argument("--test", default="knha", choices=["z", "knha", "adhoc"],
                    help="随机效应区间：z、Knapp-Hartung（默认）或 modified KH")
    ap.add_argument("--title", default="Meta 分析报告")
    ap.add_argument("--out", default="report-static.html")
    ap.add_argument("--json", dest="json_out", default=None)
    ap.add_argument("--forest-svg", default=None)
    ap.add_argument("--funnel-svg", default=None)
    ap.add_argument("--fallback-reason", action="append", default=[])
    ap.add_argument("--validation-status", default="not_cross_validated")
    ap.add_argument("--template", default=os.path.join(
        os.path.dirname(os.path.abspath(__file__)), "..", "templates", "report-static.template.html"))
    args = ap.parse_args()

    with open(args.csv, encoding="utf-8-sig") as f:
        rows = list(csv.DictReader(f))
    if len(rows) < 2:
        sys.exit("错误：至少需要 2 项研究才能合并；k=1 时请按 research-synthesis.md 做描述性报告")

    labels, yi, vi = compute_effects(rows, args.measure)
    res = full_analysis(yi, vi, args.method, args.test)
    eg = egger_test(yi, vi)
    loo = leave_one_out(yi, vi, args.method, args.test)
    ratio = args.measure.upper() in ("OR", "RR")
    exp_t = math.exp if ratio else (lambda x: x)
    unit = args.measure

    def ci_str(d):
        return f"{exp_t(d['est']):.3f} [{exp_t(d['ci_lo']):.3f}, {exp_t(d['ci_hi']):.3f}]" if ratio \
            else f"{d['est']:.3f} [{d['ci_lo']:.3f}, {d['ci_hi']:.3f}]"

    summary_rows = ""
    for lab, y, v, w in zip(labels, yi, vi, res["w_re"]):
        lo, hi = y - Z975 * math.sqrt(v), y + Z975 * math.sqrt(v)
        s = f"{exp_t(y):.3f} [{exp_t(lo):.3f}, {exp_t(hi):.3f}]" if ratio else f"{y:.3f} [{lo:.3f}, {hi:.3f}]"
        summary_rows += f"<tr><td>{html.escape(lab)}</td><td>{s}</td><td>{w/sum(res['w_re'])*100:.1f}%</td></tr>\n"

    loo_rows = ""
    for lab, r in zip(labels, loo):
        s = f"{exp_t(r['est']):.3f} [{exp_t(r['ci_lo']):.3f}, {exp_t(r['ci_hi']):.3f}]" if ratio \
            else f"{r['est']:.3f} [{r['ci_lo']:.3f}, {r['ci_hi']:.3f}]"
        loo_rows += f"<tr><td>剔除 {html.escape(lab)}</td><td>{s}</td></tr>\n"

    pi_str = "—"
    if res["pi_lo"] is not None:
        pi_str = (f"{exp_t(res['pi_lo']):.3f} – {exp_t(res['pi_hi']):.3f}" if ratio
                  else f"{res['pi_lo']:.3f} – {res['pi_hi']:.3f}")

    egger_str = ("未执行（研究数 k<10，Egger 检验不适用）" if eg is None else
                 f"截距 {eg['intercept']:.3f}（SE {eg['se']:.3f}），t={eg['t']:.2f}，P={fmt_p(eg['p'])}"
                 + ("；未发现明显不对称信号" if eg['p'] >= 0.05 else "；提示可能存在发表偏倚/小样本效应，需谨慎解读"))

    with open(args.csv, "rb") as f:
        input_sha256 = hashlib.sha256(f.read()).hexdigest()
    results = {
        "engine": "native_python",
        "engine_version": platform.python_version(),
        "package": None,
        "package_version": None,
        "script_version": SCRIPT_VERSION,
        "plot_engine": "python_stdlib_metafor_style_svg",
        "native_metafor_plot": False,
        "validation_status": args.validation_status,
        "fallback_from": args.fallback_reason or ["native_r_metafor unavailable or not selected"],
        "input_sha256": input_sha256,
        "title": args.title, "measure": args.measure, "method": args.method, "k": res["k"],
        "model": "random-effects", "inference": res["inference"], "hk_scale": res["hk_scale"],
        "fe_est": res["fe"]["est"], "fe_ci": [res["fe"]["ci_lo"], res["fe"]["ci_hi"]],
        "re_est": res["re"]["est"], "re_ci": [res["re"]["ci_lo"], res["re"]["ci_hi"]],
        "re_ci_str": ci_str(res["re"]), "Q": res["Q"], "p_Q": res["p_Q"],
        "tau2": res["tau2"], "I2": res["I2"], "H2": res["H2"],
        "pi": [res["pi_lo"], res["pi_hi"]], "egger": eg,
        "study_labels": labels, "yi": yi, "vi": vi,
    }
    if args.json_out:
        with open(args.json_out, "w", encoding="utf-8") as f:
            json.dump(results, f, ensure_ascii=False, indent=2)
        print(f"JSON 结果 → {args.json_out}")

    forest = forest_svg(labels, yi, vi, res, args.measure)
    funnel = funnel_svg(yi, vi, res, args.measure)
    if args.forest_svg:
        with open(args.forest_svg, "w", encoding="utf-8") as f:
            f.write(forest)
        print(f"森林图 SVG → {args.forest_svg}")
    if args.funnel_svg:
        with open(args.funnel_svg, "w", encoding="utf-8") as f:
            f.write(funnel)
        print(f"漏斗图 SVG → {args.funnel_svg}")

    if os.path.exists(args.template):
        ctx = {
            "TITLE": html.escape(args.title),
            "MEASURE": args.measure,
            "METHOD": "REML" if args.method == "REML" else "DerSimonian-Laird",
            "INFERENCE": res["inference"],
            "ENGINE": f"Python {platform.python_version()} / stdlib independent implementation",
            "VALIDATION": args.validation_status,
            "K": str(res["k"]),
            "RE_EST": ci_str(res["re"]),
            "FE_EST": ci_str(res["fe"]),
            "Q": f"{res['Q']:.2f}",
            "P_Q": fmt_p(res["p_Q"]),
            "TAU2": f"{res['tau2']:.4f}",
            "I2": f"{res['I2']:.1f}%",
            "H2": f"{res['H2']:.2f}",
            "PI": pi_str,
            "EGGER": egger_str,
            "SUMMARY_ROWS": summary_rows,
            "LOO_ROWS": loo_rows,
            "FOREST_SVG": forest,
            "FUNNEL_SVG": funnel,
            "GENERATED": datetime.date.today().isoformat(),
        }
        html_out = build_report(args.template, ctx)
        with open(args.out, "w", encoding="utf-8") as f:
            f.write(html_out)
        print(f"静态报告 → {args.out}（零网络依赖，双击即开）")
    else:
        print(f"提示：未找到模板 {args.template}，仅输出统计结果：", file=sys.stderr)
        print(json.dumps(results, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
