# 设计文档：中国式复杂审批系统

## 概述

本设计文档描述了一个基于 Django + SpiffWorkflow 的企业级复杂审批系统的技术架构和实现方案。系统采用单体架构，SpiffWorkflow 作为工作流引擎库集成在 Django 应用中，负责流程编排和执行。Django 负责业务逻辑、数据存储、用户界面和工作流管理。

**设计决策：集成架构 vs 微服务架构**

我们选择将 SpiffWorkflow 作为 Python 库直接集成到 Django 应用中，而不是使用独立的 SpiffArena 微服务。这个决策基于以下考虑：

1. **简化部署**：单体架构减少了部署复杂度，无需管理多个服务和网络通信
2. **降低延迟**：进程内调用比 HTTP API 调用更快，提升系统响应速度
3. **事务一致性**：业务数据和工作流状态在同一数据库中，更容易保证事务一致性
4. **开发效率**：减少了 API 接口设计和维护成本，简化了错误处理
5. **成本效益**：对于中小规模部署，单体架构的资源利用率更高

### 核心设计原则

1. **关注点分离**：Django 处理业务数据，SpiffWorkflow 处理流程逻辑
2. **库集成**：SpiffWorkflow 作为 Python 库集成在 Django 中
3. **事件驱动**：使用 Django 信号机制实现工作流事件处理
4. **幂等性**：所有状态更新操作支持幂等性，确保数据一致性
5. **可扩展性**：支持动态配置审批流程，无需修改代码

### 技术栈

- **后端框架**：Django 4.x + Django REST Framework
- **工作流引擎**：SpiffWorkflow (Python BPMN 2.0 库)
- **数据库**：PostgreSQL (生产环境) / SQLite (开发环境)
- **缓存**：Redis (用于会话、任务队列)
- **任务队列**：Celery (用于异步任务和定时任务)
- **前端**：Vue.js 3 + Element Plus (可选，也可使用简单的 HTML/JavaScript)

## 架构

### 系统架构图

```
┌─────────────────────────────────────────────────────────────┐
│                         用户界面层                            │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐      │
│  │  申请人界面   │  │  审批人界面   │  │  管理员界面   │      │
│  └──────────────┘  └──────────────┘  └──────────────┘      │
└─────────────────────────────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────┐
│                      Django 应用层                            │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐      │
│  │  REST API    │  │  业务逻辑层   │  │  通知系统     │      │
│  └──────────────┘  └──────────────┘  └──────────────┘      │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐      │
│  │  数据访问层   │  │  权限管理     │  │  审批历史     │      │
│  └──────────────┘  └──────────────┘  └──────────────┘      │
│  ┌──────────────────────────────────────────────────┐      │
│  │         SpiffWorkflow 工作流引擎 (集成库)         │      │
│  │  ┌────────────┐  ┌────────────┐  ┌────────────┐ │      │
│  │  │ BPMN 引擎  │  │ 流程实例   │  │ 任务管理   │ │      │
│  │  └────────────┘  └────────────┘  └────────────┘ │      │
│  └──────────────────────────────────────────────────┘      │
└─────────────────────────────────────────────────────────────┘
                            │
                            ▼
                  ┌──────────────────┐
                  │   PostgreSQL     │
                  │   数据库         │
                  │  - 业务数据      │
                  │  - 工作流状态    │
                  └──────────────────┘
                            │
                            ▼
                  ┌──────────────────┐
                  │   Redis 缓存     │
                  │  - 会话          │
                  │  - 任务队列      │
                  └──────────────────┘
```


### 集成流程

**设计决策：事件驱动架构**

我们使用 Django 信号机制来处理工作流事件，而不是 HTTP 回调。这样可以：
- 在同一进程内同步处理事件，避免网络延迟
- 利用数据库事务保证业务数据和工作流状态的一致性
- 简化错误处理和重试逻辑

#### 1. 流程启动流程

```
申请人提交申请
    ↓
Django 创建 LeaveRequest 记录
    ↓
Django 使用 SpiffWorkflow 启动流程实例
    ↓
SpiffWorkflow 返回 workflow_instance_id
    ↓
Django 保存 workflow_instance_id 到 LeaveRequest
    ↓
SpiffWorkflow 开始执行 BPMN 流程
    ↓
Django 信号处理器更新业务状态
```

#### 2. 任务查询流程

```
审批人登录系统
    ↓
Django 通过 SpiffWorkflow 查询用户的待办任务
    ↓
SpiffWorkflow 返回该用户的待办任务列表
    ↓
Django 渲染任务列表到前端
```

#### 3. 任务完成流程

```
审批人提交审批意见
    ↓
Django 验证审批权限
    ↓
Django 通过 SpiffWorkflow 完成任务
    ↓
SpiffWorkflow 推进流程并触发事件
    ↓
Django 信号处理器接收事件
    ↓
Django 更新 LeaveRequest 状态
    ↓
Django 发送通知给相关人员
```

## 组件和接口

### Django 端组件

#### 1. 数据模型 (Models)

##### Department (部门)
```python
class Department(models.Model):
    name = models.CharField(max_length=100)
    parent = models.ForeignKey('self', null=True, blank=True, on_delete=models.CASCADE)
    manager = models.ForeignKey('Employee', null=True, blank=True, on_delete=models.SET_NULL)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
```


##### Employee (员工)
```python
class Employee(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    employee_id = models.CharField(max_length=50, unique=True)
    department = models.ForeignKey(Department, on_delete=models.CASCADE)
    position = models.CharField(max_length=100)
    level = models.IntegerField()  # 职级：1-10
    direct_manager = models.ForeignKey('self', null=True, blank=True, on_delete=models.SET_NULL)
    email = models.EmailField()
    phone = models.CharField(max_length=20)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
```

##### Role (角色)
```python
class Role(models.Model):
    name = models.CharField(max_length=50, unique=True)
    description = models.TextField()
    employees = models.ManyToManyField(Employee, related_name='roles')
    created_at = models.DateTimeField(auto_now_add=True)
```

##### LeaveRequest (请假申请)
```python
class LeaveRequest(models.Model):
    STATUS_CHOICES = [
        ('draft', '草稿'),
        ('pending', '审批中'),
        ('approved', '已批准'),
        ('rejected', '已拒绝'),
        ('cancelled', '已取消'),
    ]
    
    applicant = models.ForeignKey(Employee, on_delete=models.CASCADE, related_name='leave_requests')
    leave_type = models.CharField(max_length=50)  # 年假、病假、事假等
    start_date = models.DateField()
    end_date = models.DateField()
    duration = models.DecimalField(max_digits=5, decimal_places=1)  # 天数
    reason = models.TextField()
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='draft')
    
    # SpiffWorkflow 集成字段
    workflow_instance_id = models.CharField(max_length=100, null=True, blank=True)
    workflow_spec_name = models.CharField(max_length=100, null=True, blank=True)
    workflow_state = models.JSONField(null=True, blank=True)  # 序列化的工作流状态
    
    # 审批相关
    current_approver = models.ForeignKey(Employee, null=True, blank=True, on_delete=models.SET_NULL, related_name='pending_approvals')
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    submitted_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)
```


##### ApprovalHistory (审批历史)
```python
class ApprovalHistory(models.Model):
    ACTION_CHOICES = [
        ('submit', '提交'),
        ('approve', '批准'),
        ('reject', '拒绝'),
        ('return', '退回'),
        ('add_sign', '加签'),
        ('transfer', '转签'),
        ('cancel', '取消'),
    ]
    
    leave_request = models.ForeignKey(LeaveRequest, on_delete=models.CASCADE, related_name='history')
    action = models.CharField(max_length=20, choices=ACTION_CHOICES)
    operator = models.ForeignKey(Employee, on_delete=models.CASCADE)
    operator_role = models.CharField(max_length=50)  # 操作时的角色
    comment = models.TextField(blank=True)
    
    # 代理信息
    is_proxy = models.BooleanField(default=False)
    proxy_for = models.ForeignKey(Employee, null=True, blank=True, on_delete=models.SET_NULL, related_name='proxy_actions')
    
    # SpiffArena 任务信息
    task_id = models.CharField(max_length=100, null=True, blank=True)
    task_name = models.CharField(max_length=100, null=True, blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
```

##### ApprovalProxy (代理设置)
```python
class ApprovalProxy(models.Model):
    principal = models.ForeignKey(Employee, on_delete=models.CASCADE, related_name='proxy_settings')
    proxy = models.ForeignKey(Employee, on_delete=models.CASCADE, related_name='proxy_for_others')
    start_date = models.DateTimeField()
    end_date = models.DateTimeField()
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        unique_together = ['principal', 'start_date', 'end_date']
```

##### CCRecord (抄送记录)
```python
class CCRecord(models.Model):
    leave_request = models.ForeignKey(LeaveRequest, on_delete=models.CASCADE, related_name='cc_records')
    cc_to = models.ForeignKey(Employee, on_delete=models.CASCADE)
    cc_by = models.ForeignKey(Employee, on_delete=models.CASCADE, related_name='cc_sent')
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    read_at = models.DateTimeField(null=True, blank=True)
```

##### Notification (通知)
```python
class Notification(models.Model):
    TYPE_CHOICES = [
        ('task_assigned', '任务分配'),
        ('task_completed', '任务完成'),
        ('request_approved', '申请批准'),
        ('request_rejected', '申请拒绝'),
        ('request_returned', '申请退回'),
        ('timeout_reminder', '超时提醒'),
        ('urge', '催办'),
    ]
    
    recipient = models.ForeignKey(Employee, on_delete=models.CASCADE, related_name='notifications')
    notification_type = models.CharField(max_length=30, choices=TYPE_CHOICES)
    title = models.CharField(max_length=200)
    content = models.TextField()
    leave_request = models.ForeignKey(LeaveRequest, null=True, blank=True, on_delete=models.CASCADE)
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    read_at = models.DateTimeField(null=True, blank=True)
```


##### ApprovalRule (审批规则)
```python
class ApprovalRule(models.Model):
    name = models.CharField(max_length=100)
    description = models.TextField()
    priority = models.IntegerField(default=0)  # 优先级，数字越大优先级越高
    is_active = models.BooleanField(default=True)
    
    # 条件字段
    leave_type = models.CharField(max_length=50, null=True, blank=True)
    min_duration = models.DecimalField(max_digits=5, decimal_places=1, null=True, blank=True)
    max_duration = models.DecimalField(max_digits=5, decimal_places=1, null=True, blank=True)
    department = models.ForeignKey(Department, null=True, blank=True, on_delete=models.CASCADE)
    min_level = models.IntegerField(null=True, blank=True)
    max_level = models.IntegerField(null=True, blank=True)
    
    # 流程配置
    workflow_spec_name = models.CharField(max_length=100)  # SpiffWorkflow 中的流程规范名称
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
```

