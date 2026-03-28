# -*- coding: utf-8 -*-
import csv
from collections import OrderedDict
from datetime import datetime
from decimal import Decimal, InvalidOperation

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db.models import Q
from django.http import HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_POST

from core.approvals.models import TaskApprovalRecord
from core.permissions.decorators import page_access_required
from core.permissions.services import permissions_service
from core.products.models import ProductSKU
from core.users.models import OrgUnit, Store
from core.users.selectors import active_org_units, active_stores
from .models import PlanCampaign, PlanTask, PlanTaskItem, SalesPlan
from .selectors import approved_task_count_for_month, campaign_detail_queryset, campaign_task_stats, task_items_for_report, task_queryset_for_user
from .services import task_service
def _can_manage_campaigns(user):
    return permissions_service.can_manage_campaigns(user)


def _task_queryset_for_user(user):
    return task_queryset_for_user(user)


def _build_task_matrix(task, target_months):
    matrix = OrderedDict()
    items = task.items.select_related('sku', 'sku__brand').order_by('sku__sku_code', 'target_month')
    for item in items:
        if item.sku_id not in matrix:
            matrix[item.sku_id] = {
                'sku': item.sku,
                'unit_price': item.unit_price,
                'months': {month: {'sales_qty': 0, 'stock_qty': 0} for month in target_months},
                'row_total_qty': 0,
                'row_total_amount': Decimal('0'),
            }
        row = matrix[item.sku_id]
        row['months'][item.target_month] = {'sales_qty': item.sales_qty, 'stock_qty': item.stock_qty}
        row['row_total_qty'] += item.sales_qty
        row['row_total_amount'] += item.sales_amount
    rows = list(matrix.values())
    for row in rows:
        row['month_cells'] = [
            {
                'month': month,
                'sales_qty': row['months'][month]['sales_qty'],
                'stock_qty': row['months'][month]['stock_qty'],
            }
            for month in target_months
        ]
    return rows


def _build_task_s2_records(task, target_months):
    records = []
    items = task.items.select_related('sku', 'sku__brand').order_by('sku__sku_code', 'target_month')
    for item in items:
        month_index = target_months.index(item.target_month) + 1 if item.target_month in target_months else None
        records.append({
            'item_id': item.pk,
            'sku_id': item.sku_id,
            'sku_code': item.sku.sku_code,
            'sku_name': item.sku.sku_name,
            'brand': item.sku.brand.name if item.sku.brand else '-',
            'target_month': item.target_month,
            'target_label': f'M+{month_index}' if month_index else item.target_month,
            'sales_qty': item.sales_qty,
            'stock_qty': item.stock_qty,
            'unit_price': float(item.unit_price),
            'sales_amount': float(item.sales_amount),
        })
    return records


def _parse_date(value):
    if not value:
        return None
    return datetime.strptime(value, '%Y-%m-%d').date()


@login_required
@page_access_required('dashboard')
def dashboard(request):
    current_month = timezone.now().strftime('%Y-%m')
    my_tasks = _task_queryset_for_user(request.user).filter(campaign__plan_month=current_month)
    return render(request, 'dashboard.html', {
        'current_month': current_month,
        'campaign_count': PlanCampaign.objects.filter(plan_month=current_month).count(),
        'my_task_count': my_tasks.count(),
        'pending_approval_count': PlanTask.pending_for_approver(request.user).count() if request.user.is_approver() else 0,
        'approved_task_count': approved_task_count_for_month(current_month),
    })


@login_required
@page_access_required('plans')
def plan_list(request):
    return redirect('plans:my_tasks')


@login_required
@page_access_required('plans')
def my_plans(request):
    plans = SalesPlan.objects.filter(submitter=request.user).order_by('-plan_month')
    return render(request, 'plans/my_plans.html', {'plans': plans, 'status_choices': SalesPlan.Status.choices})


