from decimal import Decimal

from django.db import IntegrityError, transaction

from .models import Booking, BookingPack, BookingProduct, BookingSeat, Pack, Product, Screening, Seat


class BookingError(Exception):
    pass


class SeatConflict(BookingError):
    pass


def normalize_quantities(values):
    result = {}
    for key, value in values.items():
        try:
            quantity = int(value)
        except (TypeError, ValueError):
            continue
        if quantity > 0:
            result[str(key)] = quantity
    return result


def booking_summary(selection):
    if not selection:
        raise BookingError("No hay una reserva en curso.")

    try:
        screening = Screening.objects.select_related("movie", "room").get(pk=selection["screening_id"])
    except (KeyError, Screening.DoesNotExist) as exc:
        raise BookingError("La sesión ya no está disponible.") from exc

    seat_ids = list(dict.fromkeys(selection.get("seat_ids", [])))
    seats = list(Seat.objects.filter(pk__in=seat_ids, room=screening.room, enabled=True).order_by("row", "number"))
    if len(seats) != len(seat_ids):
        raise BookingError("La selección de butacas ya no es válida.")

    product_quantities = normalize_quantities(selection.get("products", {}))
    pack_quantities = normalize_quantities(selection.get("packs", {}))
    products = list(Product.objects.filter(pk__in=product_quantities, enabled=True))
    packs = list(Pack.objects.filter(pk__in=pack_quantities, enabled=True))

    product_lines = [
        {"item": item, "quantity": product_quantities[str(item.pk)], "subtotal": item.price * product_quantities[str(item.pk)]}
        for item in products
    ]
    pack_lines = [
        {"item": item, "quantity": pack_quantities[str(item.pk)], "subtotal": item.price * pack_quantities[str(item.pk)]}
        for item in packs
    ]
    seat_total = screening.base_price * len(seats)
    extras_total = sum((line["subtotal"] for line in product_lines + pack_lines), Decimal("0"))

    return {
        "screening": screening,
        "seats": seats,
        "product_lines": product_lines,
        "pack_lines": pack_lines,
        "seat_total": seat_total,
        "extras_total": extras_total,
        "total": seat_total + extras_total,
    }


def create_booking(selection, customer_name, notes=""):
    summary = booking_summary(selection)
    screening = summary["screening"]
    if not screening.is_bookable:
        raise BookingError("La sesión ya no admite reservas.")

    seat_ids = [seat.pk for seat in summary["seats"]]

    try:
        with transaction.atomic():
            if BookingSeat.objects.filter(screening=screening, seat_id__in=seat_ids, active=True).exists():
                raise SeatConflict("Una de las butacas seleccionadas acaba de ser reservada.")

            booking = Booking.objects.create(
                screening=screening,
                customer_name=customer_name.strip(),
                notes=notes.strip(),
            )
            BookingSeat.objects.bulk_create(
                [
                    BookingSeat(
                        booking=booking,
                        screening=screening,
                        seat=seat,
                        price=screening.base_price,
                    )
                    for seat in summary["seats"]
                ]
            )
            BookingProduct.objects.bulk_create(
                [
                    BookingProduct(
                        booking=booking,
                        product=line["item"],
                        quantity=line["quantity"],
                        unit_price=line["item"].price,
                    )
                    for line in summary["product_lines"]
                ]
            )
            BookingPack.objects.bulk_create(
                [
                    BookingPack(
                        booking=booking,
                        pack=line["item"],
                        quantity=line["quantity"],
                        unit_price=line["item"].price,
                    )
                    for line in summary["pack_lines"]
                ]
            )
    except IntegrityError as exc:
        raise SeatConflict("Una de las butacas seleccionadas acaba de ser reservada.") from exc

    return booking
