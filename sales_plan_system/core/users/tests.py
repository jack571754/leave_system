from django.test import TestCase

from core.users.models import OrgUnit, Store, StoreMembership, User


class StorePermissionTests(TestCase):
    def setUp(self):
        self.platform = OrgUnit.objects.create(
            name='Tmall',
            code='PLAT_TMALL',
            unit_type=OrgUnit.UnitType.PLATFORM,
        )
        self.owner = User.objects.create_user(
            username='owner',
            password='pass1234',
            role=User.Role.STAFF,
        )
        self.editor = User.objects.create_user(
            username='editor',
            password='pass1234',
            role=User.Role.STAFF,
        )
        self.viewer = User.objects.create_user(
            username='viewer',
            password='pass1234',
            role=User.Role.STAFF,
        )
        self.admin = User.objects.create_user(
            username='admin2',
            password='pass1234',
            role=User.Role.ADMIN,
            is_staff=True,
            is_superuser=True,
        )
        self.store = Store.objects.create(
            name='Flagship Store',
            code='STORE001',
            org_unit=self.platform,
            owner=self.owner,
        )
        StoreMembership.objects.create(
            store=self.store,
            user=self.editor,
            role=StoreMembership.Role.EDITOR,
        )
        StoreMembership.objects.create(
            store=self.store,
            user=self.viewer,
            role=StoreMembership.Role.VIEWER,
        )

    def test_owner_can_manage_store(self):
        self.assertTrue(self.owner.can_manage_store(self.store))

    def test_editor_can_manage_store(self):
        self.assertTrue(self.editor.can_manage_store(self.store))

    def test_viewer_cannot_manage_store(self):
        self.assertFalse(self.viewer.can_manage_store(self.store))

    def test_admin_can_manage_store(self):
        self.assertTrue(self.admin.can_manage_store(self.store))
