from django.conf import settings

from .models import SiteSettings


def site_settings(request):
    return {
        "site_settings": SiteSettings.load(),
        "movie_metadata_provider": getattr(settings, "MOVIE_METADATA_PROVIDER", "").strip().lower(),
    }
