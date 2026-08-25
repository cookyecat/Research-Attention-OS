from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from app.services.fingerprint import NormalizedSource


@dataclass
class DiscoveredItem:
    ref: str
    metadata: dict


@dataclass
class RawSource:
    payload: bytes | str
    content_type: str
    origin: str
    metadata: dict


@dataclass
class ParsedSource:
    title: str | None
    text: str | None
    metadata: dict
    reference_candidates: list[dict]


class SourceConnector(Protocol):
    def discover(self, query_or_config) -> list[DiscoveredItem]: ...

    def fetch(self, item: DiscoveredItem) -> RawSource: ...

    def parse(self, raw: RawSource) -> ParsedSource: ...

    def normalize(self, parsed: ParsedSource) -> NormalizedSource: ...

    def fingerprint(self, normalized: NormalizedSource) -> str: ...
