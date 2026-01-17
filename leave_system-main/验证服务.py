"""
验证 Django 服务是否正常运行
"""

import requests
import time

BASE_URL = "http://localhost:8000"

def check_service():
    """检查服务是否运行"""
    print("正在检查服务状态...")
    
    max_retries = 5
    for i in range(max_retries):
        try:
            response = requests.get(f"{BASE_URL}/api/", timeout=5)
            if response.status_code == 200:
                print("✓ 服务运行正常！")
                print(f"  响应: {response.json()}")
                return True
            else:
                print(f"✗ 服务返回错误状态码: {response.status_code}")
                return False
        except requests.exceptions.ConnectionError:
            print(f"  尝试 {i+1}/{max_retries}: 连接失败，等待服务启动...")
            time.sleep(2)
        except Exception as e:
            print(f"✗ 发生错误: {e}")
            return False
    
    print("✗ 服务未启动或无法连接")
    print("  请确保运行了: python manage.py runserver 0.0.0.0:8000")
    return False

if __name__ == "__main__":
    print("\n" + "="*50)
    print("  Django 服务验证")
    print("="*50 + "\n")
    
    if check_service():
        print("\n可以开始测试了！")
        print("运行测试脚本: python test_password_change.py")
    else:
        print("\n请先启动服务:")
        print("  cd leave_system")
        print("  python manage.py runserver 0.0.0.0:8000")
