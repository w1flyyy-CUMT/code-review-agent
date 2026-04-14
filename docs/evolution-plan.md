# Code Review Agent 演进方案与 Prompt 设计

本文档基于当前仓库代码、现有测试、README 和项目状态说明整理，目标是：

- 分析当前项目真实状态
- 对照项目目标找出差距
- 给出一份可执行的详细演进路线
- 为每个阶段提供可直接使用的 Prompt

---

## 1. 当前项目状态分析

## 1.1 当前已经具备的能力

结合当前代码和测试，项目已经具备以下能力：

- 已完成 `FastAPI + LangGraph` 主链路搭建
- 已完成统一领域模型、统一 AgentState、统一 Skill 契约
- 已实现基础代码评审流程：
  - `parse_diff`
  - `classify_files`
  - `route_skills`
  - `run_skills`
  - `aggregate_findings`
  - `score_risk`
  - `approval_gate`
  - `resume_after_approval`
  - `generate_report`
- 已接入真实工具：
  - `Ruff`
  - `MyPy`
  - `pytest`
- 已接入大模型：
  - 阿里云百炼平台
  - 当前用于 `diff_summary_skill`
- 已有人工审批恢复链路
- 已有 PostgreSQL 仓储实现
- 已有基础测试与静态检查

当前成熟度判断：

> 项目已经超过“代码骨架”阶段，属于“可运行 MVP”，并开始向“接近生产可演示版本”演进。

---

## 1.2 当前和项目目标之间的差距

虽然当前已经有可运行版本，但和最初“可编排、可解释、可审计、可人工接管、可评估”的目标相比，还差以下关键能力：

### 还不够强的地方

- Diff 解析较浅
  - 还没有真正提取完整 `hunk / symbols / function impact`
- RAG 还是占位
  - `repo_policy_rag_skill` 还没有真实知识库接入
- Trace / Replay 还没落地
  - 目前只有 `trace_id` 和基础事件结构，没有完整 recorder、查询、回放
- Evaluation Harness 还没建起来
  - 现在只有测试，不是正式评估体系
- 持久化还不够完整
  - 虽然已有 PostgreSQL 仓储，但还缺完整的任务、trace、feedback、知识索引设计
- 大模型使用还偏少
  - 当前只有 `diff_summary_skill` 用到了百炼
  - 复杂语义风险判断、RAG 证据整合、review comment 生成还没用起来
- 缺 CLI 工作流
  - 当前主要依赖 API，工程化入口还不完整

---

## 1.3 对当前状态的判断

当前项目最值得肯定的地方不是“功能多”，而是结构已经比较对。

具体来说：

- 主流程已经不是杂乱函数堆叠，而是状态驱动的 graph
- Tool 和 Skill 的边界已经清楚
- 审批恢复逻辑已经被单独建模
- 大模型已经不是“万能入口”，而是被放在合适的位置

这意味着：

> 现在这个项目最适合做“能力补齐型演进”，而不是推倒重来。

---

## 2. 演进总原则

后续演进建议遵循下面 5 个原则：

1. 先补“可追踪”和“可恢复”，再补“更聪明”
2. 大模型只放在规则和工具覆盖不到、但业务价值高的位置
3. 每加一个能力，都尽量配测试、文档和验收标准
4. 优先做对系统结构影响大的能力
5. 每一阶段都要能形成一个稳定里程碑

---

## 3. 推荐演进路线

建议分 5 个阶段推进。

---

## 阶段一：补齐可运行 MVP 的工程闭环

### 目标

把当前“能跑”的版本，提升为“更稳定、更一致、更便于继续开发”的版本。

### 主要工作

- 梳理并统一文档
  - README
  - `docs/project-status.md`
  - `docs/architecture.md`
- 补 `.env.example`
- 明确 PostgreSQL 是否为默认仓储实现
- 统一 API 响应模型
- 补 trace 基础字段写入
- 清理遗留乱码和中英混杂问题

当前状态：

- 已补齐 `.env.example`
- 已新增 `docs/architecture.md`
- 已统一 README、项目状态文档与 API 关键响应字段
- 本阶段后续无需继续扩张功能，可直接进入阶段二

### 验收标准

- README、状态文档、代码结构一致
- `.env.example` 可直接复制使用
- 新同学按照 README 能启动服务
- `uv run ruff check .`
- `uv run mypy src tests`
- `uv run pytest`
  全部通过

### 阶段一 Prompt

```text
你正在维护一个基于 FastAPI + LangGraph 的 Code Review Agent 项目。

请先不要增加新功能，而是先做“工程闭环整理”：
1. 对齐 README、docs/project-status.md、代码实现之间的不一致
2. 补充 .env.example，覆盖 PostgreSQL 和阿里云百炼配置
3. 检查 API、配置、仓储默认实现是否一致
4. 清理乱码、过时说明和中英混杂问题
5. 保持所有注释、文档、示例为中文

要求：
- 不改变主链路行为
- 保持现有测试通过
- 如需改动文档，请用通俗语言
- 最后运行 ruff、mypy、pytest 并报告结果
```

