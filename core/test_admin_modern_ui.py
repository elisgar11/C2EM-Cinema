from datetime import timedelta
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from core.models import Booking, BookingSeat, Movie, Room, Screening, Seat
from core.templatetags.admin_dashboard import cinema_admin_dashboard


class ModernAdminDashboardTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_superuser(
            username="admin-ui",
            email="admin-ui@example.com",
            password="secret",
        )
        self.client.force_login(self.user)

    def test_admin_home_is_organized_as_cinema_control_center(self):
        response = self.client.get(reverse("admin:index"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Centro de control")
        self.assertContains(response, "Películas programadas")
        self.assertContains(response, "Próxima sesión")
        self.assertContains(response, "Tareas frecuentes")
        self.assertContains(response, "Áreas del cine")
        self.assertNotContains(response, "Todos los módulos")

    def test_sidebar_groups_models_by_workflow(self):
        response = self.client.get(reverse("admin:core_movie_changelist"))

        self.assertEqual(response.status_code, 200)
        for label in (
            "Cartelera",
            "Operación",
            "Bar y extras",
            "Comunicación",
            "Metadatos",
            "Configuración",
            "Sistema",
        ):
            self.assertContains(response, label)
        self.assertContains(response, "Escáner de entradas")
        self.assertContains(response, "Identificadores externos")

    def test_dashboard_metrics_include_next_screening_and_occupancy(self):
        movie = Movie.objects.create(
            title="Arrival",
            slug="arrival-admin-dashboard",
            duration_minutes=116,
            enabled=True,
        )
        room = Room.objects.create(name="Sala Dashboard", enabled=True)
        seat_a = Seat.objects.create(room=room, row="A", number=1, enabled=True)
        Seat.objects.create(room=room, row="A", number=2, enabled=True)
        screening = Screening.objects.create(
            movie=movie,
            room=room,
            start_at=timezone.now() + timedelta(days=1),
            base_price=Decimal("8.00"),
            enabled=True,
        )
        booking = Booking.objects.create(
            screening=screening,
            customer_name="Invitado",
            status=Booking.CONFIRMED,
            checked_in_at=timezone.now(),
        )
        BookingSeat.objects.create(
            booking=booking,
            screening=screening,
            seat=seat_a,
            price=Decimal("8.00"),
            active=True,
        )

        data = cinema_admin_dashboard()

        self.assertEqual(data["scheduled_movies"], 1)
        self.assertEqual(data["upcoming_bookings"], 1)
        self.assertEqual(data["checkins_today"], 1)
        self.assertEqual(data["next_screening"]["screening"], screening)
        self.assertEqual(data["next_screening"]["reserved"], 1)
        self.assertEqual(data["next_screening"]["capacity"], 2)
        self.assertEqual(data["next_screening"]["occupancy"], 50)
