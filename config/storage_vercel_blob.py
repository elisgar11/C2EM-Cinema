import mimetypes
from urllib.parse import urlparse

from django.core.files.storage import Storage
from django.utils.deconstruct import deconstructible


@deconstructible
class VercelBlobStorage(Storage):
    """Persist uploaded media on Vercel Blob (public URLs)."""

    def _is_url(self, name: str) -> bool:
        parsed = urlparse(name)
        return parsed.scheme in {"http", "https"}

    def _save(self, name, content):
        from vercel.blob import put

        data = content.read()
        content_type = getattr(content, "content_type", None) or mimetypes.guess_type(name)[0]
        result = put(
            name,
            data,
            access="public",
            content_type=content_type,
            overwrite=True,
        )
        return result.url

    def url(self, name):
        if not name:
            return ""
        if self._is_url(name):
            return name
        from vercel.blob import head

        return head(name).url

    def delete(self, name):
        if not name:
            return
        from vercel.blob import delete as blob_delete

        try:
            blob_delete(name)
        except Exception:
            return

    def exists(self, name):
        if not name:
            return False
        from vercel.blob import head

        try:
            head(name)
            return True
        except Exception:
            return False

    def size(self, name):
        from vercel.blob import head

        return head(name).size
