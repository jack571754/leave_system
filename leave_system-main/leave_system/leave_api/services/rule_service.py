"""
审批规则服务
实现业务规则匹配和流程选择逻辑
"""

import logging
from django.conf import settings
from leave_api.models import ApprovalRule

logger = logging.getLogger(__name__)


class ApprovalRuleService:
    """
    审批规则服务类
    
    负责根据请假申请的条件匹配合适的审批规则，
    并返回对应的工作流规范名称
    """
    
    def select_workflow_spec(self, leave_request):
        """
        根据请假申请选择工作流规范
        
        Args:
            leave_request: LeaveRequest 实例
            
        Returns:
            str: 工作流规范名称
        """
        # 查询所有激活的规则，按优先级降序排列
        rules = ApprovalRule.objects.filter(is_active=True).order_by('-priority', '-created_at')
        
        # 遍历规则，找到第一个匹配的
        for rule in rules:
            if self._match_rule(leave_request, rule):
                logger.info(f"匹配到规则: {rule.name} (优先级: {rule.priority})")
                return rule.workflow_spec_name
        
        # 如果没有匹配的规则，返回默认流程
        default_spec = getattr(settings, 'DEFAULT_WORKFLOW_SPEC', 'basic_approval')
        logger.info(f"没有匹配的规则，使用默认流程: {default_spec}")
        return default_spec
    
    def _match_rule(self, leave_request, rule):
        """
        检查请假申请是否匹配规则
        
        Args:
            leave_request: LeaveRequest 实例
            rule: ApprovalRule 实例
            
        Returns:
            bool: 是否匹配
        """
        # 检查请假类型
        if rule.leave_type and rule.leave_type != leave_request.leave_type:
            return False
        
        # 检查时长（天数）
        if leave_request.duration:
            if rule.min_duration and leave_request.duration < rule.min_duration:
                return False
            if rule.max_duration and leave_request.duration > rule.max_duration:
                return False
        
        # 检查部门
        if rule.department_name and leave_request.staff_dept != rule.department_name:
            return False
        
        # 检查职级（需要从 organization 模块获取）
        # 暂时跳过，因为 LeaveRequest 没有直接关联 Employee
        # TODO: 如果需要职级匹配，需要通过 user_email 查询 Employee
        
        # 所有条件都匹配
        return True
    
    def get_matching_rules(self, leave_request):
        """
        获取所有匹配的规则（用于调试和测试）
        
        Args:
            leave_request: LeaveRequest 实例
            
        Returns:
            list: 匹配的规则列表
        """
        rules = ApprovalRule.objects.filter(is_active=True).order_by('-priority', '-created_at')
        matching_rules = []
        
        for rule in rules:
            if self._match_rule(leave_request, rule):
                matching_rules.append({
                    'id': rule.id,
                    'name': rule.name,
                    'priority': rule.priority,
                    'workflow_spec_name': rule.workflow_spec_name
                })
        
        return matching_rules
    
    def simulate_rule_matching(self, leave_type=None, duration=None, department_name=None):
        """
        模拟规则匹配（用于测试和配置验证）
        
        Args:
            leave_type (str, optional): 请假类型
            duration (float, optional): 请假天数
            department_name (str, optional): 部门名称
            
        Returns:
            dict: 匹配结果
        """
        # 创建临时的请假申请对象（不保存到数据库）
        from leave_api.models import LeaveRequest
        
        temp_request = LeaveRequest(
            leave_type=leave_type or 'annual',
            duration=duration or 1.0,
            staff_dept=department_name or ''
        )
        
        # 获取匹配的规则
        matching_rules = self.get_matching_rules(temp_request)
        
        # 获取选择的工作流规范
        selected_spec = self.select_workflow_spec(temp_request)
        
        return {
            'matching_rules': matching_rules,
            'selected_workflow_spec': selected_spec,
            'total_active_rules': ApprovalRule.objects.filter(is_active=True).count()
        }
