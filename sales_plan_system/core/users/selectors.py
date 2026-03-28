from .models import OrgUnit, Store


def active_org_units():
    return OrgUnit.objects.filter(is_active=True).order_by('unit_type', 'code')


def active_stores(org_unit_id=''):
    stores = Store.objects.filter(is_active=True).select_related('org_unit', 'owner').order_by('org_unit__code', 'code')
    if org_unit_id:
        stores = stores.filter(org_unit_id=org_unit_id)
    return stores
