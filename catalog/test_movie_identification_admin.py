from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from catalog.models import MovieExternalId
from catalog.providers import CastCredit, MovieMetadata, MovieSearchResult, ProviderError
from catalog.services import sync_movie_metadata
from core.models import Movie


class IdentificationProvider:
    name = "fake"

    def __init__(self):
        self.search_calls = []
        self.fetch_calls = []

    def is_configured(self):
        return True

    def search(self, title, year=None):
        self.search_calls.append((title, year))
        return [
            MovieSearchResult(
                provider=self.name,
                external_id="1",
                title="Dune",
                release_year=1984,
                overview="Adaptación de 1984.",
                poster_url="https://images.example/dune-1984.jpg",
            ),
            MovieSearchResult(
                provider=self.name,
                external_id="2",
                title="Dune",
                release_year=2021,
                overview="Adaptación de 2021.",
                poster_url="https://images.example/dune-2021.jpg",
            ),
        ]

    def fetch(self, external_id):
        self.fetch_calls.append(str(external_id))
        return MovieMetadata(
            provider=self.name,
            external_id=str(external_id),
            title="Dune",
            overview="Sinopsis elegida desde el proveedor.",
            runtime_minutes=155,
            trailer_url="https://www.youtube.com/watch?v=dune",
            cast=(CastCredit(name="Timothée Chalamet", character="Paul Atreides", order=0),),
        )


class MovieIdentificationAdminTests(TestCase):
    def setUp(self):
        self.movie = Movie.objects.create(
            title="Dune",
            slug="dune",
            description="Sinopsis manual.",
            duration_minutes=100,
        )
        self.user = get_user_model().objects.create_superuser(
            username="admin",
            email="admin@example.com",
            password="password",
        )
        self.client.force_login(self.user)
        self.url = reverse("admin:core_movie_identify", args=[self.movie.pk])

    @patch("core.admin.get_movie_metadata_provider")
    def test_identification_screen_lists_candidates_with_year_synopsis_and_poster(self, get_provider):
        provider = IdentificationProvider()
        get_provider.return_value = provider

        response = self.client.get(self.url, {"q": "Dune"})

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "1984")
        self.assertContains(response, "2021")
        self.assertContains(response, "Adaptación de 2021")
        self.assertContains(response, "https://images.example/dune-2021.jpg")
        self.assertEqual(provider.search_calls, [("Dune", None)])

    @patch("core.admin.get_movie_metadata_provider")
    def test_selecting_candidate_persists_identity_without_overwriting_manual_fields(self, get_provider):
        provider = IdentificationProvider()
        get_provider.return_value = provider

        response = self.client.post(
            self.url,
            {"provider": "fake", "external_id": "2", "q": "Dune"},
        )

        self.assertRedirects(response, reverse("admin:core_movie_change", args=[self.movie.pk]))
        self.movie.refresh_from_db()
        identity = MovieExternalId.objects.get(movie=self.movie, provider="fake")
        self.assertEqual(identity.external_id, "2")
        self.assertEqual(self.movie.description, "Sinopsis manual.")
        self.assertEqual(self.movie.duration_minutes, 100)
        self.assertEqual(self.movie.trailer_url, "https://www.youtube.com/watch?v=dune")
        self.assertEqual(list(self.movie.cast_members.values_list("name", flat=True)), ["Timothée Chalamet"])

    @patch("core.admin.get_movie_metadata_provider")
    def test_replace_checkbox_explicitly_replaces_manual_metadata(self, get_provider):
        provider = IdentificationProvider()
        get_provider.return_value = provider

        self.client.post(
            self.url,
            {"provider": "fake", "external_id": "2", "q": "Dune", "replace": "1"},
        )

        self.movie.refresh_from_db()
        self.assertEqual(self.movie.description, "Sinopsis elegida desde el proveedor.")
        self.assertEqual(self.movie.duration_minutes, 155)

    def test_identification_requires_staff_access(self):
        self.client.logout()
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 302)
        self.assertIn("/admin/login/", response.url)


class AmbiguousAutomaticIdentificationTests(TestCase):
    def test_automatic_sync_refuses_ambiguous_title_instead_of_choosing_first_result(self):
        movie = Movie.objects.create(title="Dune", slug="dune", duration_minutes=100)
        provider = IdentificationProvider()

        with self.assertRaisesMessage(ProviderError, "varias coincidencias"):
            sync_movie_metadata(movie, provider=provider)

        self.assertFalse(MovieExternalId.objects.filter(movie=movie).exists())
        self.assertEqual(provider.fetch_calls, [])
