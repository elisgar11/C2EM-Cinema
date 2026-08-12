import json
import re
from decimal import Decimal, InvalidOperation
from urllib.error import HTTPError, URLError
from urllib.parse import quote, urlencode
from urllib.request import Request, urlopen

from django.conf import settings

from .base import CastCredit, MovieMetadata, MovieSearchResult, ProviderError


_QID_RE = re.compile(r"^Q\d+$")
_FILM_TYPE_TERMS = ("film", "movie", "película", "pelicula", "cinematographic")
_NON_FILM_TYPE_TERMS = ("film series", "movie series", "film franchise", "soundtrack", "album", "serie de películas")
_UNIT_MINUTES = {
    "Q11574": Decimal("0.0166666667"),  # second
    "Q7727": Decimal("1"),  # minute
    "Q25235": Decimal("60"),  # hour
}


class WikidataMovieMetadataProvider:
    """Public, keyless Wikidata fallback for basic film metadata."""

    name = "wikidata"
    api_base = "https://www.wikidata.org/w/api.php"
    commons_base = "https://commons.wikimedia.org/w/index.php"

    def is_configured(self) -> bool:
        return bool(getattr(settings, "WIKIDATA_ENABLED", True))

    @property
    def language(self) -> str:
        return str(getattr(settings, "WIKIDATA_LANGUAGE", "es")).strip() or "es"

    @property
    def fallback_language(self) -> str:
        return str(getattr(settings, "WIKIDATA_FALLBACK_LANGUAGE", "en")).strip() or "en"

    def _request_json(self, base_url: str, **params):
        query = urlencode({key: value for key, value in params.items() if value not in (None, "")})
        request = Request(
            f"{base_url}?{query}",
            headers={
                "Accept": "application/json",
                "User-Agent": str(getattr(settings, "WIKIDATA_USER_AGENT", "C2EM-Cinema/1.0")),
            },
        )
        timeout = float(getattr(settings, "WIKIDATA_TIMEOUT_SECONDS", 8))
        try:
            with urlopen(request, timeout=timeout) as response:
                return json.load(response)
        except HTTPError as exc:
            raise ProviderError(f"Wikidata respondió con HTTP {exc.code}.") from exc
        except URLError as exc:
            raise ProviderError(f"No se pudo conectar con Wikidata: {exc.reason}") from exc
        except (json.JSONDecodeError, ValueError) as exc:
            raise ProviderError("Wikidata devolvió una respuesta no válida.") from exc

    def _api(self, **params):
        return self._request_json(self.api_base, format="json", **params)

    def _get_entities(self, ids: list[str], *, props: str = "labels|descriptions|claims|sitelinks") -> dict:
        ids = [value for value in ids if _QID_RE.match(str(value))]
        if not ids:
            return {}
        languages = "|".join(dict.fromkeys([self.language, self.fallback_language]))
        data = self._api(
            action="wbgetentities",
            ids="|".join(ids),
            props=props,
            languages=languages,
            languagefallback=1,
        )
        return data.get("entities", {})

    @staticmethod
    def _ranked_claims(entity: dict, prop: str) -> list[dict]:
        claims = [claim for claim in entity.get("claims", {}).get(prop, []) if claim.get("rank") != "deprecated"]
        preferred = [claim for claim in claims if claim.get("rank") == "preferred"]
        return preferred or claims

    @staticmethod
    def _snak_value(snak: dict):
        if not snak or snak.get("snaktype") != "value":
            return None
        return snak.get("datavalue", {}).get("value")

    def _claim_values(self, entity: dict, prop: str) -> list:
        values = []
        for claim in self._ranked_claims(entity, prop):
            value = self._snak_value(claim.get("mainsnak", {}))
            if value is not None:
                values.append(value)
        return values

    @staticmethod
    def _entity_id(value) -> str:
        if isinstance(value, dict):
            return str(value.get("id") or "")
        return ""

    def _localized_value(self, values: dict) -> str:
        for language in (self.language, self.fallback_language):
            value = values.get(language, {}).get("value")
            if value:
                return str(value).strip()
        for value in values.values():
            text = value.get("value") if isinstance(value, dict) else None
            if text:
                return str(text).strip()
        return ""

    @staticmethod
    def _release_year(entity: dict) -> int | None:
        for claim in WikidataMovieMetadataProvider._ranked_claims(entity, "P577"):
            value = WikidataMovieMetadataProvider._snak_value(claim.get("mainsnak", {}))
            if not isinstance(value, dict):
                continue
            time_value = str(value.get("time") or "").lstrip("+")
            if len(time_value) >= 4 and time_value[:4].isdigit():
                return int(time_value[:4])
        return None

    @staticmethod
    def _duration_minutes(entity: dict) -> int | None:
        for value in [
            WikidataMovieMetadataProvider._snak_value(claim.get("mainsnak", {}))
            for claim in WikidataMovieMetadataProvider._ranked_claims(entity, "P2047")
        ]:
            if not isinstance(value, dict):
                continue
            unit_qid = str(value.get("unit") or "").rsplit("/", 1)[-1]
            multiplier = _UNIT_MINUTES.get(unit_qid)
            if multiplier is None:
                continue
            try:
                minutes = Decimal(str(value.get("amount"))) * multiplier
            except (InvalidOperation, TypeError, ValueError):
                continue
            rounded = int(minutes.to_integral_value())
            if rounded > 0:
                return rounded
        return None

    def _commons_url(self, filename: str, width: int) -> str:
        if not filename:
            return ""
        return f"{self.commons_base}?title=Special:Redirect/file/{quote(filename)}&width={int(width)}"

    def _poster_url(self, entity: dict, *, preview: bool) -> str:
        filenames = self._claim_values(entity, "P3383") or self._claim_values(entity, "P18")
        if not filenames:
            return ""
        width_setting = "WIKIDATA_POSTER_PREVIEW_WIDTH" if preview else "WIKIDATA_POSTER_WIDTH"
        default = 342 if preview else 780
        return self._commons_url(str(filenames[0]), int(getattr(settings, width_setting, default)))

    def _movie_ids(self, entities: dict) -> set[str]:
        type_ids = []
        item_types = {}
        for qid, entity in entities.items():
            current = []
            for value in self._claim_values(entity, "P31"):
                type_qid = self._entity_id(value)
                if type_qid:
                    current.append(type_qid)
                    type_ids.append(type_qid)
            item_types[qid] = current

        type_entities = self._get_entities(list(dict.fromkeys(type_ids)), props="labels|descriptions")
        movie_types = {"Q11424"}
        for qid, entity in type_entities.items():
            text = " ".join(
                filter(
                    None,
                    [
                        self._localized_value(entity.get("labels", {})),
                        self._localized_value(entity.get("descriptions", {})),
                    ],
                )
            ).casefold()
            if any(term in text for term in _NON_FILM_TYPE_TERMS):
                continue
            if any(term in text for term in _FILM_TYPE_TERMS):
                movie_types.add(qid)
        return {qid for qid, types in item_types.items() if any(value in movie_types for value in types)}

    def search(self, title: str, year: int | None = None) -> list[MovieSearchResult]:
        data = self._api(
            action="wbsearchentities",
            search=title,
            language=self.language,
            uselang=self.language,
            type="item",
            limit=10,
        )
        raw_results = data.get("search", [])
        if not raw_results and self.fallback_language != self.language:
            data = self._api(
                action="wbsearchentities",
                search=title,
                language=self.fallback_language,
                uselang=self.language,
                type="item",
                limit=10,
            )
            raw_results = data.get("search", [])

        qids = [str(item.get("id") or "") for item in raw_results if _QID_RE.match(str(item.get("id") or ""))]
        entities = self._get_entities(qids)
        allowed = self._movie_ids(entities)

        results = []
        for raw in raw_results:
            qid = str(raw.get("id") or "")
            entity = entities.get(qid)
            if not entity or qid not in allowed:
                continue
            release_year = self._release_year(entity)
            if year is not None and release_year is not None and release_year != year:
                continue
            results.append(
                MovieSearchResult(
                    provider=self.name,
                    external_id=qid,
                    title=self._localized_value(entity.get("labels", {})) or str(raw.get("label") or title).strip(),
                    release_year=release_year,
                    overview=self._localized_value(entity.get("descriptions", {})),
                    poster_url=self._poster_url(entity, preview=True),
                )
            )
        return results[:10]

    def _label_map(self, qids: list[str]) -> dict[str, str]:
        entities = self._get_entities(list(dict.fromkeys(qids)), props="labels")
        return {qid: self._localized_value(entity.get("labels", {})) for qid, entity in entities.items()}

    def _cast(self, entity: dict) -> tuple[CastCredit, ...]:
        max_cast = int(getattr(settings, "WIKIDATA_MAX_CAST_MEMBERS", 12))
        claims = self._ranked_claims(entity, "P161")[:max_cast]
        actor_ids = []
        role_ids = []
        prepared = []
        for order, claim in enumerate(claims):
            actor_id = self._entity_id(self._snak_value(claim.get("mainsnak", {})))
            if not actor_id:
                continue
            actor_ids.append(actor_id)
            qualifiers = claim.get("qualifiers", {})
            role_name = ""
            for qualifier in qualifiers.get("P4633", []):
                value = self._snak_value(qualifier)
                if isinstance(value, str) and value.strip():
                    role_name = value.strip()
                    break
            role_id = ""
            if not role_name:
                for qualifier in qualifiers.get("P453", []):
                    role_id = self._entity_id(self._snak_value(qualifier))
                    if role_id:
                        role_ids.append(role_id)
                        break
            prepared.append((order, actor_id, role_name, role_id))

        labels = self._label_map(actor_ids + role_ids)
        cast = []
        for order, actor_id, role_name, role_id in prepared:
            name = labels.get(actor_id, "").strip()
            if not name:
                continue
            cast.append(CastCredit(name=name, character=role_name or labels.get(role_id, "").strip(), order=order))
        return tuple(cast)

    def fetch(self, external_id: str) -> MovieMetadata:
        external_id = str(external_id).strip()
        if not _QID_RE.match(external_id):
            raise ProviderError(f"Identificador de Wikidata no válido: {external_id}")

        entity = self._get_entities([external_id]).get(external_id)
        if not entity or entity.get("missing") is not None:
            raise ProviderError(f"No existe la entidad Wikidata {external_id}.")

        return MovieMetadata(
            provider=self.name,
            external_id=external_id,
            title=self._localized_value(entity.get("labels", {})),
            overview=self._localized_value(entity.get("descriptions", {})),
            runtime_minutes=self._duration_minutes(entity),
            trailer_url="",
            poster_url=self._poster_url(entity, preview=False),
            backdrop_url="",
            cast=self._cast(entity),
        )
