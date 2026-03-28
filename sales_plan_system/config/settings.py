import os
from pathlib import Path

from pydantic import Field, computed_field
from pydantic_settings import BaseSettings, SettingsConfigDict

BASE_DIR = Path(__file__).resolve().parent.parent


class AppSettings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=str(BASE_DIR / ".env"),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    debug: bool = Field(
        default=(os.getenv("DJANGO_DEBUG") or os.getenv("DEBUG") or "true").strip().lower() in {"1", "true", "yes", "on"},
        alias="DJANGO_DEBUG",
    )
    secret_key: str = Field(
        default=os.getenv("DJANGO_SECRET_KEY") or os.getenv("SECRET_KEY") or "dev-secret-key-change-me",
        alias="DJANGO_SECRET_KEY",
    )
    allowed_hosts_raw: str = Field(
        default=os.getenv("DJANGO_ALLOWED_HOSTS") or os.getenv("ALLOWED_HOSTS") or "127.0.0.1,localhost",
        alias="DJANGO_ALLOWED_HOSTS",
    )
    database_name: str = Field(default="db_new.sqlite3", alias="DJANGO_SQLITE_NAME")
    secure_ssl_redirect: bool = Field(default=True, alias="SECURE_SSL_REDIRECT")
    secure_hsts_seconds: int = Field(default=31536000, alias="SECURE_HSTS_SECONDS")
    session_cookie_secure: bool = Field(default=True, alias="SESSION_COOKIE_SECURE")
    csrf_cookie_secure: bool = Field(default=True, alias="CSRF_COOKIE_SECURE")

    @computed_field
    @property
    def allowed_hosts(self) -> list[str]:
        return [item.strip() for item in self.allowed_hosts_raw.split(",") if item.strip()]


settings = AppSettings()

if not settings.debug and settings.secret_key == "dev-secret-key-change-me":
    raise RuntimeError("DJANGO_SECRET_KEY must be set when DEBUG is false.")
if not settings.allowed_hosts:
    raise RuntimeError("DJANGO_ALLOWED_HOSTS must contain at least one host.")

DEBUG = settings.debug
SECRET_KEY = settings.secret_key
ALLOWED_HOSTS = settings.allowed_hosts

INSTALLED_APPS = [
    "unfold",
    "unfold.contrib.filters",
    "unfold.contrib.forms",
    "unfold.contrib.inlines",
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "django_htmx",
    "widget_tweaks",
    "core.users",
    "core.products",
    "core.plans",
    "core.approvals",
    "core.permissions",
    "core.mechanisms",
    "core.analytics",
    "core.integrations",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "config.middleware.RequestIDMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "config.middleware.RBACCacheMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
    "django_htmx.middleware.HtmxMiddleware",
    "config.middleware.ExceptionHandlerMiddleware",
]

if not DEBUG:
    MIDDLEWARE.insert(1, "whitenoise.middleware.WhiteNoiseMiddleware")

ROOT_URLCONF = "config.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
                "core.permissions.context_processors.permission_navigation",
            ],
        },
    }
]

WSGI_APPLICATION = "config.wsgi.application"

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": BASE_DIR / settings.database_name,
    }
}

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

LANGUAGE_CODE = "zh-hans"
TIME_ZONE = "Asia/Shanghai"
USE_I18N = True
USE_TZ = True

STATIC_URL = "/static/"
STATICFILES_DIRS = [BASE_DIR / "static"]
STATIC_ROOT = BASE_DIR / "staticfiles"
STATICFILES_STORAGE = (
    "whitenoise.storage.CompressedManifestStaticFilesStorage"
    if not DEBUG
    else "django.contrib.staticfiles.storage.StaticFilesStorage"
)

MEDIA_URL = "/media/"
MEDIA_ROOT = BASE_DIR / "media"

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"
AUTH_USER_MODEL = "users.User"

LOGIN_URL = "/login/"
LOGIN_REDIRECT_URL = "/"
LOGOUT_REDIRECT_URL = "/login/"

MESSAGE_STORAGE = "django.contrib.messages.storage.session.SessionStorage"

