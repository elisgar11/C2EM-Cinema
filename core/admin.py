from django.conf import settings
from django.contrib import admin, messages
from django.urls import reverse
from django.utils.html import format_html

from catalog.providers import ProviderError
from catalog.services import get_movie_metadata_provider, sync_movie_metadata

from .models import (
    Advertisement,
    Booking,
    BookingPack,
    BookingProduct,
    BookingSeat,
    Movie,
    Pack,
    PackItem,
    Product,
    Room,
    Screening,
    Seat,
    SiteSettings,
)


@admin.register(SiteSettings)
class SiteSettingsAdmin(admin.ModelAdmin):
    fieldsets = (
        ("Identidad", {"fields": ("cinema_name", "logo", "tagline", "primary_color")}),
        ("Contenido", {"fields": ("home_message", "ticket_footer")}),
        ("Formato", {"fields": ("currency_symbol",)}),
    )

    def has_add_permission(self, request):
        return not SiteSettings.objects.exists()

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(Movie)
class MovieAdmin(admin.ModelAdmin):
    list_display = ("title", "duration_minutes", "age_rating", "metadata_source", "enabled")
    list_filter = ("enabled",)
    search_fields = ("title",)
    prepopulated_fields = {"slug": ("title",)}
    actions = ("complete_metadata", "refresh_metadata")

    def get_queryset(self, request):
        return super().get_queryset(request).prefetch_related("external_ids")

    @admin.display(description="Metadatos")
    def metadata_source(self, obj):
        identity = next(iter(obj.external_ids.all()), None)
        if identity is None:
            return "—"
        return f"{identity.provider}:{identity.external_id}"

    def save_model(self, request, obj, form, change):
        creating = obj.pk is None
        super().save_model(request, obj, form, change)

        if not creating or not getattr(settings, "MOVIE_METADATA_AUTO_FETCH", True):
            return

        try:
            provider = get_movie_metadata_provider()
            if not provider.is_configured():
                self.message_user(
                    request,
                    "Película guardada, pero el proveedor de metadatos no está configurado. Añade TMDB_API_TOKEN para autocompletar sinopsis y reparto.",
                    messages.WARNING,
                )
                return
            result = sync_movie_metadata(obj, provider=provider)
        except ProviderError as exc:
            self.message_user(request, f"Película guardada, pero no se pudieron recuperar metadatos: {exc}", messages.WARNING)
            return

        details = []
        if result.fields_updated:
            details.append(", ".join(result.fields_updated))
        if result.cast_updated:
            details.append("reparto")
        suffix = f" ({'; '.join(details)})" if details else ""
        self.message_user(request, f"Metadatos recuperados desde {result.provider}{suffix}.", messages.SUCCESS)

    def _sync_selected(self, request, queryset, *, replace):
        updated = 0
        failed = 0
        for movie in queryset:
            try:
                sync_movie_metadata(movie, replace=replace)
                updated += 1
            except ProviderError as exc:
                failed += 1
                self.message_user(request, f"{movie.title}: {exc}", messages.WARNING)

        if updated:
            mode = "actualizadas" if replace else "completadas"
            self.message_user(request, f"{updated} película(s) {mode} desde el proveedor de metadatos.", messages.SUCCESS)
        if failed:
            self.message_user(request, f"{failed} película(s) no pudieron sincronizarse.", messages.WARNING)

    @admin.action(description="Completar metadatos vacíos desde el proveedor")
    def complete_metadata(self, request, queryset):
        self._sync_selected(request, queryset, replace=False)

    @admin.action(description="Refrescar y reemplazar metadatos desde el proveedor")
    def refresh_metadata(self, request, queryset):
        self._sync_selected(request, queryset, replace=True)


class SeatInline(admin.TabularInline):
    model = Seat
    extra = 0
    fields = ("row", "number", "seat_type", "enabled")


@admin.register(Room)
class RoomAdmin(admin.ModelAdmin):
    list_display = ("name", "enabled")
    list_filter = ("enabled",)
    search_fields = ("name",)
    inlines = (SeatInline,)


