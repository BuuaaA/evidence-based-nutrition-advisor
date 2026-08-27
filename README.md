# Evidence-Based Nutrition Advisor

网上从来不缺“有论文证明”的营养建议。真正麻烦的是：论文彼此矛盾、研究对象并不一样、统计学差异未必有实际意义，保健品宣传又常把其中一段结论讲得过满。

Evidence-Based Nutrition Advisor 是一个开放的 Agent Skill。它先界定问题，再用已有系统综述作为历史证据基座，完成可复现的 PubMed 更新检索和全量题录筛查，按结局评价 GRADE，最后把结果翻译成一个能执行的决定。

它不是“帮你多找几篇论文”，而是回答这些更实际的问题：

- 证据到底适用于谁；
- 效果有多大，是否达到值得在意的程度；
- 为什么指南、综述、单项试验和产品宣传会得出不同结论；
- 哪些信息会改变现在的建议；
- 证据不完整时，结论究竟有多不稳。

> [!IMPORTANT]
> 本项目用于证据检索、审计和决策支持，不用于诊断或替代治疗。孕哺、未成年人、肝肾疾病、处方药、手术、明显异常化验或进行性症状，应优先咨询医生、药师或注册营养专业人员。

## 三类使用场景

| 场景 | 例子 | 你会得到什么 |
|---|---|---|
| 普通用户 | “补充氨糖软骨素能缓解关节疼痛吗？” | 第一屏先给决定；展开后可查看检索式、筛选记录、PICOS 纳排和逐结局 GRADE |
| 营养师及其他专业人员 | “常规补钙能预防老年人骨折吗？” | 效应量与置信区间、临床重要阈值、GRADE 五域和适用性边界 |
| 研究人员和专业用户 | “目前没有可靠结论，能否重新合并现有研究？” | 预先限定一个数据库，完整筛查并提取可获得全文，完成偏倚评价、统计合并、敏感性分析和 GRADE |

可直接查看：

