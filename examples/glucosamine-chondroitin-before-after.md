# 氨糖软骨素：使用 Skill 前后对比图说明

首页对比图的问题是：`补充氨糖软骨素能缓解关节疼痛吗？`

左侧用于表示普通 Agent 常见的短答结构，不是一次固定模型、固定版本、固定日期的基准测试，因此不声称能够量化 Skill 带来的模型能力差异。右侧字段直接来自 `cases/glucosamine-chondroitin/answer.json`，详细结论由以下证据包生成并校验：

- `cases/glucosamine-chondroitin/pubmed-search-manifest.json`
- `cases/glucosamine-chondroitin/pubmed-search.ris`
- `cases/glucosamine-chondroitin/screening.csv`

右侧的关键差异是：先限定证据只直接适用于已确诊膝骨关节炎，再报告疼痛和功能的效果上限及逐结局确定性；不会把所有关节痛、所有配方或统计学差异混成一句“有效”。

- [查看详细可展开答案](cases/glucosamine-chondroitin/answer.html)
- [查看九个行为验收案例](consumer-answer-demo.html)

重新生成首页图片：

```powershell
python scripts/build_before_after_image.py
```
