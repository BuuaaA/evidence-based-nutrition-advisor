# 示例产物

## 新版 Skill 实际生成的示例

[打开氨糖软骨素快速证据卡](https://buuaaa.github.io/evidence-based-nutrition-advisor/examples/cases/glucosamine-2026-quick/answer.html) · [查看来源核验与方法边界](cases/glucosamine-2026-quick/source-notes.md) · [查看首屏预览](cases/glucosamine-2026-quick/preview.svg)

这是 2026-09-24 按 V2.0 的 **L1-Quick** 路径重新核验、再用当前 `scripts/build_consumer_answer.py` 生成的通用问题示例。`answer.json` 保留结构化输入，`source-notes.md` 记录真实来源、适用性和方法局限。它没有冒称完成 PubMed 全量筛查或正式 EAL 结论评价。

## 历史行为验收材料

下方画廊和其他静态案例来自此前的流程与测试数据，部分仍展示旧 GRADE 字段，用于回归测试和查看交付边界。它们不是当前首页示例，也不代表新版 Skill 已对这些主题重新完成证据审计。

[▶ 在线查看普通用户可视化示例](https://buuaaa.github.io/evidence-based-nutrition-advisor/examples/consumer-answer-demo.html)

`consumer-answer-demo.html` 现在是 14 个行为验收用例的统一画廊。每个案例都能展开结果说明图，并链接到详细答案、检索清单、筛选记录或方法资源。画廊与 14 组 PNG/SVG 由 `behavior-case-results.json` 确定性生成：

```powershell
python scripts/build_behavior_case_gallery.py
```

普通功效问题的详细 HTML 仍由真实证据包生成并校验，而不是直接写入画廊：

这些静态详细页用于展示“用户选择跳过关键信息收集后”的一般情境答案；真实个人决策会先完成不超过 5 项的点击选择，再按答案确定 PICOS 和生成结果。

- `cases/fish-oil/`：鱼油与血脂；PubMed 更新检索 69 条，13 篇候选全文未取得，因此给出暂定 GRADE 并显示上传提示；
- `cases/glucosamine-chondroitin/`：氨糖软骨素与膝骨关节炎；
- `cases/calcium-older-adults/`：老年人补钙与骨折预防；
- `cases/neuriva/answer.html`：商品名案例，仅在画廊中展示。

以氨糖案例为例，重新生成详细答案：

```powershell
python scripts/build_consumer_answer.py examples/cases/glucosamine-chondroitin/answer.json `
  --html examples/cases/glucosamine-chondroitin/answer.html `
  --pubmed-manifest examples/cases/glucosamine-chondroitin/pubmed-search-manifest.json `
  --pubmed-ris examples/cases/glucosamine-chondroitin/pubmed-search.ris `
  --screening-log examples/cases/glucosamine-chondroitin/screening.csv
```

只有用户在 HTML 交付后明确同意生成“一图读懂”时，才添加 `--svg`。仓库中的氨糖 SVG 是行为验收用例 9 的已授权测试产物。所有示例用于验证方法和交付结构，不是针对任何个人的当前医疗建议。
