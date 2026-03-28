from django.test import TestCase
from django.utils import timezone

from core.permissions.models import Permission, Role, RolePermission, UserRoleAssignment
from core.plans.services import task_service
from core.plans.models import PlanCampaign, PlanTask, PlanTaskItem
from core.plans.selectors import task_items_for_report
from core.products.models import Brand, Category, ProductSKU
from core.users.models import OrgUnit, Store, User


class PlanTaskModelTests(TestCase):
    def setUp(self):
        self.platform = OrgUnit.objects.create(
            name='JD',
            code='PLAT_JD',
            unit_type=OrgUnit.UnitType.PLATFORM,
        )
        self.owner = User.objects.create_user(
            username='store_owner',
            password='pass1234',
            role=User.Role.STAFF,
        )
        self.creator = User.objects.create_user(
            username='planner',
            password='pass1234',
            role=User.Role.MANAGER,
        )
        self.owner.manager = self.creator
        self.owner.save(update_fields=['manager'])
        self.platform.manager = self.creator
        self.platform.save(update_fields=['manager'])
        self.store = Store.objects.create(
            name='JD Flagship',
            code='JD001',
            org_unit=self.platform,
            owner=self.owner,
        )
        self.campaign = PlanCampaign.objects.create(
            title='2026 April Campaign',
            plan_month='2026-04',
            org_unit=self.platform,
            created_by=self.creator,
            status=PlanCampaign.Status.ACTIVE,
            start_date=timezone.now().date(),
            end_date=timezone.now().date(),
        )
        brand = Brand.objects.create(name='Test Brand', code='TB')
        category = Category.objects.create(name='Test Category', code='TC')
        self.sku = ProductSKU.objects.create(
            sku_code='SKU001',
            sku_name='Test SKU',
            brand=brand,
            category=category,
            unit='pcs',
            unit_price=100,
            cost_price=50,
            status=ProductSKU.Status.ACTIVE,
        )

    def test_task_defaults_from_store(self):
        task = PlanTask.objects.create(
            campaign=self.campaign,
            store=self.store,
        )
        self.assertEqual(task.org_unit, self.platform)
        self.assertEqual(task.assignee, self.owner)

    def test_task_submit_requires_items(self):
        task = PlanTask.objects.create(
            campaign=self.campaign,
            store=self.store,
        )
        self.assertFalse(task.submit())

        PlanTaskItem.objects.create(
            task=task,
            sku=self.sku,
            target_month='2026-05',
            sales_qty=10,
            unit_price=100,
            stock_qty=50,
        )
        self.assertTrue(task.submit(user=self.owner))
        task.refresh_from_db()
        self.assertEqual(task.status, PlanTask.Status.SUBMITTED)
        self.assertEqual(task.approval_status, PlanTask.ApprovalStatus.PENDING)

    def test_campaign_target_months(self):
        self.assertEqual(
            self.campaign.get_target_months(),
            ['2026-05', '2026-06', '2026-07', '2026-08']
        )

    def test_save_task_matrix_updates_all_months(self):
        task = PlanTask.objects.create(
            campaign=self.campaign,
            store=self.store,
        )
        months = task.get_target_months()
        for month in months:
            PlanTaskItem.objects.create(
                task=task,
                sku=self.sku,
                target_month=month,
                sales_qty=0,
                unit_price=100,
                stock_qty=0,
            )

        self.client.force_login(self.owner)
        response = self.client.post(
            f'/plans/tasks/{task.pk}/save-matrix/',
            {
                'matrix_sku_ids': [str(self.sku.pk)],
                f'unit_price__{self.sku.pk}': '120',
                f'sales_qty__{self.sku.pk}__{months[0]}': '11',
                f'stock_qty__{self.sku.pk}__{months[0]}': '21',
                f'sales_qty__{self.sku.pk}__{months[1]}': '12',
                f'stock_qty__{self.sku.pk}__{months[1]}': '22',
                f'sales_qty__{self.sku.pk}__{months[2]}': '13',
                f'stock_qty__{self.sku.pk}__{months[2]}': '23',
                f'sales_qty__{self.sku.pk}__{months[3]}': '14',
                f'stock_qty__{self.sku.pk}__{months[3]}': '24',
            },
        )

        self.assertEqual(response.status_code, 302)
        values = list(
            task.items.order_by('target_month').values_list('sales_qty', 'stock_qty', 'unit_price')
        )
        self.assertEqual(
            values,
            [(11, 21, 120), (12, 22, 120), (13, 23, 120), (14, 24, 120)],
        )

    def test_update_task_cell_updates_sales_qty(self):
        task = PlanTask.objects.create(
            campaign=self.campaign,
            store=self.store,
        )
        month = task.get_target_months()[0]
        item = PlanTaskItem.objects.create(
            task=task,
            sku=self.sku,
            target_month=month,
            sales_qty=8,
            unit_price=100,
            stock_qty=30,
        )

        self.client.force_login(self.owner)
        response = self.client.post(
            f'/plans/tasks/{task.pk}/update-cell/',
            {
                'sku_id': str(self.sku.pk),
                'target_month': month,
                'field': 'sales_qty',
                'value': '18',
            },
        )

        self.assertEqual(response.status_code, 200)
        item.refresh_from_db()
        self.assertEqual(item.sales_qty, 18)
        self.assertEqual(response.json()['updated_row'][month]['sales_amount'], 1800.0)

    def test_update_task_cell_updates_stock_qty(self):
        task = PlanTask.objects.create(
            campaign=self.campaign,
            store=self.store,
        )
        month = task.get_target_months()[0]
        item = PlanTaskItem.objects.create(
            task=task,
            sku=self.sku,
            target_month=month,
            sales_qty=8,
            unit_price=100,
            stock_qty=30,
        )

        self.client.force_login(self.owner)
        response = self.client.post(
            f'/plans/tasks/{task.pk}/update-cell/',
            {
                'sku_id': str(self.sku.pk),
                'target_month': month,
                'field': 'stock_qty',
                'value': '45',
            },
        )

        self.assertEqual(response.status_code, 200)
        item.refresh_from_db()
        self.assertEqual(item.stock_qty, 45)
        self.assertEqual(response.json()['updated_row'][month]['stock_qty'], 45)

    def test_update_task_cell_updates_unit_price_for_entire_row(self):
        task = PlanTask.objects.create(
            campaign=self.campaign,
            store=self.store,
        )
        months = task.get_target_months()
        for month in months:
            PlanTaskItem.objects.create(
                task=task,
                sku=self.sku,
                target_month=month,
                sales_qty=10,
                unit_price=100,
                stock_qty=30,
            )

        self.client.force_login(self.owner)
        response = self.client.post(
            f'/plans/tasks/{task.pk}/update-cell/',
            {
                'sku_id': str(self.sku.pk),
                'field': 'unit_price',
                'value': '135.5',
            },
        )

        self.assertEqual(response.status_code, 200)
        values = list(task.items.order_by('target_month').values_list('unit_price', flat=True))
        self.assertEqual(values, [135.5, 135.5, 135.5, 135.5])
        self.assertEqual(response.json()['unit_price'], 135.5)

    def test_update_task_cell_rejects_approved_task(self):
        task = PlanTask.objects.create(
            campaign=self.campaign,
            store=self.store,
            status=PlanTask.Status.APPROVED,
            approval_status=PlanTask.ApprovalStatus.APPROVED,
        )
        month = task.get_target_months()[0]
        PlanTaskItem.objects.create(
            task=task,
            sku=self.sku,
            target_month=month,
            sales_qty=8,
            unit_price=100,
            stock_qty=30,
        )

        self.client.force_login(self.owner)
        response = self.client.post(
            f'/plans/tasks/{task.pk}/update-cell/',
            {
                'sku_id': str(self.sku.pk),
                'target_month': month,
                'field': 'sales_qty',
                'value': '18',
            },
        )

        self.assertEqual(response.status_code, 403)

    def test_my_tasks_can_filter_by_approval_status(self):
        task = PlanTask.objects.create(
            campaign=self.campaign,
            store=self.store,
            approval_status=PlanTask.ApprovalStatus.PENDING,
        )
        other_store = Store.objects.create(
            name='Other Store',
            code='JD002',
            org_unit=self.platform,
            owner=self.owner,
        )
        PlanTask.objects.create(
            campaign=self.campaign,
            store=other_store,
            approval_status=PlanTask.ApprovalStatus.APPROVED,
        )

        self.client.force_login(self.owner)
        response = self.client.get('/plans/tasks/my/', {'approval_status': PlanTask.ApprovalStatus.PENDING})

        self.assertEqual(response.status_code, 200)
        self.assertEqual(list(response.context['tasks']), [task])

    def test_task_import_confirm_clears_preview_session_data(self):
        task = PlanTask.objects.create(
            campaign=self.campaign,
            store=self.store,
        )
        month = task.get_target_months()[0]
        preview_rows = [{
            'sku_id': self.sku.pk,
            'sku_code': self.sku.sku_code,
            'sku_name': self.sku.sku_name,
            'unit_price': '123.00',
            'months': {
                month: {
                    'sales_qty': 12,
                    'stock_qty': 24,
                }
            },
        }]

        session = self.client.session
        session[task_service.PREVIEW_SESSION_KEY] = {str(task.pk): preview_rows}
        session[f'task_import_errors_{task.pk}'] = ['bad row']
        session.save()

        self.client.force_login(self.owner)
        response = self.client.post(f'/plans/tasks/{task.pk}/import-confirm/')

        self.assertEqual(response.status_code, 302)
        session = self.client.session
        self.assertEqual(session.get(task_service.PREVIEW_SESSION_KEY, {}).get(str(task.pk)), None)
        self.assertEqual(session.get(f'task_import_errors_{task.pk}'), None)
        self.assertTrue(task.items.filter(sku=self.sku, target_month=month, sales_qty=12, stock_qty=24).exists())

    def test_task_submit_allows_rbac_submit_permission_without_store_ownership(self):
        task = PlanTask.objects.create(campaign=self.campaign, store=self.store)
        PlanTaskItem.objects.create(
            task=task,
            sku=self.sku,
            target_month=task.get_target_months()[0],
            sales_qty=10,
            unit_price=100,
            stock_qty=50,
        )
        outsider = User.objects.create_user(username='outsider_submit', password='pass1234', role=User.Role.STAFF)
        submit_role = Role.objects.create(code='submit_delegate', name='Submit Delegate', is_active=True)
        submit_perm, _ = Permission.objects.update_or_create(
            code='plans.task.submit',
            defaults={'module': 'plans', 'resource': 'task', 'action': 'submit', 'is_active': True},
        )
        RolePermission.objects.update_or_create(role=submit_role, permission=submit_perm)
        UserRoleAssignment.objects.create(user=outsider, role=submit_role, scope_type=UserRoleAssignment.ScopeType.STORE, store=self.store)

        self.assertTrue(task.can_submit(outsider))

    def test_report_query_returns_empty_for_user_denied_report_permission(self):
        task = PlanTask.objects.create(
            campaign=self.campaign,
            store=self.store,
            approval_status=PlanTask.ApprovalStatus.APPROVED,
        )
        PlanTaskItem.objects.create(
            task=task,
            sku=self.sku,
            target_month='2026-05',
            sales_qty=10,
            unit_price=100,
            stock_qty=50,
        )
        denied_user = User.objects.create_user(username='report_blocked', password='pass1234', role=User.Role.STAFF)
        deny_role = Role.objects.create(code='deny_report', name='Deny Report', is_active=True)
        report_perm, _ = Permission.objects.update_or_create(
            code='plans.report.view',
            defaults={'module': 'plans', 'resource': 'report', 'action': 'view', 'is_active': True},
        )
        RolePermission.objects.update_or_create(role=deny_role, permission=report_perm, defaults={'effect': RolePermission.Effect.DENY})
        UserRoleAssignment.objects.create(user=denied_user, role=deny_role)

        self.assertEqual(task_items_for_report('2026-04', PlanTask.ApprovalStatus.APPROVED, denied_user).count(), 0)
