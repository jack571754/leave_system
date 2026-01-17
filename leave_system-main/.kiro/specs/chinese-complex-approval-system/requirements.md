# 需求文档：中国式复杂审批系统

## 简介

本文档描述了一个基于 Django 与 SpiffWorkflow 工作流引擎集成的企业级复杂审批系统。该系统旨在支持中国企业常见的多级审批、会签或签、加签转签、条件路由等复杂审批场景，从简单的单级审批扩展为功能完整的企业审批解决方案。

### 架构说明

SpiffWorkflow 作为工作流引擎库集成在 Django 应用中，负责流程编排和执行。Django 系统通过 SpiffWorkflow API 管理工作流实例，负责业务数据存储、用户权限管理和前端展示。系统通过以下方式协作：

1. **流程启动**：Django 使用 SpiffWorkflow 启动流程实例，并保存 workflow_instance_id
2. **任务查询**：Django 通过 SpiffWorkflow 查询用户的待办任务
3. **任务完成**：Django 通过 SpiffWorkflow 完成任务并推进流程
4. **状态回调**：SpiffWorkflow 通过事件机制通知 Django 更新业务状态

## 术语表

- **Approval_System**: 审批系统，负责处理审批流程的核心系统（Django 端）
- **Workflow_Engine**: 工作流引擎，基于 SpiffWorkflow 的 BPMN 2.0 引擎（集成在 Django 中）
- **Workflow_Instance**: 工作流实例，SpiffWorkflow 中运行的具体流程实例
- **User_Task**: 用户任务，SpiffWorkflow 中需要人工处理的任务节点
- **Service_Task**: 服务任务，SpiffWorkflow 中自动执行的任务节点
- **Script_Task**: 脚本任务，SpiffWorkflow 中执行 Python 脚本的任务节点
- **Approver**: 审批人，负责审批任务的用户
- **Applicant**: 申请人，发起审批流程的用户
- **Approval_Node**: 审批节点，审批流程中的一个审批环节
- **Organization_Structure**: 组织架构，包含部门、员工、职级等信息
- **Approval_Chain**: 审批链路，从申请到最终批准的完整审批路径
- **Countersign**: 会签，多个审批人都需要同意的审批方式（BPMN 并行网关）
- **Or_Sign**: 或签，多个审批人任意一个同意即可的审批方式（BPMN 包容网关）
- **Add_Sign**: 加签，当前审批人临时增加其他审批人
- **Transfer_Sign**: 转签，将审批任务转给其他人处理
- **Return**: 退回，将审批退回到上一级或申请人
- **CC**: 抄送，通知相关人员但不需要审批
- **Proxy**: 代理人，可以代替审批人进行审批的用户
- **Business_Rule**: 业务规则，根据条件自动确定审批路径的规则（BPMN 网关条件）
- **Approval_History**: 审批历史，记录审批过程中所有操作的日志（Django 端存储）
- **Timeout_Handler**: 超时处理器，处理审批超时的机制（BPMN 定时器事件）
- **Notification_System**: 通知系统，负责发送审批通知的子系统（Django 端）

## 需求

### 需求 1：Django 与 SpiffWorkflow 集成

**用户故事：** 作为系统架构师，我希望 Django 系统能够正确集成 SpiffWorkflow 工作流引擎，以便实现业务数据与工作流逻辑的协作。

#### 验收标准

1. WHEN 申请人在 Django 系统提交申请 THEN THE Approval_System SHALL 使用 SpiffWorkflow 启动流程实例并保存返回的 workflow_instance_id
2. WHEN Django 需要查询用户待办任务 THEN THE Approval_System SHALL 通过 SpiffWorkflow 根据用户标识查询该用户的所有 User_Task
3. WHEN 审批人在 Django 系统提交审批 THEN THE Approval_System SHALL 通过 SpiffWorkflow 完成对应的 User_Task 并传递审批数据
4. WHEN SpiffWorkflow 流程节点完成 THEN THE Workflow_Engine SHALL 通过事件机制通知 Django 更新业务状态
5. WHEN Django 接收到 SpiffWorkflow 事件通知 THEN THE Approval_System SHALL 更新对应申请的状态
6. WHEN Django 需要查询流程状态 THEN THE Approval_System SHALL 通过 SpiffWorkflow 获取 Workflow_Instance 的当前状态和变量

### 需求 2：多级审批链路

**用户故事：** 作为申请人，我希望系统能够根据我的请假时长和部门自动确定审批层级，以便我的申请能够按照公司规定流转到正确的审批人。

#### 验收标准

