from datetime import timedelta
from decimal import Decimal

from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from catalog.models import CastMember
from core.models import Movie, Room, Screening


class MovieMetadataAndListingsTests(TestCase):
    def setUp(self):
        self.room = Room.objects.create(name="Sala Principal")

    def create_movie(self, title, slug, start_at, description="Sinopsis de prueba"):
        movie = Movie.objects.create(
            title=title,
            slug=slug,
            description=description,
            duration_minutes=100,
        )
        Screening.objects.create(
            movie=movie,
            room=self.room,
            start_at=start_at,
            base_price=Decimal("5.00"),
        )
        return movie

    def test_movie_detail_shows_synopsis_and_cast(self):
        movie = self.create_movie("Arrival", "arrival", timezone.now() + timedelta(days=1), "Una lingüista intenta comprender a unos visitantes inesperados.")
        CastMember.objects.create(movie=movie, name="Amy Adams", character="Louise Banks", sort_order=1)
        CastMember.objects.create(movie=movie, name="Jeremy Renner", character="Ian Donnelly", sort_order=2)

        response = self.client.get(reverse("core:movie_detail", kwargs={"slug": movie.slug}))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Sinopsis")
        self.assertContains(response, "Una lingüista intenta comprender")
        self.assertContains(response, "Reparto")
        self.assertContains(response, "Amy Adams")
        self.assertContains(response, "Louise Banks")
        self.assertContains(response, "Jeremy Renner")

    def test_cast_members_keep_configured_order(self):
        movie = self.create_movie("Heat", "heat", timezone.now() + timedelta(days=1))
        CastMember.objects.create(movie=movie, name="Segundo", sort_order=20)
        CastMember.objects.create(movie=movie, name="Primero", sort_order=10)

        self.assertEqual(list(movie.cast_members.values_list("name", flat=True)), ["Primero", "Segundo"])

    def test_home_prioritizes_movie_with_nearest_screening(self):
        later = self.create_movie("Alpha", "alpha", timezone.now() + timedelta(days=3))
        sooner = self.create_movie("Zulu", "zulu", timezone.now() + timedelta(hours=3))

        response = self.client.get(reverse("core:home"))
        html = response.content.decode()

        self.assertEqual(response.status_code, 200)
        self.assertLess(html.find(sooner.title), html.find(later.title))
        self.assertContains(response, "Ordenada por la próxima sesión")

    def test_home_uses_relative_day_badge_for_nearest_screening(self):
        start_at = timezone.now() + timedelta(hours=2)
        self.create_movie("Moon", "moon", start_at)
        expected = "Hoy" if timezone.localdate(start_at) == timezone.localdate() else "Mañana"

        response = self.client.get(reverse("core:home"))

        self.assertContains(response, expected)
        self.assertContains(response, "Siguiente")
