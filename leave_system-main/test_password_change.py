"""
密码修改审批流程测试脚本
测试多级审批和多分支审批功能
"""

import requests
import json
import time

# API 基础 URL
BASE_URL = "http://localhost:8000/api"

def print_section(title):
    """打印分隔线"""
    print("\n" + "="*60)
    print(f"  {title}")
    print("="*60 + "\n")

def test_scenario_1():
    """
    场景1：普通用户修改普通密码
    审批路径：部门主管审批
    """
    print_section("场景1：普通用户修改普通密码")
    
    # 1. 创建密码修改申请
    print("步骤1：创建密码修改申请...")
    create_data = {
        "user_email": "user1@company.com",
        "staff_full_name": "张三",
        "staff_dept": "技术部",
        "reason": "定期更换邮箱密码",
        "leave_hours": 0,
        "password_type": "normal",
        "user_level": "normal",
        "system_name": "企业邮箱系统"
    }
    
    response = requests.post(f"{BASE_URL}/leave/create/", json=create_data)
    result = response.json()
    
    if result['success']:
        print(f"✓ 申请创建成功")
        print(f"  申请ID: {result['leave_request_id']}")
        print(f"  流程实例ID: {result['process_instance_id']}")
        print(f"  使用流程: {result['workflow_spec_name']}")
        request_id = result['leave_request_id']
    else:
        print(f"✗ 申请创建失败: {result.get('error')}")
        return
    
    time.sleep(1)

    
    # 2. 查询待审批任务
    print("\n步骤2：查询部门主管的待审批任务...")
    response = requests.get(
        f"{BASE_URL}/leave/pending-approvals/",
        params={"user_email": "manager@company.com"}
    )
    result = response.json()
    
    if result['success'] and result['count'] > 0:
        print(f"✓ 找到 {result['count']} 个待审批任务")
        task = result['tasks'][0]
        print(f"  任务ID: {task['id']}")
        print(f"  任务名称: {task['name']}")
        print(f"  申请人: {task['leave_request']['staff_full_name']}")
        task_id = task['id']
    else:
        print("✗ 未找到待审批任务")
        return
    
    time.sleep(1)
    
    # 3. 部门主管批准
    print("\n步骤3：部门主管批准申请...")
    approve_data = {
        "leave_request_id": request_id,
        "task_id": task_id,
        "approver_email": "manager@company.com",
        "approver_name": "李经理",
        "comment": "同意修改密码"
    }
    
    response = requests.post(f"{BASE_URL}/leave/approve/", json=approve_data)
    result = response.json()
    
    if result['success']:
        print(f"✓ 审批成功")
        print(f"  当前状态: {result['status']}")
        print(f"  流程完成: {'是' if result['completed'] else '否'}")
    else:
        print(f"✗ 审批失败: {result.get('error')}")
    
    time.sleep(1)
    
    # 4. 查询审批历史
    print("\n步骤4：查询审批历史...")
    response = requests.get(f"{BASE_URL}/leave/requests/{request_id}/history/")
    result = response.json()
    
    if result['success']:
        print(f"✓ 审批历史记录：")
        for record in result['history']:
            print(f"  - {record['action_display']}: {record['operator_name']} ({record['created_at']})")
            if record['comment']:
                print(f"    意见: {record['comment']}")
    
    print("\n✓ 场景1测试完成！")

