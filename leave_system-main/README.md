# 请假审批流程管理系统

一个基于 Django + SpiffWorkflow 的企业级审批流程管理系统，支持可视化流程设计、多级审批、动态路由等功能。

## ✨ 核心特性

- 🎨 **可视化流程设计**: 基于 BPMN.js 的流程设计器，支持拖拽式设计
- 🎯 **多级审批**: 支持单级、两级、三级等多级审批流程
- 🔀 **动态路由**: 根据条件自动选择不同的审批路径
- 📊 **流程监控**: 实时查看流程状态和审批进度
- 🔄 **工作流引擎**: 基于 BPMN 2.0 标准的 SpiffWorkflow 引擎
- 📝 **审批历史**: 完整记录每一步审批操作
- 🔔 **通知系统**: 支持邮件通知和站内通知
- 🧪 **集成测试**: 提供完整的测试工具验证流程

## 🚀 快速开始

### 1. 安装依赖

```bash
cd leave_system
pip install -r requirements.txt
```

### 2. 初始化数据库

```bash
python manage.py migrate
python manage.py createsuperuser
```

### 3. 启动服务

```bash
python manage.py runserver 0.0.0.0:8000
```

### 4. 访问系统

在浏览器打开: **http://localhost:8000/dashboard/**

## 📖 系统功能

### 🎨 BPMN 流程设计器
- 访问地址: http://localhost:8000/bpmn-designer/
- 可视化设计 BPMN 流程图
- 支持任务节点、网关、事件等元素
- 实时保存和加载流程定义
- 查看 XML 格式的流程定义

### 🧪 流程集成测试
- 访问地址: http://localhost:8000/test-workflow/
- 测试创建请假申请
- 测试查询我的申请
- 测试查询待审批任务
- 测试审批操作（批准/拒绝/退回）
- 测试查询审批历史
- 测试流程状态检查

### 📡 API 接口文档
- 访问地址: http://localhost:8000/api-info/
- 查看所有可用的 REST API 接口
- 包括请假申请、审批、查询等功能

### ⚙️ 系统管理后台
- 访问地址: http://localhost:8000/admin/
- Django 管理后台
- 管理用户、组织架构、审批规则等

## 📁 项目结构

```
leave_system-main/
├── leave_system/              # Django 项目
│   ├── leave_api/            # 核心 API
│   │   ├── models.py         # 数据模型
│   │   ├── serializers.py    # 序列化器
│   │   ├── views_v2.py       # 请假申请视图
│   │   ├── views_approval_tasks.py  # 审批任务视图
│   │   ├── views_bpmn.py     # BPMN 流程管理视图
│   │   ├── spiff_client_v2.py # SpiffWorkflow 客户端
│   │   └── urls.py           # 路由配置
│   ├── organization/         # 组织架构模块
│   ├── notifications/        # 通知系统模块
│   ├── templates/            # 模板文件
│   │   ├── dashboard.html    # 控制台首页
│   │   ├── bpmn_designer.html # BPMN 设计器
│   │   └── test_workflow.html # 测试页面
│   └── leave_system/         # 项目配置
│       ├── settings.py       # Django 设置
│       └── urls.py           # 主路由配置
├── process_models/           # BPMN 流程定义
│   ├── leave-approval/       # 请假审批流程
│   └── password/            # 密码修改流程
└── README.md                # 项目说明
```

## 🔧 技术栈

- **后端框架**: Django 5.1.6
- **工作流引擎**: SpiffWorkflow 3.0+
- **流程设计**: BPMN.js 17.11.1
- **数据库**: SQLite (开发环境) / PostgreSQL (生产环境)
- **前端**: 原生 HTML/CSS/JavaScript
- **API**: Django REST Framework

## 📝 审批流程示例

### 请假审批流程
```
申请人提交 → 部门主管审批 → 完成
```

### 密码修改审批流程
```
普通密码: 申请人 → 部门主管 → 完成
重要密码: 申请人 → 部门主管 → IT安全主管 → 完成
关键密码: 申请人 → 部门主管 → IT安全主管 → 系统管理员 → 完成
```

## 🎯 核心功能模块

### 申请管理
- ✅ 创建请假申请
- ✅ 创建密码修改申请
- ✅ 查看申请状态
- ✅ 查看审批历史
- ✅ 添加抄送人
- ✅ 催办审批

### 审批管理
- ✅ 查看待审批任务
- ✅ 批准/拒绝申请
- ✅ 退回申请
- ✅ 添加审批意见
- ✅ 审批历史追溯
- ✅ 加签/转签

### 流程管理
- ✅ BPMN 流程定义
- ✅ 可视化流程设计
- ✅ 动态路由选择
- ✅ 多级审批支持
- ✅ 流程状态持久化
- ✅ 流程版本管理

### 组织架构
- ✅ 部门管理
- ✅ 员工管理
- ✅ 角色权限
- ✅ 审批规则配置

### 通知系统
- ✅ 站内通知
- ✅ 邮件通知
- ✅ 通知模板
- ✅ 通知历史

## 🌐 API 接口

### 请假申请相关
- `POST /api/leave/create/` - 创建请假申请
- `GET /api/leave/my-requests/` - 查询我的申请
- `GET /api/leave/pending-approvals/` - 查询待审批任务
- `POST /api/leave/approve/` - 批准申请
- `POST /api/leave/reject/` - 拒绝申请
- `POST /api/leave/return/` - 退回申请
- `GET /api/leave/requests/{id}/history/` - 查询审批历史

### 审批任务相关
- `GET /api/approval-tasks/my-tasks/` - 查询我的待办任务
- `POST /api/approval-tasks/{task_id}/approve/` - 批准任务
- `POST /api/approval-tasks/{task_id}/reject/` - 拒绝任务
- `POST /api/approval-tasks/{task_id}/return/` - 退回任务
- `POST /api/approval-tasks/{task_id}/add-sign/` - 加签任务
- `POST /api/approval-tasks/{task_id}/transfer/` - 转签任务

### BPMN 流程管理
- `GET /api/bpmn/processes/` - 获取流程列表
- `POST /api/bpmn/processes/` - 创建新流程
- `GET /api/bpmn/processes/{id}/` - 获取流程详情
- `PUT /api/bpmn/processes/{id}/` - 更新流程
- `DELETE /api/bpmn/processes/{id}/` - 删除流程

完整 API 文档: http://localhost:8000/api-info/

## 🏗️ 架构设计

详细的架构设计文档请参考: [ARCHITECTURE.md](ARCHITECTURE.md)

## 📚 相关文档

- [Django + SpiffWorkflow 集成架构](ARCHITECTURE.md) - 详细的技术架构说明
- [SpiffWorkflow 官方文档](https://spiffworkflow.readthedocs.io/)
- [BPMN.js 官方文档](https://bpmn.io/toolkit/bpmn-js/)
- [Django REST Framework 文档](https://www.django-rest-framework.org/)

## 🔒 安全性

- ✅ 用户认证和授权
- ✅ API 访问控制
- ✅ 数据加密传输
- ✅ SQL 注入防护
- ✅ XSS 攻击防护
- ✅ CSRF 保护

## 🚀 部署建议

### 开发环境
```bash
python manage.py runserver
```

### 生产环境
- 使用 Gunicorn + Nginx
- 配置 PostgreSQL 数据库
- 启用 HTTPS
- 配置日志系统
- 设置定时任务

## 📞 技术支持

如有问题，请查看文档或提交 Issue。

## 📄 许可证

本项目采用 MIT 许可证。

---

**Made with ❤️ using Django & SpiffWorkflow**
