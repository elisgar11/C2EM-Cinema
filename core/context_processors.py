from django.conf import settings

from catalog.providers import ProviderError
from catalog.services import get_movie_metadata_provider

from .models import SiteSettings


def site_settings(request):
    provider_name = getattr(settings, "MOVIE_METADATA_PROVIDER", "").strip().lower()
    try:
        provider_name = get_movie_metadata_provider().name
    except ProviderError:
        pass

    return {
        "site_settings": SiteSettings.load(),
        "movie_metadata_provider": provider_name,
    }
