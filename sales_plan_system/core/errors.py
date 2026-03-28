from typing import Any, Dict, List, Optional


class AppError(Exception):
    """Base application error used by service and middleware layers."""

    def __init__(
        self,
        message: str,
        code: str,
        status_code: int = 500,
        details: Optional[Dict[str, Any]] = None,
    ):
        super().__init__(message)
        self.message = message
        self.code = code
        self.status_code = status_code
        self.details = details or {}
        self.is_operational = True

    def to_dict(self) -> Dict[str, Any]:
        payload = {
            "success": False,
            "error": {
                "code": self.code,
                "message": self.message,
                "status": self.status_code,
            },
        }
        if self.details:
            payload["error"]["details"] = self.details
        return payload

    def __str__(self) -> str:
        return f"[{self.code}] {self.message}"


class BadRequestError(AppError):
    def __init__(self, message: str = "请求参数错误", details: Optional[Dict[str, Any]] = None):
        super().__init__(message, "BAD_REQUEST", 400, details)


class UnauthorizedError(AppError):
    def __init__(self, message: str = "请先登录后再继续"):
        super().__init__(message, "UNAUTHORIZED", 401)


class ForbiddenError(AppError):
    def __init__(self, message: str = "你没有权限执行该操作"):
        super().__init__(message, "FORBIDDEN", 403)


class NotFoundError(AppError):
    def __init__(self, resource: str, identifier: Any = None):
        message = f"{resource}不存在"
        if identifier is not None:
            message = f"{resource}不存在: {identifier}"
        super().__init__(
            message,
            "NOT_FOUND",
            404,
            {
                "resource": resource,
                "identifier": str(identifier) if identifier is not None else None,
            },
        )


class ConflictError(AppError):
    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(message, "CONFLICT", 409, details)


class ValidationError(AppError):
    def __init__(self, errors: List[Dict[str, str]], message: str = "输入校验失败"):
        super().__init__(
            message=message,
            code="VALIDATION_ERROR",
            status_code=422,
            details={"errors": errors},
        )


class RateLimitError(AppError):
    def __init__(self, retry_after: int = 60):
        super().__init__(
            message="请求过于频繁，请稍后再试",
            code="RATE_LIMIT_EXCEEDED",
            status_code=429,
            details={"retry_after": retry_after},
        )


class PlanError(AppError):
    """Base planning-domain error."""


class PlanNotFoundError(NotFoundError):
    def __init__(self, plan_id: int):
        super().__init__("计划", plan_id)


class PlanPermissionError(ForbiddenError):
    def __init__(self, action: str = "当前操作"):
        super().__init__(f"你没有权限执行: {action}")


class PlanStatusError(BadRequestError):
    def __init__(self, current_status: str, expected_status: str = "草稿"):
        super().__init__(
            message=f"当前状态不允许执行该操作，期望状态: {expected_status}，当前状态: {current_status}",
            details={
                "current_status": current_status,
                "expected_status": expected_status,
            },
        )


class ApprovalError(AppError):
    """Base approval-domain error."""


class ApprovalPermissionError(ForbiddenError):
    def __init__(self, plan_id: int = None):
        if plan_id is None:
            super().__init__("你没有该审批操作的权限")
        else:
            super().__init__(f"你没有审批对象 {plan_id} 的权限")


class ApprovalAlreadyCompletedError(ConflictError):
    def __init__(self, plan_id: int):
        super().__init__("该审批已经完成", details={"plan_id": plan_id})


class SKUNotFoundError(NotFoundError):
    def __init__(self, sku_code: str):
        super().__init__("SKU", sku_code)


class InternalError(AppError):
    def __init__(self, message: str = "系统内部错误", details: Optional[Dict[str, Any]] = None):
        super().__init__(message, "INTERNAL_ERROR", 500, details)
        self.is_operational = False


class DatabaseError(AppError):
    def __init__(self, operation: str = "数据库操作"):
        super().__init__(
            message=f"{operation}失败，请稍后重试",
            code="DATABASE_ERROR",
            status_code=500,
            details={"operation": operation},
        )


class ExternalServiceError(AppError):
    def __init__(self, service: str, message: str = None):
        super().__init__(
            message=message or f"外部服务 {service} 调用失败",
            code="EXTERNAL_SERVICE_ERROR",
            status_code=503,
            details={"service": service},
        )
