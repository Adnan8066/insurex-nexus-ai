"""Request correlation IDs.

Every request gets an ID (taken from a well-formed incoming ``X-Request-ID``
header, otherwise generated). It is returned in the ``X-Request-ID`` response
header, attached to log records as ``request_id`` and included in API error
bodies, so a user-reported error can be matched to the server log line.
"""
import contextvars
import logging
import re
import uuid

_request_id = contextvars.ContextVar('request_id', default='-')
_VALID_ID = re.compile(r'^[A-Za-z0-9._-]{1,64}$')


def get_request_id():
    return _request_id.get()


class RequestIDMiddleware:
    header = 'HTTP_X_REQUEST_ID'

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        incoming = request.META.get(self.header, '')
        request_id = incoming if _VALID_ID.match(incoming) else uuid.uuid4().hex
        request.request_id = request_id
        token = _request_id.set(request_id)
        try:
            response = self.get_response(request)
        finally:
            _request_id.reset(token)
        response['X-Request-ID'] = request_id
        return response


class RequestIDLogFilter(logging.Filter):
    def filter(self, record):
        if not hasattr(record, 'request_id'):
            # django.request logs 4xx/5xx after the middleware chain has returned,
            # but attaches the request to the record.
            request = getattr(record, 'request', None)
            record.request_id = getattr(request, 'request_id', None) or get_request_id()
        return True
