import os
import sys
from pathlib import Path
from datetime import timedelta
from dotenv import load_dotenv
from django.core.exceptions import ImproperlyConfigured

# Load environment variables from .env file
load_dotenv()

BASE_DIR = Path(__file__).resolve().parent.parent

DEBUG = os.environ.get('DEBUG', 'True').lower() == 'true'
SECRET_KEY = os.environ.get('SECRET_KEY')
if not SECRET_KEY:
    if not DEBUG:
        raise ImproperlyConfigured('SECRET_KEY must be set when DEBUG=False.')
    SECRET_KEY = 'django-insecure-local-development-only-key'

ALLOWED_HOSTS = [
    host.strip()
    for host in os.environ.get('ALLOWED_HOSTS', 'localhost,127.0.0.1,0.0.0.0').split(',')
    if host.strip()
]

SECURE_SSL_REDIRECT = os.environ.get('SECURE_SSL_REDIRECT', str(not DEBUG)).lower() == 'true'
SECURE_HSTS_SECONDS = int(os.environ.get('SECURE_HSTS_SECONDS', '0' if DEBUG else '31536000'))
SECURE_HSTS_INCLUDE_SUBDOMAINS = os.environ.get(
    'SECURE_HSTS_INCLUDE_SUBDOMAINS', str(not DEBUG)
).lower() == 'true'
SECURE_HSTS_PRELOAD = os.environ.get('SECURE_HSTS_PRELOAD', str(not DEBUG)).lower() == 'true'
SESSION_COOKIE_SECURE = os.environ.get('SESSION_COOKIE_SECURE', str(not DEBUG)).lower() == 'true'
CSRF_COOKIE_SECURE = os.environ.get('CSRF_COOKIE_SECURE', str(not DEBUG)).lower() == 'true'
SECURE_CONTENT_TYPE_NOSNIFF = True
X_FRAME_OPTIONS = 'DENY'
SECURE_REFERRER_POLICY = 'same-origin'
if os.environ.get('USE_X_FORWARDED_PROTO', 'False').lower() == 'true':
    SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    
    # Third party
    'rest_framework',
    'rest_framework_simplejwt',
    'rest_framework_simplejwt.token_blacklist',
    'django_filters',
    'corsheaders',
    'drf_spectacular',
    
    # Local apps
    'apps.accounts',
    'apps.customers',
    'apps.policies',
    'apps.vehicles',
    'apps.claims',
    'apps.assessments',
    'apps.investigations',
    'apps.repair_shops',
    'apps.notifications',
    'apps.analytics',
    'apps.settlements',
    'apps.auditlog.apps.AuditlogConfig',
]

