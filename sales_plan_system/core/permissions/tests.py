from datetime import timedelta

from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from core.permissions.models import (
    DataPermissionConfig,
    DataScopeRule,
    FrontendPagePermission,
    Permission,
    Role,
    RolePermission,
    UserRoleAssignment,
)
from core.permissions.registry import DEFAULT_PERMISSION_CONFIGS, DEFAULT_ROLE_CONFIGS
from core.permissions.services import permissions_service
from core.users.models import OrgUnit, Store, User


class _ClearCacheMixin:
    """Clear permission caches before each test to avoid cross-test contamination."""

    def setUp(self):
        super().setUp()
        permissions_service.clear_all_caches()


class PermissionCenterTests(_ClearCacheMixin, TestCase):
    @staticmethod
    def ensure_permissions_page(**overrides):
        allowed_roles = overrides.pop('allowed_roles', ['admin'])
        defaults = {
            'label': 'Permissions',
            'url_name': 'permissions:center',
            'permission_code': '',
            'is_active': True,
            '_legacy_allowed_roles': allowed_roles,
        }
        defaults.update(overrides)
        page, _ = FrontendPagePermission.objects.update_or_create(
            page_key='permissions',
            defaults=defaults,
        )
        page.allowed_roles.set(Role.objects.filter(code__in=allowed_roles))

    def test_permission_center_requires_login(self):
        response = self.client.get(reverse('permissions:center'))
        self.assertEqual(response.status_code, 302)

    def test_permission_center_requires_admin_role_without_rbac_assignment(self):
        user = User.objects.create_user(username='perm_user', password='pass1234', role=User.Role.STAFF)
        self.ensure_permissions_page()
        self.client.force_login(user)
        response = self.client.get(reverse('permissions:center'))
        self.assertEqual(response.status_code, 302)
        self.assertIn(reverse('permissions:no_access'), response.url)

    def test_permission_center_renders_for_admin(self):
        user = User.objects.create_user(username='perm_admin', password='pass1234', role=User.Role.ADMIN)
        self.ensure_permissions_page()
        self.client.force_login(user)
        response = self.client.get(reverse('permissions:center'))
        self.assertEqual(response.status_code, 200)

    def test_permission_center_allows_rbac_permission_code(self):
        user = User.objects.create_user(username='rbac_user', password='pass1234', role=User.Role.STAFF)
        role, _ = Role.objects.update_or_create(
            code='perm_admin',
            defaults={'name': 'Permission Admin', 'is_active': True},
        )
        permission, _ = Permission.objects.update_or_create(
            code='permissions.center.view',
            defaults={
                'module': 'permissions',
                'resource': 'center',
                'action': 'view',
                'is_active': True,
            },
        )
        RolePermission.objects.update_or_create(role=role, permission=permission)
        UserRoleAssignment.objects.update_or_create(user=user, role=role)
        self.ensure_permissions_page(permission_code='permissions.center.view')

        self.client.force_login(user)
        response = self.client.get(reverse('permissions:center'))
        self.assertEqual(response.status_code, 200)

    def test_data_scope_rule_expands_authorized_store_ids(self):
        org_unit = OrgUnit.objects.create(name='Platform A', code='PLAT-A', unit_type=OrgUnit.UnitType.PLATFORM)
        user = User.objects.create_user(username='scope_user', password='pass1234', role=User.Role.STAFF, org_unit=org_unit)
        store = Store.objects.create(name='Store A', code='STORE-A', org_unit=org_unit)
        role = Role.objects.create(code='regional_viewer', name='Regional Viewer', is_active=True)
        UserRoleAssignment.objects.create(user=user, role=role, scope_type=UserRoleAssignment.ScopeType.ORG_UNIT, org_unit=org_unit)
        rule = DataScopeRule.objects.create(
            name='Regional Store Access',
            resource_code='store',
            subject_type=DataScopeRule.SubjectType.ROLE,
            scope_type=DataScopeRule.ScopeType.ORG_UNIT,
            is_active=True,
        )
        rule.target_roles.add(role)
        rule.org_units.add(org_unit)

        self.assertIn(store.id, permissions_service.get_authorized_store_ids(user))


# ---------------------------------------------------------------------------
# Phase 4: Comprehensive RBAC test coverage
# ---------------------------------------------------------------------------


class AdminHelperTests(_ClearCacheMixin, TestCase):
    """Tests for the centralized _is_admin_user helper."""

    def test_superuser_is_admin(self):
        user = User.objects.create_user(username='su', password='pass', role=User.Role.STAFF, is_superuser=True)
        self.assertTrue(permissions_service._is_admin_user(user))

    def test_legacy_admin_role_is_admin(self):
        user = User.objects.create_user(username='legacy_admin', password='pass', role=User.Role.ADMIN)
        self.assertTrue(permissions_service._is_admin_user(user))

    def test_rbac_admin_role_is_admin(self):
        user = User.objects.create_user(username='rbac_admin', password='pass', role=User.Role.STAFF)
        admin_role, _ = Role.objects.update_or_create(code='admin', defaults={'name': 'Admin', 'is_active': True})
        UserRoleAssignment.objects.create(user=user, role=admin_role, scope_type=UserRoleAssignment.ScopeType.GLOBAL)
        self.assertTrue(permissions_service._is_admin_user(user))

    def test_staff_is_not_admin(self):
        user = User.objects.create_user(username='staff', password='pass', role=User.Role.STAFF)
        self.assertFalse(permissions_service._is_admin_user(user))


