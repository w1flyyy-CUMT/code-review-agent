# Code Review Agent 架构说明

本文档说明当前版本 `Code Review Agent` 的核心分层、主链路职责与扩展边界，方便后续在不推倒现有结构的前提下持续演进。

## 1. 设计目标

当前架构围绕以下目标展开：

- 面向 `Git Diff / Patch / PR` 做结构化代码评审
- 保持 `FastAPI + LangGraph` 为主骨架
- 支持技能编排、人工审批、结果持久化与后续恢复
- 为 RAG、Trace / Replay、Evaluation Harness 预留清晰扩展点

## 2. 分层结构

当前项目遵循如下分层：

### 2.1 API 层

职责：

- 接收 HTTP 请求
- 将请求转换为应用服务调用
- 将领域对象转换为稳定的响应模型

当前模块：

- `src/review_agent/api/routes_health.py`
- `src/review_agent/api/routes_reviews.py`
- `src/review_agent/api/routes_approvals.py`
- `src/review_agent/api/schemas.py`
- `src/review_agent/api/deps.py`

约束：

- 不直接承载复杂业务逻辑
- 不在路由中拼接评审链路
- 仓储、图对象、服务实例通过依赖注入获取

### 2.2 Application 层

职责：

- 组织评审任务的创建、查询、审批与恢复
- 负责领域模型与图状态之间的转换
- 负责将任务快照写入仓储

当前模块：

- `src/review_agent/application/review_service.py`
- `src/review_agent/application/approval_service.py`
- `src/review_agent/application/report_service.py`

### 2.3 Agent 层

职责：

- 定义 LangGraph 主链路
- 维护共享状态 `AgentState`
- 承担节点级状态推进与条件分支

当前主链路：

1. `parse_input`
2. `plan_and_route`
3. `execute_review`
4. `reflect_and_decide`
5. `generate_report`

当前阶段主流程说明：

- `parse_input` 已合并原有 `parse_diff + classify_files`，会提取 `ChangedFile.hunks`、Python `symbols`，并推断 `file_type / risk_tags`
- `plan_and_route` 会在 skill 路由基础上补充 `priority_files / analysis_depth / requires_context_review`
- `execute_review` 合并原有 `run_skills + aggregate_findings`，并行执行 skills 后统一聚合 `tool_runs / findings`
- `reflect_and_decide` 会综合严重级别、显式审批标记、证据数量与整体置信度，决定是否进入人工复核
- 审批挂起不再占用单独节点，而是由 `reflect_and_decide` 直接把任务置为 `waiting_approval`

当前模块：

- `src/review_agent/agent/state.py`
- `src/review_agent/agent/nodes.py`
- `src/review_agent/agent/transitions.py`
- `src/review_agent/agent/graph.py`

### 2.4 Domain 层

职责：

- 统一任务、文件、证据、结论、审批、Trace 等核心概念
- 作为 API、Agent、仓储与报告层之间的稳定契约

当前模块：

- `src/review_agent/domain/enums.py`
- `src/review_agent/domain/models.py`
- `src/review_agent/domain/dto.py`

### 2.5 Skills 层

职责：

- 以单一职责方式封装可组合的评审能力
- 对外暴露统一的 skill 调用契约
- 避免把所有评审逻辑堆进单一节点

当前技能：

- `diff_summary_skill`
- `python_static_skill`
- `risk_pattern_skill`
- `test_impact_skill`
- `repo_policy_rag_skill`

说明：

- `python_static_skill` 已接入真实工具
- `repo_policy_rag_skill` 仍为占位实现，后续会接入真实知识库

### 2.6 Tools 层

职责：

- 封装外部命令行工具与 diff 解析能力
- 为 skills 提供稳定的调用结果模型

当前模块：

- `src/review_agent/tools/git_diff_tool.py`
- `src/review_agent/tools/ruff_tool.py`
- `src/review_agent/tools/mypy_tool.py`
- `src/review_agent/tools/pytest_tool.py`
- `src/review_agent/tools/runner.py`

### 2.7 Repository 层

职责：

- 持久化与读取评审任务快照
- 屏蔽 PostgreSQL 与测试内存仓储差异

当前实现：

- `PostgresReviewTaskRepository`：默认运行时仓储
- `InMemoryReviewTaskRepository`：测试与本地隔离场景使用

### 2.8 Reporting 层

职责：

- 输出结构化 JSON 报告
- 输出中文 Markdown 评审报告

当前模块：

- `src/review_agent/reporting/json_report.py`
- `src/review_agent/reporting/markdown_report.py`

## 3. 运行时主流程

一次评审任务的关键流程如下：

1. `POST /reviews` 接收仓库路径与 diff 内容
2. `ReviewService` 创建任务编号并启动 LangGraph
3. Agent 节点解析 diff、规划策略、路由并执行 skills
4. `reflect_and_decide` 统一完成风险评估、置信度估算与人工复核判断
5. 若无需审批，直接进入 `generate_report`
6. 若需要审批，任务在 `reflect_and_decide` 后进入 `waiting_approval`
7. `POST /reviews/{task_id}/approvals` 提交审批结果
8. `ApprovalService` 通过 `resume_after_approval -> generate_report` 恢复执行并更新最终报告

## 4. 当前默认实现约定

为了保证工程闭环一致，当前默认约定如下：

- 运行时仓储默认使用 PostgreSQL
- 配置默认从仓库根目录 `.env` 读取
- 推荐通过 `.env.example` 初始化本地配置
- 百炼 API Key 未配置时，`diff_summary_skill` 会自动回退到本地摘要逻辑
- API 响应默认返回任务状态、审批状态、关键等待信息和 `trace_id`

## 5. 后续演进边界

后续新增能力建议沿当前分层扩展，而不是推倒重来：

- Diff 解析增强：优先放在 `tools` 与 `agent` 的解析/分类节点
- Skill 路由增强：优先放在 `skills/router.py`
- 真实 RAG：新增知识导入、检索与 evidence 组装模块，再接入 `repo_policy_rag_skill`
- Trace / Replay：围绕领域模型与仓储扩展 recorder、查询接口和回放流程
- Evaluation Harness：独立于主链路实现，避免侵入线上路径

## 6. 新人阅读建议

如果你是第一次接触本项目，推荐优先按下面顺序看代码：

1. `README.md`
2. `docs/newcomer-guide.md`
3. `src/review_agent/main.py`
4. `src/review_agent/api/routes_reviews.py`
5. `src/review_agent/application/review_service.py`
6. `src/review_agent/agent/graph.py`
7. `src/review_agent/agent/nodes.py`
8. `src/review_agent/tools/git_diff_tool.py`
9. `src/review_agent/skills/router.py`

这样能先建立“请求如何流动”的整体图，再进入具体实现细节。

## 7. 当前结论

当前结构已经具备持续演进的稳定骨架，后续重点应放在补齐能力，而不是重写框架。新增模块应优先复用现有领域模型、服务边界与仓储契约，保持系统可编排、可解释、可审计、可恢复。
