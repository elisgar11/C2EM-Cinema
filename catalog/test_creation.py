from django.test import TestCase, override_settings

from core.models import Movie

from .creation import create_movie_from_provider
from .models import CastMember, MovieExternalId
from .providers import CastCredit, MovieMetadata, ProviderError


class FakeProvider:
    name = "tmdb"

    def is_configured(self):
        return True

    def fetch(self, external_id):
        return MovieMetadata(
            provider=self.name,
            external_id=str(external_id),
            title="Arrival",
            overview="Una lingüista intenta comunicarse con visitantes extraterrestres.",
            runtime_minutes=116,
            trailer_url="https://www.youtube.com/watch?v=example",
            cast=(
                CastCredit(name="Amy Adams", character="Louise Banks", order=0),
                CastCredit(name="Jeremy Renner", character="Ian Donnelly", order=1),
            ),
        )


@override_settings(MOVIE_METADATA_FETCH_IMAGES=False)
class MovieCreationFromProviderTests(TestCase):
    def test_creates_complete_movie_with_persistent_identity_and_cast(self):
        movie, result = create_movie_from_provider("329865", provider=FakeProvider())

        movie.refresh_from_db()
        self.assertEqual(movie.title, "Arrival")
        self.assertEqual(movie.slug, "arrival")
        self.assertEqual(movie.duration_minutes, 116)
        self.assertIn("lingüista", movie.description)
        self.assertEqual(result.external_id, "329865")
        self.assertTrue(
            MovieExternalId.objects.filter(movie=movie, provider="tmdb", external_id="329865").exists()
        )
        self.assertEqual(
            list(CastMember.objects.filter(movie=movie).values_list("name", flat=True)),
            ["Amy Adams", "Jeremy Renner"],
        )

    def test_uses_provider_id_suffix_when_title_slug_already_exists(self):
        Movie.objects.create(title="Arrival", slug="arrival", duration_minutes=90)

        movie, _ = create_movie_from_provider("329865", provider=FakeProvider())

        self.assertEqual(movie.slug, "arrival-tmdb-329865")

    def test_refuses_to_create_duplicate_external_identity(self):
        movie = Movie.objects.create(title="Arrival", slug="arrival", duration_minutes=116)
        MovieExternalId.objects.create(movie=movie, provider="tmdb", external_id="329865")

        with self.assertRaises(ProviderError):
            create_movie_from_provider("329865", provider=FakeProvider())

        self.assertEqual(Movie.objects.count(), 1)