##### WebhookLog (事件日志)
```python
class WorkflowEventLog(models.Model):
    """工作流事件日志 - 记录所有工作流事件以支持审计和故障排查"""
    STATUS_CHOICES = [
        ('pending', '待处理'),
        ('success', '成功'),
        ('failed', '失败'),
    ]
    
    workflow_instance_id = models.CharField(max_length=100)
    task_id = models.CharField(max_length=100, null=True, blank=True)
    event_type = models.CharField(max_length=50)  # task_completed, workflow_completed, etc.
    event_data = models.JSONField()
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    error_message = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    processed_at = models.DateTimeField(null=True, blank=True)
```

#### 2. REST API 接口

##### 申请管理 API

```python
# 创建请假申请
POST /api/leave-requests/
{
    "leave_type": "annual",
    "start_date": "2024-02-01",
    "end_date": "2024-02-03",
    "duration": 3.0,
    "reason": "家庭事务"
}

# 提交请假申请（启动流程）
POST /api/leave-requests/{id}/submit/
Response: {
    "id": 1,
    "status": "pending",
    "process_instance_id": "abc123"
}

# 查询我的申请
GET /api/leave-requests/my-requests/
Response: [
    {
        "id": 1,
        "leave_type": "annual",
        "start_date": "2024-02-01",
        "end_date": "2024-02-03",
        "duration": 3.0,
        "status": "pending",
        "current_approver": "张三"
    }
]

# 取消申请
POST /api/leave-requests/{id}/cancel/
```


##### 审批任务 API

```python
# 查询我的待办任务
GET /api/approval-tasks/my-tasks/
Response: [
    {
        "task_id": "task_123",
        "leave_request_id": 1,
        "applicant": "李四",
        "leave_type": "annual",
        "duration": 3.0,
        "reason": "家庭事务",
        "submitted_at": "2024-01-15T10:00:00Z",
        "task_name": "部门主管审批"
    }
]

# 批准任务
POST /api/approval-tasks/{task_id}/approve/
{
    "comment": "同意"
}

# 拒绝任务
POST /api/approval-tasks/{task_id}/reject/
{
    "comment": "不同意，理由不充分"
}

# 退回任务
POST /api/approval-tasks/{task_id}/return/
{
    "return_to": "applicant",  # 或 "previous"
    "comment": "请补充详细理由"
}

# 加签
POST /api/approval-tasks/{task_id}/add-sign/
{
    "add_sign_to": [employee_id1, employee_id2],
    "comment": "需要额外审批"
}

# 转签
POST /api/approval-tasks/{task_id}/transfer/
{
    "transfer_to": employee_id,
    "comment": "转给其他人处理"
}
```

##### 组织架构 API

```python
# 部门管理
GET /api/departments/
POST /api/departments/
PUT /api/departments/{id}/
DELETE /api/departments/{id}/

# 员工管理
GET /api/employees/
POST /api/employees/
PUT /api/employees/{id}/
DELETE /api/employees/{id}/

# 角色管理
GET /api/roles/
POST /api/roles/
PUT /api/roles/{id}/
DELETE /api/roles/{id}/
```

##### 代理设置 API

```python
# 设置代理
POST /api/proxy-settings/
{
    "proxy_id": employee_id,
    "start_date": "2024-02-01T00:00:00Z",
    "end_date": "2024-02-10T23:59:59Z"
}

# 查询我的代理设置
GET /api/proxy-settings/my-settings/

# 取消代理
DELETE /api/proxy-settings/{id}/
```

#### 3. SpiffWorkflow 集成服务

**设计决策：工作流状态持久化**

SpiffWorkflow 支持将工作流状态序列化为 JSON，我们将其存储在 LeaveRequest.workflow_state 字段中。这样可以：
- 在系统重启后恢复工作流状态
- 支持工作流的暂停和恢复
- 便于调试和故障排查

```python
from SpiffWorkflow.bpmn.workflow import BpmnWorkflow
from SpiffWorkflow.bpmn.parser.BpmnParser import BpmnParser
from SpiffWorkflow.bpmn.serializer.workflow import BpmnWorkflowSerializer
import json

class WorkflowService:
    """SpiffWorkflow 工作流服务"""
    
    def __init__(self):
        self.parser = BpmnParser()
        self.serializer = BpmnWorkflowSerializer()
        self._load_workflow_specs()
    
    def _load_workflow_specs(self):
        """加载所有 BPMN 流程规范"""
        self.specs = {}
        bpmn_files = {
            'basic_approval': 'workflows/basic_approval.bpmn',
            'multi_level_approval': 'workflows/multi_level_approval.bpmn',
            'countersign_approval': 'workflows/countersign_approval.bpmn',
            'or_sign_approval': 'workflows/or_sign_approval.bpmn',
            'parallel_branches': 'workflows/parallel_branches.bpmn',
        }
        
        for name, path in bpmn_files.items():
            self.parser.add_bpmn_file(path)
            self.specs[name] = self.parser.get_spec(name)
    
    def start_workflow(self, spec_name: str, data: dict) -> BpmnWorkflow:
        """启动工作流实例"""
        spec = self.specs.get(spec_name)
        if not spec:
            raise ValueError(f"未找到工作流规范: {spec_name}")
        
        workflow = BpmnWorkflow(spec, script_engine=self._get_script_engine())
        
        # 设置初始数据
        workflow.data.update(data)
        
        # 执行到第一个用户任务
        workflow.do_engine_steps()
        
        return workflow
    
    def get_user_tasks(self, workflow: BpmnWorkflow, user_id: str) -> list:
        """查询用户待办任务"""
        tasks = []
        for task in workflow.get_ready_user_tasks():
            # 检查任务是否分配给该用户
            assigned_to = task.data.get('assigned_to')
            if assigned_to == user_id:
                tasks.append({
                    'id': task.id,
                    'name': task.task_spec.name,
                    'description': task.task_spec.description,
                    'data': task.data
                })
        return tasks
    
    def complete_task(self, workflow: BpmnWorkflow, task_id: str, data: dict) -> BpmnWorkflow:
        """完成任务"""
        task = workflow.get_task_from_id(task_id)
        if not task:
            raise ValueError(f"未找到任务: {task_id}")
        
        # 更新任务数据
        task.data.update(data)
        
        # 完成任务
        workflow.complete_task_from_id(task_id)
        
        # 执行到下一个用户任务或结束
        workflow.do_engine_steps()
        
        return workflow
    
    def serialize_workflow(self, workflow: BpmnWorkflow) -> str:
        """序列化工作流状态"""
        return self.serializer.serialize_json(workflow)
    
    def deserialize_workflow(self, workflow_json: str) -> BpmnWorkflow:
        """反序列化工作流状态"""
        return self.serializer.deserialize_json(workflow_json)
    
    def is_workflow_completed(self, workflow: BpmnWorkflow) -> bool:
        """检查工作流是否完成"""
        return workflow.is_completed()
    
    def _get_script_engine(self):
        """获取脚本引擎（用于 BPMN 脚本任务）"""
        from SpiffWorkflow.bpmn.script_engine import PythonScriptEngine
        
        # 定义可在 BPMN 脚本中使用的函数
        script_env = {
            'get_direct_manager': self._get_direct_manager,
            'get_department_manager': self._get_department_manager,
            'get_role_members': self._get_role_members,
            'get_effective_approver': self._get_effective_approver,
        }
        
        return PythonScriptEngine(environment=script_env)
    
    def _get_direct_manager(self, applicant_id: str) -> str:
        """查找直属上级"""
        from approval.models import Employee
        employee = Employee.objects.get(employee_id=applicant_id)
        if employee.direct_manager:
            return employee.direct_manager.employee_id
        return None
    
    def _get_department_manager(self, department_id: int) -> str:
        """查找部门负责人"""
        from approval.models import Department
        department = Department.objects.get(id=department_id)
        if department.manager:
            return department.manager.employee_id
        return None
    
    def _get_role_members(self, role_name: str) -> list:
        """查找角色成员"""
        from approval.models import Role
        role = Role.objects.get(name=role_name)
        return [emp.employee_id for emp in role.employees.all()]
    
    def _get_effective_approver(self, approver_id: str) -> str:
        """获取有效审批人（考虑代理）"""
        from approval.models import ApprovalProxy, Employee
        from django.utils import timezone
        
        now = timezone.now()
        proxy = ApprovalProxy.objects.filter(
            principal__employee_id=approver_id,
            is_active=True,
            start_date__lte=now,
            end_date__gte=now
        ).first()
        
        if proxy:
            return proxy.proxy.employee_id
        return approver_id
```


#### 4. 业务逻辑服务

