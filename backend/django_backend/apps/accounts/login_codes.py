"""Email one-time codes for customer sign-in.

A customer asks for a code with their email address and signs in by entering it. Codes are
6 digits, expire after CUSTOMER_LOGIN_CODE_TTL_MINUTES, allow CUSTOMER_LOGIN_CODE_MAX_ATTEMPTS
wrong guesses, and work once. Asking for a new code cancels any earlier unused one. Only an
HMAC of the code is stored, keyed with SECRET_KEY, so a database leak doesn't reveal live codes.
"""
import hashlib
import hmac
import logging
import secrets
from datetime import timedelta

from django.conf import settings
from django.core.mail import send_mail
from django.db import transaction
from django.utils import timezone

from .models import CustomerLoginCode, Role, User

logger = logging.getLogger(__name__)

CODE_DIGITS = 6


def ttl_minutes():
    return int(getattr(settings, 'CUSTOMER_LOGIN_CODE_TTL_MINUTES', 10))


def max_attempts():
    return int(getattr(settings, 'CUSTOMER_LOGIN_CODE_MAX_ATTEMPTS', 5))


def _hash(code):
    return hmac.new(settings.SECRET_KEY.encode(), code.encode(), hashlib.sha256).hexdigest()


def _customer(email):
    return User.objects.filter(
        email__iexact=(email or '').strip(), role=Role.CUSTOMER, is_active=True,
    ).first()


def issue_code(email):
    """Create and email a code if the email belongs to an active customer.

    Returns True when a code was sent. Callers must not reveal the result to the client,
    so the response can't be used to find out which emails have accounts.
    """
    user = _customer(email)
    if user is None:
        return False
    code = f"{secrets.randbelow(10 ** CODE_DIGITS):0{CODE_DIGITS}d}"
    now = timezone.now()
    with transaction.atomic():
        CustomerLoginCode.objects.filter(user=user, used_at__isnull=True).update(used_at=now)
        CustomerLoginCode.objects.create(
            user=user, code_hash=_hash(code), expires_at=now + timedelta(minutes=ttl_minutes()),
        )
    send_mail(
        subject='Your InsureX sign-in code',
        message=(
            f"Your InsureX sign-in code is {code}.\n\n"
            f"It expires in {ttl_minutes()} minutes and works once. "
            "If you didn't ask for it, you can ignore this email."
        ),
        from_email=settings.DEFAULT_FROM_EMAIL,
        recipient_list=[user.email],
        fail_silently=False,
    )
    return True


def verify_code(email, code):
    """Return the customer if `code` is their current, unexpired, unused code; otherwise None."""
    user = _customer(email)
    code = ''.join(ch for ch in str(code or '') if ch.isdigit())
    if user is None or len(code) != CODE_DIGITS:
        return None
    now = timezone.now()
    with transaction.atomic():
        login_code = (
            CustomerLoginCode.objects.select_for_update()
            .filter(user=user, used_at__isnull=True, expires_at__gt=now)
            .order_by('-created_at')
            .first()
        )
        if login_code is None or login_code.attempts >= max_attempts():
            return None
        if not hmac.compare_digest(login_code.code_hash, _hash(code)):
            login_code.attempts += 1
            fields = ['attempts']
            if login_code.attempts >= max_attempts():
                login_code.used_at = now  # too many wrong guesses: the code stops working
                fields.append('used_at')
            login_code.save(update_fields=fields)
            return None
        login_code.used_at = now
        login_code.save(update_fields=['used_at'])
    return user
