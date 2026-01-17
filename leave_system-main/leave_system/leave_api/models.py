"""
数据模型模块
定义请假审批系统的数据库模型
"""

from django.db import models
from django.contrib.auth.models import User


class LeaveRequest(models.Model):
    """
    请假申请模型
    
    这是业务数据的核心模型，存储请假申请的所有信息
    
    关键字段说明：
    - process_instance_id: 关联 SpiffWorkflow 工作流实例的唯一标识
      这是连接业务数据和工作流引擎的桥梁
    - status: 业务状态，与工作流状态同步
    
    数据流转：
    1. 创建时状态为 draft（草稿）
    2. 启动工作流后更新为 pending（待审批）
    3. 审批完成后更新为 approved（已批准）或 rejected（已拒绝）
    """
    
    # ========== 状态选项 ==========
    STATUS_CHOICES = [
        ('draft', '草稿'),        # 初始状态，尚未提交审批
        ('pending', '待审批'),    # 已提交，等待审批
        ('approved', '已批准'),   # 审批通过
        ('rejected', '已拒绝'),   # 审批拒绝
        ('cancelled', '已取消'),  # 用户取消申请
    ]
    
    LEAVE_TYPE_CHOICES = [
        ('annual', '年假'),
        ('sick', '病假'),
        ('personal', '事假'),
        ('marriage', '婚假'),
        ('maternity', '产假'),
        ('paternity', '陪产假'),
        ('bereavement', '丧假'),
    ]
    
    # ========== 基本信息字段 ==========
    user_email = models.EmailField(
        verbose_name='申请人邮箱',
        help_text='申请人的邮箱地址，用于标识申请人'
    )
    
    staff_full_name = models.CharField(
        max_length=100, 
        default='', 
        verbose_name='申请人姓名',
        help_text='申请人的完整姓名'
    )
    
    staff_dept = models.CharField(
        max_length=100, 
        default='', 
        verbose_name='申请人部门',
        help_text='申请人所属部门'
    )
    
    reason = models.TextField(
        verbose_name='请假原因',
        help_text='详细的请假原因说明'
    )
    
    leave_hours = models.IntegerField(
        verbose_name='请假时长（小时）',
        help_text='请假的小时数，用于判断审批流程'
    )
    
    # ========== 新增字段 ==========
    leave_type = models.CharField(
        max_length=50,
        choices=LEAVE_TYPE_CHOICES,
        default='annual',
        verbose_name='请假类型',
        help_text='请假的类型'
    )
    
    start_date = models.DateField(
        null=True,
        blank=True,
        verbose_name='开始日期',
        help_text='请假开始日期'
    )
    
    end_date = models.DateField(
        null=True,
        blank=True,
        verbose_name='结束日期',
        help_text='请假结束日期'
    )
    
    duration = models.DecimalField(
        max_digits=5,
        decimal_places=1,
        null=True,
        blank=True,
        verbose_name='请假天数',
        help_text='请假的天数'
    )
    
    status = models.CharField(
        max_length=20, 
        choices=STATUS_CHOICES, 
        default='draft', 
        verbose_name='状态',
        help_text='当前申请的状态'
    )
    
    # ========== 工作流关联字段（核心）==========
    # 这些字段是 Django 与 SpiffWorkflow 集成的关键
    
    process_instance_id = models.CharField(
        max_length=100, 
        null=True, 
        blank=True, 
        verbose_name='流程实例ID',
        help_text='SpiffWorkflow 工作流实例的唯一标识（UUID），用于关联工作流和业务数据'
    )
    
    process_model_id = models.CharField(
        max_length=100, 
        null=True, 
        blank=True, 
        verbose_name='流程模型ID',
        help_text='BPMN 流程模型标识，格式如 "admin/admin"，对应 BPMN 文件路径'
    )
    
    workflow_spec_name = models.CharField(
        max_length=100,
        null=True,
        blank=True,
        verbose_name='工作流规范名称',
        help_text='SpiffWorkflow 中的流程规范名称'
    )
    
    workflow_state = models.JSONField(
        null=True,
        blank=True,
        verbose_name='工作流状态',
        help_text='序列化的工作流状态，用于持久化和恢复'
    )
    
    # ========== 审批信息字段 ==========
    approver_email = models.EmailField(
        null=True, 
        blank=True, 
        verbose_name='审批人邮箱',
        help_text='审批人的邮箱地址'
    )
    
    approver_name = models.CharField(
        max_length=100, 
        blank=True, 
        verbose_name='审批人姓名',
        help_text='审批人的姓名'
    )
    
    approval_comment = models.TextField(
        blank=True, 
        verbose_name='审批意见',
        help_text='审批人的审批意见或备注'
    )
    
    approved_at = models.DateTimeField(
        null=True, 
        blank=True, 
        verbose_name='审批时间',
        help_text='审批完成的时间'
    )
    
    completed_at = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name='完成时间',
        help_text='流程完成的时间'
    )
    
    # ========== 时间戳字段 ==========
    created_at = models.DateTimeField(
        auto_now_add=True, 
        verbose_name='创建时间',
        help_text='记录创建的时间，自动设置'
    )
    
    updated_at = models.DateTimeField(
        auto_now=True, 
        verbose_name='更新时间',
        help_text='记录最后更新的时间，自动更新'
    )
    
    submitted_at = models.DateTimeField(
        null=True, 
        blank=True, 
        verbose_name='提交时间',
        help_text='提交审批的时间'
    )
    
    class Meta:
        """模型元数据配置"""
        verbose_name = '请假申请'
        verbose_name_plural = '请假申请'
        ordering = ['-created_at']  # 默认按创建时间倒序排列
        
        # 数据库索引，提高查询性能
        indexes = [
            # 复合索引：按状态和创建时间查询
            models.Index(fields=['status', 'created_at']),
            # 单字段索引：按流程实例 ID 查询（用于关联工作流）
            models.Index(fields=['process_instance_id']),
        ]
    
    def __str__(self):
        """字符串表示"""
        return f"{self.staff_full_name or self.user_email} - {self.reason[:20]}"


