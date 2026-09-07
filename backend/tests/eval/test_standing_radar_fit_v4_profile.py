from eval.live import standing_radar_fit_v3 as v3
from eval.live import standing_radar_fit_v4 as v4


def test_v4_changes_user_profile_not_d_semantic_prompt():
    assert v4.prompt_sha256() == v3.prompt_sha256()
    assert v4.ESTIMATOR_VERSION == "standing-radar-fit-estimator-v4"
    assert v4.PROFILE_ID == "standing-radar-profile-v4"


def test_v4_profile_contains_latest_user_clause_calibration():
    profile = v4.load_standing_radar_profile()
    text = v4.rendered if False else v3.render_profile_for_prompt(profile)
    assert "Ordinary internal catering" in text
    assert "power supply or grid constraints substantively coupled to AI/data-center compute capacity" in text
    assert "Ordinary furniture, room renovation" in text


def test_v4_invocation_records_profile_hash_separately():
    record = v4.invocation_record(
        requested_model="deepseek-v4-flash",
        provider_base_url="test",
        thinking_protocol=None,
    )
    assert record["prompt_sha256"] == v3.prompt_sha256()
    assert len(record["profile_sha256"]) == 64
    assert record["profile_id"] == "standing-radar-profile-v4"
