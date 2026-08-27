# 普通用户双层交付协议

本协议只规定快速证据审计的用户界面。证据检索、判断和安全标准仍按 `rapid-audit.md`、`evidence-appraisal.md` 等资源完成。目标是让普通用户先得到可行动的决定，再按需查看证据。

## 0. 证据生成前的点击式收集

如果用户明确只问一般证据，直接进入检索，不弹出问卷。如果是个人决策或意图不明，且缺失信息通过“决策翻转测试”，先按 `pre-evidence-intake.md` 一次展示通常 3–5 项、至多 5 项点击选择；答案提交后再确定最终 PICOS 并生成下面的证据卡。用户可以跳过，跳过后按明确的常见情境回答。

优先使用宿主原生选择控件；其次使用 `scripts/collect_intake.py` 的一次性本地问卷；都不可用时使用紧凑编号选项。静态 HTML 若不能把答案返回给 Agent，就不能称为完成了信息收集。

## 1. 第一屏信息预算

第一屏正文只允许出现四项：

1. **买不买**：第一句话，使用受控判定语；
2. **对谁可能有用**：最匹配的人群或前提；
3. **效果上限**：用户可合理期待的最大收益，不用相对风险制造夸张感；
4. **安全红线**：最重要的禁忌、相互作用或就医信号。

四项的正文合计不超过 150 个中文字符。标题、字段标签、按钮文字不计入；不要靠删除安全信息满足字数限制。若安全红线无法压缩，宁可缩短其他三项。

买不买优先使用以下判定语：

| 代码 | 第一话术 | 典型含义 |
|---|---|---|
| `priority` | 值得优先考虑。 | 获益直接、确定性和决策价值均较高 |
| `conditional` | 只对特定人群值得。 | 获益取决于缺乏、疾病、剂型或其他明确条件 |
| `trial` | 可以试，但别期待太高。 | 风险较低，证据或效应有限，可设停止规则 |
| `not_worth` | 不太值得买。 | 证据不足、效应太小、成本不划算或替代路径更优 |
| `avoid` | 不建议自行使用。 | 潜在伤害、相互作用或需医学监督 |

不要用“总体而言”“理论上”“因人而异”占据第一句话。需要限定时放到“对谁可能有用”。

## 2. 三个展开层

第一屏下方只有三个一级交互入口，顺序固定：

### 为什么

- 2–4 个真正决定购买建议的事实；
- 实际效应使用绝对变化或普通人可理解的量级；
- 宣传从哪一层外推到了哪一层；
- 更可靠、更便宜或更直接的优先路径。

### 适不适合我

- 列出证据生成前已经采用的用户选择；
- 明示当前判断采用的暂定情境，避免把一般结论伪装成已个性化建议；
- 研究人群、基线状态和当前用户的相似性；
- 剂量、剂型、植物部位、菌株、盐型、配方或共干预边界；
- 明确列出不适合自行使用的人群；
- 用“高 / 中 / 低 / 未知”描述当前用户匹配度，不把匹配度写成研究质量；
- 只列仍未知且可能改变建议的信息。首次关键问题必须在证据生成前提出，不能藏在这一展开层；不要把这里变成第二份病史问卷，也不要要求先建健康档案。

### 证据怎么裁决

- 先用裁决表展示主要来源得出什么结论、为什么看似矛盾、各自的方法或适用性局限，以及本次为何赋予不同权重；
- 没有真正冲突时，说明哪些结局一致、为何最佳来源足以主导判断，不制造对立；
- 再按关键结局展示实际效应、证据体确定性和主要理由；
- 每个关键结局展开风险偏倚、不一致性、间接性、不精确性和传播偏倚五个域，不能只放一个笼统的“降级理由”；
- 明示确定性评价路径：引用已有 GRADE、基于快速证据综合的 GRADE、基于当前可得证据的暂定 GRADE，或 GRADE-informed 判断；后三者说明本次检索范围、全文能力、单人/双人及其他流程简化；
- 展示历史系统综述基座或“未找到合格基座”的判断，以及完整 PubMed 检索式、Query Translation、检索日期、命中/导出/筛查/全文/纳入计数和主要排除原因；
- 展示本次 PICOS 纳入与排除标准。决定性来源列表不能替代完整检索和筛选记录；
- PICOS、随访、检索/更新日期与 2–5 个决定性来源；
- 资金和利益冲突，以及什么新证据或用户信息会改变结论；
- 只有这一层可以进一步放置 Meta、GRADE、RoB、AMSTAR 2/ROBIS 或检索式等二级折叠内容。

