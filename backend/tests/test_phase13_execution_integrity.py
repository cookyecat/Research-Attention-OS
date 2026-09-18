from __future__ import annotations

from uuid import UUID

import pytest

from app.cognitive.rule_provider import RuleBasedCognitiveProvider
from app.models.analysis import AnalysisRun
from app.models.delivery import DeliveryEnvelope
from app.models.scheduler import AttentionPlan
from app.models.watch import Watch
from app.services.ingestion import ingest_text
from app.services.pipeline import run_pipeline
from app.services.scheduler import get_decision_strategy
from app.testing.kernel_fixture import seed_mvp_kernel


def _canonical_profile() -> dict:
    return {
        "profile_id": "research-dogfood-v1",
        "profile_version": 1,
        "execution_purpose": "CANONICAL",
        "authority": {
            "cognition_provider": "model",
            "cognition_contract": "research-aligned-v1",
            "decision_strategy_id": "pareto-multidelta-cardinal-free-effect-anchored-open-new",
            "decision_strategy_version": "pareto-multidelta-cardinal-free-effect-anchored-open-new-v0.2",
            "no_delta_awareness_contract": "dsp-v1",
        },
        "requirements": {"secrets": ["llm_api_key"]},
        "policy": {"canonical_attention_requires_attestation": True},
    }


def _set_canonical(monkeypatch, *, key: str | None = "test-key"):
    import app.execution_integrity as integrity

    monkeypatch.setattr(integrity, "runtime_profile", _canonical_profile())
    monkeypatch.setattr(integrity, "runtime_profile_path", "/test/research-dogfood-v1.yaml")
    monkeypatch.setattr(integrity.settings, "execution_purpose", "CANONICAL")
    monkeypatch.setattr(integrity.settings, "cognitive_provider", "model")
    monkeypatch.setattr(integrity.settings, "cognitive_contract", "research-aligned-v1")
    monkeypatch.setattr(integrity.settings, "decision_strategy_id", "pareto-multidelta-cardinal-free-effect-anchored-open-new")
    monkeypatch.setattr(integrity.settings, "no_delta_awareness_contract", "dsp-v1")
    monkeypatch.setattr(integrity.settings, "llm_api_key", key)
    return integrity


def test_canonical_missing_secret_degrades_without_legacy_fallback(monkeypatch):
    integrity = _set_canonical(monkeypatch, key=None)
    strategy = get_decision_strategy("pareto-multidelta-cardinal-free-effect-anchored-open-new")

    class ModelStub:
        provider_type = "model"

    health = integrity.execution_context(provider=ModelStub(), decision_strategy=strategy)
    assert health["attestation"]["status"] == "ATTESTED"
    assert health["capabilities"]["observation"] == "READY"
    assert health["capabilities"]["cognition"] == "BLOCKED"
    assert health["capabilities"]["attention"] == "BLOCKED"
    assert health["overall"] == "DEGRADED"
    assert health["authority"]["attention_authorized"] is False


def test_identity_mismatch_allows_forensic_cognition_but_no_attention_authority(db, monkeypatch):
    integrity = _set_canonical(monkeypatch, key="test-key")
    seed_mvp_kernel(db)
    source = ingest_text(
        db,
        "A technical note about local intelligence systems and communication rather than centralized control.",
        title="Phase13 quarantine probe",
    )
    legacy = get_decision_strategy("one-delta")
    provider = RuleBasedCognitiveProvider()

    result = run_pipeline(
        db,
        source.id,
        provider=provider,
        decision_strategy=legacy,
        allow_watch_creation=True,
        reprocess=True,
    )

    assert result["execution_authority"]["attestation"]["status"] == "FAILED"
    assert result["execution_authority"]["capabilities"]["cognition"] == "READY"
    assert result["execution_authority"]["authority"]["attention_authorized"] is False
    assert result["attention_plan"] is None
    assert result["disposition"] is None
    assert result["candidate_attention"]["disposition"] in {"DROP", "AWARE", "WATCH", "ENGAGE"}
    assert result["kernel_patches"] == []
    assert result["watches"] == []

    plans = db.query(AttentionPlan).filter(AttentionPlan.analysis_run_id == UUID(result["analysis_run"]["id"])).all()
    assert plans == []


def test_correct_canonical_identity_derives_attention_authority(monkeypatch):
    integrity = _set_canonical(monkeypatch, key="test-key")
    strategy = get_decision_strategy("pareto-multidelta-cardinal-free-effect-anchored-open-new")

    class ModelStub:
        provider_type = "model"

    context = integrity.execution_context(provider=ModelStub(), decision_strategy=strategy)
    assert context["attestation"]["status"] == "ATTESTED"
    assert context["capabilities"]["cognition"] == "READY"
    assert context["capabilities"]["attention"] == "READY"
    assert context["authority"]["attention_authorized"] is True
    assert context["overall"] == "READY"


def _set_no_profile(monkeypatch, purpose: str):
    import app.execution_integrity as integrity

    monkeypatch.setattr(integrity, "runtime_profile", None)
    monkeypatch.setattr(integrity, "runtime_profile_path", None)
    monkeypatch.setattr(integrity.settings, "execution_purpose", purpose)
    monkeypatch.setattr(integrity.settings, "cognitive_provider", "rule")
    monkeypatch.setattr(integrity.settings, "cognitive_contract", "legacy")
    monkeypatch.setattr(integrity.settings, "decision_strategy_id", "one-delta")
    monkeypatch.setattr(integrity.settings, "no_delta_awareness_contract", "disabled")
    return integrity


