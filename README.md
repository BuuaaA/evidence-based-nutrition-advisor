# Evidence-Based Nutrition Advisor

把一个通用 AI Agent 变成可追溯的营养与补剂证据审计助手：先弄清问题和安全边界，再核对证据、说明适用人群与不确定性，最后给出容易理解的下一步。

这是一个开源 **Agent Skill**，不是独立 App、医学诊断工具或预先审核好的营养数据库。运行效果取决于宿主 Agent、当次可用的检索与文件工具，以及实际完成的证据核查。

> **安全边界：**本项目提供一般证据检索与决策支持，不诊断疾病或替代医生、药师、注册营养师。孕哺、未成年人、慢性病、处方药、明显异常化验或进行性症状等情境，应优先寻求合格专业人员的意见。不要因研究任务延误必要的医疗处置。

## 适合谁

- 想判断一种营养干预、补剂或产品宣称是否值得进一步考虑的人；
- 需要核对指南、系统综述与原始研究为何不一致的营养专业人员；
- 需要把 PubMed 检索、逐条筛查、研究评价和结论边界记录下来的研究人员；
- 希望让 AI 输出包含来源、范围和限制的证据卡，而不是只有一段结论的开发者。

## 它如何工作

1. **先界定问题与安全事项。**一般知识问题不索取个人资料。只有当答案可能改变建议、证据适用性或安全处置时，才追问最少信息；通常 1–3 项，必要时最多 5 项。
2. **快速核验，尽早给出有边界的回答。**优先核对适用的本地标准、经过方法与适用性检查的指南或综述，以及权威安全资料。快速核验不会冒称完成系统综述或本轮 EAL 结论评级。
3. **用户需要时再深入审计。**缓存不匹配或快速结论仍不能回答问题时，先说明审计范围和预期价值。除用户已明确要求外，取得明确同意后才启动长时审计；约 15 分钟是阶段进展预算，不是完成保证。
4. **保留检索与筛查轨迹。**完整审计记录 PubMed 检索式、Query Translation、时间范围、命中与导出数、筛查决定、排除原因及资料访问情况。没有合格历史基座时，流程默认要求全年份检索；有基座时更新截止日之后的新证据，并检查延迟入库记录。
5. **按营养问题综合证据。**以 Academy of Nutrition and Dietetics Evidence Analysis Library（EAL）流程作为组织框架，按研究类型使用适用的 Quality Criteria Checklist（QCC），再按具体结局形成结论评价。长期饮食暴露、疗效与伤害问题可能需要不同研究设计；队列或随机试验的标签都不会自动决定质量。
6. **把不确定性与行动分开。**来源质量、结论支持程度、与个人情况的匹配、效应大小和是否值得采用是不同判断。证据体、关键资料或方法规则不完整时，保留未评级状态，不猜造等级。
7. **Meta 是有条件的深入工作。**只有问题清楚、至少有两个独立且可比较的研究、数据足够，且定量合并可能改变判断时才考虑；缺少综述、新研究出现或结论等级较低都不会自动触发 Meta。单库结果会明确说明数据库与资料覆盖限制。

使用 EAL/QCC 作为工作流程，不代表 Academy 对本项目、自动评价或结论作出认证。正式 QCC 总体规则未核定或证据不足时，项目会保留逐项理由并关闭相应的正式自动评级。

## 查看结果样例

![氨糖软骨素问题：通用回答与本 Skill 输出结构对比](assets/glucosamine-chondroitin-before-after.png)

这张图展示回答结构与证据边界，不是固定模型、版本和日期下的性能基准。可查看[氨糖软骨素详细证据卡](examples/cases/glucosamine-chondroitin/answer.html)、[PubMed 检索与筛查记录](examples/glucosamine-chondroitin-before-after.md)，以及[14 个行为验收案例](examples/consumer-answer-demo.html)。Neuriva 商品案例保留在画廊中，不用作首页表现对照。

## 竞争位置与差异

截至 2026 年 9 月，营养信息产品已经有成熟的资料库、官方事实表和个性化应用。Examine 提供营养与补剂研究资料、按健康目标组织的指南，并说明其多位专业人员参与审核；NIH Office of Dietary Supplements 提供消费者和专业人员版补剂事实表；SuppAI 面向个人提供补剂选择、剂量、安全提醒和跟踪；CliniAtlas 则公开介绍了检索 PubMed、Europe PMC、指南和监管资料并返回带来源的临床证据答案。它们各自解决不同问题，不能仅凭功能描述判定实际建议质量。

本项目更适合定位为**可移植到通用 Agent 的营养证据审计工作流**：重点在问题匹配、可复核的 PubMed 审计、营养情境下的来源评价、透明的未评级状态，以及用户控制的深入升级。它不是在已有专家团队、长期维护的内容库、移动端个性化体验或跨数据库搜索上与上述产品正面竞争。

