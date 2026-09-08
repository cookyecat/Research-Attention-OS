from __future__ import annotations

from dataclasses import dataclass
from typing import Any

SIMULATION_VERSION = "phase7b-dynamic-p-simulation-v0.1"


@dataclass(frozen=True)
class DynamicPStep:
    scenario_id: str
    step_id: str
    expected_p: str
    expected_action: str
    packet: dict[str, Any]


def _obs(kind: str, window: str, observation: str, source: str, observed_at: str,
         group: str, quality: str = "direct", contamination: list[str] | None = None) -> dict[str, Any]:
    return {
        "kind": kind,
        "window": window,
        "observation": observation,
        "source": source,
        "observed_at": observed_at,
        "independence_group": group,
        "quality": quality,
        "contamination": list(contamination or []),
    }
def _history(window: str, observation: str, source: str) -> dict[str, str]:
    return {"window": window, "observation": observation, "source": source}


def _packet(event_id: str, as_of: str, summary: str, constituency: dict[str, str],
            current: list[dict[str, Any]], history: list[dict[str, str]],
            checked: list[str], unavailable: list[str] | None = None) -> dict[str, Any]:
    return {
        "event": {"event_id": event_id, "as_of": as_of, "semantic_summary": summary},
        "constituency_prior": constituency,
        "collection_context": {
            "channels_checked": checked,
            "channels_unavailable": list(unavailable or []),
            "notes": "SIMULATED DEVELOPMENT EVIDENCE ONLY; not a claim about current real-world salience.",
        },
        "current_attention_evidence": current,
        "recent_attention_history": history,
    }


def _specialist_constituency() -> dict[str, str]:
    return {
        "description": "active embodied-agent and multi-agent benchmark researchers and engineers",
        "scope": "domain",
        "reference_scale": "10^4",
        "reference_size_hint": "unknown",
        "basis": "explicit_event_scope",
        "provenance": "simulated scenario definition fixed before attention observations",
    }
