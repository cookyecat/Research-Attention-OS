"""Phase17.3-KS-C baseline comparison.

Baselines are intentionally weak reference points:
A. surface keyword/similarity heuristic
B. current-slot-question lexical matching
C. semantic resolver placeholder contract

This is not the final resolver. It establishes the benchmark harness boundary.
"""
from pathlib import Path
import json

ROOT = Path(__file__).resolve().parents[2]
GOLD = ROOT / "eval/live/results/phase17_3_ks_c_semantic_key_resolution_benchmark_v0_1/phase17_3_ks_c_semantic_key_resolution_benchmark_v0_1_gold.json"
OUT = ROOT / "eval/live/results/phase17_3_ks_c_semantic_key_resolution_baselines_v0_1"


def lexical_baseline(case):
    text = case["new_proposition"].lower()
    for slot in case["current_slots"]:
        q = slot["question"].lower()
        if any(token in text for token in q.split()):
            return "REUSE", slot["key"]
    return "CREATE", None


def main():
    data = json.loads(GOLD.read_text())
    rows=[]
    for case in data["cases"]:
        pred, key = lexical_baseline(case)
        rows.append({
            "id": case["id"],
            "category": case["category"],
            "prediction": pred,
            "prediction_key": key,
            "gold": case["gold"],
            "gold_key": case["gold_key"],
            "correct": pred == case["gold"] and (key == case["gold_key"] or pred == "CREATE")
        })
    result={
        "benchmark":"phase17.3-ks-c-semantic-key-resolution-baselines-v0.1",
        "baseline":"lexical_slot_matching",
        "results":rows,
        "accuracy":sum(r["correct"] for r in rows)/len(rows)
    }
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT/"lexical_baseline.json").write_text(json.dumps(result,ensure_ascii=False,indent=2))
    print(json.dumps(result,ensure_ascii=False,indent=2))

if __name__=='__main__':
    main()