```python
from django.db import transaction
from django.utils import timezone
import uuid

class ApprovalService:
    """审批业务逻辑服务"""
    
    def __init__(self):
        self.workflow_service = WorkflowService()
    
    @transaction.atomic
    def submit_leave_request(self, leave_request: LeaveRequest) -> LeaveRequest:
        """提交请假申请"""
        # 1. 根据规则选择流程规范
        workflow_spec_name = self._select_workflow_spec(leave_request)
        
        # 2. 准备流程变量
        workflow_data = {
            "leave_request_id": leave_request.id,
            "applicant_id": leave_request.applicant.employee_id,
            "department_id": leave_request.applicant.department.id,
            "duration": float(leave_request.duration),
            "leave_type": leave_request.leave_type,
            "level": leave_request.applicant.level,
        }
        
        # 3. 启动 SpiffWorkflow 流程
        workflow = self.workflow_service.start_workflow(workflow_spec_name, workflow_data)
        
        # 4. 更新申请状态
        leave_request.workflow_instance_id = str(uuid.uuid4())
        leave_request.workflow_spec_name = workflow_spec_name
        leave_request.workflow_state = self.workflow_service.serialize_workflow(workflow)
        leave_request.status = 'pending'
        leave_request.submitted_at = timezone.now()
        leave_request.save()
        
        # 5. 记录历史
        ApprovalHistory.objects.create(
            leave_request=leave_request,
            action='submit',
            operator=leave_request.applicant,
            operator_role='申请人'
        )
        
        # 6. 处理工作流事件
        self._handle_workflow_events(leave_request, workflow)
        
        return leave_request
    
    def _select_workflow_spec(self, leave_request: LeaveRequest) -> str:
        """根据规则选择流程规范"""
        rules = ApprovalRule.objects.filter(is_active=True).order_by('-priority')
        
        for rule in rules:
            if self._match_rule(leave_request, rule):
                return rule.workflow_spec_name
        
        # 返回默认流程
        return settings.DEFAULT_WORKFLOW_SPEC
    
    def _match_rule(self, leave_request: LeaveRequest, rule: ApprovalRule) -> bool:
        """检查申请是否匹配规则"""
        # 检查请假类型
        if rule.leave_type and rule.leave_type != leave_request.leave_type:
            return False
        
        # 检查时长
        if rule.min_duration and leave_request.duration < rule.min_duration:
            return False
        if rule.max_duration and leave_request.duration > rule.max_duration:
            return False
        
        # 检查部门
        if rule.department and leave_request.applicant.department != rule.department:
            return False
        
        # 检查职级
        if rule.min_level and leave_request.applicant.level < rule.min_level:
            return False
        if rule.max_level and leave_request.applicant.level > rule.max_level:
            return False
        
        return True
    
    @transaction.atomic
    def approve_task(self, leave_request: LeaveRequest, task_id: str, 
                     approver: Employee, comment: str) -> LeaveRequest:
        """批准任务"""
        # 1. 反序列化工作流状态
        workflow = self.workflow_service.deserialize_workflow(leave_request.workflow_state)
        
        # 2. 完成任务
        task_data = {
            "action": "approve",
            "approver_id": approver.employee_id,
            "comment": comment,
            "timestamp": timezone.now().isoformat()
        }
        workflow = self.workflow_service.complete_task(workflow, task_id, task_data)
        
        # 3. 保存工作流状态
        leave_request.workflow_state = self.workflow_service.serialize_workflow(workflow)
        leave_request.save()
        
        # 4. 记录历史
        ApprovalHistory.objects.create(
            leave_request=leave_request,
            action='approve',
            operator=approver,
            operator_role='审批人',
            comment=comment,
            task_id=task_id
        )
        
        # 5. 处理工作流事件
        self._handle_workflow_events(leave_request, workflow)
        
        return leave_request
    
    def _handle_workflow_events(self, leave_request: LeaveRequest, workflow: BpmnWorkflow):
        """处理工作流事件"""
        # 检查工作流是否完成
        if self.workflow_service.is_workflow_completed(workflow):
            # 根据最终结果更新状态
            final_result = workflow.data.get('final_result', 'approved')
            leave_request.status = final_result
            leave_request.completed_at = timezone.now()
            leave_request.save()
            
            # 发送通知
            self._send_notification(leave_request, f'request_{final_result}')
        else:
            # 查找下一个待办任务并发送通知
            ready_tasks = workflow.get_ready_user_tasks()
            for task in ready_tasks:
                assigned_to = task.data.get('assigned_to')
                if assigned_to:
                    assignee = Employee.objects.get(employee_id=assigned_to)
                    self._send_task_notification(leave_request, task, assignee)
    
    def _send_notification(self, leave_request: LeaveRequest, notification_type: str):
        """发送通知"""
        from approval.services import NotificationService
        notification_service = NotificationService()
        notification_service.send_approval_result_notification(leave_request, notification_type)
    
    def _send_task_notification(self, leave_request: LeaveRequest, task, assignee: Employee):
        """发送任务通知"""
        from approval.services import NotificationService
        notification_service = NotificationService()
        notification_service.send_task_assigned_notification(
            {'leave_request_id': leave_request.id, 'task': task},
            assignee
        )
```


```python
    def reject_task(self, leave_request: LeaveRequest, task_id: str,
                    approver: Employee, comment: str) -> LeaveRequest:
        """拒绝任务"""
        # 1. 反序列化工作流状态
        workflow = self.workflow_service.deserialize_workflow(leave_request.workflow_state)
        
        # 2. 完成任务
        task_data = {
            "action": "reject",
            "approver_id": approver.employee_id,
            "comment": comment,
            "timestamp": timezone.now().isoformat()
        }
        workflow = self.workflow_service.complete_task(workflow, task_id, task_data)
        
        # 3. 保存工作流状态
        leave_request.workflow_state = self.workflow_service.serialize_workflow(workflow)
        leave_request.save()
        
        # 4. 记录历史
        ApprovalHistory.objects.create(
            leave_request=leave_request,
            action='reject',
            operator=approver,
            operator_role='审批人',
            comment=comment,
            task_id=task_id
        )
        
        # 5. 处理工作流事件
        self._handle_workflow_events(leave_request, workflow)
        
        return leave_request
    
    def return_task(self, leave_request: LeaveRequest, task_id: str,
                    approver: Employee, return_to: str, comment: str) -> LeaveRequest:
        """退回任务"""
        # 1. 反序列化工作流状态
        workflow = self.workflow_service.deserialize_workflow(leave_request.workflow_state)
        
        # 2. 完成任务
        task_data = {
            "action": "return",
            "return_to": return_to,
            "approver_id": approver.employee_id,
            "comment": comment,
            "timestamp": timezone.now().isoformat()
        }
        workflow = self.workflow_service.complete_task(workflow, task_id, task_data)
        
        # 3. 保存工作流状态
        leave_request.workflow_state = self.workflow_service.serialize_workflow(workflow)
        leave_request.save()
        
        # 4. 记录历史
        ApprovalHistory.objects.create(
            leave_request=leave_request,
            action='return',
            operator=approver,
            operator_role='审批人',
            comment=comment,
            task_id=task_id
        )
        
        # 5. 处理工作流事件
        self._handle_workflow_events(leave_request, workflow)
        
        return leave_request
```


#### 5. 通知服务

```python
class NotificationService:
    """通知服务"""
    
    def send_task_assigned_notification(self, task: dict, assignee: Employee):
        """发送任务分配通知"""
        leave_request = LeaveRequest.objects.get(id=task['leave_request_id'])
        
        # 创建站内通知
        Notification.objects.create(
            recipient=assignee,
            notification_type='task_assigned',
            title=f'新的审批任务：{leave_request.applicant.user.get_full_name()}的请假申请',
            content=f'请假类型：{leave_request.leave_type}，时长：{leave_request.duration}天',
            leave_request=leave_request
        )
        
        # 发送邮件
        self._send_email(
            to=assignee.email,
            subject='新的审批任务',
            template='task_assigned',
            context={'task': task, 'leave_request': leave_request}
        )
    
    def send_approval_result_notification(self, leave_request: LeaveRequest, result: str):
        """发送审批结果通知"""
        Notification.objects.create(
            recipient=leave_request.applicant,
            notification_type=f'request_{result}',
            title=f'您的请假申请已{result}',
            content=f'请假时间：{leave_request.start_date} 至 {leave_request.end_date}',
            leave_request=leave_request
        )
        
        self._send_email(
            to=leave_request.applicant.email,
            subject=f'请假申请{result}',
            template=f'request_{result}',
            context={'leave_request': leave_request}
        )
    
    def _send_email(self, to: str, subject: str, template: str, context: dict):
        """发送邮件"""
        from django.core.mail import send_mail
        from django.template.loader import render_to_string
        
        html_message = render_to_string(f'emails/{template}.html', context)
        send_mail(
            subject=subject,
            message='',
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[to],
            html_message=html_message,
            fail_silently=False
        )
```

### BPMN 流程设计

**设计决策：BPMN 文件管理**

BPMN 流程文件存储在 Django 项目的 `workflows/` 目录中，由 WorkflowService 在启动时加载。这样可以：
- 使用版本控制管理流程定义
- 支持流程的热更新（重启服务后生效）
- 便于流程的审查和测试

#### 1. 基础审批流程 (basic_approval.bpmn)

```xml
<?xml version="1.0" encoding="UTF-8"?>
<bpmn:definitions xmlns:bpmn="http://www.omg.org/spec/BPMN/20100524/MODEL"
                  xmlns:bpmndi="http://www.omg.org/spec/BPMN/20100524/DI"
                  xmlns:spiffworkflow="http://spiffworkflow.org/bpmn/schema/1.0/core">
  
  <bpmn:process id="basic_approval" name="基础审批流程" isExecutable="true">
    
    <!-- 开始事件 -->
    <bpmn:startEvent id="start" name="开始">
      <bpmn:outgoing>flow_to_manager</bpmn:outgoing>
    </bpmn:startEvent>
    
    <!-- 部门主管审批 -->
    <bpmn:userTask id="manager_approval" name="部门主管审批">
      <bpmn:incoming>flow_to_manager</bpmn:incoming>
      <bpmn:outgoing>flow_from_manager</bpmn:outgoing>
      
      <!-- 分配给直属上级 -->
      <bpmn:potentialOwner>
        <bpmn:resourceAssignmentExpression>
          <bpmn:formalExpression>
            {{ get_direct_manager(applicant_id) }}
          </bpmn:formalExpression>
        </bpmn:resourceAssignmentExpression>
      </bpmn:potentialOwner>
      
      <!-- 超时边界事件 -->
      <bpmn:boundaryEvent id="manager_timeout" name="超时提醒" 
                          attachedToRef="manager_approval" cancelActivity="false">
        <bpmn:timerEventDefinition>
          <bpmn:timeDuration>PT24H</bpmn:timeDuration>
        </bpmn:timerEventDefinition>
        <bpmn:outgoing>flow_to_reminder</bpmn:outgoing>
      </bpmn:boundaryEvent>
    </bpmn:userTask>
```

    
    <!-- 脚本任务：记录超时事件 -->
    <bpmn:scriptTask id="send_reminder" name="记录超时提醒">
      <bpmn:incoming>flow_to_reminder</bpmn:incoming>
      <bpmn:script>
        # 设置超时标记，由 Django 事件处理器发送通知
        timeout_occurred = True
        timeout_task_id = 'manager_approval'
      </bpmn:script>
    </bpmn:scriptTask>
    
    <!-- 审批结果网关 -->
    <bpmn:exclusiveGateway id="manager_decision" name="主管决策">
      <bpmn:incoming>flow_from_manager</bpmn:incoming>
      <bpmn:outgoing>flow_approved</bpmn:outgoing>
      <bpmn:outgoing>flow_rejected</bpmn:outgoing>
    </bpmn:exclusiveGateway>
    
    <bpmn:sequenceFlow id="flow_approved" name="批准" sourceRef="manager_decision" targetRef="set_approved">
      <bpmn:conditionExpression>action == 'approve'</bpmn:conditionExpression>
    </bpmn:sequenceFlow>
    
    <bpmn:sequenceFlow id="flow_rejected" name="拒绝" sourceRef="manager_decision" targetRef="set_rejected">
      <bpmn:conditionExpression>action == 'reject'</bpmn:conditionExpression>
    </bpmn:sequenceFlow>
    
    <!-- 脚本任务：设置批准结果 -->
    <bpmn:scriptTask id="set_approved" name="设置批准结果">
      <bpmn:incoming>flow_approved</bpmn:incoming>
      <bpmn:outgoing>flow_to_end_approved</bpmn:outgoing>
      <bpmn:script>
        final_result = 'approved'
      </bpmn:script>
    </bpmn:scriptTask>
    
    <!-- 脚本任务：设置拒绝结果 -->
    <bpmn:scriptTask id="set_rejected" name="设置拒绝结果">
      <bpmn:incoming>flow_rejected</bpmn:incoming>
      <bpmn:outgoing>flow_to_end_rejected</bpmn:outgoing>
      <bpmn:script>
        final_result = 'rejected'
      </bpmn:script>
    </bpmn:scriptTask>
          </spiffworkflow:parameters>
        </spiffworkflow:serviceTaskOperator>
      </bpmn:extensionElements>
    </bpmn:serviceTask>
    
    <!-- 结束事件 -->
    <bpmn:endEvent id="end_approved" name="批准结束">
      <bpmn:incoming>flow_to_end_approved</bpmn:incoming>
    </bpmn:endEvent>
    
    <bpmn:endEvent id="end_rejected" name="拒绝结束">
      <bpmn:incoming>flow_to_end_rejected</bpmn:incoming>
    </bpmn:endEvent>
    
  </bpmn:process>
