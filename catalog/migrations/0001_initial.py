from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    initial = True

    dependencies = [
        ("core", "0004_advertisement_video_duration"),
    ]

    operations = [
        migrations.CreateModel(
            name="CastMember",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("name", models.CharField(max_length=160, verbose_name="actor o actriz")),
                ("character", models.CharField(blank=True, max_length=160, verbose_name="personaje")),
                ("sort_order", models.PositiveSmallIntegerField(default=0, verbose_name="orden")),
                (
                    "movie",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="cast_members",
                        to="core.movie",
                        verbose_name="película",
                    ),
                ),
            ],
            options={
                "verbose_name": "miembro del reparto",
                "verbose_name_plural": "reparto",
                "ordering": ["sort_order", "id"],
            },
        ),
        migrations.AddConstraint(
            model_name="castmember",
            constraint=models.UniqueConstraint(fields=("movie", "name"), name="unique_movie_cast_member"),
        ),
    ]
