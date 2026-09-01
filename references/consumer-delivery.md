# 普通用户双层交付协议

本协议规定普通用户的默认产品界面。证据判断可以来自 L1-Quick、已审计缓存或本轮完成的 L1-Audited；每种状态都必须有与实际完成度匹配的证据护照。目标是先显示可行动决定，再渐进展开理由、适用性和科学审计。

## 受众适配解释层

先完成证据裁决并锁定结构化字段，再调整表达。健康场景默认面向有正常理解能力的普通成年人，不把未指定受众机械当成 5 岁儿童。

- 从用户明确说明的年龄、专业背景、角色和阅读目的判断解释深度；没有说明时使用清楚、尊重、非专业化的成人语言。
- 第一层先回答“这是什么结论”和“对我意味着什么”；专业术语只在确有必要时出现，并在首次出现时用一句普通话解释。
- 类比只能帮助理解，不能替代数值、效应方向或安全规则。若类比会模糊因果与相关、群体平均与个人体验、替代指标与真实结局，删除类比。
- 面向专业人员保留 PICOS、效应量和方法权衡；面向普通用户把这些内容翻译成适用对象、可能改善多少、多久能看出、什么情况下不适用。
- 语言可以更简单，科学精度不能打折。不得为了“更容易懂”删除不确定性、适用边界、剂型差异、风险信号或把“可能”改写成“有效”。
- 结尾落到当前受众需要作出的决定或下一步，不以百科式定义结束。

## 0. 证据生成前的点击式收集

如果用户明确只问一般证据，直接进入检索，不弹出问卷。如果是个人决策或意图不明，且缺失信息通过“决策翻转测试”，先按 `pre-evidence-intake.md` 一次展示通常 3–5 项、至多 5 项点击选择；答案提交后再确定最终 PICOS 并生成下面的证据卡。用户可以跳过，跳过后按明确的常见情境回答。

优先使用宿主原生选择控件；其次使用 `scripts/collect_intake.py` 的一次性本地问卷；都不可用时一次只问一个自然语言问题。不得展示 A/B/C、1A/2B 等机器编码。静态 HTML 若不能把答案返回给 Agent，就不能称为完成了信息收集。

## 1. 第一屏信息预算

第一屏科学正文只允许出现四项：

1. **买不买**：第一句话，使用受控判定语；
2. **对谁可能有用**：最匹配的人群或前提；
3. **效果上限**：用户可合理期待的最大收益，不用相对风险制造夸张感；
4. **安全红线**：最重要的禁忌、相互作用或就医信号。

四项的正文合计不超过 150 个中文字符。标题、字段标签、行动按钮文字不计入；行动栏不得增加新的功效或安全宣称。不要靠删除安全信息满足字数限制。若安全红线无法压缩，宁可缩短其他三项。

买不买优先使用以下判定语：

| 代码 | 第一话术 | 典型含义 |
|---|---|---|
| `priority` | 值得优先考虑。 | 获益直接、确定性和决策价值均较高 |
| `conditional` | 只对特定人群值得。 | 获益取决于缺乏、疾病、剂型或其他明确条件 |
| `trial` | 可以低风险试用。 | 证据不确定但四道门全部通过，并已预设目标、阈值和停止规则 |
| `not_worth` | 不太值得买。 | 证据不足、效应太小、成本不划算或替代路径更优 |
| `avoid` | 不建议自行使用。 | 潜在伤害、相互作用或需医学监督 |

不要用“总体而言”“理论上”“因人而异”占据第一句话。需要限定时放到“对谁可能有用”。

`verdict` 保存总体证据与决策分类，不能因为当前用户碰巧匹配就把 `conditional` 升级为 `priority`。个人决策完成关键信息收集后，还必须单独记录 `personal_match`：`matched`（符合条件）、`not_matched`（不符合条件）或 `unknown`（尚不能判断）。当 `conditional` 与 `matched/not_matched` 同时出现时，必须提供 `personalized_verdict`，让第一句话给出当前用户可直接执行的肯定或否定建议，并保留剂量、效果或安全限制；不得继续显示泛化的“只对特定人群值得”。`matched` 的首句必须明确写“值得尝试 / 值得补充 / 可以尝试 / 可以补充 / 可以使用或服用”等行动，单写“你符合条件”仍只是中间判断，不是最终结论。视觉模板只显示这条已经由科学判断层锁定的句子，不能自行推断或改写。

