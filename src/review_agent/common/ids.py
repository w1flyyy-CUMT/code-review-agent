"""标识生成工具。"""

from uuid import uuid4


def new_task_id() -> str:
    """生成评审任务编号。"""
    return f"rvw_{uuid4().hex[:12]}"


def new_trace_id() -> str:
    """生成链路追踪编号。"""
    return f"trc_{uuid4().hex[:12]}"
