"""
数据模型模块
定义请假审批系统的数据库模型
"""

from django.db import models


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
    
    status = models.CharField(
        max_length=20, 
        choices=STATUS_CHOICES, 
        default='draft', 
        verbose_name='状态',
        help_text='当前申请的状态'
    )
    
    # ========== 工作流关联字段（核心）==========
    # 这两个字段是 Django 与 SpiffWorkflow 集成的关键
    
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
