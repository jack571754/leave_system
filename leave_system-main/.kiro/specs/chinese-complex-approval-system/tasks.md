# 实现计划：中国式复杂审批系统

## 概述

本实现计划将设计文档转换为可执行的编码任务。系统基于 Django + SpiffWorkflow 架构，采用增量开发方式，每个任务都构建在前一个任务的基础上。

**当前状态分析**（2026-01-17）：
- ✅ 已有基础 Django 项目（leave_system）
- ✅ 已有 LeaveRequest 基础模型（包含 process_instance_id, status, process_model_id 等字段）
- ✅ 已有 SpiffWorkflow 客户端集成（spiff_client.py，内存存储工作流实例）
- ✅ 已有基础 REST API（创建申请、查询待办、审批）
- ✅ 已有简单的 BPMN 流程文件（admin.bpmn，包含条件网关）
- ✅ 已安装依赖：Django 4.2.9, DRF, SpiffWorkflow 2.0.1
- ❌ 缺少组织架构模型（Department, Employee, Role）
- ❌ 缺少审批历史、代理、抄送等扩展模型
- ❌ 缺少通知系统
- ❌ 缺少业务规则引擎
- ❌ 缺少完整的审批流程（会签、或签、多级审批等）
- ❌ 缺少测试环境和测试用例
- ❌ 缺少工作流状态持久化（当前仅内存存储）
- ❌ 缺少 Celery 异步任务配置

**注意**：本任务清单基于现有代码库（leave_system）进行扩展，而非从零开始创建新项目。

## 任务清单

### 阶段 1: 项目基础设置和扩展

- [ ] 1.1 扩展现有 Django 应用结构
  - 在 leave_system 项目中创建新应用 `organization`（组织架构管理）
  - 在 leave_system 项目中创建新应用 `notifications`（通知系统）
  - 更新 leave_system/settings.py 注册新应用到 INSTALLED_APPS
  - 保留现有 leave_api 应用作为核心审批逻辑
  - _需求：12.1, 12.2, 12.3, 14.1_

- [ ] 1.2 配置测试环境
  - 更新 leave_system/requirements.txt 添加 pytest、pytest-django、hypothesis
  - 在 leave_system 目录创建 pytest.ini 配置文件
  - 在 leave_system 目录创建 conftest.py 配置测试 fixtures
  - 在各应用中创建 tests/ 目录结构
  - _需求：所有（测试相关）_

- [ ] 1.3 配置 Celery 异步任务
  - 更新 leave_system/requirements.txt 添加 celery、redis
  - 在 leave_system/leave_system/ 目录创建 celery.py 配置文件
  - 更新 leave_system/leave_system/__init__.py 初始化 Celery
  - 配置 Celery Beat 定时任务调度
  - 在各应用中创建 tasks.py 基础结构
  - _需求：9.2, 14.1, 14.2_

### 阶段 2: 组织架构模块

- [ ] 2.1 实现组织架构数据模型
  - 在 organization 应用中创建 models.py
  - 创建 Department 模型（部门，支持树形结构）
  - 创建 Employee 模型（员工，关联 Django User）
  - 创建 Role 模型（角色，多对多关联员工）
  - 添加数据库索引和约束
  - 创建数据库迁移文件
  - _需求：12.1, 12.2, 12.3_

- [ ]* 2.2 编写组织架构模型单元测试
  - 在 organization/tests/ 创建 test_models.py
  - 测试部门树形结构（parent 关系）
  - 测试员工与部门关联
  - 测试角色分配（多对多关系）
  - 测试数据验证规则
  - _需求：12.1, 12.2, 12.3_

- [ ] 2.3 实现组织架构 REST API
  - 在 organization 应用中创建 serializers.py
  - 在 organization 应用中创建 views.py
  - 实现部门 CRUD API（使用 DRF ViewSets）
  - 实现员工 CRUD API
  - 实现角色 CRUD API
  - 实现查询直属上级 API（GET /api/employees/{id}/direct-manager/）
  - 实现查询部门负责人 API（GET /api/departments/{id}/manager/）
  - 实现查询角色成员 API（GET /api/roles/{id}/members/）
  - 创建 urls.py 并注册路由到主 urls.py
  - _需求：12.1, 12.2, 12.3, 3.2, 3.3, 3.4_

