from django.contrib.auth.models import AbstractUser
from django.core.validators import RegexValidator
from django.db import models


class Department(models.Model):
    """Legacy department model used by the original approval flow."""

    name = models.CharField('部门名称', max_length=100)
    code = models.CharField('部门编码', max_length=50, unique=True)
    parent = models.ForeignKey(
        'self',
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        verbose_name='上级部门',
        related_name='children'
    )
    manager = models.ForeignKey(
        'User',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        verbose_name='部门负责人',
        related_name='managed_depts'
    )
    is_active = models.BooleanField('是否启用', default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = '部门'
        verbose_name_plural = '部门'
        ordering = ['code']
        indexes = [
            models.Index(fields=['is_active'], name='dept_active_idx'),
        ]

    def __str__(self):
        return self.name

    def get_full_path(self):
        if self.parent:
            return f"{self.parent.get_full_path()} > {self.name}"
        return self.name


class OrgUnit(models.Model):
    """Hierarchical org node for department, team, and platform scopes."""

    class UnitType(models.TextChoices):
        DEPARTMENT = 'department', '部门'
        GROUP = 'group', '小组'
        PLATFORM = 'platform', '平台'

    name = models.CharField('名称', max_length=100)
    code = models.CharField('编码', max_length=50, unique=True)
    unit_type = models.CharField('类型', max_length=20, choices=UnitType.choices)
    parent = models.ForeignKey(
        'self',
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        verbose_name='上级组织',
        related_name='children'
    )
    manager = models.ForeignKey(
        'User',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        verbose_name='负责人',
        related_name='managed_org_units'
    )
    is_active = models.BooleanField('是否启用', default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = '组织单元'
        verbose_name_plural = '组织单元'
        ordering = ['unit_type', 'code']
        indexes = [
            models.Index(fields=['unit_type', 'is_active'], name='orgunit_type_active_idx'),
            models.Index(fields=['parent'], name='orgunit_parent_idx'),
        ]

    def __str__(self):
        return f"{self.get_unit_type_display()} - {self.name}"

    def get_full_path(self):
        if self.parent:
            return f"{self.parent.get_full_path()} > {self.name}"
        return self.name


class Store(models.Model):
    """A planning target store under a platform-level org node."""

    name = models.CharField('店铺名称', max_length=120)
    code = models.CharField('店铺编码', max_length=50, unique=True)
    org_unit = models.ForeignKey(
        OrgUnit,
        on_delete=models.PROTECT,
        verbose_name='所属组织',
        related_name='stores'
    )
    owner = models.ForeignKey(
        'User',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        verbose_name='店铺负责人',
        related_name='owned_stores'
    )
    is_active = models.BooleanField('是否启用', default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = '店铺'
        verbose_name_plural = '店铺'
        ordering = ['code']
        indexes = [
            models.Index(fields=['org_unit', 'is_active'], name='store_orgunit_active_idx'),
        ]

    def __str__(self):
        return f"{self.code} - {self.name}"


class User(AbstractUser):
    """User model with both legacy and new planning-scope ownership fields."""

    class Role(models.TextChoices):
        ADMIN = 'admin', '系统管理员'
        MANAGER = 'manager', '经理'
        SUPERVISOR = 'supervisor', '主管'
        STAFF = 'staff', '普通员工'

    phone_regex = RegexValidator(
        regex=r'^1[3-9]\d{9}$',
        message='请输入有效的11位手机号',
    )

    phone = models.CharField(
        '手机号',
        max_length=20,
        blank=True,
        validators=[phone_regex],
    )
    avatar = models.ImageField('头像', upload_to='avatars/', blank=True, null=True)
    department = models.ForeignKey(
        Department,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        verbose_name='所属部门',
        related_name='users'
    )
    org_unit = models.ForeignKey(
        OrgUnit,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        verbose_name='所属组织单元',
        related_name='users'
    )
    role = models.CharField('角色', max_length=20, choices=Role.choices, default=Role.STAFF)
    manager = models.ForeignKey(
        'self',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        verbose_name='直属上级',
        related_name='subordinates'
    )

    class Meta:
        verbose_name = '用户'
        verbose_name_plural = '用户'
        ordering = ['username']
        indexes = [
            models.Index(fields=['role', 'is_active'], name='user_role_active_idx'),
            models.Index(fields=['department', 'is_active'], name='user_dept_active_idx'),
            models.Index(fields=['manager'], name='user_manager_idx'),
        ]

    def __str__(self):
        return f"{self.username} ({self.get_role_display()})"

    def get_approval_level(self):
        level_map = {
            self.Role.STAFF: 0,
            self.Role.SUPERVISOR: 1,
            self.Role.MANAGER: 2,
            self.Role.ADMIN: 99,
        }
        return level_map.get(self.role, 0)

    def is_approver(self):
        return self.role in [self.Role.SUPERVISOR, self.Role.MANAGER, self.Role.ADMIN]

    def can_manage_store(self, store):
        if self.role == self.Role.ADMIN:
            return True
        if store.owner_id == self.id:
            return True
        return self.store_memberships.filter(
            store=store,
            role__in=[StoreMembership.Role.OWNER, StoreMembership.Role.EDITOR],
            is_active=True,
        ).exists()


class StoreMembership(models.Model):
    """Store-level permission assignments for planning and review."""

    class Role(models.TextChoices):
        OWNER = 'owner', '负责人'
        EDITOR = 'editor', '填报人'
        VIEWER = 'viewer', '查看人'

    store = models.ForeignKey(
        Store,
        on_delete=models.CASCADE,
        verbose_name='店铺',
        related_name='memberships'
    )
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        verbose_name='用户',
        related_name='store_memberships'
    )
    role = models.CharField('店铺角色', max_length=20, choices=Role.choices)
    is_active = models.BooleanField('是否启用', default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = '店铺成员权限'
        verbose_name_plural = '店铺成员权限'
        unique_together = ['store', 'user']
        ordering = ['store__code', 'user__username']
        indexes = [
            models.Index(fields=['user', 'is_active'], name='storemember_user_active_idx'),
            models.Index(fields=['store', 'role', 'is_active'], name='storemember_store_role_idx'),
        ]

    def __str__(self):
        return f"{self.store} - {self.user.username} - {self.get_role_display()}"