MIDDLEWARE = [
    'common.middleware.RequestIDMiddleware',
    'corsheaders.middleware.CorsMiddleware',
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'apps.auditlog.context.AuditActorMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]
if not DEBUG:
    MIDDLEWARE.insert(3, 'whitenoise.middleware.WhiteNoiseMiddleware')

ROOT_URLCONF = 'config.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'config.wsgi.application'

# Database Configuration
# SQLite by default for local development. Hosted deployments can provide DATABASE_URL.
_database_url = os.environ.get('DATABASE_URL')
if _database_url:
    import dj_database_url
    DATABASES = {
        'default': dj_database_url.parse(
            _database_url,
            conn_max_age=600,
            ssl_require=not DEBUG,
        )
    }
else:
    _db_engine = os.environ.get('DATABASE_ENGINE', 'django.db.backends.sqlite3')
    if _db_engine in ['django.db.backends.postgresql', 'postgresql']:
        DATABASES = {
            'default': {
                'ENGINE': 'django.db.backends.postgresql',
                'NAME': os.environ.get('POSTGRES_DB', 'insurex'),
                'USER': os.environ.get('POSTGRES_USER', 'postgres'),
                'PASSWORD': os.environ.get('POSTGRES_PASSWORD', 'postgres'),
                'HOST': os.environ.get('POSTGRES_HOST', 'localhost'),
                'PORT': os.environ.get('POSTGRES_PORT', '5432'),
            }
        }
    else:
        DATABASES = {
            'default': {
                'ENGINE': 'django.db.backends.sqlite3',
                'NAME': BASE_DIR / 'db.sqlite3',
            }
        }

AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator'},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]

LANGUAGE_CODE = 'en-us'
TIME_ZONE = 'UTC'
USE_I18N = True
USE_TZ = True

# Motor premium tables used by apps/policies/services/rating.py.
# SPEC = figure from the product spec (IRDAI-style structure).
# PLACEHOLDER = not in the spec; must be replaced with approved insurer data
# before these quotes are used for real contracts.
POLICY_RATING_TABLES = {
    'rating_version': 'irdai-style-v1',
    # SPEC: third-party premium by engine capacity (cc), private car, 1 year.
    'tp_premium': {'under_1000': '2094', 'from_1000_to_1500': '3416', 'above_1500': '7897'},
    # SPEC: depreciation by vehicle age in years (age taken from the model year).
    'depreciation': {0: '0.05', 1: '0.15', 2: '0.20', 3: '0.30', 4: '0.40', 5: '0.50'},
    # PLACEHOLDER: depreciation above 5 years (SPEC says mutually assessed).
    'depreciation_max': '0.50',
    # SPEC: no-claim bonus by consecutive claim-free years, applied to the OD part only.
    'ncb': {0: '0', 1: '0.20', 2: '0.25', 3: '0.35', 4: '0.45', 5: '0.50'},
    # PLACEHOLDER: OD rate as a share of IDV, inside the SPEC range of about 2.2%–3.2%.
    'od_rate': {'A': '0.030', 'B': '0.025'},
    # PLACEHOLDER: registration cities treated as Zone A (metro). Other cities are Zone B.
    'zone_a_cities': ['mumbai', 'delhi', 'new delhi', 'bengaluru', 'bangalore', 'chennai',
                      'kolkata', 'hyderabad', 'pune', 'ahmedabad'],
    # PLACEHOLDER: add-on prices. 'percent' is a share of IDV, 'fixed' is rupees per year.
    'addons': {
        'zero_depreciation': {'percent': '0.005'},
        'engine_protect': {'percent': '0.003'},
        'roadside_assistance': {'fixed': '600'},
        'consumables': {'fixed': '400'},
        'key_protect': {'fixed': '300'},
    },
    # PLACEHOLDER: compulsory personal accident cover for the owner-driver (SPEC: about 300–400 a year).
    'cpa_premium': '350',
    # SPEC: GST on motor premiums.
    'gst_rate': '0.18',
}
CLAIM_ANNUAL_DEPRECIATION_RATE = os.environ.get('CLAIM_ANNUAL_DEPRECIATION_RATE', '0.05')
CLAIM_MAX_DEPRECIATION_RATE = os.environ.get('CLAIM_MAX_DEPRECIATION_RATE', '0.80')

STATIC_URL = '/static/'
STATIC_ROOT = os.environ.get('STATIC_ROOT', BASE_DIR / 'staticfiles')
if DEBUG:
    STORAGES = {
        'default': {'BACKEND': 'django.core.files.storage.FileSystemStorage'},
        'staticfiles': {'BACKEND': 'django.contrib.staticfiles.storage.StaticFilesStorage'},
    }
else:
    STORAGES = {
        'default': {'BACKEND': 'django.core.files.storage.FileSystemStorage'},
        'staticfiles': {'BACKEND': 'whitenoise.storage.CompressedManifestStaticFilesStorage'},
    }

# Uploads (claim photos, documents, vehicle images). Local disk is for development only:
# hosted filesystems such as Render's free tier lose files on restart. Set
# USE_S3_STORAGE=true to store uploads in an S3-compatible bucket (AWS S3, Cloudflare R2,
# or Supabase Storage) through django-storages.
USE_S3_STORAGE = os.environ.get('USE_S3_STORAGE', 'False').lower() == 'true'
if USE_S3_STORAGE:
    STORAGES['default'] = {'BACKEND': 'storages.backends.s3.S3Storage'}
    AWS_STORAGE_BUCKET_NAME = os.environ['AWS_STORAGE_BUCKET_NAME']  # required when enabled
    AWS_ACCESS_KEY_ID = os.environ.get('AWS_ACCESS_KEY_ID', '')
    AWS_SECRET_ACCESS_KEY = os.environ.get('AWS_SECRET_ACCESS_KEY', '')
    AWS_S3_ENDPOINT_URL = os.environ.get('AWS_S3_ENDPOINT_URL') or None
    AWS_S3_REGION_NAME = os.environ.get('AWS_S3_REGION_NAME') or None
    AWS_S3_CUSTOM_DOMAIN = os.environ.get('AWS_S3_CUSTOM_DOMAIN') or None
    AWS_S3_FILE_OVERWRITE = False
    AWS_DEFAULT_ACL = None
    AWS_QUERYSTRING_AUTH = True

MEDIA_URL = '/media/'
MEDIA_ROOT = os.environ.get('MEDIA_ROOT', BASE_DIR / 'media')

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

AUTH_USER_MODEL = 'accounts.User'

REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': (
        'rest_framework_simplejwt.authentication.JWTAuthentication',
    ),
    'DEFAULT_PERMISSION_CLASSES': [
        'rest_framework.permissions.IsAuthenticated',
    ],
    'DEFAULT_FILTER_BACKENDS': [
        'django_filters.rest_framework.DjangoFilterBackend',
        'rest_framework.filters.SearchFilter',
        'rest_framework.filters.OrderingFilter',
    ],
    'DEFAULT_PAGINATION_CLASS': 'rest_framework.pagination.PageNumberPagination',
    'PAGE_SIZE': 20,
    'DEFAULT_SCHEMA_CLASS': 'drf_spectacular.openapi.AutoSchema',
    'EXCEPTION_HANDLER': 'common.exceptions.custom_exception_handler',
    # Only views that opt in with a throttle_scope are throttled (login, password
    # reset, registration, public callback form).
    'DEFAULT_THROTTLE_RATES': {
        'login': os.environ.get('THROTTLE_LOGIN_RATE', '10/min'),
        'password_reset': os.environ.get('THROTTLE_PASSWORD_RESET_RATE', '5/hour'),
        'login_code': os.environ.get('THROTTLE_LOGIN_CODE_RATE', '10/hour'),
        'register': os.environ.get('THROTTLE_REGISTER_RATE', '20/hour'),
        'public_form': os.environ.get('THROTTLE_PUBLIC_FORM_RATE', '20/hour'),
    },
}