- [ ]* 2.4 编写组织架构 API 单元测试
  - 在 organization/tests/ 创建 test_api.py
  - 测试 API 权限控制
  - 测试数据验证
  - 测试边界条件
  - _需求：12.1, 12.2, 12.3_


### 阶段 3: 重构 SpiffWorkflow 集成服务

- [ ] 3.1 重构 SpiffWorkflow 客户端以支持持久化
  - 修改 leave_api/spiff_client.py 添加工作流状态序列化/反序列化方法
  - 实现工作流状态持久化到数据库（使用 LeaveRequest.workflow_state JSONField）
  - 添加工作流恢复功能（从数据库恢复工作流实例）
  - 实现脚本引擎环境配置（支持 BPMN 脚本任务）
  - 添加组织架构查询函数（get_direct_manager, get_department_manager, get_role_members, get_effective_approver）
  - 移除内存存储，改为从数据库加载工作流状态
  - _需求：1.1, 1.2, 1.3, 3.1, 3.2, 3.3, 3.4_

- [ ]* 3.2 编写 SpiffWorkflow 集成单元测试
  - 在 leave_api/tests/ 创建 test_spiff_client.py
  - 测试工作流启动和状态保存
  - 测试工作流序列化和反序列化
  - 测试任务查询和完成
  - 测试脚本引擎函数调用
  - _需求：1.1, 1.2, 1.3_

- [ ]* 3.3 编写属性测试：流程启动一致性
  - 在 leave_api/tests/ 创建 test_properties.py
  - **属性 1：流程启动一致性**
  - **验证需求：1.1**
  - 使用 Hypothesis 生成随机请假申请
  - 验证 process_instance_id 正确保存
  - 验证工作流状态正确序列化
  - _需求：1.1_

### 阶段 4: 扩展审批数据模型

- [ ] 4.1 扩展 LeaveRequest 模型
  - 修改 leave_api/models.py 中的 LeaveRequest 模型
  - 添加 workflow_state 字段（JSONField，存储序列化的工作流状态）
  - 添加 workflow_spec_name 字段（替代 process_model_id）
  - 添加 leave_type、start_date、end_date、duration 字段
  - 添加 current_approver 外键（关联 Employee，需要先完成阶段 2）
  - 添加 completed_at 字段
  - 更新数据库迁移
  - _需求：2.1, 2.2_

- [ ] 4.2 实现审批相关数据模型
  - 在 leave_api/models.py 中创建 ApprovalHistory 模型（审批历史）
  - 创建 ApprovalProxy 模型（代理设置）
  - 创建 CCRecord 模型（抄送记录）
  - 创建 ApprovalRule 模型（审批规则）
  - 创建 WorkflowEventLog 模型（工作流事件日志）
  - 添加数据库索引和约束
  - 创建数据库迁移文件
  - _需求：7.1, 10.1, 6.1, 8.1, 15.1_

- [ ]* 4.3 编写审批模型单元测试
  - 在 leave_api/tests/ 创建 test_models.py
  - 测试 LeaveRequest 状态转换
  - 测试 ApprovalHistory 记录创建
  - 测试 ApprovalProxy 时间范围验证
  - 测试数据验证规则
  - _需求：2.1, 7.1, 10.1_

- [ ]* 4.4 编写属性测试：状态转换合法性
  - 在 leave_api/tests/test_properties.py 中添加
  - **属性 14：状态转换合法性**
  - **验证需求：15.3**
  - 使用 Hypothesis 生成随机状态转换
  - 验证只有合法的状态转换被允许（draft→pending→approved/rejected）
  - _需求：15.3_

### 阶段 5: 业务规则引擎

- [ ] 5.1 实现审批规则匹配逻辑
  - 在 leave_api 应用中创建 services/ 目录
  - 在 services/ 中创建 rule_service.py
  - 创建 ApprovalRuleService 类
  - 实现规则匹配算法（_match_rule 方法）
  - 实现规则选择算法（select_workflow_spec 方法）
  - 支持按优先级排序
  - 支持多条件匹配（请假类型、时长、部门、职级）
  - _需求：8.1, 8.2, 8.3_

- [ ]* 5.2 编写规则匹配单元测试
  - 在 leave_api/tests/ 创建 test_rule_service.py
  - 测试单条件匹配
  - 测试多条件匹配
  - 测试优先级排序
  - 测试默认规则
  - _需求：8.1, 8.2, 8.3, 8.5_

