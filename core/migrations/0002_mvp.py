import uuid

import django.db.models.deletion
import django.utils.timezone
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("core", "0001_initial")]

    operations = [
        migrations.CreateModel(
            name="Advertisement",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("name", models.CharField(max_length=150, verbose_name="nombre interno")),
                ("headline", models.CharField(max_length=200, verbose_name="titular")),
                ("body", models.TextField(blank=True, verbose_name="texto")),
                ("media", models.ImageField(blank=True, upload_to="ads/", verbose_name="imagen/GIF")),
                ("target_url", models.URLField(blank=True, verbose_name="enlace")),
                ("placement", models.CharField(choices=[("home", "Portada"), ("movie", "Película"), ("checkout", "Checkout"), ("ticket", "Entrada")], max_length=20, verbose_name="ubicación")),
                ("start_at", models.DateTimeField(default=django.utils.timezone.now, verbose_name="inicio")),
                ("end_at", models.DateTimeField(blank=True, null=True, verbose_name="fin")),
                ("priority", models.IntegerField(default=0, verbose_name="prioridad")),
                ("enabled", models.BooleanField(default=True, verbose_name="activo")),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
            ],
            options={"verbose_name": "anuncio", "verbose_name_plural": "anuncios", "ordering": ["-priority", "name"]},
        ),
        migrations.CreateModel(
            name="Movie",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("title", models.CharField(max_length=200, verbose_name="título")),
                ("slug", models.SlugField(unique=True)),
                ("description", models.TextField(blank=True, verbose_name="descripción")),
                ("poster", models.ImageField(blank=True, upload_to="movies/posters/", verbose_name="póster")),
                ("backdrop", models.ImageField(blank=True, upload_to="movies/backdrops/", verbose_name="fondo")),
                ("duration_minutes", models.PositiveIntegerField(verbose_name="duración (minutos)")),
                ("age_rating", models.CharField(blank=True, max_length=30, verbose_name="clasificación")),
                ("trailer_url", models.URLField(blank=True, verbose_name="tráiler")),
                ("enabled", models.BooleanField(default=True, verbose_name="activa")),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
            ],
            options={"verbose_name": "película", "verbose_name_plural": "películas", "ordering": ["title"]},
        ),
        migrations.CreateModel(
            name="Pack",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("name", models.CharField(max_length=150, verbose_name="nombre")),
                ("description", models.TextField(blank=True, verbose_name="descripción")),
                ("image", models.ImageField(blank=True, upload_to="shop/packs/", verbose_name="imagen")),
                ("price", models.DecimalField(decimal_places=2, default=0, max_digits=8, verbose_name="precio")),
                ("enabled", models.BooleanField(default=True, verbose_name="activo")),
                ("sort_order", models.IntegerField(default=0, verbose_name="orden")),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
            ],
            options={"verbose_name": "pack", "verbose_name_plural": "packs", "ordering": ["sort_order", "name"]},
        ),
        migrations.CreateModel(
            name="Product",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("name", models.CharField(max_length=150, verbose_name="nombre")),
                ("description", models.TextField(blank=True, verbose_name="descripción")),
                ("image", models.ImageField(blank=True, upload_to="shop/products/", verbose_name="imagen")),
                ("price", models.DecimalField(decimal_places=2, default=0, max_digits=8, verbose_name="precio")),
                ("enabled", models.BooleanField(default=True, verbose_name="activo")),
                ("sort_order", models.IntegerField(default=0, verbose_name="orden")),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
            ],
            options={"verbose_name": "producto", "verbose_name_plural": "productos", "ordering": ["sort_order", "name"]},
        ),
        migrations.CreateModel(
            name="Room",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("name", models.CharField(max_length=120, unique=True, verbose_name="nombre")),
                ("description", models.TextField(blank=True, verbose_name="descripción")),
                ("enabled", models.BooleanField(default=True, verbose_name="activa")),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
            ],
            options={"verbose_name": "sala", "verbose_name_plural": "salas", "ordering": ["name"]},
        ),
        migrations.CreateModel(
            name="PackItem",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("quantity", models.PositiveIntegerField(default=1, verbose_name="cantidad")),
                ("pack", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="items", to="core.pack", verbose_name="pack")),
                ("product", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="pack_items", to="core.product", verbose_name="producto")),
            ],
            options={"verbose_name": "producto del pack", "verbose_name_plural": "productos del pack"},
        ),
        migrations.CreateModel(
            name="Seat",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("row", models.CharField(max_length=8, verbose_name="fila")),
                ("number", models.PositiveIntegerField(verbose_name="número")),
                ("seat_type", models.CharField(choices=[("standard", "Estándar"), ("vip", "VIP")], default="standard", max_length=20, verbose_name="tipo")),
                ("enabled", models.BooleanField(default=True, verbose_name="activa")),
                ("room", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="seats", to="core.room", verbose_name="sala")),
            ],
            options={"verbose_name": "butaca", "verbose_name_plural": "butacas", "ordering": ["room", "row", "number"]},
        ),
        migrations.CreateModel(
            name="Screening",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("start_at", models.DateTimeField(verbose_name="inicio")),
                ("base_price", models.DecimalField(decimal_places=2, default=0, max_digits=8, verbose_name="precio")),
                ("enabled", models.BooleanField(default=True, verbose_name="activa")),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("movie", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="screenings", to="core.movie", verbose_name="película")),
                ("room", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="screenings", to="core.room", verbose_name="sala")),
            ],
            options={"verbose_name": "sesión", "verbose_name_plural": "sesiones", "ordering": ["start_at"]},
        ),
        migrations.CreateModel(
            name="Booking",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("code", models.CharField(editable=False, max_length=20, unique=True, verbose_name="código")),
                ("customer_name", models.CharField(max_length=150, verbose_name="nombre")),
                ("notes", models.TextField(blank=True, verbose_name="notas")),
                ("status", models.CharField(choices=[("confirmed", "Confirmada"), ("cancelled", "Cancelada")], default="confirmed", max_length=20, verbose_name="estado")),
                ("ticket_token", models.UUIDField(default=uuid.uuid4, editable=False, unique=True, verbose_name="token de entrada")),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("screening", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="bookings", to="core.screening", verbose_name="sesión")),
            ],
            options={"verbose_name": "reserva", "verbose_name_plural": "reservas", "ordering": ["-created_at"]},
        ),
        migrations.CreateModel(
            name="BookingPack",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("quantity", models.PositiveIntegerField(verbose_name="cantidad")),
                ("unit_price", models.DecimalField(decimal_places=2, max_digits=8, verbose_name="precio unitario")),
                ("booking", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="packs", to="core.booking", verbose_name="reserva")),
                ("pack", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="bookings", to="core.pack", verbose_name="pack")),
            ],
            options={"verbose_name": "pack reservado", "verbose_name_plural": "packs reservados"},
        ),
        migrations.CreateModel(
            name="BookingProduct",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("quantity", models.PositiveIntegerField(verbose_name="cantidad")),
                ("unit_price", models.DecimalField(decimal_places=2, max_digits=8, verbose_name="precio unitario")),
                ("booking", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="products", to="core.booking", verbose_name="reserva")),
                ("product", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="bookings", to="core.product", verbose_name="producto")),
            ],
            options={"verbose_name": "producto reservado", "verbose_name_plural": "productos reservados"},
        ),
        migrations.CreateModel(
            name="BookingSeat",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("price", models.DecimalField(decimal_places=2, max_digits=8, verbose_name="precio")),
                ("active", models.BooleanField(default=True, verbose_name="ocupada")),
                ("booking", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="seats", to="core.booking", verbose_name="reserva")),
                ("screening", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="booked_seats", to="core.screening", verbose_name="sesión")),
                ("seat", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="bookings", to="core.seat", verbose_name="butaca")),
            ],
            options={"verbose_name": "butaca reservada", "verbose_name_plural": "butacas reservadas", "ordering": ["seat__row", "seat__number"]},
        ),
        migrations.AddConstraint(model_name="packitem", constraint=models.UniqueConstraint(fields=("pack", "product"), name="unique_pack_product")),
        migrations.AddConstraint(model_name="seat", constraint=models.UniqueConstraint(fields=("room", "row", "number"), name="unique_room_seat")),
        migrations.AddConstraint(model_name="bookingseat", constraint=models.UniqueConstraint(fields=("booking", "seat"), name="unique_booking_seat")),
        migrations.AddConstraint(model_name="bookingseat", constraint=models.UniqueConstraint(condition=models.Q(active=True), fields=("screening", "seat"), name="unique_active_screening_seat")),
    ]
