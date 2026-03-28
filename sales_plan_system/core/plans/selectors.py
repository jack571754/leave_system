from core.permissions.services import permissions_service
from core.users.models import User
from .models import PlanCampaign, PlanTask, PlanTaskItem, SalesPlan


def sales_plans_for_user(user):
    """Return SalesPlan queryset scoped to the user's authorized stores."""
    if getattr(user, 'is_superuser', False):
        return SalesPlan.objects.select_related('submitter', 'department').order_by('-plan_month')

    role_codes = permissions_service.get_user_role_codes(user)
    admin_roles = {User.Role.ADMIN, User.Role.MANAGER, User.Role.SUPERVISOR}
    if role_codes & admin_roles:
        store_ids = permissions_service.get_authorized_store_ids(user)
        return SalesPlan.objects.filter(
            submitter__owned_stores__id__in=store_ids
        ).select_related('submitter', 'department').order_by('-plan_month').distinct()

    return SalesPlan.objects.filter(submitter=user).select_related('submitter', 'department').order_by('-plan_month')


def task_queryset_for_user(user):
    if not permissions_service.has_perm(user, 'plans.task.view'):
        return PlanTask.objects.none()

    store_ids = permissions_service.get_authorized_store_ids(user)
    return PlanTask.objects.select_related(
        'campaign', 'store', 'org_unit', 'assignee', 'submitter', 'pending_approver'
    ).filter(store_id__in=store_ids)


def campaign_detail_queryset(campaign_id, user=None):
    campaign = PlanCampaign.objects.select_related('created_by', 'org_unit').get(pk=campaign_id)
    tasks = campaign.tasks.select_related(
        'store', 'org_unit', 'assignee', 'pending_approver', 'submitter'
    ).order_by('store__code')
    if user is not None and getattr(user, 'role', None) != getattr(user.Role, 'ADMIN', None):
        tasks = tasks.filter(store_id__in=permissions_service.get_authorized_store_ids(user))
    return campaign, tasks


def campaign_task_stats(tasks):
    return {
        'draft': tasks.filter(approval_status=PlanTask.ApprovalStatus.NOT_STARTED).count(),
        'pending': tasks.filter(approval_status=PlanTask.ApprovalStatus.PENDING).count(),
        'approved': tasks.filter(approval_status=PlanTask.ApprovalStatus.APPROVED).count(),
        'rejected': tasks.filter(approval_status=PlanTask.ApprovalStatus.REJECTED).count(),
        'withdrawn': tasks.filter(approval_status=PlanTask.ApprovalStatus.WITHDRAWN).count(),
    }


def approved_task_count_for_month(plan_month):
    return PlanTask.objects.filter(
        campaign__plan_month=plan_month,
        approval_status=PlanTask.ApprovalStatus.APPROVED,
    ).count()


def task_items_for_report(plan_month, approval_status, user=None):
    if user is not None and not permissions_service.can_view_report(user):
        return PlanTaskItem.objects.none()

    items = PlanTaskItem.objects.filter(
        task__campaign__plan_month=plan_month,
        task__approval_status=approval_status,
    ).select_related(
        'task',
        'task__campaign',
        'task__store',
        'task__org_unit',
        'task__org_unit__parent',
        'task__org_unit__parent__parent',
        'sku',
        'sku__brand',
        'sku__category',
    )
    if user is not None and getattr(user, 'role', None) != getattr(user.Role, 'ADMIN', None):
        items = items.filter(task__store_id__in=permissions_service.get_authorized_store_ids(user))
    return items