- [ ]* 5.3 编写属性测试：业务规则匹配唯一性
  - 在 leave_api/tests/test_properties.py 中添加
  - **属性 7：业务规则匹配唯一性**
  - **验证需求：8.2, 8.3, 8.5**
  - 使用 Hypothesis 生成随机规则和申请
  - 验证总是选择优先级最高的匹配规则
  - _需求：8.2, 8.3, 8.5_

### 阶段 6: 重构审批核心服务

- [ ] 6.1 重构审批服务核心逻辑
  - 在 leave_api/services/ 中创建 approval_service.py
  - 创建 ApprovalService 类
  - 重构 submit_leave_request 方法（整合规则匹配和工作流启动）
  - 实现 approve_task 方法（批准任务）
  - 实现 reject_task 方法（拒绝任务）
  - 实现 return_task 方法（退回任务）
  - 集成 SpiffWorkflow 持久化
  - 集成 ApprovalRuleService
  - 实现审批历史记录
  - _需求：2.1, 2.4, 2.5, 5.5, 5.6, 7.1_

- [ ] 6.2 重构现有 views.py 使用新的服务层
  - 修改 leave_api/views.py 中的 create_leave_request 使用 ApprovalService
  - 修改 approve_leave_request 使用 ApprovalService
  - 添加 reject_leave_request 视图
  - 添加 return_leave_request 视图
  - 保持 API 接口向后兼容
  - _需求：2.1, 2.4, 2.5_

- [ ]* 6.3 编写审批服务单元测试
  - 在 leave_api/tests/ 创建 test_approval_service.py
  - 测试提交申请流程
  - 测试批准/拒绝/退回操作
  - 测试审批历史记录
  - 测试错误处理
  - _需求：2.1, 2.4, 2.5, 7.1_

### 阶段 7: 代理人机制

- [ ] 7.1 实现代理人查找逻辑
  - 在 leave_api/services/ 中创建 proxy_service.py
  - 创建 ProxyService 类
  - 实现 get_effective_approver 方法
  - 检查代理时间范围
  - 检查代理人权限冲突
  - 实现冲突时的升级逻辑
  - _需求：10.2, 10.3, 10.4, 10.7_

- [ ]* 7.2 编写代理人单元测试
  - 在 leave_api/tests/ 创建 test_proxy_service.py
  - 测试时间范围内代理生效
  - 测试时间范围外代理不生效
  - 测试权限冲突检测
  - 测试升级逻辑
  - _需求：10.2, 10.4, 10.7_

- [ ]* 7.3 编写属性测试：代理人生效时间范围
  - 在 leave_api/tests/test_properties.py 中添加
  - **属性 9：代理人生效时间范围**
  - **验证需求：10.2, 10.4**
  - 使用 Hypothesis 生成随机代理设置和时间
  - 验证代理人只在时间范围内生效
  - _需求：10.2, 10.4_

- [ ]* 7.4 编写属性测试：代理人权限冲突检测
  - 在 leave_api/tests/test_properties.py 中添加
  - **属性 10：代理人权限冲突检测**
  - **验证需求：10.7**
  - 使用 Hypothesis 生成随机流程和代理设置
  - 验证权限冲突被正确检测和处理
  - _需求：10.7_

### 阶段 8: 工作流事件处理

- [ ] 8.1 实现工作流事件处理机制
  - 在 leave_api 应用中创建 signals.py
  - 使用 Django 信号机制处理工作流事件
  - 实现 handle_workflow_completed 信号处理器
  - 实现 handle_task_ready 信号处理器
  - 记录 WorkflowEventLog
  - 实现幂等性检查
  - _需求：1.4, 1.5, 15.1, 15.2, 15.3_

- [ ]* 8.2 编写工作流事件处理单元测试
  - 在 leave_api/tests/ 创建 test_signals.py
  - 测试事件触发和处理
  - 测试幂等性检查
  - 测试状态更新
  - 测试错误处理
  - _需求：15.1, 15.2, 15.3_

- [ ]* 8.3 编写属性测试：事件处理幂等性
  - 在 leave_api/tests/test_properties.py 中添加
  - **属性 13：事件处理幂等性**
  - **验证需求：15.2**
  - 使用 Hypothesis 生成随机事件
  - 验证多次处理只更新一次
  - _需求：15.2_

### 阶段 9: 审批历史记录

