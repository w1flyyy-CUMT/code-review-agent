# Code Review Agent 项目当前进展说明

本文档用于说明当前版本已经完成的工作、目前具备的能力边界，以及下一阶段的优先事项，方便后续维护、迭代和阶段复盘。

## 1. 项目当前定位

当前仓库已经具备一个可运行的 `FastAPI + LangGraph` 代码评审 Agent MVP，不再只是接口骨架，而是一个具备以下特征的最小工程化版本：

- 有清晰的领域模型与状态模型
- 有完整可运行的评审主链路
- 有可扩展的 skill 体系
- 有真实工具接入能力
- 有人工审批与恢复执行闭环
- 有中文结构化报告输出
- 有 PostgreSQL 持久化能力
- 有基础测试与静态检查基线

如果按成熟度粗分，当前版本大致处于“可运行 MVP”阶段，已经从“验证思路”进入“补齐关键能力”的阶段。

## 2. 已完成能力

### 2.1 工程基础

已完成：

- 使用 `uv` 管理依赖、锁文件与虚拟环境
- 使用 `src/` 布局组织 Python 包
- 配置 `ruff / mypy / pytest`
- 使用 `.env` 统一管理中间件与服务配置
- 保持中文文档、中文说明、显式类型标注

对应文件：

- [pyproject.toml](/D:/workspace/myagent/pyproject.toml)
- [uv.lock](/D:/workspace/myagent/uv.lock)
- [AGENTS.md](/D:/workspace/myagent/AGENTS.md)
- [README.md](/D:/workspace/myagent/README.md)
- [architecture.md](/D:/workspace/myagent/docs/architecture.md)
- [.env.example](/D:/workspace/myagent/.env.example)

### 2.2 API 层

已完成：

- 健康检查接口
- 创建评审任务接口
- 查询评审任务接口
- 提交审批结果接口

当前可用接口：

- `GET /health`
- `POST /reviews`
- `GET /reviews/{task_id}`
- `POST /reviews/{task_id}/approvals`

当前响应已统一包含以下关键字段：

- `task_id`
- `status`
- `risk_level`
- `approval_required`
- `approval_status`
- `current_node`
- `next_action`
- `waiting_reason`
- `trace_id`
- `findings`
- `report_markdown`

对应文件：

- [main.py](/D:/workspace/myagent/src/review_agent/main.py)
- [routes_health.py](/D:/workspace/myagent/src/review_agent/api/routes_health.py)
- [routes_reviews.py](/D:/workspace/myagent/src/review_agent/api/routes_reviews.py)
- [routes_approvals.py](/D:/workspace/myagent/src/review_agent/api/routes_approvals.py)
- [schemas.py](/D:/workspace/myagent/src/review_agent/api/schemas.py)

### 2.3 领域模型与状态模型

已完成：

- 任务状态、风险等级、审批状态等枚举
- `ChangedFile / Evidence / Finding / ToolRunResult / ReviewTask`
- LangGraph 共用状态 `AgentState`
- Skill 输入输出契约

这一层的价值在于：主链路、持久化、报告生成、审批恢复都建立在同一套模型上，避免散落的 `dict` 和不稳定结构。

对应文件：

- [enums.py](/D:/workspace/myagent/src/review_agent/domain/enums.py)
- [models.py](/D:/workspace/myagent/src/review_agent/domain/models.py)
- [state.py](/D:/workspace/myagent/src/review_agent/agent/state.py)
- [base.py](/D:/workspace/myagent/src/review_agent/skills/base.py)

### 2.4 LangGraph 主链路

当前主链路已经打通：

1. `parse_input`
2. `plan_and_route`
3. `execute_review`
4. `reflect_and_decide`
5. `generate_report`

当前能力包括：

- 解析 diff
- 提取 hunk 与 Python symbols
- 文件分类与风险标签补充
- 轻量评审策略规划与 skill 路由
- 并行执行 skills
- findings 聚合与去重
- 风险评估、置信度估算与人工复核判断
- 审批挂起与审批后恢复
- 报告生成

对应文件：