`trial` 不是“证据不足”的委婉说法。使用前必须读取 `bounded-self-trial.md`，排除“证据显示无重要效果”和“证据提示有害”，并完成证据信号、安全、可测量性、可执行性四道门。未生成完整 `self_trial` 方案时不得使用 `trial`。

## 2. 首屏行动栏与三个展开层

四项科学正文之后可以显示一条紧凑行动栏，但它不能代替证据生成前的信息收集：

- 当 `suitability.may_fit`、`remaining_uncertainties` 非空，或 `personal_match=unknown` 时，显示 **更新我的情况**。按钮把当前“可能匹配”和剩余不确定性整理成结构化请求，要求 Agent 只追问尚未确认、后来变化或此前跳过的高价值信息，并在必要时更新同一张卡。
- 当 L1-Quick 已完成但尚未进入完整审计时，显示 **申请完整审计**。若 `card_state=audit_updating`，显示禁用的 **完整审计更新中**；已完成 L1-Audited 时不再显示升级按钮。
- 单文件离线 HTML 不能自行唤醒 Agent 或承诺后台运行。按钮只能在浏览器允许时复制请求；失败时显示可手动复制的文本，并始终写明“回到聊天发送即可”。不得使用“已开始”“后台处理中”等误导性反馈。
- 按钮必须有默认、悬停、键盘焦点、按下、禁用、处理中、失败和成功反馈；触控目标至少 44×44 px，标签不换行，复制成功只更换按钮文字，不弹庆祝提示。

行动栏之后仍只有三个一级内容入口，顺序固定：

第一屏下方只有三个一级交互入口，顺序固定：

### 为什么

- 2–4 个真正决定购买建议的事实；
- 实际效应使用绝对变化或普通人可理解的量级；
- 宣传从哪一层外推到了哪一层；
- 更可靠、更便宜或更直接的优先路径。
- 判定为 `trial` 时，在本层显示结构化个体试用方案：类型、目标、基线、固定方案、结局测量、成功规则、停止规则和混杂控制。

### 适不适合我

- 列出证据生成前已经采用的用户选择；
- 明示当前判断采用的暂定情境，避免把一般结论伪装成已个性化建议；
- 研究人群、基线状态和当前用户的相似性；
- 剂量、剂型、植物部位、菌株、盐型、配方或共干预边界；
- 明确列出不适合自行使用的人群；
- 用“高 / 中 / 低 / 未知”描述当前用户匹配度，不把匹配度写成研究质量；
- 只列仍未知且可能改变建议的信息。首次关键问题必须在证据生成前提出，不能藏在这一展开层；不要把这里变成第二份病史问卷，也不要要求先建健康档案。

### 证据怎么裁决

- L1-Quick 先显示三类核验来源、日期、覆盖范围、仍不确定的结局和完整审计计划；明确写“不是系统综述或正式 GRADE”。以下完整方法字段只适用于 L1-Audited。
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

## 3. HTML 证据卡（默认生成，不阻塞安全分流）

普通用户完成关键信息收集后，默认生成并打开单文件离线 HTML；不要求用户再次提出“展开证据”或“保存版”。聊天只承担最短判定、安全异常和文件入口。安全分流不得等待问卷或 HTML；L1-Quick 卡也不得等待完整 PubMed 审计。

- 使用 `scripts/build_consumer_answer.py` 读取 UTF-8 JSON；
- L1-Quick 使用 `certainty_method=quick_verification`，提供三类 `quick_sources`；不需要也不得伪造 PubMed manifest、RIS 或筛选日志；
- 本轮完成的 L1-Audited 同时提供 `pubmed_search.py` 生成的检索 manifest、未经修改的 RIS，以及按 `templates/rapid-screening-log.csv` 完成的筛选日志；生成器会交叉核对检索式、Query Translation、命中/导出/筛选计数和 RIS 散列；
- 已审计缓存使用 `certainty_method=cached_audit` 并通过 `--evidence-pack` 交叉核对主题、日期、覆盖计数、全文缺口和来源；不为出卡而重复联网；
- 使用 `templates/consumer-answer.template.html`；
- 不加载外部 JavaScript、CSS、字体、分析脚本或追踪器；
- 三个入口使用原生 `<details>/<summary>`，支持键盘和屏幕阅读器；
- 行动栏使用原生 `<button>`，复制结果通过 `aria-live="polite"` 反馈；静态页面不得把复制动作表述为已提交或已启动审计；
- 所有用户、网页和论文文本在插入 HTML 前转义；
- 来源链接只接受 `http` 或 `https`；
- 文件名不包含疾病、用药或其他个人健康信息；
- 生成器成功返回 `status=ok` 后，立即调用 Codex 原生打开能力，将返回的绝对 HTML 路径转换为本地 `file:` URL，并以浏览器标签自动展示；不要默认调用 `Start-Process` 或其他系统浏览器命令。用户明确要求不自动打开时除外。
- 自动打开只发生在首张可行动卡以及同一路径发生实质更新后的最终版本，避免构建过程中的重复标签和反复抢焦点；若原生打开不可用或失败，降级为可点击文件链接并简短说明。无论自动打开是否成功都保留文件链接。
- 页首必须显示“证据护照”：审计层级、更新日期、检索覆盖和确定性路径。它来自已验证的结构化数据，不由视觉模板重新推断。
- 页首状态必须使用 `l0_safety / quick_checking / quick_complete / audit_updating / audit_complete / coverage_limited / recommendation_updated` 之一；快速卡升级时复用同一输出路径。
- `recommendation_updated` 必须同时提供 `previous_verdict` 和 `change_reason`，页面可见显示改判，不得静默覆盖。
- 全文缺口使用页内非阻断式覆盖提醒，不使用打开即遮挡结论的模态框；缺口仍需在研究层重复披露。

