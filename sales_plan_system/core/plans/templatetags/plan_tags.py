import builtins

from django import template
from django.db.models import Sum

register = template.Library()


@register.filter
def get_item(dictionary, key):
    """从字典中获取值"""
    if dictionary is None:
        return []
    return dictionary.get(key, [])


@register.filter
def sum(queryset, field):
    """对查询集求和"""
    if not queryset:
        return 0
    result = queryset.aggregate(total=Sum(field))
    return result['total'] or 0


@register.filter
def sum_amount(queryset):
    """计算金额总和 (sales_qty * unit_price)"""
    if not queryset:
        return 0
    total = builtins.sum(item.sales_amount for item in queryset)
    return total


@register.filter
def status_class(status):
    """根据状态返回对应的CSS类"""
    status_classes = {
        'draft': 'bg-gray-100 text-gray-800',
        'pending': 'bg-yellow-100 text-yellow-800',
        'approved': 'bg-green-100 text-green-800',
        'rejected': 'bg-red-100 text-red-800',
    }
    return status_classes.get(status, 'bg-gray-100 text-gray-800')
