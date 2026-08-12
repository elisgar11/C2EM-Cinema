from datetime import timedelta
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.db import IntegrityError, transaction
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from .models import Advertisement, Booking, BookingSeat, Movie, Product, Room, Screening, Seat, SiteSettings
from .services import SeatConflict, create_booking


class CinemaFixture(TestCase):
    def setUp(self):
        self.room = Room.objects.create(name="Sala Principal")
        self.seat = Seat.objects.create(room=self.room, row="B", number=4)
        self.second_seat = Seat.objects.create(room=self.room, row="B", number=5)
        self.movie = Movie.objects.create(title="Alien", slug="alien", duration_minutes=117)
        self.screening = Screening.objects.create(
            movie=self.movie,
            room=self.room,
            start_at=timezone.now() + timedelta(days=1),
            base_price=Decimal("5.00"),
        )

    def selection(self, seats=None, products=None):
        return {
            "screening_id": self.screening.pk,
            "seat_ids": seats or [self.seat.pk],
            "products": products or {},
            "packs": {},
        }

    def login_staff(self):
        user = get_user_model().objects.create_user(username="staff", password="test", is_staff=True)
        self.client.force_login(user)
        return user


class SiteSettingsTests(TestCase):
    def test_singleton_uses_fixed_primary_key(self):
        first = SiteSettings.load()
        first.cinema_name = "Primer cine"
        first.save()
        second = SiteSettings(cinema_name="Cine actualizado")
        second.save()

        self.assertEqual(first.pk, 1)
        self.assertEqual(second.pk, 1)
        self.assertEqual(SiteSettings.objects.count(), 1)
        self.assertEqual(SiteSettings.objects.get().cinema_name, "Cine actualizado")


class BookingTests(CinemaFixture):
    def test_confirmed_booking_occupies_seat(self):
        booking = create_booking(self.selection(), "Ana")

        self.assertEqual(booking.status, Booking.CONFIRMED)
        self.assertTrue(BookingSeat.objects.get(booking=booking, seat=self.seat).active)

    def test_same_seat_cannot_be_booked_twice(self):
        create_booking(self.selection(), "Ana")

        with self.assertRaises(SeatConflict):
            create_booking(self.selection(), "Luis")

    def test_database_constraint_rejects_two_active_occupations(self):
        first = create_booking(self.selection(), "Ana")
        second = Booking.objects.create(screening=self.screening, customer_name="Luis")

        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                BookingSeat.objects.create(
                    booking=second,
                    screening=self.screening,
                    seat=self.seat,
                    price=self.screening.base_price,
                )

        self.assertTrue(first.seats.get().active)

    def test_cancelled_booking_releases_seat(self):
        booking = create_booking(self.selection(), "Ana")
        booking.cancel()
        second = create_booking(self.selection(), "Luis")

        self.assertEqual(booking.status, Booking.CANCELLED)
        self.assertFalse(booking.seats.get().active)
        self.assertEqual(second.status, Booking.CONFIRMED)

    def test_product_price_is_snapshotted(self):
        product = Product.objects.create(name="Palomitas", price=Decimal("4.00"))
        booking = create_booking(self.selection(products={str(product.pk): 1}), "Ana")
        product.price = Decimal("9.00")
        product.save()

        self.assertEqual(booking.products.get().unit_price, Decimal("4.00"))

    def test_check_in_is_idempotent(self):
        booking = create_booking(self.selection(), "Ana")

        self.assertTrue(booking.check_in())
        first_check_in = booking.checked_in_at
        self.assertFalse(booking.check_in())
        booking.refresh_from_db()

        self.assertEqual(booking.checked_in_at, first_check_in)

    def test_cancelled_booking_cannot_check_in(self):
        booking = create_booking(self.selection(), "Ana")
        booking.cancel()

        self.assertFalse(booking.check_in())
        self.assertIsNone(booking.checked_in_at)


