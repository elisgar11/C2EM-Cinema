from urllib.parse import urlencode

from django.conf import settings
from django.contrib import admin, messages
from django.core.exceptions import PermissionDenied
from django.http import Http404, HttpResponseNotAllowed
from django.shortcuts import redirect
from django.template.response import TemplateResponse
from django.urls import path, reverse
from django.utils.html import format_html

from catalog.creation import create_movie_from_provider
from catalog.providers import ProviderError
from catalog.runtime_config import tmdb_token_source
from catalog.services import (
    get_movie_metadata_provider,
    identify_movie_metadata,
    split_title_year,
    sync_movie_metadata,
)

from .forms import SiteSettingsAdminForm
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
    form = SiteSettingsAdminForm
    readonly_fields = ("metadata_runtime_status",)
    fieldsets = (
        ("Identidad", {"fields": ("cinema_name", "logo", "tagline", "primary_color")}),
        ("Contenido", {"fields": ("home_message", "ticket_footer")}),
        ("Formato", {"fields": ("currency_symbol",)}),
        (
            "Proveedores de metadatos",
            {
                "fields": (
                    "metadata_provider",
                    "metadata_runtime_status",
                    "tmdb_api_token_input",
                    "clear_tmdb_api_token",
                ),
                "description": (
                    "El token guardado aquí se aplica inmediatamente y tiene prioridad sobre TMDB_API_TOKEN del entorno. "
                    "Sin token TMDB, C2EM usa Wikidata automáticamente como fallback."
                ),
            },
        ),
    )

    @admin.display(description="Estado actual")
    def metadata_runtime_status(self, obj):
        try:
            active_provider = get_movie_metadata_provider().name.upper()
        except ProviderError:
            active_provider = "No disponible"
        source = tmdb_token_source()
        source_label = {
            "admin": "token TMDB guardado en el administrador",
            "environment": "token TMDB cargado desde .env",
            "none": "sin token TMDB; Wikidata queda disponible como fallback",
        }.get(source, source)
        return format_html("<strong>{}</strong><br><span>{}</span>", f"Proveedor activo: {active_provider}", source_label)

    def has_add_permission(self, request):
        return not SiteSettings.objects.exists()

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(Movie)
class MovieAdmin(admin.ModelAdmin):
    change_form_template = "admin/core/movie/change_form.html"
    list_display = (
        "poster_preview",
        "title",
        "duration_minutes",
        "age_rating",
        "metadata_source",
        "metadata_action",
        "enabled",
    )
    list_filter = ("enabled",)
    search_fields = ("title",)
    prepopulated_fields = {"slug": ("title",)}
    actions = ("complete_metadata", "refresh_metadata")
    list_per_page = 25

    def get_urls(self):
        custom = [
            path(
                "<path:object_id>/metadata/auto/",
                self.admin_site.admin_view(self.auto_metadata_view),
                name="core_movie_metadata_auto",
            ),
            path(
                "<path:object_id>/identify/",
                self.admin_site.admin_view(self.identify_view),
                name="core_movie_identify",
            ),
        ]
        return custom + super().get_urls()

    def add_view(self, request, form_url="", extra_context=None):
        if request.GET.get("manual") == "1":
            return super().add_view(request, form_url=form_url, extra_context=extra_context)
        if not self.has_add_permission(request):
            raise PermissionDenied

        provider_name = request.POST.get("provider") or request.GET.get("provider") or getattr(
            settings, "MOVIE_METADATA_PROVIDER", "tmdb"
        )
        query = (request.GET.get("q") or request.POST.get("q") or "").strip()
        candidates = []
        provider_error = ""
        provider = None

        try:
            provider = get_movie_metadata_provider(provider_name)
            if not provider.is_configured():
                raise ProviderError(f"El proveedor {provider.name} no está configurado.")

            if request.method == "POST" and request.POST.get("external_id"):
                movie, result = create_movie_from_provider(
                    request.POST["external_id"],
                    provider=provider,
                )
                self.message_user(
                    request,
                    f"«{movie.title}» creada e identificada como {result.provider}:{result.external_id}. "
                    "Ya puedes revisar los datos o programar una sesión.",
                    messages.SUCCESS,
                )
                return redirect(reverse("admin:core_movie_change", args=[movie.pk]))

            if query:
                search_title, year = split_title_year(query)
                candidates = provider.search(search_title, year=year)
        except ProviderError as exc:
            provider_error = str(exc)

        context = {
            **self.admin_site.each_context(request),
            "opts": self.model._meta,
            "title": "Añadir película",
            "query": query,
            "candidates": candidates,
            "provider_name": provider.name if provider else provider_name,
            "provider_error": provider_error,
            "manual_add_url": f"{reverse('admin:core_movie_add')}?manual=1",
            "media": self.media,
        }
        return TemplateResponse(request, "admin/core/movie/add_from_metadata.html", context)

    def get_queryset(self, request):
        return super().get_queryset(request).prefetch_related("external_ids")

    @admin.display(description="Póster")
    def poster_preview(self, obj):
        if not obj.poster:
            return format_html('<span class="cine-admin-poster-placeholder">—</span>')
        return format_html(
            '<img class="cine-admin-poster" src="{}" alt="">',
            obj.poster.url,
        )

    @admin.display(description="Metadatos")
    def metadata_source(self, obj):
        identity = next(iter(obj.external_ids.all()), None)
        if identity is None:
            return format_html('<span class="cine-status cine-status-pending">Sin identificar</span>')
        return format_html(
            '<span class="cine-status cine-status-ok">{}:{}</span>',
            identity.provider,
            identity.external_id,
        )

    @admin.display(description="Acción")
    def metadata_action(self, obj):
        url = reverse("admin:core_movie_identify", args=[obj.pk])
        return format_html('<a class="cine-inline-action" href="{}">Elegir coincidencia</a>', url)

    def _metadata_result_message(self, result):
        details = []
        if result.fields_updated:
            details.append(", ".join(result.fields_updated))
        if result.cast_updated:
            details.append("reparto")
        if getattr(result, "artwork_updated", None):
            details.append(", ".join(result.artwork_updated))
        suffix = f" ({'; '.join(details)})" if details else ""
        return f"Metadatos recuperados desde {result.provider}{suffix}."

    def auto_metadata_view(self, request, object_id):
        if request.method != "POST":
            return HttpResponseNotAllowed(["POST"])

        movie = self.get_object(request, object_id)
        if movie is None:
            raise Http404("Película no encontrada")
        if not self.has_change_permission(request, movie):
            raise PermissionDenied

        try:
            provider = get_movie_metadata_provider()
            if not provider.is_configured():
                raise ProviderError(f"El proveedor {provider.name} no está configurado.")
            result = sync_movie_metadata(movie, replace=False, provider=provider)
        except ProviderError as exc:
            self.message_user(
                request,
                f"No se pudo completar automáticamente: {exc} Revisa las coincidencias disponibles.",
                messages.WARNING,
            )
            identify_url = reverse("admin:core_movie_identify", args=[movie.pk])
            return redirect(f"{identify_url}?{urlencode({'q': movie.title})}")

        self.message_user(request, self._metadata_result_message(result), messages.SUCCESS)
        return redirect(reverse("admin:core_movie_change", args=[movie.pk]))

    def identify_view(self, request, object_id):
        movie = self.get_object(request, object_id)
        if movie is None:
            raise Http404("Película no encontrada")
        if not self.has_change_permission(request, movie):
            raise PermissionDenied

        provider_name = request.POST.get("provider") or request.GET.get("provider") or getattr(
            settings, "MOVIE_METADATA_PROVIDER", "tmdb"
        )
        query = (request.GET.get("q") or request.POST.get("q") or movie.title).strip()
        candidates = []
        provider_error = ""

        try:
            provider = get_movie_metadata_provider(provider_name)
            if not provider.is_configured():
                raise ProviderError(f"El proveedor {provider.name} no está configurado.")

            if request.method == "POST" and request.POST.get("external_id"):
                replace = request.POST.get("replace") == "1"
                result = identify_movie_metadata(
                    movie,
                    request.POST["external_id"],
                    replace=replace,
                    provider=provider,
                )
                mode = "reemplazados" if replace else "completados"
                self.message_user(
                    request,
                    f"Película identificada como {result.provider}:{result.external_id}; metadatos {mode}.",
                    messages.SUCCESS,
                )
                return redirect(reverse("admin:core_movie_change", args=[movie.pk]))

            search_title, year = split_title_year(query)
            candidates = provider.search(search_title, year=year)
        except ProviderError as exc:
            provider = None
            provider_error = str(exc)

        identity = movie.external_ids.first()
        context = {
            **self.admin_site.each_context(request),
            "opts": self.model._meta,
            "original": movie,
            "movie": movie,
            "title": f"Identificar · {movie.title}",
            "query": query,
            "candidates": candidates,
            "provider_name": provider.name if provider else provider_name,
            "provider_error": provider_error,
            "current_identity": identity,
            "media": self.media,
        }
        return TemplateResponse(request, "admin/core/movie/identify.html", context)

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
                    "Película guardada, pero el proveedor de metadatos no está configurado.",
                    messages.WARNING,
                )
                return
            result = sync_movie_metadata(obj, provider=provider)
        except ProviderError as exc:
            self.message_user(request, f"Película guardada, pero no se pudieron recuperar metadatos: {exc}", messages.WARNING)
            return

        self.message_user(request, self._metadata_result_message(result), messages.SUCCESS)

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


admin.site.site_header = "C2EM Cinema · Administración"
admin.site.site_title = "C2EM Cinema"
admin.site.index_title = "Centro de control"
