"""
初始化脚本 - 创建测试数据
运行方式: python manage.py shell < init_data.py
或: python manage.py shell
>>> exec(open('init_data.py').read())
"""

from core.users.models import User, Department
from core.products.models import Brand, Category, ProductSKU
from core.plans.models import SalesPlan, SalesPlanItem
from core.approvals.models import ApprovalFlow
from django.utils import timezone
from dateutil.relativedelta import relativedelta


def create_test_data():
    print("开始创建测试数据...")

    # 1. 创建部门
    print("创建部门...")
    sales_dept, _ = Department.objects.get_or_create(
        code='SALES',
        defaults={'name': '销售部'}
    )
    marketing_dept, _ = Department.objects.get_or_create(
        code='MKT',
        defaults={'name': '市场部'}
    )
    print(f"  - {sales_dept.name}, {marketing_dept.name}")

    # 2. 创建用户
    print("创建用户...")

    # 管理员
    admin, _ = User.objects.get_or_create(
        username='admin',
        defaults={
            'email': 'admin@example.com',
            'role': User.Role.ADMIN,
            'first_name': '系统',
            'last_name': '管理员',
            'is_staff': True,
            'is_superuser': True,
        }
    )
    admin.set_password('admin123')
    admin.save()

    # 经理
    manager, _ = User.objects.get_or_create(
        username='manager',
        defaults={
            'email': 'manager@example.com',
            'role': User.Role.MANAGER,
            'first_name': '张',
            'last_name': '经理',
            'department': sales_dept,
        }
    )
    manager.set_password('admin123')
    manager.save()

    # 主管
    supervisor, _ = User.objects.get_or_create(
        username='supervisor',
        defaults={
            'email': 'supervisor@example.com',
            'role': User.Role.SUPERVISOR,
            'first_name': '李',
            'last_name': '主管',
            'department': sales_dept,
            'manager': manager,
        }
    )
    supervisor.set_password('admin123')
    supervisor.save()

    # 普通员工
    staff, _ = User.objects.get_or_create(
        username='staff',
        defaults={
            'email': 'staff@example.com',
            'role': User.Role.STAFF,
            'first_name': '王',
            'last_name': '员工',
            'department': sales_dept,
            'manager': supervisor,
        }
    )
    staff.set_password('admin123')
    staff.save()

    # 更新部门负责人
    sales_dept.manager = manager
    sales_dept.save()

    print(f"  - 管理员: admin / admin123")
    print(f"  - 经理: manager / admin123")
    print(f"  - 主管: supervisor / admin123")
    print(f"  - 员工: staff / admin123")

    # 3. 创建品牌
    print("创建品牌...")
    brands_data = [
        ('LANCOME', '兰蔻'),
        ('ESTEE', '雅诗兰黛'),
        ('SKII', 'SK-II'),
        ('LORME', '欧莱雅'),
        ('OLAY', '玉兰油'),
    ]
    for code, name in brands_data:
        Brand.objects.get_or_create(code=code, defaults={'name': name})

    # 4. 创建品类
    print("创建品类...")
    categories_data = [
        ('SKIN_CARE', '护肤'),
        ('MAKEUP', '彩妆'),
        ('PERFUME', '香水'),
        ('BODY_CARE', '身体护理'),
    ]
    for code, name in categories_data:
        Category.objects.get_or_create(code=code, defaults={'name': name})

    # 5. 创建SKU
    print("创建SKU...")
    skus_data = [
        ('SK001', '兰蔻小黑瓶精华 50ml', 'LANCOME', 'SKIN_CARE', 1080),
        ('SK002', '兰蔻粉水 400ml', 'LANCOME', 'SKIN_CARE', 380),
        ('SK003', '雅诗兰黛小棕瓶 50ml', 'ESTEE', 'SKIN_CARE', 950),
        ('SK004', 'SK-II神仙水 230ml', 'SKII', 'SKIN_CARE', 1540),
        ('MK001', '兰蔻持妆粉底液 30ml', 'LANCOME', 'MAKEUP', 480),
        ('MK002', '雅诗兰黛DW粉底液 30ml', 'ESTEE', 'MAKEUP', 420),
        ('PF001', '兰蔻美丽人生香水 50ml', 'LANCOME', 'PERFUME', 890),
        ('BC001', '欧莱雅身体乳 400ml', 'LORME', 'BODY_CARE', 99),
    ]

    for sku_code, name, brand_code, cat_code, price in skus_data:
        brand = Brand.objects.get(code=brand_code)
        category = Category.objects.get(code=cat_code)
        ProductSKU.objects.get_or_create(
            sku_code=sku_code,
            defaults={
                'sku_name': name,
                'brand': brand,
                'category': category,
                'unit_price': price,
                'status': 'active',
            }
        )

    # 6. 创建审批流程
    print("创建审批流程...")
    ApprovalFlow.objects.get_or_create(
        flow_type='sales_plan',
        defaults={
            'name': '销售计划审批流程',
            'levels': [
                {'level': 1, 'role': 'supervisor'},
                {'level': 2, 'role': 'manager'},
            ]
        }
    )

    # 7. 创建示例销售计划
    print("创建示例计划...")
    current_month = timezone.now().strftime('%Y-%m')
    target_months = [
        (timezone.now() + relativedelta(months=i)).strftime('%Y-%m')
        for i in range(1, 5)
    ]

    plan, created = SalesPlan.objects.get_or_create(
        plan_month=current_month,
        submitter=staff,
        defaults={
            'department': sales_dept,
            'status': 'draft',
        }
    )

    if created:
        # 添加计划明细
        skus = ProductSKU.objects.filter(status='active')[:3]
        for sku in skus:
            for i, target_month in enumerate(target_months):
                SalesPlanItem.objects.create(
                    plan=plan,
                    sku=sku,
                    target_month=target_month,
                    sales_qty=100 * (i + 1),
                    unit_price=sku.unit_price,
                    stock_qty=500,
                )
        print(f"  - 创建示例计划: {plan.plan_month}")

    print("\n测试数据创建完成！")
    print("=" * 50)
    print("登录账号:")
    print("  - 管理员: admin / admin123")
    print("  - 经理: manager / admin123")
    print("  - 主管: supervisor / admin123")
    print("  - 员工: staff / admin123")


if __name__ == '__main__':
    create_test_data()