</bpmn:definitions>
```


##### 多级审批流程 (multi_level_approval.bpmn)

该流程包含：部门主管 → 总监 → HR → 总经理

关键设计点：
- 使用条件网关根据请假时长决定是否需要更高级别审批
- 每个审批节点都有超时边界事件
- 使用 Service Task 回调 Django 更新状态

##### 会签流程 (countersign_approval.bpmn)

```xml
<!-- 会签任务示例 -->
<bpmn:userTask id="hr_countersign" name="HR会签">
  <bpmn:multiInstanceLoopCharacteristics isSequential="false">
    <bpmn:loopCardinality>{{ hr_approvers | length }}</bpmn:loopCardinality>
    <bpmn:completionCondition>
      {{ completed_count == total_count }}
    </bpmn:completionCondition>
  </bpmn:multiInstanceLoopCharacteristics>
  
  <bpmn:potentialOwner>
    <bpmn:resourceAssignmentExpression>
      <bpmn:formalExpression>
        {{ hr_approvers[loop_counter] }}
      </bpmn:formalExpression>
    </bpmn:resourceAssignmentExpression>
  </bpmn:potentialOwner>
</bpmn:userTask>
```

关键设计点：
- 使用 Multi-instance User Task 实现会签
- `isSequential="false"` 表示并行执行
- `completionCondition` 可配置为全部通过或按比例通过
- 支持一票否决机制

##### 或签流程 (or_sign_approval.bpmn)

```xml
<!-- 或签使用包容网关 -->
<bpmn:inclusiveGateway id="or_sign_gateway" name="或签网关">
  <bpmn:incoming>flow_in</bpmn:incoming>
  <bpmn:outgoing>flow_to_approver1</bpmn:outgoing>
  <bpmn:outgoing>flow_to_approver2</bpmn:outgoing>
  <bpmn:outgoing>flow_to_approver3</bpmn:outgoing>
</bpmn:inclusiveGateway>

<!-- 汇聚网关 -->
<bpmn:inclusiveGateway id="or_sign_join" name="或签汇聚">
  <bpmn:incoming>flow_from_approver1</bpmn:incoming>
  <bpmn:incoming>flow_from_approver2</bpmn:incoming>
  <bpmn:incoming>flow_from_approver3</bpmn:incoming>
  <bpmn:outgoing>flow_out</bpmn:outgoing>
</bpmn:inclusiveGateway>
```

#### 2. 多级审批流程 (multi_level_approval.bpmn)

该流程包含：部门主管 → 总监 → HR → 总经理

关键设计点：
- 使用条件网关根据请假时长决定是否需要更高级别审批
- 每个审批节点都有超时边界事件
- 使用脚本任务设置流程变量，由 Django 事件处理器处理通知

#### 3. 会签流程 (countersign_approval.bpmn)

```xml
<!-- 会签任务示例 -->
<bpmn:userTask id="hr_countersign" name="HR会签">
  <bpmn:multiInstanceLoopCharacteristics isSequential="false">
    <bpmn:loopCardinality>len(hr_approvers)</bpmn:loopCardinality>
    <bpmn:completionCondition>
      completed_count == total_count
    </bpmn:completionCondition>
  </bpmn:multiInstanceLoopCharacteristics>
  
  <bpmn:potentialOwner>
    <bpmn:resourceAssignmentExpression>
      <bpmn:formalExpression>
        hr_approvers[loop_counter]
      </bpmn:formalExpression>
    </bpmn:resourceAssignmentExpression>
  </bpmn:potentialOwner>
</bpmn:userTask>
```

关键设计点：
- 使用 Multi-instance User Task 实现会签
- `isSequential="false"` 表示并行执行
- `completionCondition` 可配置为全部通过或按比例通过
- 支持一票否决机制

#### 4. 或签流程 (or_sign_approval.bpmn)

```xml
<!-- 或签使用包容网关 -->
<bpmn:inclusiveGateway id="or_sign_gateway" name="或签网关">
  <bpmn:incoming>flow_in</bpmn:incoming>
  <bpmn:outgoing>flow_to_approver1</bpmn:outgoing>
  <bpmn:outgoing>flow_to_approver2</bpmn:outgoing>
  <bpmn:outgoing>flow_to_approver3</bpmn:outgoing>
</bpmn:inclusiveGateway>

<!-- 汇聚网关 -->
<bpmn:inclusiveGateway id="or_sign_join" name="或签汇聚">
  <bpmn:incoming>flow_from_approver1</bpmn:incoming>
  <bpmn:incoming>flow_from_approver2</bpmn:incoming>
  <bpmn:incoming>flow_from_approver3</bpmn:incoming>
  <bpmn:outgoing>flow_out</bpmn:outgoing>
</bpmn:inclusiveGateway>
```

#### 5. 多分支并行审批流程 (parallel_branches_approval.bpmn)

```xml
<!-- 并行网关分支 -->
<bpmn:parallelGateway id="parallel_split" name="并行分支">
  <bpmn:incoming>flow_in</bpmn:incoming>
  <bpmn:outgoing>flow_to_finance</bpmn:outgoing>
  <bpmn:outgoing>flow_to_hr</bpmn:outgoing>
  <bpmn:outgoing>flow_to_admin</bpmn:outgoing>
</bpmn:parallelGateway>

<!-- 财务审批分支 -->
<bpmn:userTask id="finance_approval" name="财务审批">
  <bpmn:incoming>flow_to_finance</bpmn:incoming>
  <bpmn:outgoing>flow_from_finance</bpmn:outgoing>
</bpmn:userTask>

<!-- HR审批分支 -->
<bpmn:userTask id="hr_approval" name="HR审批">
  <bpmn:incoming>flow_to_hr</bpmn:incoming>
  <bpmn:outgoing>flow_from_hr</bpmn:outgoing>
</bpmn:userTask>

<!-- 行政审批分支 -->
<bpmn:userTask id="admin_approval" name="行政审批">
  <bpmn:incoming>flow_to_admin</bpmn:incoming>
  <bpmn:outgoing>flow_from_admin</bpmn:outgoing>
</bpmn:userTask>

<!-- 并行网关汇聚 -->
<bpmn:parallelGateway id="parallel_join" name="并行汇聚">
  <bpmn:incoming>flow_from_finance</bpmn:incoming>
  <bpmn:incoming>flow_from_hr</bpmn:incoming>
  <bpmn:incoming>flow_from_admin</bpmn:incoming>
  <bpmn:outgoing>flow_out</bpmn:outgoing>
</bpmn:parallelGateway>
```

#### 6. 脚本任务使用

SpiffWorkflow 支持在流程中使用 Python 脚本任务来处理复杂逻辑。这些函数在 WorkflowService 的脚本引擎中定义：

```python
# 在 BPMN 脚本任务中可用的函数已在 WorkflowService._get_script_engine() 中定义

# 示例：在 BPMN 中使用脚本任务分配审批人
<bpmn:scriptTask id="assign_approver" name="分配审批人">
  <bpmn:script>
    # 获取直属上级
    manager_id = get_direct_manager(applicant_id)
    
    # 检查代理人
    assigned_to = get_effective_approver(manager_id)
  </bpmn:script>
</bpmn:scriptTask>

# 示例：在 BPMN 中使用脚本任务处理会签结果
<bpmn:scriptTask id="check_countersign" name="检查会签结果">
  <bpmn:script>
    # 统计批准数量
    approve_count = sum(1 for result in countersign_results if result == 'approve')
    total_count = len(countersign_results)
    
    # 判断是否通过（70%通过即可）
    if approve_count / total_count >= 0.7:
        countersign_passed = True
    else:
        countersign_passed = False
  </bpmn:script>
</bpmn:scriptTask>
```


## 数据模型

### 实体关系图 (ERD)

```
┌─────────────┐       ┌─────────────┐       ┌─────────────┐
│ Department  │◄──────│  Employee   │──────►│    Role     │
│             │       │             │       │             │
│ - id        │       │ - id        │       │ - id        │
│ - name      │       │ - user_id   │       │ - name      │
│ - parent_id │       │ - dept_id   │       │             │
│ - manager_id│       │ - level     │       └─────────────┘
└─────────────┘       │ - manager_id│
                      └─────────────┘
                            │
                            │ 1:N
                            ▼
                      ┌─────────────┐
                      │LeaveRequest │
                      │             │
                      │ - id        │
                      │ - applicant │
                      │ - status    │
                      │ - process_id│
                      └─────────────┘
                            │
                            │ 1:N
                            ▼
                      ┌─────────────┐
                      │ApprovalHist │
                      │             │
                      │ - id        │
                      │ - action    │
                      │ - operator  │
                      │ - comment   │
                      └─────────────┘
```

### 关键字段说明

#### LeaveRequest.workflow_instance_id
- 类型：CharField(100)
- 用途：唯一标识工作流实例
- 重要性：这是业务数据和工作流状态的关键映射字段

#### LeaveRequest.workflow_state
- 类型：JSONField
- 用途：存储序列化的 SpiffWorkflow 工作流状态
- 重要性：用于持久化工作流状态，支持系统重启后恢复

#### ApprovalHistory.task_id
- 类型：CharField(100)
- 用途：关联 SpiffWorkflow 任务
- 重要性：用于追踪每个审批操作对应的 BPMN 任务

#### WorkflowEventLog
- 用途：记录所有工作流事件
- 重要性：用于审计和故障排查

## 错误处理

### 1. 工作流执行失败

```python
class WorkflowExecutionError(Exception):
    """工作流执行错误"""
    pass