- [ ] 9.1 实现审批历史记录功能
  - 在 leave_api/serializers.py 中创建 ApprovalHistorySerializer
  - 在 leave_api/views.py 中添加审批历史查询 API（GET /api/leave-requests/{id}/history/）
  - 实现审批轨迹可视化数据 API
  - 支持按时间排序
  - 支持过滤和搜索
  - 确保所有审批操作自动记录 ApprovalHistory
  - _需求：7.1, 7.2, 7.3, 7.4, 7.5_

- [ ]* 9.2 编写属性测试：审批历史完整性
  - 在 leave_api/tests/test_properties.py 中添加
  - **属性 6：审批历史完整性**
  - **验证需求：7.1, 7.2, 7.4**
  - 使用 Hypothesis 生成随机审批操作序列
  - 验证所有操作都被记录
  - _需求：7.1, 7.2, 7.4_

### 阶段 10: 抄送功能

- [ ] 10.1 实现抄送功能
  - 在 leave_api/serializers.py 中创建 CCRecordSerializer
  - 在 leave_api/views.py 中添加抄送 API
  - 实现添加抄送人 API（POST /api/leave-requests/{id}/cc/）
  - 实现抄送记录查询 API（GET /api/leave-requests/{id}/cc/）
  - 在流程状态变化时通知抄送人
  - 实现抄送人只读权限控制
  - _需求：6.1, 6.2, 6.3, 6.4, 6.5_

- [ ]* 10.2 编写属性测试：抄送通知完整性
  - 在 leave_api/tests/test_properties.py 中添加
  - **属性 11：抄送通知完整性**
  - **验证需求：6.1, 6.2, 6.4**
  - 使用 Hypothesis 生成随机抄送设置
  - 验证所有抄送人都收到通知
  - _需求：6.1, 6.2, 6.4_

### 阶段 11: 通知系统

- [ ] 11.1 实现通知服务
  - 在 notifications 应用中创建 models.py
  - 创建 Notification 模型
  - 在 notifications/services/ 中创建 notification_service.py
  - 创建 NotificationService 类
  - 实现站内消息通知
  - 实现邮件通知（使用 Django send_mail）
  - 实现通知模板系统（使用 Django templates）
  - 在 notifications/templates/emails/ 中创建邮件模板
  - _需求：14.1, 14.2, 14.3, 14.4, 14.5_

- [ ] 11.2 实现通知 API
  - 在 notifications 应用中创建 serializers.py 和 views.py
  - 实现通知查询 API（GET /api/notifications/my-notifications/）
  - 实现标记已读 API（POST /api/notifications/{id}/mark-read/）
  - 创建 urls.py 并注册路由
  - _需求：14.1, 14.3_

- [ ]* 11.3 编写通知服务单元测试
  - 在 notifications/tests/ 创建 test_notification_service.py
  - 测试站内消息创建
  - 测试邮件发送（使用 Django mail.outbox）
  - 测试通知模板渲染
  - 测试失败重试机制
  - _需求：14.1, 14.2, 14.6_

- [ ]* 11.4 编写属性测试：通知发送完整性
  - 在 notifications/tests/ 创建 test_properties.py
  - **属性 15：通知发送完整性**
  - **验证需求：14.1, 14.2**
  - 使用 Hypothesis 生成随机审批事件
  - 验证相关人员都收到通知
  - _需求：14.1, 14.2_

- [ ] 11.5 实现异步通知任务
  - 在 notifications 应用中创建 tasks.py
  - 创建 Celery 任务 send_email_notification
  - 创建 Celery 任务 send_in_app_notification
  - 配置任务重试策略
  - 在 ApprovalService 中集成异步通知
  - _需求：14.1, 14.2, 14.6_

### 阶段 12: 超时处理

- [ ] 12.1 实现超时检查和提醒
  - 在 leave_api 应用中创建 tasks.py
  - 创建 Celery Beat 定时任务 check_timeout_tasks
  - 实现超时任务检查逻辑
  - 实现超时提醒通知
  - 实现催办功能 API（POST /api/approval-tasks/{task_id}/urge/）
  - 配置 Celery Beat 调度（每小时执行一次）
  - 在 leave_system/leave_system/settings.py 中配置 CELERY_BEAT_SCHEDULE
  - _需求：9.1, 9.2, 9.4, 9.5_

