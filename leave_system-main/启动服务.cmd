@echo off
echo ========================================
echo   启动 Django 服务
echo ========================================
echo.

cd leave_system
python manage.py runserver 0.0.0.0:8000

pause
