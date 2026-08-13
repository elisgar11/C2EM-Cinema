from unittest.mock import MagicMock, patch

from django.core.files.base import ContentFile
from django.test import SimpleTestCase

from config.storage_vercel_blob import VercelBlobStorage


class VercelBlobStorageTests(SimpleTestCase):
    def test_save_returns_public_blob_url(self):
        storage = VercelBlobStorage()
        mock_result = MagicMock(url="https://store.public.blob.vercel-storage.com/movies/posters/test.jpg")

        with patch("vercel.blob.put", return_value=mock_result) as put:
            saved = storage._save(
                "movies/posters/test.jpg",
                ContentFile(b"image-bytes", name="test.jpg"),
            )

        self.assertEqual(saved, mock_result.url)
        put.assert_called_once()
        args, kwargs = put.call_args
        self.assertEqual(args[0], "movies/posters/test.jpg")
        self.assertEqual(args[1], b"image-bytes")
        self.assertEqual(kwargs["access"], "public")
        self.assertTrue(kwargs["overwrite"])

    def test_url_returns_stored_https_name(self):
        storage = VercelBlobStorage()
        url = "https://store.public.blob.vercel-storage.com/movies/posters/existing.jpg"
        self.assertEqual(storage.url(url), url)
