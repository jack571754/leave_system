from django.conf import settings
from django.db import models


class ApprovalRecord(models.Model):
    """Legacy personal-plan approval record."""

    class Action(models.TextChoices):
        APPROVE = 'approve', '通过'
        REJECT = 'reject', '退回'

    plan = models.ForeignKey(
        'plans.SalesPlan',
        on_delete=models.CASCADE,
        verbose_name='销售计划',
        related_name='approvals',
    )
    approver = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        verbose_name='审批人',
        related_name='approval_records',
    )
    approval_level = models.IntegerField('审批层级')
    action = models.CharField('审批动作', max_length=20, choices=Action.choices)
    comment = models.TextField('审批意见', blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = '审批记录'
        verbose_name_plural = '审批记录'
        ordering = ['-created_at']

    def __str__(self):
        return f'{self.plan.plan_month} - {self.approver.username} - {self.get_action_display()}'


class ApprovalFlow(models.Model):
    """Reusable approval configuration."""

    class FlowType(models.TextChoices):
        SALES_PLAN = 'sales_plan', '销售计划审批'
        PLAN_TASK = 'plan_task', '任务审批'

    class ScopeType(models.TextChoices):
        GLOBAL = 'global', '全局'
        DEPARTMENT = 'department', '部门'
        ORG_UNIT = 'org_unit', '组织'
        STORE = 'store', '店铺'

    name = models.CharField('流程名称', max_length=100)
    flow_type = models.CharField('流程类型', max_length=50, choices=FlowType.choices)
    scope_type = models.CharField(
        '适用范围类型',
        max_length=20,
        choices=ScopeType.choices,
        default=ScopeType.GLOBAL,
    )
    department = models.ForeignKey(
        'users.Department',
        on_delete=models.CASCADE,
        verbose_name='适用部门',
        null=True,
        blank=True,
        help_text='为空表示不按部门限制',
    )
    org_unit = models.ForeignKey(
        'users.OrgUnit',
        on_delete=models.CASCADE,
        verbose_name='适用组织',
        null=True,
        blank=True,
        related_name='approval_flows',
    )
    store = models.ForeignKey(
        'users.Store',
        on_delete=models.CASCADE,
        verbose_name='适用店铺',
        null=True,
        blank=True,
        related_name='approval_flows',
    )
    levels = models.JSONField(
        '审批层级配置',
        default=list,
        help_text='例如: [{"step": 1, "approver_type": "manager"}]',
    )
    is_active = models.BooleanField('是否启用', default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = '审批流程'
        verbose_name_plural = '审批流程'
        ordering = ['flow_type', 'scope_type', 'name']

    def __str__(self):
        return self.name

    def get_approver_for_level(self, level, submitter):
        from core.users.models import User

        level_config = next(
            (l for l in self.levels if l.get('level') == level or l.get('step') == level),
            None,
        )

        if not level_config:
            return None

        role = level_config.get('role')
        approver_type = level_config.get('approver_type')
        value = level_config.get('value')

        if level == 1 and submitter.manager:
            return submitter.manager

        if approver_type == 'user' and value:
            return User.objects.filter(pk=value, is_active=True).first()
        if approver_type == 'role' and value:
            return User.objects.filter(role=value, is_active=True).first()
        if role:
            approvers = User.objects.filter(role=role, is_active=True)
            if role == 'manager' and submitter.department:
                approvers = approvers.filter(department=submitter.department)
            return approvers.first()

        return None

    @classmethod
    def get_applicable_for_task(cls, task):
        candidates = cls.objects.filter(flow_type=cls.FlowType.PLAN_TASK, is_active=True)

        if task.store_id:
            store_flow = candidates.filter(
                scope_type=cls.ScopeType.STORE,
                store_id=task.store_id,
            ).first()
            if store_flow:
                return store_flow

        current = task.org_unit
        while current:
            org_flow = candidates.filter(
                scope_type=cls.ScopeType.ORG_UNIT,
                org_unit_id=current.pk,
            ).first()
            if org_flow:
                return org_flow
            current = current.parent

        if task.org_unit and task.org_unit.parent:
            department_flow = candidates.filter(
                scope_type=cls.ScopeType.DEPARTMENT,
                org_unit_id=task.org_unit.parent_id,
            ).first()
            if department_flow:
                return department_flow

        return candidates.filter(scope_type=cls.ScopeType.GLOBAL).first()

    def get_steps_for_task(self, task):
        from core.users.models import User

        resolved_steps = []
        seen_user_ids = set()

        def append_step(user_obj, label, order):
            if not user_obj or not getattr(user_obj, 'pk', None):
                return
            if user_obj.pk in seen_user_ids:
                return
            seen_user_ids.add(user_obj.pk)
            resolved_steps.append({
                'step': order,
                'approver': user_obj,
                'label': label,
            })

        for index, config in enumerate(self.levels, start=1):
            order = config.get('step') or index
            approver_type = config.get('approver_type') or config.get('role')
            value = config.get('value')

            user_obj = None
            label = config.get('label') or approver_type or f'step-{order}'

            if approver_type in {'manager', 'direct_manager'}:
                user_obj = task.assignee.manager if task.assignee and task.assignee.manager_id else None
            elif approver_type == 'org_unit_manager':
                user_obj = task.org_unit.manager if task.org_unit and task.org_unit.manager_id else None
            elif approver_type == 'parent_manager':
                current = task.org_unit.parent if task.org_unit else None
                while current and not current.manager_id:
                    current = current.parent
                user_obj = current.manager if current and current.manager_id else None
            elif approver_type == 'user' and value:
                user_obj = User.objects.filter(pk=value, is_active=True).first()
            elif approver_type == 'role' and value:
                user_obj = User.objects.filter(role=value, is_active=True).first()
            elif approver_type == 'admin':
                user_obj = User.objects.filter(role=User.Role.ADMIN, is_active=True).first()

            append_step(user_obj, label, order)

        # Renumber to consecutive 1, 2, 3... after dedup
        for i, step in enumerate(resolved_steps, start=1):
            step['step'] = i

        return resolved_steps


class TaskApprovalInstance(models.Model):
    """A single approval round for a store task."""

    class Status(models.TextChoices):
        PENDING = 'pending', '审批中'
        APPROVED = 'approved', '已通过'
        REJECTED = 'rejected', '已驳回'
        WITHDRAWN = 'withdrawn', '已撤回'

    task = models.ForeignKey(
        'plans.PlanTask',
        on_delete=models.CASCADE,
        related_name='approval_instances',
        verbose_name='计划任务',
    )
    round_no = models.PositiveIntegerField('审批轮次', default=1)
    status = models.CharField('实例状态', max_length=20, choices=Status.choices, default=Status.PENDING)
    current_step = models.PositiveIntegerField('当前步骤', default=1)
    submitter = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='submitted_approval_instances',
        verbose_name='提交人',
    )
    pending_approver = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='pending_approval_instances',
        verbose_name='待审批人',
    )
    submit_comment = models.TextField('提交说明', blank=True)
    steps_snapshot = models.JSONField(
        '审批步骤快照',
        default=dict,
        blank=True,
        help_text='提交时冻结的审批链快照，避免后续组织架构变更影响进行中的审批',
    )
    started_at = models.DateTimeField('发起时间', auto_now_add=True)
    finished_at = models.DateTimeField('结束时间', null=True, blank=True)
    withdrawn_at = models.DateTimeField('撤回时间', null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = '任务审批实例'
        verbose_name_plural = '任务审批实例'
        ordering = ['-created_at']
        unique_together = ['task', 'round_no']

    def __str__(self):
        return f'{self.task} - 第{self.round_no}轮'


class TaskApprovalRecord(models.Model):
    """Approval history record for store tasks."""

    class Action(models.TextChoices):
        APPROVE = 'approve', '通过'
        REJECT_TO_PREVIOUS = 'reject_to_previous', '驳回上一步'
        REJECT_TO_SUBMITTER = 'reject_to_submitter', '驳回提交人'
        WITHDRAW = 'withdraw', '撤回'
        RESUBMIT = 'resubmit', '重新提交'

    instance = models.ForeignKey(
        TaskApprovalInstance,
        on_delete=models.CASCADE,
        verbose_name='审批实例',
        related_name='records',
        null=True,
        blank=True,
    )
    task = models.ForeignKey(
        'plans.PlanTask',
        on_delete=models.CASCADE,
        verbose_name='计划任务',
        related_name='approvals',
    )
    approver = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        verbose_name='审批人',
        related_name='task_approval_records',
    )
    approval_level = models.IntegerField('审批层级')
    action = models.CharField('审批动作', max_length=30, choices=Action.choices)
    comment = models.TextField('审批意见', blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = '任务审批记录'
        verbose_name_plural = '任务审批记录'
        ordering = ['-created_at']

    def __str__(self):
        return f'{self.task} - {self.approver.username} - {self.get_action_display()}'
