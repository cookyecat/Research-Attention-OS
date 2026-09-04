"""Product acceptance cases A–O from 07_MVP_ACCEPTANCE_TESTS.md."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from io import BytesIO

import pytest
from fastapi.testclient import TestClient

from app.cognitive.factory import FallbackProvider
from app.cognitive.model_provider import ModelBackedCognitiveProvider
from app.cognitive.rule_provider import RuleBasedCognitiveProvider
from tests.conftest import add_observation, add_text, analyze, kernel_index, matched_codes
from tests.fakes import SemanticFakeChat
from tests.pdf_util import pdf_with_text


@pytest.fixture
def semantic_fake_provider(monkeypatch):
    """Opt-in model-path double for Locate/prose. Domain matching stays in the test fake."""

    def _provider(**_kwargs):
        return FallbackProvider(
            ModelBackedCognitiveProvider(chat_fn=SemanticFakeChat()),
            RuleBasedCognitiveProvider(),
        )

    monkeypatch.setattr("app.cognitive.factory.get_provider", _provider)


CASE_A_ARTICLE = """
Galaxy General unveiled a WRC folding robot for embodied household work.
The company says the robot uses an agent brain.
The company claims the low-level system produces stable, continuous movement.
The low-level brain is described as producing stable, continuous motion during cloth folding.
"""

CASE_A_OBS = (
    "The demo contains repeated movement and pause phases. "
    "At WRC I saw repeated move-pause-move during folding."
)

CASE_B = """
SpaceClaw introduced WorldDreamer-Orbit. A shared world model coordinates multiple robotic units:
one world / one model / many bodies. This is a technical architecture claim about multi-agent
collective intelligence and reducing explicit communication.
OrbitBench will be released. First in-orbit validation is planned.
The company calls it a revolutionary seamless leap for swarm robotics.
"""

CASE_C_ARTICLE = """
The founder says: "End-to-end will eventually replace hierarchical architectures."
The startup trains a humanoid with a large unified model for motor control.
Editorial praise calls the demo inspiring and unprecedented.
"""

CASE_C_USER = (
    "High-frequency embodied control may face latency and energy costs if all signals traverse one large model."
)

CASE_D = """
A celebrity invested in a consumer beverage brand and retained minority equity
while remaining outside day-to-day employment. Ownership of shares did not imply
an operating role, and the employment relationship stayed separate from contractual
restrictions on the founder.
"""

CASE_E = """
A major company announces a minor model version with slightly better MMLU.
The release notes contain no architecture details and no bearing on active work.
"""

CASE_F_BODY = """
Acme Corp announces Model Z at a press event. The company said Model Z is available today.
"""

CASE_I = """
A high-quality technical paper on arXiv argues the opposite of the belief that large
unified models may be unsuitable for the fastest embodied-control loop.
It argues that large unified models are necessary for high-frequency embodied motor control
and reports latency measurements from a control architecture study.
"""

CASE_J = """
This foundational paper develops principles of temporal motor intelligence and embodied
control loops. It is a high-quality technical treatment of mechanism and architecture,
not a product announcement.
"""

CASE_K = """
A new paper highly overlaps the user's active submission on latency × energy evaluation
for high-frequency embodied motor control and may invalidate novelty of the current
camera-ready draft. The method is nearly identical to the active paper.
"""

CASE_L = """
A promising method for decentralized local intelligence in swarm robotics is described,
but evidence is insufficient: no paper release, no code release, no independent replication,
and no benchmark update yet.
"""

CASE_M = (
    "The founder says the robot generalizes zero-shot. In the video, it succeeds once. "
    "This probably means the system is robust."
)

CASE_N = """
Unlock a revolutionary seamless game-changing lifestyle robot. Reimagine delight.
No architecture, no measurements, no papers, no relation to any research question.
"""

CASE_O_NEWS = "Company X launches robot Y today at a product event in Shenzhen."

CASE_O_MODEL = (
    "Repeated evidence suggests semantic task intelligence and temporal motor intelligence scale differently."
)


def test_case_a_galaxy_general_wrc_folding(client: TestClient, semantic_fake_provider):
    index = kernel_index(client)
    src = add_text(client, CASE_A_ARTICLE, title="Galaxy General WRC folding robot")
    obs = add_observation(client, CASE_A_OBS, title="WRC demo observation")
    result = analyze(client, src["id"], extra_ids=[obs["id"]])

    claims = [c["text"].lower() for c in result["claims"]]
    assert any("continuous" in c and "movement" in c or "continuous" in c and "motion" in c for c in claims)
    observations = [o["text"].lower() for o in result["observations"]]
    assert any("pause" in o for o in observations)
    assert not any("closed-loop bandwidth is low" in o for o in observations)
    assert not any("bandwidth is low" in o for o in observations)

    stances = {(e["source_object_type"], e["stance"], e["target_object_type"]) for e in result["evidence_links"]}
    assert ("OBSERVATION", "WEAKENS", "CLAIM") in stances

    codes = matched_codes(result, index)
    assert {"P1", "BT1", "B1", "M1"} <= codes

    plan = result["attention_plan"]
    assert plan["disposition"] == "ENGAGE"
    assert result["features"]["sources_conflict"] is True
    assert result["features"]["evidence_links_present"] is True

    delta = " ".join(result["model_delta"]["distinctions"] + result["model_delta"]["what_could_change"]).lower()
    assert "cognitive" in delta and "motor" in delta

    b1 = client.get("/kernel").json()
    belief = next(n for nodes in b1.values() for n in nodes if n["id"] == index["B1"]["id"])
    assert belief["payload"]["confidence"] == 0.68
    assert belief["status"] == "ACTIVE"
    assert all(p["status"] == "PROPOSED" for p in result["kernel_patches"]) or result["kernel_patches"] == []


def test_case_b_spaceclaw_worlddreamer(client: TestClient, semantic_fake_provider):
    index = kernel_index(client)
    src = add_text(client, CASE_B, title="SpaceClaw WorldDreamer-Orbit")
    result = analyze(client, src["id"], persist_watches=True)
    sep = result["separations"]
    assert sep["future_plans"]
    assert any("orbitbench" in x.lower() and "will" in x.lower() for x in sep["future_plans"] + [c["text"] for c in result["claims"]])
    assert any(c["claim_type"] == "PREDICTIVE" for c in result["claims"])
    assert any(c["claim_type"] == "TECHNICAL" for c in result["claims"])
    assert any(c["claim_type"] == "PROMOTIONAL" for c in result["claims"])
    assert not any("orbitbench has been released" in c["text"].lower() for c in result["claims"])
    codes = matched_codes(result, index)
    assert {"P2", "Q2", "B2"} <= codes
    plan = result["attention_plan"]
    assert plan["disposition"] == "ENGAGE"
    refs = " ".join(
        (s["target_ref"].lower() + " " + s.get("created_reason", "").lower()) for s in result["watch_suggestions"]
    )
    if result["watch_suggestions"]:
        assert any(token in refs for token in ("paper", "code", "replication", "evidence"))


def test_case_c_end_to_end_startup(client: TestClient, semantic_fake_provider):
    index = kernel_index(client)
    article = add_text(client, CASE_C_ARTICLE, title="End-to-end humanoid startup")
    user = add_observation(client, CASE_C_USER, title="User counter-belief")
    result = analyze(client, article["id"], extra_ids=[user["id"]], persist_watches=True)
    attr = {(c["attribution_type"], c["text"].lower()) for c in result["claims"]}
    assert any(a == "FOUNDER" and "end-to-end" in t for a, t in attr)
    assert any(a == "USER" and "latency" in t for a, t in attr)
    codes = matched_codes(result, index)
    assert {"P1", "Q1", "B1"} <= codes
    plan = result["attention_plan"]
    assert plan["disposition"] == "ENGAGE"
    questions = " ".join(result["model_delta"]["questions"]).lower()
    assert "temporal" in questions or "layers" in questions
    assert "good/bad" not in questions
    watches = " ".join(s["target_ref"].lower() + s.get("created_reason", "").lower() for s in result["watch_suggestions"])
    assert "paper" in watches and "code" in watches


def test_case_d_structural_relevance_equity(client: TestClient, semantic_fake_provider):
    index = kernel_index(client)
    src = add_text(client, CASE_D, title="Celebrity minority equity in a consumer brand")
    result = analyze(client, src["id"])
    features = result["features"]
    assert features["topic_relevance"] <= 0.35
    assert features["structural_relevance"] >= 0.65
    assert features["decision_relevance"] >= 0.65
    assert "D1" in matched_codes(result, index)
    plan = result["attention_plan"]
    assert plan["disposition"] != "DROP"
    assert plan["disposition"] in {"ENGAGE", "AWARE"}
    if plan["disposition"] == "ENGAGE":
        assert plan["expected_output"] == "DECISION_REVIEW"
    joined = " ".join(result["model_delta"]["distinctions"]).lower()
    assert "equity" in joined and "employment" in joined


def test_case_e_generic_ai_news(client: TestClient):
    src = add_text(client, CASE_E, title="Minor model version")
    result = analyze(client, src["id"])
    assert result["attention_plan"]["disposition"] in {"AWARE", "DROP"}
    assert result["attention_plan"]["disposition"] != "ENGAGE"


def test_case_f_duplicate_media_coverage(client: TestClient):
    ids = []
    for i in range(5):
        src = add_text(client, CASE_F_BODY, title="Acme Corp announces Model Z")
        ids.append(src["id"])
    results = [analyze(client, sid) for sid in ids]
    listed = client.get("/sources").json()
    assert len(listed) >= 5
    events = {r["attention_plan"]["score_debug"]["independence"]["independent_sources"] for r in results}
    # After linking, later items should see a single independent source.
    last_ind = results[-1]["features"]["independent_source_count"]
    assert last_ind == 1
    high = [r for r in results if r["attention_plan"]["disposition"] == "ENGAGE"]
    assert len(high) <= 1
    drop_dup = [r for r in results if r["attention_plan"]["disposition"] == "DROP"]
    assert len(drop_dup) >= 3
    graph = client.get(f"/sources/{ids[1]}/graph").json()
    assert graph["independence"]["independent_sources"] == 1
    assert graph["independence"]["secondary_reports"] >= 1


def test_case_g_paper_references(client: TestClient):
    existing_doi = add_text(client, "Prior work on motor primitives.", title="Motor primitives")
    # stamp DOI fingerprint by creating a stub-like source via PDF refs matching
    from app.services.fingerprint import NormalizedSource, fingerprint
    from app.models.source import Source

    refs = []
    refs.append("[1] Smith J. Motor primitives for embodied control. arXiv:2301.00001, 2023.")
    refs.append("[2] Lee A. Latency-energy tradeoffs. doi:10.1234/motor.latency.2022.")
    for i in range(3, 21):
        refs.append(f"[{i}] Author{i}. Unrelated paper title number {i}. Journal {i}, 2020.")
    body = (
        "Temporal Motor Evaluation in High-Frequency Embodied Control\n\n"
        "Abstract. We study latency and energy in motor intelligence.\n\n"
        "References\n" + "\n".join(refs)
    )
    pdf = pdf_with_text(body.splitlines())
    r = client.post("/sources/pdf", files={"file": ("paper.pdf", pdf, "application/pdf")})
    assert r.status_code == 200, r.text
    paper = r.json()
    assert paper["source_type"] in {"PAPER", "PDF"}
    resolved = client.post(f"/sources/{paper['id']}/resolve-references").json()
    refs_out = client.get(f"/sources/{paper['id']}/references").json()
    assert refs_out["count"] >= 20
    stubs = [x for x in refs_out["references"] if x["stub"]]
    assert stubs
    dois = [x for x in refs_out["references"] if x.get("doi")]
    arxivs = [x for x in refs_out["references"] if x.get("arxiv_id")]
    assert dois and arxivs
    graph = client.get(f"/sources/{paper['id']}/graph").json()
    assert any(e["relationship"] == "CITES" for e in graph["outgoing"])
    stub_id = stubs[0]["target_id"]
    stub_graph = client.get(f"/sources/{stub_id}/graph").json()
    assert stub_graph["outgoing"] == []
    from app.services.source_graph import resolve_references

    with pytest.raises(ValueError, match="depth-2"):
        resolve_references(None, paper["id"], max_depth=2)  # type: ignore[arg-type]


def test_case_h_kernel_mutation_protection(client: TestClient):
    index = kernel_index(client)
    src = add_text(client, CASE_I, title="Conflict with B1")
    result = analyze(client, src["id"])
    assert result["kernel_patches"]
    patch = result["kernel_patches"][0]
    assert patch["status"] == "PROPOSED"
    b1 = next(n for nodes in client.get("/kernel").json().values() for n in nodes if n["id"] == index["B1"]["id"])
    assert b1["payload"]["confidence"] == 0.68
    assert b1["current_version"] == 1
    accepted = client.post(f"/kernel/patches/{patch['id']}/accept")
    assert accepted.status_code == 200, accepted.text
    b1b = next(n for nodes in client.get("/kernel").json().values() for n in nodes if n["id"] == index["B1"]["id"])
    assert b1b["current_version"] == 2
    versions = client.get(f"/kernel/nodes/{index['B1']['id']}/versions").json()
    assert len(versions) >= 2


def test_case_i_disagreement_not_filtered(client: TestClient):
    src = add_text(client, CASE_I, title="Opposite of B1")
    result = analyze(client, src["id"])
    plan = result["attention_plan"]
    assert plan["disposition"] == "ENGAGE"
    assert plan["disposition"] != "DROP"
    assert "disagreement" in plan["reason"].lower() or "verif" in plan["reason"].lower()


def test_case_j_runtime_context_changes_route(client: TestClient, semantic_fake_provider):
    src = add_text(client, CASE_J, title="Foundational embodied control paper")
    open_ctx = client.post(
        "/scheduler/plan",
        json={
            "source_id": src["id"],
            "runtime_context": {
                "current_task": "reading",
                "interruptibility": "HIGH",
                "cognitive_capacity": "HIGH",
            },
        },
    )
    assert open_ctx.status_code == 200, open_ctx.text
    plan1 = open_ctx.json()["attention_plan"]
    assert plan1["disposition"] == "ENGAGE"

    deadline = (datetime.now(timezone.utc) + timedelta(hours=2)).isoformat()
    tight = client.post(
        "/scheduler/plan",
        json={
            "source_id": src["id"],
            "runtime_context": {
                "current_task": "camera-ready",
                "interruptibility": "LOW",
                "cognitive_capacity": "LOW",
                "deadline_at": deadline,
            },
        },
    )
    assert tight.status_code == 200, tight.text
    plan2 = tight.json()["attention_plan"]
    assert plan2["disposition"] in {"WATCH", "DROP"} or plan2["urgency"] == "BACKGROUND"
    assert plan2["urgency"] in {"BACKGROUND", "NORMAL"}
    assert plan2["urgency"] != "PREEMPT"


def test_case_k_preempt(client: TestClient):
    src = add_text(client, CASE_K, title="Novelty collision paper")
    result = analyze(client, src["id"])
    plan = result["attention_plan"]
    assert plan["disposition"] == "ENGAGE"
    assert plan["urgency"] == "PREEMPT"
    assert "interrupt" in plan["reason"].lower() or "preempt" in plan["reason"].lower()


def test_case_l_watch_is_not_bookmark(client: TestClient):
    src = add_text(client, CASE_L, title="Promising method, thin evidence")
    created = client.post(
        "/watches",
        json={
            "target_type": "METHOD",
            "target_ref": "decentralized local intelligence method",
            "created_reason": "You do not need to remember to come back.",
            "triggers": ["PAPER_RELEASE", "CODE_RELEASE", "INDEPENDENT_REPLICATION", "BENCHMARK_UPDATE"],
        },
    )
    assert created.status_code == 200, created.text
    watch = created.json()
    assert watch["status"] == "ACTIVE"
    types = {t["trigger_type"] for t in watch["triggers"]}
    assert {"PAPER_RELEASE", "CODE_RELEASE", "INDEPENDENT_REPLICATION", "BENCHMARK_UPDATE"} <= types
    listed = client.get("/watches").json()
    assert any(w["id"] == watch["id"] for w in listed)
    fire = client.post(
        f"/watches/{watch['id']}/triggers/{watch['triggers'][0]['id']}/fire",
        params={"source_id": src["id"]},
    )
    assert fire.status_code == 200, fire.text
    body = fire.json()
    assert body["analysis"]["attention_plan"]["disposition"] in {"ENGAGE", "WATCH", "AWARE"}
    if body["analysis"]["attention_plan"]["disposition"] == "ENGAGE":
        assert body["watch"]["status"] == "PROMOTED"


def test_case_m_claim_observation_inference(client: TestClient):
    src = add_text(client, CASE_M, title="Zero-shot demo paragraph")
    result = analyze(client, src["id"])
    claims = " ".join(c["text"].lower() for c in result["claims"])
    obs = " ".join(o["text"].lower() for o in result["observations"])
    inf = " ".join(i["text"].lower() for i in result["inferences"])
    assert "zero-shot" in claims
    assert "succeeds once" in obs or "one successful" in obs
    assert "robust" in claims or "probably" in claims
    assert "robust" not in obs
    assert not any("robust" in o["text"].lower() for o in result["observations"])
    assert not any("probably means the system is robust" in i["text"].lower() for i in result["inferences"])


def test_case_n_promotional_drop(client: TestClient):
    src = add_text(client, CASE_N, title="Lifestyle robot ad")
    result = analyze(client, src["id"])
    assert result["attention_plan"]["disposition"] == "DROP"
    got = client.get(f"/sources/{src['id']}")
    assert got.status_code == 200
    assert got.json()["id"] == src["id"]


def test_case_o_kernel_admission_rule(client: TestClient):
    news = add_text(client, CASE_O_NEWS, title="Company X launches robot Y")
    news_result = analyze(client, news["id"])
    assert news_result["kernel_patches"] == []
    before = client.get("/kernel").json()
    count_before = sum(len(v) for v in before.values())

    model = add_text(client, CASE_O_MODEL, title="Scaling distinction")
    model_result = analyze(client, model["id"])
    assert model_result["kernel_patches"]
    assert any(p["target_object_type"] in {"BELIEF", "MODEL"} and p["status"] == "PROPOSED" for p in model_result["kernel_patches"])
    after = client.get("/kernel").json()
    assert sum(len(v) for v in after.values()) == count_before


def test_end_to_end_happy_path_accept(client: TestClient, semantic_fake_provider):
    index = kernel_index(client)
    src = add_text(client, CASE_A_ARTICLE, title="Slice source")
    obs = add_observation(client, CASE_A_OBS)
    result = analyze(client, src["id"], extra_ids=[obs["id"]])
    assert result["claims"] and result["observations"]
    assert result["kernel_matches"]
    assert result["attention_plan"]
    assert result["model_delta"]
    revise = next(
        (
            p
            for p in result["kernel_patches"]
            if p.get("change_type") == "REVISE" and p.get("target_object_id")
        ),
        None,
    )
    if revise:
        patch_id = revise["id"]
        target_id = revise["target_object_id"]
    else:
        created = client.post(
            "/kernel/patches",
            json={
                "target_object_type": "BELIEF",
                "target_object_id": index["B1"]["id"],
                "change_type": "REVISE",
                "current_state": index["B1"],
                "proposed_state": {
                    "title": index["B1"]["title"],
                    "status": "CONTESTED",
                    "payload": {**index["B1"]["payload"], "status": "CONTESTED"},
                },
                "reasoning": "Human-confirmable proposal from the vertical slice.",
            },
        )
        assert created.status_code == 200
        patch_id = created.json()["id"]
        target_id = index["B1"]["id"]
    acc = client.post(f"/kernel/patches/{patch_id}/accept")
    assert acc.status_code == 200
    assert acc.json()["status"] == "ACCEPTED"
    node = next(n for nodes in client.get("/kernel").json().values() for n in nodes if n["id"] == target_id)
    assert node["current_version"] >= 2