@login_required
@page_access_required('campaigns')
def campaign_create(request):
    if not _can_manage_campaigns(request.user):
        messages.error(request, 'You do not have permission to create planning campaigns.')
        return redirect('plans:my_tasks')

    org_unit_id = request.GET.get('org_unit', '')
    org_units = active_org_units()
    stores = active_stores(org_unit_id)

    if request.method == 'POST':
        try:
            selected_stores = list(Store.objects.filter(pk__in=request.POST.getlist('stores'), is_active=True))
            campaign = task_service.create_campaign(
                created_by=request.user,
                title=request.POST.get('title', '').strip(),
                plan_month=request.POST.get('plan_month', '').strip(),
                plan_type=request.POST.get('plan_type', PlanCampaign.PlanType.MONTHLY),
                start_date=_parse_date(request.POST.get('start_date')),
                end_date=_parse_date(request.POST.get('end_date')),
                org_unit=OrgUnit.objects.filter(pk=request.POST.get('org_unit')).first() if request.POST.get('org_unit') else None,
                stores=selected_stores,
                remark=request.POST.get('remark', '').strip(),
            )
            messages.success(request, f'Campaign created successfully with {len(selected_stores)} stores.')
            return redirect('plans:campaign_detail', pk=campaign.pk)
        except Exception as exc:
            messages.error(request, getattr(exc, 'message', str(exc)))

    return render(request, 'plans/campaign_form.html', {
        'default_month': timezone.now().strftime('%Y-%m'),
        'default_start_date': timezone.now().date().isoformat(),
        'default_end_date': timezone.now().date().isoformat(),
        'org_units': org_units,
        'stores': stores,
        'selected_org_unit': org_unit_id,
        'plan_type_choices': PlanCampaign.PlanType.choices,
    })


@login_required
@page_access_required('campaigns')
def campaign_detail(request, pk):
    campaign = get_object_or_404(PlanCampaign.objects.select_related('created_by', 'org_unit'), pk=pk)
    if not _can_manage_campaigns(request.user) and campaign.created_by_id != request.user.id:
        messages.error(request, 'You do not have permission to view this campaign.')
        return redirect('plans:my_tasks')
    # Use data-scoped queryset to filter tasks by authorized stores
    _, tasks = campaign_detail_queryset(campaign.pk, user=request.user)
    return render(request, 'plans/campaign_detail.html', {
        'campaign': campaign,
        'tasks': tasks,
        'status_choices': PlanTask.Status.choices,
        'approval_status_choices': PlanTask.ApprovalStatus.choices,
        'task_stats': campaign_task_stats(tasks),
    })


@login_required
@page_access_required('plans')
def my_tasks(request):
    tasks = _task_queryset_for_user(request.user)
    if request.GET.get('status'):
        tasks = tasks.filter(status=request.GET['status'])
    if request.GET.get('approval_status'):
        tasks = tasks.filter(approval_status=request.GET['approval_status'])
    if request.GET.get('month'):
        tasks = tasks.filter(campaign__plan_month=request.GET['month'])
    if request.GET.get('search'):
        search = request.GET['search'].strip()
        tasks = tasks.filter(Q(store__name__icontains=search) | Q(store__code__icontains=search) | Q(campaign__title__icontains=search))
    return render(request, 'plans/task_list.html', {
        'tasks': tasks.order_by('-campaign__plan_month', 'store__code'),
        'status': request.GET.get('status', ''),
        'approval_status': request.GET.get('approval_status', ''),
        'plan_month': request.GET.get('month', ''),
        'search': request.GET.get('search', ''),
        'status_choices': PlanTask.Status.choices,
        'approval_status_choices': PlanTask.ApprovalStatus.choices,
    })


