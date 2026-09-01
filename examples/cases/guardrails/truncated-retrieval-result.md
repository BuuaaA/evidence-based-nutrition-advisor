# 用例 6 运行记录：检索被截断

输入条件：PubMed 命中 650 条。脚本默认会按每批 200 条分页，依次获取 200、200、200、50 条。本用例人为设置 `--retmax=200`，模拟把总导出量错误限制为 200 条。

运行 `tests/test_pubmed_search.py::test_rejects_silent_truncation` 后，`pubmed_search.py` 抛出 `ValueError`，拒绝生成可被下游误认为完整检索的 manifest。与生成器的完整性校验合用时：

- 不得设置 `complete_retrieval=true`；
- 不得输出 `rapid_grade`；
- 确定性功效结论必须退化为“暂不能可靠判断”；
- 下一步只能是缩窄 PICOS、完成剩余命中的筛查，或把任务升级为更完整的证据综合。

因此，200 是单批大小，不是工具的总导出上限。本案例是合成输入的自动化回归测试，不是临床研究结论。
