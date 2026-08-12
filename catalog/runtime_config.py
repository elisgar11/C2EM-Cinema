from django.conf import settings
from django.db import OperationalError, ProgrammingError


_PROVIDER_CHOICES = {"auto", "tmdb", "wikidata"}


def _site_metadata_values() -> dict:
    """Read persisted admin settings without creating the singleton as a side effect."""
    try:
        from core.models import SiteSettings

        return (
            SiteSettings.objects.filter(pk=1)
            .values("metadata_provider", "tmdb_api_token")
            .first()
            or {}
        )
    except (OperationalError, ProgrammingError):
        # Allows checks/migrations to import provider code before the table/columns exist.
        return {}


def metadata_provider_preference() -> str:
    values = _site_metadata_values()
    configured = str(values.get("metadata_provider") or "auto").strip().lower()
    if configured not in _PROVIDER_CHOICES:
        configured = "auto"
    if configured != "auto":
        return configured
    return str(getattr(settings, "MOVIE_METADATA_PROVIDER", "tmdb")).strip().lower() or "tmdb"


def tmdb_api_token() -> str:
    """Admin token overrides the environment token and takes effect immediately."""
    values = _site_metadata_values()
    admin_token = str(values.get("tmdb_api_token") or "").strip()
    if admin_token:
        return admin_token
    return str(getattr(settings, "TMDB_API_TOKEN", "")).strip()


def tmdb_token_source() -> str:
    values = _site_metadata_values()
    if str(values.get("tmdb_api_token") or "").strip():
        return "admin"
    if str(getattr(settings, "TMDB_API_TOKEN", "")).strip():
        return "environment"
    return "none"
