from django.db import models


class CastMember(models.Model):
    movie = models.ForeignKey(
        "core.Movie",
        on_delete=models.CASCADE,
        related_name="cast_members",
        verbose_name="película",
    )
    name = models.CharField("actor o actriz", max_length=160)
    character = models.CharField("personaje", max_length=160, blank=True)
    sort_order = models.PositiveSmallIntegerField("orden", default=0)

    class Meta:
        ordering = ["sort_order", "id"]
        constraints = [
            models.UniqueConstraint(fields=["movie", "name"], name="unique_movie_cast_member"),
        ]
        verbose_name = "miembro del reparto"
        verbose_name_plural = "reparto"

    def __str__(self):
        if self.character:
            return f"{self.name} · {self.character}"
        return self.name


class MovieExternalId(models.Model):
    """Persistent identity for a movie in an external metadata provider."""

    movie = models.ForeignKey(
        "core.Movie",
        on_delete=models.CASCADE,
        related_name="external_ids",
        verbose_name="película",
    )
    provider = models.CharField("proveedor", max_length=40)
    external_id = models.CharField("identificador externo", max_length=120)
    last_synced_at = models.DateTimeField("última sincronización", null=True, blank=True)

    class Meta:
        ordering = ["provider"]
        constraints = [
            models.UniqueConstraint(fields=["movie", "provider"], name="unique_movie_metadata_provider"),
            models.UniqueConstraint(fields=["provider", "external_id"], name="unique_provider_external_movie"),
        ]
        verbose_name = "identificador externo de película"
        verbose_name_plural = "identificadores externos de películas"

    def __str__(self):
        return f"{self.movie} · {self.provider}:{self.external_id}"
