import json
from pathlib import Path
from eval.live.phase10d6i1_compositional_evidence_classifier_v0_1 import CompositionalEvidenceResponse,SYSTEM_PROMPT
from eval.live.run_phase10d6i1_compositional_evidence_form_holdout_v0_1 import REPEATS,materialize,jaccard
ROOT=Path(__file__).resolve().parents[3]
def test_holdout_is_fresh_and_compositional():
 ref=json.loads((ROOT/'eval/live/phase10d6i1_compositional_evidence_form_holdout_v0_1.json').read_text()); old=json.loads((ROOT/'eval/live/phase10d6i_evidence_form_reference_v0_1.json').read_text())
 assert len(ref['items'])==20
 assert not ({(x['case'],x['unit_id']) for x in ref['items']} & {(x['case'],x['unit_id']) for x in old['items']})
 assert any(len(x['evidence_forms'])>1 for x in ref['items'])
def test_schema_has_no_cardinal_authority():
 s=json.dumps(CompositionalEvidenceResponse.model_json_schema())
 for x in ('change_magnitude','target_importance','epistemic_strength','confidence'): assert x not in s
 assert 'Do not judge truth' in SYSTEM_PROMPT
def test_materialization_and_metric():
 ref=json.loads((ROOT/'eval/live/phase10d6i1_compositional_evidence_form_holdout_v0_1.json').read_text()); items=materialize(ref)
 assert len(items)==20 and REPEATS==6
 assert jaccard({'A','B'},{'B','C'})==1/3
