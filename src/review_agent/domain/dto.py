"""领域层 DTO。"""

from pydantic import BaseModel


class ReviewResumeCommand(BaseModel):
    """恢复评审执行的命令对象。"""

    task_id: str
    comment: str | None = None
