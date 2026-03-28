from django.test import TestCase

from core.errors import (
    AppError,
    ApprovalAlreadyCompletedError,
    ApprovalPermissionError,
    BadRequestError,
    ConflictError,
    DatabaseError,
    ExternalServiceError,
    ForbiddenError,
    InternalError,
    NotFoundError,
    PlanNotFoundError,
    PlanPermissionError,
    PlanStatusError,
    RateLimitError,
    SKUNotFoundError,
    UnauthorizedError,
    ValidationError,
)


class AppErrorBaseTests(TestCase):
    def test_app_error_attributes(self):
        err = AppError("test msg", "TEST_CODE", 418)
        self.assertEqual(err.message, "test msg")
        self.assertEqual(err.code, "TEST_CODE")
        self.assertEqual(err.status_code, 418)
        self.assertTrue(err.is_operational)

    def test_app_error_to_dict(self):
        err = AppError("msg", "CODE", 400, {"key": "val"})
        data = err.to_dict()
        self.assertFalse(data["success"])
        self.assertEqual(data["error"]["code"], "CODE")
        self.assertEqual(data["error"]["message"], "msg")
        self.assertEqual(data["error"]["details"]["key"], "val")

    def test_app_error_to_dict_no_details(self):
        err = AppError("msg", "CODE", 400)
        self.assertNotIn("details", err.to_dict()["error"])

    def test_app_error_str(self):
        self.assertEqual(str(AppError("msg", "CODE", 400)), "[CODE] msg")


class HttpErrorTests(TestCase):
    def test_bad_request(self):
        self.assertEqual(BadRequestError().status_code, 400)

    def test_unauthorized(self):
        self.assertEqual(UnauthorizedError().status_code, 401)

    def test_forbidden(self):
        self.assertEqual(ForbiddenError().status_code, 403)

    def test_not_found(self):
        err = NotFoundError("计划", 42)
        self.assertEqual(err.status_code, 404)
        self.assertIn("计划", err.message)
        self.assertIn("42", err.message)

    def test_not_found_without_identifier(self):
        self.assertEqual(NotFoundError("资源").message, "资源不存在")

    def test_conflict(self):
        self.assertEqual(ConflictError("冲突").status_code, 409)

    def test_validation_error(self):
        err = ValidationError([{"field": "name", "message": "必填"}])
        self.assertEqual(err.status_code, 422)
        self.assertEqual(err.details["errors"][0]["field"], "name")

    def test_rate_limit(self):
        err = RateLimitError(120)
        self.assertEqual(err.status_code, 429)
        self.assertEqual(err.details["retry_after"], 120)


class DomainErrorTests(TestCase):
    def test_plan_not_found(self):
        self.assertIn("99", PlanNotFoundError(99).message)

    def test_plan_permission_error(self):
        self.assertIn("编辑", PlanPermissionError("编辑").message)

    def test_plan_status_error(self):
        err = PlanStatusError("approved", "草稿")
        self.assertEqual(err.details["current_status"], "approved")
        self.assertEqual(err.details["expected_status"], "草稿")

    def test_approval_permission_error(self):
        self.assertIn("1", ApprovalPermissionError(1).message)

    def test_approval_already_completed(self):
        self.assertEqual(ApprovalAlreadyCompletedError(5).details["plan_id"], 5)

    def test_sku_not_found(self):
        self.assertIn("SKU123", SKUNotFoundError("SKU123").message)


class ServerErrorTests(TestCase):
    def test_internal_error(self):
        err = InternalError()
        self.assertEqual(err.status_code, 500)
        self.assertFalse(err.is_operational)

    def test_database_error(self):
        self.assertIn("查询", DatabaseError("查询").message)

    def test_external_service_error(self):
        self.assertIn("Feishu", ExternalServiceError("Feishu").message)

    def test_external_service_custom_message(self):
        err = ExternalServiceError("Feishu", message="飞书调用失败")
        self.assertEqual(err.message, "飞书调用失败")
