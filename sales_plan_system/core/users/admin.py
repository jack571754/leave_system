from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin

from unfold.admin import ModelAdmin
from unfold.decorators import display

from .models import Department, OrgUnit, Store, StoreMembership, User


@admin.register(Department)
class DepartmentAdmin(ModelAdmin):
    list_display = ('name', 'code', 'parent', 'manager', 'show_is_active', 'updated_at')
    list_filter = ('is_active',)
    search_fields = ('name', 'code')
    list_select_related = ('parent', 'manager')
    readonly_fields = ('created_at', 'updated_at')
    ordering = ('code',)
    compressed_fields = True
    warn_unsaved_form = True
    list_fullwidth = True

    @display(description="状态", label=True)
    def show_is_active(self, obj):
        return ("启用", "success") if obj.is_active else ("停用", "danger")


@admin.register(OrgUnit)
class OrgUnitAdmin(ModelAdmin):
    list_display = ('name', 'code', 'show_unit_type', 'parent', 'manager', 'show_is_active', 'updated_at')
    list_filter = ('unit_type', 'is_active')
    search_fields = ('name', 'code')
    list_select_related = ('parent', 'manager')
    readonly_fields = ('created_at', 'updated_at')
    ordering = ('unit_type', 'code')
    compressed_fields = True
    warn_unsaved_form = True
    list_fullwidth = True

    @display(description="组织类型", label=True)
    def show_unit_type(self, obj):
        type_map = {
            "department": ("部门", "info"),
            "group": ("组", "warning"),
            "platform": ("平台", "success"),
        }
        return type_map.get(obj.unit_type, (obj.unit_type, "secondary"))

    @display(description="状态", label=True)
    def show_is_active(self, obj):
        return ("启用", "success") if obj.is_active else ("停用", "danger")


@admin.register(Store)
class StoreAdmin(ModelAdmin):
    list_display = ('name', 'code', 'org_unit', 'owner', 'show_is_active', 'updated_at')
    list_filter = ('is_active', 'org_unit')
    search_fields = ('name', 'code', 'owner__username')
    list_select_related = ('org_unit', 'owner')
    readonly_fields = ('created_at', 'updated_at')
    ordering = ('code',)
    autocomplete_fields = ('org_unit', 'owner')
    compressed_fields = True
    warn_unsaved_form = True
    list_fullwidth = True

    @display(description="状态", label=True)
    def show_is_active(self, obj):
        return ("启用", "success") if obj.is_active else ("停用", "danger")


@admin.register(StoreMembership)
class StoreMembershipAdmin(ModelAdmin):
    list_display = ('store', 'user', 'show_role', 'show_is_active', 'updated_at')
    list_filter = ('role', 'is_active')
    search_fields = ('store__name', 'store__code', 'user__username')
    list_select_related = ('store', 'user')
    readonly_fields = ('created_at', 'updated_at')
    autocomplete_fields = ('store', 'user')
    compressed_fields = True
    warn_unsaved_form = True
    list_fullwidth = True

    @display(description="角色", label=True)
    def show_role(self, obj):
        role_map = {
            "owner": ("负责人", "success"),
            "editor": ("编辑", "info"),
            "viewer": ("查看", "secondary"),
        }
        return role_map.get(obj.role, (obj.role, "secondary"))

    @display(description="状态", label=True)
    def show_is_active(self, obj):
        return ("启用", "success") if obj.is_active else ("停用", "danger")


@admin.register(User)
class CustomUserAdmin(BaseUserAdmin, ModelAdmin):
    list_display = ('username', 'email', 'department', 'org_unit', 'show_role', 'show_is_staff', 'show_is_active')
    list_filter = ('role', 'department', 'org_unit', 'is_active', 'is_staff', 'is_superuser')
    search_fields = ('username', 'first_name', 'last_name', 'email', 'phone')
    list_select_related = ('department', 'org_unit', 'manager')
    readonly_fields = ('last_login', 'date_joined')
    autocomplete_fields = ('department', 'org_unit', 'manager')
    compressed_fields = True
    warn_unsaved_form = True
    list_fullwidth = True
    fieldsets = (
        (None, {'fields': ('username', 'password')}),
        ('个人信息', {'fields': ('first_name', 'last_name', 'email', 'phone', 'avatar')}),
        ('组织信息', {'fields': ('department', 'org_unit', 'role', 'manager')}),
        ('权限', {'fields': ('is_active', 'is_staff', 'is_superuser', 'groups', 'user_permissions')}),
        ('重要日期', {'fields': ('last_login', 'date_joined')}),
    )
    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('username', 'password1', 'password2', 'email', 'role', 'department', 'org_unit', 'manager'),
        }),
    )

    @display(description="角色", label=True)
    def show_role(self, obj):
        role_map = {
            "admin": ("管理员", "danger"),
            "manager": ("经理", "warning"),
            "supervisor": ("主管", "info"),
            "staff": ("员工", "secondary"),
        }
        return role_map.get(obj.role, (obj.role, "secondary"))

    @display(description="员工", label=True, boolean=True)
    def show_is_staff(self, obj):
        return obj.is_staff

    @display(description="状态", label=True)
    def show_is_active(self, obj):
        return ("活跃", "success") if obj.is_active else ("停用", "danger")
