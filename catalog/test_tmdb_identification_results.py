from unittest.mock import patch

from django.test import TestCase, override_settings

from catalog.providers import TmdbMovieMetadataProvider


@override_settings(TMDB_API_TOKEN="token", TMDB_LANGUAGE="es-ES")
class TmdbIdentificationResultTests(TestCase):
    def test_search_exposes_poster_url_for_admin_identification(self):
        provider = TmdbMovieMetadataProvider()
        payload = {
            "results": [
                {
                    "id": 438631,
                    "title": "Dune",
                    "release_date": "2021-09-15",
                    "overview": "Sinopsis",
                    "poster_path": "/poster.jpg",
                }
            ]
        }

        with patch.object(provider, "_get", return_value=payload):
            result = provider.search("Dune", year=2021)[0]

        self.assertEqual(result.external_id, "438631")
        self.assertEqual(result.poster_url, "https://image.tmdb.org/t/p/w342/poster.jpg")
