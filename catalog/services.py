import mimetypes
import re
from dataclasses import dataclass
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import urlparse
from urllib.request import Request, urlopen

from django.conf import settings
from django.core.files.base import ContentFile
from django.db import IntegrityError, transaction
from django.utils import timezone

from .models import CastMember, MovieExternalId
from .providers import (
    MovieMetadataProvider,
    ProviderError,
    TmdbMovieMetadataProvider,
    WikidataMovieMetadataProvider,
)


@dataclass(frozen=True)
class MetadataSyncResult:
    provider: str
    external_id: str
    fields_updated: tuple[str, ...]
    cast_updated: bool
    used_existing_identity: bool
    artwork_updated: tuple[str, ...] = ()
    artwork_errors: tuple[str, ...] = ()


PROVIDERS = {
    "tmdb": TmdbMovieMetadataProvider,
    "wikidata": WikidataMovieMetadataProvider,
}
_ALLOWED_IMAGE_TYPES = {"image/jpeg", "image/png", "image/webp"}


def _provider_instance(name: str) -> MovieMetadataProvider:
    provider_name = name.strip().lower()
    provider_cls = PROVIDERS.get(provider_name)
    if provider_cls is None:
        raise ProviderError(f"Proveedor de metadatos no soportado: {provider_name}")
    return provider_cls()


def get_movie_metadata_provider(name: str | None = None) -> MovieMetadataProvider:
    provider_name = (name or getattr(settings, "MOVIE_METADATA_PROVIDER", "tmdb")).strip().lower()
    provider = _provider_instance(provider_name)
    if provider.is_configured():
        return provider

    fallback_name = str(getattr(settings, "MOVIE_METADATA_FALLBACK_PROVIDER", "wikidata")).strip().lower()
    if fallback_name and fallback_name != provider_name:
        fallback = _provider_instance(fallback_name)
        if fallback.is_configured():
            return fallback
    return provider


def split_title_year(title: str) -> tuple[str, int | None]:
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
    exact = [result for result in results if _normalize_title(result.title) == normalized]
    if len(exact) == 1:
        return exact[0]
    if len(results) == 1:
        return results[0]
    return None


def _download_remote_image(url: str) -> tuple[bytes, str]:
    parsed = urlparse(url)
    if parsed.scheme != "https":
        raise ProviderError("La imagen remota debe usar HTTPS.")

    request = Request(url, headers={"Accept": "image/*", "User-Agent": "C2EM-Cinema/1.0"})
    timeout = float(getattr(settings, "MOVIE_METADATA_IMAGE_TIMEOUT_SECONDS", 8))
    max_bytes = int(getattr(settings, "MOVIE_METADATA_IMAGE_MAX_BYTES", 15 * 1024 * 1024))

    try:
        with urlopen(request, timeout=timeout) as response:
            final_url = response.geturl()
            if urlparse(final_url).scheme != "https":
                raise ProviderError("La descarga de imagen fue redirigida fuera de HTTPS.")
            content_type = response.headers.get_content_type().lower()
            if content_type not in _ALLOWED_IMAGE_TYPES:
                raise ProviderError(f"Formato de imagen remoto no permitido: {content_type}.")
            data = response.read(max_bytes + 1)
    except HTTPError as exc:
        raise ProviderError(f"La imagen remota respondió con HTTP {exc.code}.") from exc
    except URLError as exc:
        raise ProviderError(f"No se pudo descargar la imagen remota: {exc.reason}") from exc

    if len(data) > max_bytes:
        raise ProviderError("La imagen remota supera el tamaño máximo permitido.")

    extension = mimetypes.guess_extension(content_type) or Path(parsed.path).suffix.lower() or ".jpg"
    if extension == ".jpe":
        extension = ".jpg"
    return data, extension


def _save_movie_artwork(movie, field_name: str, url: str, *, replace: bool, provider_name: str, external_id: str) -> bool:
    field = getattr(movie, field_name)
    if not url or (field and not replace):
        return False

    data, extension = _download_remote_image(url)
    old_name = field.name if field else ""
    filename = f"{movie.slug}-{provider_name}-{external_id}-{field_name}{extension}"
    field.save(filename, ContentFile(data), save=False)
    new_name = field.name
    movie.save(update_fields=[field_name, "updated_at"])

    if old_name and old_name != new_name:
        field.storage.delete(old_name)
    return True


def _apply_movie_metadata(movie, provider, metadata, *, replace: bool, used_existing_identity: bool):
    fields_updated = []
    try:
        with transaction.atomic():
            identity, _ = MovieExternalId.objects.update_or_create(
                movie=movie,
                provider=provider.name,
                defaults={"external_id": metadata.external_id, "last_synced_at": timezone.now()},
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
                    [CastMember(movie=movie, name=c.name, character=c.character, sort_order=c.order) for c in metadata.cast],
                    ignore_conflicts=True,
                )
    except IntegrityError as exc:
        raise ProviderError(f"El identificador {provider.name}:{metadata.external_id} ya está asociado a otra película.") from exc

    artwork_updated = []
    artwork_errors = []
    if getattr(settings, "MOVIE_METADATA_FETCH_IMAGES", True):
        for field_name, url in (("poster", metadata.poster_url), ("backdrop", metadata.backdrop_url)):
            try:
                if _save_movie_artwork(
                    movie,
                    field_name,
                    url,
                    replace=replace,
                    provider_name=provider.name,
                    external_id=metadata.external_id,
                ):
                    artwork_updated.append(field_name)
            except ProviderError as exc:
                artwork_errors.append(f"{field_name}: {exc}")

    return MetadataSyncResult(
        provider=provider.name,
        external_id=identity.external_id,
        fields_updated=tuple(fields_updated),
        cast_updated=cast_updated,
        used_existing_identity=used_existing_identity,
        artwork_updated=tuple(artwork_updated),
        artwork_errors=tuple(artwork_errors),
    )


def identify_movie_metadata(movie, external_id: str, *, replace: bool = False, provider: MovieMetadataProvider | None = None):
    provider = provider or get_movie_metadata_provider()
    if not provider.is_configured():
        raise ProviderError(f"El proveedor {provider.name} no está configurado.")
    existing = MovieExternalId.objects.filter(movie=movie, provider=provider.name).exists()
    metadata = provider.fetch(str(external_id).strip())
    return _apply_movie_metadata(movie, provider, metadata, replace=replace, used_existing_identity=existing)


def sync_movie_metadata(movie, *, replace: bool = False, provider: MovieMetadataProvider | None = None) -> MetadataSyncResult:
    provider = provider or get_movie_metadata_provider()
    if not provider.is_configured():
        raise ProviderError(f"El proveedor {provider.name} no está configurado.")

    identity = MovieExternalId.objects.filter(movie=movie, provider=provider.name).first()
    used_existing_identity = identity is not None
    if identity is None:
        query_title, year = split_title_year(movie.title)
        results = provider.search(query_title, year=year)
        candidate = _choose_search_result(query_title, results)
        if candidate is None:
            if results:
                raise ProviderError(f"Hay varias coincidencias posibles para «{movie.title}». Usa la pantalla Identificar del admin.")
            raise ProviderError(f"No se encontraron metadatos para «{movie.title}».")
        external_id = candidate.external_id
    else:
        external_id = identity.external_id

    metadata = provider.fetch(external_id)
    return _apply_movie_metadata(movie, provider, metadata, replace=replace, used_existing_identity=used_existing_identity)
