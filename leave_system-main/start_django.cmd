@echo off
echo ========================================
echo 启动 Django 请假系统 (使用 SpiffWorkflow)
echo ========================================
echo.

cd leave_system

echo 1. 安装依赖...
pip install -r requirements.txt
echo.

echo 2. 运行数据库迁移...
python manage.py migrate
echo.

echo 3. 启动 Django 服务器...
echo 服务地址: http://localhost:8888
echo.
python manage.py runserver 8888
