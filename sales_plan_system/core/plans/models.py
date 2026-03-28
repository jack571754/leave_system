from django.conf import settings
from django.db import models
from django.db.models import Q
from django.utils import timezone
from dateutil.relativedelta import relativedelta


class SalesPlan(models.Model):
    """Legacy personal sales plan model kept for backward compatibility."""

    class Status(models.TextChoices):
        DRAFT = 'draft', '草稿'
        PENDING = 'pending', '审批中'
        APPROVED = 'approved', '已批准'
        REJECTED = 'rejected', '已退回'

    plan_month = models.CharField('计划月份', max_length=7, help_text='格式: YYYY-MM')
    submitter = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        verbose_name='提报人',
        related_name='sales_plans',
    )
    department = models.ForeignKey(
        'users.Department',
        on_delete=models.SET_NULL,
        null=True,
        verbose_name='所属部门',
        related_name='sales_plans',
    )
    status = models.CharField('状态', max_length=20, choices=Status.choices, default=Status.DRAFT)
    remark = models.TextField('备注', blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    submitted_at = models.DateTimeField('提交时间', null=True, blank=True)
    approved_at = models.DateTimeField('批准时间', null=True, blank=True)

    class Meta:
        verbose_name = '销售计划'
        verbose_name_plural = '销售计划'
        ordering = ['-plan_month', '-created_at']
        unique_together = ['plan_month', 'submitter']

    def __str__(self):
        return f'{self.plan_month} - {self.submitter.username}'

    def get_target_months(self):
        year, month = map(int, self.plan_month.split('-'))
        base_date = timezone.datetime(year, month, 1)
        return [
            (base_date + relativedelta(months=i)).strftime('%Y-%m')
            for i in range(1, 5)
        ]

    def get_total_amount(self):
        return self.items.aggregate(
            total=models.Sum(models.F('sales_qty') * models.F('unit_price'))
        )['total'] or 0

    def can_edit(self):
        return self.status == self.Status.DRAFT

    def can_submit(self):
        return self.status == self.Status.DRAFT and self.items.exists()

    def can_approve(self, user):
        if self.status != self.Status.PENDING:
            return False
        if user == self.submitter:
            return False
        if getattr(user, 'role', None) == user.Role.ADMIN:
            return True
        approver = self.get_current_approver()
        return approver is not None and approver.pk == user.pk

    def get_current_approval_level(self):
        if self.status != self.Status.PENDING:
            return None

        approved_levels = self.approvals.filter(
            action='approve'
        ).values_list('approval_level', flat=True)

        if not approved_levels:
            return 1
        return max(approved_levels) + 1

    def get_approval_flow(self):
        from core.approvals.models import ApprovalFlow

        flows = ApprovalFlow.objects.filter(
            flow_type=ApprovalFlow.FlowType.SALES_PLAN,
            is_active=True,
        ).filter(Q(department=self.department) | Q(department__isnull=True))

        if self.department:
            department_flow = flows.filter(department=self.department).first()
            if department_flow:
                return department_flow

        return flows.filter(department__isnull=True).first()

    def get_max_approval_level(self):
        flow = self.get_approval_flow()
        if flow and flow.levels:
            return max(level.get('level', 0) for level in flow.levels)
        return 2

    def get_current_approver(self):
        if self.status != self.Status.PENDING:
            return None

        flow = self.get_approval_flow()
        current_level = self.get_current_approval_level()

        if flow and current_level:
            approver = flow.get_approver_for_level(current_level, self.submitter)
            if approver:
                return approver

        if current_level == 1:
            return self.submitter.manager

        if current_level == 2 and self.submitter.department:
            return self.submitter.department.manager

        return None

    def submit(self):
        if self.can_submit():
            self.status = self.Status.PENDING
            self.submitted_at = timezone.now()
            self.save()
            return True
        return False

    @classmethod
    def pending_for_approver(cls, user):
        if not getattr(user, 'is_authenticated', False) or not user.is_approver():
            return cls.objects.none()

        pending_plans = cls.objects.filter(status=cls.Status.PENDING).exclude(
            submitter=user
        ).select_related('submitter', 'submitter__manager', 'department', 'department__manager')

        approvable_ids = [plan.pk for plan in pending_plans if plan.can_approve(user)]
        return cls.objects.filter(pk__in=approvable_ids).select_related(
            'submitter', 'department'
        ).order_by('-submitted_at', '-created_at')


class SalesPlanItem(models.Model):
    """Legacy personal sales plan item."""

    plan = models.ForeignKey(
        SalesPlan,
        on_delete=models.CASCADE,
        verbose_name='销售计划',
        related_name='items',
    )
    sku = models.ForeignKey(
        'products.ProductSKU',
        on_delete=models.CASCADE,
        verbose_name='SKU',
    )
    target_month = models.CharField('目标月份', max_length=7, help_text='M+1 ~ M+4')
    sales_qty = models.IntegerField('销售数量', default=0)
    unit_price = models.DecimalField('单价', max_digits=10, decimal_places=2, default=0)
    stock_qty = models.IntegerField('库存数量', default=0)
    remark = models.TextField('备注', blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = '销售计划明细'
        verbose_name_plural = '销售计划明细'
        ordering = ['target_month', 'sku__sku_code']
        unique_together = ['plan', 'sku', 'target_month']

    def __str__(self):
        return f'{self.plan.plan_month} - {self.sku.sku_code} - {self.target_month}'

    @property
    def sales_amount(self):
        return self.sales_qty * self.unit_price


class PlanCampaign(models.Model):
    """Top-level planning campaign that owns all store tasks."""

    class Status(models.TextChoices):
        DRAFT = 'draft', '草稿'
        ACTIVE = 'active', '进行中'
        CLOSED = 'closed', '已结束'
        ARCHIVED = 'archived', '已归档'

    class PlanType(models.TextChoices):
        MONTHLY = 'monthly', '月度'
        AD_HOC = 'ad_hoc', '临时'
        NEW_PRODUCT = 'new_product', '新品'

    title = models.CharField('标题', max_length=120)
    plan_month = models.CharField('计划月份', max_length=7, help_text='格式: YYYY-MM')
    plan_type = models.CharField(
        '计划类型',
        max_length=30,
        choices=PlanType.choices,
        default=PlanType.MONTHLY,
    )
    start_date = models.DateField('开始日期', null=True, blank=True)
    end_date = models.DateField('结束日期', null=True, blank=True)
    org_unit = models.ForeignKey(
        'users.OrgUnit',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        verbose_name='组织单元',
        related_name='plan_campaigns',
    )
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        verbose_name='创建人',
        related_name='created_campaigns',
    )
    status = models.CharField('状态', max_length=20, choices=Status.choices, default=Status.DRAFT)
    remark = models.TextField('备注', blank=True)
    published_at = models.DateTimeField('发布时间', null=True, blank=True)
    closed_at = models.DateTimeField('关闭时间', null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = '计划活动'
        verbose_name_plural = '计划活动'
        ordering = ['-plan_month', '-created_at']
        unique_together = ['plan_month', 'title']

    def __str__(self):
        return f'{self.plan_month} - {self.title}'

    def get_target_months(self):
        year, month = map(int, self.plan_month.split('-'))
        base_date = timezone.datetime(year, month, 1)
        return [
            (base_date + relativedelta(months=i)).strftime('%Y-%m')
            for i in range(1, 5)
        ]

    def is_open(self, at_time=None):
        if self.status != self.Status.ACTIVE:
            return False
        at_time = at_time or timezone.localtime()
        current_date = at_time.date()
        if self.start_date and current_date < self.start_date:
            return False
        if self.end_date and current_date > self.end_date:
            return False
        return True

    def publish(self):
        if self.status == self.Status.DRAFT:
            self.status = self.Status.ACTIVE
            self.published_at = timezone.now()
            self.save(update_fields=['status', 'published_at', 'updated_at'])

    def close(self):
        if self.status == self.Status.ACTIVE:
            self.status = self.Status.CLOSED
            self.closed_at = timezone.now()
            self.save(update_fields=['status', 'closed_at', 'updated_at'])

    @property
    def task_count(self):
        return self.tasks.count()

    @property
    def submitted_task_count(self):
        return self.tasks.filter(
            approval_status__in=[
                PlanTask.ApprovalStatus.PENDING,
                PlanTask.ApprovalStatus.APPROVED,
            ]
        ).count()


class PlanTask(models.Model):
    """Store-level fill-in task generated from a planning campaign."""

    class Status(models.TextChoices):
        DRAFT = 'draft', '待填报'
        SUBMITTED = 'submitted', '已提交'
        APPROVED = 'approved', '已通过'
        REJECTED = 'rejected', '已驳回'
        WITHDRAWN = 'withdrawn', '已撤回'

    class ApprovalStatus(models.TextChoices):
        NOT_STARTED = 'not_started', '未开始'
        PENDING = 'pending', '审批中'
        APPROVED = 'approved', '已通过'
        REJECTED = 'rejected', '已驳回'
        WITHDRAWN = 'withdrawn', '已撤回'

    campaign = models.ForeignKey(
        PlanCampaign,
        on_delete=models.CASCADE,
        verbose_name='计划活动',
        related_name='tasks',
    )
    store = models.ForeignKey(
        'users.Store',
        on_delete=models.PROTECT,
        verbose_name='店铺',
        related_name='plan_tasks',
    )
    org_unit = models.ForeignKey(
        'users.OrgUnit',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        verbose_name='组织单元',
        related_name='plan_tasks',
    )
    assignee = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        verbose_name='负责人',
        related_name='assigned_plan_tasks',
    )
    submitter = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        verbose_name='提交人',
        related_name='submitted_plan_tasks',
    )
    pending_approver = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        verbose_name='待审批人',
        related_name='pending_plan_tasks',
    )
    status = models.CharField('任务状态', max_length=20, choices=Status.choices, default=Status.DRAFT)
    approval_status = models.CharField(
        '审批状态',
        max_length=20,
        choices=ApprovalStatus.choices,
        default=ApprovalStatus.NOT_STARTED,
    )
    current_step = models.PositiveIntegerField('当前步骤', null=True, blank=True)
    round_no = models.PositiveIntegerField('审批轮次', default=0)
    remark = models.TextField('备注', blank=True)
    submitted_at = models.DateTimeField('提交时间', null=True, blank=True)
    last_submitted_at = models.DateTimeField('最后提交时间', null=True, blank=True)
    approved_at = models.DateTimeField('批准时间', null=True, blank=True)
    last_withdrawn_at = models.DateTimeField('最后撤回时间', null=True, blank=True)
    editable_until = models.DateTimeField('可编辑截止时间', null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = '计划任务'
        verbose_name_plural = '计划任务'
        ordering = ['-campaign__plan_month', 'store__code']
        unique_together = ['campaign', 'store']

    def __str__(self):
        return f'{self.campaign.plan_month} - {self.store.name}'

    def save(self, *args, **kwargs):
        if not self.org_unit_id and self.store_id:
            self.org_unit = self.store.org_unit
        if not self.assignee_id and self.store_id and self.store.owner_id:
            self.assignee = self.store.owner
        if not self.editable_until and self.campaign_id and self.campaign.end_date:
            self.editable_until = timezone.make_aware(
                timezone.datetime.combine(
                    self.campaign.end_date,
                    timezone.datetime.max.time().replace(microsecond=0),
                )
            )
        super().save(*args, **kwargs)

    def get_target_months(self):
        return self.campaign.get_target_months()

    def can_view(self, user):
        from core.permissions.services import access_service

        return access_service.can_view_task(user, self)

    def is_in_edit_window(self, at_time=None):
        at_time = at_time or timezone.localtime()
        if not self.campaign.is_open(at_time=at_time):
            return False
        if self.editable_until and at_time > self.editable_until:
            return False
        return True

    def can_edit(self, user):
        from core.permissions.services import access_service

        return access_service.can_edit_task(user, self)

    def can_submit(self, user):
        from core.permissions.services import access_service

        return access_service.can_submit_task(user, self)

    def can_withdraw(self, user):
        from core.permissions.services import access_service

        return access_service.can_withdraw_task(user, self)

    def can_approve(self, user):
        from core.permissions.services import access_service

        return access_service.can_approve_task(user, self)

    def get_active_approval_instance(self):
        return self.approval_instances.order_by('-round_no', '-created_at').first()

    def get_current_approval_level(self):
        instance = self.get_active_approval_instance()
        return instance.current_step if instance else None

    def get_current_approver(self):
        instance = self.get_active_approval_instance()
        if instance:
            return instance.pending_approver
        return self.pending_approver

    def get_approval_flow(self):
        from core.approvals.models import ApprovalFlow

        return ApprovalFlow.get_applicable_for_task(self)

    def get_approval_steps(self):
        flow = self.get_approval_flow()
        if flow:
            steps = flow.get_steps_for_task(self)
            if steps:
                return steps

        steps = []
        seen_user_ids = set()

        def append_step(user_obj, label):
            if not user_obj or not getattr(user_obj, 'pk', None):
                return
            if user_obj.pk in seen_user_ids:
                return
            seen_user_ids.add(user_obj.pk)
            steps.append({
                'step': len(steps) + 1,
                'approver': user_obj,
                'label': label,
            })

        if self.assignee and self.assignee.manager_id:
            append_step(self.assignee.manager, 'Direct manager')
        if self.org_unit and self.org_unit.manager_id:
            append_step(self.org_unit.manager, 'Org unit manager')

        current = self.org_unit.parent if self.org_unit else None
        while current:
            if current.manager_id:
                append_step(current.manager, f'{current.name} manager')
            current = current.parent

        if not steps:
            from core.users.models import User

            append_step(
                User.objects.filter(role=User.Role.ADMIN, is_active=True).first(),
                'System admin',
            )

        return steps

    def get_max_approval_level(self):
        return len(self.get_approval_steps())

    def sync_from_instance(self, instance):
        self.round_no = instance.round_no
        self.current_step = instance.current_step
        self.pending_approver = instance.pending_approver
        if instance.status == instance.Status.APPROVED:
            self.status = self.Status.APPROVED
            self.approval_status = self.ApprovalStatus.APPROVED
            self.approved_at = instance.finished_at or timezone.now()
        elif instance.status == instance.Status.REJECTED:
            self.status = self.Status.REJECTED
            self.approval_status = self.ApprovalStatus.REJECTED
            self.pending_approver = None
            self.current_step = None
        elif instance.status == instance.Status.WITHDRAWN:
            self.status = self.Status.WITHDRAWN
            self.approval_status = self.ApprovalStatus.WITHDRAWN
            self.pending_approver = None
            self.current_step = None
        else:
            self.status = self.Status.SUBMITTED
            self.approval_status = self.ApprovalStatus.PENDING

    def submit(self, user=None, comment=''):
        from .services import task_service

        actor = user or self.assignee or self.store.owner
        if not actor:
            return False
        try:
            task_service.submit_task(self, actor, comment=comment)
            return True
        except Exception:
            return False

    @classmethod
    def pending_for_approver(cls, user):
        from core.permissions.services import access_service

        if not getattr(user, 'is_authenticated', False):
            return cls.objects.none()

        base_queryset = cls.objects.filter(
            approval_status=cls.ApprovalStatus.PENDING,
            store_id__in=access_service.get_authorized_store_ids(user),
        ).select_related(
            'campaign', 'store', 'org_unit', 'assignee', 'submitter', 'pending_approver'
        )

        if access_service.has_perm(user, 'approvals.instance.approve'):
            return base_queryset.order_by('-last_submitted_at', '-created_at')

        if not user.is_approver():
            return cls.objects.none()

        if getattr(user, 'role', None) == user.Role.ADMIN:
            return base_queryset.order_by('-last_submitted_at', '-created_at')

        return base_queryset.filter(
            pending_approver=user,
        ).order_by('-last_submitted_at', '-created_at')

    @property
    def total_amount(self):
        return sum(item.sales_amount for item in self.items.all())


class PlanTaskItem(models.Model):
    """Store-level plan detail item for the task workflow."""

    task = models.ForeignKey(
        PlanTask,
        on_delete=models.CASCADE,
        verbose_name='计划任务',
        related_name='items',
    )
    sku = models.ForeignKey(
        'products.ProductSKU',
        on_delete=models.CASCADE,
        verbose_name='SKU',
    )
    target_month = models.CharField('目标月份', max_length=7, help_text='M+1 ~ M+4')
    sales_qty = models.IntegerField('销售数量', default=0)
    unit_price = models.DecimalField('单价', max_digits=10, decimal_places=2, default=0)
    stock_qty = models.IntegerField('库存数量', default=0)
    remark = models.TextField('备注', blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = '任务明细'
        verbose_name_plural = '任务明细'
        ordering = ['target_month', 'sku__sku_code']
        unique_together = ['task', 'sku', 'target_month']

    def __str__(self):
        return f'{self.task} - {self.sku.sku_code} - {self.target_month}'

    @property
    def sales_amount(self):
        return self.sales_qty * self.unit_price