@transaction.atomic
def execute_workflow_with_error_handling(leave_request: LeaveRequest, action: str):
    """带错误处理的工作流执行"""
    try:
        workflow = workflow_service.deserialize_workflow(leave_request.workflow_state)
        
        # 执行工作流操作
        workflow = workflow_service.complete_task(task_id, data)
        
        # 保存状态
        leave_request.workflow_state = workflow_service.serialize_workflow(workflow)
        leave_request.save()
        
    except Exception as e:
        # 记录错误日志
        WorkflowEventLog.objects.create(
            workflow_instance_id=leave_request.workflow_instance_id,
            event_type='workflow_error',
            event_data={'error': str(e)},
            status='failed',
            error_message=str(e)
        )
        
        # 回滚事务
        raise WorkflowExecutionError(f"工作流执行失败: {str(e)}")
```

### 2. 工作流状态恢复

```python
def recover_workflow_state(leave_request_id: int):
    """恢复工作流状态"""
    leave_request = LeaveRequest.objects.get(id=leave_request_id)
    
    if not leave_request.workflow_state:
        raise ValueError("工作流状态为空，无法恢复")
    
    try:
        # 反序列化工作流状态
        workflow = workflow_service.deserialize_workflow(leave_request.workflow_state)
        
        # 检查工作流状态
        if workflow_service.is_workflow_completed(workflow):
            leave_request.status = 'approved' if workflow.data.get('final_result') == 'approved' else 'rejected'
            leave_request.completed_at = timezone.now()
        else:
            leave_request.status = 'pending'
        
        leave_request.save()
        
    except Exception as e:
        raise WorkflowExecutionError(f"工作流状态恢复失败: {str(e)}")
```

### 3. 代理人权限冲突

```python
def get_effective_approver(self, approver_id: str, leave_request: LeaveRequest) -> str:
    """获取有效审批人（考虑代理和权限冲突）"""
    now = timezone.now()
    
    # 查找活跃的代理设置
    proxy_setting = ApprovalProxy.objects.filter(
        principal__employee_id=approver_id,
        is_active=True,
        start_date__lte=now,
        end_date__gte=now
    ).first()
    
    if proxy_setting:
        proxy_id = proxy_setting.proxy.employee_id
        
        # 检查代理人是否在流程中已经是审批人
        if self._is_approver_in_process(proxy_id, leave_request):
            # 权限冲突，升级到上级
            return self._get_next_level_approver(approver_id)
        
        return proxy_id
    
    return approver_id
```


## 测试策略

### 测试方法

本系统采用双重测试策略：

1. **单元测试**：测试具体的业务逻辑、边界条件和错误处理
2. **属性测试**：验证系统的通用正确性属性

### 测试工具

- **单元测试框架**：pytest + pytest-django
- **属性测试框架**：Hypothesis (Python 的属性测试库)
- **API 测试**：pytest + requests-mock
- **BPMN 测试**：SpiffWorkflow 测试工具

### 测试配置

- 每个属性测试至少运行 100 次迭代
- 使用 Hypothesis 的策略生成随机测试数据
- 每个测试都标注对应的设计属性编号

### 测试环境

- 开发环境：SQLite + 本地 SpiffArena
- CI/CD 环境：PostgreSQL + Docker化的 SpiffArena
- 使用 Docker Compose 编排测试环境

### 单元测试示例

```python
import pytest
from django.test import TestCase
from approval.models import LeaveRequest, Employee
from approval.services import ApprovalService

class TestApprovalService(TestCase):
    def setUp(self):
        self.service = ApprovalService()
        self.employee = Employee.objects.create(
            employee_id='emp001',
            level=3
        )
    
    def test_select_process_model_by_duration(self):
        """测试根据时长选择流程模型"""
        # 短期请假（<= 3天）
        leave_request = LeaveRequest.objects.create(
            applicant=self.employee,
            duration=2.0
        )
        model_id = self.service._select_process_model(leave_request)
        assert model_id == 'basic_approval'
        
        # 长期请假（> 3天）
        leave_request.duration = 5.0
        model_id = self.service._select_process_model(leave_request)
        assert model_id == 'multi_level_approval'
    
    def test_webhook_idempotency(self):
        """测试 webhook 幂等性"""
        payload = {
            'process_instance_id': 'test_123',
            'task_id': 'task_456',
            'event_type': 'task_completed',
            'data': {}
        }
        
        # 第一次调用
        result1 = self.service.handle_webhook_callback(payload)
        assert result1['status'] == 'success'
        
        # 第二次调用（重复）
        result2 = self.service.handle_webhook_callback(payload)
        assert result2['status'] == 'duplicate'
```

### 集成测试示例

```python
@pytest.mark.integration
class TestApprovalIntegration(TestCase):
    def test_complete_approval_flow(self):
        """测试完整的审批流程"""
        # 1. 创建申请
        leave_request = LeaveRequest.objects.create(
            applicant=self.employee,
            duration=2.0,
            leave_type='annual'
        )
        
        # 2. 提交申请
        service = ApprovalService()
        leave_request = service.submit_leave_request(leave_request)
        assert leave_request.status == 'pending'
        assert leave_request.process_instance_id is not None
        
        # 3. 查询待办任务
        tasks = service.get_user_tasks(self.manager.employee_id)
        assert len(tasks) == 1
        
        # 4. 批准任务
        service.approve_task(tasks[0]['id'], self.manager, '同意')
        
        # 5. 验证最终状态
        leave_request.refresh_from_db()
        assert leave_request.status == 'approved'
```


## 正确性属性

*属性是一个特征或行为，应该在系统的所有有效执行中保持为真——本质上是关于系统应该做什么的形式化陈述。属性作为人类可读规范和机器可验证正确性保证之间的桥梁。*

### 属性 1：流程启动一致性

*对于任何*有效的请假申请，当提交申请时，系统应该创建一个 SpiffArena 流程实例，并且 LeaveRequest 的 process_instance_id 应该与 SpiffArena 返回的实例 ID 一致。

**验证需求：1.1**

### 属性 2：审批人动态分配正确性

*对于任何*审批节点和组织架构状态，当系统根据规则（直属上级、部门负责人、特定角色）查找审批人时，返回的审批人应该满足规则定义的条件。

**验证需求：3.1, 3.2, 3.3, 3.4**

### 属性 3：会签完成条件

*对于任何*配置为会签的审批节点，当所有指定的审批人都批准时，节点应该通过；当任意一个审批人拒绝时（如果配置为一票否决），流程应该终止。

**验证需求：4.1, 4.3**

### 属性 4：或签完成条件

*对于任何*配置为或签的审批节点，当任意一个审批人批准时，节点应该通过并取消其他审批人的任务；当所有审批人都拒绝时，流程应该终止。

**验证需求：4.4, 4.5, 4.6**

### 属性 5：退回后流程路径一致性

*对于任何*被退回的申请，当申请人修改后重新提交时，如果配置为从退回节点继续，流程应该从退回节点开始；如果配置为重新开始，流程应该从头开始。

**验证需求：5.6, 5.7, 5.9**

### 属性 6：审批历史完整性

*对于任何*审批流程，系统应该记录每一个审批操作（提交、批准、拒绝、退回、加签、转签），并且记录应该包含操作人、操作时间、操作类型和审批意见。

**验证需求：7.1, 7.2, 7.4**

### 属性 7：业务规则匹配唯一性

*对于任何*请假申请，当存在多个匹配的业务规则时，系统应该选择优先级最高的规则；当没有匹配的规则时，系统应该使用默认流程。

**验证需求：8.2, 8.3, 8.5**

### 属性 8：超时提醒触发正确性

*对于任何*审批任务，当任务超过配置的超时时间未处理时，系统应该发送提醒通知给审批人。

**验证需求：9.2**

### 属性 9：代理人生效时间范围

*对于任何*代理设置，当当前时间在代理时间范围内时，审批任务应该分配给代理人；当当前时间不在代理时间范围内时，审批任务应该分配给原审批人。

**验证需求：10.2, 10.4**

### 属性 10：代理人权限冲突检测

*对于任何*代理设置，当代理人在同一流程中既是原审批人又是代理人时，系统应该检测到权限冲突并自动跳过该节点或升级到更高一级审批人。

**验证需求：10.7**

### 属性 11：抄送通知完整性

*对于任何*指定了抄送人的审批流程，当流程状态变化时，所有抄送人都应该收到通知。

**验证需求：6.1, 6.2, 6.4**

### 属性 12：并行分支独立性

*对于任何*包含并行分支的审批流程，每个分支的审批操作应该独立进行，互不影响；只有当所有分支都完成时，流程才应该汇聚到下一个节点。

**验证需求：13.2, 13.3**

### 属性 13：Webhook 回调幂等性

*对于任何*SpiffArena 回调请求，当同一个 process_instance_id 和 task_id 的回调被多次接收时，系统应该只处理一次，后续的重复回调应该返回"已处理"状态。

**验证需求：15.2**

### 属性 14：状态转换合法性

*对于任何*LeaveRequest，状态转换应该遵循合法的状态机：draft → pending → (approved | rejected | cancelled)，不应该出现非法的状态转换（如从 approved 转换到 rejected）。

**验证需求：15.3**

### 属性 15：通知发送完整性

*对于任何*审批任务分配或流程状态变化事件，系统应该发送邮件通知和站内消息通知给相关人员。

**验证需求：14.1, 14.2**


### 属性测试示例

```python
from hypothesis import given, strategies as st
from hypothesis.extra.django import from_model
import pytest

# Feature: chinese-complex-approval-system, Property 1: 流程启动一致性
@given(
    leave_request=from_model(
        LeaveRequest,
        applicant=from_model(Employee),
        duration=st.floats(min_value=0.5, max_value=30.0),
        leave_type=st.sampled_from(['annual', 'sick', 'personal'])
    )
)
@pytest.mark.property_test
def test_property_1_process_start_consistency(leave_request, mock_spiff_service):
    """
    属性 1：流程启动一致性
    对于任何有效的请假申请，提交后应该创建流程实例并保存正确的 ID
    """
    # 模拟 SpiffArena 返回
    expected_process_id = f"process_{leave_request.id}"
    mock_spiff_service.start_process.return_value = {'id': expected_process_id}
    
    # 提交申请
    service = ApprovalService()
    result = service.submit_leave_request(leave_request)
    
    # 验证
    assert result.process_instance_id == expected_process_id
    assert result.status == 'pending'
    assert mock_spiff_service.start_process.called


