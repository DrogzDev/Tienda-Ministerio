from pathlib import Path
import os
from datetime import timedelta
from dotenv import load_dotenv

JWT_ACCESS_COOKIE = (
    "inventory_access"
)

JWT_REFRESH_COOKIE = (
    "inventory_refresh"
)


JWT_COOKIE_HTTPONLY = True

JWT_COOKIE_SAMESITE = "Lax"

# ============================================================
# BASE
# ============================================================

BASE_DIR = Path(__file__).resolve().parent.parent

load_dotenv(BASE_DIR / ".env")


# ============================================================
# SEGURIDAD
# ============================================================

SECRET_KEY = os.getenv(
    "SECRET_KEY",
    "django-insecure-development-key-change-this"
)

DEBUG = os.getenv("DEBUG", "True").lower() == "true"

ALLOWED_HOSTS = [
    "127.0.0.1",
    "localhost",
]


# ============================================================
# APPS
# ============================================================

INSTALLED_APPS = [
    # Django
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",

    # Terceros
    "rest_framework",
    "corsheaders",
    "django_filters",

    # Propias
    "inventory",
    "accounts",
    "documents",
]


# ============================================================
# MIDDLEWARE
# ============================================================

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",

    "corsheaders.middleware.CorsMiddleware",

    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",

    "django.contrib.auth.middleware.AuthenticationMiddleware",

    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]


ROOT_URLCONF = "backend.urls"


# ============================================================
# TEMPLATES
# ============================================================

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]


WSGI_APPLICATION = "backend.wsgi.application"


# ============================================================
# DATABASE
# ============================================================

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": BASE_DIR / "db.sqlite3",
    }
}


# ============================================================
# PASSWORDS
# ============================================================

AUTH_PASSWORD_VALIDATORS = [
    {
        "NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.MinimumLengthValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.CommonPasswordValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.NumericPasswordValidator",
    },
]


# ============================================================
# IDIOMA / HORA
# ============================================================

LANGUAGE_CODE = "es-ve"

TIME_ZONE = "America/Caracas"

USE_I18N = True

USE_TZ = True


# ============================================================
# STATIC
# ============================================================

STATIC_URL = "static/"


# ============================================================
# MEDIA
# ============================================================

MEDIA_URL = "/media/"
MEDIA_ROOT = BASE_DIR / "media"

# ============================================================
# CORS - ANGULAR LOCAL
# ============================================================

CORS_ALLOWED_ORIGINS = [
    "http://localhost:4200",
    "http://127.0.0.1:4200",
]

CSRF_TRUSTED_ORIGINS = [
    "http://localhost:4200",
    "http://127.0.0.1:4200",
]

CORS_ALLOW_CREDENTIALS = True

# ============================================================
# JWT - COOKIES HTTPONLY
# ============================================================

JWT_ACCESS_COOKIE = (
    "inventory_access"
)

JWT_REFRESH_COOKIE = (
    "inventory_refresh"
)

# En desarrollo estamos usando:
# http://localhost:4200
#
# Por eso debe ser False.
#
# En producción con HTTPS / Cloudflare
# lo cambiaremos a True.
JWT_COOKIE_SECURE = False

JWT_COOKIE_HTTPONLY = True

JWT_COOKIE_SAMESITE = "Lax"


# ============================================================
# CSRF
# ============================================================

# Angular necesita poder leer csrftoken
# para enviarlo como X-CSRFToken.
CSRF_COOKIE_HTTPONLY = False

# Desarrollo HTTP
CSRF_COOKIE_SECURE = False

CSRF_COOKIE_SAMESITE = "Lax"



####################################
# DJANGO REST FRAMEWORK
####################################

REST_FRAMEWORK = {

    "DEFAULT_AUTHENTICATION_CLASSES": (
        "accounts.authentication.CookieJWTAuthentication",
    ),

    "DEFAULT_PERMISSION_CLASSES": (
        "rest_framework.permissions.IsAuthenticated",
    ),
}

# ============================================================
# PRIMARY KEY
# ============================================================

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"