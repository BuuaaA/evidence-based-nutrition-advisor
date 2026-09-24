# 案例索引

## 先看 V2.0 的实际输出

“补充氨糖软骨素能缓解关节疼痛吗？”是目前首页展示的案例。[打开可展开证据卡](https://buuaaa.github.io/evidence-based-nutrition-advisor/examples/cases/glucosamine-2026-quick/answer.html)，或阅读[来源核验记录](../examples/cases/glucosamine-2026-quick/source-notes.md)。它在 2026-09-24 按 L1-Quick 流程处理一般问题：先给购买判断，再说明研究人群、效果上限、安全提示和不确定性。本次没有进行完整 PubMed 审计，也没有给出 EAL I–V 等级。

如果想了解个人决策、专业审计或研究合成分别怎么提问，请看[使用指南](USER_GUIDE.md)。当前流程与验收边界记录在 [`SKILL.md`](../SKILL.md) 和 [`tests/behavior-cases.md`](../tests/behavior-cases.md)。

## V1.0.1 历史存档

[旧版行为验收画廊](https://buuaaa.github.io/evidence-based-nutrition-advisor/examples/consumer-answer-demo.html)保留 14 个早期用例，包括鱼油、氨糖软骨素、补钙、产品宣称、安全风险和 Meta 路由。旧报告沿用当时的 GRADE 字段与流程，适合回归测试和追溯设计变化，不能当作 V2.0 的当前审计。

| 历史材料 | 可以查看什么 |
|---|---|
| [鱼油与血脂](../examples/cases/fish-oil/) | 旧版更新检索、全文可得性提示和暂定评级 |
| [氨糖软骨素与膝骨关节炎](../examples/cases/glucosamine-chondroitin/) | 旧版详细报告与 PubMed 筛查轨迹 |
| [老年人补钙](../examples/cases/calcium-older-adults/) | 旧版专业证据展示 |
| [14 个行为验收用例](https://buuaaa.github.io/evidence-based-nutrition-advisor/examples/consumer-answer-demo.html) | 当时的交互、路由和安全边界图卡 |

仓库保留这些原始产物的版本标记。若用它们回答今天的问题，需要重新核查发表后的研究、适用人群、产品配方、用药和地区要求；旧 GRADE 等级不能直接换算成 EAL 等级。
