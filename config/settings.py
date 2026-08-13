import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent

IS_VERCEL = bool(
    os.environ.get("VERCEL_ENV")
    or os.environ.get("VERCEL")
    or os.environ.get("VERCEL_URL")
)

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
if not IS_VERCEL:
    ASGI_APPLICATION = "config.asgi.application"

database_url = os.environ.get("DATABASE_URL", "").strip()
if database_url:
    import dj_database_url

    DATABASES = {
        "default": dj_database_url.config(
            default=database_url,
            conn_max_age=600,
            conn_health_checks=True,
        )
    }
elif IS_VERCEL:
    vercel_db_path = Path("/tmp/c2em-db.sqlite3")
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.sqlite3",
            "NAME": vercel_db_path,
            "OPTIONS": {"timeout": 20},
        }
    }
else:
    db_path = Path(os.environ.get("SQLITE_PATH", BASE_DIR / "data" / "db.sqlite3"))
    db_path.parent.mkdir(parents=True, exist_ok=True)
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.sqlite3",
            "NAME": db_path,
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

if IS_VERCEL:
    if ".vercel.app" not in ALLOWED_HOSTS:
        ALLOWED_HOSTS.append(".vercel.app")
    for env_name in (
        "VERCEL_URL",
        "VERCEL_BRANCH_URL",
        "VERCEL_PROJECT_PRODUCTION_URL",
    ):
        host = os.environ.get(env_name, "").strip()
        if host and host not in ALLOWED_HOSTS:
            ALLOWED_HOSTS.append(host)
        origin = f"https://{host}"
        if host and origin not in CSRF_TRUSTED_ORIGINS:
            CSRF_TRUSTED_ORIGINS.append(origin)
    if "https://*.vercel.app" not in CSRF_TRUSTED_ORIGINS:
        CSRF_TRUSTED_ORIGINS.append("https://*.vercel.app")

SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")

STATIC_URL = "/static/"
STATIC_ROOT = BASE_DIR / "staticfiles"
STATICFILES_DIRS = [BASE_DIR / "static"]
STORAGES = {
    "default": {"BACKEND": "django.core.files.storage.FileSystemStorage"},
    "staticfiles": {"BACKEND": "whitenoise.storage.CompressedManifestStaticFilesStorage"},
}

MEDIA_URL = "/media/"
if IS_VERCEL:
    media_root = Path("/tmp/c2em-media")
    media_root.mkdir(parents=True, exist_ok=True)
    MEDIA_ROOT = media_root
else:
    MEDIA_ROOT = Path(os.environ.get("MEDIA_ROOT", BASE_DIR / "media"))

MOVIE_METADATA_PROVIDER = os.environ.get("MOVIE_METADATA_PROVIDER", "tmdb")
MOVIE_METADATA_FALLBACK_PROVIDER = os.environ.get("MOVIE_METADATA_FALLBACK_PROVIDER", "wikidata")
MOVIE_METADATA_AUTO_FETCH = os.environ.get("MOVIE_METADATA_AUTO_FETCH", "true").lower() in {"1", "true", "yes", "on"}
MOVIE_METADATA_FETCH_IMAGES = os.environ.get(
    "MOVIE_METADATA_FETCH_IMAGES",
    "false" if IS_VERCEL else "true",
).lower() in {"1", "true", "yes", "on"}
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
WIKIDATA_ENABLED = os.environ.get("WIKIDATA_ENABLED", "true").lower() in {"1", "true", "yes", "on"}
WIKIDATA_LANGUAGE = os.environ.get("WIKIDATA_LANGUAGE", "es")
WIKIDATA_FALLBACK_LANGUAGE = os.environ.get("WIKIDATA_FALLBACK_LANGUAGE", "en")
WIKIDATA_TIMEOUT_SECONDS = os.environ.get("WIKIDATA_TIMEOUT_SECONDS", "8")
WIKIDATA_MAX_CAST_MEMBERS = os.environ.get("WIKIDATA_MAX_CAST_MEMBERS", "12")
WIKIDATA_POSTER_PREVIEW_WIDTH = os.environ.get("WIKIDATA_POSTER_PREVIEW_WIDTH", "342")
WIKIDATA_POSTER_WIDTH = os.environ.get("WIKIDATA_POSTER_WIDTH", "780")
WIKIDATA_USER_AGENT = os.environ.get("WIKIDATA_USER_AGENT", "C2EM-Cinema/1.0")

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"