L1-Quick 最小 JSON 结构：

```json
{
  "title": "产品或干预名称",
  "card_state": "audit_updating",
  "status_detail": "快速核验完成；完整审计不阻塞当前卡。",
  "verdict": "conditional",
  "personal_match": "matched",
  "personalized_verdict": "可以补充，但先核对合适剂量。",
  "for_whom": "最匹配的人群或前提。",
  "effect_ceiling": "合理效果上限。",
  "safety_red_line": "最重要的安全红线。",
  "why": {"summary": "一句解释", "key_points": ["决定结论的事实"], "better_options": ["更优先路径"]},
  "suitability": {
    "intake_summary": ["本次采用的信息"],
    "assumption": "暂定情境。",
    "user_match": "当前匹配度。",
    "may_fit": ["可能匹配"],
    "avoid_or_check": ["避免或先确认"],
    "remaining_uncertainties": ["仍可能改变建议的信息"]
  },
  "research": {
    "certainty_method": "quick_verification",
    "certainty": "快速核验，未正式评级，也不是系统综述。",
    "coverage": "已核验1份本地标准、1份高质量综合来源和1份权威安全资料",
    "updated": "YYYY-MM-DD",
    "quick_sources": [
      {"label": "本地标准", "url": "https://example.org", "role": "local_standard", "checked_at": "YYYY-MM-DD"},
      {"label": "指南或系统综述", "url": "https://example.org", "role": "high_quality_synthesis", "checked_at": "YYYY-MM-DD"},
      {"label": "权威安全资料", "url": "https://example.org", "role": "safety_authority", "checked_at": "YYYY-MM-DD"}
    ],
    "uncertainties": ["仍不确定的结局"],
    "what_would_change": ["可能改判的信息"],
    "audit_plan": "完整审计继续、暂停或仅按明确请求进行。"
  }
}
```

L1-Audited JSON 在上述首屏与适用性字段基础上使用以下研究结构：

