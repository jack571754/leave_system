"""
代理人服务
实现代理人查找和权限冲突检测逻辑
"""

import logging
from django.utils import timezone
from leave_api.models import ApprovalProxy

logger = logging.getLogger(__name__)


class ProxyService:
    """
    代理人服务类
    
    负责处理审批代理相关的业务逻辑：
    - 查找有效的代理人
    - 检查代理时间范围
    - 检查代理人权限冲突
    - 实现冲突时的升级逻辑
    
    需求映射：
    - 10.2: 代理时间范围内将任务分配给代理人
    - 10.3: 记录代理操作
    - 10.4: 代理时间范围结束后停止代理
    - 10.7: 检测权限冲突并升级
    """
    
    def get_effective_approver(self, approver_email, workflow_context=None):
        """
        获取有效的审批人（考虑代理设置）
        
        Args:
            approver_email: 原审批人邮箱
            workflow_context: 工作流上下文（可选），用于检测权限冲突
                格式: {
                    'leave_request_id': int,
                    'applicant_email': str,
                    'previous_approvers': [str],  # 已审批过的人员邮箱列表
                }
        
        Returns:
            dict: {
                'effective_approver': str,  # 有效审批人邮箱
                'is_proxy': bool,           # 是否为代理
                'proxy_for': str or None,   # 如果是代理，原审批人邮箱
                'conflict_detected': bool,  # 是否检测到权限冲突
                'escalated_to': str or None # 如果升级，升级到的审批人邮箱
            }
        
        需求：10.2, 10.3, 10.4, 10.7
        """
        try:
            # 1. 检查是否有有效的代理设置
            proxy = self._find_active_proxy(approver_email)
            
            if not proxy:
                # 没有代理，返回原审批人
                return {
                    'effective_approver': approver_email,
                    'is_proxy': False,
                    'proxy_for': None,
                    'conflict_detected': False,
                    'escalated_to': None
                }
            
            # 2. 检查代理人权限冲突
            if workflow_context:
                conflict = self._check_proxy_conflict(
                    proxy.proxy_email,
                    workflow_context
                )
                
                if conflict['has_conflict']:
                    # 3. 处理冲突：升级到更高一级审批人
                    escalated_approver = self._escalate_approver(
                        approver_email,
                        conflict['reason']
                    )
                    
                    logger.warning(
                        f"代理人权限冲突: 原审批人={approver_email}, "
                        f"代理人={proxy.proxy_email}, "
                        f"冲突原因={conflict['reason']}, "
                        f"升级到={escalated_approver}"
                    )
                    
                    return {
                        'effective_approver': escalated_approver,
                        'is_proxy': False,
                        'proxy_for': None,
                        'conflict_detected': True,
                        'escalated_to': escalated_approver
                    }
            
            # 4. 无冲突，使用代理人
            logger.info(
                f"使用代理人: 原审批人={approver_email}, "
                f"代理人={proxy.proxy_email}, "
                f"代理期间={proxy.start_date} 至 {proxy.end_date}"
            )
            
            return {
                'effective_approver': proxy.proxy_email,
                'is_proxy': True,
                'proxy_for': approver_email,
                'conflict_detected': False,
                'escalated_to': None
            }
            
        except Exception as e:
            logger.error(f"获取有效审批人失败: {e}", exc_info=True)
            # 出错时返回原审批人，确保流程不中断
            return {
                'effective_approver': approver_email,
                'is_proxy': False,
                'proxy_for': None,
                'conflict_detected': False,
                'escalated_to': None
            }
    
    def _find_active_proxy(self, principal_email):
        """
        查找有效的代理设置
        
        Args:
            principal_email: 委托人邮箱
        
        Returns:
            ApprovalProxy or None: 有效的代理设置，如果没有则返回 None
        
        需求：10.2, 10.4
        """
        now = timezone.now()
        
        # 查询满足以下条件的代理设置：
        # 1. 委托人匹配
        # 2. 激活状态
        # 3. 当前时间在代理时间范围内
        proxy = ApprovalProxy.objects.filter(
            principal_email=principal_email,
            is_active=True,
            start_date__lte=now,
            end_date__gte=now
        ).first()
        
        return proxy
    
    def _check_proxy_conflict(self, proxy_email, workflow_context):
        """
        检查代理人权限冲突
        
        权限冲突场景：
        1. 代理人是申请人本人
        2. 代理人已经在该流程中审批过
        3. 代理人在流程中既是原审批人又是代理人（循环代理）
        
        Args:
            proxy_email: 代理人邮箱
            workflow_context: 工作流上下文
        
        Returns:
            dict: {
                'has_conflict': bool,
                'reason': str or None
            }
        
        需求：10.7
        """
        # 场景 1: 代理人是申请人本人
        if proxy_email == workflow_context.get('applicant_email'):
            return {
                'has_conflict': True,
                'reason': 'proxy_is_applicant'
            }
        
        # 场景 2: 代理人已经在该流程中审批过
        previous_approvers = workflow_context.get('previous_approvers', [])
        if proxy_email in previous_approvers:
            return {
                'has_conflict': True,
                'reason': 'proxy_already_approved'
            }
        
        # 场景 3: 检查循环代理（代理人也设置了代理）
        # 根据需求 10.6，不支持二级代理
        proxy_of_proxy = self._find_active_proxy(proxy_email)
        if proxy_of_proxy:
            return {
                'has_conflict': True,
                'reason': 'circular_proxy'
            }
        
        # 无冲突
        return {
            'has_conflict': False,
            'reason': None
        }
    
    def _escalate_approver(self, original_approver_email, conflict_reason):
        """
        升级审批人到更高一级
        
        当检测到代理人权限冲突时，将审批任务升级到更高一级审批人。
        升级策略：
        1. 查找原审批人的直属上级
        2. 如果没有直属上级，查找部门负责人
        3. 如果都没有，返回原审批人（记录警告）
        
        Args:
            original_approver_email: 原审批人邮箱
            conflict_reason: 冲突原因
        
        Returns:
            str: 升级后的审批人邮箱
        
        需求：10.7
        """
        try:
            from organization.models import Employee
            
            # 1. 查找原审批人
            try:
                employee = Employee.objects.select_related(
                    'direct_manager',
                    'department'
                ).get(email=original_approver_email)
            except Employee.DoesNotExist:
                logger.warning(
                    f"未找到员工信息: {original_approver_email}, "
                    f"无法升级审批人"
                )
                return original_approver_email
            
            # 2. 尝试升级到直属上级
            if employee.direct_manager:
                escalated_email = employee.direct_manager.email
                logger.info(
                    f"升级到直属上级: {original_approver_email} -> {escalated_email}"
                )
                return escalated_email
            
            # 3. 尝试升级到部门负责人
            if employee.department and employee.department.manager:
                escalated_email = employee.department.manager.email
                logger.info(
                    f"升级到部门负责人: {original_approver_email} -> {escalated_email}"
                )
                return escalated_email
            
            # 4. 无法升级，返回原审批人
            logger.warning(
                f"无法找到更高一级审批人: {original_approver_email}, "
                f"冲突原因={conflict_reason}"
            )
            return original_approver_email
            
        except Exception as e:
            logger.error(f"升级审批人失败: {e}", exc_info=True)
            return original_approver_email
    
    def check_proxy_validity(self, proxy_id):
        """
        检查代理设置的有效性
        
        Args:
            proxy_id: 代理设置 ID
        
        Returns:
            dict: {
                'is_valid': bool,
                'reason': str or None,
                'expires_at': datetime or None
            }
        """
        try:
            proxy = ApprovalProxy.objects.get(id=proxy_id)
            now = timezone.now()
            
            if not proxy.is_active:
                return {
                    'is_valid': False,
                    'reason': 'proxy_deactivated',
                    'expires_at': None
                }
            
            if now < proxy.start_date:
                return {
                    'is_valid': False,
                    'reason': 'proxy_not_started',
                    'expires_at': proxy.start_date
                }
            
            if now > proxy.end_date:
                return {
                    'is_valid': False,
                    'reason': 'proxy_expired',
                    'expires_at': proxy.end_date
                }
            
            return {
                'is_valid': True,
                'reason': None,
                'expires_at': proxy.end_date
            }
            
        except ApprovalProxy.DoesNotExist:
            return {
                'is_valid': False,
                'reason': 'proxy_not_found',
                'expires_at': None
            }
    
    def get_proxy_info(self, approver_email):
        """
        获取审批人的代理信息
        
        Args:
            approver_email: 审批人邮箱
        
        Returns:
            dict or None: 代理信息，如果没有代理则返回 None
        """
        proxy = self._find_active_proxy(approver_email)
        
        if not proxy:
            return None
        
        return {
            'proxy_id': proxy.id,
            'principal_email': proxy.principal_email,
            'proxy_email': proxy.proxy_email,
            'start_date': proxy.start_date.isoformat(),
            'end_date': proxy.end_date.isoformat(),
            'is_active': proxy.is_active
        }
