from datetime import timedelta
from decimal import Decimal

from django.template.loader import render_to_string
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from core.models import Advertisement, Movie, Room, Screening, Seat


class CinematicFrontendRedesignTests(TestCase):
    def test_public_base_loads_redesign_and_motion_assets(self):
        response = self.client.get(reverse("core:reservation_lookup"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "css/cinema-redesign")
        self.assertContains(response, "js/cinema-motion")
        self.assertContains(response, 'class="cinema-header"')

    def test_home_featured_movie_exposes_cinema_showtime_marquee(self):
        movie = Movie.objects.create(
            title="Blade Runner",
            slug="blade-runner-redesign",
            duration_minutes=117,
            enabled=True,
        )
        room = Room.objects.create(name="Sala 1", enabled=True)
        screening = Screening.objects.create(
            movie=movie,
            room=room,
            start_at=timezone.now() + timedelta(hours=2),
            base_price=Decimal("8.50"),
            enabled=True,
        )

        response = self.client.get(reverse("core:home"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "cinema-showtime-strip")
        self.assertContains(response, "Próximo pase")
        self.assertContains(response, screening.room.name)

    def test_seat_selection_renders_three_step_progress(self):
        movie = Movie.objects.create(
            title="Arrival",
            slug="arrival-redesign",
            duration_minutes=116,
            enabled=True,
        )
        room = Room.objects.create(name="Sala Principal", enabled=True)
        Seat.objects.create(room=room, row="A", number=1, enabled=True)
        screening = Screening.objects.create(
            movie=movie,
            room=room,
            start_at=timezone.now() + timedelta(hours=3),
            base_price=Decimal("9.00"),
            enabled=True,
        )

        response = self.client.get(reverse("core:screening_detail", args=[screening.pk]))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "cinema-booking-progress")
        self.assertContains(response, "Paso 1 de 3 · Butacas")
        self.assertContains(response, "Continuar a extras")

    def test_public_video_ad_uses_video_element(self):
        ad = Advertisement(headline="Spot de prueba", placement=Advertisement.HOME, enabled=True)
        ad.media.name = "ads/spot.mp4"

        html = render_to_string("core/includes/ad.html", {"ad": ad})

        self.assertIn("<video", html)
        self.assertNotIn("<img", html)

    def test_public_image_ad_uses_image_element(self):
        ad = Advertisement(headline="Cartel de prueba", placement=Advertisement.HOME, enabled=True)
        ad.media.name = "ads/cartel.jpg"

        html = render_to_string("core/includes/ad.html", {"ad": ad})

        self.assertIn("<img", html)
        self.assertNotIn("<video", html)
