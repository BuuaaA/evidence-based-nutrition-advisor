# 示例产物

[▶ 在线查看普通用户可视化示例](https://buuaaa.github.io/evidence-based-nutrition-advisor/examples/consumer-answer-demo.html)

`consumer-answer-demo.html` 收录 14 个行为验收用例。页面先给出 [普通用户 L1-Quick 证据卡](consumer-answer-quick-demo.html)，展示三类核验来源、“快速核验，未正式评级”的状态和“申请完整审计”按钮。每个用例都能展开结果图，并回到详细答案、筛选记录或方法文件。

快速证据卡由 `consumer-answer-quick.sample.json` 生成：

```powershell
python scripts/build_consumer_answer.py examples/consumer-answer-quick.sample.json `
  --html examples/consumer-answer-quick-demo.html
```

这条 L1-Quick 路径不需要 PubMed manifest、RIS 或筛选日志。画廊与 14 组 PNG/SVG 由 `behavior-case-results.json` 确定性生成：

```powershell
python scripts/build_behavior_case_gallery.py
```

完整审计示例由真实证据包生成并校验。这些静态页对应用户申请 L1-Audited 后的结果，包含完整 PubMed 检索、筛选和逐结局确定性。普通提问默认停在快速核验；个人决策会先完成不超过 5 项的点击选择，再按答案确定问题边界并生成快速卡。

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

用户在 HTML 交付后明确同意生成“一图读懂”时，才添加 `--svg`。仓库中的氨糖 SVG 是行为验收用例 9 的已授权测试产物。所有示例用于验证方法和交付结构，不提供针对个人的当前医疗建议。
