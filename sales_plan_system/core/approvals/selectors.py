from core.permissions.services import permissions_service
from .models import TaskApprovalInstance, TaskApprovalRecord


def pending_instances_for_user(user):
    if not permissions_service.has_perm(user, 'approvals.instance.approve') and not getattr(user, 'is_approver', lambda: False)():
        return TaskApprovalInstance.objects.none()

    queryset = TaskApprovalInstance.objects.filter(
        status=TaskApprovalInstance.Status.PENDING,
        task__store_id__in=permissions_service.get_authorized_store_ids(user),
    ).select_related('task', 'task__store', 'task__campaign')

    if permissions_service.has_perm(user, 'approvals.instance.approve'):
        return queryset

    return queryset.filter(pending_approver=user)


def my_request_instances_for_user(user):
    if not permissions_service.has_perm(user, 'approvals.instance.view') and not getattr(user, 'is_authenticated', False):
        return TaskApprovalInstance.objects.none()

    return TaskApprovalInstance.objects.filter(
        submitter=user,
        task__store_id__in=permissions_service.get_authorized_store_ids(user),
    ).select_related('task', 'task__store', 'task__campaign', 'pending_approver')


def approval_history_for_user(user):
    if not permissions_service.has_perm(user, 'approvals.instance.view') and not permissions_service.has_perm(user, 'approvals.instance.approve'):
        return TaskApprovalRecord.objects.none()

    return TaskApprovalRecord.objects.filter(
        approver=user,
        task__store_id__in=permissions_service.get_authorized_store_ids(user),
    ).select_related('task', 'task__store', 'task__campaign', 'instance').order_by('-created_at')