- [ ]* 12.2 编写属性测试：超时提醒触发正确性
  - 在 leave_api/tests/test_properties.py 中添加
  - **属性 8：超时提醒触发正确性**
  - **验证需求：9.2**
  - 使用 Hypothesis 生成随机任务和超时配置
  - 验证超时任务触发提醒
  - _需求：9.2_

### 阶段 13: 重构和扩展审批任务 API

- [ ] 13.1 重构审批任务 REST API
  - 在 leave_api/serializers.py 中创建 ApprovalTaskSerializer
  - 重构 leave_api/views.py 中的审批 API
  - 增强查询我的待办任务 API（GET /api/approval-tasks/my-tasks/）
  - 重构批准任务 API 使用 ApprovalService（POST /api/approval-tasks/{task_id}/approve/）
  - 实现拒绝任务 API（POST /api/approval-tasks/{task_id}/reject/）
  - 实现退回任务 API（POST /api/approval-tasks/{task_id}/return/）
  - 实现加签 API（POST /api/approval-tasks/{task_id}/add-sign/）
  - 实现转签 API（POST /api/approval-tasks/{task_id}/transfer/）
  - 添加权限验证（使用 DRF permissions）
  - _需求：2.3, 2.4, 2.5, 5.1, 5.2, 5.3, 5.4, 9.4_

- [ ]* 13.2 编写审批任务 API 单元测试
  - 在 leave_api/tests/ 创建 test_approval_api.py
  - 测试权限控制
  - 测试各种审批操作
  - 测试错误处理
  - _需求：2.3, 2.4, 2.5, 5.1, 5.2, 5.3_

### 阶段 14: 代理设置 API

- [ ] 14.1 实现代理设置 REST API
  - 在 leave_api/serializers.py 中创建 ApprovalProxySerializer
  - 在 leave_api/views.py 中添加代理设置 API
  - 实现设置代理 API（POST /api/proxy-settings/）
  - 实现查询代理设置 API（GET /api/proxy-settings/my-settings/）
  - 实现取消代理 API（DELETE /api/proxy-settings/{id}/）
  - 实现查询有效审批人 API（GET /api/employees/{id}/effective-approver/）
  - 添加权限验证
  - _需求：10.1, 10.5_

- [ ]* 14.2 编写代理设置 API 单元测试
  - 在 leave_api/tests/test_proxy_api.py 中创建
  - 测试代理设置创建
  - 测试代理取消
  - 测试权限控制
  - _需求：10.1, 10.5_

### 阶段 15: BPMN 流程设计和扩展

- [ ] 15.1 扩展基础审批流程
  - 修改现有 process_models/admin/admin/admin.bpmn
  - 添加审批人动态分配脚本任务
  - 配置超时边界事件（24小时）
  - 配置决策网关（批准/拒绝）
  - 添加结束事件（修复当前流程缺少结束事件的问题）
  - 测试流程执行
  - _需求：2.1, 2.2, 2.3, 2.4, 2.5, 9.1, 9.2_

- [ ] 15.2 设计多级审批流程
  - 在 process_models/admin/ 中创建 multi_level_approval/ 目录
  - 创建 multi_level_approval.bpmn
  - 配置部门主管 → 总监 → HR → 总经理审批链
  - 配置条件网关根据时长决定审批层级
  - 为每个审批节点配置超时边界事件
  - 配置脚本任务动态分配审批人
  - 创建 process_model.json 元数据文件
  - _需求：2.1, 2.2, 8.1, 8.2_

- [ ] 15.3 设计会签流程
  - 在 process_models/admin/ 中创建 countersign_approval/ 目录
  - 创建 countersign_approval.bpmn
  - 配置 Multi-instance User Task（并行多实例）
  - 配置会签完成条件（全部通过或按比例）
  - 配置一票否决机制
  - 配置动态审批人列表
  - 创建 process_model.json 元数据文件
  - _需求：4.1, 4.2, 4.3, 4.7_

- [ ]* 15.4 编写属性测试：会签完成条件
  - 在 leave_api/tests/test_properties.py 中添加
  - **属性 3：会签完成条件**
  - **验证需求：4.1, 4.3**
  - 使用 Hypothesis 生成随机会签场景
  - 验证会签逻辑正确
  - _需求：4.1, 4.3_

- [ ] 15.5 设计或签流程
  - 在 process_models/admin/ 中创建 or_sign_approval/ 目录
  - 创建 or_sign_approval.bpmn
  - 配置包容网关实现或签
  - 配置任意一人通过即可继续
  - 配置自动取消其他任务
  - 创建 process_model.json 元数据文件
  - _需求：4.4, 4.5, 4.6_

