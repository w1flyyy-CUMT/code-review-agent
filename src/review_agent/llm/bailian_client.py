"""阿里云百炼平台客户端。"""

from __future__ import annotations

from dataclasses import dataclass

from openai import AsyncOpenAI, OpenAIError

from review_agent.config.settings import Settings, get_settings
from review_agent.domain.models import ChangedFile


@dataclass(slots=True)
class DiffSummaryResult:
    """大模型生成的变更摘要结果。"""

    summary: str
    suggestion: str
    model_name: str


class BailianChatClient:
    """通过百炼 OpenAI 兼容接口访问通义千问模型。"""

    def __init__(self, settings: Settings | None = None) -> None:
        self._settings = settings or get_settings()
        self._client: AsyncOpenAI | None = None

        if self._settings.dashscope_api_key:
            self._client = AsyncOpenAI(
                api_key=self._settings.dashscope_api_key,
                base_url=self._settings.dashscope_base_url,
                timeout=self._settings.dashscope_timeout_seconds,
            )

    @property
    def enabled(self) -> bool:
        """是否已启用百炼客户端。"""
        return self._client is not None

    async def summarize_diff(
        self,
        changed_files: list[ChangedFile],
        diff_text: str,
    ) -> DiffSummaryResult | None:
        """调用百炼生成变更摘要。"""
        if self._client is None:
            return None

        file_lines = [
            (
                f"- 路径：{changed_file.path}；语言：{changed_file.language}；"
                f"新增 {changed_file.added_lines} 行；删除 {changed_file.deleted_lines} 行"
            )
            for changed_file in changed_files[:20]
        ]
        file_block = "\n".join(file_lines) if file_lines else "- 未识别到变更文件"
        trimmed_diff = diff_text[:4000]

        try:
            completion = await self._client.chat.completions.create(
                model=self._settings.dashscope_model,
                temperature=0.2,
                messages=[
                    {
                        "role": "system",
                        "content": (
                            "你是代码评审系统中的变更摘要助手。"
                            "请严格输出两行中文。"
                            "第一行以“摘要：”开头，第二行以“建议：”开头。"
                            "不要输出额外解释。"
                        ),
                    },
                    {
                        "role": "user",
                        "content": (
                            "请基于以下代码变更生成摘要。\n\n"
                            f"变更文件：\n{file_block}\n\n"
                            f"diff 内容：\n{trimmed_diff}"
                        ),
                    },
                ],
            )
        except OpenAIError as exc:
            raise RuntimeError(f"百炼调用失败：{exc}") from exc

        content = completion.choices[0].message.content or ""
        summary, suggestion = _parse_summary_response(content)
        return DiffSummaryResult(
            summary=summary,
            suggestion=suggestion,
            model_name=self._settings.dashscope_model,
        )


def _parse_summary_response(content: str) -> tuple[str, str]:
    lines = [line.strip() for line in content.splitlines() if line.strip()]
    summary = ""
    suggestion = ""

    for line in lines:
        if line.startswith("摘要："):
            summary = line.removeprefix("摘要：").strip()
        elif line.startswith("建议："):
            suggestion = line.removeprefix("建议：").strip()

    if not summary:
        summary = content.strip() or "模型未返回有效摘要，已回退为默认描述。"
    if not suggestion:
        suggestion = "建议结合测试结果和高风险路径继续确认此次变更影响。"

    return summary, suggestion
