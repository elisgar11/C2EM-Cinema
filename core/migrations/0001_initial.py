from django.db import migrations, models


def create_default_settings(apps, schema_editor):
    SiteSettings = apps.get_model("core", "SiteSettings")
    SiteSettings.objects.create(pk=1, cinema_name="Mi cine")


class Migration(migrations.Migration):
    initial = True

    dependencies = []

    operations = [
        migrations.CreateModel(
            name="SiteSettings",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("cinema_name", models.CharField(default="Mi cine", max_length=120, verbose_name="nombre del cine")),
                ("logo", models.ImageField(blank=True, upload_to="branding/", verbose_name="logo")),
                ("tagline", models.CharField(blank=True, max_length=200, verbose_name="eslogan")),
                ("currency_symbol", models.CharField(default="€", max_length=8, verbose_name="símbolo de moneda")),
                ("primary_color", models.CharField(default="#e50914", max_length=20, verbose_name="color principal")),
                ("ticket_footer", models.TextField(blank=True, verbose_name="pie de entrada")),
                ("home_message", models.TextField(blank=True, verbose_name="mensaje de portada")),
            ],
            options={
                "verbose_name": "configuración del cine",
                "verbose_name_plural": "configuración del cine",
            },
        ),
        migrations.RunPython(create_default_settings, migrations.RunPython.noop),
    ]
