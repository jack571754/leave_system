from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_GET, require_POST

from core.permissions.decorators import page_access_required
from core.permissions.services import permissions_service
from core.plans.models import PlanTask, SalesPlan
from .models import TaskApprovalInstance
from .selectors import approval_history_for_user, my_request_instances_for_user, pending_instances_for_user
from .services import approval_service


@login_required
@page_access_required('approvals')
def approval_center(request):
    pending_instances = pending_instances_for_user(request.user)[:5]
    my_requests = my_request_instances_for_user(request.user)[:5]
    return render(request, 'approvals/center.html', {
        'pending_instances': pending_instances,
        'pending_count': pending_instances_for_user(request.user).count(),
        'my_pending_requests': my_request_instances_for_user(request.user).count(),
        'my_requests_preview': my_requests,
    })


@login_required
@page_access_required('approvals')
def pending_approvals(request):
    if not permissions_service.has_perm(request.user, 'approvals.instance.approve') and not request.user.is_approver():
        messages.warning(request, 'You do not have approval access.')
        return redirect('dashboard')

    instances = pending_instances_for_user(request.user).select_related('submitter', 'pending_approver')
    if request.GET.get('month'):
        instances = instances.filter(task__campaign__plan_month=request.GET['month'])
    return render(request, 'approvals/pending.html', {
        'instances': instances.order_by('-created_at'),
        'current_month': request.GET.get('month', ''),
    })


@login_required
@page_access_required('approvals')
def my_requests(request):
    return render(request, 'approvals/my_requests.html', {
        'instances': my_request_instances_for_user(request.user).order_by('-created_at'),
    })


@login_required
@page_access_required('approvals')
def approval_history(request):
    return render(request, 'approvals/history.html', {
        'task_records': approval_history_for_user(request.user),
    })


@login_required
@page_access_required('approvals')
@require_GET
def approval_instance_detail(request, instance_id):
    instance = get_object_or_404(
        TaskApprovalInstance.objects.select_related(
            'task', 'task__store', 'task__campaign', 'submitter', 'pending_approver'
        ),
        pk=instance_id,
    )
    if not permissions_service.can_view_approval_instance(request.user, instance):
        messages.error(request, 'You do not have access to this approval instance.')
        return redirect('approvals:center')
    records = instance.records.select_related('approver').order_by('created_at')
    return render(request, 'approvals/instance_detail.html', {'instance': instance, 'records': records})


@login_required
@page_access_required('approvals')
@require_POST
def approve_plan(request, plan_id):
    plan = get_object_or_404(SalesPlan, pk=plan_id)
    try:
        result = approval_service.approve_plan(plan=plan, approver=request.user, comment=request.POST.get('comment', ''))
        messages.success(request, result.message)
    except Exception as exc:
        messages.error(request, getattr(exc, 'message', str(exc)))
    return redirect('approvals:pending')


@login_required
@page_access_required('approvals')
@require_POST
def reject_plan(request, plan_id):
    plan = get_object_or_404(SalesPlan, pk=plan_id)
    try:
        result = approval_service.reject_plan(plan=plan, approver=request.user, comment=request.POST.get('comment', ''))
        messages.success(request, result.message)
    except Exception as exc:
        messages.error(request, getattr(exc, 'message', str(exc)))
    return redirect('approvals:pending')


@login_required
@page_access_required('approvals')
@require_POST
def approve_task(request, task_id):
    task = get_object_or_404(PlanTask.objects.select_related('campaign', 'store'), pk=task_id)
    try:
        result = approval_service.approve_task(task=task, approver=request.user, comment=request.POST.get('comment', ''))
        messages.success(request, result.message)
    except Exception as exc:
        messages.error(request, getattr(exc, 'message', str(exc)))
    return redirect('approvals:pending')


@login_required
@page_access_required('approvals')
@require_POST
def reject_task(request, task_id):
    task = get_object_or_404(PlanTask.objects.select_related('campaign', 'store'), pk=task_id)
    action = request.POST.get('action', 'reject_to_submitter')
    try:
        if action == 'reject_to_previous':
            result = approval_service.reject_task_to_previous(
                task=task, approver=request.user, comment=request.POST.get('comment', '')
            )
        else:
            result = approval_service.reject_task_to_submitter(
                task=task, approver=request.user, comment=request.POST.get('comment', '')
            )
        messages.success(request, result.message)
    except Exception as exc:
        messages.error(request, getattr(exc, 'message', str(exc)))
    return redirect('approvals:pending')


@login_required
@page_access_required('approvals')
@require_POST
def batch_approve(request):
    ids = [int(value) for value in request.POST.getlist('task_ids') if value]
    summary = {'success': 0, 'failed': 0}
    for task in PlanTask.objects.filter(pk__in=ids):
        try:
            approval_service.approve_task(task=task, approver=request.user, comment=request.POST.get('comment', ''))
            summary['success'] += 1
        except Exception:
            summary['failed'] += 1
    if summary['success']:
        messages.success(request, f'Approved {summary["success"]} task(s).')
    if summary['failed']:
        messages.warning(request, f'Failed to approve {summary["failed"]} task(s).')
    return redirect('approvals:pending')


@login_required
@page_access_required('approvals')
@require_POST
def batch_reject(request):
    ids = [int(value) for value in request.POST.getlist('task_ids') if value]
    summary = {'success': 0, 'failed': 0}
    action = request.POST.get('action', 'reject_to_submitter')
    for task in PlanTask.objects.filter(pk__in=ids):
        try:
            if action == 'reject_to_previous':
                approval_service.reject_task_to_previous(
                    task=task, approver=request.user, comment=request.POST.get('comment', '')
                )
            else:
                approval_service.reject_task_to_submitter(
                    task=task, approver=request.user, comment=request.POST.get('comment', '')
                )
            summary['success'] += 1
        except Exception:
            summary['failed'] += 1
    if summary['success']:
        messages.success(request, f'Rejected {summary["success"]} task(s).')
    if summary['failed']:
        messages.warning(request, f'Failed to reject {summary["failed"]} task(s).')
    return redirect('approvals:pending')


@login_required
@page_access_required('approvals')
def pending_count_api(request):
    count = pending_instances_for_user(request.user).count() if (
        permissions_service.has_perm(request.user, 'approvals.instance.approve') or request.user.is_approver()
    ) else 0
    return JsonResponse({'count': count})
