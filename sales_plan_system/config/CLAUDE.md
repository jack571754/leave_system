# Config 模块 - 项目配置

> 🏠 [返回根目录](../CLAUDE.md)

## 模块概述

项目配置模块，包含 Django 项目的核心配置、路由和 WSGI 入口。

---

## 文件结构

```
config/
├── __init__.py       # 包初始化
├── settings.py       # Django 核心配置
├── urls.py           # 根路由配置
└── wsgi.py           # WSGI 部署入口
```

---

## 关键配置项

### settings.py

| 配置项 | 值 | 说明 |
|--------|-----|------|
| `SECRET_KEY` | 需修改 | 生产环境必须更换 |
| `DEBUG` | True | 开发模式 |
| `ALLOWED_HOSTS` | ['*'] | 允许所有主机（生产需限制） |
| `AUTH_USER_MODEL` | 'users.User' | 自定义用户模型 |
| `LANGUAGE_CODE` | 'zh-hans' | 简体中文 |
| `TIME_ZONE` | 'Asia/Shanghai' | 上海时区 |
| `DATABASE` | SQLite | 开发用 SQLite |

### 已安装应用

```python
INSTALLED_APPS = [
    # Django 内置
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    # 第三方
    'django_htmx',
    'widget_tweaks',
    # 本地业务模块
    'core.users',
    'core.products',
    'core.plans',
    'core.approvals',
]
```

### 中间件配置

```python
MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    'django_htmx.middleware.HtmxMiddleware',  # HTMX 支持
]
```

---

## 路由设计 (urls.py)

| 路径 | 包含模块 | 说明 |
|------|----------|------|
| `/admin/` | admin.site.urls | Django 管理后台 |
| `/` | dashboard | 首页看板 |
| `/` | core.users.urls | 用户认证路由 |
| `/products/` | core.products.urls | SKU 管理 |
| `/plans/` | core.plans.urls | 计划提报 |
| `/approvals/` | core.approvals.urls | 审批流程 |

---

## 登录配置

```python
LOGIN_URL = '/login/'
LOGIN_REDIRECT_URL = '/'
LOGOUT_REDIRECT_URL = '/login/'
```

---

## 开发注意事项

1. **生产部署前必须修改**:
   - `SECRET_KEY`: 使用环境变量
   - `DEBUG = False`
   - `ALLOWED_HOSTS`: 设置实际域名
   - `DATABASE`: 切换到 PostgreSQL/MySQL

2. **静态文件**:
   - 开发: `STATIC_URL = '/static/'`
   - 生产: 使用 `whitenoise` 或 CDN

3. **HTMX 中间件**: 确保 `HtmxMiddleware` 在认证中间件之后
