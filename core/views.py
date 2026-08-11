from collections import defaultdict

import qrcode
import qrcode.image.svg
from django.contrib import messages
from django.db.models import Prefetch
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone
from django.views.decorators.http import require_GET, require_POST, require_http_methods

from .models import Booking, BookingSeat, Movie, Pack, Product, Screening, Seat
from .services import BookingError, SeatConflict, booking_summary, create_booking, normalize_quantities


@require_GET
def home(request):
    upcoming = Screening.objects.filter(enabled=True, room__enabled=True, start_at__gte=timezone.now()).select_related("room").order_by("start_at")
    movies = (
        Movie.objects.filter(enabled=True, screenings__enabled=True, screenings__room__enabled=True, screenings__start_at__gte=timezone.now())
        .distinct()
        .prefetch_related(Prefetch("screenings", queryset=upcoming, to_attr="upcoming_screenings"))
    )
    next_screenings = Screening.objects.filter(enabled=True, movie__enabled=True, room__enabled=True, start_at__gte=timezone.now()).select_related("movie", "room")[:8]
    return render(request, "core/home.html", {"movies": movies, "next_screenings": next_screenings})


@require_GET
def movie_detail(request, slug):
    movie = get_object_or_404(Movie, slug=slug, enabled=True)
    screenings = movie.screenings.filter(enabled=True, room__enabled=True, start_at__gte=timezone.now()).select_related("room")
    grouped = defaultdict(list)
    for screening in screenings:
        grouped[timezone.localdate(screening.start_at)].append(screening)
    return render(request, "core/movie_detail.html", {"movie": movie, "screening_days": list(grouped.items())})


@require_GET
def screening_detail(request, pk):
    screening = get_object_or_404(Screening.objects.select_related("movie", "room"), pk=pk)
    if not screening.is_bookable:
        messages.error(request, "Esta sesión ya no admite reservas.")
        return redirect(screening.movie if screening.movie.enabled else "core:home")

    occupied = set(
        BookingSeat.objects.filter(screening=screening, active=True).values_list("seat_id", flat=True)
    )
    rows = defaultdict(list)
    for seat in Seat.objects.filter(room=screening.room).order_by("row", "number"):
        rows[seat.row].append({"seat": seat, "occupied": seat.pk in occupied})

    return render(request, "core/screening_detail.html", {"screening": screening, "seat_rows": rows.items()})


@require_POST
def booking_start(request):
    screening = get_object_or_404(Screening.objects.select_related("movie", "room"), pk=request.POST.get("screening_id"))
    if not screening.is_bookable:
        messages.error(request, "Esta sesión ya no admite reservas.")
        return redirect(screening.movie if screening.movie.enabled else "core:home")

    seat_ids = []
    for value in request.POST.getlist("seats"):
        try:
            seat_ids.append(int(value))
        except ValueError:
            pass
    seat_ids = list(dict.fromkeys(seat_ids))

    valid_ids = set(
        Seat.objects.filter(pk__in=seat_ids, room=screening.room, enabled=True).values_list("pk", flat=True)
    )
    occupied = set(
        BookingSeat.objects.filter(screening=screening, seat_id__in=seat_ids, active=True).values_list("seat_id", flat=True)
    )
    if not seat_ids or len(valid_ids) != len(seat_ids) or occupied:
        messages.error(request, "Selecciona una o más butacas disponibles.")
        return redirect("core:screening_detail", pk=screening.pk)

    request.session["booking"] = {
        "screening_id": screening.pk,
        "seat_ids": seat_ids,
        "products": {},
        "packs": {},
    }
    return redirect("core:booking_extras")


@require_http_methods(["GET", "POST"])
def booking_extras(request):
    selection = request.session.get("booking")
    if not selection:
        messages.info(request, "Primero selecciona una sesión y tus butacas.")
        return redirect("core:home")

    if request.method == "POST":
        selection["products"] = normalize_quantities(
            {product.pk: request.POST.get(f"product_{product.pk}", 0) for product in Product.objects.filter(enabled=True)}
        )
        selection["packs"] = normalize_quantities(
            {pack.pk: request.POST.get(f"pack_{pack.pk}", 0) for pack in Pack.objects.filter(enabled=True)}
        )
        request.session["booking"] = selection
        request.session.modified = True
        return redirect("core:checkout")

    try:
        summary = booking_summary(selection)
    except BookingError as exc:
        request.session.pop("booking", None)
        messages.error(request, str(exc))
        return redirect("core:home")

    products = Product.objects.filter(enabled=True)
    packs = Pack.objects.filter(enabled=True).prefetch_related("items__product")
    return render(request, "core/extras.html", {"summary": summary, "products": products, "packs": packs})


@require_http_methods(["GET", "POST"])
def checkout(request):
    selection = request.session.get("booking")
    try:
        summary = booking_summary(selection)
    except BookingError as exc:
        request.session.pop("booking", None)
        messages.error(request, str(exc))
        return redirect("core:home")

    if request.method == "POST":
        customer_name = request.POST.get("customer_name", "").strip()
        notes = request.POST.get("notes", "")
        if not customer_name:
            messages.error(request, "Escribe un nombre para la reserva.")
            return render(request, "core/checkout.html", {"summary": summary, "customer_name": customer_name, "notes": notes})
        try:
            booking = create_booking(selection, customer_name, notes)
        except SeatConflict as exc:
            messages.error(request, str(exc) + " Selecciona otras butacas.")
            return redirect("core:screening_detail", pk=summary["screening"].pk)
        except BookingError as exc:
            messages.error(request, str(exc))
            return redirect("core:home")

        request.session.pop("booking", None)
        return redirect("core:booking_complete", token=booking.ticket_token)

    return render(request, "core/checkout.html", {"summary": summary})


@require_GET
def booking_complete(request, token):
    booking = get_object_or_404(
        Booking.objects.select_related("screening__movie", "screening__room").prefetch_related("seats__seat"),
        ticket_token=token,
    )
    return render(request, "core/booking_complete.html", {"booking": booking})


@require_GET
def ticket(request, token):
    booking = get_object_or_404(
        Booking.objects.select_related("screening__movie", "screening__room")
        .prefetch_related("seats__seat", "products__product", "packs__pack"),
        ticket_token=token,
    )
    return render(request, "core/ticket.html", {"booking": booking})


@require_GET
def ticket_qr(request, token):
    booking = get_object_or_404(Booking, ticket_token=token)
    url = request.build_absolute_uri(reverse("core:ticket", kwargs={"token": booking.ticket_token}))
    image = qrcode.make(url, image_factory=qrcode.image.svg.SvgPathImage)
    response = HttpResponse(content_type="image/svg+xml")
    image.save(response)
    return response
