from decimal import Decimal
from typing import Optional

from core.errors import PlanPermissionError, PlanStatusError, SKUNotFoundError, ValidationError
from core.products.models import ProductSKU

from .models import SalesPlan, SalesPlanItem
from .service_results import PlanResult


class PlanService:
    """Legacy personal-plan service kept for backward compatibility."""

    def create_plan(self, user, plan_month: str, remark: str = "") -> PlanResult:
        if SalesPlan.objects.filter(plan_month=plan_month, submitter=user).exists():
            raise ValidationError([{"field": "plan_month", "message": f"{plan_month} 的计划已存在"}])

        plan = SalesPlan.objects.create(
            plan_month=plan_month,
            submitter=user,
            department=user.department,
            remark=remark,
        )
        return PlanResult(success=True, plan=plan, message=f"{plan_month} 计划已创建")

    def add_plan_item(
        self,
        plan: SalesPlan,
        sku_id: int,
        target_month: str,
        sales_qty: int = 0,
        unit_price: Optional[Decimal] = None,
        stock_qty: int = 0,
        remark: str = "",
    ) -> PlanResult:
        if not plan.can_edit():
            raise PlanStatusError(current_status=plan.get_status_display(), expected_status="草稿")

        target_months = plan.get_target_months()
        if target_month not in target_months:
            raise ValidationError(
                [{"field": "target_month", "message": f"目标月份必须是以下之一: {', '.join(target_months)}"}]
            )

        try:
            sku = ProductSKU.objects.get(pk=sku_id)
        except ProductSKU.DoesNotExist as exc:
            raise SKUNotFoundError(str(sku_id)) from exc

        SalesPlanItem.objects.update_or_create(
            plan=plan,
            sku=sku,
            target_month=target_month,
            defaults={
                "sales_qty": sales_qty,
                "unit_price": unit_price if unit_price is not None else sku.unit_price,
                "stock_qty": stock_qty,
                "remark": remark,
            },
        )
        return PlanResult(success=True, plan=plan, message=f"SKU {sku.sku_code} 已保存")

    def submit_plan(self, plan: SalesPlan, user) -> PlanResult:
        if plan.submitter != user:
            raise PlanPermissionError("提交计划")
        if not plan.can_submit():
            raise ValidationError([{"field": "items", "message": "请先补充计划明细后再提交"}])

        plan.submit()
        return PlanResult(success=True, plan=plan, message=f"{plan.plan_month} 计划已提交")
