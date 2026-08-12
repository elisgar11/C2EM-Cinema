import tempfile
from pathlib import Path
from unittest.mock import patch

from django.core.files.base import ContentFile
from django.test import TestCase, override_settings

from catalog.models import MovieExternalId
from catalog.providers import MovieMetadata, TmdbMovieMetadataProvider
from catalog.services import identify_movie_metadata
from core.models import Movie


class ArtworkProvider:
    name = "artwork"

    def is_configured(self):
        return True

    def search(self, title, year=None):
        return []

    def fetch(self, external_id):
        return MovieMetadata(
            provider=self.name,
            external_id=str(external_id),
            title="Arrival",
            overview="Sinopsis",
            runtime_minutes=116,
            poster_url="https://images.example/poster.jpg",
            backdrop_url="https://images.example/backdrop.jpg",
        )


class MovieArtworkSyncTests(TestCase):
    def setUp(self):
        self.media_dir = tempfile.TemporaryDirectory()
        self.addCleanup(self.media_dir.cleanup)
        self.settings_override = override_settings(
            MEDIA_ROOT=self.media_dir.name,
            MOVIE_METADATA_FETCH_IMAGES=True,
        )
        self.settings_override.enable()
        self.addCleanup(self.settings_override.disable)
        self.movie = Movie.objects.create(
            title="Arrival",
            slug="arrival",
            description="",
            duration_minutes=100,
        )

    @patch("catalog.services._download_remote_image")
    def test_identification_downloads_missing_poster_and_backdrop(self, download):
        download.side_effect = [(b"poster-bytes", ".jpg"), (b"backdrop-bytes", ".jpg")]

        result = identify_movie_metadata(self.movie, "42", provider=ArtworkProvider())
        self.movie.refresh_from_db()

        self.assertEqual(result.artwork_updated, ("poster", "backdrop"))
        self.assertIn("movies/posters/arrival-artwork-42-poster", self.movie.poster.name)
        self.assertIn("movies/backdrops/arrival-artwork-42-backdrop", self.movie.backdrop.name)
        self.assertTrue(Path(self.movie.poster.path).exists())
        self.assertTrue(Path(self.movie.backdrop.path).exists())
        self.assertEqual(download.call_count, 2)

    @patch("catalog.services._download_remote_image")
    def test_default_identification_preserves_manually_uploaded_artwork(self, download):
        self.movie.poster.save("manual-poster.jpg", ContentFile(b"manual-poster"), save=False)
        self.movie.backdrop.save("manual-backdrop.jpg", ContentFile(b"manual-backdrop"), save=False)
        self.movie.save(update_fields=["poster", "backdrop", "updated_at"])
        poster_name = self.movie.poster.name
        backdrop_name = self.movie.backdrop.name

        result = identify_movie_metadata(self.movie, "42", provider=ArtworkProvider(), replace=False)
        self.movie.refresh_from_db()

        self.assertEqual(result.artwork_updated, ())
        self.assertEqual(self.movie.poster.name, poster_name)
        self.assertEqual(self.movie.backdrop.name, backdrop_name)
        download.assert_not_called()

    @patch("catalog.services._download_remote_image")
    def test_explicit_refresh_replaces_manual_artwork_and_removes_old_files(self, download):
        self.movie.poster.save("manual-poster.jpg", ContentFile(b"manual-poster"), save=False)
        self.movie.backdrop.save("manual-backdrop.jpg", ContentFile(b"manual-backdrop"), save=False)
        self.movie.save(update_fields=["poster", "backdrop", "updated_at"])
        old_poster = Path(self.movie.poster.path)
        old_backdrop = Path(self.movie.backdrop.path)
        download.side_effect = [(b"new-poster", ".jpg"), (b"new-backdrop", ".jpg")]

        result = identify_movie_metadata(self.movie, "42", provider=ArtworkProvider(), replace=True)
        self.movie.refresh_from_db()

        self.assertEqual(result.artwork_updated, ("poster", "backdrop"))
        self.assertFalse(old_poster.exists())
        self.assertFalse(old_backdrop.exists())
        self.assertTrue(Path(self.movie.poster.path).exists())
        self.assertTrue(Path(self.movie.backdrop.path).exists())

    @patch("catalog.services._download_remote_image")
    def test_artwork_download_failure_does_not_rollback_metadata_identity(self, download):
        from catalog.providers import ProviderError

        download.side_effect = ProviderError("CDN no disponible")

        result = identify_movie_metadata(self.movie, "42", provider=ArtworkProvider())
        self.movie.refresh_from_db()

        self.assertEqual(MovieExternalId.objects.get(movie=self.movie).external_id, "42")
        self.assertEqual(self.movie.description, "Sinopsis")
        self.assertEqual(len(result.artwork_errors), 2)


@override_settings(
    TMDB_POSTER_SIZE="w780",
    TMDB_BACKDROP_SIZE="w1280",
    TMDB_IMAGE_BASE_URL="https://image.tmdb.org/t/p",
)
class TmdbArtworkMappingTests(TestCase):
    def test_fetch_maps_tmdb_poster_and_backdrop_paths(self):
        provider = TmdbMovieMetadataProvider()
        payload = {
            "id": 438631,
            "title": "Dune",
            "overview": "Sinopsis",
            "runtime": 155,
            "poster_path": "/poster.jpg",
            "backdrop_path": "/backdrop.jpg",
            "credits": {"cast": []},
            "videos": {"results": []},
        }

        with patch.object(provider, "_get", return_value=payload):
            metadata = provider.fetch("438631")

        self.assertEqual(metadata.poster_url, "https://image.tmdb.org/t/p/w780/poster.jpg")
        self.assertEqual(metadata.backdrop_url, "https://image.tmdb.org/t/p/w1280/backdrop.jpg")
