from dataclasses import dataclass, field
from typing import Protocol


class ProviderError(RuntimeError):
    """Raised when an external metadata provider cannot satisfy a request."""


@dataclass(frozen=True)
class MovieSearchResult:
    provider: str
    external_id: str
    title: str
    release_year: int | None = None
    overview: str = ""


@dataclass(frozen=True)
class CastCredit:
    name: str
    character: str = ""
    order: int = 0


@dataclass(frozen=True)
class MovieMetadata:
    provider: str
    external_id: str
    title: str
    overview: str = ""
    runtime_minutes: int | None = None
    trailer_url: str = ""
    cast: tuple[CastCredit, ...] = field(default_factory=tuple)


class MovieMetadataProvider(Protocol):
    name: str

    def is_configured(self) -> bool: ...

    def search(self, title: str, year: int | None = None) -> list[MovieSearchResult]: ...

    def fetch(self, external_id: str) -> MovieMetadata: ...
