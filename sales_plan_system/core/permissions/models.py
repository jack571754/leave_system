from django.db import models

from core.users.models import OrgUnit, Store, User


class Role(models.Model):
    class RoleType(models.TextChoices):
        SYSTEM = 'system', '系统'
        BUSINESS = 'business', '业务'

    code = models.CharField('角色编码', max_length=50, unique=True)
    name = models.CharField('角色名称', max_length=100)
    role_type = models.CharField('角色类型', max_length=20, choices=RoleType.choices, default=RoleType.BUSINESS)
    description = models.TextField('描述', blank=True)
    priority = models.PositiveIntegerField('优先级', default=100)
    is_system = models.BooleanField('系统角色', default=False)
    is_active = models.BooleanField('是否启用', default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['priority', 'code']
        verbose_name = 'RBAC 角色'
        verbose_name_plural = 'RBAC 角色'

    def __str__(self):
        return f'{self.name} ({self.code})'


class Permission(models.Model):
    code = models.CharField('权限编码', max_length=100, unique=True)
    module = models.CharField('模块', max_length=50)
    resource = models.CharField('资源', max_length=50)
    action = models.CharField('操作', max_length=50)
    description = models.TextField('描述', blank=True)
    is_active = models.BooleanField('是否启用', default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['module', 'resource', 'action']
        verbose_name = 'RBAC 权限'
        verbose_name_plural = 'RBAC 权限'

    def __str__(self):
        return self.code

    def save(self, *args, **kwargs):
        if not self.code:
            self.code = f'{self.module}.{self.resource}.{self.action}'
        super().save(*args, **kwargs)


class RolePermission(models.Model):
    class Effect(models.TextChoices):
        ALLOW = 'allow', '允许'
        DENY = 'deny', '拒绝'

    role = models.ForeignKey(Role, on_delete=models.CASCADE, related_name='role_permissions', verbose_name='角色')
    permission = models.ForeignKey(Permission, on_delete=models.CASCADE, related_name='role_permissions', verbose_name='权限')
    effect = models.CharField('效果', max_length=10, choices=Effect.choices, default=Effect.ALLOW)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['role__priority', 'permission__code']
        unique_together = ['role', 'permission']
        verbose_name = '角色权限'
        verbose_name_plural = '角色权限'

    def __str__(self):
        return f'{self.role.code} -> {self.permission.code} ({self.effect})'


class UserRoleAssignment(models.Model):
    class ScopeType(models.TextChoices):
        GLOBAL = 'global', '全局'
        ORG_UNIT = 'org_unit', '组织单元'
        STORE = 'store', '店铺'

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='role_assignments', verbose_name='用户')
    role = models.ForeignKey(Role, on_delete=models.CASCADE, related_name='user_assignments', verbose_name='角色')
    scope_type = models.CharField('范围类型', max_length=20, choices=ScopeType.choices, default=ScopeType.GLOBAL)
    org_unit = models.ForeignKey(
        OrgUnit,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='role_assignments',
        verbose_name='组织单元',
    )
    store = models.ForeignKey(
        Store,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='role_assignments',
        verbose_name='店铺',
    )
    starts_at = models.DateTimeField('生效时间', null=True, blank=True)
    ends_at = models.DateTimeField('失效时间', null=True, blank=True)
    is_active = models.BooleanField('是否启用', default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['user__username', 'role__priority', 'scope_type']
        verbose_name = '用户角色分配'
        verbose_name_plural = '用户角色分配'
        constraints = [
            models.UniqueConstraint(
                fields=['user', 'role', 'scope_type'],
                name='unique_user_role_scope',
                condition=models.Q(org_unit__isnull=True, store__isnull=True),
            ),
            models.UniqueConstraint(
                fields=['user', 'role', 'scope_type', 'org_unit'],
                name='unique_user_role_scope_org',
                condition=models.Q(org_unit__isnull=False, store__isnull=True),
            ),
            models.UniqueConstraint(
                fields=['user', 'role', 'scope_type', 'store'],
                name='unique_user_role_scope_store',
                condition=models.Q(store__isnull=False),
            ),
        ]

    def __str__(self):
        return f'{self.user.username} -> {self.role.code}'


class DataPermissionConfig(models.Model):
    """DEPRECATED: Use DataScopeRule instead.

    This model is retained for migration compatibility only.
    All permission logic now uses DataScopeRule exclusively.
    """

    class SubjectType(models.TextChoices):
        USER = 'user', '用户'
        ROLE = 'role', '角色'

    class ScopeType(models.TextChoices):
        ALL = 'all', '全部店铺'
        ORG_UNIT = 'org_unit', '组织单元'
        STORE = 'store', '店铺'

    name = models.CharField('名称', max_length=100, unique=True)
    subject_type = models.CharField('主体类型', max_length=20, choices=SubjectType.choices)
    target_users = models.ManyToManyField(User, blank=True, related_name='data_permission_configs', verbose_name='目标用户')
    target_roles = models.JSONField('目标角色', default=list, blank=True)
    scope_type = models.CharField('范围类型', max_length=20, choices=ScopeType.choices, default=ScopeType.STORE)
    org_units = models.ManyToManyField(OrgUnit, blank=True, related_name='data_permission_configs', verbose_name='组织单元')
    stores = models.ManyToManyField(Store, blank=True, related_name='data_permission_configs', verbose_name='店铺')
    is_active = models.BooleanField('是否启用', default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['name']
        verbose_name = '数据权限配置（已废弃）'
        verbose_name_plural = '数据权限配置（已废弃）'

    def __str__(self):
        return self.name


class DataScopeRule(models.Model):
    class SubjectType(models.TextChoices):
        USER = 'user', '用户'
        ROLE = 'role', '角色'

    class ScopeType(models.TextChoices):
        ALL = 'all', '全部店铺'
        ORG_UNIT = 'org_unit', '组织单元'
        STORE = 'store', '店铺'
        SELF = 'self', '本人所属'
        SUBORDINATE = 'subordinate', '下属所属'
        ASSIGNED = 'assigned', '已分配'

    name = models.CharField('名称', max_length=100, unique=True)
    resource_code = models.CharField('资源编码', max_length=100, default='store')
    subject_type = models.CharField('主体类型', max_length=20, choices=SubjectType.choices)
    target_users = models.ManyToManyField(User, blank=True, related_name='data_scope_rules', verbose_name='目标用户')
    target_roles = models.ManyToManyField(Role, blank=True, related_name='data_scope_rules', verbose_name='目标角色')
    scope_type = models.CharField('范围类型', max_length=20, choices=ScopeType.choices, default=ScopeType.STORE)
    org_units = models.ManyToManyField(OrgUnit, blank=True, related_name='data_scope_rules', verbose_name='组织单元')
    stores = models.ManyToManyField(Store, blank=True, related_name='data_scope_rules', verbose_name='店铺')
    conditions = models.JSONField('条件', default=dict, blank=True)
    is_active = models.BooleanField('是否启用', default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['resource_code', 'name']
        verbose_name = '数据范围规则'
        verbose_name_plural = '数据范围规则'

    def __str__(self):
        return self.name


class FrontendPagePermission(models.Model):
    page_key = models.CharField('页面标识', max_length=50, unique=True)
    label = models.CharField('页面标签', max_length=100)
    url_name = models.CharField('路由名称', max_length=100, blank=True)
    permission_code = models.CharField('权限编码', max_length=100, blank=True)
    show_in_menu = models.BooleanField('显示在菜单', default=True)
    menu_order = models.PositiveIntegerField('菜单排序', default=100)
    require_auth = models.BooleanField('需要登录', default=True)
    allow_all_users = models.BooleanField('允许所有用户', default=False)
    allowed_roles = models.ManyToManyField(Role, blank=True, related_name='visible_pages', verbose_name='允许角色')
    _legacy_allowed_roles = models.JSONField(default=list, blank=True, editable=False)
    is_active = models.BooleanField('是否启用', default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['menu_order', 'page_key']
        verbose_name = '前端页面权限'
        verbose_name_plural = '前端页面权限'

    def __str__(self):
        return f'{self.label} ({self.page_key})'
