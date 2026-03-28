from django.contrib import admin

from unfold.admin import ModelAdmin
from unfold.contrib.filters.admin import RangeDateFilter
from unfold.decorators import display

from .models import ApprovalFlow, ApprovalRecord, TaskApprovalInstance, TaskApprovalRecord


@admin.register(ApprovalRecord)
class ApprovalRecordAdmin(ModelAdmin):
    list_display = ('plan', 'approver', 'approval_level', 'show_action', 'created_at')
    list_filter = ('action', 'approval_level', ('created_at', RangeDateFilter))
    search_fields = ('plan__plan_month', 'approver__username')
    readonly_fields = ('created_at',)
    list_select_related = ('plan', 'approver')
    autocomplete_fields = ('plan', 'approver')
    compressed_fields = True
    warn_unsaved_form = True
    list_fullwidth = True

    @display(description="审批动作", label=True)
    def show_action(self, obj):
        return ("通过", "success") if obj.action == "approve" else ("退回", "danger")


@admin.register(TaskApprovalInstance)
class TaskApprovalInstanceAdmin(ModelAdmin):
    list_display = ('task', 'round_no', 'show_status', 'current_step', 'submitter', 'pending_approver', 'started_at')
    list_filter = ('status', 'round_no', ('started_at', RangeDateFilter))
    search_fields = ('task__store__name', 'task__campaign__title', 'submitter__username', 'pending_approver__username')
    readonly_fields = ('started_at', 'finished_at', 'withdrawn_at', 'created_at', 'updated_at')
    list_select_related = ('task', 'submitter', 'pending_approver')
    autocomplete_fields = ('task', 'submitter', 'pending_approver')
    compressed_fields = True
    warn_unsaved_form = True
    list_fullwidth = True

    @display(description="状态", label=True)
    def show_status(self, obj):
        status_map = {
            "pending": ("审批中", "info"),
            "approved": ("已通过", "success"),
            "rejected": ("已驳回", "danger"),
            "withdrawn": ("已撤回", "warning"),
        }
        return status_map.get(obj.status, (obj.status, "secondary"))


@admin.register(TaskApprovalRecord)
class TaskApprovalRecordAdmin(ModelAdmin):
    list_display = ('task', 'instance', 'approver', 'approval_level', 'show_action', 'created_at')
    list_filter = ('action', 'approval_level', ('created_at', RangeDateFilter))
    search_fields = ('task__store__name', 'task__campaign__title', 'approver__username')
    readonly_fields = ('created_at',)
    list_select_related = ('task', 'instance', 'approver')
    autocomplete_fields = ('instance', 'task', 'approver')
    compressed_fields = True
    warn_unsaved_form = True
    list_fullwidth = True

    @display(description="审批动作", label=True)
    def show_action(self, obj):
        action_map = {
            "approve": ("通过", "success"),
            "reject_to_previous": ("驳回上一步", "warning"),
            "reject_to_submitter": ("驳回提交人", "danger"),
            "withdraw": ("撤回", "secondary"),
            "resubmit": ("重新提交", "info"),
        }
        return action_map.get(obj.action, (obj.action, "secondary"))


@admin.register(ApprovalFlow)
class ApprovalFlowAdmin(ModelAdmin):
    list_display = ('name', 'show_flow_type', 'show_scope_type', 'department', 'org_unit', 'store', 'show_is_active', 'updated_at')
    list_filter = ('flow_type', 'scope_type', 'is_active')
    search_fields = ('name',)
    list_select_related = ('department', 'org_unit', 'store')
    autocomplete_fields = ('department', 'org_unit', 'store')
    readonly_fields = ('created_at', 'updated_at')
    compressed_fields = True
    warn_unsaved_form = True
    list_fullwidth = True

    @display(description="流程类型", label=True)
    def show_flow_type(self, obj):
        type_map = {
            "sales_plan": ("销售计划", "info"),
            "plan_task": ("任务审批", "warning"),
        }
        return type_map.get(obj.flow_type, (obj.flow_type, "secondary"))

    @display(description="适用范围", label=True)
    def show_scope_type(self, obj):
        scope_map = {
            "global": ("全局", "secondary"),
            "department": ("部门", "info"),
            "org_unit": ("组织", "warning"),
            "store": ("店铺", "success"),
        }
        return scope_map.get(obj.scope_type, (obj.scope_type, "secondary"))

    @display(description="状态", label=True)
    def show_is_active(self, obj):
        return ("启用", "success") if obj.is_active else ("停用", "danger")