class PublicFlowTests(CinemaFixture):
    def test_home_lists_bookable_movie(self):
        response = self.client.get(reverse("core:home"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Alien")

    def test_disabled_movie_is_not_in_home(self):
        self.movie.enabled = False
        self.movie.save()

        response = self.client.get(reverse("core:home"))

        self.assertNotContains(response, "Alien")

    def test_disabled_screening_does_not_start_booking(self):
        self.screening.enabled = False
        self.screening.save()

        response = self.client.post(
            reverse("core:booking_start"),
            {"screening_id": self.screening.pk, "seats": [self.seat.pk]},
        )

        self.assertEqual(response.status_code, 302)
        self.assertNotIn("booking", self.client.session)

    def test_checkout_creates_ticket(self):
        session = self.client.session
        session["booking"] = self.selection()
        session.save()

        response = self.client.post(reverse("core:checkout"), {"customer_name": "Ana", "notes": ""})
        booking = Booking.objects.get()

        self.assertRedirects(response, reverse("core:booking_complete", kwargs={"token": booking.ticket_token}))
        ticket = self.client.get(reverse("core:ticket", kwargs={"token": booking.ticket_token}))
        self.assertContains(ticket, booking.code)
        self.assertContains(ticket, "B4")

    def test_ticket_qr_is_svg(self):
        booking = create_booking(self.selection(), "Ana")

        response = self.client.get(reverse("core:ticket_qr", kwargs={"token": booking.ticket_token}))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response["Content-Type"], "image/svg+xml")

    def test_reservation_lookup_redirects_to_ticket(self):
        booking = create_booking(self.selection(), "Ana")

        response = self.client.post(reverse("core:reservation_lookup"), {"code": booking.code.lower()})

        self.assertRedirects(response, reverse("core:ticket", kwargs={"token": booking.ticket_token}))

    def test_unknown_reservation_code_stays_on_lookup(self):
        response = self.client.post(reverse("core:reservation_lookup"), {"code": "CINE-XXXXXX"})

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "No hemos encontrado")


class StaffFlowTests(CinemaFixture):
    def test_check_in_requires_staff(self):
        booking = create_booking(self.selection(), "Ana")

        response = self.client.post(reverse("core:ticket_check_in", kwargs={"token": booking.ticket_token}))
        booking.refresh_from_db()

        self.assertEqual(response.status_code, 302)
        self.assertIsNone(booking.checked_in_at)

    def test_staff_can_check_in_ticket(self):
        booking = create_booking(self.selection(), "Ana")
        self.login_staff()

        response = self.client.post(reverse("core:ticket_check_in", kwargs={"token": booking.ticket_token}))
        booking.refresh_from_db()

        self.assertRedirects(response, reverse("core:ticket", kwargs={"token": booking.ticket_token}))
        self.assertIsNotNone(booking.checked_in_at)

    def test_preshow_requires_staff(self):
        response = self.client.get(reverse("core:preshow", kwargs={"pk": self.screening.pk}))

        self.assertEqual(response.status_code, 302)

    def test_preshow_lists_active_preshow_ads(self):
        Advertisement.objects.create(
            name="Pre-show",
            headline="APAGA EL MÓVIL",
            placement=Advertisement.PRESHOW,
            start_at=timezone.now() - timedelta(minutes=1),
        )
        self.login_staff()

        response = self.client.get(reverse("core:preshow", kwargs={"pk": self.screening.pk}))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "APAGA EL MÓVIL")
        self.assertContains(response, "Alien")


class AdvertisementTests(CinemaFixture):
    def test_expired_ad_is_not_rendered(self):
        Advertisement.objects.create(
            name="Viejo",
            headline="ANUNCIO CADUCADO",
            placement=Advertisement.HOME,
            start_at=timezone.now() - timedelta(days=2),
            end_at=timezone.now() - timedelta(days=1),
        )

        response = self.client.get(reverse("core:home"))

        self.assertNotContains(response, "ANUNCIO CADUCADO")

    def test_active_ad_is_rendered(self):
        Advertisement.objects.create(
            name="Actual",
            headline="ANUNCIO ACTIVO",
            placement=Advertisement.HOME,
            start_at=timezone.now() - timedelta(minutes=1),
        )

        response = self.client.get(reverse("core:home"))

        self.assertContains(response, "ANUNCIO ACTIVO")
