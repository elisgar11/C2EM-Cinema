from datetime import timedelta
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from .models import Movie, Product, Room, Screening, Seat
from .services import create_booking


class StaffDashboardTests(TestCase):
    def setUp(self):
        self.room = Room.objects.create(name="Sala Principal")
        self.seat = Seat.objects.create(room=self.room, row="B", number=4)
        Seat.objects.create(room=self.room, row="B", number=5)
        self.movie = Movie.objects.create(title="Alien", slug="alien", duration_minutes=117)
        self.screening = Screening.objects.create(
            movie=self.movie,
            room=self.room,
            start_at=timezone.now() + timedelta(days=1),
            base_price=Decimal("5.00"),
        )
        self.product = Product.objects.create(name="Palomitas", price=Decimal("4.00"))

    def selection(self):
        return {
            "screening_id": self.screening.pk,
            "seat_ids": [self.seat.pk],
            "products": {str(self.product.pk): 1},
            "packs": {},
        }

    def login_staff(self):
        user = get_user_model().objects.create_user(username="staff", password="test", is_staff=True)
        self.client.force_login(user)

    def test_dashboard_list_requires_staff(self):
        response = self.client.get(reverse("core:staff_screenings"))

        self.assertEqual(response.status_code, 302)

    def test_dashboard_detail_requires_staff(self):
        response = self.client.get(reverse("core:screening_dashboard", kwargs={"pk": self.screening.pk}))

        self.assertEqual(response.status_code, 302)

    def test_dashboard_list_shows_reservations_and_checkins(self):
        booking = create_booking(self.selection(), "Ana")
        booking.check_in()
        self.login_staff()

        response = self.client.get(reverse("core:staff_screenings"))
        screening = response.context["screenings"][0]

        self.assertContains(response, "Alien")
        self.assertEqual(screening.confirmed_count, 1)
        self.assertEqual(screening.checked_in_count, 1)

    def test_dashboard_detail_shows_booking_seats_extras_and_total(self):
        booking = create_booking(self.selection(), "Ana")
        self.login_staff()

        response = self.client.get(reverse("core:screening_dashboard", kwargs={"pk": self.screening.pk}))

        self.assertContains(response, booking.code)
        self.assertContains(response, "Ana")
        self.assertContains(response, "B4")
        self.assertContains(response, "1× Palomitas")
        self.assertEqual(response.context["gross_total"], Decimal("9.00"))
        self.assertEqual(response.context["occupancy_percent"], 50)

    def test_cancelled_booking_is_excluded_from_dashboard(self):
        booking = create_booking(self.selection(), "Ana")
        booking.cancel()
        self.login_staff()

        response = self.client.get(reverse("core:screening_dashboard", kwargs={"pk": self.screening.pk}))

        self.assertNotContains(response, booking.code)
        self.assertContains(response, "Todavía no hay reservas confirmadas")
        self.assertEqual(response.context["booking_count"], 0)
