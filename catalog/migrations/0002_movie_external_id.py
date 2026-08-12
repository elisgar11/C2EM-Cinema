from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [
        ("catalog", "0001_initial"),
        ("core", "0004_advertisement_video_duration"),
    ]

    operations = [
        migrations.CreateModel(
            name="MovieExternalId",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("provider", models.CharField(max_length=40, verbose_name="proveedor")),
                ("external_id", models.CharField(max_length=120, verbose_name="identificador externo")),
                ("last_synced_at", models.DateTimeField(blank=True, null=True, verbose_name="última sincronización")),
                (
                    "movie",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="external_ids",
                        to="core.movie",
                        verbose_name="película",
                    ),
                ),
            ],
            options={
                "verbose_name": "identificador externo de película",
                "verbose_name_plural": "identificadores externos de películas",
                "ordering": ["provider"],
            },
        ),
        migrations.AddConstraint(
            model_name="movieexternalid",
            constraint=models.UniqueConstraint(fields=("movie", "provider"), name="unique_movie_metadata_provider"),
        ),
        migrations.AddConstraint(
            model_name="movieexternalid",
            constraint=models.UniqueConstraint(fields=("provider", "external_id"), name="unique_provider_external_movie"),
        ),
    ]