class ApprovalHistory(models.Model):
    """审批历史记录"""
    ACTION_CHOICES = [
        ('submit', '提交'),
        ('approve', '批准'),
        ('reject', '拒绝'),
        ('return', '退回'),
        ('add_sign', '加签'),
        ('transfer', '转签'),
        ('cancel', '取消'),
    ]
    
    leave_request = models.ForeignKey(
        LeaveRequest,
        on_delete=models.CASCADE,
        related_name='history',
        verbose_name='请假申请'
    )
    
    action = models.CharField(
        max_length=20,
        choices=ACTION_CHOICES,
        verbose_name='操作类型'
    )
    
    operator_email = models.EmailField(
        verbose_name='操作人邮箱'
    )
    
    operator_name = models.CharField(
        max_length=100,
        verbose_name='操作人姓名'
    )
    
    operator_role = models.CharField(
        max_length=50,
        verbose_name='操作人角色'
    )
    
    comment = models.TextField(
        blank=True,
        verbose_name='操作意见'
    )
    
    is_proxy = models.BooleanField(
        default=False,
        verbose_name='是否代理操作'
    )
    
    proxy_for_email = models.EmailField(
        null=True,
        blank=True,
        verbose_name='代理的原审批人邮箱'
    )
    
    task_id = models.CharField(
        max_length=100,
        null=True,
        blank=True,
        verbose_name='任务ID'
    )
    
    task_name = models.CharField(
        max_length=100,
        null=True,
        blank=True,
        verbose_name='任务名称'
    )
    
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name='操作时间'
    )
    
    class Meta:
        verbose_name = '审批历史'
        verbose_name_plural = '审批历史'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['leave_request', 'created_at']),
        ]
    
    def __str__(self):
        return f"{self.operator_name} - {self.get_action_display()}"


class ApprovalProxy(models.Model):
    """代理设置"""
    principal_email = models.EmailField(
        verbose_name='委托人邮箱'
    )
    
    proxy_email = models.EmailField(
        verbose_name='代理人邮箱'
    )
    
    start_date = models.DateTimeField(
        verbose_name='开始时间'
    )
    
    end_date = models.DateTimeField(
        verbose_name='结束时间'
    )
    
    is_active = models.BooleanField(
        default=True,
        verbose_name='是否激活'
    )
    
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name='创建时间'
    )
    
    class Meta:
        verbose_name = '代理设置'
        verbose_name_plural = '代理设置'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['principal_email', 'is_active']),
            models.Index(fields=['start_date', 'end_date']),
        ]
    
    def __str__(self):
        return f"{self.principal_email} -> {self.proxy_email}"


