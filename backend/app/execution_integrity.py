from __future__ import annotations

import hashlib
import json
import os
import subprocess
from functools import lru_cache
from pathlib import Path
from typing import Any

from app.config import runtime_profile, runtime_profile_path, settings

EXECUTION_INTEGRITY_VERSION = "execution-integrity-v0.2"


def _stable_hash(value: dict) -> str:
    body = json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True)
    return hashlib.sha256(body.encode("utf-8")).hexdigest()


def desired_identity() -> dict[str, Any] | None:
    if runtime_profile is None:
        return None
    authority = dict(runtime_profile.get("authority") or {})
    return {
        "profile_id": str(runtime_profile.get("profile_id")),
        "profile_version": runtime_profile.get("profile_version"),
        "execution_purpose": str(runtime_profile.get("execution_purpose") or settings.execution_purpose).upper(),
        "authority": {
            "cognition_provider": str(authority.get("cognition_provider") or ""),
            "cognition_contract": str(authority.get("cognition_contract") or ""),
            "decision_strategy_id": str(authority.get("decision_strategy_id") or ""),
            "decision_strategy_version": str(authority.get("decision_strategy_version") or ""),
            "no_delta_awareness_contract": str(authority.get("no_delta_awareness_contract") or ""),
        },
    }


def runtime_profile_hash() -> str | None:
    desired = desired_identity()
    return _stable_hash(desired) if desired is not None else None


@lru_cache(maxsize=1)
def build_identity() -> dict[str, Any]:
    repo = Path(__file__).resolve().parents[2]
    sha = None
    dirty = None
    try:
        sha = subprocess.check_output(["git", "-C", str(repo), "rev-parse", "HEAD"], text=True).strip()
        dirty = bool(subprocess.check_output(["git", "-C", str(repo), "status", "--porcelain"], text=True).strip())
    except Exception:
        pass
    return {"git_sha": sha, "dirty": dirty, "repo": str(repo)}


def _strategy_snapshot(decision_strategy=None) -> dict[str, Any]:
    from app.services.scheduler import decision_strategy_snapshot, get_decision_strategy

    strategy = decision_strategy or get_decision_strategy()
    return dict(decision_strategy_snapshot(strategy))


def resolved_identity(*, provider=None, decision_strategy=None) -> dict[str, Any]:
    provider_type = str(getattr(provider, "provider_type", None) or settings.cognitive_provider or "")
    strategy = _strategy_snapshot(decision_strategy)
    return {
        "cognition_provider": provider_type.split("+")[0],
        "cognition_contract": str(settings.cognitive_contract or ""),
        "decision_strategy_id": str(strategy.get("strategy_id") or ""),
        "decision_strategy_version": str(strategy.get("version") or ""),
        "no_delta_awareness_contract": str(settings.no_delta_awareness_contract or ""),
        "strategy_execution": strategy,
    }


def _execution_purpose(desired: dict[str, Any] | None = None) -> str:
    desired = desired if desired is not None else desired_identity()
    if desired is not None:
        return str(desired.get("execution_purpose") or "CANONICAL").upper()
    return str(settings.execution_purpose or "UNSPECIFIED").upper()