# Feature: chinese-complex-approval-system, Property 3: 会签完成条件
@given(
    approvers=st.lists(
        from_model(Employee),
        min_size=2,
        max_size=5
    ),
    approval_results=st.lists(
        st.sampled_from(['approve', 'reject']),
        min_size=2,
        max_size=5
    )
)
@pytest.mark.property_test
def test_property_3_countersign_completion(approvers, approval_results):
    """
    属性 3：会签完成条件
    对于任何会签节点，所有人批准才通过，任意一人拒绝则终止
    """
    # 确保列表长度一致
    approval_results = approval_results[:len(approvers)]
    
    # 模拟会签流程
    all_approved = all(result == 'approve' for result in approval_results)
    any_rejected = any(result == 'reject' for result in approval_results)
    
    # 验证逻辑
    if all_approved:
        # 所有人批准，流程应该继续
        assert should_continue_process(approval_results) == True
    elif any_rejected:
        # 任意一人拒绝，流程应该终止
        assert should_terminate_process(approval_results) == True


# Feature: chinese-complex-approval-system, Property 7: 业务规则匹配唯一性
@given(
    leave_request=from_model(LeaveRequest),
    rules=st.lists(
        from_model(ApprovalRule, priority=st.integers(min_value=0, max_value=100)),
        min_size=1,
        max_size=10
    )
)
@pytest.mark.property_test
def test_property_7_business_rule_uniqueness(leave_request, rules):
    """
    属性 7：业务规则匹配唯一性
    对于任何请假申请，应该选择优先级最高的匹配规则
    """
    service = ApprovalService()
    
    # 找出所有匹配的规则
    matching_rules = [
        rule for rule in rules
        if service._match_rule(leave_request, rule)
    ]
    
    if matching_rules:
        # 应该选择优先级最高的
        selected_rule = service._select_process_model(leave_request)
        highest_priority_rule = max(matching_rules, key=lambda r: r.priority)
        assert selected_rule == highest_priority_rule.process_model_id
    else:
        # 没有匹配规则，应该使用默认流程
        selected_rule = service._select_process_model(leave_request)
        assert selected_rule == settings.DEFAULT_APPROVAL_PROCESS_MODEL


# Feature: chinese-complex-approval-system, Property 9: 代理人生效时间范围
@given(
    proxy_setting=from_model(ApprovalProxy),
    current_time=st.datetimes(
        min_value=datetime(2024, 1, 1),
        max_value=datetime(2024, 12, 31)
    )
)
@pytest.mark.property_test
def test_property_9_proxy_time_range(proxy_setting, current_time):
    """
    属性 9：代理人生效时间范围
    对于任何代理设置，只有在时间范围内才应该生效
    """
    service = ApprovalService()
    
    # 获取有效审批人
    effective_approver = service.get_effective_approver(
        proxy_setting.principal.employee_id,
        current_time
    )
    
    # 验证
    if proxy_setting.start_date <= current_time <= proxy_setting.end_date:
        # 在时间范围内，应该返回代理人
        assert effective_approver == proxy_setting.proxy.employee_id
    else:
        # 不在时间范围内，应该返回原审批人
        assert effective_approver == proxy_setting.principal.employee_id


# Feature: chinese-complex-approval-system, Property 13: Webhook 回调幂等性
@given(
    payload=st.fixed_dictionaries({
        'process_instance_id': st.text(min_size=10, max_size=50),
        'task_id': st.text(min_size=10, max_size=50),
        'event_type': st.sampled_from(['task_completed', 'process_completed']),
        'data': st.dictionaries(st.text(), st.text())
    }),
    call_count=st.integers(min_value=1, max_value=5)
)
@pytest.mark.property_test
def test_property_13_webhook_idempotency(payload, call_count):
    """
    属性 13：Webhook 回调幂等性
    对于任何回调请求，多次调用应该只处理一次
    """
    service = ApprovalService()
    results = []
    
    # 多次调用同一个回调
    for _ in range(call_count):
        result = service.handle_webhook_callback(payload)
        results.append(result['status'])
    
    # 验证：第一次应该成功，后续应该返回 duplicate
    assert results[0] == 'success'
    assert all(status == 'duplicate' for status in results[1:])


# Feature: chinese-complex-approval-system, Property 14: 状态转换合法性
@given(
    initial_status=st.sampled_from(['draft', 'pending', 'approved', 'rejected']),
    target_status=st.sampled_from(['draft', 'pending', 'approved', 'rejected', 'cancelled'])
)
@pytest.mark.property_test
def test_property_14_state_transition_legality(initial_status, target_status):
    """
    属性 14：状态转换合法性
    对于任何状态转换，应该遵循合法的状态机
    """
    # 定义合法的状态转换
    legal_transitions = {
        'draft': ['pending', 'cancelled'],
        'pending': ['approved', 'rejected', 'cancelled'],
        'approved': [],  # 终态
        'rejected': [],  # 终态
        'cancelled': []  # 终态
    }
    
    is_legal = target_status in legal_transitions.get(initial_status, [])
    
    # 尝试状态转换
    leave_request = LeaveRequest.objects.create(status=initial_status)
    
    try:
        leave_request.status = target_status
        leave_request.full_clean()  # 验证模型
        leave_request.save()
        # 如果保存成功，应该是合法转换
        assert is_legal
    except ValidationError:
        # 如果抛出异常，应该是非法转换
        assert not is_legal
```

### 测试运行配置

```python
# pytest.ini
[pytest]
DJANGO_SETTINGS_MODULE = approval_system.settings.test
python_files = tests.py test_*.py *_tests.py
python_classes = Test*
python_functions = test_*
markers =
    property_test: Property-based tests (run with --hypothesis-profile=ci)
    integration: Integration tests
    slow: Slow tests

# Hypothesis 配置
[hypothesis]
max_examples = 100
deadline = None
```

### CI/CD 集成

```yaml
# .github/workflows/test.yml
name: Tests

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    
    services:
      postgres:
        image: postgres:14
        env:
          POSTGRES_PASSWORD: postgres
        options: >-
          --health-cmd pg_isready
          --health-interval 10s
          --health-timeout 5s
          --health-retries 5
      
      spiffarena:
        image: sartography/spiff-arena:latest
        ports:
          - 8000:8000
    
    steps:
      - uses: actions/checkout@v2
      
      - name: Set up Python
        uses: actions/setup-python@v2
        with:
          python-version: '3.11'
      
      - name: Install dependencies
        run: |
          pip install -r requirements.txt
          pip install -r requirements-test.txt
      
      - name: Run unit tests
        run: pytest tests/ -v --cov=approval
      
      - name: Run property tests
        run: pytest tests/ -m property_test --hypothesis-profile=ci
      
      - name: Run integration tests
        run: pytest tests/ -m integration
```


## 开发环境配置

**注意：开发环境不需要 Docker，直接使用 SQLite 数据库和 Django 开发服务器即可。**

### 环境要求

- Python 3.11+
- Django 4.x
- SQLite（Django 自带，无需额外安装）
- SpiffWorkflow 库（已在 requirements.txt 中）

### 快速启动开发环境

```bash
# 1. 安装依赖
cd leave_system
pip install -r requirements.txt

# 2. 运行数据库迁移
python manage.py migrate

# 3. 创建测试数据（见下文）
python create_test_data.py

# 4. 启动开发服务器
python manage.py runserver

# 访问 http://localhost:8000/
```

### 用户和角色绑定

在开发环境中，由于没有完整的组织架构数据，我们需要手动创建用户、员工和角色数据来测试审批流程。

#### 1. 创建测试数据脚本

在 `leave_system` 目录下创建 `create_test_data.py` 脚本：

```python
"""
创建测试数据脚本
用于在开发环境中快速创建用户、员工、部门和角色数据
"""

import os
import django

# 设置 Django 环境
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'leave_system.settings')
django.setup()

from django.contrib.auth.models import User
from organization.models import Department, Employee, Role