- [graph.py](/D:/workspace/myagent/src/review_agent/agent/graph.py)
- [nodes.py](/D:/workspace/myagent/src/review_agent/agent/nodes.py)
- [transitions.py](/D:/workspace/myagent/src/review_agent/agent/transitions.py)

### 2.5 Skill 体系

当前已实现并接入：

- `diff_summary_skill`
- `python_static_skill`
- `risk_pattern_skill`
- `test_impact_skill`
- `repo_policy_rag_skill`

说明：

- `python_static_skill` 已接入真实工具
- `risk_pattern_skill` 与 `test_impact_skill` 目前仍以启发式规则为主
- `repo_policy_rag_skill` 目前仍为占位实现
- `SkillRouter` 已开始结合 `risk_tags / symbols` 进行路由

对应文件：

- [registry.py](/D:/workspace/myagent/src/review_agent/skills/registry.py)
- [router.py](/D:/workspace/myagent/src/review_agent/skills/router.py)
- [diff_summary.py](/D:/workspace/myagent/src/review_agent/skills/diff_summary.py)
- [python_static.py](/D:/workspace/myagent/src/review_agent/skills/python_static.py)
- [risk_pattern.py](/D:/workspace/myagent/src/review_agent/skills/risk_pattern.py)
- [test_impact.py](/D:/workspace/myagent/src/review_agent/skills/test_impact.py)
- [repo_policy_rag.py](/D:/workspace/myagent/src/review_agent/skills/repo_policy_rag.py)

### 2.6 工具接入

已完成：

- `Git diff` 结构化解析
- `Ruff / MyPy / pytest` 封装
- 针对目标仓库存在性与目标文件存在性的降级处理
- 工具执行结果纳入结构化报告

当前 diff 解析已支持：

- 文件级增删行统计
- `hunks` 提取
- Python `function / class / import` 级别 `symbols` 提取

对应文件：

- [runner.py](/D:/workspace/myagent/src/review_agent/tools/runner.py)
- [ruff_tool.py](/D:/workspace/myagent/src/review_agent/tools/ruff_tool.py)
- [mypy_tool.py](/D:/workspace/myagent/src/review_agent/tools/mypy_tool.py)
- [pytest_tool.py](/D:/workspace/myagent/src/review_agent/tools/pytest_tool.py)
- [git_diff_tool.py](/D:/workspace/myagent/src/review_agent/tools/git_diff_tool.py)

### 2.7 报告输出

已完成：

- JSON 报告
- 中文 Markdown 报告
- 通过 reporting 层统一生成报告

报告内容已包含：

- 任务状态
- 风险等级
- 审批状态
- changed files
- findings
- tool runs
- trace_id

对应文件：

- [json_report.py](/D:/workspace/myagent/src/review_agent/reporting/json_report.py)
- [markdown_report.py](/D:/workspace/myagent/src/review_agent/reporting/markdown_report.py)
- [report_service.py](/D:/workspace/myagent/src/review_agent/application/report_service.py)

### 2.8 持久化

已完成：

- 抽象 `ReviewTaskRepository` 仓储契约
- 提供 `PostgresReviewTaskRepository`
- 使用 PostgreSQL 存储任务快照
- 应用启动后按需自动建表
- 保留内存仓储用于测试隔离

当前策略：

- 生产路径默认走 PostgreSQL
- 测试中通过依赖覆盖使用 `InMemoryReviewTaskRepository`
- 当前以 JSONB 保存整份任务快照，优先保证落地和演进速度

对应文件：

- [review_task_repo.py](/D:/workspace/myagent/src/review_agent/repository/review_task_repo.py)
- [postgres_review_task_repo.py](/D:/workspace/myagent/src/review_agent/repository/postgres_review_task_repo.py)
- [deps.py](/D:/workspace/myagent/src/review_agent/api/deps.py)

### 2.9 配置管理

已完成：

- 通过 `pydantic-settings` 管理配置
- 默认从 `.env` 读取配置
- 支持数据库与百炼兼容环境变量
- 提供 `.env.example`

当前统一管理的中间件配置包括：

