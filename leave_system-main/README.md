# 审批流程管理系统

一个基于 Django + SpiffWorkflow 的多级审批流程管理系统，支持请假申请、密码修改等多种审批场景。

## ✨ 特性

- 🎯 **多级审批**: 支持单级、两级、三级等多级审批流程
- 🔀 **多分支路由**: 根据条件自动选择不同的审批路径
- 📊 **可视化管理**: 提供 Web 管理界面，操作简单直观
- 🔄 **工作流引擎**: 基于 BPMN 2.0 标准的 SpiffWorkflow 引擎
- 📝 **审批历史**: 完整记录每一步审批操作
- 🔔 **通知系统**: 支持邮件通知和站内通知

## 🚀 快速开始

### 1. 启动服务

```bash
cd leave_system
python manage.py runserver 0.0.0.0:8000
```

### 2. 访问管理面板

在浏览器打开: **http://localhost:8000/dashboard/**

### 3. 开始使用

- 创建申请
- 查看我的申请
- 审批待办任务
- 查看审批历史

## 📖 详细文档

- [访问指南](访问指南.md) - 如何使用管理面板
- [密码修改审批流程配置教程](密码修改审批流程配置教程.md) - 完整的配置教程

## 🧪 测试

运行自动化测试：

```bash
python test_password_change.py
```

## 📁 项目结构

```
leave_system-main/
├── leave_system/              # Django 项目
│   ├── leave_api/            # 核心 API
│   ├── organization/         # 组织架构
│   ├── notifications/        # 通知系统
│   └── templates/            # 模板文件
│       └── dashboard.html    # 管理面板
├── process_models/           # BPMN 流程定义
│   ├── admin/               # 请假审批流程
│   └── password/            # 密码修改流程
├── test_password_change.py  # 测试脚本
└── 访问指南.md              # 使用指南
```

## 🔧 技术栈

- **后端**: Django 4.2.9
- **工作流引擎**: SpiffWorkflow
- **数据库**: SQLite (开发环境)
- **前端**: 原生 HTML/CSS/JavaScript

## 📝 审批流程示例

### 请假审批
- 短期请假（≤24小时）→ 部门主管
- 长期请假（>24小时）→ 部门主管

### 密码修改审批
- 普通密码 → 部门主管
- 重要密码 → 部门主管 → IT安全主管
- 关键密码 → 部门主管 → IT安全主管 → 系统管理员

## 🎯 核心功能

### 申请管理
- ✅ 创建请假申请
- ✅ 创建密码修改申请
- ✅ 查看申请状态
- ✅ 查看审批历史

### 审批管理
- ✅ 查看待审批任务
- ✅ 批准/拒绝申请
- ✅ 添加审批意见
- ✅ 审批历史追溯

### 流程管理
- ✅ BPMN 流程定义
- ✅ 动态路由选择
- ✅ 多级审批支持
- ✅ 流程状态持久化

## 🌐 API 接口

主要 API 端点：

- `POST /api/leave/create/` - 创建申请
- `GET /api/leave/my-requests/` - 我的申请
- `GET /api/leave/pending-approvals/` - 待审批任务
- `POST /api/leave/approve/` - 批准申请
- `POST /api/leave/reject/` - 拒绝申请
- `GET /api/leave/requests/{id}/history/` - 审批历史

完整 API 文档: http://localhost:8000/api/

## 📞 联系方式

如有问题，请查看文档或提交 Issue。

---

**Made with ❤️ using Django & SpiffWorkflow**
