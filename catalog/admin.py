from django.contrib import admin

from .models import CastMember


@admin.register(CastMember)
class CastMemberAdmin(admin.ModelAdmin):
    list_display = ("name", "character", "movie", "sort_order")
    list_filter = ("movie",)
    search_fields = ("name", "character", "movie__title")
    autocomplete_fields = ("movie",)
    list_editable = ("sort_order",)
