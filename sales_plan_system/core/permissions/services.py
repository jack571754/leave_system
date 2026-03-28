from collections import deque
from threading import local

from django.db import OperationalError, ProgrammingError, connection
from django.db.models import Q
from django.utils import timezone

from core.approvals.models import TaskApprovalInstance
from core.plans.models import PlanTask
from core.users.models import OrgUnit, Store, StoreMembership
from .models import (
    DataScopeRule,
    FrontendPagePermission,
    RolePermission,
    UserRoleAssignment,
)
from .registry import DEFAULT_PAGE_CONFIGS

_thread_local = local()


class AccessService:
    """Centralized RBAC permission service.

    All permission checks should flow through this service.  It merges
    legacy ``user.role`` with proper RBAC role assignments and provides
    both page-level and data-level access control.

    Performance notes
    -----------------
    * ``_schema_ready_cache`` 鈥?process-level bool, reset on ``post_migrate``.
    * ``_org_tree_cache`` 鈥?process-level dict of {root_id: set(descendant_ids)},
      rebuilt on ``reset_schema_cache()``.
    * Per-request caches are stored on ``request._rbac_cache`` via
      ``_get_request_cache`` so that repeated calls within the same
      request-response cycle hit the same result without extra queries.
    """

    _schema_ready_cache = None
    _org_tree_cache = None  # {root_id: set(child_ids)}

    PERMISSIONS_TABLES = {
        'permissions_frontendpagepermission',
        'permissions_role',
        'permissions_permission',
        'permissions_rolepermission',
        'permissions_userroleassignment',
        'permissions_datapermissionconfig',
        'permissions_datascoperule',
    }

    # ------------------------------------------------------------------
    # Request-level cache helpers
    # ------------------------------------------------------------------
    def _get_request_cache(self, request_or_user):
        """Return a per-request dict for caching permission results.

        Resolution order:
        1. ``request._rbac_cache`` (set by RBACCacheMiddleware on every
           authenticated request)
        2. ``user._request._rbac_cache`` (when a User object is passed
           that has a back-reference to its request)
        3. Empty throwaway dict (management commands, tests calling
           service methods directly 鈥?no caching to avoid stale data)
        """
        # Direct request object
        if hasattr(request_or_user, '_rbac_cache'):
            return request_or_user._rbac_cache
        # User 鈫?request chain
        request = getattr(request_or_user, '_request', None)
        if request and hasattr(request, '_rbac_cache'):
            return request._rbac_cache
        # No request context 鈫?no caching (avoids stale data in tests/scripts)
        return {}

    @classmethod
    def clear_all_caches(cls):
        """Clear all process-level caches (schema readiness, org tree)."""
        cls.reset_schema_cache()

    # ------------------------------------------------------------------
    # Admin helpers
    # ------------------------------------------------------------------
    def _is_admin_user(self, user):
        cache = self._get_request_cache(user)
        key = '_is_admin'
        if key in cache:
            return cache[key]
        if getattr(user, 'is_superuser', False):
            cache[key] = True
            return True
        result = 'admin' in self.get_user_role_codes(user)
        cache[key] = result
        return result

    def is_rbac_ready(self):
        return self._permissions_schema_ready()

    # ------------------------------------------------------------------
    # Page visibility  (optimised: single role-codes fetch)
    # ------------------------------------------------------------------
    def get_visible_pages(self, user):
        if not self._permissions_schema_ready():
            pages = [self._build_fallback_page(config) for config in DEFAULT_PAGE_CONFIGS]
            return [page for page in pages if self.can_access_page(user, page.page_key)]

        # Fetch all pages in one query then filter in Python with a
        # single ``get_user_role_codes`` call instead of N calls.
        pages = list(
            FrontendPagePermission.objects.filter(is_active=True).order_by('menu_order', 'page_key')
        )
        if not pages:
            return []

        user_roles = self.get_user_role_codes(user)
        is_admin = self._is_admin_user(user)
        perm_codes = self.get_effective_permission_codes(user) if (not is_admin and user_roles) else set()

        result = []
        for page in pages:
            if page.allow_all_users:
                result.append(page)
            elif is_admin:
                result.append(page)
            elif page.permission_code and page.permission_code in perm_codes:
                result.append(page)
            else:
                # M2M check: use prefetched allowed_roles
                page_role_codes = self._get_page_allowed_role_codes(page)
                if user_roles.intersection(page_role_codes):
                    result.append(page)
        return result

    def get_visible_page_keys(self, user):
        return {page.page_key for page in self.get_visible_pages(user)}

    def get_navigation_pages(self, user):
        return [page for page in self.get_visible_pages(user) if page.show_in_menu and page.url_name]

    # ------------------------------------------------------------------
    # Role resolution
    # ------------------------------------------------------------------
    def get_user_role_codes(self, user, *, store=None, org_unit=None):
        if not getattr(user, 'is_authenticated', False):
            return set()

        # Per-request cache key includes scope params
        cache = self._get_request_cache(user)
        cache_key = ('role_codes', store, org_unit)
        if cache_key in cache:
            return cache[cache_key]

        role_codes = set()
        legacy_role = getattr(user, 'role', None)
        if legacy_role:
            role_codes.add(legacy_role)

        if not self._permissions_schema_ready():
            cache[cache_key] = role_codes
            return role_codes

        now = timezone.now()
        assignments = UserRoleAssignment.objects.filter(
            user=user,
            is_active=True,
            role__is_active=True,
        ).filter(
            Q(starts_at__isnull=True) | Q(starts_at__lte=now),
            Q(ends_at__isnull=True) | Q(ends_at__gte=now),
        ).select_related('role', 'org_unit', 'store')

        resolved_store = store or getattr(user, 'store', None)
        resolved_org_unit = org_unit or getattr(resolved_store, 'org_unit', None) or getattr(user, 'org_unit', None)

        for assignment in assignments:
            if self._assignment_applies(assignment, store=resolved_store, org_unit=resolved_org_unit):
                role_codes.add(assignment.role.code)

        cache[cache_key] = role_codes
        return role_codes

    # ------------------------------------------------------------------
    # Permission resolution
    # ------------------------------------------------------------------
    def get_effective_permission_codes(self, user, *, obj=None, store=None, org_unit=None):
        if not getattr(user, 'is_authenticated', False):
            return set()
        if not self._permissions_schema_ready():
            return self._fallback_permission_codes(user)

        # Per-request cache
        cache = self._get_request_cache(user)
        cache_key = ('perm_codes', store, org_unit)
        if cache_key in cache:
            return cache[cache_key]

        resolved_store = store or getattr(obj, 'store', None) or getattr(user, 'store', None)
        resolved_org_unit = org_unit or getattr(obj, 'org_unit', None) or getattr(resolved_store, 'org_unit', None) or getattr(user, 'org_unit', None)
        role_codes = self.get_user_role_codes(user, store=resolved_store, org_unit=resolved_org_unit)
        if not role_codes:
            cache[cache_key] = set()
            return set()

        links = RolePermission.objects.filter(
            role__code__in=role_codes,
            role__is_active=True,
            permission__is_active=True,
        ).select_related('permission')

        allowed = set()
        denied = set()
        for link in links:
            code = link.permission.code
            if link.effect == RolePermission.Effect.DENY:
                denied.add(code)
                allowed.discard(code)
            elif code not in denied:
                allowed.add(code)

        cache[cache_key] = allowed
        return allowed

    def has_perm(self, user, permission_code, *, obj=None, store=None, org_unit=None):
        if not getattr(user, 'is_authenticated', False):
            return False
        # Django superuser bypasses RBAC entirely
        if getattr(user, 'is_superuser', False):
            return True
        # Explicit deny takes priority 鈥?applies to ALL role-based users including admin
        role_codes = self.get_user_role_codes(user, store=store, org_unit=org_unit)
        if self._is_permission_denied(role_codes, permission_code):
            return False
        # Admin role (legacy or RBAC) gets all non-denied permissions
        if 'admin' in role_codes:
            return True
        # Standard permission check
        return permission_code in self.get_effective_permission_codes(user, obj=obj, store=store, org_unit=org_unit)

    def has_any_perm(self, user, permission_codes, *, obj=None, store=None, org_unit=None):
        if not getattr(user, 'is_authenticated', False):
            return False
        if getattr(user, 'is_superuser', False):
            return True
        role_codes = self.get_user_role_codes(user, store=store, org_unit=org_unit)
        codes_set = set(permission_codes)
        # Explicit deny takes priority
        if self._any_permission_denied(role_codes, codes_set):
            return False
        if 'admin' in role_codes:
            return True
        effective = self.get_effective_permission_codes(user, obj=obj, store=store, org_unit=org_unit)
        return bool(effective.intersection(codes_set))

    def _is_permission_denied(self, role_codes, permission_code):
        """Check if a specific permission is explicitly denied for any of the user's roles."""
        if not self._permissions_schema_ready():
            return False
        return RolePermission.objects.filter(
            role__code__in=role_codes,
            permission__code=permission_code,
            permission__is_active=True,
            effect=RolePermission.Effect.DENY,
            role__is_active=True,
        ).exists()

    def _any_permission_denied(self, role_codes, permission_codes):
        """Check if any of the given permissions are denied for the user's roles."""
        if not self._permissions_schema_ready():
            return False
        return RolePermission.objects.filter(
            role__code__in=role_codes,
            permission__code__in=permission_codes,
            permission__is_active=True,
            effect=RolePermission.Effect.DENY,
            role__is_active=True,
        ).exists()

    def _get_page_allowed_role_codes(self, page):
        if hasattr(page, '_prefetched_objects_cache') and 'allowed_roles' in page._prefetched_objects_cache:
            return {role.code for role in page._prefetched_objects_cache['allowed_roles']}
        return set(page.allowed_roles.values_list('code', flat=True))
    def can_access_page(self, user, page_key):
        if page_key == 'no_access':
            return True

        # Fast path: check if visible_page_keys was already computed this request
        cache = self._get_request_cache(user)
        visible_keys = cache.get('_visible_page_keys')
        if visible_keys is not None:
            return page_key in visible_keys

        if not self._permissions_schema_ready():
            return self._can_access_page_fallback(user, page_key)

        page = FrontendPagePermission.objects.filter(page_key=page_key, is_active=True).first()
        if not page:
            return False
        if page.allow_all_users:
            return True
        if not getattr(user, 'is_authenticated', False):
            return False
        if self._is_admin_user(user):
            return True
        if page.permission_code and self.has_perm(user, page.permission_code):
            return True

        user_roles = self.get_user_role_codes(user)
        return bool(user_roles.intersection(self._get_page_allowed_role_codes(page)))

    # ------------------------------------------------------------------
    # Business-level permission shortcuts
    # ------------------------------------------------------------------
    def can_manage_campaigns(self, user):
        return self.has_perm(user, 'plans.task.manage')

    def can_view_task(self, user, task):
        if self.has_perm(user, 'plans.task.view', obj=task):
            return True
        if not getattr(user, 'is_authenticated', False):
            return False
        if task.assignee_id == user.id:
            return True
        return user.can_manage_store(task.store)

    def can_edit_task(self, user, task):
        if not task.is_in_edit_window():
            return False
        if task.approval_status not in [
            task.ApprovalStatus.NOT_STARTED,
            task.ApprovalStatus.REJECTED,
            task.ApprovalStatus.WITHDRAWN,
        ]:
            return False
        if self.has_any_perm(user, ['plans.task.manage', 'plans.task.edit'], obj=task):
            return True
        if task.assignee_id == user.id:
            return True
        return user.can_manage_store(task.store)

    def can_submit_task(self, user, task):
        if not task.items.exists():
            return False
        if self.has_perm(user, 'plans.task.submit', obj=task):
            return task.campaign.is_open()
        return self.can_edit_task(user, task)

    def can_withdraw_task(self, user, task):
        if task.approval_status != task.ApprovalStatus.PENDING:
            return False
        if self.has_perm(user, 'plans.task.withdraw', obj=task):
            return True
        return user.id == task.submitter_id

    def can_approve_task(self, user, task):
        if task.approval_status != task.ApprovalStatus.PENDING:
            return False
        if self.has_perm(user, 'approvals.instance.approve', obj=task):
            return True
        return task.pending_approver_id == user.id

    def can_view_report(self, user):
        return self.has_perm(user, 'plans.report.view')

    def can_view_approval_instance(self, user, instance):
        if self.has_any_perm(user, ['approvals.instance.view', 'approvals.instance.approve'], obj=instance.task):
            return True
        return (
            instance.submitter_id == user.id
            or instance.pending_approver_id == user.id
        )

    def can_access_store(self, user, store_or_store_id):
        store_id = getattr(store_or_store_id, 'id', store_or_store_id)
        return store_id in self.get_authorized_store_ids(user)

    # ------------------------------------------------------------------
    # Data-level store authorisation
    # ------------------------------------------------------------------
    def get_authorized_store_ids(self, user):
        if not getattr(user, 'is_authenticated', False):
            return set()

        # Per-request cache
        cache = self._get_request_cache(user)
        if '_authorized_store_ids' in cache:
            return cache['_authorized_store_ids']

        if self._is_admin_user(user):
            result = set(Store.objects.filter(is_active=True).values_list('id', flat=True))
            cache['_authorized_store_ids'] = result
            return result

        store_ids = set()

        # Batch 1: Owned stores + membership stores (2 queries combined via UNION)
        owned_store_ids = set(
            Store.objects.filter(owner=user, is_active=True).values_list('id', flat=True)
        )
        member_store_ids = set(
            StoreMembership.objects.filter(user=user, is_active=True).values_list('store_id', flat=True)
        )
        store_ids.update(owned_store_ids)
        store_ids.update(member_store_ids)

        # Batch 2: Task-related stores (PlanTask + TaskApprovalInstance combined)
        task_store_ids = set(
            PlanTask.objects.filter(
                Q(assignee=user) | Q(submitter=user) | Q(pending_approver=user)
            ).values_list('store_id', flat=True)
        )
        approval_store_ids = set(
            TaskApprovalInstance.objects.filter(
                Q(submitter=user) | Q(pending_approver=user)
            ).values_list('task__store_id', flat=True)
        )
        store_ids.update(task_store_ids)
        store_ids.update(approval_store_ids)

        if self._permissions_schema_ready():
            for rule in self._matching_data_scope_rules(user):
                self._expand_store_scope(store_ids, rule.scope_type, rule.org_units.all(), rule.stores.all(), user)

        cache['_authorized_store_ids'] = store_ids
        return store_ids

    # ------------------------------------------------------------------
    # Data scope rule matching (unified 鈥?DataScopeRule only)
    # ------------------------------------------------------------------
    def _matching_data_scope_rules(self, user):
        if not self._permissions_schema_ready():
            return []

        user_roles = self.get_user_role_codes(user)
        rules = DataScopeRule.objects.filter(is_active=True).prefetch_related('target_users', 'target_roles', 'org_units', 'stores').distinct()

        user_pk = user.pk
        role_codes_lower = {c.lower() for c in user_roles}
        matched = []
        for rule in rules:
            if rule.subject_type == DataScopeRule.SubjectType.USER:
                if any(u.pk == user_pk for u in rule.target_users.all()):
                    matched.append(rule)
            elif rule.subject_type == DataScopeRule.SubjectType.ROLE:
                rule_role_codes = {r.code.lower() for r in rule.target_roles.all()}
                if role_codes_lower.intersection(rule_role_codes):
                    matched.append(rule)
        return matched

    # ------------------------------------------------------------------
    # Store scope expansion
    # ------------------------------------------------------------------
    def _expand_store_scope(self, store_ids, scope_type, org_units, stores, user):
        if scope_type == DataScopeRule.ScopeType.ALL:
            store_ids.update(Store.objects.filter(is_active=True).values_list('id', flat=True))
        elif scope_type == DataScopeRule.ScopeType.STORE:
            store_ids.update(stores.filter(is_active=True).values_list('id', flat=True))
        elif scope_type == DataScopeRule.ScopeType.ORG_UNIT:
            org_unit_ids = set()
            for org_unit in org_units:
                org_unit_ids.add(org_unit.id)
                org_unit_ids.update(self._descendant_org_unit_ids(org_unit.id))
            if org_unit_ids:
                store_ids.update(Store.objects.filter(org_unit_id__in=org_unit_ids, is_active=True).values_list('id', flat=True))
        elif scope_type == DataScopeRule.ScopeType.SELF:
            store_ids.update(Store.objects.filter(owner=user, is_active=True).values_list('id', flat=True))
        elif scope_type == DataScopeRule.ScopeType.SUBORDINATE:
            store_ids.update(Store.objects.filter(owner__manager=user, is_active=True).values_list('id', flat=True))
        elif scope_type == DataScopeRule.ScopeType.ASSIGNED:
            store_ids.update(StoreMembership.objects.filter(user=user, is_active=True).values_list('store_id', flat=True))

    # ------------------------------------------------------------------
    # Assignment scope helpers
    # ------------------------------------------------------------------
    def _assignment_applies(self, assignment, *, store=None, org_unit=None):
        if assignment.scope_type == UserRoleAssignment.ScopeType.GLOBAL:
            return True
        if assignment.scope_type == UserRoleAssignment.ScopeType.STORE:
            return bool(store and assignment.store_id == store.id)
        if assignment.scope_type == UserRoleAssignment.ScopeType.ORG_UNIT:
            target_org_unit = org_unit or getattr(store, 'org_unit', None)
            return self._org_unit_matches_scope(target_org_unit, assignment.org_unit)
        return False

    def _org_unit_matches_scope(self, current, scoped_org_unit):
        node = current
        while node:
            if scoped_org_unit and node.id == scoped_org_unit.id:
                return True
            node = node.parent
        return False

    # ------------------------------------------------------------------
    # Org-unit tree helpers (cached at process level)
    # ------------------------------------------------------------------
    def _descendant_org_unit_ids(self, root_id):
        if self._org_tree_cache is None:
            self._build_org_tree_cache()
        return self._org_tree_cache.get(root_id, {root_id})

    def _build_org_tree_cache(self):
        """Build a complete parent鈫抎escendants map with O(N) single-pass traversal.

        Uses a single query to fetch all (parent_id, id) pairs, then builds
        the children map and propagates descendants bottom-up in one pass.
        """
        from collections import defaultdict

        # Single query: get all (parent_id, id) pairs
        pairs = list(OrgUnit.objects.exclude(parent_id__isnull=True).values_list('parent_id', 'id'))
        children_of = defaultdict(list)
        for parent_id, child_id in pairs:
            children_of[parent_id].append(child_id)

        # Collect all node IDs (both parents and children)
        all_ids = set()
        for parent_id, child_id in pairs:
            all_ids.add(parent_id)
            all_ids.add(child_id)

        # Bottom-up: compute descendants for each node in a single pass
        # Use memoization 鈥?process leaves first, then propagate upward
        descendants_map = {}

        def _get_descendants(node_id, visited=None):
            if node_id in descendants_map:
                return descendants_map[node_id]
            if visited is None:
                visited = set()
            if node_id in visited:
                return set()  # cycle guard
            visited.add(node_id)

            result = set()
            for child_id in children_of.get(node_id, []):
                result.add(child_id)
                result.update(_get_descendants(child_id, visited))
            descendants_map[node_id] = result
            return result

        for node_id in all_ids:
            _get_descendants(node_id)

        # Ensure every node has an entry (empty set for leaves)
        for node_id in all_ids:
            if node_id not in descendants_map:
                descendants_map[node_id] = set()

        self._org_tree_cache = descendants_map

    # ------------------------------------------------------------------
    # Schema readiness (cached at process level)
    # ------------------------------------------------------------------
    def _permissions_schema_ready(self):
        if self._schema_ready_cache is not None:
            return self._schema_ready_cache
        try:
            table_names = set(connection.introspection.table_names())
        except (OperationalError, ProgrammingError):
            return False
        result = self.PERMISSIONS_TABLES.issubset(table_names)
        self._schema_ready_cache = result
        return result

    @classmethod
    def reset_schema_cache(cls):
        """Reset all process-level caches (called after migrations)."""
        cls._schema_ready_cache = None
        cls._org_tree_cache = None

    # ------------------------------------------------------------------
    # Fallback helpers (pre-RBAC / legacy)
    # ------------------------------------------------------------------
    def _fallback_permission_codes(self, user):
        cache = self._get_request_cache(user)
        if '_fallback_perms' in cache:
            return cache['_fallback_perms']

        role = getattr(user, 'role', None)
        if role == getattr(user.Role, 'ADMIN', None):
            result = {
                'dashboard.view', 'products.sku.view', 'plans.task.view', 'plans.task.manage',
                'plans.task.edit', 'plans.task.submit', 'plans.task.withdraw', 'plans.task.export',
                'plans.report.view', 'approvals.center.view', 'approvals.instance.view',
                'approvals.instance.approve', 'permissions.center.view', 'mechanisms.center.view',
                'analytics.center.view', 'integrations.center.view',
            }
        elif role in {getattr(user.Role, 'MANAGER', None), getattr(user.Role, 'SUPERVISOR', None)}:
            result = {
                'dashboard.view', 'products.sku.view', 'plans.task.view', 'plans.task.manage',
                'plans.task.edit', 'plans.task.submit', 'plans.task.withdraw', 'plans.task.export',
                'plans.report.view', 'approvals.center.view', 'approvals.instance.view',
                'approvals.instance.approve', 'mechanisms.center.view', 'analytics.center.view',
            }
        elif role == getattr(user.Role, 'STAFF', None):
            result = {
                'dashboard.view', 'products.sku.view', 'plans.task.view', 'plans.task.edit',
                'plans.task.submit', 'plans.task.withdraw', 'approvals.center.view',
                'approvals.instance.view',
            }
        else:
            result = set()

        cache['_fallback_perms'] = result
        return result

    def _can_access_page_fallback(self, user, page_key):
        config = next((item for item in DEFAULT_PAGE_CONFIGS if item['page_key'] == page_key), None)
        if not config:
            return False
        if config.get('allow_all_users'):
            return True
        if not getattr(user, 'is_authenticated', False):
            return False
        if self._is_admin_user(user):
            return True
        permission_code = config.get('permission_code')
        if permission_code and permission_code in self._fallback_permission_codes(user):
            return True
        user_roles = self.get_user_role_codes(user)
        return bool(user_roles.intersection(set(config.get('allowed_roles') or [])))

    def _build_fallback_page(self, config):
        return type('FallbackPage', (), config)()


permissions_service = AccessService()
access_service = permissions_service


