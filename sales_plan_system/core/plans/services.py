from .service_results import PlanResult, TaskResult
from .services_legacy import PlanService
from .services_task import TaskService

plan_service = PlanService()
task_service = TaskService()

__all__ = [
    "PlanResult",
    "TaskResult",
    "PlanService",
    "TaskService",
    "plan_service",
    "task_service",
]
