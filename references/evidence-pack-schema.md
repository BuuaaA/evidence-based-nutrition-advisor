# 运行时证据包结构

证据包用于复用一次已经完成的通用主题 L1 审计。它不保存用户问卷、健康档案或某次个性化回答，也不随开源仓库分发。

## 必需字段

```json
{
  "schema_version": "nutrition-evidence-pack-v2",
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
    "assessment_framework": "EAL",
    "method_version": "EAL-2022-11 / QCC 表单标识与版本",
    "assessment_status": "preliminary | human_reviewed",
    "review_record": null,
    "records_found": 0,
    "records_exported": 0,
    "records_screened": 0,
    "full_text_unavailable": 0,
    "assessment_summary": "逐结局 EAL 结论支持状态及未评级原因",
    "outcomes": [
      {
        "outcome": "关键结局及时间点",
        "eal_grade_state": "preliminary | human_reviewed",
        "eal_grade": "I | II | III | IV | V | null",
        "finding": "该证据支持、反驳或无法判断的具体结论",
        "synthesis_rationale": "依据质量、数量、一致性、临床影响和可推广性的解释",
        "effect": "效应大小、区间或结构化叙述结果",
        "qcc_summary": "来源质量要点；引用适用工具版本和证据定位"
      }
    ],
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

`nutrition-evidence-pack-v1` 为 GRADE 时代旧格式，仍可读取以保留历史来源和范围，但查询必须返回 `reappraisal_required`，不得将旧结论当成新鲜可复用建议或把 GRADE 等级换算为 EAL I–V。完成来源与结局重新评价后，方可注册 v2。

v2 仅收录本轮范围、筛查和结局综合均完整的通用证据包；若 QCC 表单总体规则未核定，可以存储逐条记录，但不能注册为已验证新鲜包。EAL 等级状态不完整时 `eal_grade` 必须为 null。AI 初步产物与人工复核产物都要标明真实状态和方法版本。

`verdict` 只允许：`priority`、`conditional`、`trial`、`not_worth`、`avoid`、`uncertain`。`trial` 仍必须满足结构化个体试用四道门，不能仅凭证据不足写入。

## 注册门槛

- `records_found = records_exported = records_screened`；截断或未完成筛查的审计不得注册为新鲜包。
- 每个来源必须是 `http`/`https`，并能支撑相应结论。
- 日期、确定性方法、全文缺口和覆盖限制必须真实记录。
- 所有文字必须描述通用证据边界。不得出现姓名、联系方式、问卷答案、化验单或健康档案字段。
- 注册前运行 `register`，注册后运行 `validate`。脚本失败时不得手工绕过校验或只改索引日期。
