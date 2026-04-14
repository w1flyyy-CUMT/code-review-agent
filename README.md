# Code Review Agent

面向 `Git Diff / Patch / PR` 的结构化代码评审 Agent 项目。

当前版本以 `FastAPI + LangGraph` 为主骨架，已经具备以下能力：

- 基于 `FastAPI` 提供评审与审批接口
- 基于 `LangGraph` 编排评审主链路
- 使用 `uv` 管理依赖、虚拟环境与锁文件
- 输出结构化 JSON 和中文 Markdown 报告
- 接入阿里云百炼兼容接口生成 diff 摘要
- 使用 PostgreSQL 持久化评审任务快照
- 支持人工审批与审批后恢复执行

补充说明可参考：

- [项目状态说明](./docs/project-status.md)
- [架构说明](./docs/architecture.md)
- [新人学习路径](./docs/newcomer-guide.md)
- [演进方案](./docs/evolution-plan.md)

## 环境要求

- Python `3.13`
- `uv`
- PostgreSQL `14+`

## 安装依赖

```bash
uv sync
```

## 配置方式

项目默认从仓库根目录的 `.env` 读取配置。推荐先基于示例文件初始化：

```powershell
Copy-Item .env.example .env
```

然后按需修改 `.env` 中的变量。`.env` 已加入 `.gitignore`，适合存放本地开发配置。

### 关键配置项

```env
REVIEW_AGENT_HOST=127.0.0.1
REVIEW_AGENT_PORT=8000
REVIEW_AGENT_DATABASE_URL=postgresql://postgres:postgres@127.0.0.1:5432/review_agent
REVIEW_AGENT_DASHSCOPE_API_KEY=your_dashscope_api_key
REVIEW_AGENT_DASHSCOPE_BASE_URL=https://dashscope.aliyuncs.com/compatible-mode/v1
REVIEW_AGENT_DASHSCOPE_MODEL=qwen-plus
REVIEW_AGENT_DASHSCOPE_TIMEOUT_SECONDS=30
```

### PostgreSQL 配置

运行时默认仓储实现为 PostgreSQL。服务启动前必须在 `.env` 或系统环境变量中配置数据库连接：

```env
REVIEW_AGENT_DATABASE_URL=postgresql://postgres:postgres@127.0.0.1:5432/review_agent
```

也支持以下兼容变量名：

```env
DATABASE_URL=postgresql://postgres:postgres@127.0.0.1:5432/review_agent
REVIEW_AGENT_POSTGRES_DSN=postgresql://postgres:postgres@127.0.0.1:5432/review_agent
```

应用首次连接时会自动创建 `review_tasks` 表。

### 百炼配置

项目通过阿里云百炼提供的 OpenAI 兼容接口接入大模型。至少配置以下变量之一：

```env
REVIEW_AGENT_DASHSCOPE_API_KEY=你的百炼 API Key
DASHSCOPE_API_KEY=你的百炼 API Key
```

如果未配置百炼 API Key，`diff_summary_skill` 会自动降级为本地摘要逻辑，不阻塞主流程。

## 启动服务

```bash
uv run review-agent
```

启动后可访问：

- `GET /health`
- `POST /reviews`
- `GET /reviews/{task_id}`
- `POST /reviews/{task_id}/approvals`

## 主链路

```mermaid
flowchart TD
    A["START"] --> B["parse_input"]
    B --> C["plan_and_route"]
    C --> D["execute_review"]
    D --> E["reflect_and_decide"]
    E -->|无需审批| F["generate_report"]
    E -->|等待审批| G["END"]
    H["resume_after_approval"] --> F
    F --> I["END"]
```

当前首轮评审主链路收敛为 5 个核心节点：

1. `parse_input`：解析 diff，并补全 `changed_files / file_type / risk_tags`
2. `plan_and_route`：规划轻量评审策略，产出 `selected_skills / priority_files / analysis_depth`
3. `execute_review`：并行执行 skills，汇总 `tool_runs` 并聚合去重 findings
4. `reflect_and_decide`：做二次判断，产出 `risk_level / confidence / manual_review_reasons`，并决定是否挂起等待审批
5. `generate_report`：基于最新状态生成 JSON / Markdown 报告

## 请求示例

### 创建评审任务

```json
{
  "repo_path": "D:/demo/repo",
  "diff_text": "diff --git a/app/service/user.py b/app/service/user.py\n--- a/app/service/user.py\n+++ b/app/service/user.py\n@@ -1,3 +1,6 @@\n+def load_user_name(user):\n+    return user.name\n"
}
```

### 创建评审任务响应

```json
{
  "task_id": "rvw_xxxxxxxx",
  "status": "completed",
  "risk_level": "low",
  "approval_required": false,
  "approval_status": "not_required",
  "current_node": "generate_report",
  "next_action": null,
  "waiting_reason": null,
  "trace_id": "trc_xxxxxxxx",
  "findings": [],
  "report_markdown": "# 代码评审报告\n..."
}
```

### 提交审批结果

```json
{
  "decision": "approve",
  "comment": "确认发布该高风险提示"
}
```

## 目录结构

```text
src/review_agent/
  api/            HTTP 接口与依赖注入
  agent/          LangGraph 状态、节点与图定义
  application/    评审与审批应用服务
  common/         通用时钟、异常、ID
  config/         配置与日志
  domain/         领域模型与枚举
  llm/            百炼客户端封装
  reporting/      JSON / Markdown 报告输出
  repository/     PostgreSQL 与内存仓储
  skills/         各类评审能力模块
  tools/          外部工具与 diff 解析封装
```

## 新人如何学习这个项目

建议按“先跑通环境，再沿主链路读代码，最后看扩展点”的顺序上手：

1. 阅读 README、架构说明和项目状态说明。
2. 执行 `uv sync`，复制 `.env.example`，跑通 `ruff / mypy / pytest`。
3. 沿 `POST /reviews -> ReviewService -> LangGraph -> nodes -> skills -> tools` 看一次真实请求。
4. 再重点阅读 `domain/models.py`、`agent/nodes.py`、`tools/git_diff_tool.py`、`skills/router.py`。

更完整的阅读顺序、调试方式和第一批适合新人的任务，见 [docs/newcomer-guide.md](./docs/newcomer-guide.md)。

## 质量检查

```bash
uv run ruff check .
uv run mypy src tests
uv run pytest
```

## 当前阶段结论

当前已经完成“阶段二：Diff 解析与 Skill 路由增强”的第一版落地。`git_diff_tool` 已能提取 `hunks` 与 Python `symbols`，文件分类会结合路径、symbols 和 hunk header 生成 `file_type / risk_tags`，`SkillRouter` 也开始消费这些结构化信号。下一步建议进入“真实 RAG 接入”，把 `repo_policy_rag_skill` 从占位实现推进到最小可运行版本。