@admin.register(Seat)
class SeatAdmin(admin.ModelAdmin):
    list_display = ("room", "row", "number", "seat_type", "enabled")
    list_filter = ("room", "seat_type", "enabled")
    list_editable = ("seat_type", "enabled")


@admin.register(Screening)
class ScreeningAdmin(admin.ModelAdmin):
    list_display = ("movie", "start_at", "room", "base_price", "enabled", "preshow_link")
    list_filter = ("enabled", "room", "movie")
    date_hierarchy = "start_at"
    autocomplete_fields = ("movie", "room")

    @admin.display(description="Pre-show")
    def preshow_link(self, obj):
        return format_html(
            '<a href="{}" target="_blank" rel="noopener">Abrir</a>',
            reverse("core:preshow", args=[obj.pk]),
        )


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ("name", "price", "enabled", "sort_order")
    list_filter = ("enabled",)
    list_editable = ("price", "enabled", "sort_order")
    search_fields = ("name",)


class PackItemInline(admin.TabularInline):
    model = PackItem
    extra = 1
    autocomplete_fields = ("product",)


@admin.register(Pack)
class PackAdmin(admin.ModelAdmin):
    list_display = ("name", "price", "enabled", "sort_order")
    list_filter = ("enabled",)
    list_editable = ("price", "enabled", "sort_order")
    search_fields = ("name",)
    inlines = (PackItemInline,)


class BookingSeatInline(admin.TabularInline):
    model = BookingSeat
    extra = 0
    can_delete = False
    readonly_fields = ("seat", "price", "active")
    fields = ("seat", "price", "active")


class BookingProductInline(admin.TabularInline):
    model = BookingProduct
    extra = 0
    can_delete = False
    readonly_fields = ("product", "quantity", "unit_price")


class BookingPackInline(admin.TabularInline):
    model = BookingPack
    extra = 0
    can_delete = False
    readonly_fields = ("pack", "quantity", "unit_price")


@admin.register(Booking)
class BookingAdmin(admin.ModelAdmin):
    list_display = (
        "code",
        "customer_name",
        "movie",
        "screening_time",
        "seat_labels",
        "status",
        "checked_in",
        "booking_total",
        "created_at",
    )
    list_filter = ("status", "screening__movie")
    search_fields = ("code", "customer_name")
    readonly_fields = (
        "code",
        "screening",
        "customer_name",
        "notes",
        "status",
        "checked_in_at",
        "ticket_token",
        "created_at",
        "updated_at",
    )
    inlines = (BookingSeatInline, BookingProductInline, BookingPackInline)
    actions = ("check_in_bookings", "cancel_bookings")

    @admin.display(description="Película")
    def movie(self, obj):
        return obj.screening.movie

    @admin.display(description="Sesión", ordering="screening__start_at")
    def screening_time(self, obj):
        return obj.screening.start_at

    @admin.display(description="Butacas")
    def seat_labels(self, obj):
        return ", ".join(item.seat.label for item in obj.seats.all())

    @admin.display(boolean=True, description="Entrada")
    def checked_in(self, obj):
        return bool(obj.checked_in_at)

    @admin.display(description="Total")
    def booking_total(self, obj):
        return obj.total

    @admin.action(description="Validar entrada de reservas seleccionadas")
    def check_in_bookings(self, request, queryset):
        count = sum(1 for booking in queryset if booking.check_in())
        self.message_user(request, f"{count} entrada(s) validada(s).", messages.SUCCESS)

    @admin.action(description="Cancelar reservas seleccionadas")
    def cancel_bookings(self, request, queryset):
        count = 0
        for booking in queryset:
            if booking.status == Booking.CONFIRMED:
                booking.cancel()
                count += 1
        self.message_user(request, f"{count} reserva(s) cancelada(s).", messages.SUCCESS)

    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(Advertisement)
class AdvertisementAdmin(admin.ModelAdmin):
    list_display = ("name", "placement", "priority", "start_at", "end_at", "enabled")
    list_filter = ("placement", "enabled")
    list_editable = ("priority", "enabled")
    search_fields = ("name", "headline")


admin.site.site_header = "Administración del cine"
admin.site.site_title = "Cine"
admin.site.index_title = "Gestión"
