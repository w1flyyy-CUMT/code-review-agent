"""LangGraph 转移条件。"""

from review_agent.agent.state import AgentState


def need_approval(state: AgentState) -> str:
    """根据风险判断是否进入审批。"""
    return "approval_gate" if state.approval_required else "generate_report"
