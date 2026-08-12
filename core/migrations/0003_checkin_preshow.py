from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("core", "0002_mvp"),
    ]

    operations = [
        migrations.AddField(
            model_name="booking",
            name="checked_in_at",
            field=models.DateTimeField(blank=True, editable=False, null=True, verbose_name="entrada validada"),
        ),
        migrations.AlterField(
            model_name="advertisement",
            name="placement",
            field=models.CharField(
                choices=[
                    ("home", "Portada"),
                    ("movie", "Película"),
                    ("checkout", "Checkout"),
                    ("ticket", "Entrada"),
                    ("preshow", "Pre-show"),
                ],
                max_length=20,
                verbose_name="ubicación",
            ),
        ),
    ]