def test_compatibility_mode_is_forensic_not_authoritative(monkeypatch):
    integrity = _set_no_profile(monkeypatch, "COMPATIBILITY")
    context = integrity.execution_context(decision_strategy=get_decision_strategy("one-delta"))
    assert context["attestation"]["status"] == "UNATTESTED_COMPATIBILITY"
    assert context["attestation"]["enforced"] is True
    assert context["capabilities"]["cognition"] == "READY"
    assert context["capabilities"]["attention"] == "BLOCKED"
    assert context["authority"]["forensic_cognition_authorized"] is True
    assert context["authority"]["attention_authorized"] is False
    assert context["authority"]["side_effects_authorized"] is False
    assert context["overall"] == "FORENSIC"


def test_canonical_purpose_without_profile_is_blocked(monkeypatch):
    integrity = _set_no_profile(monkeypatch, "CANONICAL")
    context = integrity.execution_context(decision_strategy=get_decision_strategy("one-delta"))
    assert context["attestation"]["status"] == "MISSING_CANONICAL_IDENTITY"
    assert context["overall"] == "BLOCKED"
    assert context["capabilities"]["cognition"] == "BLOCKED"
    assert context["capabilities"]["attention"] == "BLOCKED"
    assert context["authority"]["side_effects_authorized"] is False


def test_missing_identity_fails_closed_before_analysis_run(db, monkeypatch):
    _set_no_profile(monkeypatch, "UNSPECIFIED")
    seed_mvp_kernel(db)
    source = ingest_text(db, "A technical note about embodied intelligence.", title="missing identity")

    with pytest.raises(RuntimeError, match="Cognition is not authorized"):
        run_pipeline(
            db,
            source.id,
            provider=RuleBasedCognitiveProvider(),
            decision_strategy=get_decision_strategy("one-delta"),
            reprocess=True,
        )

    assert db.query(AnalysisRun).filter(AnalysisRun.source_id == source.id).count() == 0
    assert db.query(AttentionPlan).filter(AttentionPlan.candidate_id == source.id).count() == 0


def test_explicit_replay_is_forensic_and_creates_no_side_effects(db, monkeypatch):
    integrity = _set_no_profile(monkeypatch, "REPLAY")
    seed_mvp_kernel(db)
    source = ingest_text(
        db,
        "A technical note about local intelligence systems and communication rather than centralized control.",
        title="replay forensic probe",
    )
    result = run_pipeline(
        db,
        source.id,
        provider=RuleBasedCognitiveProvider(),
        decision_strategy=get_decision_strategy("one-delta"),
        allow_watch_creation=True,
        reprocess=True,
    )

    authority = result["execution_authority"]
    assert authority["purpose"] == "REPLAY"
    assert authority["overall"] == "FORENSIC"
    assert authority["authority"]["forensic_cognition_authorized"] is True
    assert authority["authority"]["attention_authorized"] is False
    assert result["attention_plan"] is None
    assert result["candidate_attention"]["disposition"] in {"DROP", "AWARE", "WATCH", "ENGAGE"}
    run_id = UUID(result["analysis_run"]["id"])
    stored = db.get(AnalysisRun, run_id)
    assert integrity.stored_run_authority(stored)["authoritative"] is False
    assert db.query(AttentionPlan).filter(AttentionPlan.analysis_run_id == run_id).count() == 0
    assert db.query(Watch).filter(Watch.analysis_run_id == run_id).count() == 0
    assert db.query(DeliveryEnvelope).join(AttentionPlan, DeliveryEnvelope.attention_plan_id == AttentionPlan.id).filter(AttentionPlan.analysis_run_id == run_id).count() == 0


def test_reschedule_cannot_bypass_execution_authority(db, monkeypatch):
    from app.models.analysis import AnalysisRun
    from app.services.pipeline import _reschedule
    from app.services.scheduler import RuntimeView

    seed_mvp_kernel(db)
    source = ingest_text(db, "A technical paper about motor intelligence latency.", title="reschedule gate")
    first = run_pipeline(db, source.id)
    run = db.get(AnalysisRun, UUID(first["analysis_run"]["id"]))
    before = db.query(AttentionPlan).filter(AttentionPlan.analysis_run_id == run.id).count()
    assert before >= 1

    integrity = _set_no_profile(monkeypatch, "REPLAY")
    replay_context = integrity.execution_context(
        provider=RuleBasedCognitiveProvider(),
        decision_strategy=get_decision_strategy("one-delta"),
    )
    result = _reschedule(
        db,
        run,
        RuntimeView(current_task="forensic replay"),
        source,
        provider=RuleBasedCognitiveProvider(),
        decision_strategy=get_decision_strategy("one-delta"),
        execution_context=replay_context,
    )
    after = db.query(AttentionPlan).filter(AttentionPlan.analysis_run_id == run.id).count()
    assert after == before
    assert result["reschedule_suppressed"]["reason"] == "execution-authority-required"
