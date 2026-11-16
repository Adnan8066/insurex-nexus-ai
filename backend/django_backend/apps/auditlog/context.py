from contextvars import ContextVar


_current_actor = ContextVar('audit_actor', default=None)


def get_current_actor():
    actor = _current_actor.get()
    return actor if actor is not None and getattr(actor, 'is_authenticated', False) else None


class AuditActorViewSetMixin:
    """Set actor after DRF authentication, including JWT, for the request lifetime."""

    def initial(self, request, *args, **kwargs):
        super().initial(request, *args, **kwargs)
        self._audit_actor_token = _current_actor.set(request.user)

    def finalize_response(self, request, response, *args, **kwargs):
        try:
            return super().finalize_response(request, response, *args, **kwargs)
        finally:
            token = getattr(self, '_audit_actor_token', None)
            if token is not None:
                _current_actor.reset(token)
                self._audit_actor_token = None


class AuditActorMiddleware:
    """Make the authenticated request user available to model-save audit signals."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        token = _current_actor.set(getattr(request, 'user', None))
        try:
            return self.get_response(request)
        finally:
            _current_actor.reset(token)
