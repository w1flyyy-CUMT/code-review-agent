"""Markdown 报告生成。"""

from review_agent.domain.models import ReviewTask


class MarkdownReportBuilder:
    """生成中文 Markdown 报告。"""

    def build(self, task: ReviewTask) -> str:
        """构建 Markdown 文本。"""
        lines = [
            "# 代码评审报告",
            "",
            f"- 任务编号：`{task.task_id}`",
            f"- 当前状态：`{task.status.value}`",
            f"- 风险等级：`{task.risk_level.value}`",
            f"- 分析深度：`{task.analysis_depth or 'standard'}`",
            f"- 整体置信度：`{task.confidence if task.confidence is not None else 'n/a'}`",
            f"- 证据数量：`{task.evidence_count}`",
            f"- 审批状态：`{task.approval_status.value}`",
            "",
            "## 评审策略",
        ]

        if not task.priority_files:
            lines.append("- 本次未识别出需要额外优先关注的文件")
        else:
            for file_path in task.priority_files:
                lines.append(f"- 优先关注：`{file_path}`")

        if task.manual_review_reasons:
            lines.append("")
            lines.append("## 人工复核建议")
            for reason in task.manual_review_reasons:
                lines.append(f"- {reason}")

        lines.extend(
            [
                "",
            "## 变更文件",
            ]
        )

        if not task.changed_files:
            lines.append("- 未解析到变更文件")
        else:
            for changed_file in task.changed_files:
                lines.append(
                    f"- `{changed_file.path}`："
                    f"新增 {changed_file.added_lines} 行，删除 {changed_file.deleted_lines} 行"
                )

        lines.append("")
        lines.append("## Findings")

        if not task.findings:
            lines.append("- 暂未发现结构化问题")
        else:
            for finding in task.findings:
                lines.extend(
                    [
                        f"### {finding.title}",
                        f"- 类别：`{finding.category}`",
                        f"- 严重级别：`{finding.severity.value}`",
                        f"- 置信度：`{finding.confidence}`",
                        f"- 摘要：{finding.summary}",
                        f"- 建议：{finding.suggestion}",
                        "",
                    ]
                )

        lines.append("## 工具执行结果")
        if not task.tool_runs:
            lines.append("- 本次未执行外部工具")
        else:
            for tool_run in task.tool_runs:
                status_text = (
                    "跳过" if tool_run.skipped else ("成功" if tool_run.success else "失败")
                )
                lines.append(f"- `{tool_run.tool_name}`：{status_text}，{tool_run.summary}")

        if task.approval_record is not None:
            lines.extend(
                [
                    "## 审批记录",
                    f"- 决策：`{task.approval_record.decision.value}`",
                    f"- 说明：{task.approval_record.comment or '无'}",
                    "",
                ]
            )

        return "\n".join(lines)
