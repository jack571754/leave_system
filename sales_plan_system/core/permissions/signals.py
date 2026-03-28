from django.db.models.signals import post_migrate
from django.dispatch import receiver

from .models import FrontendPagePermission, Permission, Role, RolePermission
from .registry import (
    DEFAULT_PAGE_CONFIGS,
    DEFAULT_PERMISSION_CONFIGS,
    DEFAULT_ROLE_CONFIGS,
    DEFAULT_ROLE_PERMISSION_MAP,
)
from .services import AccessService


@receiver(post_migrate)
def ensure_default_permissions_setup(sender, **kwargs):
    if sender.name != 'core.permissions':
        return

    # Reset schema cache so the next check re-introspects
    AccessService.reset_schema_cache()

    permissions_by_code = {}
    for config in DEFAULT_PERMISSION_CONFIGS:
        permission, _ = Permission.objects.update_or_create(
            code=config['code'],
            defaults=config,
        )
        permissions_by_code[permission.code] = permission

    roles_by_code = {}
    for config in DEFAULT_ROLE_CONFIGS:
        role, _ = Role.objects.update_or_create(
            code=config['code'],
            defaults=config,
        )
        roles_by_code[role.code] = role

    for role_code, permission_codes in DEFAULT_ROLE_PERMISSION_MAP.items():
        role = roles_by_code.get(role_code)
        if not role:
            continue
        for permission_code in permission_codes:
            permission = permissions_by_code.get(permission_code)
            if not permission:
                continue
            RolePermission.objects.get_or_create(
                role=role,
                permission=permission,
                defaults={'effect': RolePermission.Effect.ALLOW},
            )

    for config in DEFAULT_PAGE_CONFIGS:
        allowed_role_codes = config.get('allowed_roles', [])
        defaults = {key: value for key, value in config.items() if key != 'allowed_roles'}
        defaults['_legacy_allowed_roles'] = allowed_role_codes
        page, _ = FrontendPagePermission.objects.update_or_create(
            page_key=config['page_key'],
            defaults=defaults,
        )
        if allowed_role_codes:
            page.allowed_roles.set(Role.objects.filter(code__in=allowed_role_codes))
        else:
            page.allowed_roles.clear()

