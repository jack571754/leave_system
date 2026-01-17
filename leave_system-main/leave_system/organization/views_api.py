"""
组织架构 API 视图
提供员工、部门、角色等数据的 API 接口
"""

from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from .models import Employee, Department, Role


@require_http_methods(["GET"])
def list_employees(request):
    """
    获取员工列表
    
    GET /api/organization/employees/
    
    返回:
    {
        "employees": [
            {
                "id": 1,
                "employee_id": "E001",
                "name": "张三",
                "email": "zhangsan@example.com",
                "department": "技术部",
                "position": "工程师"
            }
        ]
    }
    """
    try:
        employees = Employee.objects.select_related('user', 'department').all()
        
        employee_list = []
        for emp in employees:
            employee_list.append({
                'id': emp.id,
                'employee_id': emp.employee_id,
                'name': emp.get_full_name(),
                'email': emp.email,
                'department': emp.department.name if emp.department else '',
                'department_id': emp.department.id if emp.department else None,
                'position': emp.position,
                'level': emp.level,
                'direct_manager_id': emp.direct_manager.id if emp.direct_manager else None,
                'direct_manager_name': emp.direct_manager.get_full_name() if emp.direct_manager else None
            })
        
        return JsonResponse({
            'employees': employee_list,
            'count': len(employee_list)
        })
    except Exception as e:
        return JsonResponse({
            'error': str(e)
        }, status=500)


@require_http_methods(["GET"])
def list_departments(request):
    """
    获取部门列表
    
    GET /api/organization/departments/
    
    返回:
    {
        "departments": [
            {
                "id": 1,
                "name": "技术部",
                "parent_id": null,
                "manager_id": 1,
                "manager_name": "张三"
            }
        ]
    }
    """
    try:
        departments = Department.objects.select_related('parent', 'manager').all()
        
        dept_list = []
        for dept in departments:
            dept_list.append({
                'id': dept.id,
                'name': dept.name,
                'full_path': dept.get_full_path(),
                'parent_id': dept.parent.id if dept.parent else None,
                'parent_name': dept.parent.name if dept.parent else None,
                'manager_id': dept.manager.id if dept.manager else None,
                'manager_name': dept.manager.get_full_name() if dept.manager else None
            })
        
        return JsonResponse({
            'departments': dept_list,
            'count': len(dept_list)
        })
    except Exception as e:
        return JsonResponse({
            'error': str(e)
        }, status=500)


@require_http_methods(["GET"])
def list_roles(request):
    """
    获取角色列表
    
    GET /api/organization/roles/
    
    返回:
    {
        "roles": [
            {
                "id": 1,
                "name": "HR",
                "description": "人力资源",
                "member_count": 5
            }
        ]
    }
    """
    try:
        roles = Role.objects.prefetch_related('employees').all()
        
        role_list = []
        for role in roles:
            role_list.append({
                'id': role.id,
                'name': role.name,
                'description': role.description,
                'member_count': role.employees.count()
            })
        
        return JsonResponse({
            'roles': role_list,
            'count': len(role_list)
        })
    except Exception as e:
        return JsonResponse({
            'error': str(e)
        }, status=500)


@require_http_methods(["GET"])
def get_role_members(request, role_id):
    """
    获取角色成员列表
    
    GET /api/organization/roles/<role_id>/members/
    
    返回:
    {
        "members": [
            {
                "id": 1,
                "employee_id": "E001",
                "name": "张三",
                "email": "zhangsan@example.com"
            }
        ]
    }
    """
    try:
        role = Role.objects.prefetch_related('employees__user').get(id=role_id)
        
        member_list = []
        for emp in role.employees.all():
            member_list.append({
                'id': emp.id,
                'employee_id': emp.employee_id,
                'name': emp.get_full_name(),
                'email': emp.email,
                'department': emp.department.name if emp.department else '',
                'position': emp.position
            })
        
        return JsonResponse({
            'role_name': role.name,
            'members': member_list,
            'count': len(member_list)
        })
    except Role.DoesNotExist:
        return JsonResponse({
            'error': '角色不存在'
        }, status=404)
    except Exception as e:
        return JsonResponse({
            'error': str(e)
        }, status=500)
