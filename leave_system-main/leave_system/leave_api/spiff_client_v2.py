"""
SpiffWorkflow 客户端模块 V2 - 支持持久化

这个模块封装了 SpiffWorkflow 工作流引擎的所有操作
是 Django 与 SpiffWorkflow 集成的核心组件

主要功能：
1. 加载和解析 BPMN 流程定义文件
2. 启动工作流实例
3. 查询待办任务
4. 完成任务并继续执行工作流
5. 查询工作流实例状态
6. 工作流状态序列化和反序列化（持久化支持）

改进：
- 支持工作流状态持久化到数据库
- 支持从数据库恢复工作流实例
- 添加组织架构查询函数
- 支持脚本引擎环境配置
"""

import os
import logging
import uuid
from pathlib import Path
from lxml import etree
from SpiffWorkflow.bpmn.workflow import BpmnWorkflow
from SpiffWorkflow.bpmn.parser.BpmnParser import BpmnParser
from SpiffWorkflow.bpmn.serializer.workflow import BpmnWorkflowSerializer
from SpiffWorkflow.bpmn.PythonScriptEngine import PythonScriptEngine
import json

# 获取日志记录器
logger = logging.getLogger(__name__)


class SpiffWorkflowClient:
    """
    SpiffWorkflow 客户端类
    
    封装 SpiffWorkflow 工作流引擎的所有操作
    提供简单易用的 API 接口供 Django 视图调用
    
    属性:
        process_dir (Path): BPMN 流程文件目录
        serializer (BpmnWorkflowSerializer): 工作流序列化器
        specs_cache (dict): 流程规范缓存
    """
    
    def __init__(self):
        """
        初始化 SpiffWorkflow 客户端
        
        主要完成：
        1. 加载 BPMN 流程文件目录配置
        2. 初始化序列化器
        3. 初始化流程规范缓存
        """
        # ========== 加载 BPMN 目录配置 ==========
        process_dir_env = os.getenv('BPMN_PROCESS_DIR', '../process_models')
        self.process_dir = Path(process_dir_env)
        
        if not self.process_dir.is_absolute():
            from django.conf import settings
            self.process_dir = (settings.BASE_DIR.parent / process_dir_env).resolve()
        
        logger.info(f"BPMN 流程目录: {self.process_dir}")
        
        # ========== 初始化序列化器 ==========
        self.serializer = BpmnWorkflowSerializer()
        
        # ========== 初始化流程规范缓存 ==========
        self.specs_cache = {}
    
    def _load_bpmn_spec(self, process_model_id):
        """
        加载 BPMN 流程定义
        
        Args:
            process_model_id (str): 流程模型标识符，格式如 "admin/admin"
            
        Returns:
            BpmnProcessSpec: BPMN 流程规范对象
            
        Raises:
            FileNotFoundError: 如果找不到 BPMN 文件
            ValueError: 如果 BPMN 文件中没有可用的流程定义
        """
        # 检查缓存
        if process_model_id in self.specs_cache:
            return self.specs_cache[process_model_id]
        
        # 构建 BPMN 文件路径
        parts = process_model_id.split('/')
        bpmn_file = self.process_dir / parts[0] / parts[1] / f"{parts[1]}.bpmn"
        
        if not bpmn_file.exists():
            bpmn_file = self.process_dir / parts[0] / parts[1] / f"{parts[1]}-phase1.bpmn"
        
        if not bpmn_file.exists():
            raise FileNotFoundError(f"找不到 BPMN 文件: {bpmn_file}")
        
        logger.info(f"加载 BPMN 文件: {bpmn_file}")
        
        # 解析 BPMN 文件
        parser = BpmnParser()
        with open(str(bpmn_file), 'r', encoding='utf-8') as f:
            parser.add_bpmn_xml(etree.parse(f), str(bpmn_file))
        
        # 获取流程规范
        try:
            spec = parser.get_spec(parts[1])
        except Exception:
            available_specs = list(parser.get_process_ids())
            if available_specs:
                logger.info(f"使用流程 ID: {available_specs[0]}")
                spec = parser.get_spec(available_specs[0])
            else:
                raise ValueError("BPMN 文件中没有找到可用的流程")
        
        # 缓存流程规范
        self.specs_cache[process_model_id] = spec
        
        return spec
    
    def _get_script_engine(self):
        """
        获取脚本引擎
        
        配置 BPMN 脚本任务可以使用的函数
        
        Returns:
            PythonScriptEngine: 配置好的脚本引擎
        """
        # 定义可在 BPMN 脚本中使用的函数
        script_env = {
            'get_direct_manager': self._get_direct_manager,
            'get_department_manager': self._get_department_manager,
            'get_role_members': self._get_role_members,
            'get_effective_approver': self._get_effective_approver,
        }
        
        return PythonScriptEngine(environment=script_env)
    
    def _get_direct_manager(self, employee_email):
        """
        查找直属上级
        
        Args:
            employee_email (str): 员工邮箱
            
        Returns:
            str: 直属上级邮箱，如果没有返回 None
        """
        try:
            from organization.models import Employee
            employee = Employee.objects.filter(email=employee_email).first()
            if employee and employee.direct_manager:
                return employee.direct_manager.email
        except Exception as e:
            logger.error(f"查找直属上级失败: {e}")
        return None
    
    def _get_department_manager(self, department_name):
        """
        查找部门负责人
        
        Args:
            department_name (str): 部门名称
            
        Returns:
            str: 部门负责人邮箱，如果没有返回 None
        """
        try:
            from organization.models import Department
            department = Department.objects.filter(name=department_name).first()
            if department and department.manager:
                return department.manager.email
        except Exception as e:
            logger.error(f"查找部门负责人失败: {e}")
        return None
    
    def _get_role_members(self, role_name):
        """
        查找角色成员
        
        Args:
            role_name (str): 角色名称
            
        Returns:
            list: 角色成员邮箱列表
        """
        try:
            from organization.models import Role
            role = Role.objects.filter(name=role_name).first()
            if role:
                return [emp.email for emp in role.employees.all()]
        except Exception as e:
            logger.error(f"查找角色成员失败: {e}")
        return []
    
    def _get_effective_approver(self, approver_email, workflow_context=None):
        """
        获取有效审批人（考虑代理）
        
        使用 ProxyService 进行代理人查找和权限冲突检测
        
        Args:
            approver_email (str): 原审批人邮箱
            workflow_context (dict, optional): 工作流上下文，用于权限冲突检测
            
        Returns:
            str: 有效审批人邮箱（如果有代理返回代理人，否则返回原审批人）
        """
        try:
            from leave_api.services.proxy_service import ProxyService
            
            proxy_service = ProxyService()
            result = proxy_service.get_effective_approver(approver_email, workflow_context)
            
            # 记录代理信息
            if result['is_proxy']:
                logger.info(
                    f"使用代理人: {approver_email} -> {result['effective_approver']}"
                )
            
            if result['conflict_detected']:
                logger.warning(
                    f"检测到权限冲突，已升级: {approver_email} -> {result['escalated_to']}"
                )
            
            return result['effective_approver']
            
        except Exception as e:
            logger.error(f"查找有效审批人失败: {e}", exc_info=True)
            # 出错时返回原审批人
            return approver_email
    
    def start_process(self, process_model_id, variables=None):
        """
        启动工作流实例
        
        Args:
            process_model_id (str): 流程模型标识符
            variables (dict, optional): 流程变量
            
        Returns:
            dict: 包含 id, status, process_model_id, workflow_state, ready_tasks 的字典
        """
        try:
            # 加载流程定义
            spec = self._load_bpmn_spec(process_model_id)
            
            # 创建工作流实例（使用脚本引擎）
            workflow = BpmnWorkflow(spec, script_engine=self._get_script_engine())
            
            # 设置流程变量
            if variables:
                workflow.data.update(variables)
            
            # 生成实例 ID
            instance_id = str(uuid.uuid4())
            
            # 执行工作流
            workflow.do_engine_steps()
            
            # 序列化工作流状态
            workflow_state = self.serialize_workflow(workflow)
            
            # 获取就绪的任务
            ready_tasks = []
            for task in workflow.get_ready_user_tasks():
                ready_tasks.append({
                    'id': str(task.id),
                    'name': task.task_spec.name,
                    'assigned_to': task.data.get('assigned_to'),
                    'data': task.data
                })
            
            logger.info(f"流程启动成功: {instance_id}, 就绪任务数: {len(ready_tasks)}")
            
            return {
                'id': instance_id,
                'status': 'completed' if workflow.is_completed() else 'running',
                'process_model_id': process_model_id,
                'workflow_state': workflow_state,
                'ready_tasks': ready_tasks,
                'completed': workflow.is_completed(),
                'data': workflow.data
            }
            
        except Exception as e:
            logger.error(f"启动流程失败: {e}", exc_info=True)
            return None
    
    def serialize_workflow(self, workflow):
        """
        序列化工作流状态
        
        Args:
            workflow (BpmnWorkflow): 工作流实例
            
        Returns:
            str: 序列化后的 JSON 字符串
        """
        try:
            return self.serializer.serialize_json(workflow)
        except Exception as e:
            logger.error(f"序列化工作流失败: {e}", exc_info=True)
            return None
    
    def deserialize_workflow(self, workflow_state, process_model_id):
        """
        反序列化工作流状态
        
        Args:
            workflow_state (str): 序列化的工作流状态（JSON 字符串）
            process_model_id (str): 流程模型 ID
            
        Returns:
            BpmnWorkflow: 恢复的工作流实例
        """
        try:
            # 加载流程定义
            spec = self._load_bpmn_spec(process_model_id)
            
            # 反序列化工作流
            workflow = self.serializer.deserialize_json(workflow_state)
            
            # 设置脚本引擎
            workflow.script_engine = self._get_script_engine()
            
            return workflow
        except Exception as e:
            logger.error(f"反序列化工作流失败: {e}", exc_info=True)
            return None
    
    def get_user_tasks(self, workflow_state, process_model_id, user_email=None):
        """
        获取用户待办任务
        
        Args:
            workflow_state (str): 序列化的工作流状态
            process_model_id (str): 流程模型 ID
            user_email (str, optional): 用户邮箱（用于过滤）
            
        Returns:
            list: 任务列表
        """
        try:
            # 反序列化工作流
            workflow = self.deserialize_workflow(workflow_state, process_model_id)
            if not workflow:
                return []
            
            tasks = []
            ready_tasks = workflow.get_ready_user_tasks()
            
            for task in ready_tasks:
                # 获取任务分配的审批人
                assigned_to = task.data.get('assigned_to')
                
                # 如果指定了用户邮箱，只返回分配给该用户的任务
                if user_email and assigned_to != user_email:
                    continue
                
                tasks.append({
                    'id': str(task.id),
                    'name': task.task_spec.name,
                    'task_guid': str(task.id),
                    'state': task.state,
                    'data': task.data,
                    'assigned_to': assigned_to
                })
            
            return tasks
            
        except Exception as e:
            logger.error(f"获取用户任务失败: {e}", exc_info=True)
            return []
    
    def complete_task(self, workflow_state, process_model_id, task_guid, data=None):
        """
        完成任务
        
        Args:
            workflow_state (str): 序列化的工作流状态
            process_model_id (str): 流程模型 ID
            task_guid (str): 任务 GUID
            data (dict, optional): 任务数据
            
        Returns:
            dict: 包含 success, status, completed, workflow_state, ready_tasks, data 的字典
        """
        try:
            # 反序列化工作流
            workflow = self.deserialize_workflow(workflow_state, process_model_id)
            if not workflow:
                return None
            
            # 查找任务
            task = None
            for ready_task in workflow.get_ready_user_tasks():
                if str(ready_task.id) == task_guid:
                    task = ready_task
                    break
            
            if not task:
                logger.error(f"找不到任务: {task_guid}")
                return None
            
            # 更新任务数据
            if data:
                task.data.update(data)
            
            # 完成任务
            task.complete()
            
            # 继续执行工作流
            workflow.do_engine_steps()
            
            # 序列化新状态
            new_workflow_state = self.serialize_workflow(workflow)
            
            # 获取就绪的任务
            ready_tasks = []
            for ready_task in workflow.get_ready_user_tasks():
                ready_tasks.append({
                    'id': str(ready_task.id),
                    'name': ready_task.task_spec.name,
                    'assigned_to': ready_task.data.get('assigned_to'),
                    'data': ready_task.data
                })
            
            logger.info(f"任务完成: {task_guid}, 新就绪任务数: {len(ready_tasks)}")
            
            return {
                'success': True,
                'status': 'completed' if workflow.is_completed() else 'running',
                'completed': workflow.is_completed(),
                'workflow_state': new_workflow_state,
                'data': workflow.data,
                'ready_tasks': ready_tasks
            }
            
        except Exception as e:
            logger.error(f"完成任务失败: {e}", exc_info=True)
            return None
    
    def is_workflow_completed(self, workflow_state, process_model_id):
        """
        检查工作流是否完成
        
        Args:
            workflow_state (str): 序列化的工作流状态
            process_model_id (str): 流程模型 ID
            
        Returns:
            bool: 是否完成
        """
        try:
            workflow = self.deserialize_workflow(workflow_state, process_model_id)
            if workflow:
                return workflow.is_completed()
        except Exception as e:
            logger.error(f"检查工作流状态失败: {e}", exc_info=True)
        return False


# ========== 全局单例 ==========
spiff_client = SpiffWorkflowClient()
