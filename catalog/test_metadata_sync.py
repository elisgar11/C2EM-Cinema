from unittest.mock import Mock, patch

from django.test import TestCase, override_settings

from catalog.models import CastMember, MovieExternalId
from catalog.providers import CastCredit, MovieMetadata, MovieSearchResult, ProviderError, TmdbMovieMetadataProvider
from catalog.services import sync_movie_metadata
from core.models import Movie


class FakeProvider:
    name = "fake"

    def __init__(self, *, configured=True):
        self.configured = configured
        self.search_calls = []
        self.fetch_calls = []

    def is_configured(self):
        return self.configured

    def search(self, title, year=None):
        self.search_calls.append((title, year))
        return [
            MovieSearchResult(
                provider=self.name,
                external_id="42",
                title=title,
                release_year=year,
            )
        ]

    def fetch(self, external_id):
        self.fetch_calls.append(external_id)
        return MovieMetadata(
            provider=self.name,
            external_id=external_id,
            title="Arrival",
            overview="Sinopsis recuperada desde el proveedor.",
            runtime_minutes=116,
            trailer_url="https://www.youtube.com/watch?v=example",
            cast=(
                CastCredit(name="Amy Adams", character="Louise Banks", order=0),
                CastCredit(name="Jeremy Renner", character="Ian Donnelly", order=1),
            ),
        )


class MovieMetadataSyncTests(TestCase):
    def create_movie(self, *, title="Arrival", description=""):
        return Movie.objects.create(
            title=title,
            slug=title.lower().replace(" ", "-").replace("(", "").replace(")", ""),
            description=description,
            duration_minutes=100,
        )

    def test_initial_sync_searches_title_and_populates_empty_metadata(self):
        movie = self.create_movie()
        provider = FakeProvider()

        result = sync_movie_metadata(movie, provider=provider)
        movie.refresh_from_db()

        self.assertEqual(provider.search_calls, [("Arrival", None)])
        self.assertEqual(provider.fetch_calls, ["42"])
        self.assertEqual(movie.description, "Sinopsis recuperada desde el proveedor.")
        self.assertEqual(movie.trailer_url, "https://www.youtube.com/watch?v=example")
        self.assertEqual(list(movie.cast_members.values_list("name", flat=True)), ["Amy Adams", "Jeremy Renner"])
        identity = MovieExternalId.objects.get(movie=movie, provider="fake")
        self.assertEqual(identity.external_id, "42")
        self.assertIsNotNone(identity.last_synced_at)
        self.assertFalse(result.used_existing_identity)

    def test_existing_provider_identity_skips_title_search(self):
        movie = self.create_movie()
        MovieExternalId.objects.create(movie=movie, provider="fake", external_id="99")
        provider = FakeProvider()

        result = sync_movie_metadata(movie, provider=provider)

        self.assertEqual(provider.search_calls, [])
        self.assertEqual(provider.fetch_calls, ["99"])
        self.assertTrue(result.used_existing_identity)

    def test_default_sync_preserves_manual_synopsis_and_cast(self):
        movie = self.create_movie(description="Sinopsis escrita a mano.")
        CastMember.objects.create(movie=movie, name="Reparto manual", character="Personaje", sort_order=0)
        provider = FakeProvider()

        sync_movie_metadata(movie, provider=provider)
        movie.refresh_from_db()

        self.assertEqual(movie.description, "Sinopsis escrita a mano.")
        self.assertEqual(list(movie.cast_members.values_list("name", flat=True)), ["Reparto manual"])

    def test_forced_refresh_replaces_provider_managed_metadata(self):
        movie = self.create_movie(description="Sinopsis antigua.")
        CastMember.objects.create(movie=movie, name="Reparto antiguo", sort_order=0)
        provider = FakeProvider()

        sync_movie_metadata(movie, provider=provider, replace=True)
        movie.refresh_from_db()

        self.assertEqual(movie.description, "Sinopsis recuperada desde el proveedor.")
        self.assertEqual(movie.duration_minutes, 116)
        self.assertEqual(list(movie.cast_members.values_list("name", flat=True)), ["Amy Adams", "Jeremy Renner"])

    def test_year_suffix_can_disambiguate_title_search(self):
        movie = self.create_movie(title="Dune (2021)")
        provider = FakeProvider()

        sync_movie_metadata(movie, provider=provider)

        self.assertEqual(provider.search_calls, [("Dune", 2021)])

    def test_unconfigured_provider_fails_without_changing_movie(self):
        movie = self.create_movie()
        provider = FakeProvider(configured=False)

        with self.assertRaises(ProviderError):
            sync_movie_metadata(movie, provider=provider)

        self.assertFalse(MovieExternalId.objects.filter(movie=movie).exists())


@override_settings(TMDB_LANGUAGE="es-ES", TMDB_FALLBACK_LANGUAGE="en-US", TMDB_MAX_CAST_MEMBERS="2")
class TmdbProviderTests(TestCase):
    def test_fetch_falls_back_for_empty_spanish_synopsis_and_maps_cast(self):
        provider = TmdbMovieMetadataProvider()
        spanish = {
            "id": 10,
            "title": "Película",
            "overview": "",
            "runtime": 120,
            "credits": {
                "cast": [
                    {"name": "Segundo", "character": "B", "order": 2},
                    {"name": "Primero", "character": "A", "order": 1},
                    {"name": "Tercero", "character": "C", "order": 3},
                ]
            },
            "videos": {
                "results": [
                    {"site": "YouTube", "type": "Trailer", "official": True, "key": "abc123"}
                ]
            },
        }
        english = {"overview": "English fallback synopsis."}

        with patch.object(provider, "_get", side_effect=[spanish, english]) as get:
            metadata = provider.fetch("10")

        self.assertEqual(metadata.overview, "English fallback synopsis.")
        self.assertEqual(metadata.runtime_minutes, 120)
        self.assertEqual([credit.name for credit in metadata.cast], ["Primero", "Segundo"])
        self.assertEqual(metadata.trailer_url, "https://www.youtube.com/watch?v=abc123")
        self.assertEqual(get.call_count, 2)

    @override_settings(TMDB_API_TOKEN="token")
    def test_search_maps_tmdb_results_without_network(self):
        provider = TmdbMovieMetadataProvider()
        payload = {
            "results": [
                {"id": 438631, "title": "Dune", "release_date": "2021-09-15", "overview": "Sinopsis"}
            ]
        }

        with patch.object(provider, "_get", return_value=payload) as get:
            results = provider.search("Dune", year=2021)

        self.assertEqual(results[0].external_id, "438631")
        self.assertEqual(results[0].release_year, 2021)
        get.assert_called_once()