def create_test_data():
    """创建测试数据"""
    
    print("开始创建测试数据...")
    
    # ========== 1. 创建部门 ==========
    print("\n创建部门...")
    
    # 创建根部门
    company = Department.objects.create(
        name="公司总部",
        parent=None
    )
    
    # 创建子部门
    tech_dept = Department.objects.create(
        name="技术部",
        parent=company
    )
    
    hr_dept = Department.objects.create(
        name="人力资源部",
        parent=company
    )
    
    finance_dept = Department.objects.create(
        name="财务部",
        parent=company
    )
    
    print(f"✓ 创建部门: {company.name}, {tech_dept.name}, {hr_dept.name}, {finance_dept.name}")
    
    # ========== 2. 创建用户和员工 ==========
    print("\n创建用户和员工...")
    
    # 创建总经理
    ceo_user = User.objects.create_user(
        username='ceo',
        email='ceo@company.com',
        password='password123',
        first_name='张',
        last_name='总'
    )
    ceo = Employee.objects.create(
        user=ceo_user,
        employee_id='EMP001',
        department=company,
        position='总经理',
        level=10,
        direct_manager=None,
        email='ceo@company.com',
        phone='13800000001'
    )
    company.manager = ceo
    company.save()
    print(f"✓ 创建总经理: {ceo_user.username} ({ceo.employee_id})")
    
    # 创建技术部经理
    tech_manager_user = User.objects.create_user(
        username='tech_manager',
        email='tech.manager@company.com',
        password='password123',
        first_name='李',
        last_name='经理'
    )
    tech_manager = Employee.objects.create(
        user=tech_manager_user,
        employee_id='EMP002',
        department=tech_dept,
        position='技术部经理',
        level=8,
        direct_manager=ceo,
        email='tech.manager@company.com',
        phone='13800000002'
    )
    tech_dept.manager = tech_manager
    tech_dept.save()
    print(f"✓ 创建技术部经理: {tech_manager_user.username} ({tech_manager.employee_id})")
    
    # 创建技术部员工
    developer_user = User.objects.create_user(
        username='developer',
        email='developer@company.com',
        password='password123',
        first_name='王',
        last_name='开发'
    )
    developer = Employee.objects.create(
        user=developer_user,
        employee_id='EMP003',
        department=tech_dept,
        position='高级开发工程师',
        level=5,
        direct_manager=tech_manager,
        email='developer@company.com',
        phone='13800000003'
    )
    print(f"✓ 创建开发工程师: {developer_user.username} ({developer.employee_id})")
    
    # 创建 HR 经理
    hr_manager_user = User.objects.create_user(
        username='hr_manager',
        email='hr.manager@company.com',
        password='password123',
        first_name='赵',
        last_name='HR'
    )
    hr_manager = Employee.objects.create(
        user=hr_manager_user,
        employee_id='EMP004',
        department=hr_dept,
        position='HR经理',
        level=8,
        direct_manager=ceo,
        email='hr.manager@company.com',
        phone='13800000004'
    )
    hr_dept.manager = hr_manager
    hr_dept.save()
    print(f"✓ 创建HR经理: {hr_manager_user.username} ({hr_manager.employee_id})")
    
    # 创建财务经理
    finance_manager_user = User.objects.create_user(
        username='finance_manager',
        email='finance.manager@company.com',
        password='password123',
        first_name='钱',
        last_name='财务'
    )
    finance_manager = Employee.objects.create(
        user=finance_manager_user,
        employee_id='EMP005',
        department=finance_dept,
        position='财务经理',
        level=8,
        direct_manager=ceo,
        email='finance.manager@company.com',
        phone='13800000005'
    )
    finance_dept.manager = finance_manager
    finance_dept.save()
    print(f"✓ 创建财务经理: {finance_manager_user.username} ({finance_manager.employee_id})")
    
    # ========== 3. 创建角色 ==========
    print("\n创建角色...")
    
    # 创建管理层角色
    management_role = Role.objects.create(
        name='管理层',
        description='公司管理层，包括各部门经理和总经理'
    )
    management_role.employees.add(ceo, tech_manager, hr_manager, finance_manager)
    print(f"✓ 创建角色: {management_role.name} (成员: 4人)")
    
    # 创建 HR 角色
    hr_role = Role.objects.create(
        name='HR',
        description='人力资源部门成员'
    )
    hr_role.employees.add(hr_manager)
    print(f"✓ 创建角色: {hr_role.name} (成员: 1人)")
    
    # 创建财务角色
    finance_role = Role.objects.create(
        name='财务',
        description='财务部门成员'
    )
    finance_role.employees.add(finance_manager)
    print(f"✓ 创建角色: {finance_role.name} (成员: 1人)")
    
    # 创建技术团队角色
    tech_team_role = Role.objects.create(
        name='技术团队',
        description='技术部门所有成员'
    )
    tech_team_role.employees.add(tech_manager, developer)
    print(f"✓ 创建角色: {tech_team_role.name} (成员: 2人)")
    
    # ========== 4. 输出测试账号信息 ==========
    print("\n" + "="*60)
    print("测试数据创建完成！")
    print("="*60)
    print("\n测试账号信息：")
    print("-" * 60)
    print(f"{'用户名':<15} {'密码':<15} {'角色':<15} {'员工ID':<10}")
    print("-" * 60)
    print(f"{'ceo':<15} {'password123':<15} {'总经理':<15} {'EMP001':<10}")
    print(f"{'tech_manager':<15} {'password123':<15} {'技术部经理':<15} {'EMP002':<10}")
    print(f"{'developer':<15} {'password123':<15} {'开发工程师':<15} {'EMP003':<10}")
    print(f"{'hr_manager':<15} {'password123':<15} {'HR经理':<15} {'EMP004':<10}")
    print(f"{'finance_manager':<15} {'password123':<15} {'财务经理':<15} {'EMP005':<10}")
    print("-" * 60)
    
    print("\n组织架构：")
    print("-" * 60)
    print("公司总部 (总经理: 张总)")
    print("├── 技术部 (经理: 李经理)")
    print("│   └── 王开发 (上级: 李经理)")
    print("├── 人力资源部 (经理: 赵HR)")
    print("└── 财务部 (经理: 钱财务)")
    print("-" * 60)
    
    print("\n使用说明：")
    print("1. 使用上述账号登录系统")
    print("2. developer 可以提交请假申请")
    print("3. tech_manager 作为直属上级审批")
    print("4. 根据请假时长，可能需要 hr_manager 或 ceo 审批")
    print("\n" + "="*60)

if __name__ == '__main__':
    # 清除旧数据（可选）
    print("警告：此操作将清除所有现有的用户、员工、部门和角色数据！")
    confirm = input("是否继续？(yes/no): ")
    
    if confirm.lower() == 'yes':
        print("\n清除旧数据...")
        Employee.objects.all().delete()
        Department.objects.all().delete()
        Role.objects.all().delete()
        User.objects.filter(is_superuser=False).delete()
        print("✓ 旧数据已清除")
        
        create_test_data()
    else:
        print("操作已取消")
```

#### 2. 运行测试数据脚本

```bash
# 进入项目目录
cd leave_system

# 运行脚本创建测试数据
python create_test_data.py
```

#### 3. 使用 Django Admin 管理用户和角色

如果需要通过 Web 界面管理用户和角色，可以使用 Django Admin：

```python
# 在 organization/admin.py 中注册模型
from django.contrib import admin
from .models import Department, Employee, Role

@admin.register(Department)
class DepartmentAdmin(admin.ModelAdmin):
    list_display = ['name', 'parent', 'manager', 'created_at']
    search_fields = ['name']
    list_filter = ['created_at']

@admin.register(Employee)
class EmployeeAdmin(admin.ModelAdmin):
    list_display = ['employee_id', 'user', 'department', 'position', 'level', 'direct_manager']
    search_fields = ['employee_id', 'user__username', 'user__email']
    list_filter = ['department', 'level']
    raw_id_fields = ['user', 'direct_manager']

@admin.register(Role)
class RoleAdmin(admin.ModelAdmin):
    list_display = ['name', 'description', 'created_at']
    search_fields = ['name']
    filter_horizontal = ['employees']
```

然后创建超级用户并访问 Admin 界面：

```bash
# 创建超级用户
python manage.py createsuperuser

# 启动开发服务器
python manage.py runserver

# 访问 http://localhost:8000/admin/
```

#### 4. 通过 API 创建用户和角色

也可以通过 REST API 创建用户和角色：

```python
# 在 organization/views.py 中添加 API 视图
from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.response import Response
from django.contrib.auth.models import User
from .models import Department, Employee, Role
from .serializers import DepartmentSerializer, EmployeeSerializer, RoleSerializer

class EmployeeViewSet(viewsets.ModelViewSet):
    queryset = Employee.objects.all()
    serializer_class = EmployeeSerializer
    
    @action(detail=False, methods=['post'])
    def create_with_user(self, request):
        """创建员工并自动创建关联的用户"""
        # 创建用户
        user_data = request.data.get('user')
        user = User.objects.create_user(
            username=user_data['username'],
            email=user_data['email'],
            password=user_data['password'],
            first_name=user_data.get('first_name', ''),
            last_name=user_data.get('last_name', '')
        )
        
        # 创建员工
        employee_data = request.data.get('employee')
        employee = Employee.objects.create(
            user=user,
            employee_id=employee_data['employee_id'],
            department_id=employee_data['department_id'],
            position=employee_data['position'],
            level=employee_data['level'],
            direct_manager_id=employee_data.get('direct_manager_id'),
            email=user.email,
            phone=employee_data.get('phone', '')
        )
        
        serializer = self.get_serializer(employee)
        return Response(serializer.data)

class RoleViewSet(viewsets.ModelViewSet):
    queryset = Role.objects.all()
    serializer_class = RoleSerializer
    
    @action(detail=True, methods=['post'])
    def add_employee(self, request, pk=None):
        """向角色添加员工"""
        role = self.get_object()
        employee_id = request.data.get('employee_id')
        employee = Employee.objects.get(id=employee_id)
        role.employees.add(employee)
        return Response({'status': 'employee added'})
```

#### 5. 开发环境快速测试流程

```python
# 在 Django shell 中快速创建测试数据
python manage.py shell

# 在 shell 中执行
from django.contrib.auth.models import User
from organization.models import Department, Employee, Role

# 创建简单的测试数据
user1 = User.objects.create_user('applicant', 'applicant@test.com', 'pass123')
user2 = User.objects.create_user('manager', 'manager@test.com', 'pass123')

dept = Department.objects.create(name='测试部门')

emp1 = Employee.objects.create(
    user=user1, employee_id='E001', department=dept,
    position='员工', level=3, email='applicant@test.com'
)

emp2 = Employee.objects.create(
    user=user2, employee_id='E002', department=dept,
    position='经理', level=7, email='manager@test.com'
)

emp1.direct_manager = emp2
emp1.save()

dept.manager = emp2
dept.save()

print("测试数据创建完成！")
print(f"申请人: {user1.username} / pass123")
print(f"审批人: {user2.username} / pass123")
```

#### 6. 环境变量配置

在开发环境的 `.env` 文件中添加：

```bash
# 开发环境配置
DEBUG=True
SECRET_KEY=dev-secret-key-change-in-production

# 数据库（开发环境使用 SQLite）
DATABASE_URL=sqlite:///db.sqlite3

# 默认审批流程
DEFAULT_WORKFLOW_SPEC=basic_approval

# 跳过邮件发送（开发环境）
EMAIL_BACKEND=django.core.mail.backends.console.EmailBackend
```

#### 7. 测试审批流程

创建测试数据后，可以通过以下步骤测试审批流程：

```bash
# 1. 以申请人身份登录并创建请假申请
curl -X POST http://localhost:8000/api/leave/create/ \
  -H "Content-Type: application/json" \
  -d '{
    "user_email": "developer@company.com",
    "reason": "测试请假",
    "leave_hours": 8
  }'

# 2. 以审批人身份查询待办任务
curl http://localhost:8000/api/leave/pending-approvals/?user_id=tech_manager

# 3. 审批任务
curl -X POST http://localhost:8000/api/leave/approve/ \
  -H "Content-Type: application/json" \
  -d '{
    "task_guid": "xxx",
    "process_instance_id": "yyy",
    "leave_request_id": 1,
    "approved": true,
    "comment": "同意"
  }'
```

### 注意事项

1. **密码安全**：开发环境使用简单密码，生产环境必须使用强密码
2. **数据隔离**：开发环境数据不要同步到生产环境
3. **权限测试**：确保测试不同角色的权限控制
4. **工作流测试**：测试不同的审批路径和条件分支
5. **无需 Docker**：开发环境直接使用 SQLite，无需配置 Docker 和 PostgreSQL
6. **邮件测试**：开发环境使用 console backend，邮件会输出到控制台而不是真实发送

### 开发环境 vs 生产环境对比

| 项目 | 开发环境 | 生产环境 |
|------|---------|---------|
| 数据库 | SQLite | PostgreSQL |
| 部署方式 | Django runserver | Docker + Gunicorn |
| 缓存 | 内存缓存 | Redis |
| 任务队列 | 同步执行 | Celery + Redis |
| 邮件 | Console Backend | SMTP |
| 静态文件 | Django 直接服务 | Nginx |
| 工作流持久化 | 内存 + 数据库 | 数据库 |

---

## 部署架构（生产环境）

**以下内容仅适用于生产环境部署，开发环境请参考上面的"开发环境配置"章节。**

### 生产环境架构

```
┌─────────────────────────────────────────────────────────────┐
│                      负载均衡器 (Nginx)                        │
└─────────────────────────────────────────────────────────────┘
                            │
                ┌───────────┴───────────┐
                │                       │
                ▼                       ▼
