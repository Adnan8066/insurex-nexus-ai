"""Helpers that turn malformed client input into 400 responses instead of 500s."""
from rest_framework.exceptions import ValidationError


def parse_int(value, field, minimum=None, maximum=None, default=None):
    """Parse an integer request value, raising a DRF ValidationError (HTTP 400)."""
    if value in (None, ''):
        if default is not None:
            return default
        raise ValidationError({field: 'This field is required.'})
    try:
        number = int(str(value).strip())
    except (TypeError, ValueError):
        raise ValidationError({field: 'A valid integer is required.'})
    if minimum is not None and number < minimum:
        raise ValidationError({field: f'Must be at least {minimum}.'})
    if maximum is not None and number > maximum:
        raise ValidationError({field: f'Must be at most {maximum}.'})
    return number


from rest_framework.exceptions import APIException  # noqa: E402


class Conflict(APIException):
    status_code = 409
    default_detail = 'The request conflicts with the current state of the resource.'
    default_code = 'conflict'
