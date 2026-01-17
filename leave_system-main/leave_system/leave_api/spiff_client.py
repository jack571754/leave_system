"""
SpiffWorkflow 客户端模块

这个模块封装了 SpiffWorkflow 工作流引擎的所有操作
是 Django 与 SpiffWorkflow 集成的核心组件

主要功能：
1. 加载和解析 BPMN 流程定义文件
2. 启动工作流实例
3. 查询待办任务
4. 完成任务并继续执行工作流
5. 查询工作流实例状态

注意事项：
- 当前实现将工作流实例存储在内存中
- 生产环境应该实现持久化（存储到数据库）
- 重启服务后内存中的工作流实例会丢失
"""

import os
import logging
import uuid
from pathlib import Path
from lxml import etree
from SpiffWorkflow.bpmn.workflow import BpmnWorkflow
from SpiffWorkflow.bpmn.parser.BpmnParser import BpmnParser
from SpiffWorkflow.bpmn.serializer.workflow import BpmnWorkflowSerializer
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
        workflow_instances (dict): 工作流实例存储（内存）
            格式: {instance_id: {'workflow': BpmnWorkflow, 'status': str, ...}}
    """
    
    def __init__(self):
        """
        初始化 SpiffWorkflow 客户端
        
        主要完成：
        1. 加载 BPMN 流程文件目录配置
        2. 初始化工作流实例存储
        """
        # ========== 加载 BPMN 目录配置 ==========
        # 从环境变量获取 BPMN 文件目录，默认为 '../process_models'
        process_dir_env = os.getenv('BPMN_PROCESS_DIR', '../process_models')
        self.process_dir = Path(process_dir_env)
        
        # 如果是相对路径，转换为绝对路径
        if not self.process_dir.is_absolute():
            from django.conf import settings
            # 相对于 Django 项目根目录（leave_system/）
            # 例如: leave_system/../process_models -> /path/to/process_models
            self.process_dir = (settings.BASE_DIR.parent / process_dir_env).resolve()
        
        logger.info(f"BPMN 流程目录: {self.process_dir}")
        
        # ========== 初始化工作流实例存储 ==========
        # 使用字典存储所有活动的工作流实例
        # key: instance_id (UUID字符串)
        # value: {
        #     'workflow': BpmnWorkflow 对象,
        #     'process_model_id': 流程模型 ID,
        #     'status': 'running' 或 'completed'
        # }
        # 
        # 注意：这是内存存储，重启后会丢失
        # 生产环境应该序列化后存储到数据库
        self.workflow_instances = {}
    
    def _load_bpmn_spec(self, process_model_id):
        """
        加载 BPMN 流程定义
        
        这是一个私有方法，用于从 BPMN 文件加载流程定义
        
        文件路径规则：
        - process_model_id 格式: "组/模型"，例如 "admin/admin"
        - 对应文件路径: {BPMN_PROCESS_DIR}/admin/admin/admin.bpmn
        
        Args:
            process_model_id (str): 流程模型标识符，格式如 "admin/admin"
            
        Returns:
            BpmnProcessSpec: BPMN 流程规范对象，包含流程定义的所有信息
            
        Raises:
            FileNotFoundError: 如果找不到 BPMN 文件
            ValueError: 如果 BPMN 文件中没有可用的流程定义
        """
        # ========== 构建 BPMN 文件路径 ==========
        # 将 "admin/admin" 分割为 ['admin', 'admin']
        parts = process_model_id.split('/')
        
        # 构建文件路径: process_models/admin/admin/admin.bpmn
        bpmn_file = self.process_dir / parts[0] / parts[1] / f"{parts[1]}.bpmn"
        
        # 如果主文件不存在，尝试查找 phase1 版本
        if not bpmn_file.exists():
            bpmn_file = self.process_dir / parts[0] / parts[1] / f"{parts[1]}-phase1.bpmn"
        
        # 检查文件是否存在
        if not bpmn_file.exists():
            raise FileNotFoundError(f"找不到 BPMN 文件: {bpmn_file}")
        
        logger.info(f"加载 BPMN 文件: {bpmn_file}")
        
        # ========== 解析 BPMN 文件 ==========
        # 创建 BPMN 解析器
        parser = BpmnParser()
        
        # 使用 UTF-8 编码打开文件，避免编码问题
        # 使用 lxml 解析 XML 格式的 BPMN 文件
        with open(str(bpmn_file), 'r', encoding='utf-8') as f:
            parser.add_bpmn_xml(etree.parse(f), str(bpmn_file))
        
        # ========== 获取流程规范 ==========
        # 尝试使用模型名称获取流程规范
        try:
            spec = parser.get_spec(parts[1])
        except Exception:
            # 如果找不到，可能是流程 ID 与文件名不匹配
            # 尝试获取第一个可用的流程
            available_specs = list(parser.get_process_ids())
            if available_specs:
                logger.info(f"使用流程 ID: {available_specs[0]}")
                spec = parser.get_spec(available_specs[0])
            else:
                raise ValueError("BPMN 文件中没有找到可用的流程")
        
        return spec
    
    def start_process(self, process_model_id, variables=None):
        """
        启动工作流实例
        
        这是启动工作流的核心方法，完成以下操作：
        1. 加载 BPMN 流程定义
        2. 创建工作流实例
        3. 设置流程变量
        4. 执行工作流直到第一个用户任务或结束
        5. 保存工作流实例到内存
        
        Args:
            process_model_id (str): 流程模型标识符，格式如 "admin/admin"
            variables (dict, optional): 流程变量字典，例如:
                {
                    'leave_request_id': 1,
                    'user_email': 'user@example.com',
                    'leave_hours': 8
                }
                这些变量可以在 BPMN 的脚本任务、条件表达式中使用
            
        Returns:
            dict: 包含以下字段的字典:
                - id (str): 工作流实例 ID（UUID）
                - status (str): 工作流状态 ('running' 或 'completed')
                - process_model_id (str): 流程模型 ID
            
            如果启动失败返回 None
            
        示例:
            result = spiff_client.start_process(
                "admin/admin",
                {'leave_request_id': 1, 'user_email': 'test@example.com'}
            )
            # result = {'id': 'xxx-xxx-xxx', 'status': 'running', ...}
        """
        try:
            # ========== 步骤 1: 加载流程定义 ==========
            spec = self._load_bpmn_spec(process_model_id)
            
            # ========== 步骤 2: 创建工作流实例 ==========
            # BpmnWorkflow 是 SpiffWorkflow 的核心类
            # 它管理工作流的执行状态和任务
            workflow = BpmnWorkflow(spec)
            
            # ========== 步骤 3: 设置流程变量 ==========
            # workflow.data 是一个字典，存储所有流程变量
            # 这些变量在整个工作流执行过程中都可以访问和修改
            if variables:
                workflow.data.update(variables)
            
            # ========== 步骤 4: 生成实例 ID ==========
            # 使用 UUID 生成唯一的实例标识符
            # 这个 ID 会保存到数据库的 process_instance_id 字段
            instance_id = str(uuid.uuid4())
            
            # ========== 步骤 5: 执行工作流 ==========
            # do_engine_steps() 会自动执行所有可以自动完成的任务
            # 例如：开始事件、脚本任务、服务任务、网关等
            # 执行会在遇到用户任务时停止，等待人工处理
            workflow.do_engine_steps()
            
            # ========== 步骤 6: 保存工作流实例 ==========
            # 将工作流实例保存到内存字典中
            self.workflow_instances[instance_id] = {
                'workflow': workflow,  # 工作流对象
                'process_model_id': process_model_id,  # 流程模型 ID
                'status': 'running' if not workflow.is_completed() else 'completed'  # 状态
            }
            
            logger.info(f"流程启动成功: {instance_id}, 状态: {self.workflow_instances[instance_id]['status']}")
            
            # 返回实例信息
            return {
                'id': instance_id,
                'status': self.workflow_instances[instance_id]['status'],
                'process_model_id': process_model_id
            }
            
        except Exception as e:
            # 捕获所有异常并记录日志
            logger.error(f"启动流程失败: {e}", exc_info=True)
            return None
    
    def get_user_tasks(self, user_id=None):
        """
        获取用户待办任务
        
        查询所有工作流实例中就绪的用户任务
        用户任务是需要人工处理的任务节点
        
        Args:
            user_id (str, optional): 用户标识符
                当前实现忽略此参数，返回所有待办任务
                未来可以根据用户 ID 过滤任务
            
        Returns:
            list: 任务列表，每个任务是一个字典:
                - id (str): 任务 ID
                - name (str): 任务名称（来自 BPMN 定义）
                - process_instance_id (str): 所属的工作流实例 ID
                - task_guid (str): 任务 GUID（用于完成任务）
                - state (str): 任务状态
                - data (dict): 任务数据（包含流程变量）
                
        示例:
            tasks = spiff_client.get_user_tasks('admin')
            # tasks = [
            #     {
            #         'id': 'task-1',
            #         'name': '审批',
            #         'process_instance_id': 'xxx-xxx',
            #         'task_guid': 'yyy-yyy',
            #         ...
            #     }
            # ]
        """
        tasks = []
        
        # 遍历所有工作流实例
        for instance_id, instance_data in self.workflow_instances.items():
            workflow = instance_data['workflow']
            
            # 获取所有就绪的用户任务
            # get_ready_user_tasks() 返回当前可以执行的用户任务列表
            ready_tasks = workflow.get_ready_user_tasks()
            
            # 将每个任务转换为字典格式
            for task in ready_tasks:
                tasks.append({
                    'id': str(task.id),
                    'name': task.task_spec.name,  # 任务名称，来自 BPMN
                    'process_instance_id': instance_id,
                    'task_guid': str(task.id),  # 任务 GUID，用于完成任务
                    'state': task.state,  # 任务状态
                    'data': task.data  # 任务数据，包含所有流程变量
                })
        
        logger.info(f"查询到 {len(tasks)} 个待办任务")
        return tasks
    
    def complete_task(self, process_instance_id, task_guid, data=None):
        """
        完成任务
        
        完成指定的用户任务并继续执行工作流
        
        执行流程：
        1. 查找工作流实例
        2. 查找指定的任务
        3. 更新任务数据
        4. 完成任务
        5. 继续执行工作流（自动执行后续的自动任务）
        6. 更新实例状态
        
        Args:
            process_instance_id (str): 工作流实例 ID
            task_guid (str): 任务 GUID
            data (dict, optional): 任务完成时提交的数据，例如:
                {
                    'approved': True,
                    'comment': '同意'
                }
                这些数据会合并到流程变量中
            
        Returns:
            dict: 任务完成结果:
                - success (bool): 是否成功
                - status (str): 工作流状态
                - completed (bool): 工作流是否完全结束
            
            如果失败返回 None
            
        示例:
            result = spiff_client.complete_task(
                'xxx-xxx-xxx',
                'yyy-yyy-yyy',
                {'approved': True, 'comment': '同意'}
            )
            # result = {'success': True, 'status': 'running', 'completed': False}
        """
        try:
            # ========== 步骤 1: 查找工作流实例 ==========
            if process_instance_id not in self.workflow_instances:
                logger.error(f"找不到流程实例: {process_instance_id}")
                return None
            
            instance_data = self.workflow_instances[process_instance_id]
            workflow = instance_data['workflow']
            
            # ========== 步骤 2: 查找任务 ==========
            # 在所有就绪的用户任务中查找指定的任务
            task = None
            for ready_task in workflow.get_ready_user_tasks():
                if str(ready_task.id) == task_guid:
                    task = ready_task
                    break
            
            if not task:
                logger.error(f"找不到任务: {task_guid}")
                return None
            
            # ========== 步骤 3: 更新任务数据 ==========
            # 将提交的数据合并到任务数据中
            # 这些数据会成为流程变量，可以在后续节点中使用
            if data:
                task.data.update(data)
            
            # ========== 步骤 4: 完成任务 ==========
            # task.complete() 标记任务为完成状态
            task.complete()
            
            # ========== 步骤 5: 继续执行工作流 ==========
            # do_engine_steps() 会自动执行后续的所有自动任务
            # 直到遇到下一个用户任务或工作流结束
            workflow.do_engine_steps()
            
            # ========== 步骤 6: 更新实例状态 ==========
            # 检查工作流是否完全结束
            instance_data['status'] = 'completed' if workflow.is_completed() else 'running'
            
            logger.info(f"任务完成: {task_guid}, 流程状态: {instance_data['status']}")
            
            return {
                'success': True,
                'status': instance_data['status'],
                'completed': workflow.is_completed()
            }
            
        except Exception as e:
            logger.error(f"完成任务失败: {e}", exc_info=True)
            return None
    
    def get_process_instance(self, process_instance_id):
        """
        查询流程实例详情
        
        获取指定工作流实例的详细信息
        
        Args:
            process_instance_id (str): 流程实例 ID
            
        Returns:
            dict: 流程实例信息:
                - id (str): 实例 ID
                - status (str): 状态
                - process_model_id (str): 流程模型 ID
                - data (dict): 流程变量
                - is_completed (bool): 是否完成
            
            如果找不到返回 None
            
        示例:
            instance = spiff_client.get_process_instance('xxx-xxx-xxx')
            # instance = {
            #     'id': 'xxx-xxx-xxx',
            #     'status': 'running',
            #     'data': {'leave_request_id': 1, ...},
            #     'is_completed': False
            # }
        """
        if process_instance_id not in self.workflow_instances:
            return None
        
        instance_data = self.workflow_instances[process_instance_id]
        workflow = instance_data['workflow']
        
        return {
            'id': process_instance_id,
            'status': instance_data['status'],
            'process_model_id': instance_data['process_model_id'],
            'data': workflow.data,  # 所有流程变量
            'is_completed': workflow.is_completed()
        }


# ========== 全局单例 ==========
# 创建全局的 SpiffWorkflow 客户端实例
# 在整个 Django 应用中共享同一个实例
# 这样可以保持工作流实例在内存中的一致性
spiff_client = SpiffWorkflowClient()
