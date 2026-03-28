from django.contrib.auth.decorators import login_required
from django.shortcuts import render

from core.permissions.decorators import page_access_required


@login_required
@page_access_required('mechanisms')
def mechanism_center(request):
    return render(request, 'platform/placeholder.html', {
        'title': '机制中心',
        'subtitle': '机制配置、机制商品池和机制应用将在这里继续扩展。',
        'module_name': 'mechanisms',
    })