| 用户要解决的问题 | 常见替代方案 | 本 Skill 的侧重点 |
|---|---|---|
| 查某种补剂通常怎么用、有哪些研究 | Examine 等主题资料库 | 按用户当前问题重新界定人群、产品、剂量与结局，并追溯本轮依据 |
| 查营养素背景与官方安全信息 | NIH ODS、地区指南和监管资料 | 把这些资料作为候选来源，与具体宣称及地区适用性一起审查 |
| 获取方便的个性化补剂推荐和日常跟踪 | SuppAI 等消费应用 | 不以“推荐更多产品”为目标；解释什么证据适用、何时不建议购买或需进一步核实 |
| 对临床问题做快速文献问答 | CliniAtlas 等通用临床证据助手 | 聚焦营养、饮食暴露、补剂及产品宣称，支持完整审计记录和可选单库合成 |

**竞争力判断：当前有清晰的细分差异，但尚未证明整体竞争优势。**流程完整度和可追溯性是值得验证的优点；宿主依赖、需要用户理解 Skill 安装方式、单库边界、没有经过专家复核的主题库，以及尚无与人工或成熟产品比较的准确性与可用性基准，是实际短板。下一步最有价值的投入不是再增加评级术语，而是方法学专家复核、常见问题的高质量证据包，以及与普通 AI 回答和成熟资料库开展盲评，测量重大错误、安全遗漏、用户理解度与首次可用回答时间。

## 安装

将整个仓库放入宿主的 Skills 目录，并在新会话中启用 `evidence-based-nutrition-advisor`。以 Codex 的用户级目录为例：

```powershell
$skillsDir = Join-Path $HOME ".codex\skills"
git clone https://github.com/BuuaaA/evidence-based-nutrition-advisor.git `
  (Join-Path $skillsDir "evidence-based-nutrition-advisor")
```

已有安装时，在仓库目录内按自己的变更流程更新；不要覆盖个人证据缓存或健康档案。不同宿主的安装位置和启用方式可能不同，请查看对应产品的官方 Skills 文档。

## 使用示例

**普通问题：**

```text
使用 $evidence-based-nutrition-advisor：鱼油能改善甘油三酯吗？
如果这是个人使用决策，只询问会改变建议或安全判断的关键信息；先给快速核验结果，并标出仍不确定的部分。
```

**专业审计：**

```text
使用 $evidence-based-nutrition-advisor 做营养证据审计：
比较指南、系统综述和 PubMed 更新研究对某个具体结局的判断；
记录检索范围、纳排、来源评价、新旧证据冲突和 EAL 结论支持状态。
```

**请求 Meta：**

```text
基于预先界定的 PICOS 和一个指定数据库，评估这些独立研究是否适合定量合并。
请报告数据提取、统计方法、异质性、敏感性分析及单库和资料访问限制；
不满足合并条件时改做结构化叙述综合。
```

## 仓库内容

```text
SKILL.md       入口说明、任务路由与关键边界
references/    EAL/QCC、检索、来源评价、综合、隐私与交付规则
scripts/       PubMed 检索、缓存校验、筛查辅助与答案生成
templates/     证据卡、检索策略、筛查和报告模板
examples/      可复核示例及测试材料
tests/         行为验收用例、单元测试和统计校验
```

## 开发与验证

需要 Python 3。基础验证：

```powershell
python -m unittest discover -s tests -p "test_*.py"
python scripts/build_behavior_case_gallery.py
python scripts/build_before_after_image.py
```

如果安装了 Codex `skill-creator`，还可运行其 `quick_validate.py` 检查 Skill 结构。部分统计引擎和离线 WebR 能力需要额外依赖；按任务读取相关 `references/`，不必为普通快速核验安装全部工具。

不要提交健康档案、用户问卷正文、令牌、Cookie、数据库凭据、缓存中的个人信息或临时运行输出。贡献与安全报告方式见 [CONTRIBUTING.md](CONTRIBUTING.md)、[HEALTH_AND_PRIVACY.md](HEALTH_AND_PRIVACY.md) 和 [SECURITY.md](SECURITY.md)。

## 参考与竞品资料

- [Examine：研究流程](https://examine.com/about/research-process/) · [Examine：产品与研究内容](https://help.examine.com/help/getting-started)
- [NIH ODS：膳食补充剂事实表](https://ods.od.nih.gov/factsheets/list-all/)
- [SuppAI：App Store 产品说明](https://apps.apple.com/us/app/suppai-ai-supplement-guide/id6795253143)
- [CliniAtlas：临床证据搜索产品说明](https://cliniatlas.com/)
- [EAL Evidence Analysis Manual 与表单](https://www.andeal.org/evidence-analysis-manual)

## 许可

本项目采用 [MIT License](LICENSE)。