class DenyOverrideTests(_ClearCacheMixin, TestCase):
    """Tests for DENY overriding ALLOW in permission resolution."""

    def setUp(self):
        self.user = User.objects.create_user(username='deny_user', password='pass', role=User.Role.STAFF)
        self.allow_role = Role.objects.create(code='allow_role', name='Allow Role', is_active=True)
        self.deny_role = Role.objects.create(code='deny_role', name='Deny Role', is_active=True)
        self.perm = Permission.objects.create(code='test.deny.check', module='test', resource='deny', action='check')
        UserRoleAssignment.objects.create(user=self.user, role=self.allow_role, scope_type=UserRoleAssignment.ScopeType.GLOBAL)
        UserRoleAssignment.objects.create(user=self.user, role=self.deny_role, scope_type=UserRoleAssignment.ScopeType.GLOBAL)

    def test_deny_overrides_allow(self):
        RolePermission.objects.create(role=self.allow_role, permission=self.perm, effect=RolePermission.Effect.ALLOW)
        RolePermission.objects.create(role=self.deny_role, permission=self.perm, effect=RolePermission.Effect.DENY)
        self.assertFalse(permissions_service.has_perm(self.user, 'test.deny.check'))


class TimeExpiryTests(_ClearCacheMixin, TestCase):
    """Tests for time-bounded role assignments."""

    def setUp(self):
        self.user = User.objects.create_user(username='time_user', password='pass', role=User.Role.STAFF)
        self.role = Role.objects.create(code='temp_role', name='Temp Role', is_active=True)
        self.perm = Permission.objects.create(code='temp.perm', module='temp', resource='perm', action='view')

    def test_expired_assignment_not_counted(self):
        UserRoleAssignment.objects.create(
            user=self.user, role=self.role, scope_type=UserRoleAssignment.ScopeType.GLOBAL,
            starts_at=timezone.now() - timedelta(days=10),
            ends_at=timezone.now() - timedelta(days=1),
        )
        RolePermission.objects.create(role=self.role, permission=self.perm, effect=RolePermission.Effect.ALLOW)
        self.assertFalse(permissions_service.has_perm(self.user, 'temp.perm'))

    def test_active_assignment_counted(self):
        UserRoleAssignment.objects.create(
            user=self.user, role=self.role, scope_type=UserRoleAssignment.ScopeType.GLOBAL,
            starts_at=timezone.now() - timedelta(days=1),
            ends_at=timezone.now() + timedelta(days=10),
        )
        RolePermission.objects.create(role=self.role, permission=self.perm, effect=RolePermission.Effect.ALLOW)
        self.assertTrue(permissions_service.has_perm(self.user, 'temp.perm'))


class ScopedAssignmentTests(_ClearCacheMixin, TestCase):
    """Tests for scoped role assignments (GLOBAL vs STORE vs ORG_UNIT)."""

    def setUp(self):
        self.org_unit = OrgUnit.objects.create(name='Test OU', code='OU1', unit_type=OrgUnit.UnitType.PLATFORM)
        self.store_a = Store.objects.create(name='Store A', code='SA', org_unit=self.org_unit)
        self.store_b = Store.objects.create(name='Store B', code='SB', org_unit=self.org_unit)
        self.user = User.objects.create_user(username='scoped_user', password='pass', role=User.Role.STAFF)

    def test_store_scoped_assignment_resolves_role_code(self):
        """Store-scoped role assignment contributes role code when querying with matching store."""
        role = Role.objects.create(code='store_viewer', name='Store Viewer', is_active=True)
        UserRoleAssignment.objects.create(
            user=self.user, role=role, scope_type=UserRoleAssignment.ScopeType.STORE, store=self.store_a,
        )
        # When resolving roles with store_a context, the role code should appear
        role_codes = permissions_service.get_user_role_codes(self.user, store=self.store_a)
        self.assertIn('store_viewer', role_codes)
        # When resolving with a different store, it should NOT appear
        role_codes_other = permissions_service.get_user_role_codes(self.user, store=self.store_b)
        self.assertNotIn('store_viewer', role_codes_other)

    def test_global_assignment_applies_everywhere(self):
        role = Role.objects.create(code='global_viewer', name='Global Viewer', is_active=True)
        UserRoleAssignment.objects.create(
            user=self.user, role=role, scope_type=UserRoleAssignment.ScopeType.GLOBAL,
        )
        authorized = permissions_service.get_authorized_store_ids(self.user)
        # Global assignment doesn't automatically add stores without data scope rules,
        # but the role code should be resolved
        role_codes = permissions_service.get_user_role_codes(self.user)
        self.assertIn('global_viewer', role_codes)