- PostgreSQL
- DashScope / 百炼
- 服务监听地址与端口

对应文件：

- [settings.py](/D:/workspace/myagent/src/review_agent/config/settings.py)
- [.env.example](/D:/workspace/myagent/.env.example)

### 2.10 测试与质量基线

已完成：

- diff 解析测试
- `python_static_skill` 降级测试
- `diff_summary_skill` 降级测试
- SkillRouter 路由测试
- 风险评分与审批状态机测试
- 报告构建与报告服务测试
- API 集成测试
- PostgreSQL 仓储测试
- `.env` 配置加载测试

当前质量检查基线：

- `uv run ruff check .`
- `uv run mypy src tests`
- `uv run pytest`

当前全量测试会覆盖：

- 配置文件加载
- API 关键响应结构
- PostgreSQL 仓储
- LangGraph 状态流转
- 技能路由与报告输出

对应文件：

- [tests](/D:/workspace/myagent/tests)

## 3. 当前仍待补齐的关键能力

### 3.1 Trace / Replay

当前状态：

- 已有 `trace_id` 和 `TraceEvent`
- 但还没有节点级 trace recorder
- 也还没有 trace 查询接口与 replay 流程

下一步建议：

- 为每个关键节点记录 trace 事件
- 将 trace 持久化到 PostgreSQL
- 新增 trace 查询接口
- 支持按 trace 回放评审链路

### 3.2 Diff 解析增强

当前状态：

- 已能识别文件路径、语言、增删行数
- 已能填充 `hunks / symbols`
- 但当前 symbols 仍以 Python 的启发式提取为主
- 风险标签和路由规则仍有继续细化空间

下一步建议：

- 增加更多语言或框架级符号提取
- 继续增强文件级风险标签质量
- 让 findings 能更精准引用 hunk / symbol 位置

### 3.3 RAG 接入

当前状态：

- `repo_policy_rag_skill` 仍是占位实现

下一步建议：

- 建立知识导入脚本
- 确定切块、索引与检索策略
- 将检索结果转成 evidence bundle 并进入 findings

### 3.4 Evaluation Harness

当前状态：

- 已有基础测试和静态检查
- 但还没有独立评估集与指标体系

下一步建议：

- 建立标准 case 集
- 增加路由准确率、误报率、高风险召回率等指标
- 支持模型/策略对比

## 4. 当前项目成熟度判断

如果将项目阶段粗分为：

1. 概念设计
2. 代码骨架
3. 可运行 MVP
4. 接近生产的可演示版本

那么当前版本更接近：

> `3`，即“可运行 MVP，并开始补齐工程化能力”

原因是：

- 主链路已经能跑通
- API、skills、tools、reporting、审批恢复已经连起来
- PostgreSQL 持久化已经落地
- `.env` 配置管理已经统一
- `.env.example` 与架构文档已经补齐
- diff 结构化解析和 skill 路由已经完成第一版增强
- 测试和静态检查已经形成稳定基线

但以下关键能力还没有真正落地完成：

- trace / replay
- 真实 RAG
- 更强的 diff 语义解析
- 完整评估体系

## 5. 下一步建议顺序

建议按以下顺序继续推进：

1. `repo_policy_rag_skill` 真接入
2. trace recorder 与 trace 持久化
3. trace 查询接口与 replay 流程
4. evaluation harness
5. 更完整的 CLI 工作流

这样推进的原因是：

- 先把“状态可追踪”和“过程可观察”做稳
- 再提升分析质量
- 最后补齐评估与使用入口

## 6. 当前结论

当前项目已经完成了一版较扎实的代码评审 Agent MVP。它已经不是简单的大模型问答 Demo，而是具备以下核心特征的工程雏形：

- 有 agent 主链路
- 有 skill 分层
- 有真实工具接入
- 有审批恢复闭环
- 有 PostgreSQL 持久化
- 有 `.env` 配置管理
- 有中文文档与质量基线

下一阶段的重点已经不是“从零搭起来”，而是优先把真实 RAG 接入做成最小可运行版本，再继续补 trace、replay 和评估体系。
