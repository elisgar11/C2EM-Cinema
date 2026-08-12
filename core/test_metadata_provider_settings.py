from types import SimpleNamespace
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.test import TestCase, override_settings
from django.urls import reverse

from catalog.providers import TmdbMovieMetadataProvider, WikidataMovieMetadataProvider
from catalog.runtime_config import metadata_provider_preference, tmdb_api_token, tmdb_token_source
from catalog.services import get_movie_metadata_provider

from .forms import SiteSettingsAdminForm
from .models import SiteSettings


class MetadataProviderSettingsTests(TestCase):
    def setUp(self):
        self.site = SiteSettings.load()

    def form_data(self, **overrides):
        data = {
            "cinema_name": self.site.cinema_name,
            "tagline": self.site.tagline,
            "primary_color": self.site.primary_color,
            "home_message": self.site.home_message,
            "ticket_footer": self.site.ticket_footer,
            "currency_symbol": self.site.currency_symbol,
            "metadata_provider": "auto",
            "tmdb_api_token_input": "",
        }
        data.update(overrides)
        return data

    @override_settings(TMDB_API_TOKEN="")
    def test_admin_token_is_saved_and_used_immediately(self):
        form = SiteSettingsAdminForm(
            data=self.form_data(tmdb_api_token_input="admin-read-token"),
            instance=self.site,
        )
        self.assertTrue(form.is_valid(), form.errors)
        form.save()

        self.assertEqual(tmdb_api_token(), "admin-read-token")
        self.assertEqual(tmdb_token_source(), "admin")
        self.assertIsInstance(get_movie_metadata_provider(), TmdbMovieMetadataProvider)

    @override_settings(TMDB_API_TOKEN="environment-token")
    def test_admin_token_has_priority_over_environment(self):
        self.site.tmdb_api_token = "admin-token"
        self.site.save()

        self.assertEqual(tmdb_api_token(), "admin-token")
        self.assertEqual(tmdb_token_source(), "admin")

    @override_settings(TMDB_API_TOKEN="environment-token")
    def test_clearing_admin_token_returns_to_environment(self):
        self.site.tmdb_api_token = "admin-token"
        self.site.save()
        form = SiteSettingsAdminForm(
            data=self.form_data(clear_tmdb_api_token="on"),
            instance=self.site,
        )
        self.assertTrue(form.is_valid(), form.errors)
        form.save()

        self.assertEqual(tmdb_api_token(), "environment-token")
        self.assertEqual(tmdb_token_source(), "environment")

    @override_settings(TMDB_API_TOKEN="token", MOVIE_METADATA_PROVIDER="tmdb")
    def test_admin_can_force_wikidata(self):
        self.site.metadata_provider = "wikidata"
        self.site.save()

        self.assertEqual(metadata_provider_preference(), "wikidata")
        self.assertIsInstance(get_movie_metadata_provider(), WikidataMovieMetadataProvider)

    @override_settings(TMDB_API_TOKEN="", MOVIE_METADATA_PROVIDER="tmdb", MOVIE_METADATA_FALLBACK_PROVIDER="wikidata")
    def test_auto_mode_falls_back_to_wikidata_without_tmdb_token(self):
        self.site.metadata_provider = "auto"
        self.site.tmdb_api_token = ""
        self.site.save()

        self.assertIsInstance(get_movie_metadata_provider(), WikidataMovieMetadataProvider)


class MetadataProviderSettingsAdminSecurityTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_superuser(
            username="metadata-admin",
            email="metadata@example.com",
            password="secret",
        )
        self.client.force_login(self.user)
        self.site = SiteSettings.load()
        self.site.tmdb_api_token = "super-secret-read-token"
        self.site.save()

    @override_settings(TMDB_API_TOKEN="")
    def test_saved_token_is_never_rendered_back_in_admin_html(self):
        response = self.client.get(reverse("admin:core_sitesettings_change", args=[self.site.pk]))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Proveedores de metadatos")
        self.assertContains(response, "Nuevo API Read Access Token de TMDB")
        self.assertContains(response, "token TMDB guardado en el administrador")
        self.assertNotContains(response, "super-secret-read-token")
        self.assertContains(response, 'type="password"')

    @override_settings(TMDB_API_TOKEN="token", MOVIE_METADATA_PROVIDER="tmdb")
    @patch("core.admin.get_movie_metadata_provider")
    def test_add_movie_assistant_uses_provider_selected_in_cinema_settings(self, get_provider):
        self.site.metadata_provider = "wikidata"
        self.site.save()
        get_provider.return_value = SimpleNamespace(
            name="wikidata",
            is_configured=lambda: True,
            search=lambda title, year=None: [],
        )

        response = self.client.get(reverse("admin:core_movie_add"))

        self.assertEqual(response.status_code, 200)
        get_provider.assert_called_once_with("wikidata")
        self.assertContains(response, "WIKIDATA")
