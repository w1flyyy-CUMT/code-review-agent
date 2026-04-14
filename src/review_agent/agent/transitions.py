"""LangGraph 转移条件。"""

from review_agent.agent.state import AgentState


def route_after_reflection(state: AgentState) -> str:
    """根据反思决策结果选择继续生成报告或先结束等待审批。"""
    return "end" if state.approval_required else "generate_report"