---

## 阶段二：强化 Diff 解析与路由质量

### 目标

让系统真正“理解变更结构”，而不是只看文件路径和增删行数。

### 主要工作

- 增强 `git_diff_tool`
- 提取 `Hunk`
- 提取函数/类/导入等 symbol
- 为 `ChangedFile` 补充更准确的 `risk_tags`
- 优化 `classify_files_node`
- 优化 `SkillRouter`

### 具体产出

- 更完整的 `ChangedFile.hunks`
- 更完整的 `ChangedFile.symbols`
- 更准确的 `risk_tags`
- 对应单测

当前状态：

- 已完成 `GitDiffTool` 的 `hunks` 提取
- 已完成 Python `function / class / import` 级别 `symbols` 提取
- `classify_files_node` 已开始结合路径、symbols 和 hunk header 生成 `file_type / risk_tags`
- `SkillRouter` 已开始消费 `risk_tags / symbols`
- 已补充对应单元测试

### 为什么这一阶段重要

因为后面这些能力都依赖它：

- `risk_pattern_skill`
- `test_impact_skill`
- RAG 检索路由
- finding 精准定位

### 验收标准

- `ChangedFile` 中能看到 hunk 信息
- `ChangedFile.symbols` 至少能覆盖 Python 函数/类
- skill 路由测试更新并通过
- 核心解析逻辑有单元测试

### 阶段二 Prompt

```text
请为当前 Code Review Agent 增强 diff 解析能力，重点提升“结构化理解变更”的能力。

目标：
1. 增强 git_diff_tool，提取 hunk 信息
2. 对 Python 文件提取函数、类、导入等 symbols
3. 优化 classify_files_node，为 ChangedFile 增加更准确的 file_type 和 risk_tags
4. 更新 SkillRouter，让路由不只依赖文件路径，还依赖 risk_tags 和 symbols
5. 为新增逻辑补单元测试

要求：
- 保持领域模型一致
- 不要引入破坏性重构
- 注释、文档、测试说明使用中文
- 最后运行 ruff、mypy、pytest
```

---

## 阶段三：接入真实 RAG

### 目标

让 `repo_policy_rag_skill` 从占位实现变成真实可用能力。

### 主要工作

- 设计知识源
  - 团队代码规范
  - 安全文档
  - ADR
  - 历史 review comment
- 设计知识切块模型
- 设计检索接口
- 给 finding 补充 evidence bundle
- 将 RAG 变成按需触发，而不是默认执行

### 推荐实现思路

- 第一版可先用 PostgreSQL + pgvector
- 或先用本地简化向量库做 MVP
- 增加：
  - `knowledge_chunk`
  - `retriever`
  - `retrieval_router`

### 大模型在这一阶段的作用

这一阶段是大模型的第二个重点使用场景：

- 不负责“先查知识库再回答一切”
- 而是负责“把检索到的规范和当前代码问题结合起来”

### 验收标准

- `repo_policy_rag_skill` 不再是占位实现
- 能将检索结果放进 findings.evidences
- 能区分哪些任务需要 RAG
- 有至少 1 组端到端测试

### 阶段三 Prompt

```text
请为当前 Code Review Agent 接入真实 RAG，重点完成 repo_policy_rag_skill 的落地。

目标：
1. 设计知识切块模型和索引结构
2. 实现知识导入与检索接口
3. 为 repo_policy_rag_skill 接入真实检索
4. 将检索结果封装为 evidence bundle 并写入 findings
5. 保持 RAG 为“按需触发”，不要改成默认全量检索

要求：
- 优先做最小可运行版本
- 保持领域模型一致
- 注释和文档都使用中文
- 为关键路径补测试
- 最后运行 ruff、mypy、pytest
```

---

## 阶段四：强化大模型使用场景

### 目标

让大模型从“只做摘要”升级为“做高价值语义增强”。

### 重点使用场景

1. `risk_pattern_skill`
- 规则先命中
- 大模型再解释风险含义

2. `repo_policy_rag_skill`
- 将检索到的规范与当前 diff 结合，生成更像正式 review 的结论

3. `review comment generation`
- 把结构化 findings 组织为更自然的评论文本

### 不建议的做法

- 不要让大模型替代工具执行
- 不要让大模型直接替代 diff parser
- 不要让大模型无证据地产生高风险结论

### 验收标准

- 至少两个 skill 明确接入百炼
- 有“调用失败自动回退”逻辑
- 高风险 finding 的 evidence 更完整
- 新增 LLM 行为有测试或可验证示例