class CCRecord(models.Model):
    """抄送记录"""
    leave_request = models.ForeignKey(
        LeaveRequest,
        on_delete=models.CASCADE,
        related_name='cc_records',
        verbose_name='请假申请'
    )
    
    cc_to_email = models.EmailField(
        verbose_name='抄送人邮箱'
    )
    
    cc_by_email = models.EmailField(
        verbose_name='抄送发起人邮箱'
    )
    
    is_read = models.BooleanField(
        default=False,
        verbose_name='是否已读'
    )
    
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name='抄送时间'
    )
    
    read_at = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name='阅读时间'
    )
    
    class Meta:
        verbose_name = '抄送记录'
        verbose_name_plural = '抄送记录'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['leave_request']),
            models.Index(fields=['cc_to_email', 'is_read']),
        ]
    
    def __str__(self):
        return f"抄送给 {self.cc_to_email}"


class ApprovalRule(models.Model):
    """审批规则"""
    name = models.CharField(
        max_length=100,
        verbose_name='规则名称'
    )
    
    description = models.TextField(
        verbose_name='规则描述'
    )
    
    priority = models.IntegerField(
        default=0,
        verbose_name='优先级',
        help_text='数字越大优先级越高'
    )
    
    is_active = models.BooleanField(
        default=True,
        verbose_name='是否激活'
    )
    
    # 条件字段
    leave_type = models.CharField(
        max_length=50,
        null=True,
        blank=True,
        verbose_name='请假类型'
    )
    
    min_duration = models.DecimalField(
        max_digits=5,
        decimal_places=1,
        null=True,
        blank=True,
        verbose_name='最小时长（天）'
    )
    
    max_duration = models.DecimalField(
        max_digits=5,
        decimal_places=1,
        null=True,
        blank=True,
        verbose_name='最大时长（天）'
    )
    
    department_name = models.CharField(
        max_length=100,
        null=True,
        blank=True,
        verbose_name='部门名称'
    )
    
    min_level = models.IntegerField(
        null=True,
        blank=True,
        verbose_name='最小职级'
    )
    
    max_level = models.IntegerField(
        null=True,
        blank=True,
        verbose_name='最大职级'
    )
    
    # 流程配置
    workflow_spec_name = models.CharField(
        max_length=100,
        verbose_name='工作流规范名称'
    )
    
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name='创建时间'
    )
    
    updated_at = models.DateTimeField(
        auto_now=True,
        verbose_name='更新时间'
    )
    
    class Meta:
        verbose_name = '审批规则'
        verbose_name_plural = '审批规则'
        ordering = ['-priority', '-created_at']
        indexes = [
            models.Index(fields=['is_active', 'priority']),
        ]
    
    def __str__(self):
        return self.name


class WorkflowEventLog(models.Model):
    """工作流事件日志"""
    STATUS_CHOICES = [
        ('pending', '待处理'),
        ('success', '成功'),
        ('failed', '失败'),
    ]
    
    workflow_instance_id = models.CharField(
        max_length=100,
        verbose_name='工作流实例ID'
    )
    
    task_id = models.CharField(
        max_length=100,
        null=True,
        blank=True,
        verbose_name='任务ID'
    )
    
    event_type = models.CharField(
        max_length=50,
        verbose_name='事件类型'
    )
    
    event_data = models.JSONField(
        verbose_name='事件数据'
    )
    
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='pending',
        verbose_name='处理状态'
    )
    
    error_message = models.TextField(
        blank=True,
        verbose_name='错误信息'
    )
    
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name='创建时间'
    )
    
    processed_at = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name='处理时间'
    )
    
    class Meta:
        verbose_name = '工作流事件日志'
        verbose_name_plural = '工作流事件日志'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['workflow_instance_id']),
            models.Index(fields=['status', 'created_at']),
        ]
    
    def __str__(self):
        return f"{self.event_type} - {self.workflow_instance_id}"