# Maximum size of a single uploaded document/photo (see common/uploads.py).
MAX_UPLOAD_BYTES = int(os.environ.get('MAX_UPLOAD_BYTES', 25 * 1024 * 1024))

SIMPLE_JWT = {
    'ACCESS_TOKEN_LIFETIME': timedelta(minutes=int(os.environ.get('JWT_ACCESS_TOKEN_LIFETIME_MINUTES', 60))),
    'REFRESH_TOKEN_LIFETIME': timedelta(days=int(os.environ.get('JWT_REFRESH_TOKEN_LIFETIME_DAYS', 7))),
    'ROTATE_REFRESH_TOKENS': os.environ.get('JWT_ROTATE_REFRESH_TOKENS', 'True').lower() == 'true',
    'BLACKLIST_AFTER_ROTATION': os.environ.get('JWT_BLACKLIST_AFTER_ROTATION', 'True').lower() == 'true',
    'UPDATE_LAST_LOGIN': True,
    'ALGORITHM': 'HS256',
    'SIGNING_KEY': SECRET_KEY,
    'VERIFYING_KEY': None,
    'AUDIENCE': None,
    'ISSUER': None,
    'JWK_URL': None,
    'LEEWAY': 0,
    'AUTH_HEADER_TYPES': ('Bearer',),
    'AUTH_HEADER_NAME': 'HTTP_AUTHORIZATION',
    'USER_ID_FIELD': 'id',
    'USER_ID_CLAIM': 'user_id',
    'USER_AUTHENTICATION_RULE': 'rest_framework_simplejwt.authentication.default_user_authentication_rule',
    'AUTH_TOKEN_CLASSES': ('rest_framework_simplejwt.tokens.AccessToken',),
    'TOKEN_TYPE_CLAIM': 'token_type',
    'TOKEN_USER_CLASS': 'rest_framework_simplejwt.models.TokenUser',
    'JTI_CLAIM': 'jti',
    'SLIDING_TOKEN_REFRESH_EXP_CLAIM': 'refresh_exp',
    'SLIDING_TOKEN_LIFETIME': timedelta(minutes=5),
    'SLIDING_TOKEN_REFRESH_LIFETIME': timedelta(days=1),
}

CORS_ALLOWED_ORIGINS = [
    origin.strip().rstrip('/')
    for origin in os.environ.get(
        'CORS_ALLOWED_ORIGINS',
        'http://localhost:5173,http://127.0.0.1:5173,http://localhost:3000,http://127.0.0.1:3000',
    ).split(',')
    if origin.strip()
]
CSRF_TRUSTED_ORIGINS = [
    origin.strip()
    for origin in os.environ.get('CSRF_TRUSTED_ORIGINS', '').split(',')
    if origin.strip()
]
CORS_ALLOW_CREDENTIALS = os.environ.get('CORS_ALLOW_CREDENTIALS', 'True').lower() == 'true'
CORS_ALLOW_ALL_ORIGINS = DEBUG