@login_required
@page_access_required('plans')
def task_detail(request, pk):
    task = get_object_or_404(
        PlanTask.objects.select_related('campaign', 'store', 'org_unit', 'assignee', 'pending_approver', 'submitter'),
        pk=pk,
    )
    if not task.can_view(request.user):
        messages.error(request, 'You do not have permission to view this task.')
        return redirect('plans:my_tasks')

    target_months = task.get_target_months()
    available_skus = ProductSKU.objects.filter(status=ProductSKU.Status.ACTIVE).select_related('brand', 'category')
    if request.GET.get('sku_q'):
        term = request.GET['sku_q'].strip()
        available_skus = available_skus.filter(Q(sku_code__icontains=term) | Q(sku_name__icontains=term))
    if request.GET.get('brand'):
        available_skus = available_skus.filter(brand_id=request.GET['brand'])

    preview_bucket = request.session.get(task_service.PREVIEW_SESSION_KEY, {})
    preview_rows = preview_bucket.get(str(task.pk), [])
    import_errors = request.session.get(f'task_import_errors_{task.pk}', [])

    return render(request, 'plans/task_detail.html', {
        'task': task,
        'target_months': target_months,
        'can_edit': task.can_edit(request.user),
        'can_submit': task.can_submit(request.user),
        'can_withdraw': task.can_withdraw(request.user),
        'available_skus': available_skus[:30],
        'sku_q': request.GET.get('sku_q', ''),
        'brand_id': request.GET.get('brand', ''),
        'brands': ProductSKU.objects.filter(status=ProductSKU.Status.ACTIVE).exclude(brand__isnull=True).values_list('brand__id', 'brand__name').distinct(),
        'matrix_rows': _build_task_matrix(task, target_months),
        's2_records': _build_task_s2_records(task, target_months),
        'active_instance': task.get_active_approval_instance(),
        'approval_records': task.approvals.select_related('approver', 'instance').order_by('-created_at'),
        'preview_rows': preview_rows,
        'import_errors': import_errors,
    })


@login_required
@page_access_required('plans')
@require_POST
def add_task_items(request, pk):
    task = get_object_or_404(PlanTask, pk=pk)
    if not task.can_edit(request.user):
        messages.error(request, 'You do not have permission to edit this task.')
        return redirect('plans:task_detail', pk=task.pk)
    try:
        unit_price = Decimal(request.POST.get('unit_price')) if request.POST.get('unit_price') else None
    except InvalidOperation:
        unit_price = None
    try:
        result = task_service.add_task_items(
            task=task,
            sku_ids=[int(value) for value in request.POST.getlist('sku_ids')],
            unit_price=unit_price,
            remark=request.POST.get('remark', '').strip(),
        )
        messages.success(request, result.message)
    except Exception as exc:
        messages.error(request, getattr(exc, 'message', str(exc)))
    return redirect('plans:task_detail', pk=task.pk)


@login_required
@page_access_required('plans')
@require_POST
def save_task_matrix(request, pk):
    task = get_object_or_404(PlanTask, pk=pk)
    if not task.can_edit(request.user):
        messages.error(request, 'You do not have permission to edit this task.')
        return redirect('plans:task_detail', pk=task.pk)
    payload = request.POST.copy()
    payload['sku_ids'] = request.POST.getlist('matrix_sku_ids')
    payload['delete_sku_ids'] = request.POST.getlist('delete_sku_ids')
    try:
        result = task_service.save_task_matrix(task, payload)
        messages.success(request, result.message)
    except Exception as exc:
        messages.error(request, getattr(exc, 'message', str(exc)))
    return redirect('plans:task_detail', pk=task.pk)


