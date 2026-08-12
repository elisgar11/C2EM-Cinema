from unittest.mock import patch

from django.test import TestCase, override_settings

from catalog.providers import TmdbMovieMetadataProvider, WikidataMovieMetadataProvider
from catalog.services import get_movie_metadata_provider


def entity_claim(value, *, qualifiers=None, rank="normal"):
    return {
        "rank": rank,
        "mainsnak": {"snaktype": "value", "datavalue": {"value": value}},
        "qualifiers": qualifiers or {},
    }


def entity_value(qid):
    return {"entity-type": "item", "id": qid, "numeric-id": int(qid[1:])}


class MetadataProviderFallbackTests(TestCase):
    @override_settings(
        MOVIE_METADATA_PROVIDER="tmdb",
        MOVIE_METADATA_FALLBACK_PROVIDER="wikidata",
        TMDB_API_TOKEN="",
        WIKIDATA_ENABLED=True,
    )
    def test_wikidata_is_used_when_tmdb_has_no_token(self):
        provider = get_movie_metadata_provider()
        self.assertIsInstance(provider, WikidataMovieMetadataProvider)
        self.assertEqual(provider.name, "wikidata")

    @override_settings(
        MOVIE_METADATA_PROVIDER="tmdb",
        MOVIE_METADATA_FALLBACK_PROVIDER="wikidata",
        TMDB_API_TOKEN="configured-token",
        WIKIDATA_ENABLED=True,
    )
    def test_tmdb_remains_primary_when_token_exists(self):
        provider = get_movie_metadata_provider()
        self.assertIsInstance(provider, TmdbMovieMetadataProvider)
        self.assertEqual(provider.name, "tmdb")


@override_settings(
    WIKIDATA_ENABLED=True,
    WIKIDATA_LANGUAGE="es",
    WIKIDATA_FALLBACK_LANGUAGE="en",
    WIKIDATA_MAX_CAST_MEMBERS="12",
    WIKIDATA_POSTER_PREVIEW_WIDTH="342",
    WIKIDATA_POSTER_WIDTH="780",
)
class WikidataProviderTests(TestCase):
    def setUp(self):
        self.provider = WikidataMovieMetadataProvider()

    def test_search_keeps_films_and_uses_release_year_and_poster(self):
        raw_search = {
            "search": [
                {"id": "Q100", "label": "Dune", "description": "película de 2021"},
                {"id": "Q200", "label": "Dune", "description": "novela"},
            ]
        }
        entities = {
            "Q100": {
                "labels": {"es": {"value": "Dune"}},
                "descriptions": {"es": {"value": "película de ciencia ficción de 2021"}},
                "claims": {
                    "P31": [entity_claim(entity_value("Q11424"))],
                    "P577": [entity_claim({"time": "+2021-09-03T00:00:00Z"})],
                    "P18": [entity_claim("Dune (2021 film).jpg")],
                },
            },
            "Q200": {
                "labels": {"es": {"value": "Dune"}},
                "descriptions": {"es": {"value": "novela de Frank Herbert"}},
                "claims": {"P31": [entity_claim(entity_value("Q571"))]},
            },
        }
        type_entities = {
            "Q11424": {"labels": {"es": {"value": "película"}}, "descriptions": {}},
            "Q571": {"labels": {"es": {"value": "libro"}}, "descriptions": {}},
        }

        with patch.object(self.provider, "_api", return_value=raw_search), patch.object(
            self.provider,
            "_get_entities",
            side_effect=[entities, type_entities],
        ):
            results = self.provider.search("Dune", year=2021)

        self.assertEqual(len(results), 1)
        self.assertEqual(results[0].external_id, "Q100")
        self.assertEqual(results[0].release_year, 2021)
        self.assertEqual(results[0].overview, "película de ciencia ficción de 2021")
        self.assertIn("title=Special:Redirect/file/", results[0].poster_url)
        self.assertIn("width=342", results[0].poster_url)

    def test_fetch_maps_description_runtime_cast_roles_and_commons_poster(self):
        movie = {
            "labels": {"es": {"value": "Arrival"}},
            "descriptions": {"es": {"value": "película de ciencia ficción de 2016"}},
            "claims": {
                "P2047": [
                    entity_claim(
                        {
                            "amount": "+116",
                            "unit": "http://www.wikidata.org/entity/Q7727",
                        }
                    )
                ],
                "P18": [entity_claim("Arrival, Movie Poster.jpg")],
                "P161": [
                    entity_claim(
                        entity_value("Q10"),
                        qualifiers={
                            "P4633": [
                                {"snaktype": "value", "datavalue": {"value": "Louise Banks"}}
                            ]
                        },
                    ),
                    entity_claim(
                        entity_value("Q11"),
                        qualifiers={
                            "P453": [
                                {"snaktype": "value", "datavalue": {"value": entity_value("Q12")}}
                            ]
                        },
                    ),
                ],
            },
        }
        labels = {
            "Q10": {"labels": {"es": {"value": "Amy Adams"}}},
            "Q11": {"labels": {"es": {"value": "Jeremy Renner"}}},
            "Q12": {"labels": {"es": {"value": "Ian Donnelly"}}},
        }

        with patch.object(
            self.provider,
            "_get_entities",
            side_effect=[{"Q999": movie}, labels],
        ):
            metadata = self.provider.fetch("Q999")

        self.assertEqual(metadata.provider, "wikidata")
        self.assertEqual(metadata.external_id, "Q999")
        self.assertEqual(metadata.title, "Arrival")
        self.assertEqual(metadata.overview, "película de ciencia ficción de 2016")
        self.assertEqual(metadata.runtime_minutes, 116)
        self.assertEqual([credit.name for credit in metadata.cast], ["Amy Adams", "Jeremy Renner"])
        self.assertEqual([credit.character for credit in metadata.cast], ["Louise Banks", "Ian Donnelly"])
        self.assertIn("Arrival%2C%20Movie%20Poster.jpg", metadata.poster_url)
        self.assertIn("width=780", metadata.poster_url)
        self.assertEqual(metadata.backdrop_url, "")