┌──────────────────────┐    ┌──────────────────────┐
│  Django App Server 1 │    │  Django App Server 2 │
│  (Gunicorn)          │    │  (Gunicorn)          │
│  + SpiffWorkflow     │    │  + SpiffWorkflow     │
└──────────────────────┘    └──────────────────────┘
                │                       │
                └───────────┬───────────┘
                            │
                ┌───────────┴───────────┐
                │                       │
                ▼                       ▼
┌──────────────────────┐    ┌──────────────────────┐
│  PostgreSQL          │    │  Redis               │
│  (Primary + Replica) │    │  (Sentinel)          │
└──────────────────────┘    └──────────────────────┘
                │
                ▼
┌──────────────────────┐
│  Celery Workers      │
│  (Beat + Workers)    │
└──────────────────────┘
```

**设计决策：单体部署架构**

我们采用单体部署架构，SpiffWorkflow 作为库集成在 Django 应用中。这样可以：
- 简化部署和运维，减少服务数量
- 降低网络通信开销，提升性能
- 利用数据库事务保证数据一致性
- 减少基础设施成本

### Docker Compose 配置

```yaml
version: '3.8'

services:
  db:
    image: postgres:14
    environment:
      POSTGRES_DB: approval_system
      POSTGRES_USER: approval
      POSTGRES_PASSWORD: ${DB_PASSWORD}
    volumes:
      - postgres_data:/var/lib/postgresql/data
    networks:
      - approval_network
  
  redis:
    image: redis:7-alpine
    networks:
      - approval_network
  
  django:
    build: .
    command: gunicorn approval_system.wsgi:application --bind 0.0.0.0:8000
    volumes:
      - ./:/app
      - static_volume:/app/staticfiles
      - media_volume:/app/media
    environment:
      - DATABASE_URL=postgresql://approval:${DB_PASSWORD}@db:5432/approval_system
      - REDIS_URL=redis://redis:6379/0
      - DEFAULT_WORKFLOW_SPEC=basic_approval
    depends_on:
      - db
      - redis
    networks:
      - approval_network
  
  celery:
    build: .
    command: celery -A approval_system worker -l info
    volumes:
      - ./:/app
    environment:
      - DATABASE_URL=postgresql://approval:${DB_PASSWORD}@db:5432/approval_system
      - REDIS_URL=redis://redis:6379/0
    depends_on:
      - db
      - redis
    networks:
      - approval_network
  
  celery-beat:
    build: .
    command: celery -A approval_system beat -l info
    volumes:
      - ./:/app
    environment:
      - DATABASE_URL=postgresql://approval:${DB_PASSWORD}@db:5432/approval_system
      - REDIS_URL=redis://redis:6379/0
    depends_on:
      - db
      - redis
    networks:
      - approval_network
  
  nginx:
    image: nginx:alpine
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - ./nginx.conf:/etc/nginx/nginx.conf
      - static_volume:/app/staticfiles
      - media_volume:/app/media
    depends_on:
      - django
    networks:
      - approval_network

volumes:
  postgres_data:
  static_volume:
  media_volume:

networks:
  approval_network:
    driver: bridge
```

### 环境变量配置

```bash
# .env.production
DEBUG=False
SECRET_KEY=your-secret-key-here
ALLOWED_HOSTS=yourdomain.com,www.yourdomain.com

# Database
DATABASE_URL=postgresql://user:password@localhost:5432/approval_system

# Redis
REDIS_URL=redis://localhost:6379/0

# Workflow
DEFAULT_WORKFLOW_SPEC=basic_approval
WORKFLOW_FILES_PATH=workflows/

# Email
EMAIL_BACKEND=django.core.mail.backends.smtp.EmailBackend
EMAIL_HOST=smtp.gmail.com
EMAIL_PORT=587
EMAIL_USE_TLS=True
EMAIL_HOST_USER=your-email@gmail.com
EMAIL_HOST_PASSWORD=your-password

# Celery
CELERY_BROKER_URL=redis://localhost:6379/0
CELERY_RESULT_BACKEND=redis://localhost:6379/0

# Security
SECURE_SSL_REDIRECT=True
SESSION_COOKIE_SECURE=True
CSRF_COOKIE_SECURE=True
```

## 性能优化

### 1. 数据库优化

```python
# 索引优化
class LeaveRequest(models.Model):
    # ...
    class Meta:
        indexes = [
            models.Index(fields=['status', 'created_at']),
            models.Index(fields=['applicant', 'status']),
            models.Index(fields=['process_instance_id']),
        ]

# 查询优化
def get_user_requests(user_id):
    return LeaveRequest.objects.filter(
        applicant__user_id=user_id
    ).select_related(
        'applicant',
        'applicant__department',
        'current_approver'
    ).prefetch_related(
        'history',
        'cc_records'
    ).order_by('-created_at')
```

### 2. 缓存策略

```python
from django.core.cache import cache

def get_user_tasks(user_id):
    """获取用户待办任务（带缓存）"""
    cache_key = f'user_tasks:{user_id}'
    tasks = cache.get(cache_key)
    
    if tasks is None:
        tasks = spiff_service.get_user_tasks(user_id)
        cache.set(cache_key, tasks, timeout=300)  # 5分钟缓存
    
    return tasks

def invalidate_user_tasks_cache(user_id):
    """清除用户任务缓存"""
    cache_key = f'user_tasks:{user_id}'
    cache.delete(cache_key)
```

### 3. 异步任务

```python
from celery import shared_task

@shared_task
def send_notification_async(notification_id):
    """异步发送通知"""
    notification = Notification.objects.get(id=notification_id)
    notification_service = NotificationService()
    notification_service.send_email(notification)

@shared_task
def check_timeout_tasks():
    """定时检查超时任务"""
    now = timezone.now()
    timeout_threshold = now - timedelta(hours=24)
    
    # 查找超时任务
    timeout_requests = LeaveRequest.objects.filter(
        status='pending',
        submitted_at__lt=timeout_threshold
    )
    
    for request in timeout_requests:
        # 发送催办通知
        send_timeout_reminder.delay(request.id)
```

## 安全考虑

### 1. API 认证

```python
from rest_framework.authentication import TokenAuthentication
from rest_framework.permissions import IsAuthenticated

class ApprovalTaskViewSet(viewsets.ViewSet):
    authentication_classes = [TokenAuthentication]
    permission_classes = [IsAuthenticated]
    
    def list(self, request):
        # 只能查看自己的任务
        user = request.user
        # 从工作流状态中查询用户任务
        leave_request = LeaveRequest.objects.get(...)
        workflow = workflow_service.deserialize_workflow(leave_request.workflow_state)
        tasks = workflow_service.get_user_tasks(workflow, user.employee.employee_id)
        return Response(tasks)
```

### 2. 权限控制

```python
def check_approval_permission(user, leave_request, task_id):
    """检查用户是否有权限审批该任务"""
    # 1. 反序列化工作流状态
    workflow = workflow_service.deserialize_workflow(leave_request.workflow_state)
    
    # 2. 查询任务信息
    task = workflow.get_task_from_id(task_id)
    if not task:
        raise PermissionDenied('任务不存在')
    
    # 3. 检查是否分配给该用户
    assigned_to = task.data.get('assigned_to')
    if assigned_to != user.employee.employee_id:
        # 4. 检查是否是代理人
        proxy = ApprovalProxy.objects.filter(
            principal__employee_id=assigned_to,
            proxy=user.employee,
            is_active=True,
            start_date__lte=timezone.now(),
            end_date__gte=timezone.now()
        ).first()
        
        if not proxy:
            raise PermissionDenied('无权限审批该任务')
```

### 3. 工作流状态保护

```python
# 确保工作流状态只能通过 ApprovalService 修改
class LeaveRequest(models.Model):
    # ...
    
    def save(self, *args, **kwargs):
        # 防止直接修改工作流状态
        if self.pk and 'workflow_state' in kwargs.get('update_fields', []):
            raise ValueError('工作流状态只能通过 ApprovalService 修改')
        super().save(*args, **kwargs)
```

## 监控和日志

### 1. 日志配置

```python
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'verbose': {
            'format': '{levelname} {asctime} {module} {process:d} {thread:d} {message}',
            'style': '{',
        },
    },
    'handlers': {
        'file': {
            'level': 'INFO',
            'class': 'logging.handlers.RotatingFileHandler',
            'filename': '/var/log/approval/django.log',
            'maxBytes': 1024 * 1024 * 15,  # 15MB
            'backupCount': 10,
            'formatter': 'verbose',
        },
        'webhook': {
            'level': 'INFO',
            'class': 'logging.handlers.RotatingFileHandler',
            'filename': '/var/log/approval/workflow_events.log',
            'maxBytes': 1024 * 1024 * 15,
            'backupCount': 10,
            'formatter': 'verbose',
        },
    },
    'loggers': {
        'django': {
            'handlers': ['file'],
            'level': 'INFO',
            'propagate': True,
        },
        'approval.webhooks': {
            'handlers': ['workflow_events'],
            'level': 'INFO',
            'propagate': False,
        },
    },
}
```

### 2. 监控指标

```python
from prometheus_client import Counter, Histogram

# 定义指标
approval_requests_total = Counter(
    'approval_requests_total',
    'Total number of approval requests',
    ['status']
)

approval_duration = Histogram(
    'approval_duration_seconds',
    'Time taken for approval process',
    ['leave_type']
)

workflow_calls_total = Counter(
    'workflow_calls_total',
    'Total number of workflow operations',
    ['operation_type', 'status']
)

# 使用指标
def submit_leave_request(leave_request):
    with approval_duration.labels(leave_type=leave_request.leave_type).time():
        # 处理逻辑
        result = service.submit_leave_request(leave_request)
        approval_requests_total.labels(status='submitted').inc()
        return result
```

## 总结

本设计文档描述了一个完整的中国式复杂审批系统的技术架构。系统采用 Django + SpiffWorkflow 的集成架构，SpiffWorkflow 作为 Python 库直接集成在 Django 应用中。设计充分考虑了：

1. **功能完整性**：支持多级审批、会签或签、加签转签、代理人、超时处理等复杂场景
2. **可靠性**：通过事务管理、工作流状态持久化、错误处理确保数据一致性
3. **可扩展性**：通过业务规则配置和 BPMN 流程设计实现灵活的流程定制
4. **可测试性**：采用单元测试和属性测试双重策略，确保系统正确性
5. **性能**：通过缓存、异步任务、数据库优化提升系统性能
6. **安全性**：通过认证、授权、工作流状态保护保障系统安全
7. **简化部署**：单体架构减少了部署复杂度和运维成本

系统设计遵循最佳实践，充分利用 SpiffWorkflow 的 BPMN 能力和 Django 的生态系统，为企业提供一个功能强大、稳定可靠、易于部署的审批解决方案。