@login_required
@page_access_required('plans')
@require_POST
def update_task_cell(request, pk):
    task = get_object_or_404(PlanTask, pk=pk)
    if not task.can_edit(request.user):
        return JsonResponse({'ok': False, 'error': 'Task is not editable.'}, status=403)

    field = (request.POST.get('field') or '').strip()
    sku_id = request.POST.get('sku_id')
    target_month = (request.POST.get('target_month') or '').strip()
    if field not in {'sales_qty', 'stock_qty', 'unit_price'}:
        return JsonResponse({'ok': False, 'error': 'Unsupported field.'}, status=400)
    if not sku_id:
        return JsonResponse({'ok': False, 'error': 'Missing sku_id.'}, status=400)

    if field == 'unit_price':
        try:
            unit_price = Decimal((request.POST.get('value') or '').strip())
        except InvalidOperation:
            return JsonResponse({'ok': False, 'error': 'Unit price must be numeric.'}, status=400)
        if unit_price < 0:
            return JsonResponse({'ok': False, 'error': 'Unit price cannot be negative.'}, status=400)
        row_items = list(task.items.filter(sku_id=sku_id).select_related('sku'))
        for row_item in row_items:
            row_item.unit_price = unit_price
            row_item.save(update_fields=['unit_price', 'updated_at'])
    else:
        try:
            value = int((request.POST.get('value') or '').strip())
        except ValueError:
            return JsonResponse({'ok': False, 'error': 'Value must be an integer.'}, status=400)
        if value < 0:
            return JsonResponse({'ok': False, 'error': 'Value cannot be negative.'}, status=400)
        item = task.items.filter(sku_id=sku_id, target_month=target_month).select_related('sku').first()
        if not item:
            return JsonResponse({'ok': False, 'error': 'Task item not found.'}, status=404)
        setattr(item, field, value)
        item.save(update_fields=[field, 'updated_at'])
        row_items = list(task.items.filter(sku_id=sku_id).select_related('sku'))

    column_items = task.items.filter(target_month=target_month) if target_month else PlanTaskItem.objects.none()
    task_items = task.items.all()
    return JsonResponse({
        'ok': True,
        'field': field,
        'sku_id': int(sku_id),
        'target_month': target_month,
        'unit_price': float(row_items[0].unit_price) if row_items else 0,
        'updated_row': {
            entry.target_month: {
                'item_id': entry.pk,
                'sales_qty': entry.sales_qty,
                'stock_qty': entry.stock_qty,
                'unit_price': float(entry.unit_price),
                'sales_amount': float(entry.sales_amount),
            } for entry in row_items
        },
        'row_total_qty': sum(entry.sales_qty for entry in row_items),
        'row_total_amount': float(sum(entry.sales_amount for entry in row_items)),
        'column_total_qty': sum(entry.sales_qty for entry in column_items) if target_month else None,
        'task_total_qty': sum(entry.sales_qty for entry in task_items),
        'task_total_amount': float(sum(entry.sales_amount for entry in task_items)),
        'saved_at': timezone.localtime().strftime('%Y-%m-%d %H:%M:%S'),
    })


@login_required
@page_access_required('plans')
@require_POST
def submit_task(request, pk):
    task = get_object_or_404(PlanTask, pk=pk)
    try:
        result = task_service.submit_task(task, request.user, comment=request.POST.get('comment', '').strip())
        messages.success(request, result.message)
    except Exception as exc:
        messages.error(request, getattr(exc, 'message', str(exc)))
    return redirect('plans:task_detail', pk=task.pk)


@login_required
@page_access_required('plans')
@require_POST
def withdraw_task(request, pk):
    task = get_object_or_404(PlanTask, pk=pk)
    try:
        result = task_service.withdraw_task(task, request.user, comment=request.POST.get('comment', '').strip())
        messages.success(request, result.message)
    except Exception as exc:
        messages.error(request, getattr(exc, 'message', str(exc)))
    return redirect('plans:task_detail', pk=task.pk)


@login_required
@page_access_required('plans')
@require_POST
def bulk_delete_task_items(request, pk):
    task = get_object_or_404(PlanTask, pk=pk)
    if not task.can_edit(request.user):
        messages.error(request, 'You do not have permission to edit this task.')
        return redirect('plans:task_detail', pk=task.pk)
    try:
        result = task_service.bulk_delete_items(task, [int(value) for value in request.POST.getlist('sku_ids')])
        messages.success(request, result.message)
    except Exception as exc:
        messages.error(request, getattr(exc, 'message', str(exc)))
    return redirect('plans:task_detail', pk=task.pk)


