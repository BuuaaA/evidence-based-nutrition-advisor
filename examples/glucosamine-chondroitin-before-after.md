# 氨糖软骨素：使用 Skill 前后对比图说明

首页对比图的问题是：`补充氨糖软骨素能缓解关节疼痛吗？`

左侧表示普通 Agent 常见的短答结构。这张图只比较交付方式，不量化模型能力。右侧的购买判定、适用人群、效果上限和安全红线取自 `cases/glucosamine-chondroitin/answer.json`；界面状态按当前普通用户默认路径绘制为 L1-Quick。

L1-Quick 只核验本地标准、可靠指南或综述、权威安全资料，明确标注“快速核验，未正式评级”。普通提问到这里即可拿到证据卡，并能点击“申请完整审计”。PubMed 全量导出筛查、PICOS 纳排和逐结局 GRADE 在用户申请完整审计或风险需要更高保证时继续。

仓库同时保留完整审计后的氨糖案例，其详细结论由以下证据包生成并校验：

- `cases/glucosamine-chondroitin/pubmed-search-manifest.json`
- `cases/glucosamine-chondroitin/pubmed-search.ris`
- `cases/glucosamine-chondroitin/screening.csv`

右侧先限定证据直接适用的人群，再报告效果上限和安全红线。快速卡保留升级入口，用户可以在需要时继续查看完整筛查与逐结局确定性。

- [查看详细可展开答案](cases/glucosamine-chondroitin/answer.html)
- [查看 14 个行为验收案例](consumer-answer-demo.html)

重新生成首页图片：

```powershell
python scripts/build_before_after_image.py
```