def test_scenario_2():
    """
    场景2：普通用户修改重要密码
    审批路径：部门主管 → IT安全主管
    """
    print_section("场景2：普通用户修改重要密码")
    
    # 1. 创建密码修改申请
    print("步骤1：创建密码修改申请...")
    create_data = {
        "user_email": "user2@company.com",
        "staff_full_name": "李四",
        "staff_dept": "财务部",
        "reason": "数据库密码泄露，需要紧急更换",
        "leave_hours": 0,
        "password_type": "important",
        "user_level": "normal",
        "system_name": "财务数据库系统"
    }
    
    response = requests.post(f"{BASE_URL}/leave/create/", json=create_data)
    result = response.json()
    
    if result['success']:
        print(f"✓ 申请创建成功")
        print(f"  申请ID: {result['leave_request_id']}")
        request_id = result['leave_request_id']
    else:
        print(f"✗ 申请创建失败: {result.get('error')}")
        return
    
    time.sleep(1)
    
    # 2. 部门主管审批
    print("\n步骤2：部门主管审批...")
    response = requests.get(
        f"{BASE_URL}/leave/pending-approvals/",
        params={"user_email": "finance_manager@company.com"}
    )
    result = response.json()
    
    if result['success'] and result['count'] > 0:
        task_id = result['tasks'][0]['id']
        print(f"✓ 找到待审批任务: {task_id}")
        
        approve_data = {
            "leave_request_id": request_id,
            "task_id": task_id,
            "approver_email": "finance_manager@company.com",
            "approver_name": "王经理",
            "comment": "情况属实，同意修改"
        }
        
        response = requests.post(f"{BASE_URL}/leave/approve/", json=approve_data)
        result = response.json()
        
        if result['success']:
            print(f"✓ 部门主管审批通过")
        else:
            print(f"✗ 审批失败: {result.get('error')}")
            return
    else:
        print("✗ 未找到待审批任务")
        return
    
    time.sleep(1)
    
    # 3. IT安全主管审批
    print("\n步骤3：IT安全主管审批...")
    response = requests.get(
        f"{BASE_URL}/leave/pending-approvals/",
        params={"user_email": "it_security@company.com"}
    )
    result = response.json()
    
    if result['success'] and result['count'] > 0:
        task_id = result['tasks'][0]['id']
        print(f"✓ 找到待审批任务: {task_id}")
        
        approve_data = {
            "leave_request_id": request_id,
            "task_id": task_id,
            "approver_email": "it_security@company.com",
            "approver_name": "赵主管",
            "comment": "已确认安全风险，批准修改"
        }
        
        response = requests.post(f"{BASE_URL}/leave/approve/", json=approve_data)
        result = response.json()
        
        if result['success']:
            print(f"✓ IT安全主管审批通过")
            print(f"  流程完成: {'是' if result['completed'] else '否'}")
        else:
            print(f"✗ 审批失败: {result.get('error')}")
    else:
        print("✗ 未找到待审批任务")
    
    print("\n✓ 场景2测试完成！")


def test_scenario_3():
    """
    场景3：管理员修改关键密码
    审批路径：部门主管 → IT安全主管 → 系统管理员
    """
    print_section("场景3：管理员修改关键密码")
    
    # 1. 创建密码修改申请
    print("步骤1：创建密码修改申请...")
    create_data = {
        "user_email": "admin@company.com",
        "staff_full_name": "王五",
        "staff_dept": "IT部",
        "reason": "系统升级需要更换root密码",
        "leave_hours": 0,
        "password_type": "critical",
        "user_level": "admin",
        "system_name": "生产服务器"
    }
    
    response = requests.post(f"{BASE_URL}/leave/create/", json=create_data)
    result = response.json()
    
    if result['success']:
        print(f"✓ 申请创建成功")
        print(f"  申请ID: {result['leave_request_id']}")
        request_id = result['leave_request_id']
    else:
        print(f"✗ 申请创建失败: {result.get('error')}")
        return
    
    time.sleep(1)
    
    # 2. 部门主管审批
    print("\n步骤2：部门主管审批...")
    response = requests.get(
        f"{BASE_URL}/leave/pending-approvals/",
        params={"user_email": "it_manager@company.com"}
    )
    result = response.json()
    
    if result['success'] and result['count'] > 0:
        task_id = result['tasks'][0]['id']
        approve_data = {
            "leave_request_id": request_id,
            "task_id": task_id,
            "approver_email": "it_manager@company.com",
            "approver_name": "刘经理",
            "comment": "系统升级需要，同意"
        }
        
        response = requests.post(f"{BASE_URL}/leave/approve/", json=approve_data)
        if response.json()['success']:
            print(f"✓ 部门主管审批通过")
    
    time.sleep(1)
    
    # 3. IT安全主管审批
    print("\n步骤3：IT安全主管审批...")
    response = requests.get(
        f"{BASE_URL}/leave/pending-approvals/",
        params={"user_email": "it_security@company.com"}
    )
    result = response.json()
    
    if result['success'] and result['count'] > 0:
        task_id = result['tasks'][0]['id']
        approve_data = {
            "leave_request_id": request_id,
            "task_id": task_id,
            "approver_email": "it_security@company.com",
            "approver_name": "赵主管",
            "comment": "已评估安全风险，同意"
        }
        
        response = requests.post(f"{BASE_URL}/leave/approve/", json=approve_data)
        if response.json()['success']:
            print(f"✓ IT安全主管审批通过")
    
    time.sleep(1)
    
    # 4. 系统管理员审批
    print("\n步骤4：系统管理员审批...")
    response = requests.get(
        f"{BASE_URL}/leave/pending-approvals/",
        params={"user_email": "sysadmin@company.com"}
    )
    result = response.json()
    
    if result['success'] and result['count'] > 0:
        task_id = result['tasks'][0]['id']
        approve_data = {
            "leave_request_id": request_id,
            "task_id": task_id,
            "approver_email": "sysadmin@company.com",
            "approver_name": "孙管理员",
            "comment": "最终批准，可以执行密码修改"
        }
        
        response = requests.post(f"{BASE_URL}/leave/approve/", json=approve_data)
        result = response.json()
        
        if result['success']:
            print(f"✓ 系统管理员审批通过")
            print(f"  流程完成: {'是' if result['completed'] else '否'}")
    
    print("\n✓ 场景3测试完成！")

