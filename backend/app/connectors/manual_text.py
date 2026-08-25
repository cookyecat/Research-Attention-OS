from app.connectors.base import DiscoveredItem, ParsedSource, RawSource
from app.services.fingerprint import NormalizedSource, fingerprint as make_fingerprint


class ManualTextConnector:
    def discover(self, query_or_config) -> list[DiscoveredItem]:
        return []

    def fetch(self, item: DiscoveredItem) -> RawSource:
        return RawSource(payload=item.ref, content_type="text/plain", origin="manual", metadata={})

    def parse(self, raw: RawSource) -> ParsedSource:
        text = raw.payload.decode("utf-8") if isinstance(raw.payload, bytes) else raw.payload
        title = (raw.metadata or {}).get("title")
        return ParsedSource(title=title, text=text, metadata=dict(raw.metadata or {}), reference_candidates=[])

    def normalize(self, parsed: ParsedSource) -> NormalizedSource:
        return NormalizedSource(
            source_type="TEXT",
            title=parsed.title,
            content_text=parsed.text,
            author_entities=list(parsed.metadata.get("author_entities") or []),
            publisher=parsed.metadata.get("publisher"),
            language=parsed.metadata.get("language"),
            raw_metadata=parsed.metadata,
            ingestion_method="MANUAL_TEXT",
        )

    def fingerprint(self, normalized: NormalizedSource) -> str:
        return make_fingerprint(normalized)

    def ingest(self, text: str, title: str | None = None, **metadata) -> NormalizedSource:
        raw = RawSource(payload=text, content_type="text/plain", origin="manual", metadata={"title": title, **metadata})
        return self.normalize(self.parse(raw))
