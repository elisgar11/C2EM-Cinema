from django import template
from django.db.models import Q
from django.utils import timezone

from core.models import Advertisement

register = template.Library()


@register.inclusion_tag("core/includes/ad.html")
def show_ad(placement):
    now = timezone.now()
    ad = (
        Advertisement.objects.filter(
            placement=placement,
            enabled=True,
            start_at__lte=now,
        )
        .filter(Q(end_at__isnull=True) | Q(end_at__gte=now))
        .order_by("-priority", "?")
        .first()
    )
    return {"ad": ad}