用户未展开研究层时，不应先被专业术语阻塞。

## 3. HTML 产物

优先生成一个单文件、离线可打开的 HTML：

- 使用 `scripts/build_consumer_answer.py` 读取 UTF-8 JSON；
- 同时提供 `pubmed_search.py` 生成的检索 manifest、未经修改的 RIS，以及按 `templates/rapid-screening-log.csv` 完成的筛选日志；生成器会交叉核对检索式、Query Translation、命中/导出/筛选计数和 RIS 散列；
- 使用 `templates/consumer-answer.template.html`；
- 不加载外部 JavaScript、CSS、字体、分析脚本或追踪器；
- 三个入口使用原生 `<details>/<summary>`，支持键盘和屏幕阅读器；
- 所有用户、网页和论文文本在插入 HTML 前转义；
- 来源链接只接受 `http` 或 `https`；
- 文件名不包含疾病、用药或其他个人健康信息；
- 有文件预览能力时打开 HTML，并始终提供可点击文件链接。

最小 JSON 结构：

```json
{
  "title": "产品或干预名称",
  "verdict": "not_worth",
  "for_whom": "仅在某个明确条件下可能有用。",
  "effect_ceiling": "即使有效，预期也只是小幅改善。",
  "safety_red_line": "出现某风险或属于某人群时不要自行使用。",
  "why": {
    "summary": "一句解释",
    "key_points": ["决定结论的事实"],
    "better_options": ["更优先的路径"]
  },
  "suitability": {
    "intake_summary": ["本次已采用的点击选择；跳过时写明按一般情境"],
    "assumption": "暂按一般健康成人判断。",
    "user_match": "未知：缺少诊断和具体产品信息。",
    "may_fit": ["可能匹配的人群"],
    "avoid_or_check": ["禁忌或需先确认的情况"],
    "remaining_uncertainties": ["仍未知且可能改变建议的信息"]
  },
  "research": {
    "picos": "P 人群；I 干预；C 对照；O 结局与时间点；S 研究设计；随访",
    "effect": "关键效应和区间",
    "certainty": "低至极低（逐结局）",
    "certainty_method": "rapid_grade",
    "certainty_scope": "完整导出并单人筛查 PubMed 全部命中；未检索 Embase、CENTRAL 和注册库。",
    "certainty_reasons": ["降级理由"],
    "adjudication": [
      {"source": "来源或观点", "finding": "得出的结论", "why_differs": "为何不同或看似冲突", "weight": "本次权重及理由"}
    ],
    "outcomes": [{
      "outcome": "关键结局",
      "effect": "实际效应",
      "certainty": "低",
      "why": "升降级结论",
      "grade_domains": {
        "risk_of_bias": "严重/不严重/无法判断及理由",
        "inconsistency": "严重/不严重/无法判断及理由",
        "indirectness": "严重/不严重/无法判断及理由",
        "imprecision": "严重/不严重/无法判断及理由",
        "dissemination_bias": "严重/不严重/无法判断及理由"
      }
    }],
    "evidence_base": {
      "approach": "existing_review_plus_pubmed_update",
      "summary": "采用哪一份现有系统综述作为历史证据基座，以及为什么。",
      "appraisal": "基座的主要方法学优点和缺陷。",
      "search_end": "YYYY-MM-DD"
    },
    "search": {
      "database": "PubMed",
      "query": "完整检索式",
      "query_translation": "PubMed 返回的 Query Translation",
      "searched_at": "YYYY-MM-DD",
      "records_found": 0,
      "records_exported": 0,
      "records_screened": 0,
      "full_text_assessed": 0,
      "reports_included": 0,
      "studies_included": 0,
      "complete_retrieval": true,
      "screening_complete": true,
      "limits": "PubMed-only、单人筛选等限制。"
    },
    "evidence_access": {
      "full_text_unavailable": 0,
      "impact": "缺失全文可能如何影响效应与 GRADE。",
      "upload_prompt": "提示用户上传全文后重新筛选、提取和评级。"
    },
    "eligibility": {
      "inclusion": ["P/I/C/O/S 纳入标准"],
      "exclusion": ["预定义排除标准"],
      "exclusion_log": [{"reason": "实际主要排除原因", "count": "0"}]
    },
    "funding": "资金和利益冲突",
    "what_would_change": ["什么新证据或用户信息会改变结论"],
    "updated": "YYYY-MM-DD",
    "sources": [{"label": "来源标题", "url": "https://example.org", "role": "直接证据", "year": 2026}],
    "meta": "可选的 Meta 说明",
    "grade": "可选的 GRADE 说明",
    "rob": "可选的 RoB 说明"
  }
}
```

