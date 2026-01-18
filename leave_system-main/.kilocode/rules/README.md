# 项目规则文档

这是一个基于 Django + SpiffWorkflow 的企业级审批流程管理系统。

## 🎯 项目概述

本系统支持可视化流程设计、多级审批、动态路由等功能，采用分层架构设计，将业务逻辑、工作流引擎和数据持久化清晰分离。

## 📁 项目结构

```
leave_system-main/
├── leave_system/              # Django 项目根目录
│   ├── leave_api/            # 核心 API 模块
│   │   ├── models.py         # 数据模型定义
│   │   ├── serializers.py    # API 序列化器
│   │   ├── views_v2.py       # 请假申请视图
│   │   ├── views_approval_tasks.py  # 审批任务视图
│   │   ├── views_bpmn.py     # BPMN 流程管理视图
│   │   ├── spiff_client_v2.py # SpiffWorkflow 客户端封装
│   │   └── services/         # 业务服务层
│   ├── organization/         # 组织架构模块
│   ├── notifications/        # 通知系统模块
│   ├── templates/            # HTML 模板
│   └── leave_system/         # 项目配置
└── process_models/           # BPMN 流程定义文件
```

## 🔧 技术栈

- **后端框架**: Django 5.1.6
- **工作流引擎**: SpiffWorkflow 3.0+
- **流程设计**: BPMN.js 17.11.1
- **数据库**: SQLite (开发) / PostgreSQL (生产)
- **API**: Django REST Framework
- **异步任务**: Celery 5.3+

## 💡 开发规范

### 代码组织

1. **分层架构**: 严格遵循 Views → Services → Models 的分层结构
2. **模块化**: 每个 Django app 负责独立的业务领域
3. **服务封装**: 复杂业务逻辑封装在 [`services/`](leave_system/leave_api/services/) 目录下

### 工作流集成

1. **客户端封装**: 通过 [`spiff_client_v2.py`](leave_system/leave_api/spiff_client_v2.py) 封装 SpiffWorkflow
2. **状态持久化**: 工作流状态使用 JSONField 存储在数据库
3. **BPMN 管理**: 流程定义文件存储在 [`process_models/`](process_models/) 目录

### API 设计

1. **RESTful 风格**: 遵循 REST API 设计规范
2. **序列化器**: 使用 DRF Serializers 进行数据验证和转换
3. **权限控制**: 实现基于角色的访问控制

### 命名约定

- **模型类**: 使用 PascalCase，如 [`LeaveRequest`](leave_system/leave_api/models.py)
- **视图函数**: 使用 snake_case，如 `create_leave_request()`
- **API 端点**: 使用 kebab-case，如 `/api/leave/my-requests/`
- **BPMN 文件**: 使用 kebab-case，如 `leave-approval.bpmn`

## 🔒 安全要求

- ✅ 用户认证和授权验证
- ✅ API 访问控制
- ✅ SQL 注入防护
- ✅ XSS 攻击防护
- ✅ CSRF 保护

## 📚 参考文档

- [项目架构文档](../../ARCHITECTUR) - 详细的技术架构说明
- [SpiffWorkflow 官方文档](https://spiffworkflow.readthedocs.io/)
- [BPMN.js 官方文档](https://bpmn.io/toolkit/bpmn-js/)
- [Django REST Framework 文档](https://www.django-rest-framework.org/)
- [Django 官方文档](https://docs.djangoproject.com/)

## 🚀 开发流程

### 添加新功能

1. 在对应的 Django app 中创建或修改模型
2. 创建数据库迁移: `python manage.py makemigrations`
3. 应用迁移: `python manage.py migrate`
4. 实现序列化器和视图
5. 配置 URL 路由
6. 测试 API 接口

### 修改工作流

1. 使用 BPMN 设计器编辑流程: http://localhost:8000/bpmn-designer/
2. 保存 BPMN XML 到 [`process_models/`](process_models/) 目录
3. 更新 [`spiff_client_v2.py`](leave_system/leave_api/spiff_client_v2.py) 中的流程逻辑
4. 测试工作流执行: http://localhost:8000/test-workflow/

## 🧪 测试

- **集成测试页面**: http://localhost:8000/test-workflow/
- **API 文档**: http://localhost:8000/api-info/
- **管理后台**: http://localhost:8000/admin/

## ⚠️ 注意事项

1. **工作流状态**: 不要直接修改 `workflow_data` 字段，使用 SpiffWorkflow Client 操作
2. **数据库迁移**: 修改模型后必须创建并应用迁移
3. **BPMN 文件**: 流程定义文件必须符合 BPMN 2.0 标准
4. **异步任务**: 长时间运行的操作应使用 Celery 异步处理
