import json
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from django.conf import settings

from .base import CastCredit, MovieMetadata, MovieSearchResult, ProviderError


class TmdbMovieMetadataProvider:
    """Small TMDB adapter with the same search -> identify -> fetch split used by media servers."""

    name = "tmdb"
    api_base = "https://api.themoviedb.org"

    def is_configured(self) -> bool:
        return bool(getattr(settings, "TMDB_API_TOKEN", "").strip())

    def _get(self, path: str, **params):
        token = getattr(settings, "TMDB_API_TOKEN", "").strip()
        if not token:
            raise ProviderError("TMDB_API_TOKEN no está configurado.")

        query = urlencode({key: value for key, value in params.items() if value not in (None, "")})
        url = f"{self.api_base}{path}"
        if query:
            url = f"{url}?{query}"

        request = Request(
            url,
            headers={
                "Accept": "application/json",
                "Authorization": f"Bearer {token}",
                "User-Agent": "C2EM-Cinema/1.0",
            },
        )
        timeout = float(getattr(settings, "TMDB_TIMEOUT_SECONDS", 8))

        try:
            with urlopen(request, timeout=timeout) as response:
                return json.load(response)
        except HTTPError as exc:
            raise ProviderError(f"TMDB respondió con HTTP {exc.code}.") from exc
        except URLError as exc:
            raise ProviderError(f"No se pudo conectar con TMDB: {exc.reason}") from exc
        except (json.JSONDecodeError, ValueError) as exc:
            raise ProviderError("TMDB devolvió una respuesta no válida.") from exc

    def _image_url(self, file_path: str | None, size: str) -> str:
        if not file_path:
            return ""
        base = getattr(settings, "TMDB_IMAGE_BASE_URL", "https://image.tmdb.org/t/p").rstrip("/")
        return f"{base}/{size}/{file_path.lstrip('/')}"

    def _poster_url(self, poster_path: str | None) -> str:
        size = getattr(settings, "TMDB_POSTER_PREVIEW_SIZE", "w342")
        return self._image_url(poster_path, size)

    def search(self, title: str, year: int | None = None) -> list[MovieSearchResult]:
        language = getattr(settings, "TMDB_LANGUAGE", "es-ES")
        data = self._get(
            "/3/search/movie",
            query=title,
            language=language,
            include_adult="false",
            primary_release_year=year,
            page=1,
        )
        results = []
        for item in data.get("results", [])[:10]:
            external_id = item.get("id")
            if external_id is None:
                continue
            release_year = None
            release_date = item.get("release_date") or ""
            if len(release_date) >= 4 and release_date[:4].isdigit():
                release_year = int(release_date[:4])
            results.append(
                MovieSearchResult(
                    provider=self.name,
                    external_id=str(external_id),
                    title=(item.get("title") or item.get("original_title") or title).strip(),
                    release_year=release_year,
                    overview=(item.get("overview") or "").strip(),
                    poster_url=self._poster_url(item.get("poster_path")),
                )
            )
        return results

    def fetch(self, external_id: str) -> MovieMetadata:
        language = getattr(settings, "TMDB_LANGUAGE", "es-ES")
        data = self._get(
            f"/3/movie/{external_id}",
            language=language,
            append_to_response="credits,videos",
        )

        overview = (data.get("overview") or "").strip()
        fallback_language = getattr(settings, "TMDB_FALLBACK_LANGUAGE", "en-US")
        if not overview and fallback_language and fallback_language != language:
            fallback = self._get(f"/3/movie/{external_id}", language=fallback_language)
            overview = (fallback.get("overview") or "").strip()

        max_cast = int(getattr(settings, "TMDB_MAX_CAST_MEMBERS", 12))
        cast_items = sorted(data.get("credits", {}).get("cast", []), key=lambda item: item.get("order", 9999))
        cast = []
        for item in cast_items:
            name = (item.get("name") or "").strip()
            if not name:
                continue
            cast.append(CastCredit(name=name, character=(item.get("character") or "").strip(), order=int(item.get("order") or 0)))
            if len(cast) >= max_cast:
                break

        trailer_url = ""
        candidates = sorted(
            data.get("videos", {}).get("results", []),
            key=lambda video: (str(video.get("type", "")).lower() != "trailer", not bool(video.get("official"))),
        )
        for video in candidates:
            if str(video.get("site", "")).lower() == "youtube" and video.get("key"):
                trailer_url = f"https://www.youtube.com/watch?v={video['key']}"
                break

        runtime = data.get("runtime")
        runtime_minutes = int(runtime) if isinstance(runtime, (int, float)) and runtime > 0 else None

        return MovieMetadata(
            provider=self.name,
            external_id=str(data.get("id") or external_id),
            title=(data.get("title") or data.get("original_title") or "").strip(),
            overview=overview,
            runtime_minutes=runtime_minutes,
            trailer_url=trailer_url,
            poster_url=self._image_url(data.get("poster_path"), getattr(settings, "TMDB_POSTER_SIZE", "w780")),
            backdrop_url=self._image_url(data.get("backdrop_path"), getattr(settings, "TMDB_BACKDROP_SIZE", "w1280")),
            cast=tuple(cast),
        )
