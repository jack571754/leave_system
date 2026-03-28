def environment_callback(request):
    from django.conf import settings

    if settings.DEBUG:
        return [
            ("开发环境", "warning"),
        ]
    return [
        ("生产环境", "success"),
    ]
