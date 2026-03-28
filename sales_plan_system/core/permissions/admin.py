from django.contrib import admin

from unfold.admin import ModelAdmin
from unfold.decorators import display

from .models import (
    DataPermissionConfig,  # Deprecated — kept for admin compat
    DataScopeRule,
    FrontendPagePermission,
    Permission,
    Role,
    RolePermission,
    UserRoleAssignment,
)


@admin.register(Role)
class RoleAdmin(ModelAdmin):
    list_display = ('code', 'name', 'role_type', 'priority', 'is_system', 'show_is_active')
    list_filter = ('role_type', 'is_system', 'is_active')
    search_fields = ('code', 'name')
    readonly_fields = ('created_at', 'updated_at')
    compressed_fields = True
    warn_unsaved_form = True
    list_fullwidth = True

    @display(description='状态', label=True)
    def show_is_active(self, obj):
        return ('启用', 'success') if obj.is_active else ('停用', 'danger')


@admin.register(Permission)
class PermissionAdmin(ModelAdmin):
    list_display = ('code', 'module', 'resource', 'action', 'show_is_active')
    list_filter = ('module', 'resource', 'action', 'is_active')
    search_fields = ('code', 'description')
    readonly_fields = ('created_at', 'updated_at')
    compressed_fields = True
    warn_unsaved_form = True
    list_fullwidth = True

    @display(description='状态', label=True)
    def show_is_active(self, obj):
        return ('启用', 'success') if obj.is_active else ('停用', 'danger')


@admin.register(RolePermission)
class RolePermissionAdmin(ModelAdmin):
    list_display = ('role', 'permission', 'effect', 'updated_at')
    list_filter = ('effect', 'role')
    search_fields = ('role__code', 'permission__code')
    autocomplete_fields = ('role', 'permission')
    readonly_fields = ('created_at', 'updated_at')
    compressed_fields = True
    warn_unsaved_form = True
    list_fullwidth = True


@admin.register(UserRoleAssignment)
class UserRoleAssignmentAdmin(ModelAdmin):
    list_display = ('user', 'role', 'scope_type', 'org_unit', 'store', 'show_is_active')
    list_filter = ('scope_type', 'is_active', 'role')
    search_fields = ('user__username', 'role__code', 'org_unit__name', 'store__name')
    autocomplete_fields = ('user', 'role', 'org_unit', 'store')
    readonly_fields = ('created_at', 'updated_at')
    compressed_fields = True
    warn_unsaved_form = True
    list_fullwidth = True

    @display(description='状态', label=True)
    def show_is_active(self, obj):
        return ('启用', 'success') if obj.is_active else ('停用', 'danger')


@admin.register(DataPermissionConfig)
class DataPermissionConfigAdmin(ModelAdmin):
    list_display = ('name', 'show_subject_type', 'show_scope_type', 'show_is_active', 'updated_at')
    list_filter = ('subject_type', 'scope_type', 'is_active')
    search_fields = ('name',)
    filter_horizontal = ('target_users', 'org_units', 'stores')
    compressed_fields = True
    warn_unsaved_form = True
    list_fullwidth = True

    @display(description='主体类型', label=True)
    def show_subject_type(self, obj):
        return (obj.get_subject_type_display(), 'info')

    @display(description='范围', label=True)
    def show_scope_type(self, obj):
        return (obj.get_scope_type_display(), 'warning')

    @display(description='状态', label=True)
    def show_is_active(self, obj):
        return ('启用', 'success') if obj.is_active else ('停用', 'danger')


@admin.register(DataScopeRule)
class DataScopeRuleAdmin(ModelAdmin):
    list_display = ('name', 'resource_code', 'subject_type', 'scope_type', 'show_is_active', 'updated_at')
    list_filter = ('resource_code', 'subject_type', 'scope_type', 'is_active')
    search_fields = ('name', 'resource_code')
    filter_horizontal = ('target_users', 'target_roles', 'org_units', 'stores')
    compressed_fields = True
    warn_unsaved_form = True
    list_fullwidth = True

    @display(description='状态', label=True)
    def show_is_active(self, obj):
        return ('启用', 'success') if obj.is_active else ('停用', 'danger')


@admin.register(FrontendPagePermission)
class FrontendPagePermissionAdmin(ModelAdmin):
    list_display = ('page_key', 'label', 'url_name', 'permission_code', 'show_in_menu', 'allow_all_users', 'show_is_active')
    list_filter = ('show_in_menu', 'allow_all_users', 'is_active')
    search_fields = ('page_key', 'label', 'url_name', 'permission_code')
    filter_horizontal = ('allowed_roles',)
    compressed_fields = True
    warn_unsaved_form = True
    list_fullwidth = True

    @display(description='菜单', label=True, boolean=True)
    def show_in_menu(self, obj):
        return obj.show_in_menu

    @display(description='公开', label=True, boolean=True)
    def allow_all_users(self, obj):
        return obj.allow_all_users

    @display(description='状态', label=True)
    def show_is_active(self, obj):
        return ('启用', 'success') if obj.is_active else ('停用', 'danger')
