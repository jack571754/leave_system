from dataclasses import dataclass
from typing import Optional

from django.db import transaction
from django.utils import timezone

from core.errors import ApprovalPermissionError, PlanStatusError
from core.plans.models import PlanTask, SalesPlan

from .models import ApprovalRecord, TaskApprovalInstance, TaskApprovalRecord


@dataclass
class ApprovalResult:
    success: bool
    plan: Optional[SalesPlan] = None
    task: Optional[PlanTask] = None
    instance: Optional[TaskApprovalInstance] = None
    message: str = ""
    is_final_approval: bool = False


class ApprovalService:
    def approve_plan(self, plan: SalesPlan, approver, comment: str = "") -> ApprovalResult:
        if not plan.can_approve(approver):
            raise ApprovalPermissionError(plan.pk)
        if plan.status != SalesPlan.Status.PENDING:
            raise PlanStatusError(current_status=plan.get_status_display(), expected_status="审批中")

        with transaction.atomic():
            current_level = plan.get_current_approval_level() or 1
            max_level = plan.get_max_approval_level()
            ApprovalRecord.objects.create(
                plan=plan,
                approver=approver,
                approval_level=current_level,
                action=ApprovalRecord.Action.APPROVE,
                comment=comment,
            )
            is_final = current_level >= max_level
            if is_final:
                plan.status = SalesPlan.Status.APPROVED
                plan.approved_at = timezone.now()
                plan.save(update_fields=["status", "approved_at", "updated_at"])
            else:
                plan.save(update_fields=["updated_at"])

        return ApprovalResult(
            success=True,
            plan=plan,
            message=f"计划 {plan.plan_month} 审批通过",
            is_final_approval=is_final,
        )

    def reject_plan(self, plan: SalesPlan, approver, comment: str = "") -> ApprovalResult:
        if not plan.can_approve(approver):
            raise ApprovalPermissionError(plan.pk)

        with transaction.atomic():
            current_level = plan.get_current_approval_level() or 1
            ApprovalRecord.objects.create(
                plan=plan,
                approver=approver,
                approval_level=current_level,
                action=ApprovalRecord.Action.REJECT,
                comment=comment,
            )
            plan.status = SalesPlan.Status.REJECTED
            plan.save(update_fields=["status", "updated_at"])

        return ApprovalResult(success=True, plan=plan, message=f"计划 {plan.plan_month} 已驳回")

    def _get_step_map(self, task: PlanTask, instance=None):
        if instance and instance.steps_snapshot:
            from core.users.models import User

            user_ids = [entry["approver_id"] for entry in instance.steps_snapshot if entry.get("approver_id")]
            users = {user.pk: user for user in User.objects.filter(pk__in=user_ids)}
            return {
                entry["step"]: {
                    "step": entry["step"],
                    "approver": users.get(entry.get("approver_id")),
                    "label": entry.get("label", ""),
                }
                for entry in instance.steps_snapshot
            }
        return {step["step"]: step for step in task.get_approval_steps()}

    def approve_task(self, task: PlanTask, approver, comment: str = "") -> ApprovalResult:
        if not task.can_approve(approver):
            raise ApprovalPermissionError()
        if task.approval_status != PlanTask.ApprovalStatus.PENDING:
            raise PlanStatusError(current_status=task.get_approval_status_display(), expected_status="审批中")

        instance = task.get_active_approval_instance()
        if not instance or instance.status != TaskApprovalInstance.Status.PENDING:
            raise PlanStatusError(current_status="无可审批实例", expected_status="审批中")

        step_map = self._get_step_map(task, instance)
        current_step = instance.current_step

        with transaction.atomic():
            TaskApprovalRecord.objects.create(
                instance=instance,
                task=task,
                approver=approver,
                approval_level=current_step,
                action=TaskApprovalRecord.Action.APPROVE,
                comment=comment,
            )

            next_step = current_step + 1
            next_step_data = step_map.get(next_step)
            if next_step_data:
                instance.current_step = next_step
                instance.pending_approver = next_step_data["approver"]
                instance.save(update_fields=["current_step", "pending_approver", "updated_at"])
                task.sync_from_instance(instance)
                task.save(update_fields=["status", "approval_status", "current_step", "pending_approver", "round_no", "updated_at"])
                return ApprovalResult(
                    success=True,
                    task=task,
                    instance=instance,
                    message=f"任务 {task.store.name} 已流转到下一审批步骤",
                    is_final_approval=False,
                )

            instance.status = TaskApprovalInstance.Status.APPROVED
            instance.pending_approver = None
            instance.finished_at = timezone.now()
            instance.save(update_fields=["status", "pending_approver", "finished_at", "updated_at"])
            task.sync_from_instance(instance)
            task.save(
                update_fields=["status", "approval_status", "current_step", "pending_approver", "round_no", "approved_at", "updated_at"]
            )

        return ApprovalResult(
            success=True,
            task=task,
            instance=instance,
            message=f"任务 {task.store.name} 审批完成",
            is_final_approval=True,
        )

    def reject_task_to_submitter(self, task: PlanTask, approver, comment: str = "") -> ApprovalResult:
        if not task.can_approve(approver):
            raise ApprovalPermissionError()
        instance = task.get_active_approval_instance()
        if not instance or instance.status != TaskApprovalInstance.Status.PENDING:
            raise PlanStatusError(current_status="无可驳回实例", expected_status="审批中")

        with transaction.atomic():
            TaskApprovalRecord.objects.create(
                instance=instance,
                task=task,
                approver=approver,
                approval_level=instance.current_step,
                action=TaskApprovalRecord.Action.REJECT_TO_SUBMITTER,
                comment=comment,
            )
            instance.status = TaskApprovalInstance.Status.REJECTED
            instance.pending_approver = None
            instance.finished_at = timezone.now()
            instance.save(update_fields=["status", "pending_approver", "finished_at", "updated_at"])

            task.sync_from_instance(instance)
            task.save(update_fields=["status", "approval_status", "current_step", "pending_approver", "round_no", "updated_at"])

        return ApprovalResult(success=True, task=task, instance=instance, message=f"任务 {task.store.name} 已驳回给提报人")

    def reject_task_to_previous(self, task: PlanTask, approver, comment: str = "") -> ApprovalResult:
        if not task.can_approve(approver):
            raise ApprovalPermissionError()
        instance = task.get_active_approval_instance()
        if not instance or instance.status != TaskApprovalInstance.Status.PENDING:
            raise PlanStatusError(current_status="无可驳回实例", expected_status="审批中")

        previous_step = max(instance.current_step - 1, 1)
        previous_step_data = self._get_step_map(task, instance).get(previous_step)
        if not previous_step_data:
            return self.reject_task_to_submitter(task, approver, comment)

        with transaction.atomic():
            TaskApprovalRecord.objects.create(
                instance=instance,
                task=task,
                approver=approver,
                approval_level=instance.current_step,
                action=TaskApprovalRecord.Action.REJECT_TO_PREVIOUS,
                comment=comment,
            )
            instance.current_step = previous_step
            instance.pending_approver = previous_step_data["approver"]
            instance.save(update_fields=["current_step", "pending_approver", "updated_at"])

            task.sync_from_instance(instance)
            task.save(update_fields=["status", "approval_status", "current_step", "pending_approver", "round_no", "updated_at"])

        return ApprovalResult(success=True, task=task, instance=instance, message=f"任务 {task.store.name} 已退回到上一审批步骤")

    def get_pending_approvals(self, user):
        if not user.is_approver():
            return SalesPlan.objects.none(), PlanTask.objects.none()
        return SalesPlan.pending_for_approver(user), PlanTask.pending_for_approver(user)