def attestation(*, provider=None, decision_strategy=None) -> dict[str, Any]:
    desired = desired_identity()
    resolved = resolved_identity(provider=provider, decision_strategy=decision_strategy)
    purpose = _execution_purpose(desired)
    if desired is None:
        if purpose == "CANONICAL":
            status = "MISSING_CANONICAL_IDENTITY"
            mismatches = [{"field": "runtime_profile", "expected": "explicit canonical profile", "actual": "missing"}]
        elif purpose in {"REPLAY", "FORENSIC", "COMPATIBILITY"}:
            status = f"UNATTESTED_{purpose}"
            mismatches = []
        else:
            status = "UNATTESTED_NO_IDENTITY"
            mismatches = []
        return {
            "status": status,
            "enforced": True,
            "mismatches": mismatches,
            "desired": None,
            "resolved": resolved,
            "purpose": purpose,
        }
    mismatches: list[dict[str, str]] = []
    expected = desired["authority"]
    for key in (
        "cognition_provider",
        "cognition_contract",
        "decision_strategy_id",
        "decision_strategy_version",
        "no_delta_awareness_contract",
    ):
        if str(expected.get(key) or "") != str(resolved.get(key) or ""):
            mismatches.append({"field": key, "expected": str(expected.get(key) or ""), "actual": str(resolved.get(key) or "")})
    status = "ATTESTED" if not mismatches else "FAILED"
    return {
        "status": status,
        "enforced": True,
        "mismatches": mismatches,
        "desired": desired,
        "resolved": resolved,
        "purpose": purpose,
    }


def capability_state(*, attested: dict | None = None) -> dict[str, Any]:
    attested = attested or attestation()
    purpose = str(attested.get("purpose") or _execution_purpose()).upper()
    required = list((runtime_profile or {}).get("requirements", {}).get("secrets", []) if runtime_profile else [])
    missing: list[str] = []
    for name in required:
        if name == "llm_api_key" and not settings.llm_api_key:
            missing.append(name)
        elif name != "llm_api_key" and not os.getenv(f"RAOS_{name.upper()}"):
            missing.append(name)

    technical_ready = not missing
    has_identity = attested.get("desired") is not None
    explicit_forensic = purpose in {"REPLAY", "FORENSIC", "COMPATIBILITY"}
    cognition_ready = technical_ready and (has_identity or explicit_forensic)

    profile_policy = dict((runtime_profile or {}).get("policy") or {}) if runtime_profile else {}
    purpose_allows_side_effects = purpose == "CANONICAL" or (
        purpose == "TEST" and profile_policy.get("allow_side_effects") is True
    )
    attention_ready = bool(
        technical_ready
        and has_identity
        and attested.get("status") == "ATTESTED"
        and purpose_allows_side_effects
    )
    return {
        "observation": "READY",
        "cognition": "READY" if cognition_ready else "BLOCKED",
        "attention": "READY" if attention_ready else "BLOCKED",
        "delivery": "READY",
        "forensic_cognition": "READY" if cognition_ready else "BLOCKED",
        "missing_requirements": missing,
    }


def execution_context(*, provider=None, decision_strategy=None) -> dict[str, Any]:
    attest = attestation(provider=provider, decision_strategy=decision_strategy)
    capabilities = capability_state(attested=attest)
    purpose = str(attest.get("purpose") or _execution_purpose()).upper()
    attention_authorized = capabilities.get("attention") == "READY"
    forensic_cognition_authorized = capabilities.get("cognition") == "READY"

    if purpose in {"REPLAY", "FORENSIC", "COMPATIBILITY"} and forensic_cognition_authorized:
        overall = "FORENSIC"
    elif attest.get("status") in {"FAILED", "MISSING_CANONICAL_IDENTITY", "UNATTESTED_NO_IDENTITY"}:
        overall = "BLOCKED"
    elif capabilities.get("cognition") != "READY":
        overall = "DEGRADED" if attest.get("status") == "ATTESTED" else "BLOCKED"
    elif capabilities.get("attention") != "READY":
        overall = "BLOCKED"
    else:
        overall = "READY"
    return {
        "version": EXECUTION_INTEGRITY_VERSION,
        "purpose": purpose,
        "runtime_profile_path": runtime_profile_path,
        "runtime_profile_hash": runtime_profile_hash(),
        "build": build_identity(),
        "attestation": attest,
        "capabilities": capabilities,
        "authority": {
            "forensic_cognition_authorized": forensic_cognition_authorized,
            "attention_authorized": attention_authorized,
            "side_effects_authorized": attention_authorized,
            "derivation": "explicit-purpose+identity+attestation+capability-readiness",
        },
        "overall": overall,
    }


