from datetime import timedelta

from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from .models import Advertisement, Movie, Room, Screening


class PreshowMediaTests(TestCase):
    def setUp(self):
        room = Room.objects.create(name="Sala Principal")
        movie = Movie.objects.create(title="Alien", slug="alien", duration_minutes=117)
        self.screening = Screening.objects.create(
            movie=movie,
            room=room,
            start_at=timezone.now() + timedelta(days=1),
        )
        user = get_user_model().objects.create_user(username="staff", password="test", is_staff=True)
        self.client.force_login(user)

    def create_ad(self, **kwargs):
        defaults = {
            "name": "Pre-show",
            "headline": "Publicidad",
            "placement": Advertisement.PRESHOW,
            "start_at": timezone.now() - timedelta(minutes=1),
        }
        defaults.update(kwargs)
        return Advertisement.objects.create(**defaults)

    def test_mp4_media_is_video(self):
        ad = self.create_ad(media="ads/spot.MP4")

        self.assertTrue(ad.media_is_video)

    def test_image_media_is_not_video(self):
        ad = self.create_ad(media="ads/cartel.jpg")

        self.assertFalse(ad.media_is_video)

    def test_preshow_renders_video_with_configured_duration(self):
        self.create_ad(media="ads/spot.mp4", preshow_duration_seconds=12)

        response = self.client.get(reverse("core:preshow", kwargs={"pk": self.screening.pk}))

        self.assertContains(response, "<video")
        self.assertContains(response, 'data-duration="12"')
        self.assertContains(response, "ads/spot.mp4")

    def test_preshow_duration_must_be_positive(self):
        ad = Advertisement(
            name="Inválido",
            headline="Publicidad",
            placement=Advertisement.PRESHOW,
            preshow_duration_seconds=0,
        )

        with self.assertRaises(ValidationError):
            ad.full_clean()
