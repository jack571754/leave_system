# 🎨 BPMN 流程设计器使用指南

## 访问地址

**BPMN 设计器**: http://localhost:8000/bpmn-designer/

或从管理面板进入：
1. 访问 http://localhost:8000/dashboard/
2. 点击 **🎨 BPMN 配置** 标签
3. 点击 **🚀 立即打开设计器** 按钮

---

## ✨ 核心功能

### 1. 可视化流程设计
- 🎯 拖拽式设计界面
- 📊 基于 bpmn-js 的专业建模器
- 🔄 实时预览和编辑

### 2. 智能属性面板
- 📝 右侧属性编辑面板
- 🎨 深色主题界面
- 🔧 根据元素类型动态显示属性

### 3. 代码编辑器（CodeMirror）
- 🌈 语法高亮（Python、XML、JavaScript）
- 📏 行号显示
- 🎯 自动补全和括号匹配
- 🌙 Monokai 主题

---

## 🛠️ 功能详解

### 顶部工具栏

| 按钮 | 功能 | 说明 |
|------|------|------|
| 📄 新建 | 创建新流程 | 创建一个空白的 BPMN 流程图 |
| 📂 打开 | 打开文件 | 从本地加载 BPMN 文件 |
| 💾 保存 | 保存流程 | 下载 BPMN 文件到本地 |
| ⬇️ 下载 | 下载文件 | 导出 BPMN XML 文件 |
| 🖼️ 导出SVG | 导出图片 | 导出流程图为 SVG 格式 |
| 🏠 返回 | 返回首页 | 返回管理面板 |

### 画布工具栏

| 按钮 | 功能 | 快捷键 |
|------|------|--------|
| 🔍+ | 放大 | - |
| 🔍- | 缩小 | - |
| ⚡ | 适应画布 | - |
| ↶ | 撤销 | Ctrl+Z |
| ↷ | 重做 | Ctrl+Y |

### 属性面板

#### 基本属性（所有元素）
- **ID**: 元素唯一标识符（只读）
- **名称**: 元素显示名称

#### 用户任务 (UserTask)

**表单配置**
- `formJsonSchemaFilename`: 表单 Schema 文件名
- `formUiSchemaFilename`: 表单 UI Schema 文件名

**前置脚本 (Pre-Script)**
- 在任务执行前运行的 Python 代码
- 用于设置变量、分配审批人等
- 支持语法高亮和自动补全

示例：
```python
# 动态分配审批人
assigned_to = "manager@company.com"

# 设置变量
approval_level = 1
```

**后置脚本 (Post-Script)**
- 在任务完成后运行的 Python 代码
- 用于处理任务结果、更新状态等

示例：
```python
# 处理审批结果
if action == "approve":
    status = "approved"
else:
    status = "rejected"
```

#### 脚本任务 (ScriptTask)

**脚本内容**
- 完整的 Python 脚本
- 用于执行业务逻辑

示例：
```python
# 计算审批级别
if leave_hours > 24:
    approval_level = 2
else:
    approval_level = 1

# 查找审批人
assigned_to = get_direct_manager(user_email)
```

#### 条件流 (SequenceFlow)

**条件表达式**
- Python 表达式
- 返回 True/False 决定流转

示例：
```python
# 根据请假时长判断
leave_hours > 24

# 根据密码类型判断
password_type == "critical" and user_level == "admin"

# 根据审批结果判断
action == "approve"
```

#### 网关 (Gateway)

**排他网关 (ExclusiveGateway)**
- 只选择一条满足条件的路径
- 需要在出口流上设置条件表达式
- 可以设置默认流

**并行网关 (ParallelGateway)**
- 同时执行所有出口流
- 用于并行审批

---

## 📝 使用流程

### 1. 创建新流程

1. 点击 **📄 新建** 按钮
2. 系统自动创建基础流程模板
3. 包含：开始事件 → 用户任务 → 结束事件

### 2. 添加元素

1. 从左侧工具面板拖拽元素到画布
2. 或点击现有元素的快捷菜单添加

