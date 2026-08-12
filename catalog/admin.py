from django.contrib import admin

from .models import CastMember, MovieExternalId


@admin.register(CastMember)
class CastMemberAdmin(admin.ModelAdmin):
    list_display = ("name", "character", "movie", "sort_order")
    list_filter = ("movie",)
    search_fields = ("name", "character", "movie__title")
    autocomplete_fields = ("movie",)
    list_editable = ("sort_order",)


@admin.register(MovieExternalId)
class MovieExternalIdAdmin(admin.ModelAdmin):
    list_display = ("movie", "provider", "external_id", "last_synced_at")
    list_filter = ("provider",)
    search_fields = ("movie__title", "provider", "external_id")
    autocomplete_fields = ("movie",)
    readonly_fields = ("last_synced_at",)
