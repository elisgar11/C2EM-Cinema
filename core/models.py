import secrets
import uuid
from decimal import Decimal

from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models, transaction
from django.urls import reverse
from django.utils import timezone


BOOKING_ALPHABET = "23456789ABCDEFGHJKLMNPQRSTUVWXYZ"


def generate_booking_code():
    return "CINE-" + "".join(secrets.choice(BOOKING_ALPHABET) for _ in range(6))


class SiteSettings(models.Model):
    cinema_name = models.CharField("nombre del cine", max_length=120, default="Mi cine")
    logo = models.ImageField("logo", upload_to="branding/", blank=True)
    tagline = models.CharField("eslogan", max_length=200, blank=True)
    currency_symbol = models.CharField("símbolo de moneda", max_length=8, default="€")
    primary_color = models.CharField("color principal", max_length=20, default="#e50914")
    ticket_footer = models.TextField("pie de entrada", blank=True)
    home_message = models.TextField("mensaje de portada", blank=True)

    class Meta:
        verbose_name = "configuración del cine"
        verbose_name_plural = "configuración del cine"

    @classmethod
    def load(cls):
        obj, _ = cls.objects.get_or_create(pk=1)
        return obj

    def save(self, *args, **kwargs):
        self.pk = 1
        super().save(*args, **kwargs)

    def __str__(self):
        return self.cinema_name


