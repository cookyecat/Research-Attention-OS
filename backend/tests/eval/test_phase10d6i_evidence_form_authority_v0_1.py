import json
from pathlib import Path

from eval.live.phase10d6i_evidence_form_classifier_v0_1 import EvidenceClassificationResponse, SYSTEM_PROMPT
from eval.live.run_phase10d6i_evidence_form_authority_v0_1 import REPEATS, materialize_items, validate_run

ROOT=Path(__file__).resolve().parents[3]

def test_reference_has_frozen_two_axis_labels():
    ref=json.loads((ROOT/'eval/live/phase10d6i_evidence_form_reference_v0_1.json').read_text())
    assert len(ref['items'])==18
    assert all(x['provenance_role'] and x['evidence_form'] for x in ref['items'])


def test_classifier_contract_has_no_cardinal_authority_fields():
    schema=json.dumps(EvidenceClassificationResponse.model_json_schema())
    for forbidden in ('change_magnitude','target_importance','epistemic_strength','confidence'):
        assert forbidden not in schema
    assert 'Attention' not in SYSTEM_PROMPT or 'NOT' in SYSTEM_PROMPT


def test_materialized_ids_are_complete():
    ref=json.loads((ROOT/'eval/live/phase10d6i_evidence_form_reference_v0_1.json').read_text())
    items=materialize_items(ref); ids=[x['item_id'] for x in items]
    assert len(ids)==18 and len(set(ids))==18
    class X:
        def __init__(self,item_id): self.item_id=item_id
    parsed=type('P',(),{'classifications':[X(i) for i in ids]})()
    assert validate_run(parsed,ids)==(True,None)
    assert REPEATS==6