def specialist_attention_cycle() -> list[DynamicPStep]:
    event_id = "SIM-P-SPECIALIST-01"
    summary = "A new embodied-agent benchmark is released for multi-agent long-horizon task execution."
    c = _specialist_constituency()
    checked = ["specialist_forum", "field_search", "independent_labs"]
    steps: list[DynamicPStep] = []

    steps.append(DynamicPStep("specialist_cycle", "T0_QUIET", "NOT_SALIENT", "DROP", _packet(
        event_id, "2026-09-08T00:00:00Z", summary, c,
        [
            _obs("discussion", "6h", "Two isolated forum mentions; no sustained thread participation.", "sim-forum", "2026-09-08T00:00:00Z", "forum"),
            _obs("search", "6h", "Field-specific search interest remains near ordinary baseline.", "sim-search", "2026-09-08T00:00:00Z", "search"),
            _obs("institutional_followup", "6h", "No independent lab follow-up detected in checked channels.", "sim-labs", "2026-09-08T00:00:00Z", "labs", "structural"),
        ],
        [_history("previous 7d", "Comparable benchmark announcements usually remained at low baseline attention.", "sim-history")], checked,
    )))
    steps.append(DynamicPStep("specialist_cycle", "T1_FORMING", "SALIENT", "AWARE", _packet(
        event_id, "2026-09-08T06:00:00Z", summary, c,
        [
            _obs("discussion", "6h", "Independent specialist threads show sustained technical discussion across multiple subcommunities.", "sim-forum", "2026-09-08T06:00:00Z", "forum"),
            _obs("search", "6h", "Field-specific search activity is about six times the ordinary baseline and still rising.", "sim-search", "2026-09-08T06:00:00Z", "search"),
            _obs("institutional_followup", "6h", "Eight independent labs publicly inspect, reproduce, or reference the benchmark.", "sim-labs", "2026-09-08T06:00:00Z", "labs", "structural"),
        ],
        [_history("previous 6h", "Attention moved from isolated mentions to multi-channel specialist uptake.", "sim-history")], checked,
    )))

    steps.append(DynamicPStep("specialist_cycle", "T2_ESTABLISHED", "SALIENT", "AWARE", _packet(
        event_id, "2026-09-09T06:00:00Z", summary, c,
        [
            _obs("discussion", "24h", "Technical discussion is broad and sustained across the active specialist community.", "sim-forum", "2026-09-09T06:00:00Z", "forum"),
            _obs("search", "24h", "Search remains about five times baseline with repeated return visits.", "sim-search", "2026-09-09T06:00:00Z", "search"),
            _obs("institutional_followup", "24h", "Twenty independent labs or research groups have posted analyses or reproductions.", "sim-labs", "2026-09-09T06:00:00Z", "labs", "structural"),
        ],
        [_history("previous 24h", "Rapid formation was followed by sustained high specialist attention.", "sim-history")], checked,
    )))
    steps.append(DynamicPStep("specialist_cycle", "T3_SHORT_DECLINE", "SALIENT", "AWARE", _packet(
        event_id, "2026-09-10T06:00:00Z", summary, c,
        [
            _obs("discussion", "24h", "Discussion volume is down roughly 25% from yesterday but remains broad and technically active.", "sim-forum", "2026-09-10T06:00:00Z", "forum"),
            _obs("search", "24h", "Search is down from peak but remains about three times ordinary baseline.", "sim-search", "2026-09-10T06:00:00Z", "search"),
            _obs("institutional_followup", "24h", "Independent analyses continue to appear, though more slowly.", "sim-labs", "2026-09-10T06:00:00Z", "labs", "structural"),
        ],
        [
            _history("previous 48h", "The event reached established high specialist attention before the current short decline.", "sim-history"),
            _history("last 24h", "Current attention remains materially above ordinary baseline despite negative velocity.", "sim-history"),
        ], checked,
    )))

    steps.append(DynamicPStep("specialist_cycle", "T4_SUSTAINED_DECAY", "NOT_SALIENT", "DROP", _packet(
        event_id, "2026-09-22T06:00:00Z", summary, c,
        [
            _obs("discussion", "72h", "Checked specialist channels show only isolated references and no active discussion threads.", "sim-forum", "2026-09-22T06:00:00Z", "forum"),
            _obs("search", "72h", "Field-specific search has returned close to ordinary baseline.", "sim-search", "2026-09-22T06:00:00Z", "search"),
            _obs("institutional_followup", "72h", "No new independent lab follow-up appeared in the last three days.", "sim-labs", "2026-09-22T06:00:00Z", "labs", "structural"),
        ],
        [_history("previous 10d", "Attention decayed steadily from the earlier peak toward ordinary baseline across all checked channels.", "sim-history")], checked,
    )))
    steps.append(DynamicPStep("specialist_cycle", "T5_ORGANIC_REBOUND", "SALIENT", "AWARE", _packet(
        event_id, "2026-09-29T06:00:00Z", summary, c,
        [
            _obs("discussion", "12h", "A new benchmark result triggers renewed independent technical threads across the specialist community.", "sim-forum", "2026-09-29T06:00:00Z", "forum"),
            _obs("search", "12h", "Field-specific search rises to about five times baseline after the new result.", "sim-search", "2026-09-29T06:00:00Z", "search"),
            _obs("institutional_followup", "12h", "Twelve independent labs publish follow-up analyses or reproduction notes.", "sim-labs", "2026-09-29T06:00:00Z", "labs", "structural"),
        ],
        [
            _history("previous 10d", "The original attention state had decayed back toward baseline before the current rebound.", "sim-history"),
            _history("last 12h", "Renewed attention is independently visible across discussion, search, and institutional follow-up.", "sim-history"),
        ], checked,
    )))
    return steps


def _product_constituency() -> dict[str, str]:
    return {
        "description": "active users and evaluators of a newly launched AI application",
        "scope": "product",
        "reference_scale": "10^5",
        "reference_size_hint": "unknown",
        "basis": "explicit_event_scope",
        "provenance": "simulated scenario definition fixed before attention observations",
    }
