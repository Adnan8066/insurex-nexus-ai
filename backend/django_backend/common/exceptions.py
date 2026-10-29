from rest_framework.views import exception_handler
from rest_framework.response import Response
from rest_framework import status
from django.conf import settings
import logging

from common.middleware import get_request_id

logger = logging.getLogger(__name__)

def custom_exception_handler(exc, context):
    response = exception_handler(exc, context)
    
    if response is not None:
        custom_response = {
            'success': False,
            'error': {
                'code': response.status_code,
                'message': 'An error occurred',
                'details': response.data,
                'request_id': get_request_id(),
            }
        }
        
        if isinstance(response.data, dict):
            if 'detail' in response.data:
                custom_response['error']['message'] = str(response.data['detail'])
            elif 'non_field_errors' in response.data:
                custom_response['error']['message'] = str(response.data['non_field_errors'][0])
            elif response.data:
                # Field validation errors: surface the first one as "field: message".
                field, errors = next(iter(response.data.items()))
                first = errors[0] if isinstance(errors, (list, tuple)) and errors else errors
                custom_response['error']['message'] = f'{field}: {first}'
        elif isinstance(response.data, list) and response.data:
            custom_response['error']['message'] = str(response.data[0])

        # Top-level human-readable string for clients that read `data.detail`.
        custom_response['detail'] = custom_response['error']['message']
        response.data = custom_response
    
    else:
        view = context.get('view')
        logger.exception(
            'Unhandled exception in %s (request_id=%s): %s',
            view.__class__.__name__ if view else 'unknown view', get_request_id(), exc,
        )
        response = Response({
            'success': False,
            'detail': 'Internal server error',
            'error': {
                'code': 500,
                'message': 'Internal server error',
                'details': str(exc) if settings.DEBUG else 'An unexpected error occurred',
                'request_id': get_request_id(),
            }
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    return response