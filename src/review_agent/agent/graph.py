"""LangGraph 图编排。"""

from typing import Any, cast

from langgraph.graph import END, START, StateGraph

from src.review_agent.agent.nodes import (
    aggregate_findings_node,
    approval_gate_node,
    classify_files_node,
    generate_report_node,
    parse_diff_node,
    resume_after_approval_node,
    route_skills_node,
    run_skills_node,
    score_risk_node,
)
from src.review_agent.agent.state import AgentState
from src.review_agent.agent.transitions import need_approval


def build_review_graph() -> Any:
    """构建首次评审工作流。"""
    graph = StateGraph(AgentState)

    graph.add_node("parse_diff", cast(Any, parse_diff_node))
    graph.add_node("classify_files", cast(Any, classify_files_node))
    graph.add_node("route_skills", cast(Any, route_skills_node))
    graph.add_node("run_skills", cast(Any, run_skills_node))
    graph.add_node("aggregate_findings", cast(Any, aggregate_findings_node))
    graph.add_node("score_risk", cast(Any, score_risk_node))
    graph.add_node("approval_gate", cast(Any, approval_gate_node))
    graph.add_node("generate_report", cast(Any, generate_report_node))

    graph.add_edge(START, "parse_diff")
    graph.add_edge("parse_diff", "classify_files")
    graph.add_edge("classify_files", "route_skills")
    graph.add_edge("route_skills", "run_skills")
    graph.add_edge("run_skills", "aggregate_findings")
    graph.add_edge("aggregate_findings", "score_risk")
    graph.add_conditional_edges(
        "score_risk",
        need_approval,
        {
            "approval_gate": "approval_gate",
            "generate_report": "generate_report",
        },
    )
    graph.add_edge("approval_gate", END)
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
