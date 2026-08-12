import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent

SECRET_KEY = os.environ.get("SECRET_KEY", "dev-only-change-me")
DEBUG = os.environ.get("DEBUG", "true").lower() in {"1", "true", "yes", "on"}
ALLOWED_HOSTS = [
    host.strip()
    for host in os.environ.get("ALLOWED_HOSTS", "localhost,127.0.0.1,[::1]").split(",")
    if host.strip()
]

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "core",
    "catalog",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.locale.LocaleMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "config.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
                "core.context_processors.site_settings",
            ],
        },
    }
]

WSGI_APPLICATION = "config.wsgi.application"
ASGI_APPLICATION = "config.asgi.application"

DB_PATH = Path(os.environ.get("SQLITE_PATH", BASE_DIR / "data" / "db.sqlite3"))
DB_PATH.parent.mkdir(parents=True, exist_ok=True)
DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": DB_PATH,
        "OPTIONS": {"timeout": 20},
    }
}

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

LANGUAGE_CODE = "es-es"
TIME_ZONE = os.environ.get("TIME_ZONE", "Europe/Madrid")
USE_I18N = True
USE_TZ = True

CSRF_TRUSTED_ORIGINS = [
    origin.strip()
    for origin in os.environ.get("CSRF_TRUSTED_ORIGINS", "").split(",")
    if origin.strip()
]
SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")

STATIC_URL = "/static/"
STATIC_ROOT = BASE_DIR / "staticfiles"
STATICFILES_DIRS = [BASE_DIR / "static"]
STORAGES = {
    "default": {"BACKEND": "django.core.files.storage.FileSystemStorage"},
    "staticfiles": {"BACKEND": "whitenoise.storage.CompressedManifestStaticFilesStorage"},
}

MEDIA_URL = "/media/"
MEDIA_ROOT = Path(os.environ.get("MEDIA_ROOT", BASE_DIR / "media"))

MOVIE_METADATA_PROVIDER = os.environ.get("MOVIE_METADATA_PROVIDER", "tmdb")
MOVIE_METADATA_AUTO_FETCH = os.environ.get("MOVIE_METADATA_AUTO_FETCH", "true").lower() in {"1", "true", "yes", "on"}
MOVIE_METADATA_FETCH_IMAGES = os.environ.get("MOVIE_METADATA_FETCH_IMAGES", "true").lower() in {"1", "true", "yes", "on"}
MOVIE_METADATA_IMAGE_TIMEOUT_SECONDS = os.environ.get("MOVIE_METADATA_IMAGE_TIMEOUT_SECONDS", "8")
MOVIE_METADATA_IMAGE_MAX_BYTES = int(os.environ.get("MOVIE_METADATA_IMAGE_MAX_BYTES", str(15 * 1024 * 1024)))
TMDB_API_TOKEN = os.environ.get("TMDB_API_TOKEN", "")
TMDB_LANGUAGE = os.environ.get("TMDB_LANGUAGE", "es-ES")
TMDB_FALLBACK_LANGUAGE = os.environ.get("TMDB_FALLBACK_LANGUAGE", "en-US")
TMDB_TIMEOUT_SECONDS = os.environ.get("TMDB_TIMEOUT_SECONDS", "8")
TMDB_MAX_CAST_MEMBERS = os.environ.get("TMDB_MAX_CAST_MEMBERS", "12")
TMDB_IMAGE_BASE_URL = os.environ.get("TMDB_IMAGE_BASE_URL", "https://image.tmdb.org/t/p")
TMDB_POSTER_PREVIEW_SIZE = os.environ.get("TMDB_POSTER_PREVIEW_SIZE", "w342")
TMDB_POSTER_SIZE = os.environ.get("TMDB_POSTER_SIZE", "w780")
TMDB_BACKDROP_SIZE = os.environ.get("TMDB_BACKDROP_SIZE", "w1280")

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"
