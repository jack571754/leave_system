from django.core.paginator import Paginator
from django.db.models import Q

from .models import ProductSKU


def filtered_skus(search='', status='', brand_id='', category_id=''):
    skus = ProductSKU.objects.select_related('brand', 'category').all()
    if search:
        skus = skus.filter(Q(sku_code__icontains=search) | Q(sku_name__icontains=search))
    if status:
        skus = skus.filter(status=status)
    if brand_id:
        skus = skus.filter(brand_id=brand_id)
    if category_id:
        skus = skus.filter(category_id=category_id)
    return skus


def paginated_skus(page_number, *, search='', status='', brand_id='', category_id='', per_page=20):
    paginator = Paginator(
        filtered_skus(search=search, status=status, brand_id=brand_id, category_id=category_id),
        per_page,
    )
    return paginator.get_page(page_number)
