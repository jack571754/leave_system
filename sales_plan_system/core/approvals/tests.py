from django.test import Client, TestCase
from django.utils import timezone

from core.approvals.models import TaskApprovalRecord
from core.permissions.models import Permission, Role, RolePermission, UserRoleAssignment
from core.plans.models import PlanCampaign, PlanTask, PlanTaskItem
from core.products.models import Brand, Category, ProductSKU
from core.users.models import OrgUnit, Store, StoreMembership, User


class TaskApprovalWorkflowTests(TestCase):
    def setUp(self):
        self.department = OrgUnit.objects.create(
            name='Approval Department',
            code='ORG_APPR_DEPT',
            unit_type=OrgUnit.UnitType.DEPARTMENT,
        )
        self.platform = OrgUnit.objects.create(
            name='Approval Platform',
            code='ORG_APPR_PLAT',
            unit_type=OrgUnit.UnitType.PLATFORM,
            parent=self.department,
        )
        self.manager = User.objects.create_user(
            username='approval_manager',
            password='pass1234',
            role=User.Role.MANAGER,
            org_unit=self.department,
        )
        self.staff = User.objects.create_user(
            username='approval_staff',
            password='pass1234',
            role=User.Role.STAFF,
            manager=self.manager,
            org_unit=self.platform,
        )
        self.platform.manager = self.manager
        self.platform.save()

        self.store = Store.objects.create(
            name='Approval Store',
            code='STORE_APPR',
            org_unit=self.platform,
            owner=self.staff,
        )
        StoreMembership.objects.create(
            store=self.store,
            user=self.staff,
            role=StoreMembership.Role.OWNER,
        )

        brand = Brand.objects.create(name='Approval Brand', code='ABR')
        category = Category.objects.create(name='Approval Category', code='ACT')
        self.sku = ProductSKU.objects.create(
            sku_code='APPRSKU1',
            sku_name='Approval SKU',
            brand=brand,
            category=category,
            unit='pcs',
            unit_price=100,
            cost_price=50,
            status=ProductSKU.Status.ACTIVE,
        )
        self.campaign = PlanCampaign.objects.create(
            title='Approval Campaign',
            plan_month=timezone.now().strftime('%Y-%m'),
            org_unit=self.platform,
            created_by=self.manager,
            status=PlanCampaign.Status.ACTIVE,
            start_date=timezone.now().date(),
            end_date=timezone.now().date(),
            published_at=timezone.now(),
        )
        self.task = PlanTask.objects.create(
            campaign=self.campaign,
            store=self.store,
            assignee=self.staff,
            org_unit=self.platform,
        )
        PlanTaskItem.objects.create(
            task=self.task,
            sku=self.sku,
            target_month=self.task.get_target_months()[0],
            sales_qty=10,
            unit_price=100,
            stock_qty=20,
        )
        self.task.submit(user=self.staff)

    def test_task_pending_for_manager(self):
        self.task.refresh_from_db()
        pending = PlanTask.pending_for_approver(self.manager)
        self.assertIn(self.task, pending)
        self.assertEqual(self.task.pending_approver, self.manager)

    def test_approve_task_view(self):
        client = Client()
        self.assertTrue(client.login(username='approval_manager', password='pass1234'))
        response = client.post(f'/approvals/tasks/{self.task.pk}/approve/', {'comment': 'ok'})
        self.assertEqual(response.status_code, 302)
        self.task.refresh_from_db()
        self.assertEqual(self.task.status, PlanTask.Status.APPROVED)
        self.assertEqual(self.task.approval_status, PlanTask.ApprovalStatus.APPROVED)
        self.assertEqual(TaskApprovalRecord.objects.filter(task=self.task, action='approve').count(), 1)

    def test_reject_task_view(self):
        second_store = Store.objects.create(
            name='Approval Store 2',
            code='STORE_APPR_2',
            org_unit=self.platform,
            owner=self.staff,
        )
        second_task = PlanTask.objects.create(
            campaign=self.campaign,
            store=second_store,
            assignee=self.staff,
            org_unit=self.platform,
        )
        PlanTaskItem.objects.create(
            task=second_task,
            sku=self.sku,
            target_month=second_task.get_target_months()[0],
            sales_qty=10,
            unit_price=100,
            stock_qty=20,
        )
        second_task.submit(user=self.staff)

        client = Client()
        self.assertTrue(client.login(username='approval_manager', password='pass1234'))
        response = client.post(f'/approvals/tasks/{second_task.pk}/reject/', {'comment': 'need revise'})
        self.assertEqual(response.status_code, 302)
        second_task.refresh_from_db()
        self.assertEqual(second_task.status, PlanTask.Status.REJECTED)
        self.assertEqual(second_task.approval_status, PlanTask.ApprovalStatus.REJECTED)
        self.assertEqual(TaskApprovalRecord.objects.filter(task=second_task, action='reject_to_submitter').count(), 1)

    def test_user_with_rbac_approval_permission_can_approve_task(self):
        delegate = User.objects.create_user(
            username='approval_delegate',
            password='pass1234',
            role=User.Role.STAFF,
            org_unit=self.department,
        )
        approval_role = Role.objects.create(code='approval_delegate_role', name='Approval Delegate', is_active=True)
        approval_perm, _ = Permission.objects.update_or_create(
            code='approvals.instance.approve',
            defaults={'module': 'approvals', 'resource': 'instance', 'action': 'approve', 'is_active': True},
        )
        RolePermission.objects.update_or_create(role=approval_role, permission=approval_perm)
        UserRoleAssignment.objects.create(user=delegate, role=approval_role, scope_type=UserRoleAssignment.ScopeType.STORE, store=self.store)

        client = Client()
        self.assertTrue(client.login(username='approval_delegate', password='pass1234'))
        response = client.post(f'/approvals/tasks/{self.task.pk}/approve/', {'comment': 'delegate ok'})
        self.assertEqual(response.status_code, 302)
        self.task.refresh_from_db()
        self.assertEqual(self.task.status, PlanTask.Status.APPROVED)
