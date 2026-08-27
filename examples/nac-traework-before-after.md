# NAC 购买建议：TraeWork 使用 Skill 前后对比

## 测试条件

- 平台：TraeWork
- 模型：Qwen 3.8 Max
- 日期：2026-08-28
- 相同初始问题：`我看见营养补剂 NAC 的宣传，很心动，值得购买吗？`

这张图比较的是同一模型在是否安装 `evidence-based-nutrition-advisor` 时的工作流和结果可核查性，不是通用模型排行榜，也不把回答长度当作能力提升。

## 未安装 Skill

[查看 TraeWork 原始分享结果](https://share.traecontent.cn/share/DX7LJLDXDBJLV.?enter_from=pc)。

回答搜索了 10 个网页，结论方向总体合理：NAC 有明确药用场景，但健康人若只是为了泛化的“抗氧化、排毒、增强免疫”，购买价值不高。回答还涉及慢性呼吸道疾病、精神科辅助治疗、常见剂量和相互作用。

它的局限不是“完全错误”，而是没有先确认用户究竟被哪项宣传打动，因此把多个用途放在同一个宽泛答案中；同时没有展示可复现检索式、命中和筛选流、PICOS 纳排或逐结局 GRADE，读者无法判断是否系统覆盖了相互冲突的证据。

## 安装 Skill 后

Skill 先把模糊购买意图收敛为：健康成人、无处方药、购买目标为美白/抗衰。随后针对这个问题完成 PubMed 单数据库快速证据综合：

- 命中 225 条，完整导出并逐条筛查 225 条；
- 17 条进入全文评估，最终纳入 16 条；
- 直接口服随机试验纳入 50 名黄褐斑女性，NAC 与安慰剂的 mMASI 均下降 12%，组间 `p=0.613`；
- 美白获益证据为极低确定性；对黄褐斑“无额外获益”的确定性为中等；
- 分开说明直接人体结局、外用研究、替代终点和体外机制，避免用“抗氧化机制成立”推出“口服后可以美白抗衰”。

可核查文件：

- [安装 Skill 后的完整可交互 HTML](https://buuaaa.github.io/evidence-based-nutrition-advisor/examples/cases/nac-traework/after-skill.html)
- [PubMed 检索清单](cases/nac-traework/pubmed-search-manifest.json)
- [完整检索式](cases/nac-traework/query.txt)
- [逐条筛选记录](cases/nac-traework/screening.csv)
- [原始 RIS](cases/nac-traework/pubmed-search.ris)

## 公平性边界

安装 Skill 后的回答包含一次证据生成前的信息收集，因此最终审计的问题比初始提示更具体。这不是额外提示词作弊，而是 Skill 针对模糊个人决策问题的设计行为。对比图据此展示“从模糊购买问题到可审计结论”的完整路径。

重新生成首页图片：

```powershell
python scripts/build_before_after_image.py
```
