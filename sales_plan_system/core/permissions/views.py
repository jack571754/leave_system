from django.contrib.auth.decorators import login_required
from django.db.models import Count
from django.shortcuts import render

from core.users.models import User

from .decorators import page_access_required
from .models import (
    DataScopeRule,
    FrontendPagePermission,
    Permission,
    Role,
    UserRoleAssignment,
)
from .registry import DEFAULT_PAGE_CONFIGS
from .services import permissions_service


@login_required
@page_access_required('permissions')
def permission_center(request):
    rbac_ready = permissions_service.is_rbac_ready()

    if rbac_ready:
        roles = Role.objects.filter(is_active=True).annotate(
            permission_total=Count('role_permissions', distinct=True),
            assignment_total=Count('user_assignments', distinct=True),
        ).order_by('priority', 'code')
        assignments = UserRoleAssignment.objects.filter(is_active=True).select_related(
            'user', 'role', 'org_unit', 'store'
        ).order_by('-updated_at', 'user__username')[:10]
        page_configs = FrontendPagePermission.objects.filter(is_active=True).order_by('menu_order', 'page_key')
        permission_catalog = Permission.objects.filter(is_active=True).order_by('module', 'resource', 'action')[:12]
        data_scope_rules = DataScopeRule.objects.filter(is_active=True).order_by('resource_code', 'name')[:10]
        legacy_data_configs = []
        role_count = Role.objects.filter(is_active=True).count()
        permission_count = Permission.objects.filter(is_active=True).count()
        assignment_count = UserRoleAssignment.objects.filter(is_active=True).count()
    else:
        roles = []
        assignments = []
        page_configs = [type('FallbackPage', (), config)() for config in DEFAULT_PAGE_CONFIGS]
        permission_catalog = []
        data_scope_rules = []
        legacy_data_configs = []
        role_count = 0
        permission_count = 0
        assignment_count = 0

    return render(request, 'permissions/center.html', {
        'rbac_ready': rbac_ready,
        'users_count': User.objects.filter(is_active=True).count(),
        'role_count': role_count,
        'permission_count': permission_count,
        'assignment_count': assignment_count,
        'authorized_store_count': len(permissions_service.get_authorized_store_ids(request.user)),
        'roles': roles,
        'assignments': assignments,
        'page_configs': page_configs,
        'permission_catalog': permission_catalog,
        'data_scope_rules': data_scope_rules,
        'legacy_data_configs': legacy_data_configs,
    })


@login_required
def no_access(request):
    return render(request, 'permissions/no_access.html', status=403)
