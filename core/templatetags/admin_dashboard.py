from datetime import datetime, time

from django import template
from django.urls import reverse
from django.utils import timezone

from catalog.providers import ProviderError
from catalog.services import get_movie_metadata_provider
from core.models import Booking, BookingSeat, Movie, Screening, Seat

register = template.Library()


def _today_range():
    local_date = timezone.localdate()
    tz = timezone.get_current_timezone()
    start = timezone.make_aware(datetime.combine(local_date, time.min), tz)
    end = timezone.make_aware(datetime.combine(local_date, time.max), tz)
    return start, end


@register.simple_tag
def cinema_admin_dashboard():
    now = timezone.now()
    today_start, today_end = _today_range()

    future_screenings = Screening.objects.filter(
        enabled=True,
        movie__enabled=True,
        room__enabled=True,
        start_at__gte=now,
    )
    today_screenings = future_screenings.filter(start_at__range=(today_start, today_end)).count()
    scheduled_movies = (
        Movie.objects.filter(enabled=True, screenings__in=future_screenings)
        .distinct()
        .count()
    )
    upcoming_bookings = Booking.objects.filter(
        status=Booking.CONFIRMED,
        screening__enabled=True,
        screening__start_at__gte=now,
    ).count()
    checkins_today = Booking.objects.filter(
        checked_in_at__range=(today_start, today_end),
    ).count()

    next_screening = future_screenings.select_related("movie", "room").order_by("start_at").first()
    next_screening_data = None
    if next_screening is not None:
        reserved = BookingSeat.objects.filter(screening=next_screening, active=True).count()
        capacity = Seat.objects.filter(room=next_screening.room, enabled=True).count()
        occupancy = round((reserved / capacity) * 100) if capacity else 0
        next_screening_data = {
            "screening": next_screening,
            "reserved": reserved,
            "capacity": capacity,
            "occupancy": occupancy,
            "dashboard_url": reverse("core:screening_dashboard", args=[next_screening.pk]),
            "preshow_url": reverse("core:preshow", args=[next_screening.pk]),
        }

    try:
        provider_name = get_movie_metadata_provider().name
    except ProviderError:
        provider_name = "sin proveedor"

    return {
        "scheduled_movies": scheduled_movies,
        "today_screenings": today_screenings,
        "upcoming_bookings": upcoming_bookings,
        "checkins_today": checkins_today,
        "next_screening": next_screening_data,
        "provider_name": provider_name,
    }