def test_scenario_4():
    """
    场景4：拒绝场景
    测试审批拒绝功能
    """
    print_section("场景4：审批拒绝场景")
    
    # 1. 创建申请
    print("步骤1：创建密码修改申请...")
    create_data = {
        "user_email": "user3@company.com",
        "staff_full_name": "赵六",
        "staff_dept": "市场部",
        "reason": "忘记密码",
        "leave_hours": 0,
        "password_type": "normal",
        "user_level": "normal",
        "system_name": "CRM系统"
    }
    
    response = requests.post(f"{BASE_URL}/leave/create/", json=create_data)
    result = response.json()
    
    if result['success']:
        print(f"✓ 申请创建成功")
        request_id = result['leave_request_id']
    else:
        print(f"✗ 申请创建失败")
        return
    
    time.sleep(1)
    
    # 2. 部门主管拒绝
    print("\n步骤2：部门主管拒绝申请...")
    response = requests.get(
        f"{BASE_URL}/leave/pending-approvals/",
        params={"user_email": "manager@company.com"}
    )
    result = response.json()
    
    if result['success'] and result['count'] > 0:
        task_id = result['tasks'][0]['id']
        reject_data = {
            "leave_request_id": request_id,
            "task_id": task_id,
            "approver_email": "manager@company.com",
            "approver_name": "周经理",
            "comment": "请先尝试密码找回功能，不需要修改密码"
        }
        
        response = requests.post(f"{BASE_URL}/leave/reject/", json=reject_data)
        result = response.json()
        
        if result['success']:
            print(f"✓ 申请已被拒绝")
            print(f"  最终状态: {result['status']}")
    
    print("\n✓ 场景4测试完成！")

if __name__ == "__main__":
    print("\n" + "="*60)
    print("  密码修改审批流程测试")
    print("="*60)
    
    try:
        # 测试场景1：普通用户 + 普通密码
        test_scenario_1()
        time.sleep(2)
        
        # 测试场景2：普通用户 + 重要密码
        test_scenario_2()
        time.sleep(2)
        
        # 测试场景3：管理员 + 关键密码
        test_scenario_3()
        time.sleep(2)
        
        # 测试场景4：拒绝场景
        test_scenario_4()
        
        print_section("所有测试完成！")
        
    except Exception as e:
        print(f"\n✗ 测试过程中出现错误: {str(e)}")
        import traceback
        traceback.print_exc()
