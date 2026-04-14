"""通用异常定义。"""


class ReviewAgentError(Exception):
    """项目基础异常。"""


class TaskNotFoundError(ReviewAgentError):
    """任务不存在。"""


class ApprovalError(ReviewAgentError):
    """审批相关异常。"""


class RepositoryConfigError(ReviewAgentError):
    """仓储配置异常。"""