1. WHEN 申请人提交请假申请 THEN THE Approval_System SHALL 根据请假时长、部门、职级自动确定审批层级
2. WHEN 审批层级确定后 THEN THE Workflow_Engine SHALL 在 BPMN 流程中按顺序创建审批节点（部门主管 → 总监 → HR → 总经理）
3. WHEN 审批人在审批节点进行操作 THEN THE Approval_System SHALL 支持批准、拒绝、退回三种操作
4. WHEN 审批人批准当前节点 THEN THE Workflow_Engine SHALL 自动流转到下一个审批节点
5. WHEN 审批人拒绝当前节点 THEN THE Workflow_Engine SHALL 终止整个审批流程并通知 Django 系统
6. WHEN 所有审批节点都批准 THEN THE Workflow_Engine SHALL 将流程标记为完成并通知 Django 系统

### 需求 3：审批人动态分配

**用户故事：** 作为系统管理员，我希望系统能够根据组织架构自动查找审批人，以便审批流程能够自动适应组织变化，无需手动配置每个申请的审批人。

#### 验收标准

1. WHEN 审批节点需要确定审批人 THEN THE Approval_System SHALL 根据组织架构自动查找符合条件的审批人
2. WHEN 审批人规则为"直属上级" THEN THE Approval_System SHALL 查找申请人的直属上级作为审批人
3. WHEN 审批人规则为"部门负责人" THEN THE Approval_System SHALL 查找申请人所在部门的负责人作为审批人
4. WHEN 审批人规则为"特定角色" THEN THE Approval_System SHALL 查找具有该角色的所有用户作为审批人
5. WHEN 找不到符合条件的审批人 THEN THE Approval_System SHALL 返回错误并通知系统管理员
6. WHEN 审批人规则配置更新 THEN THE Approval_System SHALL 在新的审批流程中应用新规则

### 需求 4：会签与或签

**用户故事：** 作为审批流程设计者，我希望系统支持会签和或签两种审批方式，以便在需要多人共同决策或任意一人决策的场景中使用。

#### 验收标准

1. WHEN 审批节点配置为会签模式 THEN THE Workflow_Engine SHALL 使用 BPMN Multi-instance User Task 要求所有指定的审批人都同意才能通过
2. WHEN 会签节点配置通过阈值 THEN THE Workflow_Engine SHALL 支持按比例通过（如 70% 同意即通过）或全部通过
3. WHEN 会签节点配置一票否决 THEN THE Workflow_Engine SHALL 在任意一个审批人拒绝时立即终止整个审批流程
4. WHEN 审批节点配置为或签模式 THEN THE Workflow_Engine SHALL 使用 BPMN 包容网关允许任意一个审批人同意即可通过
5. WHEN 或签节点中第一个审批人同意 THEN THE Workflow_Engine SHALL 自动流转到下一个节点，其他审批人的任务自动取消
6. WHEN 或签节点中所有审批人都拒绝 THEN THE Workflow_Engine SHALL 终止整个审批流程
7. WHEN 配置会签或或签节点 THEN THE Approval_System SHALL 支持在 BPMN 流程中动态指定审批人列表

### 需求 5：加签、转签、退回

**用户故事：** 作为审批人，我希望能够在审批过程中灵活地加签其他人、转签给其他人或退回申请，以便处理复杂的审批场景。

#### 验收标准

1. WHEN 审批人选择加签操作 THEN THE Approval_System SHALL 允许审批人指定一个或多个加签人
2. WHEN 加签人完成审批 THEN THE Approval_System SHALL 将审批任务返回给原审批人继续处理
3. WHEN 审批人选择转签操作 THEN THE Approval_System SHALL 将当前审批任务转移给指定的其他审批人
4. WHEN 转签完成 THEN THE Approval_System SHALL 记录转签操作并通知新的审批人
5. WHEN 审批人选择退回操作 THEN THE Approval_System SHALL 支持退回到上一级审批人或退回给申请人修改
6. WHEN 申请被退回给申请人 THEN THE Approval_System SHALL 允许申请人修改申请内容后重新提交
7. WHEN 申请人修改后重新提交 THEN THE Approval_System SHALL 根据配置决定是从头开始流程还是从退回节点继续
8. WHEN 申请被退回到上一级 THEN THE Approval_System SHALL 将审批任务发送给上一级审批人重新审批
9. WHEN 配置退回规则 THEN THE Approval_System SHALL 支持管理员配置退回后的流程走向（重新开始或继续）

### 需求 6：抄送与知会

**用户故事：** 作为申请人或审批人，我希望能够将审批流程抄送给相关人员，以便他们了解审批进度，但不需要他们进行审批操作。

#### 验收标准

