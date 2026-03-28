from django.contrib import admin

from unfold.admin import ModelAdmin
from unfold.contrib.filters.admin import RangeNumericFilter
from unfold.decorators import display

from .models import Brand, Category, ProductSKU


@admin.register(Brand)
class BrandAdmin(ModelAdmin):
    list_display = ('name', 'code', 'show_is_active', 'created_at', 'updated_at')
    list_filter = ('is_active',)
    search_fields = ('name', 'code')
    readonly_fields = ('created_at', 'updated_at')
    ordering = ('name',)
    compressed_fields = True
    warn_unsaved_form = True
    list_fullwidth = True

    @display(description="状态", label=True)
    def show_is_active(self, obj):
        return ("启用", "success") if obj.is_active else ("停用", "danger")


@admin.register(Category)
class CategoryAdmin(ModelAdmin):
    list_display = ('name', 'code', 'parent', 'show_is_active', 'updated_at')
    list_filter = ('is_active', 'parent')
    search_fields = ('name', 'code')
    list_select_related = ('parent',)
    readonly_fields = ('created_at', 'updated_at')
    ordering = ('code',)
    autocomplete_fields = ('parent',)
    compressed_fields = True
    warn_unsaved_form = True
    list_fullwidth = True

    @display(description="状态", label=True)
    def show_is_active(self, obj):
        return ("启用", "success") if obj.is_active else ("停用", "danger")


@admin.register(ProductSKU)
class ProductSKUAdmin(ModelAdmin):
    list_display = (
        'sku_code', 'sku_name', 'brand', 'category',
        'show_unit_price', 'show_cost_price', 'show_status', 'created_at',
    )
    list_filter = ('status', 'brand', 'category', ('unit_price', RangeNumericFilter))
    search_fields = ('sku_code', 'sku_name', 'spu_code')
    list_select_related = ('brand', 'category')
    readonly_fields = ('created_at', 'updated_at')
    autocomplete_fields = ('brand', 'category')
    compressed_fields = True
    warn_unsaved_form = True
    list_fullwidth = True
    list_filter_submit = True
    fieldsets = (
        ('基本信息', {'fields': ('sku_code', 'sku_name', 'spu_code', 'brand', 'category')}),
        ('价格信息', {'fields': ('spec_info', 'unit', 'unit_price', 'cost_price')}),
        ('状态', {'fields': ('status', 'remark')}),
        ('时间戳', {'fields': ('created_at', 'updated_at'), 'classes': ('collapse',)}),
    )

    @display(description="销售价", label=True)
    def show_unit_price(self, obj):
        return f"¥{obj.unit_price}"

    @display(description="成本价", label=True)
    def show_cost_price(self, obj):
        return f"¥{obj.cost_price}"

    @display(description="状态", label=True)
    def show_status(self, obj):
        status_map = {
            "active": ("在售", "success"),
            "inactive": ("停售", "danger"),
            "out_of_stock": ("缺货", "warning"),
        }
        return status_map.get(obj.status, (obj.status, "secondary"))