```json
{
  "title": "产品或干预名称",
  "card_state": "audit_complete",
  "verdict": "not_worth",
  "for_whom": "仅在某个明确条件下可能有用。",
  "effect_ceiling": "即使有效，预期也只是小幅改善。",
  "safety_red_line": "出现某风险或属于某人群时不要自行使用。",
  "why": {
    "summary": "一句解释",
    "key_points": ["决定结论的事实"],
    "better_options": ["更优先的路径"],
    "self_trial": {
      "type": "structured_self_trial",
      "target": "一个主要症状或功能结局",
      "baseline": "试用前如何记录以及记录多久",
      "plan": "单一产品、剂量、频率、时限和依从性记录",
      "outcome_measure": "量表、日记或可重复指标",
      "success_rule": "预先定义的最小有意义改善",
      "stop_rules": ["不良反应、恶化、无效截止点或就医条件"],
      "confounder_controls": ["需保持稳定并记录的睡眠、咖啡因等因素"]
    }
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

`certainty_method` 为必填。L1-Quick 只能使用 `quick_verification`；已审计缓存使用 `cached_audit`；本轮 L1-Audited 使用 `source_grade`、`rapid_grade`、`provisional_grade` 或 `grade_informed`。`provisional_grade` 只用于 PubMed 命中已完整导出、题名摘要已全部筛查、证据体边界可识别而部分候选全文不可得的情况；总确定性和每个结局等级必须带“暂定”。同时填写 `evidence_access.full_text_unavailable`、`impact` 和 `upload_prompt`，生成器会把数量与筛选 CSV 中的 `abstract_only` 记录核对并显示上传全文提示框。`grade_informed` 不得使用四级术语冒充正式评级。`certainty_scope` 说明证据识别范围、全文能力、单人/双人和关键简化。

`evidence_base`、`search`、`eligibility` 和每个 outcome 的 `grade_domains` 为新产物必填字段。`search.complete_retrieval=true` 时 `records_found` 必须等于 `records_exported`；`screening_complete=true` 时 `records_exported` 必须等于 `records_screened`。若检索或筛查不完整，普通功效结论只能使用 `insufficient`（“暂不能可靠判断”）或基于独立安全证据的 `avoid`，不能照常生成正向或购买性判定。

`picos` 是当前首选字段。生成脚本仍兼容旧输入中的 `pico`，但新产物必须显式包含 `S`（研究设计），并在适用时另列随访时长。`funding` 为当前字段，生成脚本仍兼容旧字段 `conflicts`。

`suitability.intake_summary` 用于显示证据生成前已经采用的信息；用户跳过时也要记录这一事实。`remaining_uncertainties` 只列提交后仍未知且可能改变建议的项目，最多 5 项。生成脚本继续兼容旧字段 `questions`，但新产物不再用它承载首次关键提问。

一般证据问题或未完成个人匹配判断时可省略 `personal_match`，生成器按 `unknown` 处理并保留通用受控判定语。`personal_match=matched/not_matched` 时必须同时提供非空 `suitability.intake_summary`、`suitability.user_match` 和 `personalized_verdict`；这是为了防止没有问卷或其他明确用户信息时伪造个性化结论。旧输入不受影响。

`why.self_trial` 仅在 `verdict=trial` 时允许且必填。`type` 使用 `structured_self_trial` 或 `n_of_1`；只有重复交叉、合理处理随机次序/盲法/洗脱和携带效应的方案才可使用 `n_of_1`。其他判定不得附带试用方案，避免把不建议包装成“仍可试试”。

`meta`、`grade`、`rob` 缺失或为空时，不生成空的二级折叠。

L1-Quick 生成命令：

```powershell
python scripts/build_consumer_answer.py answer-quick.json --html answer.html --intake-response response.json
```

个人问卷路径应传入临时 `response.json`。生成器只读取提交时间，不把问卷答案复制到报告；命令输出 `quick_elapsed_seconds`、`quick_sla_seconds` 和 `quick_sla_met`，用于验证从提交到首卡是否在180秒内。没有问卷的一般证据问题可省略该参数，由 Agent 按 `fast-path.md` 自行计时。

L1-Audited 生成命令：

```powershell
python scripts/build_consumer_answer.py answer.json `
  --html answer.html `
  --pubmed-manifest search-manifest.json `
  --pubmed-ris hits.ris `
  --screening-log screening.csv
```

任一审计文件与 JSON 不一致时停止生成，不能只修改 JSON 数字绕过检索和筛选。

已审计缓存生成命令：

```powershell
python scripts/build_consumer_answer.py answer-cached.json --html answer.html --evidence-pack pack.json
```

## 4. 一图读懂

交付 HTML 后单独询问：

> 要不要我再生成一张“一图读懂”图片，方便你保存？

只有用户同意后才生成。图片必须从同一 JSON 的 `verdict`、`for_whom`、`effect_ceiling`、`safety_red_line` 和来源日期生成，不重新总结，不新增研究结论。优先用脚本的 `--svg` 输出生成可保存的矢量图；环境能可靠转换时可同时提供 PNG。文字不得交给会改写或拼错中文的图像生成模型。

## 5. 降级路径

- **不能提供点击控件或本地问卷**：一次只问一个自然语言问题，显示完整语义选项；不得要求用户回复代码。用户可以回复“跳过”。
- **不能写结果文件**：在聊天内用相同四项首屏，随后用“为什么 / 适不适合我 / 证据怎么裁决”三个 `<details>`；若界面过滤 HTML，则改用三个短链接式标题并等待用户选择展开。
- **不能预览 HTML**：仍生成文件并提供链接，附一句“下载后用浏览器打开”。
- **用户明确只要一句话**：只给判定语和最关键安全红线，不强制生成文件。
- **专业用户或单数据库 Meta 证据合成**：不使用本协议，转入专业研究交付。