def manipulated_to_organic_cycle() -> list[DynamicPStep]:
    event_id = "SIM-P-PRODUCT-01"
    summary = "A newly launched AI application begins a large promotional campaign."
    c = _product_constituency()
    checked = ["campaign_telemetry", "product_search", "independent_user_communities"]
    steps: list[DynamicPStep] = []

    steps.append(DynamicPStep("manipulated_to_organic", "T0_PAID_EXPOSURE", "NOT_SALIENT", "DROP", _packet(
        event_id, "2026-09-08T00:00:00Z", summary, c,
        [
            _obs("reach", "12h", "Two million paid impressions and 500,000 autoplay starts were delivered.", "sim-campaign", "2026-09-08T00:00:00Z", "campaign", "contaminated", ["paid", "forced_exposure"]),
            _obs("engagement", "12h", "Meaningful voluntary interactions remain very low relative to campaign reach.", "sim-community", "2026-09-08T00:00:00Z", "community", "direct"),
            _obs("search", "12h", "Product search remains near baseline despite promotional reach.", "sim-search", "2026-09-08T00:00:00Z", "search", "direct"),
        ],
        [_history("previous 7d", "No established organic attention state existed before the campaign.", "sim-history")], checked,
    )))

    steps.append(DynamicPStep("manipulated_to_organic", "T1_SYNTHETIC_TREND", "NOT_SALIENT", "DROP", _packet(
        event_id, "2026-09-08T12:00:00Z", summary, c,
        [
            _obs("reach", "12h", "Promotional reach remains very high.", "sim-campaign", "2026-09-08T12:00:00Z", "campaign", "contaminated", ["paid"]),
            _obs("trend_volume", "12h", "A large fraction of trend mentions are duplicated or bot-amplified.", "sim-trend", "2026-09-08T12:00:00Z", "trend", "contaminated", ["bot", "duplicate"]),
            _obs("search", "12h", "Independent product search remains only slightly above baseline.", "sim-search", "2026-09-08T12:00:00Z", "search"),
        ],
        [_history("previous 12h", "High exposure has not converted into broad voluntary attention.", "sim-history")], checked,
    )))
    steps.append(DynamicPStep("manipulated_to_organic", "T2_ORGANIC_FORMATION", "SALIENT", "AWARE", _packet(
        event_id, "2026-09-09T12:00:00Z", summary, c,
        [
            _obs("search", "24h", "Independent product search rises to about eight times baseline.", "sim-search", "2026-09-09T12:00:00Z", "search"),
            _obs("discussion", "24h", "Twenty independent user communities sustain substantive voluntary discussion.", "sim-community", "2026-09-09T12:00:00Z", "community"),
            _obs("meaningful_use", "24h", "Voluntary long-session use and repeat visits rise sharply independent of paid impressions.", "sim-product", "2026-09-09T12:00:00Z", "product", "structural"),
        ],
        [_history("previous 24h", "Attention shifted from paid exposure toward independent search, discussion, and meaningful use.", "sim-history")], checked,
    )))

    steps.append(DynamicPStep("manipulated_to_organic", "T3_ORGANIC_SUSTAINED", "SALIENT", "AWARE", _packet(
        event_id, "2026-09-11T12:00:00Z", summary, c,
        [
            _obs("search", "48h", "Independent search remains about six times baseline while paid spend declines.", "sim-search", "2026-09-11T12:00:00Z", "search"),
            _obs("discussion", "48h", "Substantive user discussion remains broad across independent communities.", "sim-community", "2026-09-11T12:00:00Z", "community"),
            _obs("meaningful_use", "48h", "Repeat voluntary use remains elevated after promotional reach declines.", "sim-product", "2026-09-11T12:00:00Z", "product", "structural"),
        ],
        [_history("previous 48h", "Organic attention remained established after formation and no longer depended on paid exposure.", "sim-history")], checked,
    )))
    return steps


def all_dynamic_p_steps() -> list[DynamicPStep]:
    return specialist_attention_cycle() + manipulated_to_organic_cycle()
