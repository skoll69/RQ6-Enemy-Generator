# Minimal Django settings for running tests and local development
# Self-contained to avoid dependency on a missing mythras_eg package.

from pathlib import Path
import os

# Ensure PyMySQL is used as MySQLdb driver to satisfy Django's mysql backend
try:
    import pymysql  # type: ignore
    pymysql.install_as_MySQLdb()
except Exception:
    # If PyMySQL is not available, Django will error when connecting; requirements include pymysql
    pass

BASE_DIR = Path(__file__).resolve().parent

SECRET_KEY = os.environ.get("SECRET_KEY", "dev-secret-key")
DEBUG = True
ALLOWED_HOSTS = ["*"]

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "taggit",
    "enemygen",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
]

ROOT_URLCONF = "enemygen.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [str(BASE_DIR / "templates")],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

WSGI_APPLICATION = os.environ.get("WSGI_APPLICATION", "wsgi.application")

# Load .env early so Django always picks up container MySQL settings
try:
    from dotenv import load_dotenv  # type: ignore
    load_dotenv(dotenv_path=str(BASE_DIR / '.env'))
except Exception:
    # python-dotenv may not be installed in all environments; it's optional.
    # If unavailable, environment variables must be exported by the shell.
    pass

# Mandatory MySQL configuration (SQLite disabled by requirement)
DB_NAME = os.environ.get("DB_NAME")
if not DB_NAME:
    raise RuntimeError(
        "DB_NAME is not set. SQLite is disabled for this project. "
        "Set DB_NAME and other DB_* variables in .env or environment."
    )


DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.mysql",
        "NAME": os.environ.get("DB_NAME", "mythras_eg"),
        "USER": os.environ.get("DB_USER", "mythras_eg"),
        "PASSWORD": os.environ["DB_PASSWORD"],
        "HOST": os.environ.get("DB_HOST", "127.0.0.1"),
        "PORT": os.environ.get("DB_PORT", "3308"),
        "OPTIONS": {
            "charset": "utf8mb4",
            "init_command": "SET sql_mode='STRICT_ALL_TABLES'",
            "connect_timeout": 5,
            "read_timeout": 5,
            "write_timeout": 5,
            "ssl": {},
        },
    }
}

LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "handlers": {
        "console": {"class": "logging.StreamHandler"},
    },
    "root": {
        "handlers": ["console"],
        "level": "DEBUG",
    },
    "loggers": {
        "django.db.backends": {
            "level": "DEBUG",
            "handlers": ["console"],
        },
    },
}

LANGUAGE_CODE = "en-us"
TIME_ZONE = os.environ.get("TIME_ZONE", "UTC")
USE_I18N = True
USE_L10N = True
USE_TZ = True

STATIC_URL = "/static/"
STATIC_ROOT = str(BASE_DIR / "static_root")

DEFAULT_AUTO_FIELD = "django.db.models.AutoField"

# Speed up tests by creating tables directly from models (no migrations for enemygen)
#MIGRATION_MODULES = {"enemygen": None}

# Optional: value used by enemygen.urls if present
WEB_ROOT = ""