class Movie(models.Model):
    title = models.CharField("título", max_length=200)
    slug = models.SlugField(unique=True)
    description = models.TextField("descripción", blank=True)
    poster = models.ImageField("póster", upload_to="movies/posters/", blank=True)
    backdrop = models.ImageField("fondo", upload_to="movies/backdrops/", blank=True)
    duration_minutes = models.PositiveIntegerField("duración (minutos)")
    age_rating = models.CharField("clasificación", max_length=30, blank=True)
    trailer_url = models.URLField("tráiler", blank=True)
    enabled = models.BooleanField("activa", default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["title"]
        verbose_name = "película"
        verbose_name_plural = "películas"

    def get_absolute_url(self):
        return reverse("core:movie_detail", kwargs={"slug": self.slug})

    def __str__(self):
        return self.title


class Room(models.Model):
    name = models.CharField("nombre", max_length=120, unique=True)
    description = models.TextField("descripción", blank=True)
    enabled = models.BooleanField("activa", default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["name"]
        verbose_name = "sala"
        verbose_name_plural = "salas"

    def __str__(self):
        return self.name


class Seat(models.Model):
    STANDARD = "standard"
    VIP = "vip"
    TYPE_CHOICES = [(STANDARD, "Estándar"), (VIP, "VIP")]

    room = models.ForeignKey(Room, on_delete=models.CASCADE, related_name="seats", verbose_name="sala")
    row = models.CharField("fila", max_length=8)
    number = models.PositiveIntegerField("número")
    seat_type = models.CharField("tipo", max_length=20, choices=TYPE_CHOICES, default=STANDARD)
    enabled = models.BooleanField("activa", default=True)

    class Meta:
        ordering = ["room", "row", "number"]
        constraints = [
            models.UniqueConstraint(fields=["room", "row", "number"], name="unique_room_seat"),
        ]
        verbose_name = "butaca"
        verbose_name_plural = "butacas"

    @property
    def label(self):
        return f"{self.row}{self.number}"

    def __str__(self):
        return f"{self.room} · {self.label}"


class Screening(models.Model):
    movie = models.ForeignKey(Movie, on_delete=models.PROTECT, related_name="screenings", verbose_name="película")
    room = models.ForeignKey(Room, on_delete=models.PROTECT, related_name="screenings", verbose_name="sala")
    start_at = models.DateTimeField("inicio")
    base_price = models.DecimalField("precio", max_digits=8, decimal_places=2, default=0)
    enabled = models.BooleanField("activa", default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["start_at"]
        verbose_name = "sesión"
        verbose_name_plural = "sesiones"

    @property
    def is_bookable(self):
        return self.enabled and self.movie.enabled and self.room.enabled and self.start_at >= timezone.now()

    def __str__(self):
        return f"{self.movie} · {timezone.localtime(self.start_at):%d/%m/%Y %H:%M}"


class Booking(models.Model):
    CONFIRMED = "confirmed"
    CANCELLED = "cancelled"
    STATUS_CHOICES = [(CONFIRMED, "Confirmada"), (CANCELLED, "Cancelada")]

    code = models.CharField("código", max_length=20, unique=True, editable=False)
    screening = models.ForeignKey(Screening, on_delete=models.PROTECT, related_name="bookings", verbose_name="sesión")
    customer_name = models.CharField("nombre", max_length=150)
    notes = models.TextField("notas", blank=True)
    status = models.CharField("estado", max_length=20, choices=STATUS_CHOICES, default=CONFIRMED)
    checked_in_at = models.DateTimeField("entrada validada", null=True, blank=True, editable=False)
    ticket_token = models.UUIDField("token de entrada", default=uuid.uuid4, unique=True, editable=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "reserva"
        verbose_name_plural = "reservas"

    def save(self, *args, **kwargs):
        if not self.code:
            code = generate_booking_code()
            while Booking.objects.filter(code=code).exists():
                code = generate_booking_code()
            self.code = code
        super().save(*args, **kwargs)

    def cancel(self):
        if self.status == self.CANCELLED:
            return
        with transaction.atomic():
            self.status = self.CANCELLED
            self.save(update_fields=["status", "updated_at"])
            self.seats.filter(active=True).update(active=False)

    def check_in(self):
        if self.status != self.CONFIRMED or self.checked_in_at:
            return False
        now = timezone.now()
        updated = Booking.objects.filter(
            pk=self.pk,
            status=self.CONFIRMED,
            checked_in_at__isnull=True,
        ).update(checked_in_at=now, updated_at=now)
        if updated:
            self.checked_in_at = now
            self.updated_at = now
        return bool(updated)

    @property
    def total(self):
        seat_total = sum((item.price for item in self.seats.all()), Decimal("0"))
        product_total = sum((item.unit_price * item.quantity for item in self.products.all()), Decimal("0"))
        pack_total = sum((item.unit_price * item.quantity for item in self.packs.all()), Decimal("0"))
        return seat_total + product_total + pack_total

    def __str__(self):
        return f"{self.code} · {self.customer_name}"


class BookingSeat(models.Model):
    booking = models.ForeignKey(Booking, on_delete=models.CASCADE, related_name="seats", verbose_name="reserva")
    screening = models.ForeignKey(Screening, on_delete=models.PROTECT, related_name="booked_seats", verbose_name="sesión")
    seat = models.ForeignKey(Seat, on_delete=models.PROTECT, related_name="bookings", verbose_name="butaca")
    price = models.DecimalField("precio", max_digits=8, decimal_places=2)
    active = models.BooleanField("ocupada", default=True)

    class Meta:
        ordering = ["seat__row", "seat__number"]
        constraints = [
            models.UniqueConstraint(fields=["booking", "seat"], name="unique_booking_seat"),
            models.UniqueConstraint(
                fields=["screening", "seat"],
                condition=models.Q(active=True),
                name="unique_active_screening_seat",
            ),
        ]
        verbose_name = "butaca reservada"
        verbose_name_plural = "butacas reservadas"

    def __str__(self):
        return f"{self.booking.code} · {self.seat.label}"


class Product(models.Model):
    name = models.CharField("nombre", max_length=150)
    description = models.TextField("descripción", blank=True)
    image = models.ImageField("imagen", upload_to="shop/products/", blank=True)
    price = models.DecimalField("precio", max_digits=8, decimal_places=2, default=0)
    enabled = models.BooleanField("activo", default=True)
    sort_order = models.IntegerField("orden", default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["sort_order", "name"]
        verbose_name = "producto"
        verbose_name_plural = "productos"

    def __str__(self):
        return self.name


class Pack(models.Model):
    name = models.CharField("nombre", max_length=150)
    description = models.TextField("descripción", blank=True)
    image = models.ImageField("imagen", upload_to="shop/packs/", blank=True)
    price = models.DecimalField("precio", max_digits=8, decimal_places=2, default=0)
    enabled = models.BooleanField("activo", default=True)
    sort_order = models.IntegerField("orden", default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["sort_order", "name"]
        verbose_name = "pack"
        verbose_name_plural = "packs"

    def __str__(self):
        return self.name


class PackItem(models.Model):
    pack = models.ForeignKey(Pack, on_delete=models.CASCADE, related_name="items", verbose_name="pack")
    product = models.ForeignKey(Product, on_delete=models.PROTECT, related_name="pack_items", verbose_name="producto")
    quantity = models.PositiveIntegerField("cantidad", default=1)

    class Meta:
        constraints = [models.UniqueConstraint(fields=["pack", "product"], name="unique_pack_product")]
        verbose_name = "producto del pack"
        verbose_name_plural = "productos del pack"

    def __str__(self):
        return f"{self.quantity} × {self.product}"


class BookingProduct(models.Model):
    booking = models.ForeignKey(Booking, on_delete=models.CASCADE, related_name="products", verbose_name="reserva")
    product = models.ForeignKey(Product, on_delete=models.PROTECT, related_name="bookings", verbose_name="producto")
    quantity = models.PositiveIntegerField("cantidad")
    unit_price = models.DecimalField("precio unitario", max_digits=8, decimal_places=2)

    class Meta:
        verbose_name = "producto reservado"
        verbose_name_plural = "productos reservados"

    def __str__(self):
        return f"{self.quantity} × {self.product}"


class BookingPack(models.Model):
    booking = models.ForeignKey(Booking, on_delete=models.CASCADE, related_name="packs", verbose_name="reserva")
    pack = models.ForeignKey(Pack, on_delete=models.PROTECT, related_name="bookings", verbose_name="pack")
    quantity = models.PositiveIntegerField("cantidad")
    unit_price = models.DecimalField("precio unitario", max_digits=8, decimal_places=2)

    class Meta:
        verbose_name = "pack reservado"
        verbose_name_plural = "packs reservados"

    def __str__(self):
        return f"{self.quantity} × {self.pack}"


class Advertisement(models.Model):
    HOME = "home"
    MOVIE = "movie"
    CHECKOUT = "checkout"
    TICKET = "ticket"
    PRESHOW = "preshow"
    PLACEMENT_CHOICES = [
        (HOME, "Portada"),
        (MOVIE, "Película"),
        (CHECKOUT, "Checkout"),
        (TICKET, "Entrada"),
        (PRESHOW, "Pre-show"),
    ]

    name = models.CharField("nombre interno", max_length=150)
    headline = models.CharField("titular", max_length=200)
    body = models.TextField("texto", blank=True)
    media = models.FileField("imagen/GIF/vídeo", upload_to="ads/", blank=True)
    target_url = models.URLField("enlace", blank=True)
    placement = models.CharField("ubicación", max_length=20, choices=PLACEMENT_CHOICES)
    preshow_duration_seconds = models.PositiveSmallIntegerField(
        "duración pre-show (segundos)",
        default=8,
        validators=[MinValueValidator(1), MaxValueValidator(300)],
    )
    start_at = models.DateTimeField("inicio", default=timezone.now)
    end_at = models.DateTimeField("fin", null=True, blank=True)
    priority = models.IntegerField("prioridad", default=0)
    enabled = models.BooleanField("activo", default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-priority", "name"]
        verbose_name = "anuncio"
        verbose_name_plural = "anuncios"

    @property
    def media_is_video(self):
        if not self.media:
            return False
        return self.media.name.lower().endswith((".mp4", ".webm"))

    def __str__(self):
        return self.name