@login_required
@page_access_required('plans')
def task_import_template(request, pk):
    task = get_object_or_404(PlanTask, pk=pk)
    workbook = task_service.build_import_template(task)
    response = HttpResponse(content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
    response['Content-Disposition'] = f'attachment; filename="task_{task.pk}_template.xlsx"'
    workbook.save(response)
    return response


@login_required
@page_access_required('plans')
@require_POST
def task_import_preview(request, pk):
    task = get_object_or_404(PlanTask, pk=pk)
    if not task.can_edit(request.user):
        messages.error(request, 'This task is not editable in its current status.')
        return redirect('plans:task_detail', pk=task.pk)
    uploaded_file = request.FILES.get('file')
    if not uploaded_file:
        messages.error(request, 'Please choose an import file.')
        return redirect('plans:task_detail', pk=task.pk)
    rows, errors = task_service.parse_import_file(task, uploaded_file)
    request.session.setdefault(task_service.PREVIEW_SESSION_KEY, {})
    request.session[task_service.PREVIEW_SESSION_KEY][str(task.pk)] = rows
    request.session[f'task_import_errors_{task.pk}'] = errors
    request.session.modified = True
    messages.success(request, f'Import preview generated for {len(rows)} SKU rows.')
    if errors:
        messages.warning(request, f'There are {len(errors)} row-level validation issues in the preview.')
    return redirect('plans:task_detail', pk=task.pk)


@login_required
@page_access_required('plans')
@require_POST
def task_import_confirm(request, pk):
    task = get_object_or_404(PlanTask, pk=pk)
    preview_rows = request.session.get(task_service.PREVIEW_SESSION_KEY, {}).get(str(task.pk), [])
    if not preview_rows:
        messages.error(request, 'There is no import preview data to confirm.')
        return redirect('plans:task_detail', pk=task.pk)
    try:
        result = task_service.confirm_import_rows(task, preview_rows)
        messages.success(request, result.message)
        request.session[task_service.PREVIEW_SESSION_KEY].pop(str(task.pk), None)
        request.session.pop(f'task_import_errors_{task.pk}', None)
        request.session.modified = True
    except Exception as exc:
        messages.error(request, getattr(exc, 'message', str(exc)))
    return redirect('plans:task_detail', pk=task.pk)


@login_required
@page_access_required('plans')
def export_task(request, pk):
    task = get_object_or_404(PlanTask.objects.select_related('campaign', 'store'), pk=pk)
    if not task.can_view(request.user):
        messages.error(request, 'You do not have permission to export this task.')
        return redirect('plans:my_tasks')
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = f'attachment; filename="task_{task.pk}.csv"'
    writer = csv.writer(response)
    writer.writerow(['Task', 'Store', 'SKU Code', 'SKU Name', 'Target Month', 'Sales Qty', 'Stock Qty', 'Unit Price', 'Sales Amount'])
    for item in task.items.select_related('sku').order_by('sku__sku_code', 'target_month'):
        writer.writerow([task.campaign.title, task.store.name, item.sku.sku_code, item.sku.sku_name, item.target_month, item.sales_qty, item.stock_qty, item.unit_price, item.sales_amount])
    return response


@login_required
@page_access_required('reports')
def plan_report(request):
    if not permissions_service.can_view_report(request.user):
        messages.error(request, 'You do not have permission to view reports.')
        return redirect('plans:my_tasks')

    plan_month = request.GET.get('month', timezone.now().strftime('%Y-%m'))
    group_by = request.GET.get('group_by', 'store')
    approval_status = request.GET.get('approval_status', PlanTask.ApprovalStatus.APPROVED)
    items = task_items_for_report(plan_month, approval_status, request.user)
    records = []
    summary = {}
    for item in items:
        org_unit = item.task.org_unit
        record = {
            'department': org_unit.parent.parent.name if org_unit and org_unit.parent and org_unit.parent.parent else 'Unknown Department',
            'group': org_unit.parent.name if org_unit and org_unit.parent else 'Unknown Group',
            'platform': org_unit.name if org_unit else 'Unknown Platform',
            'store': item.task.store.name,
            'brand': item.sku.brand.name if item.sku.brand else 'Unknown Brand',
            'category': item.sku.category.name if item.sku.category else 'Unknown Category',
            'sku': f'{item.sku.sku_code} / {item.sku.sku_name}',
            'target_month': item.target_month,
            'plan_month': item.task.campaign.plan_month,
            'campaign': item.task.campaign.title,
            'sales_qty': item.sales_qty,
            'stock_qty': item.stock_qty,
            'unit_price': float(item.unit_price),
            'sales_amount': float(item.sales_amount),
        }
        records.append(record)
        key = record.get(group_by, record['store'])
        summary.setdefault(key, {'qty': 0, 'amount': 0, 'count': 0})
        summary[key]['qty'] += item.sales_qty
        summary[key]['amount'] += float(item.sales_amount)
        summary[key]['count'] += 1
    return render(request, 'plans/report.html', {
        'plan_month': plan_month,
        'group_by': group_by,
        'group_by_display': {'department': 'Department', 'group': 'Group', 'platform': 'Platform', 'store': 'Store', 'brand': 'Brand', 'category': 'Category', 'sku': 'SKU'}.get(group_by, 'Store'),
        'summary': summary,
        'total_qty': sum(item['qty'] for item in summary.values()),
        'total_amount': sum(item['amount'] for item in summary.values()),
        'records': records,
        'approval_status': approval_status,
        'approval_status_choices': PlanTask.ApprovalStatus.choices,
    })


@login_required
@page_access_required('reports')
def export_report(request):
    if not permissions_service.can_view_report(request.user):
        messages.error(request, 'You do not have permission to export reports.')
        return redirect('plans:my_tasks')

    plan_month = request.GET.get('month', timezone.now().strftime('%Y-%m'))
    approval_status = request.GET.get('approval_status', PlanTask.ApprovalStatus.APPROVED)
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = f'attachment; filename="sales_plan_{plan_month}.csv"'
    writer = csv.writer(response)
    writer.writerow(['Plan Month', 'Campaign', 'Store', 'SKU Code', 'SKU Name', 'Target Month', 'Sales Qty', 'Stock Qty', 'Unit Price', 'Sales Amount'])
    for item in task_items_for_report(plan_month, approval_status, request.user):
        writer.writerow([item.task.campaign.plan_month, item.task.campaign.title, item.task.store.name, item.sku.sku_code, item.sku.sku_name, item.target_month, item.sales_qty, item.stock_qty, item.unit_price, item.sales_amount])
    return response


@login_required
@page_access_required('dashboard')
def plan_summary_api(request):
    current_month = timezone.now().strftime('%Y-%m')
    my_tasks = _task_queryset_for_user(request.user).filter(campaign__plan_month=current_month)
    return JsonResponse({
        'current_month': current_month,
        'total_campaigns': PlanCampaign.objects.filter(plan_month=current_month).count(),
        'total_tasks': PlanTask.objects.filter(campaign__plan_month=current_month).count(),
        'pending_tasks': PlanTask.objects.filter(campaign__plan_month=current_month, approval_status=PlanTask.ApprovalStatus.PENDING).count(),
        'approved_tasks': PlanTask.objects.filter(campaign__plan_month=current_month, approval_status=PlanTask.ApprovalStatus.APPROVED).count(),
        'my_tasks': my_tasks.count(),
        'my_pending_tasks': my_tasks.filter(approval_status=PlanTask.ApprovalStatus.PENDING).count(),
        'pending_approval': PlanTask.pending_for_approver(request.user).count() if request.user.is_approver() else 0,
    })