def require_cognition_ready(*, provider=None, decision_strategy=None) -> dict[str, Any]:
    context = execution_context(provider=provider, decision_strategy=decision_strategy)
    if context["capabilities"].get("cognition") != "READY":
        missing = context["capabilities"].get("missing_requirements") or []
        status = str((context.get("attestation") or {}).get("status") or "UNKNOWN")
        purpose = str(context.get("purpose") or "UNSPECIFIED")
        detail = f" (missing: {', '.join(missing)})" if missing else ""
        raise RuntimeError(
            f"Cognition is not authorized for purpose={purpose}, attestation={status}; "
            "load an explicit runtime profile or explicitly select REPLAY/FORENSIC for non-authoritative computation"
            + detail
        )
    return context


def stored_run_authority(run) -> dict[str, Any]:
    """Evaluate whether a persisted historical AnalysisRun may back CURRENT Attention.

    Historical runs remain immutable forensic records. In canonical mode, only runs
    whose stored execution identity is compatible with the desired canonical identity
    may be projected into current Attention surfaces. Pre-Phase13 research-aligned
    runs are admitted by their persisted provider + decision-strategy provenance.
    """
    desired = desired_identity()
    if desired is None:
        return {"authoritative": False, "reason": "no-runtime-profile", "migration_attested": False}
    if str(desired.get("execution_purpose") or "CANONICAL").upper() not in {"CANONICAL", "TEST"}:
        return {"authoritative": False, "reason": "non-authoritative-execution-purpose", "migration_attested": False}

    payload = run.result_payload if isinstance(getattr(run, "result_payload", None), dict) else {}
    recorded = payload.get("execution_authority") if isinstance(payload, dict) else None
    current_hash = runtime_profile_hash()
    if isinstance(recorded, dict):
        recorded_hash = recorded.get("runtime_profile_hash")
        recorded_auth = (recorded.get("authority") or {}).get("attention_authorized") is True
        if recorded_hash == current_hash and recorded_auth:
            return {"authoritative": True, "reason": "phase13-attested", "migration_attested": False}

    authority = desired.get("authority") or {}
    execution = payload.get("execution_snapshot") if isinstance(payload, dict) else {}
    execution = execution if isinstance(execution, dict) else {}
    strategy = execution.get("decision_strategy") or {}
    if not isinstance(strategy, dict):
        strategy = {}
    if not strategy:
        stored_plan = payload.get("attention_plan") or {}
        debug = stored_plan.get("score_debug") if isinstance(stored_plan, dict) else {}
        strategy = (debug or {}).get("decision_strategy") or {}

    actual_provider = str(getattr(run, "provider_type", "") or "").split("+")[0]
    provider_ok = actual_provider == str(authority.get("cognition_provider") or "")
    strategy_ok = (
        str(strategy.get("strategy_id") or "") == str(authority.get("decision_strategy_id") or "")
        and str(strategy.get("version") or "") == str(authority.get("decision_strategy_version") or "")
    )
    desired_contract = str(authority.get("cognition_contract") or "")
    contract_snapshot = execution.get("cognition_contract") or {}
    contract_version = str(contract_snapshot.get("version") or "") if isinstance(contract_snapshot, dict) else ""
    if desired_contract == "research-aligned-v1":
        contract_ok = contract_version.startswith("research-aligned-cognition-v")
    else:
        contract_ok = True

    authoritative = bool(provider_ok and strategy_ok and contract_ok)
    return {
        "authoritative": authoritative,
        "reason": "pre-phase13-provenance-match" if authoritative else "execution-identity-mismatch",
        "migration_attested": authoritative,
        "stored": {
            "provider": actual_provider,
            "strategy_id": str(strategy.get("strategy_id") or ""),
            "strategy_version": str(strategy.get("version") or ""),
            "cognition_contract_version": contract_version,
        },
    }

def health_contract() -> dict[str, Any]:
    return execution_context()
