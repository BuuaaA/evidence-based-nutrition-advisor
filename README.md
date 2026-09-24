# 先看证据，再决定要不要补

**Evidence-Based Nutrition Advisor · V2.0** 是一个用于 Codex 等 AI Agent 的营养证据 Skill。问它“鱼油能改善甘油三酯吗？”或“这瓶氨糖软骨素值得买吗？”，它会先给出简明判断，再交代研究适用于谁、效果有多大、有哪些安全问题。

补充剂的宣传常引用论文，但论文研究的人群、剂量和结局未必与你面前的产品相同。这个 Skill 会逐项核对这些差别。遇到相互矛盾的指南和综述，它会解释差异从哪里来；资料不足时，也会说明目前还不能判断什么。

![氨糖软骨素证据卡首屏](examples/cases/glucosamine-2026-quick/preview.svg)

[打开完整证据卡](https://buuaaa.github.io/evidence-based-nutrition-advisor/examples/cases/glucosamine-2026-quick/answer.html) · [查看来源核验记录](examples/cases/glucosamine-2026-quick/source-notes.md)

这张卡在 **2026-09-24** 按 V2.0 的快速核验流程制作，回答的是一般证据问题。它没有使用个人健康资料，也没有进行完整 PubMed 筛查或正式 EAL 评级。

## 一张卡，先回答最实际的问题

以“氨糖软骨素能缓解关节疼痛吗”为例，当前快速核验的建议是：**病因还不清楚时，先别急着买。**现有研究主要针对已确诊的膝骨关节炎。氨糖即使有止痛作用，幅度也可能很小；功能改善尚不明确，单一成分的结果也不能直接套到复方产品上。

这次核验同时看了[中国膝骨关节炎专家共识](https://zhgjwkzz.cma-cmc.com.cn/CN/abstract/article/1674-134X/33136)、[美国风湿病学会 2026 年指南摘要](https://assets.contentstack.io/v3/assets/bltee37abb6b278ab2c/bltb3d12c34020da842/oa-guideline-summary-2026.pdf)、[2026 年伞状综述](https://www.frontiersin.org/journals/nutrition/articles/10.3389/fnut.2026.1806413/full)及[安全资料](https://www.nccih.nih.gov/health/glucosamine-and-chondroitin-for-osteoarthritis-what-you-need-to-know)。卡片把不同结论的依据、适用范围和仍需核查的地方放在展开层，方便你自己追溯。

## 适合怎么用

| 你的问题 | Skill 会做什么 |
|---|---|
| “这种成分有用吗？” | 先核验相关指南、研究综合和安全资料，给出有边界的快速判断 |
| “这款产品适合我吗？” | 只追问可能改变结论的诊断、剂量、用药等信息，再核对产品与研究是否匹配 |
| “证据到底靠不靠谱？” | 经你明确要求后，保存 PubMed 检索与筛查记录，按结局检查研究质量和证据缺口 |
| “能重新合并研究吗？” | 先判断研究能否合并；数据足够时做单数据库证据合成，并公开检索和资料限制 |

一般问题可以直接问。涉及自己的疾病、用药或具体产品时，提供你愿意分享、且会影响判断的信息即可。快速卡会标出核验日期、覆盖范围和未解决的问题；完整审计需要你另外提出。

## V2.0 为什么改用 EAL

完整审计现在以美国营养与饮食学会（Academy of Nutrition and Dietetics）的 Evidence Analysis Library（EAL）方法为主线：先明确问题，再按研究设计选择相应的 Quality Criteria Checklist（QCC），最后针对每个结局评价整组证据。长期饮食暴露、短期干预和罕见伤害需要不同的研究设计，这套流程便于把选择理由和评价过程留下来。

[GRADE 也能评价营养研究](https://book.gradepro.org/guideline/principles-for-assessing-the-certainty-of-interventions)，队列研究也不会因为属于营养学就自动变成高质量。若原指南或综述使用 GRADE，Skill 会保留其原评级及出处，不把它换算成 EAL 等级。快速核验不自行给 EAL 等级；完整审计也只有在筛查、资料和方法核对足够充分时才评级。

方法来源：[EAL《Evidence Analysis Manual》（2022 年 11 月版）](https://www.andeal.org/vault/2440/web/files/EAL/EAL%20Manual%20and%20Forms/EA_Manual_2022Nov.pdf)、[QCC 表单](https://www.andeal.org/evidence-analysis-manual)、[结论评级表](https://www.andeal.org/vault/2440/web/files/EAL/EAL%20Manual%20and%20Forms/EAL_Grading_Table.pdf)。按官网要求署名：©2022 Evidence Analysis Manual Academy of Nutrition and Dietetics。项目独立使用公开方法，未获得 Academy 认证或背书。[查看完整方法说明](references/eal-methodology.md)。

## 安装与提问

把仓库放入 Agent 的 Skills 目录。以 Windows 上的 Codex 用户目录为例：

```powershell
$skillRoot = Join-Path $env:USERPROFILE '.codex\skills'
New-Item -ItemType Directory -Force -Path $skillRoot | Out-Null
git clone https://github.com/BuuaaA/evidence-based-nutrition-advisor.git `
  (Join-Path $skillRoot 'evidence-based-nutrition-advisor')
```

新开会话后可以这样问：

```text
使用 $evidence-based-nutrition-advisor：鱼油能改善甘油三酯吗？
先给我快速判断，再说清适用人群、效果、安全问题和依据。
```

这个 Skill 提供证据检索与决策支持，不能诊断或替代医生、药师和注册营养专业人员。实际结果取决于当前 Agent 能访问的来源和工具。[使用指南](docs/USER_GUIDE.md)写了个人决策、专业审计和研究合成的提问方式；[案例索引](docs/CASE_GALLERY.md)区分 V2.0 当前示例与 V1.0.1 历史材料。

[贡献指南](CONTRIBUTING.md) · [隐私与健康信息](HEALTH_AND_PRIVACY.md) · [安全报告](SECURITY.md) · [MIT License](LICENSE)
