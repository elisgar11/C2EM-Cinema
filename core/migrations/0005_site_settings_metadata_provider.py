from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("core", "0004_advertisement_video_duration"),
    ]

    operations = [
        migrations.AddField(
            model_name="sitesettings",
            name="metadata_provider",
            field=models.CharField(
                choices=[
                    ("auto", "Automático (TMDB si hay token; Wikidata como fallback)"),
                    ("tmdb", "TMDB"),
                    ("wikidata", "Wikidata"),
                ],
                default="auto",
                max_length=20,
                verbose_name="proveedor de metadatos",
            ),
        ),
        migrations.AddField(
            model_name="sitesettings",
            name="tmdb_api_token",
            field=models.TextField(blank=True, editable=False, verbose_name="token TMDB"),
        ),
    ]
