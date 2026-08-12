import django.core.validators
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("core", "0003_checkin_preshow"),
    ]

    operations = [
        migrations.AlterField(
            model_name="advertisement",
            name="media",
            field=models.FileField(blank=True, upload_to="ads/", verbose_name="imagen/GIF/vídeo"),
        ),
        migrations.AddField(
            model_name="advertisement",
            name="preshow_duration_seconds",
            field=models.PositiveSmallIntegerField(
                default=8,
                validators=[
                    django.core.validators.MinValueValidator(1),
                    django.core.validators.MaxValueValidator(300),
                ],
                verbose_name="duración pre-show (segundos)",
            ),
        ),
    ]
