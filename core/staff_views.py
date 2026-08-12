from collections import defaultdict
from datetime import timedelta
from decimal import Decimal

from django.contrib.admin.views.decorators import staff_member_required
from django.db.models import Count, Q
from django.shortcuts import get_object_or_404, render
from django.utils import timezone

from .models import Booking, Screening


@staff_member_required
def screening_dashboard_list(request):
    screenings = (
        Screening.objects.filter(start_at__gte=timezone.now() - timedelta(hours=6))
        .select_related("movie", "room")
        .annotate(
            confirmed_count=Count(
                "bookings",
                filter=Q(bookings__status=Booking.CONFIRMED),
            ),
            checked_in_count=Count(
                "bookings",
                filter=Q(
                    bookings__status=Booking.CONFIRMED,
                    bookings__checked_in_at__isnull=False,
                ),
            ),
        )
        .order_by("start_at")[:30]
    )
    return render(request, "core/staff_screenings.html", {"screenings": screenings})


@staff_member_required
def screening_dashboard(request, pk):
    screening = get_object_or_404(
        Screening.objects.select_related("movie", "room"),
        pk=pk,
    )
    bookings = list(
        screening.bookings.filter(status=Booking.CONFIRMED)
        .prefetch_related("seats__seat", "products__product", "packs__pack")
        .order_by("created_at")
    )

    product_totals = defaultdict(int)
    pack_totals = defaultdict(int)
    gross_total = Decimal("0")
    for booking in bookings:
        gross_total += booking.total
        for item in booking.products.all():
            product_totals[item.product.name] += item.quantity
        for item in booking.packs.all():
            pack_totals[item.pack.name] += item.quantity

    booking_count = len(bookings)
    checked_in_count = sum(1 for booking in bookings if booking.checked_in_at)
    total_seats = screening.room.seats.count()
    reserved_seats = screening.booked_seats.filter(active=True).count()

    context = {
        "screening": screening,
        "bookings": bookings,
        "booking_count": booking_count,
        "checked_in_count": checked_in_count,
        "checkin_percent": round(checked_in_count * 100 / booking_count) if booking_count else 0,
        "total_seats": total_seats,
        "reserved_seats": reserved_seats,
        "occupancy_percent": round(reserved_seats * 100 / total_seats) if total_seats else 0,
        "gross_total": gross_total,
        "product_totals": sorted(product_totals.items()),
        "pack_totals": sorted(pack_totals.items()),
    }
    return render(request, "core/staff_screening_dashboard.html", context)
