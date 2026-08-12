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
