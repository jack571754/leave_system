from django.contrib import admin

from unfold.admin import ModelAdmin, TabularInline
from unfold.contrib.filters.admin import RangeNumericFilter, RangeDateFilter
from unfold.decorators import display

from .models import PlanCampaign, PlanTask, PlanTaskItem, SalesPlan, SalesPlanItem


class SalesPlanItemInline(TabularInline):
    model = SalesPlanItem
    extra = 0
    autocomplete_fields = ('sku',)
    tab = True


class PlanTaskItemInline(TabularInline):
    model = PlanTaskItem
    extra = 0
    autocomplete_fields = ('sku',)
    tab = True


@admin.register(SalesPlan)
class SalesPlanAdmin(ModelAdmin):
    list_display = ('plan_month', 'submitter', 'department', 'show_status', 'submitted_at', 'approved_at')
    list_filter = ('status', 'plan_month', 'department', ('submitted_at', RangeDateFilter))
    search_fields = ('plan_month', 'submitter__username')
    inlines = [SalesPlanItemInline]
    readonly_fields = ('created_at', 'updated_at', 'submitted_at', 'approved_at')
    autocomplete_fields = ('submitter', 'department')
    compressed_fields = True
    warn_unsaved_form = True
    list_fullwidth = True

    @display(description="状态", label=True)
    def show_status(self, obj):
        status_map = {
            "draft": ("草稿", "secondary"),
            "pending": ("审批中", "info"),
            "approved": ("已批准", "success"),
            "rejected": ("已退回", "danger"),
        }
        return status_map.get(obj.status, (obj.status, "secondary"))


@admin.register(SalesPlanItem)
class SalesPlanItemAdmin(ModelAdmin):
    list_display = ('plan', 'sku', 'target_month', 'sales_qty', 'show_unit_price', 'stock_qty')
    list_filter = ('target_month', 'sku__brand', 'sku__category', ('sales_qty', RangeNumericFilter))
    autocomplete_fields = ('plan', 'sku')
    compressed_fields = True
    warn_unsaved_form = True
    list_fullwidth = True

    @display(description="单价", label=True)
    def show_unit_price(self, obj):
        return f"¥{obj.unit_price}"


@admin.register(PlanCampaign)
class PlanCampaignAdmin(ModelAdmin):
    list_display = ('title', 'plan_month', 'show_plan_type', 'start_date', 'end_date', 'org_unit', 'show_status', 'created_by')
    list_filter = ('status', 'plan_type', 'plan_month', 'org_unit', ('published_at', RangeDateFilter))
    search_fields = ('title', 'plan_month', 'created_by__username')
    readonly_fields = ('created_at', 'updated_at', 'published_at', 'closed_at')
    autocomplete_fields = ('org_unit', 'created_by')
    compressed_fields = True
    warn_unsaved_form = True
    list_fullwidth = True

    @display(description="计划类型", label=True)
    def show_plan_type(self, obj):
        type_map = {
            "monthly": ("月度", "info"),
            "ad_hoc": ("临时", "warning"),
            "new_product": ("新品", "success"),
        }
        return type_map.get(obj.plan_type, (obj.plan_type, "secondary"))

    @display(description="状态", label=True)
    def show_status(self, obj):
        status_map = {
            "draft": ("草稿", "secondary"),
            "active": ("进行中", "info"),
            "closed": ("已结束", "warning"),
            "archived": ("已归档", "secondary"),
        }
        return status_map.get(obj.status, (obj.status, "secondary"))


@admin.register(PlanTask)
class PlanTaskAdmin(ModelAdmin):
    list_display = ('campaign', 'store', 'assignee', 'show_status', 'show_approval_status', 'current_step', 'pending_approver', 'last_submitted_at')
    list_filter = ('status', 'approval_status', 'campaign__plan_month', 'org_unit', ('last_submitted_at', RangeDateFilter))
    search_fields = ('campaign__title', 'store__name', 'store__code', 'assignee__username')
    readonly_fields = ('created_at', 'updated_at', 'submitted_at', 'last_submitted_at', 'approved_at', 'last_withdrawn_at')
    inlines = [PlanTaskItemInline]
    autocomplete_fields = ('campaign', 'store', 'org_unit', 'assignee', 'submitter', 'pending_approver')
    compressed_fields = True
    warn_unsaved_form = True
    list_fullwidth = True

    @display(description="任务状态", label=True)
    def show_status(self, obj):
        status_map = {
            "draft": ("待填报", "secondary"),
            "submitted": ("待审批", "info"),
            "approved": ("已通过", "success"),
            "rejected": ("已驳回", "danger"),
            "withdrawn": ("已撤回", "warning"),
        }
        return status_map.get(obj.status, (obj.status, "secondary"))

    @display(description="审批状态", label=True)
    def show_approval_status(self, obj):
        status_map = {
            "not_started": ("未开始", "secondary"),
            "pending": ("审批中", "info"),
            "approved": ("已通过", "success"),
            "rejected": ("已驳回", "danger"),
            "withdrawn": ("已撤回", "warning"),
        }
        return status_map.get(obj.approval_status, (obj.approval_status, "secondary"))


@admin.register(PlanTaskItem)
class PlanTaskItemAdmin(ModelAdmin):
    list_display = ('task', 'sku', 'target_month', 'sales_qty', 'show_unit_price', 'stock_qty')
    list_filter = ('target_month', 'sku__brand', 'sku__category', ('sales_qty', RangeNumericFilter))
    autocomplete_fields = ('task', 'sku')
    compressed_fields = True
    warn_unsaved_form = True
    list_fullwidth = True

    @display(description="单价", label=True)
    def show_unit_price(self, obj):
        return f"¥{obj.unit_price}"
