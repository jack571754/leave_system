# 请假审批系统 - Django + SpiffWorkflow

[![Python](https://img.shields.io/badge/Python-3.11+-blue.svg)](https://www.python.org/)
[![Django](https://img.shields.io/badge/Django-4.2-green.svg)](https://www.djangoproject.com/)
[![SpiffWorkflow](https://img.shields.io/badge/SpiffWorkflow-2.0-orange.svg)](https://github.com/sartography/SpiffWorkflow)
[![License](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

一个基于 Django + SpiffWorkflow 的企业级请假审批系统，直接使用 SpiffWorkflow Python 库执行 BPMN 工作流。

## 🎯 项目特点

- ✅ **简化架构**：Django 直接集成 SpiffWorkflow 库，无需外部服务
- ✅ **BPMN 2.0 标准**：使用标准的 BPMN 流程设计
- ✅ **本地执行**：工作流在 Django 进程中直接执行
- ✅ **灵活的审批规则**：支持条件路由、动态审批人分配
- ✅ **完整的审批功能**：多级审批、会签、或签、加签、转签、退回
- ✅ **详细的文档**：包含完整的配置指南和测试文档

## 📦 项目结构

```
leave_system/
├── docs/                           # 📚 文档目录
│   ├── 01-集成配置指南.md          # 完整集成说明
│   ├── 02-快速参考手册.md          # 代码速查表
│   ├── 03-配置总结.md              # 配置清单
│   ├── check_integration.py        # 配置检查脚本
│   └── README.md                   # 文档使用指南
├── leave_system/                   # Django 项目
│   ├── leave_api/                  # 审批 API 应用
│   │   ├── models.py              # 数据模型
│   │   ├── views.py               # API 视图
│   │   ├── spiff_client.py        # SpiffWorkflow 客户端
│   │   └── urls.py                # URL 路由
│   ├── leave_system/              # 项目配置
│   │   └── settings.py            # Django 配置
│   └── static/                    # 前端静态文件
├── process_models/                 # BPMN 流程模型
│   └── admin/admin/
│       └── admin.bpmn             # 审批流程
├── test_spiffworkflow.py          # 基础测试
├── test_api.ps1                   # API 测试
├── start_django.cmd               # 启动脚本
└── README.md                      # 本文档
```

## 🚀 快速开始

### 前置要求

- Python 3.11+
- Git

### 1. 克隆项目

```bash
git clone https://github.com/jack571754/leave_system.git
cd leave_system
```

### 2. 安装依赖

```cmd
cd leave_system
pip install -r requirements.txt
```

### 3. 运行数据库迁移

```cmd
python manage.py migrate
```

### 4. 启动 Django

```cmd
python manage.py runserver 8888
```

访问 Django：http://127.0.0.1:8888

### 5. 运行测试

```cmd
cd ..
python test_spiffworkflow.py
```

## 📚 文档

所有核心文档已整理到 `docs/` 目录：

- **[01-集成配置指南](docs/01-集成配置指南.md)** - 完整的 Django + SpiffWorkflow 集成说明
- **[02-快速参考手册](docs/02-快速参考手册.md)** - 核心配置和代码速查表
- **[03-配置总结](docs/03-配置总结.md)** - 配置清单和验证步骤
- **[配置检查脚本](docs/check_integration.py)** - 自动化配置验证工具

查看 [docs/README.md](docs/README.md) 了解文档使用指南。

## 🔧 API 接口

| 接口 | 方法 | 说明 |
|------|------|------|
| `/api/leave/create/` | POST | 创建请假申请并启动流程 |
| `/api/leave/my-requests/` | GET | 查询我的请假申请 |
| `/api/leave/pending-approvals/` | GET | 查询待审批任务 |
| `/api/leave/approve/` | POST | 审批请假申请 |

### API 使用示例

#### 创建请假申请

```bash
curl -X POST http://127.0.0.1:8888/api/leave/create/ \
  -H "Content-Type: application/json" \
  -d '{"user_email":"test@example.com","reason":"请假","leave_hours":8}'
```

#### 查询我的请假

```bash
curl http://127.0.0.1:8888/api/leave/my-requests/?user_email=test@example.com
```

#### 查询待审批

```bash
curl http://127.0.0.1:8888/api/leave/pending-approvals/?user_id=admin
```

## 🎓 核心功能

### 已完成功能 ✅

- ✅ Django + SpiffWorkflow 集成
- ✅ 流程启动和执行
- ✅ 基础审批流程
- ✅ 任务查询和完成

### 计划功能 📋

- 📋 工作流持久化
- 📋 多级审批
- 📋 会签/或签
- 📋 动态审批人分配
- 📋 审批历史追溯

## 🏗️ 技术架构

### 系统架构

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
│  │  REST API    │  │  业务逻辑层   │  │  数据访问层   │      │
│  └──────────────┘  └──────────────┘  └──────────────┘      │
│                                                              │
│  ┌──────────────────────────────────────────────────────┐  │
│  │         SpiffWorkflow 引擎 (内嵌)                     │  │
│  │  - BPMN 解析器                                        │  │
│  │  - 工作流执行引擎                                      │  │
│  │  - 任务管理                                           │  │
│  └──────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────┘
                            │
                            ▼
                  ┌──────────────────┐
                  │   SQLite/        │
                  │   PostgreSQL     │
                  └──────────────────┘
```

### 核心流程

#### 流程启动
```
用户提交请假 → Django 创建记录 → SpiffWorkflow 解析 BPMN → 
创建工作流实例 → 执行到第一个用户任务 → 返回成功响应
```

#### 任务完成
```
用户提交审批 → Django 查找工作流实例 → 
完成当前任务 → 继续执行工作流 → 更新状态
```

## 🧪 测试

### 运行自动化测试

```powershell
cd leave_system
.\test_phase1.ps1
```

### 手动测试

1. 访问 Django Admin：http://127.0.0.1:8888/admin/
## 🧪 测试

运行测试脚本验证配置：

```cmd
python test_spiffworkflow.py
```

## 🐛 常见问题

### 问题 1：流程启动失败

**解决方案**：
- 检查 BPMN 文件路径是否正确
- 检查环境变量 `BPMN_PROCESS_DIR`
- 查看 Django 日志

### 问题 2：找不到 BPMN 文件

**解决方案**：
- 确认 `process_models` 目录存在
- 检查 BPMN 文件命名是否正确
- 查看日志中的文件路径

### 问题 3：任务查询为空

**解决方案**：
- 检查工作流是否已启动
- 验证工作流是否执行到用户任务
- 查看工作流实例状态

## 🤝 贡献

欢迎贡献代码、报告问题或提出建议！

1. Fork 本项目
2. 创建特性分支 (`git checkout -b feature/AmazingFeature`)
3. 提交更改 (`git commit -m 'Add some AmazingFeature'`)
4. 推送到分支 (`git push origin feature/AmazingFeature`)
5. 开启 Pull Request

## 📄 许可证

本项目采用 MIT 许可证 - 详见 [LICENSE](LICENSE) 文件

## 📞 联系方式

- 项目地址：https://github.com/jack571754/leave_system
- 问题反馈：https://github.com/jack571754/leave_system/issues

## 🙏 致谢

- [Django](https://www.djangoproject.com/) - Web 框架
- [SpiffWorkflow](https://github.com/sartography/SpiffWorkflow) - 工作流引擎库
- [BPMN 2.0](https://www.omg.org/spec/BPMN/2.0/) - 流程建模标准

---

**开始使用：** 运行 `start_django.cmd` 启动系统

**测试配置：** 运行 `python test_spiffworkflow.py` 验证配置

**祝使用愉快！** 🎉
