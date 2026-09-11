import json
from pathlib import Path
from eval.live.phase10d6j_relation_support_directness_v0_1 import DirectnessResponse,SYSTEM_PROMPT
from eval.live.run_phase10d6j_relation_support_directness_v0_1 import REPEATS,materialize
ROOT=Path(__file__).resolve().parents[3]
def test_reference_has_all_fit_classes():
 ref=json.loads((ROOT/'eval/live/phase10d6j_relation_support_directness_reference_v0_1.json').read_text()); assert len(ref['items'])==16; assert {x['fit'] for x in ref['items']}=={'DIRECT','PARTIAL','INSUFFICIENT','CONTRADICTS_OPERATION'}
def test_directness_contract_has_no_cardinals():
 s=json.dumps(DirectnessResponse.model_json_schema())+SYSTEM_PROMPT
 for x in ('change_magnitude','target_importance','epistemic_strength','confidence score'): assert x not in s
def test_reference_materializes_exact_effects():
 ref=json.loads((ROOT/'eval/live/phase10d6j_relation_support_directness_reference_v0_1.json').read_text()); items=materialize(ref); assert len(items)==16 and REPEATS==6; assert all(x['support_units'] and x['target_proposition'] for x in items)
