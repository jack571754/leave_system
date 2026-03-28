from django.contrib.auth.decorators import login_required
from django.shortcuts import render

from core.permissions.decorators import page_access_required


@login_required
@page_access_required('analytics')
def analytics_center(request):
    return render(request, 'platform/placeholder.html', {
        'title': '分析中心',
        'subtitle': '分析报表、异常分析和导出能力会在这个模块继续完善。',
        'module_name': 'analytics',
    })
