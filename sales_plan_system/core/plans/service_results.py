from dataclasses import dataclass
from typing import List, Optional

from .models import PlanTask, SalesPlan


@dataclass
class PlanResult:
    success: bool
    plan: Optional[SalesPlan] = None
    message: str = ""
    errors: Optional[List[dict]] = None


@dataclass
class TaskResult:
    success: bool
    task: Optional[PlanTask] = None
    message: str = ""
    errors: Optional[List[dict]] = None
    preview_rows: Optional[List[dict]] = None
