from types import SimpleNamespace
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from catalog.providers import ProviderError

from .models import Movie


class AdminInterfaceTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_superuser(
            username="admin-ui",
            email="admin-ui@example.com",
            password="secret",
        )
        self.client.force_login(self.user)
        self.movie = Movie.objects.create(
            title="Dune (2021)",
            slug="dune-2021",
            description="",
            duration_minutes=155,
            enabled=True,
        )

    def test_admin_dashboard_has_cinema_quick_actions(self):
        response = self.client.get(reverse("admin:index"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Centro de control")
        self.assertContains(response, "Añadir película")
        self.assertContains(response, "Panel de sala")
        self.assertContains(response, reverse("core:ticket_scanner"))

    def test_movie_change_page_has_prominent_metadata_button(self):
        response = self.client.get(reverse("admin:core_movie_change", args=[self.movie.pk]))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Buscar metadatos")
        self.assertContains(response, "Elegir coincidencia manualmente")
        self.assertContains(response, reverse("admin:core_movie_metadata_auto", args=[self.movie.pk]))

    def test_auto_metadata_endpoint_is_post_only(self):
        response = self.client.get(reverse("admin:core_movie_metadata_auto", args=[self.movie.pk]))

        self.assertEqual(response.status_code, 405)

    @patch("core.admin.sync_movie_metadata")
    @patch("core.admin.get_movie_metadata_provider")
    def test_auto_metadata_button_completes_movie_and_returns_to_change_form(self, get_provider, sync_metadata):
        provider = SimpleNamespace(name="tmdb", is_configured=lambda: True)
        get_provider.return_value = provider
        sync_metadata.return_value = SimpleNamespace(
            provider="tmdb",
            fields_updated=("description",),
            cast_updated=True,
            artwork_updated=("poster", "backdrop"),
        )

        response = self.client.post(reverse("admin:core_movie_metadata_auto", args=[self.movie.pk]))

        self.assertRedirects(response, reverse("admin:core_movie_change", args=[self.movie.pk]))
        sync_metadata.assert_called_once_with(self.movie, replace=False, provider=provider)

    @patch("core.admin.sync_movie_metadata")
    @patch("core.admin.get_movie_metadata_provider")
    def test_auto_metadata_button_redirects_to_candidates_when_matching_is_not_automatic(
        self,
        get_provider,
        sync_metadata,
    ):
        provider = SimpleNamespace(name="tmdb", is_configured=lambda: True)
        get_provider.return_value = provider
        sync_metadata.side_effect = ProviderError("Hay varias coincidencias posibles.")

        response = self.client.post(reverse("admin:core_movie_metadata_auto", args=[self.movie.pk]))

        self.assertEqual(response.status_code, 302)
        self.assertTrue(response["Location"].startswith(reverse("admin:core_movie_identify", args=[self.movie.pk])))
        self.assertIn("q=Dune%20(2021)", response["Location"])