UNFOLD = {
    "SITE_TITLE": "销售计划系统 Admin",
    "SITE_HEADER": "销售计划系统",
    "SITE_SYMBOL": "shopping_cart",
    "SITE_ICON": {
        "light": "/static/images/logo-light.svg",
        "dark": "/static/images/logo-dark.svg",
    },
    "SHOW_HISTORY": True,
    "SHOW_VIEW_ON_SITE": True,
    "ENVIRONMENT": "config.settings_env.environment_callback",
    "COLORS": {
        "primary": {
            50: "239 246 255",
            100: "224 242 254",
            200: "191 219 254",
            300: "147 197 253",
            400: "96 165 250",
            500: "59 130 246",
            600: "37 99 235",
            700: "29 78 216",
            800: "30 64 175",
            900: "30 58 138",
            950: "23 37 99",
        },
    },
    "SIDEBAR": {
        "show_search": True,
        "show_all_applications": True,
        "navigation": [
            {
                "title": "计划与活动",
                "separator": True,
                "collapsible": True,
                "items": [
                    {"title": "活动批次", "icon": "campaign", "link": "/admin/plans/plancampaign/"},
                    {"title": "门店任务", "icon": "task", "link": "/admin/plans/plantask/"},
                    {"title": "任务明细", "icon": "list_alt", "link": "/admin/plans/plantaskitem/"},
                    {"title": "旧版计划", "icon": "history", "link": "/admin/plans/salesplan/"},
                ],
            },
            {
                "title": "审批流程",
                "collapsible": True,
                "items": [
                    {"title": "审批实例", "icon": "pending_actions", "link": "/admin/approvals/taskapprovalinstance/"},
                    {"title": "审批记录", "icon": "fact_check", "link": "/admin/approvals/taskapprovalrecord/"},
                    {"title": "流程配置", "icon": "account_tree", "link": "/admin/approvals/approvalflow/"},
                ],
            },
            {
                "title": "商品数据",
                "collapsible": True,
                "items": [
                    {"title": "SKU 管理", "icon": "qr_code", "link": "/admin/products/productsku/"},
                    {"title": "品牌", "icon": "label", "link": "/admin/products/brand/"},
                    {"title": "品类", "icon": "category", "link": "/admin/products/category/"},
                ],
            },
            {
                "title": "用户与组织",
                "separator": True,
                "collapsible": True,
                "items": [
                    {"title": "用户", "icon": "person", "link": "/admin/users/user/"},
                    {"title": "组织单元", "icon": "corporate_fare", "link": "/admin/users/orgunit/"},
                    {"title": "店铺", "icon": "store", "link": "/admin/users/store/"},
                    {"title": "部门", "icon": "domain", "link": "/admin/users/department/"},
                    {"title": "店铺成员", "icon": "group", "link": "/admin/users/storemembership/"},
                ],
            },
            {
                "title": "权限中心",
                "collapsible": True,
                "items": [
                    {"title": "角色", "icon": "shield", "link": "/admin/permissions/role/"},
                    {"title": "权限", "icon": "key", "link": "/admin/permissions/permission/"},
                    {"title": "角色权限", "icon": "lock", "link": "/admin/permissions/rolepermission/"},
                    {"title": "用户授权", "icon": "badge", "link": "/admin/permissions/userroleassignment/"},
                    {"title": "数据范围", "icon": "filter_alt", "link": "/admin/permissions/datascoperule/"},
                    {"title": "页面权限", "icon": "web", "link": "/admin/permissions/frontendpagepermission/"},
                ],
            },
        ],
    },
    "STYLES": [
        lambda request: "/static/css/admin-custom.css",
    ],
}

LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "standard": {
            "format": "%(asctime)s %(levelname)s %(name)s %(message)s"
        }
    },
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
            "formatter": "standard",
        }
    },
    "root": {
        "handlers": ["console"],
        "level": "INFO",
    },
}

if not DEBUG:
    SECURE_SSL_REDIRECT = settings.secure_ssl_redirect
    SECURE_HSTS_SECONDS = settings.secure_hsts_seconds
    SESSION_COOKIE_SECURE = settings.session_cookie_secure
    CSRF_COOKIE_SECURE = settings.csrf_cookie_secure
    SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
