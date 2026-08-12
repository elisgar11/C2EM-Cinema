from datetime import timedelta

from django import template
from django.utils import timezone

register = template.Library()


def _relative_day_kind(day):
    today = timezone.localdate()
    if day == today:
        return "today"
    if day == today + timedelta(days=1):
        return "tomorrow"
    return "upcoming"


@register.filter
def relative_day_kind(day):
    if not day:
        return "upcoming"
    return _relative_day_kind(day)


@register.simple_tag
def dynamic_movies(movies):
    """Order movies by their nearest screening and attach display-only timing metadata."""
    dynamic = []
    for movie in list(movies):
        screenings = list(getattr(movie, "upcoming_screenings", []))
        if not screenings:
            continue
        next_screening = screenings[0]
        next_screening.relative_day_kind = _relative_day_kind(timezone.localdate(next_screening.start_at))
        movie.next_screening = next_screening
        dynamic.append(movie)

    dynamic.sort(key=lambda movie: movie.next_screening.start_at)
    return dynamic


@register.simple_tag
def dynamic_screening_groups(screenings):
    """Group chronological screenings into local calendar days for the home schedule."""
    groups = []
    current = None

    for screening in list(screenings):
        day = timezone.localdate(screening.start_at)
        if current is None or current["day"] != day:
            current = {
                "day": day,
                "kind": _relative_day_kind(day),
                "screenings": [],
            }
            groups.append(current)
        current["screenings"].append(screening)

    return groups
