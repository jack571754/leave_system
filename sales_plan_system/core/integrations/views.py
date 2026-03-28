from django.contrib.auth.decorators import login_required
from django.shortcuts import render

from core.permissions.decorators import page_access_required


@login_required
@page_access_required('integrations')
def integration_center(request):
    return render(request, 'platform/placeholder.html', {
        'title': '集成中心',
        'subtitle': '飞书登录、通知和外部系统对接会在这个模块继续接入。',
        'module_name': 'integrations',
    })