SPECTACULAR_SETTINGS = {
    'TITLE': 'InsureX Nexus AI API',
    'DESCRIPTION': 'Intelligent Insurance Claim and Decision Management Platform API',
    'VERSION': '1.0.0',
    'SERVE_INCLUDE_SCHEMA': False,
    'COMPONENT_SPLIT_REQUEST': True,
    'ENUM_NAME_OVERRIDES': {
        'ClaimStatusEnum': 'apps.claims.models.ClaimStatus.choices',
        'ClaimPriorityEnum': 'apps.claims.models.ClaimPriority.choices',
        'PolicyStatusEnum': 'apps.policies.models.PolicyStatus.choices',
        'VehicleStatusEnum': 'apps.vehicles.models.VehicleStatus.choices',
        'AssessmentStatusEnum': 'apps.assessments.models.AssessmentStatus.choices',
        'InvestigationStatusEnum': 'apps.investigations.models.InvestigationStatus.choices',
        'NotificationPriorityEnum': 'apps.notifications.models.NotificationPriority.choices',
        'AgentOutputStatusEnum': 'apps.assessments.models.AGENT_OUTPUT_STATUS_CHOICES',
        'FraudAlertStatusEnum': 'apps.investigations.models.FRAUD_ALERT_STATUS_CHOICES',
    },
    'SCHEMA_PATH_PREFIX': '/api/v1/',
    'TAGS': [
        {'name': 'Authentication', 'description': 'User authentication and authorization'},
        {'name': 'Customers', 'description': 'Customer management'},
        {'name': 'Policies', 'description': 'Insurance policy management'},
        {'name': 'Vehicles', 'description': 'Vehicle management'},
        {'name': 'Claims', 'description': 'Insurance claim management'},
        {'name': 'Assessments', 'description': 'AI claim assessments'},
        {'name': 'Investigations', 'description': 'SIU investigations'},
        {'name': 'Notifications', 'description': 'User notifications'},
        {'name': 'Analytics', 'description': 'Dashboard analytics'},
    ],
}

EMAIL_BACKEND = os.environ.get('EMAIL_BACKEND', 'django.core.mail.backends.console.EmailBackend')
EMAIL_HOST = os.environ.get('EMAIL_HOST', 'smtp.gmail.com')
EMAIL_PORT = int(os.environ.get('EMAIL_PORT', 587))
EMAIL_USE_TLS = os.environ.get('EMAIL_USE_TLS', 'True').lower() == 'true'
EMAIL_HOST_USER = os.environ.get('EMAIL_HOST_USER', '')
EMAIL_HOST_PASSWORD = os.environ.get('EMAIL_HOST_PASSWORD', '')
DEFAULT_FROM_EMAIL = os.environ.get('DEFAULT_FROM_EMAIL', 'InsureX Nexus AI <noreply@insurex.ai>')

FRONTEND_URL = os.environ.get('FRONTEND_URL', 'http://localhost:3000')

# Customer sign-in by emailed one-time code (apps/accounts/login_codes.py).
CUSTOMER_LOGIN_CODE_TTL_MINUTES = int(os.environ.get('CUSTOMER_LOGIN_CODE_TTL_MINUTES', 10))
CUSTOMER_LOGIN_CODE_MAX_ATTEMPTS = int(os.environ.get('CUSTOMER_LOGIN_CODE_MAX_ATTEMPTS', 5))


CELERY_BROKER_URL = os.environ.get('CELERY_BROKER_URL', 'redis://localhost:6379/0')
CELERY_RESULT_BACKEND = os.environ.get('CELERY_RESULT_BACKEND', 'redis://localhost:6379/0')
CELERY_TASK_TRACK_STARTED = True
CELERY_TASK_TIME_LIMIT = 30 * 60
# Run tasks in-process (no broker needed) when asked, and always under `manage.py test` or pytest.
CELERY_TASK_ALWAYS_EAGER = (
    os.environ.get('CELERY_TASK_ALWAYS_EAGER', 'False').lower() == 'true'
    or sys.argv[1:2] == ['test']
    or 'pytest' in sys.modules
)
CELERY_TASK_EAGER_PROPAGATES = True
# Scheduled jobs for `celery -A config beat`. Intervals are in seconds.
CELERY_BEAT_SCHEDULE = {
    'check-policy-expirations': {
        'task': 'apps.policies.tasks.check_policy_expirations',
        'schedule': 24 * 60 * 60.0,
    },
    'send-renewal-reminders': {
        'task': 'apps.policies.tasks.send_renewal_reminders',
        'schedule': 24 * 60 * 60.0,
    },
}

LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'verbose': {
            'format': '{levelname} {asctime} [{request_id}] {module} {process:d} {thread:d} {message}',
            'style': '{',
        },
        'simple': {
            'format': '{levelname} {message}',
            'style': '{',
        },
    },
    'filters': {
        'request_id': {'()': 'common.middleware.RequestIDLogFilter'},
    },
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
            'formatter': 'verbose',
            'filters': ['request_id'],
        },
    },
    'root': {
        'handlers': ['console'],
        'level': os.environ.get('LOG_LEVEL', 'INFO'),
    },
    'loggers': {
        'django': {
            'handlers': ['console'],
            'level': os.environ.get('LOG_LEVEL', 'INFO'),
            'propagate': False,
        },
        'apps': {
            'handlers': ['console'],
            'level': os.environ.get('LOG_LEVEL', 'INFO'),
            'propagate': False,
        },
    },
}
