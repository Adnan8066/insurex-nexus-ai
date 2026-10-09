from rest_framework.views import exception_handler
from rest_framework.response import Response
from rest_framework import status
from django.conf import settings
import logging

logger = logging.getLogger(__name__)

def custom_exception_handler(exc, context):
    response = exception_handler(exc, context)
    
    if response is not None:
        custom_response = {
            'success': False,
            'error': {
                'code': response.status_code,
                'message': 'An error occurred',
                'details': response.data
            }
        }
        
        if isinstance(response.data, dict):
            if 'detail' in response.data:
                custom_response['error']['message'] = str(response.data['detail'])
            elif 'non_field_errors' in response.data:
                custom_response['error']['message'] = str(response.data['non_field_errors'][0])
        
        response.data = custom_response
    
    else:
        logger.exception(f"Unhandled exception: {exc}")
        response = Response({
            'success': False,
            'error': {
                'code': 500,
                'message': 'Internal server error',
                'details': str(exc) if settings.DEBUG else 'An unexpected error occurred'
            }
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    return response