### 阶段四 Prompt

```text
请扩展当前 Code Review Agent 中大模型的使用范围，但保持“规则优先、模型增强”的原则。

重点目标：
1. 在 risk_pattern_skill 中加入百炼辅助解释能力
2. 在 repo_policy_rag_skill 中加入“规范证据 + 代码问题”的整合能力
3. 为最终 finding 增加更自然的 review_comment 生成逻辑
4. 保留无 Key、调用失败、超时情况下的回退策略

要求：
- 大模型不要替代工具执行
- 高风险结论必须保留 evidence
- 所有中文输出保持简洁、专业、适合代码评审场景
- 为新增行为补测试或最小验证样例
- 最后运行 ruff、mypy、pytest
```

---

## 阶段五：建立 Trace / Replay / Evaluation Harness

### 目标

把项目从“能跑”提升到“可追踪、可复现、可评估”。

### 主要工作

- 为每个关键节点记录 trace
- 增加 trace 查询接口
- 增加 replay 逻辑
- 建立评估数据集
- 跑指标：
  - `skill_route_accuracy`
  - `false_positive_rate`
  - `high_risk_recall`
  - `evidence_coverage`
  - `approval_trigger_accuracy`

### 为什么这一阶段重要

这是这个项目区别于普通 Demo 的关键：

- 不只是“模型会说”
- 而是“系统可解释、可复盘、可持续优化”

### 验收标准

- 至少关键节点有 trace
- 支持通过接口查询 trace
- 有 replay 示例
- 有最小评估集和评估结果输出

### 阶段五 Prompt

```text
请为当前 Code Review Agent 建立 Trace / Replay / Evaluation Harness。

目标：
1. 为关键节点记录 trace event
2. 设计 trace 查询接口
3. 支持按 task_id 或 trace_id 回放一次评审流程
4. 建立最小评估集
5. 输出基础指标报告，如 skill_route_accuracy、false_positive_rate、high_risk_recall

要求：
- 不追求一次做全，先完成最小可运行版本
- 设计尽量兼容当前领域模型和仓储结构
- 文档、注释和示例使用中文
- 最后运行 ruff、mypy、pytest
```

---

## 4. 一份总控 Prompt

如果你想把这个项目交给一个编码 Agent 按阶段连续推进，推荐用下面这份总控 Prompt。

```text
你正在维护一个基于 FastAPI + LangGraph 的 Code Review Agent 项目。

项目目标：
- 面向 Git Diff / Patch / PR 做结构化代码评审
- 具备 Harness、Skills、RAG、Human-in-the-Loop
- 强调可编排、可解释、可审计、可恢复、可评估

当前状态：
- 已有统一领域模型和 AgentState
- 已有 LangGraph 主链路
- 已有 python_static_skill，接入 Ruff / MyPy / pytest
- 已有 diff_summary_skill，接入阿里云百炼
- 已有审批恢复流程
- 已有 PostgreSQL 仓储实现

请按照以下原则继续演进：
1. 先补工程闭环与一致性
2. 再增强 diff 解析与 skill 路由
3. 再接入真实 RAG
4. 再扩展大模型在高价值场景中的使用
5. 最后补齐 Trace / Replay / Evaluation Harness

要求：
- 每次只做一个清晰阶段
- 优先保持现有结构，不随意推倒重来
- 注释、文档、示例全部使用中文
- 遵循 Python 最佳工程实践
- 使用 uv 管理依赖
- 每次完成后都更新 README 和相关 docs
- 每次完成后都运行：
  - uv run ruff check .
  - uv run mypy src tests
  - uv run pytest

输出时请始终包含：
- 本次目标
- 修改的关键模块
- 验收结果
- 下一步建议
```

---

## 5. 推荐优先级结论

如果只给一个最推荐的顺序，我建议这样做：

1. 补工程闭环
2. 强化 diff 解析
3. 接真实 RAG
4. 扩展百炼在风险分析和评论生成中的使用
5. 建立 trace / replay / evaluation

最重要的原因是：

> 现在系统结构已经够稳，不要再花太多时间改框架，应该开始补真正决定项目质量上限的能力。

---

## 6. 当前阶段的建议动作

如果现在立刻进入下一轮开发，我最推荐你先做：

> 阶段三：接入真实 RAG

原因：

- 阶段二已经把结构化输入打好了基础
- 现在可以把 `repo_policy_rag_skill` 从占位实现推进到最小可运行版本
- 相比先做 trace / replay，RAG 更直接影响评审结果质量

如果你更在意“项目展示效果”，那就优先做：

> 阶段四：扩展大模型使用场景

因为这会让项目更像一个“真正的 Agent”，而不仅是工具编排器。