- [ ]* 15.6 编写属性测试：或签完成条件
  - 在 leave_api/tests/test_properties.py 中添加
  - **属性 4：或签完成条件**
  - **验证需求：4.4, 4.5, 4.6**
  - 使用 Hypothesis 生成随机或签场景
  - 验证或签逻辑正确
  - _需求：4.4, 4.5, 4.6_

- [ ] 15.7 设计并行分支流程
  - 在 process_models/admin/ 中创建 parallel_branches_approval/ 目录
  - 创建 parallel_branches_approval.bpmn
  - 配置并行网关分支（财务、HR、行政）
  - 配置并行网关汇聚
  - 配置分支独立审批
  - 创建 process_model.json 元数据文件
  - _需求：13.1, 13.2, 13.3_

- [ ]* 15.8 编写属性测试：并行分支独立性
  - 在 leave_api/tests/test_properties.py 中添加
  - **属性 12：并行分支独立性**
  - **验证需求：13.2, 13.3**
  - 使用 Hypothesis 生成随机并行场景
  - 验证分支独立性和汇聚逻辑
  - _需求：13.2, 13.3_

### 阶段 16: 审批规则配置后台

- [ ] 16.1 实现审批规则管理 API
  - 在 leave_api/serializers.py 中创建 ApprovalRuleSerializer
  - 在 leave_api/views.py 中添加规则管理 API
  - 实现规则 CRUD API（使用 DRF ViewSets）
  - 实现规则优先级调整 API（PATCH /api/approval-rules/{id}/priority/）
  - 实现规则启用/禁用 API（PATCH /api/approval-rules/{id}/toggle/）
  - 实现规则测试/模拟 API（POST /api/approval-rules/simulate/）
  - _需求：11.1, 11.2, 11.3, 11.4, 11.6_

- [ ]* 16.2 编写规则管理 API 单元测试
  - 在 leave_api/tests/ 创建 test_rule_api.py
  - 测试规则创建和验证
  - 测试优先级排序
  - 测试规则模拟
  - _需求：11.1, 11.3, 11.4, 11.6_

### 阶段 17: 前端界面（可选）

- [ ]* 17.1 扩展申请人界面
  - 修改现有 leave_system/static/index.html
  - 增强请假申请表单（添加请假类型、日期选择）
  - 改进我的申请列表展示
  - 实现申请详情和历史查看
  - 实现取消申请功能
  - _需求：2.1, 7.2, 7.3_

- [ ]* 17.2 实现审批人界面
  - 创建审批人待办任务页面（approver.html）
  - 实现任务详情查看
  - 实现批准/拒绝/退回操作界面
  - 实现加签/转签功能界面
  - 实现催办功能
  - _需求：2.3, 2.4, 2.5, 5.1, 5.2, 5.3, 9.4_

- [ ]* 17.3 实现管理员界面
  - 创建管理员界面（admin_panel.html）
  - 实现组织架构管理界面
  - 实现审批规则配置界面
  - 实现流程监控界面
  - 实现系统日志查看
  - _需求：11.1, 11.2, 11.3, 12.1, 12.2, 12.3_

### 阶段 18: 集成测试

- [ ]* 18.1 编写端到端集成测试
  - 在 leave_system/ 创建 integration_tests/ 目录
  - 创建 test_complete_workflow.py
  - 测试完整的审批流程（提交 → 审批 → 完成）
  - 测试多级审批流程
  - 测试会签流程
  - 测试或签流程
  - 测试并行分支流程
  - 测试退回和重新提交
  - 测试代理人场景
  - 测试超时提醒
  - _需求：所有_

- [ ]* 18.2 编写属性测试：审批人动态分配正确性
  - 在 leave_api/tests/test_properties.py 中添加
  - **属性 2：审批人动态分配正确性**
  - **验证需求：3.1, 3.2, 3.3, 3.4**
  - 使用 Hypothesis 生成随机组织架构和规则
  - 验证审批人分配逻辑正确
  - _需求：3.1, 3.2, 3.3, 3.4_

- [ ]* 18.3 编写属性测试：退回后流程路径一致性
  - 在 leave_api/tests/test_properties.py 中添加
  - **属性 5：退回后流程路径一致性**
  - **验证需求：5.6, 5.7, 5.9**
  - 使用 Hypothesis 生成随机退回场景
  - 验证退回后流程路径正确
  - _需求：5.6, 5.7, 5.9_

