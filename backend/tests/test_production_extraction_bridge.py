from __future__ import annotations

from app.cognitive.rule_provider import RuleBasedCognitiveProvider
from app.enums import AttributionType, ClaimType
from app.services.extraction import ExtractedClaim, ExtractionResult
from app.services.extraction_bridge import ExtractionBridgeResult
from app.services.ingestion import ingest_text
from app.services.pipeline import run_pipeline
from app.testing.kernel_fixture import seed_mvp_kernel


class SpyRuleProvider(RuleBasedCognitiveProvider):
    def __init__(self):
        self.extract_calls = 0
        self.reason_calls = 0

    def extract_information(self, *args, **kwargs):
        self.extract_calls += 1
        return super().extract_information(*args, **kwargs)

    def reason_evidence(self, extraction, **kwargs):
        self.reason_calls += 1
        return super().reason_evidence(extraction, **kwargs)


class FixedBridge:
    def execution_snapshot(self):
        return {"bridge_version": "test-fixed-bridge-v1", "sensor": "fixture"}

    def extract(self, source, extra_sources):
        assert extra_sources == []
        extraction = ExtractionResult(
            claims=[
                ExtractedClaim(
                    text="Shared world models can reduce explicit multi-agent communication.",
                    claim_type=ClaimType.FACTUAL,
                    attributed_to="source",
                    attribution_type=AttributionType.UNKNOWN,
                    confidence_extraction=0.9,
                    temporal_status="CURRENT",
                    source_span_text="shared world model evidence",
                )
            ],
            event_summary="Shared world models reduce explicit multi-agent communication.",
            evidence_maturity=0.35,
        )
        return ExtractionBridgeResult(
            extraction=extraction,
            diagnostics={"admitted_units": 1, "fixture": True},
        )


def test_default_pipeline_keeps_legacy_extraction_path(db):
    seed_mvp_kernel(db)
    source = ingest_text(db, "A neutral source sentence.", title="legacy path")
    provider = SpyRuleProvider()

    result = run_pipeline(db, source.id, provider=provider, allow_watch_creation=False)

    assert provider.extract_calls == 1
    assert provider.reason_calls == 1
    assert result["extraction_path"] == {
        "mode": "legacy",
        "bridge_execution": None,
        "diagnostics": {"mode": "legacy"},
    }
    assert "extraction_bridge" not in result["execution_snapshot"]


def test_bridge_bypasses_legacy_extraction_but_keeps_production_downstream(db):
    seed_mvp_kernel(db)
    source = ingest_text(db, "Raw text intentionally does not contain the bridge claim.", title="bridge path")
    provider = SpyRuleProvider()
    bridge = FixedBridge()

    result = run_pipeline(
        db,
        source.id,
        provider=provider,
        extraction_bridge=bridge,
        allow_watch_creation=False,
    )

    assert provider.extract_calls == 0
    assert provider.reason_calls == 0
    assert [row["text"] for row in result["claims"]] == [
        "Shared world models can reduce explicit multi-agent communication."
    ]
    assert result["extraction_path"]["mode"] == "bridge"
    assert result["extraction_path"]["diagnostics"]["admitted_units"] == 1
    assert result["execution_snapshot"]["extraction_bridge"] == bridge.execution_snapshot()
    assert result["analysis_run"]["identity_key"]
    assert result["kernel_matches"]  # production Locate executed on the bridged representation


def test_bridge_execution_fingerprint_changes_analysis_identity(db):
    seed_mvp_kernel(db)
    source_a = ingest_text(db, "Same semantic input.", title="identity A")
    source_b = ingest_text(db, "Same semantic input.", title="identity B")
    provider_a = SpyRuleProvider()
    provider_b = SpyRuleProvider()

    legacy = run_pipeline(db, source_a.id, provider=provider_a, allow_watch_creation=False)
    bridged = run_pipeline(
        db,
        source_b.id,
        provider=provider_b,
        extraction_bridge=FixedBridge(),
        allow_watch_creation=False,
    )

    assert legacy["execution_digest"] != bridged["execution_digest"]
    assert "extraction_bridge" not in legacy["execution_snapshot"]
    assert bridged["execution_snapshot"]["extraction_bridge"]["bridge_version"] == "test-fixed-bridge-v1"


class RequiresAuditedProvider(SpyRuleProvider):
    requires_audited_semantics = True


def test_research_aligned_provider_auto_installs_audited_bridge(db, monkeypatch):
    seed_mvp_kernel(db)
    source = ingest_text(db, "Raw text should not hit legacy extraction.", title="auto bridge")
    provider = RequiresAuditedProvider()
    bridge = FixedBridge()
    monkeypatch.setattr(
        "app.services.extraction_bridge.research_aligned_extraction_bridge",
        lambda: bridge,
    )

    result = run_pipeline(db, source.id, provider=provider, allow_watch_creation=False)

    assert provider.extract_calls == 0
    assert provider.reason_calls == 0
    assert result["extraction_path"]["mode"] == "bridge"
    assert result["execution_snapshot"]["extraction_bridge"] == bridge.execution_snapshot()
    provenance = result["impact_input"]["extraction"]["analysis_provenance"]
    assert provenance["primary_source_id"] == str(source.id)
    assert provenance["independent_source_ids"] == [str(source.id)]
