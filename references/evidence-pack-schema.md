# 运行时证据包结构

证据包用于复用一次已经完成的通用主题 L1 审计。它不保存用户问卷、健康档案或某次个性化回答，也不随开源仓库分发。

## 必需字段

```json
{
  "schema_version": "nutrition-evidence-pack-v1",
  "topic_id": "lowercase-hyphen-topic",
  "title": "通用主题名称",
  "aliases": ["检索别名"],
  "scope": {
    "population": "证据覆盖的人群",
    "intervention": "剂型、配方与剂量边界",
    "outcomes": ["关键结局"],
    "not_covered": ["不可外推的情境"]
  },
  "freshness_days": 180,
  "searched_at": "YYYY-MM-DD",
  "valid_until": "YYYY-MM-DD",
  "evidence_passport": {
    "audit_level": "L1-Audited",
    "database": "PubMed",
    "historical_base": "历史基座及检索截止日；没有合格基座时明确写无",
    "records_found": 0,
    "records_exported": 0,
    "records_screened": 0,
    "full_text_unavailable": 0,
    "certainty_method": "rapid_grade | provisional_grade | grade_informed",
    "certainty_summary": "逐结局确定性摘要",
    "coverage_limits": "数据库、筛查者、全文与灰色文献边界",
    "sources": [{"label": "决定性来源", "url": "https://..."}]
  },
  "pubmed": {
    "base_query": "不含日期块的可复现检索式",
    "last_search_end": "YYYY-MM-DD"
  },
  "safety_rules": [
    {"when": "可观察的触发条件", "verdict": "avoid", "message": "安全动作", "priority": 1}
  ],
  "decision_matrix": [
    {"match": "情境边界", "verdict": "conditional", "first_sentence": "只对特定人群值得。", "effect_ceiling": "效果上限"}
  ],
  "product_boundaries": ["不能外推到哪些产品、剂型或宣称"]
}
```

`verdict` 只允许：`priority`、`conditional`、`trial`、`not_worth`、`avoid`、`uncertain`。`trial` 仍必须满足结构化个体试用四道门，不能仅凭证据不足写入。

## 注册门槛

- `records_found = records_exported = records_screened`；截断或未完成筛查的审计不得注册为新鲜包。
- 每个来源必须是 `http`/`https`，并能支撑相应结论。
- 日期、确定性方法、全文缺口和覆盖限制必须真实记录。
- 所有文字必须描述通用证据边界。不得出现姓名、联系方式、问卷答案、化验单或健康档案字段。
- 注册前运行 `register`，注册后运行 `validate`。脚本失败时不得手工绕过校验或只改索引日期。