- [普通用户可视化示例](https://buuaaa.github.io/evidence-based-nutrition-advisor/examples/consumer-answer-demo.html)
- [氨糖软骨素详细答案](examples/cases/glucosamine-chondroitin/answer.html)
- [专业证据展示：老年人补钙](examples/cases/calcium-older-adults/professional-evidence.md)
- [单数据库 Meta 证据合成示例](examples/cases/meta-routing/original-meta-result.md)

## 使用前后有什么不同

![NAC 购买问题在 TraeWork 中使用 Skill 前后的回答对比](assets/nac-traework-before-after.png)

同一初始问题、同一测试环境：TraeWork，Qwen 3.8 Max。未安装 Skill 时，回答能给出大体合理的购买方向；安装后，先确认购买目标，再展示可复现的 PubMed 检索、全量筛查、直接人体证据和逐结局 GRADE。这里比较的是工作流与可核查性，不把篇幅差异当作模型能力差异。[查看原始结果与制图口径](examples/nac-traework-before-after.md)。

## 方法底线

普通功效问题默认执行以下流程：

1. 先判断是在问一般证据，还是准备为自己作决定。一般证据问题直接检索；个人决策或意图不明时，先用点击选项确认通常 3–5 项、至多 5 项真正可能改变建议的信息，不要求填写完整病史，也不为凑数询问无关资料。
2. 寻找可信的系统综述或指南证据综述，核查其检索范围、截止日期和适用性。
3. 保存可复现的 PubMed 检索式、Query Translation、检索日期和命中数。
4. 完整导出并筛查全部命中，不静默截取前 N 条，也不只看“最相关”结果。
5. 按关键结局综合证据并评价 GRADE，不给单篇论文贴 GRADE 等级。
6. 把证据确定性、当前用户匹配度和最终决策分开表达。

历史系统综述是证据基座，不是跳过更新检索的理由。PubMed 是普通功效问题的最低检索来源。多数据库、注册平台、灰色文献和双人流程属于发表级系统综述的要求，不是本 Skill 单数据库 Meta 证据合成所声称达到的范围。

### 为什么先点几项再生成证据

“血脂”“关节痛”“老年人补钙”都不是单一问题：异常分项、诊断、剂型、关键用药或风险状态可能直接换掉检索人群和最终建议。Skill 会先做“决策翻转测试”，只保留会改变 PICOS、安全边界或购买判定的问题。

- 宿主支持选择卡或表单时，直接使用原生点击控件；
- 本地环境可运行脚本时，可用一次性 localhost 问卷收集选择，答案只写入临时文件；
- 两者都不可用时，才退化为紧凑编号选项，用户只需回复代码；
- 每题都有“不清楚”，也可一键跳过并先看一般结论。

这不是完整健康问卷。通常 3–5 项，硬上限 5 项；若只有 1–2 项真正会改变建议，就只问 1–2 项。答案提交后才确定最终 PICOS、运行证据检索并生成证据卡；“适不适合我”展开层用于回顾已采用的信息和剩余不确定性，不再把首次关键问题藏在里面。

### 全文拿不到时怎么处理

全文获取不完整不等于研究结果阴性，也不等于论文质量差。如果 PubMed 命中已完整导出、题名摘要已全部筛查，而且历史证据基座足以界定证据体，Skill 会继续给出逐结局的**暂定 GRADE**，但必须：

- 把等级写成“暂定高 / 暂定中 / 暂定低 / 暂定极低”；
- 显示尚未取得全文的篇数和记录；
- 说明哪些 GRADE 域可能受影响；
- 在结果打开时提示用户上传全文，上传后重新筛选、提取和评级。

如果连检索边界或关键效应都无法识别，则只做 GRADE-informed 判断，不使用四级等级。检索被截断或筛查未完成时，生成器会拒绝输出通常的功效结论。

## 单数据库 Meta 证据合成

这项功能主要面对目前**没有可靠综合结论**的问题，例如：没有系统综述、现有 Meta 已明显过时、纳排或统计方法存在严重缺陷，或者出现了可能改变旧结论的新研究。

它不是为了替代发表级系统综述，而是用 Meta 分析的方法，对一个边界清楚的证据集重新进行合成：

1. 预先确定 PICOS、主要结局、检索截止日期和分析方案；
2. 根据问题和访问条件指定一个数据库，保存完整检索式并导出全部命中；
3. 按预设标准完成题名摘要和全文筛选；
4. 只从能够取得全文、数据可核查的研究中提取效应数据；
5. 评价偏倚风险，判断研究是否适合合并；
6. 完成统计合并、异质性与敏感性分析，并按结局评价 GRADE；
7. 明确列出未取得全文、无法提取或不适合合并的研究。

结果应命名为“基于【数据库名称】和可获得全文的 Meta 证据合成”，只代表该数据库中已识别且能够核查全文的研究。单数据库可能漏掉其他数据库和未发表研究，因此不能写成“全面系统综述”或“发表级 Meta”。它的价值是，在证据结论空白或不可靠时，提供一个范围透明、可以复核、比随机挑选论文更可信的当前估计。

## 安装

请保留整个仓库。`references/`、`scripts/` 和 `templates/` 都是 Skill 的一部分，只复制 `SKILL.md` 会丢失关键能力。

### 让 AI 直接安装

把仓库地址复制给支持 Skills 的 AI：

```text
请从 https://github.com/BuuaaA/evidence-based-nutrition-advisor 安装这个 Skill。
请保留完整目录，并确认最终目录的根部可以直接看到 SKILL.md。
```

### 按宿主的官方文档安装

- Codex：[OpenAI Skills](https://github.com/openai/skills)
- Claude Code：[Agent Skills](https://code.claude.com/docs/en/skills)
- WorkBuddy：[技能说明](https://cloud.tencent.com/document/product/1831/134432)
- TraeWork：[Skills 文档](https://docs.trae.cn/work_skills)

一般做法是把完整仓库放进宿主的用户级或项目级 Skills 目录。不同产品的目录和启用方式可能变化，请以对应官方文档为准。

### 下载 ZIP

在 GitHub 点击 **Code → Download ZIP**，解压后把整个 `evidence-based-nutrition-advisor` 文件夹放入宿主的 Skills 目录；如果宿主支持上传 Skill ZIP，也可直接上传。安装后开启新任务，必要时重启宿主。

## 怎么提问

普通用户：

```text
使用 $evidence-based-nutrition-advisor：吃鱼油能改善血脂吗？
如果这是个人决策且关键信息会改变建议，请先让我点击选择最关键的 3 至 5 项；至多 5 项，不要为凑数提问。收到选择后再生成证据。
```

专业审计：

```text
使用 $evidence-based-nutrition-advisor 做专业证据审计：
比较近期指南与系统综述对维生素 D 预防跌倒的结论，给出 PICOS、效应量、GRADE 五域和冲突原因。
```

单数据库 Meta 证据合成：

```text
使用 $evidence-based-nutrition-advisor，基于 PubMed 和可获得全文，
重新合并某干预对某结局的研究。请先形成 PICOS、主要结局、截止日期和分析方案；
结果不要称为发表级系统综述，并列出无法获取全文或无法提取数据的研究。
```

## 示例与验收

仓库内置 9 个行为验收用例，覆盖模糊提问、产品审计、全文缺失、检索截断、Meta 意图分流和图文一致性。每个用例都有 PNG 与 SVG 结果图，并统一收在[可视化示例页](https://buuaaa.github.io/evidence-based-nutrition-advisor/examples/consumer-answer-demo.html)。商品名案例只出现在案例页，不作为首页代表问题。

普通功效案例的 HTML 不是手写页面，而是由结构化答案、PubMed search manifest、原始 RIS 和逐条筛选 CSV 共同生成。生成器会核对检索式、Query Translation、命中数、筛选数、RIS 散列和全文缺失记录；任一项对不上即拒绝生成。

## 开发与验证

```powershell
python -m unittest discover -s tests -p "test_*.py"
python scripts/build_behavior_case_gallery.py
python scripts/build_before_after_image.py
```

如本机安装了 Codex 的 Skill 校验器：

```powershell
python "$env:USERPROFILE\.codex\skills\.system\skill-creator\scripts\quick_validate.py" .
```

主要目录：

```text
SKILL.md       Skill 入口和模式路由
references/    检索、证据评价、GRADE、研究合成与隐私规则
scripts/       PubMed 检索、HTML 生成、去重和 Meta 工具
templates/     证据卡、筛选日志、提取表和报告模板
examples/      三类用户场景与可复现证据包
tests/         行为用例、单元测试和统计引擎校验
```

## 安全、贡献与许可

不要把病历、健康档案、Cookie、API 密钥、数据库凭据或下载令牌提交到仓库。健康档案只有在用户明确要求时才建立，并须保存在 Skill 和 Git 仓库之外。更多边界见 [HEALTH_AND_PRIVACY.md](HEALTH_AND_PRIVACY.md)，安全问题见 [SECURITY.md](SECURITY.md)。

欢迎提交 Issue 和 Pull Request；提交前请阅读 [CONTRIBUTING.md](CONTRIBUTING.md)。

本项目采用 [MIT License](LICENSE)。Copyright © 2026 BuuaaA。
