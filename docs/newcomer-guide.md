# Code Review Agent 新人学习路径

本文档面向第一次接触本项目的同学，目标是帮助你在较短时间内建立整体认知，并能开始安全地做阶段性改动。

## 1. 先理解项目是什么

这个项目是一个面向 `Git Diff / Patch / PR` 的结构化代码评审 Agent，而不是单纯的大模型问答接口。

它当前主要做四件事：

- 把原始 diff 解析成结构化变更数据
- 用 LangGraph 编排完整评审流程
- 通过 skills 执行摘要、静态分析、风险识别和测试影响判断
- 将结果持久化、生成报告，并在高风险场景接入人工审批

如果先记一句话，可以记成：

> 这是一个“图编排 + 规则/工具优先 + 大模型增强”的代码评审系统。

## 2. 推荐阅读顺序

建议按下面顺序阅读，而不是一开始就把 `src/` 整体扫一遍：

1. [README.md](/D:/workspace/myagent/README.md)
2. [docs/architecture.md](/D:/workspace/myagent/docs/architecture.md)
3. [docs/project-status.md](/D:/workspace/myagent/docs/project-status.md)
4. [src/review_agent/main.py](/D:/workspace/myagent/src/review_agent/main.py)
5. [src/review_agent/api/routes_reviews.py](/D:/workspace/myagent/src/review_agent/api/routes_reviews.py)
6. [src/review_agent/application/review_service.py](/D:/workspace/myagent/src/review_agent/application/review_service.py)
7. [src/review_agent/agent/graph.py](/D:/workspace/myagent/src/review_agent/agent/graph.py)
8. [src/review_agent/agent/nodes.py](/D:/workspace/myagent/src/review_agent/agent/nodes.py)
9. [src/review_agent/domain/models.py](/D:/workspace/myagent/src/review_agent/domain/models.py)
10. [src/review_agent/tools/git_diff_tool.py](/D:/workspace/myagent/src/review_agent/tools/git_diff_tool.py)
11. [src/review_agent/skills/router.py](/D:/workspace/myagent/src/review_agent/skills/router.py)
12. [tests/](/D:/workspace/myagent/tests)

这样读的好处是：

- 先知道系统对外提供什么能力
- 再知道请求是如何进入主链路的
- 最后回头理解领域模型、解析器和 skills

## 3. 第一天建议怎么上手

### 3.1 先把环境跑通

```bash
uv sync
Copy-Item .env.example .env
uv run ruff check .
uv run mypy src tests
uv run pytest
```

如果本地还没有 PostgreSQL，可以先跑测试，再按 README 配置数据库后启动服务。

### 3.2 沿着一条真实请求看代码

最推荐的切入点是 `POST /reviews` 这条链路：

1. 请求进入 `routes_reviews.py`
2. 路由调用 `ReviewService.create_review`
3. `ReviewService` 启动 LangGraph
4. `graph.py` 组织节点顺序
5. `nodes.py` 完成解析、分类、路由、执行和报告生成
6. 任务快照写入仓储并返回 API 响应

只要你把这条链路看通，项目的大部分结构就建立起来了。

## 4. 各层重点看什么

### 4.1 Domain 层

先重点理解这些模型：

- `ChangedFile`
- `Hunk`
- `Finding`
- `ReviewTask`
- `AgentState`

这层是整个项目的共享语言。很多“看不懂调用链”的问题，最后都要回到这里。

### 4.2 Agent 层

重点看：

- `build_review_graph`
- `build_resume_graph`
- `parse_diff_node`
- `classify_files_node`
- `route_skills_node`
- `run_skills_node`

Agent 层解决的是“流程怎么走”，而不是“某个能力如何实现”。

### 4.3 Tools 层

重点看：

- `git_diff_tool` 如何把原始 diff 解析成 `ChangedFile / Hunk / symbols`
- `ruff / mypy / pytest` 的封装如何统一成结构化输出

如果你想参与后续 diff 增强、RAG 路由或静态分析接入，这层会非常关键。

### 4.4 Skills 层

重点理解：

- skill 的统一输入输出契约
- `SkillRouter` 如何决定执行哪些能力
- 哪些 skill 是规则驱动，哪些会调用真实工具或大模型

建议先看：

- `diff_summary_skill`
- `python_static_skill`
- `risk_pattern_skill`

## 5. 新人最容易困惑的几个点

### 5.1 为什么有 API 层还要有 Application 层？

因为路由只负责请求转换，真正的业务组织放在应用服务里，更容易测试，也更符合当前架构约束。

### 5.2 为什么有 skills 还要有 LangGraph？

skill 负责“做什么能力”，LangGraph 负责“这些能力何时执行、按什么顺序执行、是否需要审批”。

### 5.3 为什么不是所有事情都交给大模型？

这是项目当前的重要原则：

- 能用规则解决的，先用规则
- 能用真实工具解决的，先用工具
- 只有在高价值、规则覆盖不足的场景，才用大模型增强

## 6. 最推荐的调试方式

建议按下面顺序定位问题：

1. 先找 `tests/` 中最接近的用例
2. 再看 `routes -> service -> graph -> node` 的调用链
3. 重点观察 `changed_files`、`selected_skills`、`skill_results`
4. 最后再看仓储快照和报告输出

这比直接从最终 Markdown 报告倒推更高效。

## 7. 第一次提交适合做什么

对新人来说，最适合的第一批任务通常是：

- 补测试
- 补文档和示例
- 优化 diff 分类规则
- 增加新的 `risk_tags`
- 调整 skill 路由条件

不建议一开始就做：

- 大范围重构 LangGraph 主链路
- 一次性接入完整 RAG 基础设施
- 同时修改仓储、API、报告和审批流程

## 8. 一个很适合练手的小练习

建议你做下面这个练习：

1. 准备一个包含 Python 函数改动的 diff
2. 调 `GitDiffTool.parse`
3. 看 `ChangedFile.hunks`、`symbols`、`risk_tags`
4. 再看 `SkillRouter.route` 的输出
5. 最后跑对应测试

这个练习能很快把“解析 -> 分类 -> 路由”这条主线串起来。

## 9. 当前最值得优先熟悉的模块

如果你准备继续参与下一阶段迭代，最值得先熟悉的是：

- [src/review_agent/tools/git_diff_tool.py](/D:/workspace/myagent/src/review_agent/tools/git_diff_tool.py)
- [src/review_agent/agent/nodes.py](/D:/workspace/myagent/src/review_agent/agent/nodes.py)
- [src/review_agent/skills/router.py](/D:/workspace/myagent/src/review_agent/skills/router.py)

因为后续真实 RAG、风险增强和评估能力，都会建立在这些结构化输入之上。
