# 示例与历史案例

## 当前版本：V2.0 快速证据卡

[打开氨糖软骨素证据卡](https://buuaaa.github.io/evidence-based-nutrition-advisor/examples/cases/glucosamine-2026-quick/answer.html) · [查看首屏预览](cases/glucosamine-2026-quick/preview.svg) · [阅读核验记录](cases/glucosamine-2026-quick/source-notes.md)

这个案例在 2026-09-24 按 L1-Quick 流程重新核验。问题没有个人诊断或商品信息，因此卡片只回答一般证据；它列出了实际核查的来源，也写明尚未完成 PubMed 全量筛查和正式 EAL 评级。结构化输入保存在 [`answer.json`](cases/glucosamine-2026-quick/answer.json)。

可以用仓库中的生成器重建 HTML：

```powershell
python scripts/build_consumer_answer.py `
  examples/cases/glucosamine-2026-quick/answer.json `
  --html examples/cases/glucosamine-2026-quick/answer.html
```

## V1.0.1 历史材料

[旧版行为验收画廊](https://buuaaa.github.io/evidence-based-nutrition-advisor/examples/consumer-answer-demo.html)保存了 14 个早期用例。鱼油、老年人补钙、Neuriva 和旧氨糖案例中的检索记录、图卡与 GRADE 字段均保留原样，方便回归测试和追溯当时的做法。这些案例没有按 V2.0 重新审计，不能当作当前证据结论。

历史画廊由 `behavior-case-results.json` 生成；需要复现时运行：

```powershell
python scripts/build_behavior_case_gallery.py
```

图卡与报告都是方法演示，不针对任何人的现时健康情况。个人决策应重新核查证据日期、诊断、剂型、剂量和用药。
