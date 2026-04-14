"""LangGraph 图编排。"""

from typing import Any, cast

from langgraph.graph import END, START, StateGraph

from review_agent.agent.nodes import (
    execute_review_node,
    generate_report_node,
    parse_input_node,
    plan_and_route_node,
    reflect_and_decide_node,
    resume_after_approval_node,
)
from review_agent.agent.state import AgentState
from review_agent.agent.transitions import route_after_reflection


def build_review_graph() -> Any:
    """构建首次评审工作流。"""
    graph = StateGraph(AgentState)

    graph.add_node("parse_input", cast(Any, parse_input_node))
    graph.add_node("plan_and_route", cast(Any, plan_and_route_node))
    graph.add_node("execute_review", cast(Any, execute_review_node))
    graph.add_node("reflect_and_decide", cast(Any, reflect_and_decide_node))
    graph.add_node("generate_report", cast(Any, generate_report_node))

    graph.add_edge(START, "parse_input")
    graph.add_edge("parse_input", "plan_and_route")
    graph.add_edge("plan_and_route", "execute_review")
    graph.add_edge("execute_review", "reflect_and_decide")
    graph.add_conditional_edges(
        "reflect_and_decide",
        route_after_reflection,
        {
            "generate_report": "generate_report",
            "end": END,
        },
    )
    graph.add_edge("generate_report", END)

    return graph.compile()


def build_resume_graph() -> Any:
    """构建审批后的恢复执行图。"""
    graph = StateGraph(AgentState)

    graph.add_node("resume_after_approval", cast(Any, resume_after_approval_node))
    graph.add_node("generate_report", cast(Any, generate_report_node))

    graph.add_edge(START, "resume_after_approval")
    graph.add_edge("resume_after_approval", "generate_report")
    graph.add_edge("generate_report", END)

    return graph.compile()
