from .services import permissions_service


def permission_navigation(request):
    if not getattr(request.user, 'is_authenticated', False):
        return {
            'visible_navigation_pages': [],
            'visible_page_keys': set(),
            'active_page_key': None,
        }

    # Compute visible pages once and derive both values from it
    visible_pages = permissions_service.get_visible_pages(request.user)
    page_keys = {page.page_key for page in visible_pages}

    # Resolve active page key for sub-page nav highlighting.
    # Convention: view_name like "plans:task_detail" → page_key "plans"
    active_page_key = None
    match = getattr(request, 'resolver_match', None)
    if match and match.view_name:
        view_prefix = match.view_name.split(':')[0]
        if view_prefix in page_keys:
            active_page_key = view_prefix

    return {
        'visible_navigation_pages': [p for p in visible_pages if p.show_in_menu and p.url_name],
        'visible_page_keys': page_keys,
        'active_page_key': active_page_key,
    }