1. WHEN 申请人提交申请时指定抄送人 THEN THE Approval_System SHALL 将审批流程抄送给指定的人员
2. WHEN 审批人在审批时指定抄送人 THEN THE Approval_System SHALL 将当前审批节点的信息抄送给指定的人员
3. WHEN 抄送人查看抄送信息 THEN THE Approval_System SHALL 显示完整的审批流程和当前状态，但不允许进行审批操作
4. WHEN 审批流程状态变化 THEN THE Approval_System SHALL 自动通知所有抄送人最新的审批进度
5. WHEN 抄送人列表更新 THEN THE Approval_System SHALL 通知新增的抄送人

### 需求 7：审批历史与轨迹

**用户故事：** 作为申请人或审批人，我希望能够查看完整的审批历史和轨迹，以便了解审批流程的每一步操作和当前状态。

#### 验收标准

1. WHEN 审批流程中发生任何操作 THEN THE Approval_System SHALL 记录操作人、操作时间、操作类型、审批意见到审批历史
2. WHEN 用户查看审批历史 THEN THE Approval_System SHALL 按时间顺序显示所有审批操作记录
3. WHEN 用户查看审批轨迹 THEN THE Approval_System SHALL 以可视化方式展示审批流程的完整路径和当前节点
4. WHEN 审批节点包含审批意见 THEN THE Approval_System SHALL 在审批历史中显示审批意见内容
5. WHEN 审批流程完成或终止 THEN THE Approval_System SHALL 保留完整的审批历史记录供后续查询

### 需求 8：条件路由与业务规则

**用户故事：** 作为系统管理员，我希望能够配置复杂的业务规则来自动确定审批路径，以便系统能够根据不同的条件（如请假时长、部门、职级）自动选择合适的审批流程。

#### 验收标准

1. WHEN 系统管理员配置业务规则 THEN THE Approval_System SHALL 支持基于请假时长、部门、职级、请假类型等条件的规则配置
2. WHEN 申请人提交申请 THEN THE Approval_System SHALL 根据业务规则自动计算并确定审批路径
3. WHEN 业务规则包含多个条件 THEN THE Approval_System SHALL 按优先级顺序评估规则并选择第一个匹配的规则
4. WHEN 业务规则更新 THEN THE Approval_System SHALL 在新的审批流程中应用新规则，已有流程不受影响
5. WHEN 没有匹配的业务规则 THEN THE Approval_System SHALL 使用默认的审批流程
6. WHEN 业务规则配置错误 THEN THE Approval_System SHALL 返回错误信息并阻止规则保存

### 需求 9：催办与超时处理

**用户故事：** 作为申请人，我希望系统能够在审批超时时自动提醒审批人或升级到上级，以便我的申请能够及时得到处理。

#### 验收标准

1. WHEN 审批节点创建时 THEN THE Approval_System SHALL 根据配置设置超时时间
2. WHEN 审批任务超过设定时间未处理 THEN THE Approval_System SHALL 自动发送提醒通知给审批人
3. WHEN 审批任务超时后仍未处理 THEN THE Approval_System SHALL 支持自动升级到上级审批人
4. WHEN 申请人选择催办操作 THEN THE Approval_System SHALL 立即发送催办通知给当前审批人
5. WHEN 审批人在超时后完成审批 THEN THE Approval_System SHALL 记录超时信息到审批历史
6. WHEN 系统管理员配置超时规则 THEN THE Approval_System SHALL 支持为不同类型的审批节点设置不同的超时时间

### 需求 10：代理人机制

**用户故事：** 作为审批人，我希望能够在出差或休假时设置代理人，以便我不在时审批流程能够继续进行。

#### 验收标准

1. WHEN 审批人设置代理人 THEN THE Approval_System SHALL 记录代理人信息和代理时间范围
2. WHEN 审批任务分配给设置了代理人的审批人 THEN THE Approval_System SHALL 在代理时间范围内将任务分配给代理人
3. WHEN 代理人完成审批 THEN THE Approval_System SHALL 记录实际操作人为代理人，但标注是代理原审批人操作
4. WHEN 代理时间范围结束 THEN THE Approval_System SHALL 自动停止代理，新的审批任务分配给原审批人
5. WHEN 审批人取消代理设置 THEN THE Approval_System SHALL 立即停止代理，未完成的任务返回给原审批人
6. WHEN 代理人也设置了代理 THEN THE Approval_System SHALL 不支持二级代理，任务仍分配给一级代理人
7. WHEN 代理人在流程中既是原审批人又是代理人 THEN THE Approval_System SHALL 检测权限冲突并自动跳过该节点或升级到更高一级审批人

### 需求 11：审批配置后台

**用户故事：** 作为系统管理员，我希望有一个可视化的配置后台来管理审批流程，以便我能够灵活地配置和调整审批规则，而不需要修改代码。

#### 验收标准

