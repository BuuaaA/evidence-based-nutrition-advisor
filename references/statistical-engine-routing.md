# Meta 分析统计引擎路由与审计

本规则只适用于已经通过临床可合并性判断、确实需要定量合并的研究级任务。统计引擎不能替代协议、双人筛选、数据核对、偏倚风险评价或 GRADE。

## 一、固定路由顺序

按下列顺序选择第一个可实际运行并通过自检的引擎，不按偏好随意切换：

1. **本机 R + metafor**：首选研究级路径。检测 `Rscript`，再运行 `requireNamespace("metafor", quietly=TRUE)`。使用 `scripts/meta_analysis.R`，由 `metafor::escalc()`、`metafor::rma()`、`metafor::forest()`、`metafor::funnel()` 完成计算和标准图形。
2. **本机 Python**：仅当本机 R 路径不可用时启用 `scripts/meta_compute.py`。这是独立复现实现，不得标成“由 metafor 运行”。输出必须注明 Python 版本、脚本版本、模型、区间方法、回退原因和交叉验证状态。
3. **在线 webR**：当本机 R 和 Python 都不能完成任务时，使用 `templates/metafor-runner.template.html` 在浏览器内运行 R + metafor。只使用项目锁定的官方 webR 与 R-Wasm 仓库；不得把研究数据上传到随机第三方在线 R 网站。
4. **离线 webR**：在线 webR 不可达，且没有用户明确选择、无需登录、完全免费、隐私可接受的在线 R 服务时，使用 `templates/metafor-runner-offline.template.html` 与 `webr-offline/`。本地服务优先 Python，若 Python 不存在则由 `scripts/serve_offline_webr.ps1` 提供纯 PowerShell/.NET 静态服务。

“无须账户的在线 R 服务”不是默认第五层。涉及健康或未发表研究数据时，不主动搜索或上传第三方服务；只有用户明确选择且完成隐私、可用性和方法学核验后才能使用。

## 二、引擎合格条件

### 本机 R

- `Rscript` 可执行；
- `metafor` 可加载并记录版本；
- 分析脚本退出码为 0，结果 JSON、研究级图形和 `sessionInfo()` 均生成；
- 原始输入、效应方向、连续性校正和至少一个独立计算已核对。

若 R 已安装但缺少 metafor，不擅自修改系统库。可在用户授权联网安装后写入项目或用户级 R library；否则记录原因并进入 Python 层。

### Python

- Python 3.8+；
- 数据校验、计算和图形生成全部成功；
- 对预计算 `yi`/`sei` 的金标准夹具与 metafor 结果在预设容差内一致；
- 森林图的研究 CI、权重方块、无效线、合并菱形、合并 CI、预测区间、坐标轴和数值列不能互相遮挡或错位。

Python 图形以 `metafor` 的信息结构、统计语义和版式关系为金标准。不同字体、SVG/PNG 渲染器和操作系统下不承诺逐像素一致；若任务要求逐像素相同，必须调用同一版本的 R/metafor 和相同图形设备。

### webR

- 记录 webR、R 和 metafor 版本；
- 在线路径必须先完成资源可达性检查；
- 离线路径必须核对 `webr-offline/manifest.json` 及其列出的包文件存在；
- 页面必须从 `http://localhost` 提供，不能用 `file://` 直接打开。

## 三、统一统计约定

- 默认随机效应模型，tau 平方估计器为 REML；固定效应结果仅作敏感性对照。
- 默认报告 95% CI、Q、I 平方、H 平方、tau 平方；k 至少为 3 时报告预测区间。
- 小样本随机效应推断优先使用 Knapp-Hartung（`test="knha"`）；若偏离必须预先说明。
- k<10 不运行 Egger 检验，也不能把“未发现不对称”解释为“无发表偏倚”。
- 不为得到森林图强行合并；高临床异质性、不可换算数据或 k=1 时采用结构化叙述合成。
- 比值型效应在对数尺度拟合，在展示层指数还原；图的无效线必须与展示尺度一致。

## 四、每次分析必须输出的审计字段

至少记录：

- `engine`、`engine_version`、`package`、`package_version`；
- `script_version`、运行时间、操作系统；
- `measure`、`model`、`tau2_estimator`、`inference`、`continuity_correction`；
- `fallback_from` 与逐层失败原因；
- 输入文件散列、研究数、排除或修正记录；
- `validation_status`、对照引擎/夹具及容差；
- 图形引擎、格式、尺寸和是否为 metafor 原生输出。

未完成对拍时写 `validation_status: not_cross_validated`，不得写“已通过 metafor 验证”。

## 五、最小可复现命令

先探测：

```powershell
python scripts/detect_meta_engine.py
```

本机 R + metafor：

```powershell
Rscript scripts/meta_analysis.R --csv data.csv --measure OR --method REML --test knha --outdir meta-output
```

Python 回退前先跑锁定夹具；没有 R 时仍会与冻结的 metafor 4.8.0 金标准对拍：

```powershell
python tests/validate_cross_engine.py
python scripts/meta_compute.py data.csv --measure OR --method REML --test knha --json results.json --forest-svg forest.svg --funnel-svg funnel.svg --out report.html --fallback-reason "native R/metafor unavailable" --validation-status "passed_against_metafor_4.8.0_golden"
```

在线 webR 报告由 `templates/metafor-runner.template.html` 填入数据和 R 代码后生成。离线版改用 `templates/metafor-runner-offline.template.html`，读取 `webr-offline/manifest.json` 填充本地运行时、仓库和包清单；Windows 双击 `start-offline-server.bat`，无 Python 时会自动调用 `scripts/serve_offline_webr.ps1`。