**常用元素**：
- ⭕ 开始事件 (Start Event)
- 📋 用户任务 (User Task)
- 📝 脚本任务 (Script Task)
- 🔀 排他网关 (Exclusive Gateway)
- ⚡ 并行网关 (Parallel Gateway)
- 🔚 结束事件 (End Event)
- ➡️ 连接线 (Sequence Flow)

### 3. 配置属性

1. 点击画布上的元素
2. 右侧属性面板自动显示该元素的属性
3. 编辑属性值
4. 修改自动保存到流程中

### 4. 编辑脚本

1. 选择用户任务或脚本任务
2. 在属性面板找到脚本编辑器
3. 输入 Python 代码
4. 享受语法高亮和自动补全

### 5. 设置条件

1. 选择连接线（Sequence Flow）
2. 在属性面板的条件编辑器中输入表达式
3. 使用 Python 语法

### 6. 保存流程

1. 点击 **💾 保存** 或 **⬇️ 下载** 按钮
2. 文件自动下载到本地
3. 将文件保存到 `process_models/` 目录

---

## 🎯 实战示例

### 示例1：简单审批流程

```
开始 → 填写申请 → 部门主管审批 → 结束
```

**配置步骤**：
1. 创建用户任务"填写申请"
   - 设置表单：`leave-form-schema.json`
2. 创建用户任务"部门主管审批"
   - 前置脚本：`assigned_to = "manager@company.com"`
   - 设置表单：`approval-form-schema.json`
3. 连接所有元素

### 示例2：条件分支流程

```
开始 → 填写申请 → 网关
                    ├─ 短期 → 主管审批 → 结束
                    └─ 长期 → 主管审批 → 总监审批 → 结束
```

**配置步骤**：
1. 添加排他网关
2. 设置短期分支条件：`leave_hours <= 24`
3. 设置长期分支条件：`leave_hours > 24`
4. 配置各审批任务的审批人

### 示例3：并行审批流程

```
开始 → 填写申请 → 并行网关
                    ├─ 部门主管审批 ─┐
                    └─ HR审批 ────────┤→ 汇聚网关 → 结束
```

**配置步骤**：
1. 添加并行网关（分支）
2. 添加两个审批任务
3. 添加并行网关（汇聚）
4. 连接所有元素

---

## 💡 最佳实践

### 1. 命名规范
- 使用有意义的元素名称
- ID 使用驼峰命名：`Task_ManagerApproval`
- 名称使用中文：`部门主管审批`

### 2. 脚本编写
- 保持脚本简洁
- 使用注释说明逻辑
- 避免复杂的业务逻辑

### 3. 条件表达式
- 使用简单的比较表达式
- 避免复杂的嵌套条件
- 确保条件互斥（排他网关）

### 4. 文件管理
- 定期保存流程
- 使用版本控制（Git）
- 备份重要流程

---

## 🔧 快捷键

| 快捷键 | 功能 |
|--------|------|
| Ctrl+Z | 撤销 |
| Ctrl+Y | 重做 |
| Delete | 删除选中元素 |
| Ctrl+C | 复制 |
| Ctrl+V | 粘贴 |
| Ctrl+A | 全选 |

---

## 📚 相关资源

- **BPMN 2.0 规范**: https://www.omg.org/spec/BPMN/2.0/
- **bpmn-js 文档**: https://bpmn.io/toolkit/bpmn-js/
- **SpiffWorkflow 文档**: https://spiffworkflow.readthedocs.io/
- **CodeMirror 文档**: https://codemirror.net/

---

## ❓ 常见问题

### Q: 如何保存流程到服务器？
A: 点击保存按钮下载文件，然后手动复制到 `process_models/` 目录。

### Q: 脚本中可以使用哪些函数？
A: 可以使用 SpiffWorkflow 提供的函数，如 `get_direct_manager()`, `get_department_manager()` 等。

### Q: 如何测试流程？
A: 保存流程后，在管理面板创建申请，选择该流程进行测试。

### Q: 条件表达式不生效？
A: 检查表达式语法，确保返回布尔值，变量名正确。

---

**祝你设计出完美的工作流程！** 🎉
