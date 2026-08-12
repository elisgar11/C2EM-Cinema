import re
from dataclasses import dataclass

from django.conf import settings
from django.db import IntegrityError, transaction
from django.utils import timezone

from .models import CastMember, MovieExternalId
from .providers import MovieMetadataProvider, ProviderError, TmdbMovieMetadataProvider


@dataclass(frozen=True)
class MetadataSyncResult:
    provider: str
    external_id: str
    fields_updated: tuple[str, ...]
    cast_updated: bool
    used_existing_identity: bool


PROVIDERS = {
    "tmdb": TmdbMovieMetadataProvider,
}


def get_movie_metadata_provider(name: str | None = None) -> MovieMetadataProvider:
    provider_name = (name or getattr(settings, "MOVIE_METADATA_PROVIDER", "tmdb")).strip().lower()
    provider_cls = PROVIDERS.get(provider_name)
    if provider_cls is None:
        raise ProviderError(f"Proveedor de metadatos no soportado: {provider_name}")
    return provider_cls()


def _split_title_year(title: str) -> tuple[str, int | None]:
    match = re.match(r"^(?P<title>.+?)\s*\((?P<year>\d{4})\)\s*$", title.strip())
    if not match:
        return title.strip(), None
    return match.group("title").strip(), int(match.group("year"))


def _normalize_title(value: str) -> str:
    return " ".join(value.casefold().replace(":", " ").replace("-", " ").split())


def _choose_search_result(title: str, results):
    if not results:
        return None
    normalized = _normalize_title(title)
    for result in results:
        if _normalize_title(result.title) == normalized:
            return result
    return results[0]


def sync_movie_metadata(movie, *, replace: bool = False, provider: MovieMetadataProvider | None = None) -> MetadataSyncResult:
    """Synchronize a movie from a remote provider without overwriting manual edits by default."""

    provider = provider or get_movie_metadata_provider()
    if not provider.is_configured():
        raise ProviderError(f"El proveedor {provider.name} no está configurado.")

    identity = MovieExternalId.objects.filter(movie=movie, provider=provider.name).first()
    used_existing_identity = identity is not None

    if identity is None:
        query_title, year = _split_title_year(movie.title)
        candidate = _choose_search_result(query_title, provider.search(query_title, year=year))
        if candidate is None:
            raise ProviderError(f"No se encontraron metadatos para «{movie.title}».")
        external_id = candidate.external_id
    else:
        external_id = identity.external_id

    metadata = provider.fetch(external_id)
    fields_updated = []

    try:
        with transaction.atomic():
            identity, _ = MovieExternalId.objects.update_or_create(
                movie=movie,
                provider=provider.name,
                defaults={
                    "external_id": metadata.external_id,
                    "last_synced_at": timezone.now(),
                },
            )

            if metadata.overview and (replace or not movie.description.strip()):
                movie.description = metadata.overview
                fields_updated.append("description")

            if metadata.runtime_minutes and (replace or not movie.duration_minutes):
                movie.duration_minutes = metadata.runtime_minutes
                fields_updated.append("duration_minutes")

            if metadata.trailer_url and (replace or not movie.trailer_url.strip()):
                movie.trailer_url = metadata.trailer_url
                fields_updated.append("trailer_url")

            if fields_updated:
                movie.save(update_fields=[*fields_updated, "updated_at"])

            has_cast = movie.cast_members.exists()
            cast_updated = bool(metadata.cast) and (replace or not has_cast)
            if cast_updated:
                if replace:
                    movie.cast_members.all().delete()
                CastMember.objects.bulk_create(
                    [
                        CastMember(
                            movie=movie,
                            name=credit.name,
                            character=credit.character,
                            sort_order=credit.order,
                        )
                        for credit in metadata.cast
                    ],
                    ignore_conflicts=True,
                )
    except IntegrityError as exc:
        raise ProviderError(
            f"El identificador {provider.name}:{metadata.external_id} ya está asociado a otra película."
        ) from exc

    return MetadataSyncResult(
        provider=provider.name,
        external_id=identity.external_id,
        fields_updated=tuple(fields_updated),
        cast_updated=cast_updated,
        used_existing_identity=used_existing_identity,
    )