`certainty_method` 为必填，使用 `source_grade`、`rapid_grade`、`provisional_grade` 或 `grade_informed`。`provisional_grade` 只用于 PubMed 命中已完整导出、题名摘要已全部筛查、证据体边界可识别而部分候选全文不可得的情况；总确定性和每个结局等级必须带“暂定”。同时填写 `evidence_access.full_text_unavailable`、`impact` 和 `upload_prompt`，生成器会把数量与筛选 CSV 中的 `abstract_only` 记录核对并显示上传全文提示框。`grade_informed` 不得使用四级术语冒充正式评级。`certainty_scope` 说明证据识别范围、全文能力、单人/双人和关键简化。

`evidence_base`、`search`、`eligibility` 和每个 outcome 的 `grade_domains` 为新产物必填字段。`search.complete_retrieval=true` 时 `records_found` 必须等于 `records_exported`；`screening_complete=true` 时 `records_exported` 必须等于 `records_screened`。若检索或筛查不完整，普通功效结论只能使用 `insufficient`（“暂不能可靠判断”）或基于独立安全证据的 `avoid`，不能照常生成正向或购买性判定。

`picos` 是当前首选字段。生成脚本仍兼容旧输入中的 `pico`，但新产物必须显式包含 `S`（研究设计），并在适用时另列随访时长。`funding` 为当前字段，生成脚本仍兼容旧字段 `conflicts`。

`suitability.intake_summary` 用于显示证据生成前已经采用的信息；用户跳过时也要记录这一事实。`remaining_uncertainties` 只列提交后仍未知且可能改变建议的项目，最多 5 项。生成脚本继续兼容旧字段 `questions`，但新产物不再用它承载首次关键提问。

`meta`、`grade`、`rob` 缺失或为空时，不生成空的二级折叠。

生成命令：

```powershell
python scripts/build_consumer_answer.py answer.json `
  --html answer.html `
  --pubmed-manifest search-manifest.json `
  --pubmed-ris hits.ris `
  --screening-log screening.csv
```

任一审计文件与 JSON 不一致时停止生成，不能只修改 JSON 数字绕过检索和筛选。

## 4. 一图读懂

交付 HTML 后单独询问：

> 要不要我再生成一张“一图读懂”图片，方便你保存？

只有用户同意后才生成。图片必须从同一 JSON 的 `verdict`、`for_whom`、`effect_ceiling`、`safety_red_line` 和来源日期生成，不重新总结，不新增研究结论。优先用脚本的 `--svg` 输出生成可保存的矢量图；环境能可靠转换时可同时提供 PNG。文字不得交给会改写或拼错中文的图像生成模型。

## 5. 降级路径

- **不能提供点击控件或本地问卷**：先用一条紧凑消息列出全部编号选项，让用户只回复选项代码；用户也可以回复“跳过”。
- **不能写结果文件**：在聊天内用相同四项首屏，随后用“为什么 / 适不适合我 / 证据怎么裁决”三个 `<details>`；若界面过滤 HTML，则改用三个短链接式标题并等待用户选择展开。
- **不能预览 HTML**：仍生成文件并提供链接，附一句“下载后用浏览器打开”。
- **用户明确只要一句话**：只给判定语和最关键安全红线，不强制生成文件。
- **专业用户或单数据库 Meta 证据合成**：不使用本协议，转入专业研究交付。
