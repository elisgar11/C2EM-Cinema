from django.utils.text import slugify

from core.models import Movie

from .models import MovieExternalId
from .providers import MovieMetadataProvider, ProviderError
from .services import _apply_movie_metadata, get_movie_metadata_provider


def _unique_movie_slug(title: str, provider_name: str, external_id: str) -> str:
    base = slugify(title) or "pelicula"
    if not Movie.objects.filter(slug=base).exists():
        return base

    provider_suffix = slugify(provider_name) or "provider"
    external_suffix = slugify(str(external_id)) or "id"
    candidate = f"{base}-{provider_suffix}-{external_suffix}"
    if not Movie.objects.filter(slug=candidate).exists():
        return candidate

    counter = 2
    while Movie.objects.filter(slug=f"{candidate}-{counter}").exists():
        counter += 1
    return f"{candidate}-{counter}"


def create_movie_from_provider(
    external_id: str,
    *,
    provider: MovieMetadataProvider | None = None,
):
    provider = provider or get_movie_metadata_provider()
    if not provider.is_configured():
        raise ProviderError(f"El proveedor {provider.name} no está configurado.")

    external_id = str(external_id).strip()
    existing = MovieExternalId.objects.filter(provider=provider.name, external_id=external_id).select_related("movie").first()
    if existing is not None:
        raise ProviderError(
            f"{provider.name}:{external_id} ya está asociado a «{existing.movie.title}»."
        )

    metadata = provider.fetch(external_id)
    title = (metadata.title or f"Película {external_id}").strip()
    movie = Movie.objects.create(
        title=title,
        slug=_unique_movie_slug(title, provider.name, external_id),
        duration_minutes=0,
        enabled=True,
    )

    try:
        result = _apply_movie_metadata(
            movie,
            provider,
            metadata,
            replace=False,
            used_existing_identity=False,
        )
    except Exception:
        movie.delete()
        raise

    return movie, result
