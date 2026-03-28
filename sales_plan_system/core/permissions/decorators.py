from functools import wraps

from django.contrib import messages
from django.http import HttpResponseForbidden
from django.shortcuts import redirect, render

from .services import permissions_service


def _build_denied_response(request, message):
    """Return the right kind of denial response depending on the request type.

    - HTMX requests get an HTTP 403 with an inline error fragment (or
      ``HX-Redirect`` for a full-page redirect).
    - Normal browser requests get a 302 redirect to the no-access page.
    """
    if getattr(request, 'htmx', False):
        # For HTMX partial requests, return a 403 with a toast-style fragment
        # so the client can swap it into the page without a full redirect.
        return HttpResponseForbidden(
            render(request, 'permissions/partials/access_denied.html', {
                'message': message,
            }).content,
            content_type='text/html',
        )
    return redirect('permissions:no_access')


def page_access_required(page_key):
    def decorator(view_func):
        @wraps(view_func)
        def _wrapped(request, *args, **kwargs):
            if permissions_service.can_access_page(request.user, page_key):
                return view_func(request, *args, **kwargs)
            messages.error(request, 'You do not have access to this page.')
            return _build_denied_response(request, 'You do not have access to this page.')

        return _wrapped

    return decorator


def permission_required(permission_code):
    """Decorator that checks a fine-grained permission code (not a page key).

    Use this for views that need permission-code-level access control beyond
    page-level gating. Example::

        @login_required
        @page_access_required('plans')
        @permission_required('plans.task.export')
        def export_task(request, pk):
            ...
    """
    def decorator(view_func):
        @wraps(view_func)
        def _wrapped(request, *args, **kwargs):
            if permissions_service.has_perm(request.user, permission_code):
                return view_func(request, *args, **kwargs)
            messages.error(request, 'You do not have the required permission.')
            return _build_denied_response(request, 'You do not have the required permission.')
        return _wrapped
    return decorator