### 阶段 19: 性能优化（可选）

- [ ]* 19.1 实现缓存策略
  - 在 leave_system/requirements.txt 中添加 django-redis
  - 在 leave_system/leave_system/settings.py 中配置 Redis 缓存后端
  - 实现用户待办任务缓存
  - 实现组织架构缓存
  - 实现审批规则缓存
  - 实现缓存失效机制
  - _需求：所有（性能优化）_

- [ ]* 19.2 优化数据库查询
  - 添加必要的数据库索引
  - 优化 N+1 查询问题
  - 使用 select_related 和 prefetch_related
  - _需求：所有（性能优化）_

### 阶段 20: 部署和监控（可选）

- [ ]* 20.1 配置生产环境
  - 在项目根目录创建 docker-compose.yml
  - 创建 Dockerfile
  - 配置 PostgreSQL 数据库
  - 配置 Redis 服务
  - 配置 Nginx 反向代理
  - 配置环境变量
  - _需求：所有_

- [ ]* 20.2 配置监控和日志
  - 增强 leave_system/leave_system/settings.py 中的 Django 日志系统配置
  - 配置工作流事件日志
  - 配置 Celery 任务日志
  - 配置错误告警
  - _需求：所有_

- [ ]* 20.3 配置 CI/CD
  - 在项目根目录创建 .github/workflows/ 目录
  - 创建 ci.yml 工作流
  - 配置自动化测试
  - 配置自动化部署
  - _需求：所有_

### 阶段 21: 检查点 - 确保所有测试通过

- [ ] 21.1 运行所有单元测试
  - 在 leave_system/ 目录运行 pytest
  - 确保所有单元测试通过
  - 检查测试覆盖率（目标 > 80%）
  - 修复失败的测试

- [ ] 21.2 运行所有属性测试
  - 确保所有属性测试通过（100次迭代）
  - 检查是否发现边界情况
  - 修复属性测试发现的问题

- [ ] 21.3 运行集成测试
  - 确保端到端流程正常工作
  - 验证 Django 和 SpiffWorkflow 集成正常
  - 验证通知系统正常工作

- [ ] 21.4 用户验收测试
  - 与用户确认功能是否满足需求
  - 收集用户反馈
  - 根据反馈进行调整

## 注意事项

1. **任务标记说明**：
   - `*` 标记的任务为可选任务（主要是测试相关和优化相关）
   - 核心实现任务必须完成
   - 可选任务建议完成以确保系统质量

2. **测试策略**：
   - 单元测试：验证具体功能和边界条件
   - 属性测试：验证通用正确性属性（每个至少100次迭代）
   - 集成测试：验证端到端流程

3. **开发顺序**：
   - 按阶段顺序开发（阶段 1 → 阶段 21）
   - 每个阶段内按任务编号顺序开发
   - 每个任务完成后运行相关测试
   - 在检查点（阶段 21）确保所有测试通过

4. **现有代码重构**：
   - 保留现有 leave_system 项目结构
   - 扩展现有 LeaveRequest 模型而非重新创建
   - 重构现有 API 以使用新的服务层
   - 保持向后兼容性

5. **SpiffWorkflow 集成**：
   - 使用 SpiffWorkflow 2.0.1 库（已安装）而非 SpiffArena 微服务
   - BPMN 文件存储在 process_models/ 目录
   - 工作流状态持久化到数据库（LeaveRequest.workflow_state JSONField）
   - 使用 Django 信号处理工作流事件

6. **增量开发**：
   - 每个任务都构建在前一个任务的基础上
   - 避免跳过任务
   - 及时提交代码到版本控制系统

7. **数据库迁移**：
   - 每次修改模型后创建迁移文件（python manage.py makemigrations）
   - 测试迁移的向前和向后兼容性
   - 在生产环境应用迁移前备份数据

8. **依赖管理**：
   - 所有新依赖添加到 leave_system/requirements.txt
   - 使用 pip install -r requirements.txt 安装依赖
   - 保持依赖版本明确

9. **文件路径约定**：
   - Django 应用：leave_system/{app_name}/
   - 服务层：leave_system/{app_name}/services/
   - 测试：leave_system/{app_name}/tests/
   - BPMN 文件：process_models/{group}/{model}/{model}.bpmn