class DecoratorTests(_ClearCacheMixin, TestCase):
    """Tests for @page_access_required decorator behavior."""

    def setUp(self):
        page, _ = FrontendPagePermission.objects.update_or_create(
            page_key='test_reports',
            defaults={
                'label': 'Test Reports',
                'url_name': 'plans:plan_report',
                'permission_code': 'plans.report.view',
                'allow_all_users': False,
                '_legacy_allowed_roles': ['admin', 'manager', 'supervisor'],
                'is_active': True,
            },
        )
        page.allowed_roles.set(Role.objects.filter(code__in=['admin', 'manager', 'supervisor']))

    def test_staff_redirected_from_restricted_page(self):
        user = User.objects.create_user(username='staff_decor', password='pass', role=User.Role.STAFF)
        self.client.force_login(user)
        response = self.client.get(reverse('plans:plan_report'))
        # Should be redirected (302) to no_access
        self.assertIn(response.status_code, [302, 403])

    def test_manager_can_access_report_page(self):
        user = User.objects.create_user(username='mgr_decor', password='pass', role=User.Role.MANAGER)
        self.client.force_login(user)
        response = self.client.get(reverse('plans:plan_report'))
        self.assertEqual(response.status_code, 200)


class DataScopeExpansionTests(_ClearCacheMixin, TestCase):
    """Tests for store scope expansion in get_authorized_store_ids."""

    def setUp(self):
        self.parent_ou = OrgUnit.objects.create(name='Parent OU', code='P-OU', unit_type=OrgUnit.UnitType.GROUP)
        self.child_ou = OrgUnit.objects.create(name='Child OU', code='C-OU', unit_type=OrgUnit.UnitType.PLATFORM, parent=self.parent_ou)
        self.store = Store.objects.create(name='Child Store', code='CS', org_unit=self.child_ou)
        self.user = User.objects.create_user(username='scope_user', password='pass', role=User.Role.STAFF)

    def test_org_unit_scope_expands_to_descendant_stores(self):
        role = Role.objects.create(code='ou_viewer', name='OU Viewer', is_active=True)
        rule = DataScopeRule.objects.create(
            name='OU Rule', resource_code='store',
            subject_type=DataScopeRule.SubjectType.ROLE,
            scope_type=DataScopeRule.ScopeType.ORG_UNIT,
            is_active=True,
        )
        rule.target_roles.add(role)
        rule.org_units.add(self.parent_ou)
        UserRoleAssignment.objects.create(user=self.user, role=role, scope_type=UserRoleAssignment.ScopeType.GLOBAL)

        authorized = permissions_service.get_authorized_store_ids(self.user)
        self.assertIn(self.store.id, authorized)

    def test_self_scope_returns_owned_stores(self):
        self.store.owner = self.user
        self.store.save()
        role = Role.objects.create(code='self_viewer', name='Self Viewer', is_active=True)
        rule = DataScopeRule.objects.create(
            name='Self Rule', resource_code='store',
            subject_type=DataScopeRule.SubjectType.ROLE,
            scope_type=DataScopeRule.ScopeType.SELF,
            is_active=True,
        )
        rule.target_roles.add(role)
        UserRoleAssignment.objects.create(user=self.user, role=role, scope_type=UserRoleAssignment.ScopeType.GLOBAL)

        authorized = permissions_service.get_authorized_store_ids(self.user)
        self.assertIn(self.store.id, authorized)


class InactiveEntityTests(_ClearCacheMixin, TestCase):
    """Tests that is_active=False entities are excluded."""

    def test_inactive_role_not_counted(self):
        user = User.objects.create_user(username='inactive_role_user', password='pass', role=User.Role.STAFF)
        role = Role.objects.create(code='dead_role', name='Dead Role', is_active=False)
        UserRoleAssignment.objects.create(user=user, role=role, scope_type=UserRoleAssignment.ScopeType.GLOBAL)
        role_codes = permissions_service.get_user_role_codes(user)
        self.assertNotIn('dead_role', role_codes)

    def test_inactive_assignment_not_counted(self):
        user = User.objects.create_user(username='inactive_assign', password='pass', role=User.Role.STAFF)
        role = Role.objects.create(code='live_role', name='Live Role', is_active=True)
        UserRoleAssignment.objects.create(user=user, role=role, scope_type=UserRoleAssignment.ScopeType.GLOBAL, is_active=False)
        role_codes = permissions_service.get_user_role_codes(user)
        self.assertNotIn('live_role', role_codes)

    def test_default_permission_and_role_registry_is_seedable(self):
        self.assertTrue(any(item['code'] == 'permissions.center.view' for item in DEFAULT_PERMISSION_CONFIGS))
        self.assertTrue(any(item['code'] == 'admin' for item in DEFAULT_ROLE_CONFIGS))


