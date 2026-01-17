#!/usr/bin/env python
"""Django + SpiffWorkflow 集成配置检查脚本"""

import os
import sys
from pathlib import Path

def check_dependencies():
    """检查依赖包"""
    print("=" * 60)
    print("1. 检查依赖包")
    print("=" * 60)
    
    required_packages = [
        'django',
        'rest_framework',
        'corsheaders',
        'dotenv',
        'SpiffWorkflow',
        'lxml'
    ]
    
    missing = []
    for package in required_packages:
        try:
            __import__(package)
            print(f"✓ {package}")
        except ImportError:
            print(f"✗ {package} - 未安装")
            missing.append(package)
    
    if missing:
        print(f"\n缺少依赖: {', '.join(missing)}")
        print("运行: pip install -r requirements.txt")
        return False
    return True

def check_env_file():
    """检查环境变量文件"""
    print("\n" + "=" * 60)
    print("2. 检查环境变量")
    print("=" * 60)
    
    env_file = Path('leave_system/.env')
    if not env_file.exists():
        print("✗ .env 文件不存在")
        print("创建: leave_system/.env")
        return False
    
    print("✓ .env 文件存在")
    
    # 检查必需的环境变量
    from dotenv import load_dotenv
    load_dotenv(env_file)
    
    required_vars = ['BPMN_PROCESS_DIR']
    missing = []
    
    for var in required_vars:
        value = os.getenv(var)
        if value:
            print(f"✓ {var} = {value}")
        else:
            print(f"✗ {var} - 未配置")
            missing.append(var)
    
    if missing:
        print(f"\n缺少环境变量: {', '.join(missing)}")
        return False
    return True

def check_django_settings():
    """检查 Django 配置"""
    print("\n" + "=" * 60)
    print("3. 检查 Django 配置")
    print("=" * 60)
    
    sys.path.insert(0, str(Path('leave_system')))
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'leave_system.settings')
    
    try:
        import django
        django.setup()
        from django.conf import settings
        
        # 检查 INSTALLED_APPS
        required_apps = ['rest_framework', 'corsheaders', 'leave_api']
        for app in required_apps:
            if app in settings.INSTALLED_APPS:
                print(f"✓ {app} 已安装")
            else:
                print(f"✗ {app} 未安装")
                return False
        
        return True
    except Exception as e:
        print(f"✗ Django 配置错误: {e}")
        return False

def check_bpmn_files():
    """检查 BPMN 文件"""
    print("\n" + "=" * 60)
    print("4. 检查 BPMN 文件")
    print("=" * 60)
    
    bpmn_dir = os.getenv('BPMN_PROCESS_DIR', 'process_models')
    bpmn_path = Path(bpmn_dir)
    
    if not bpmn_path.exists():
        print(f"✗ BPMN 目录不存在: {bpmn_path}")
        return False
    
    print(f"✓ BPMN 目录存在: {bpmn_path}")
    
    # 检查示例流程
    example_bpmn = bpmn_path / 'admin' / 'admin' / 'admin.bpmn'
    if example_bpmn.exists():
        print(f"✓ 示例流程存在: {example_bpmn}")
    else:
        print(f"⚠ 示例流程不存在: {example_bpmn}")
    
    return True

def check_database():
    """检查数据库"""
    print("\n" + "=" * 60)
    print("5. 检查数据库")
    print("=" * 60)
    
    try:
        from django.db import connection
        from leave_api.models import LeaveRequest
        
        # 检查表是否存在
        with connection.cursor() as cursor:
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='leave_requests'")
            if cursor.fetchone():
                print("✓ leave_requests 表存在")
            else:
                print("✗ leave_requests 表不存在")
                print("运行: python manage.py migrate")
                return False
        
        # 检查必需字段
        fields = [f.name for f in LeaveRequest._meta.get_fields()]
        required_fields = ['process_instance_id', 'process_model_id', 'status']
        
        for field in required_fields:
            if field in fields:
                print(f"✓ 字段 {field} 存在")
            else:
                print(f"✗ 字段 {field} 不存在")
                return False
        
        return True
    except Exception as e:
        print(f"✗ 数据库检查失败: {e}")
        return False

def check_spiff_client():
    """检查 SpiffWorkflow 客户端"""
    print("\n" + "=" * 60)
    print("6. 检查 SpiffWorkflow 客户端")
    print("=" * 60)
    
    try:
        from leave_api.spiff_client import spiff_client
        
        print("✓ spiff_client 导入成功")
        print(f"✓ BPMN 目录: {spiff_client.process_dir}")
        
        # 检查关键方法
        methods = ['start_process', 'get_user_tasks', 'complete_task']
        for method in methods:
            if hasattr(spiff_client, method):
                print(f"✓ 方法 {method} 存在")
            else:
                print(f"✗ 方法 {method} 不存在")
                return False
        
        return True
    except Exception as e:
        print(f"✗ SpiffWorkflow 客户端检查失败: {e}")
        return False

def main():
    """主函数"""
    print("\n" + "=" * 60)
    print("Django + SpiffWorkflow 集成配置检查")
    print("=" * 60 + "\n")
    
    checks = [
        ("依赖包", check_dependencies),
        ("环境变量", check_env_file),
        ("Django 配置", check_django_settings),
        ("BPMN 文件", check_bpmn_files),
        ("数据库", check_database),
        ("SpiffWorkflow 客户端", check_spiff_client),
    ]
    
    results = []
    for name, check_func in checks:
        try:
            result = check_func()
            results.append((name, result))
        except Exception as e:
            print(f"\n✗ {name} 检查失败: {e}")
            results.append((name, False))
    
    # 总结
    print("\n" + "=" * 60)
    print("检查总结")
    print("=" * 60)
    
    for name, result in results:
        status = "✓ 通过" if result else "✗ 失败"
        print(f"{name}: {status}")
    
    all_passed = all(result for _, result in results)
    
    if all_passed:
        print("\n" + "=" * 60)
        print("✓ 所有检查通过！可以启动项目。")
        print("=" * 60)
        print("\n运行: python leave_system/manage.py runserver 8888")
    else:
        print("\n" + "=" * 60)
        print("✗ 部分检查失败，请修复后重试。")
        print("=" * 60)
        print("\n参考文档: INTEGRATION_GUIDE.md")
    
    return 0 if all_passed else 1

if __name__ == '__main__':
    sys.exit(main())
