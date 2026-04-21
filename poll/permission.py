from functools import wraps

from django.core.exceptions import PermissionDenied


def require_permission(*flag_names):
    """
    Restrict access to users who have at least one of the given boolean flags.
    Redirects to 'no_access' page if unauthorized.
    """

    def decorator(view_func):
        @wraps(view_func)
        def _wrapped_view(request, *args, **kwargs):
            if not any(getattr(request.user, flag, False) for flag in flag_names):
                raise PermissionDenied
            return view_func(request, *args, **kwargs)

        return _wrapped_view

    return decorator


class PermissionRequiredMixin:
    permission_flags = []

    def dispatch(self, request, *args, **kwargs):
        if self.permission_flags and not any(
            getattr(request.user, flag, False) for flag in self.permission_flags
        ):
            raise PermissionDenied
        return super().dispatch(request, *args, **kwargs)
