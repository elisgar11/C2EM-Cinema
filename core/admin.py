from django.contrib import admin, messages

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
    list_display = ("title", "duration_minutes", "age_rating", "enabled")
    list_filter = ("enabled",)
    search_fields = ("title",)
    prepopulated_fields = {"slug": ("title",)}


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
    list_display = ("movie", "start_at", "room", "base_price", "enabled")
    list_filter = ("enabled", "room", "movie")
    date_hierarchy = "start_at"
    autocomplete_fields = ("movie", "room")


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
    list_display = ("code", "customer_name", "movie", "screening_time", "seat_labels", "status", "booking_total", "created_at")
    list_filter = ("status", "screening__movie")
    search_fields = ("code", "customer_name")
    readonly_fields = ("code", "screening", "customer_name", "notes", "status", "ticket_token", "created_at", "updated_at")
    inlines = (BookingSeatInline, BookingProductInline, BookingPackInline)
    actions = ("cancel_bookings",)

    @admin.display(description="Película")
    def movie(self, obj):
        return obj.screening.movie

    @admin.display(description="Sesión", ordering="screening__start_at")
    def screening_time(self, obj):
        return obj.screening.start_at

    @admin.display(description="Butacas")
    def seat_labels(self, obj):
        return ", ".join(item.seat.label for item in obj.seats.all())

    @admin.display(description="Total")
    def booking_total(self, obj):
        return obj.total

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