1. WHEN 系统管理员访问配置后台 THEN THE Approval_System SHALL 提供可视化的流程配置界面
2. WHEN 系统管理员配置审批流程 THEN THE Approval_System SHALL 支持拖拽方式创建审批节点和连接线
3. WHEN 系统管理员配置审批节点 THEN THE Approval_System SHALL 支持设置审批人规则、超时时间、会签或签模式等参数
4. WHEN 系统管理员保存流程配置 THEN THE Approval_System SHALL 验证流程配置的完整性和正确性
5. WHEN 系统管理员发布新版本流程 THEN THE Approval_System SHALL 创建新版本并保留历史版本
6. WHEN 系统管理员测试流程 THEN THE Approval_System SHALL 提供流程模拟功能，允许输入测试数据查看流程走向

### 需求 12：组织架构管理

**用户故事：** 作为系统管理员，我希望能够管理完整的组织架构信息，以便审批系统能够准确地查找审批人和应用审批规则。

#### 验收标准

1. WHEN 系统管理员管理部门 THEN THE Approval_System SHALL 支持树形结构的部门管理，包括创建、修改、删除、移动部门
2. WHEN 系统管理员管理员工 THEN THE Approval_System SHALL 支持录入员工的姓名、邮箱、部门、职级、直属上级等信息
3. WHEN 系统管理员管理角色 THEN THE Approval_System SHALL 支持创建和分配角色（如部门主管、HR、财务等）
4. WHEN 系统管理员删除部门 THEN THE Approval_System SHALL 检查该部门是否有员工，如有则阻止删除或提示转移员工
5. WHEN 系统管理员修改员工的部门或上级 THEN THE Approval_System SHALL 更新组织架构关系并影响后续的审批人查找
6. WHEN 系统需要从外部系统同步组织架构 THEN THE Approval_System SHALL 提供 API 接口支持批量导入和更新组织架构数据

### 需求 13：多分支同步审批

**用户故事：** 作为审批流程设计者，我希望系统支持多分支同步审批，以便在需要多个部门或多个审批人同时并行审批的场景中使用，提高审批效率。

#### 验收标准

1. WHEN 审批流程到达分支节点 THEN THE Approval_System SHALL 同时创建多个并行的审批分支
2. WHEN 多个审批分支并行执行 THEN THE Approval_System SHALL 独立处理每个分支的审批任务，互不影响
3. WHEN 所有并行分支都完成审批 THEN THE Approval_System SHALL 汇聚到下一个节点继续流程
4. WHEN 任意一个并行分支被拒绝 THEN THE Approval_System SHALL 根据配置决定是否终止整个流程或仅终止该分支
5. WHEN 并行分支中包含不同的审批人 THEN THE Approval_System SHALL 为每个分支独立分配审批人
6. WHEN 并行分支汇聚时 THEN THE Approval_System SHALL 收集所有分支的审批结果并记录到审批历史

### 需求 14：通知系统

**用户故事：** 作为用户，我希望在审批流程的关键节点收到及时的通知，以便我能够及时处理审批任务或了解审批进度。

#### 验收标准

1. WHEN 审批任务分配给审批人 THEN THE Notification_System SHALL 发送邮件通知和站内消息通知给审批人
2. WHEN 审批流程状态变化 THEN THE Notification_System SHALL 通知申请人和相关抄送人
3. WHEN 审批任务超时 THEN THE Notification_System SHALL 发送催办通知给审批人
4. WHEN 系统管理员配置通知模板 THEN THE Notification_System SHALL 支持自定义邮件和站内消息的模板内容
5. WHEN 用户查看站内消息 THEN THE Notification_System SHALL 显示未读消息数量并支持标记为已读
6. WHEN 邮件发送失败 THEN THE Notification_System SHALL 记录失败日志并支持重试机制

### 需求 15：幂等性与补偿机制

**用户故事：** 作为系统架构师，我希望系统能够处理工作流执行异常、状态不一致等异常情况，以便保证数据一致性和系统稳定性。

#### 验收标准

1. WHEN SpiffWorkflow 触发状态变更事件 THEN THE Approval_System SHALL 验证事件的有效性
2. WHEN Django 接收到重复的状态变更事件 THEN THE Approval_System SHALL 通过幂等性检查确保同一任务多次处理结果一致
3. WHEN Django 更新业务状态前 THEN THE Approval_System SHALL 校验当前业务状态的合法性（如已完成的申请不能再被修改为拒绝）
4. WHEN 工作流执行出现异常 THEN THE Approval_System SHALL 记录异常信息并支持事务回滚
5. WHEN 状态更新失败 THEN THE Approval_System SHALL 记录失败日志并发送告警通知给系统管理员
6. WHEN Django 系统恢复后 THEN THE Approval_System SHALL 支持手动触发状态同步以修复不一致的数据
