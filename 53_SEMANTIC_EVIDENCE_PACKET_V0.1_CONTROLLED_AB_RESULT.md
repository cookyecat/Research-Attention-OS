# Semantic Evidence Packet v0.1 — Controlled A/B Result

Status: **DEVELOPMENT-ONLY / PARTIAL SUPPORT / STABILITY RESIDUAL OPEN**  
Date: 2026-09-07

> Recovery purpose: archive the first controlled A/B of Evidence Packet v0.1 on the same 17 real RS02 Sensor edges. Resume from this result without reopening CLOSED Auditor-role questions.

---

# 1. North star

```text
Massive Information -> Minimal Human Attention -> Maximum Useful Cognitive Progress
```

This experiment does not optimize pass rate. It asks whether a better explicit evidence dossier can improve audit quality without silently repairing provenance or expanding Auditor authority.

Canonical role reminder:

> **Auditor 不应该拥有更多权力，但可以获得更完整的卷宗。**

---

# 2. Controlled A/B

Fixed:

```text
Semantic Sensor artifact: v0.2.2 RS02
semantic objects: fixed
Auditor: v0.1.1 fixed
Auditor prompt/schema/model configuration: fixed
```

Changed:

```text
A = original cited excerpts
B = Evidence Packet v0.1
    + full same-pointer citation container when the original excerpt was narrower
    + deterministic source metadata
```

No adjacent paragraph/page retrieval. No semantic repair. No Human Gold.

Artifact:

```text
semantic_evidence_packet_ab_v0_1_20260907T134028Z.json
```

Measurement git head:

```text
f3815494a9b80bb449cc71c73f91d544ff489d47
```

---

# 3. Topline

```text
n_edges             17
n_scorable          17
n_first_pass_valid  17
```

Verdict transitions:

```text
INSUFFICIENT -> INSUFFICIENT   4
INSUFFICIENT -> SUFFICIENT     1
SUFFICIENT   -> INSUFFICIENT   1
SUFFICIENT   -> SUFFICIENT    11
```

Packet items:

```text
PRIMARY_EXCERPT    19
CITATION_CONTEXT    7
SOURCE_METADATA    17
```

This is not an accuracy score because no independent Human Gold was attached.

---

# 4. Clear success: metadata-dependent temporal edge recovered

Edge:

```text
Absolute calendar dates for PR merges are unknown
because source publication time is unknown.
```

Baseline:

```text
INSUFFICIENT / MISSING_SUPPORT
```

Packet v0.1:

```text
INSUFFICIENT -> SUFFICIENT
MISSING_SUPPORT -> SUPPORTED
```

Why:

```text
PRIMARY_EXCERPT:
  relative dates in PARA 0004

SOURCE_METADATA:
  published_at=unknown
  updated_at=unknown
  captured_at=unknown
```

This directly supports the previous attribution that source metadata is a legitimate evidence type when the semantic object depends on source-time availability.

Observed lesson:

```text
Evidence != TextExcerpt only
```

---

# 5. Strong negative controls remained blocked

Three known provenance defects remained INSUFFICIENT.

## 5.1 Actor identity / role

```text
Lauren Tan / Cursor engineer
<- PARA 0004 + PARA 0011
```

Packet did not retrieve PARA 0003.

Result:

```text
INSUFFICIENT -> INSUFFICIENT
MISSING_SUPPORT -> MISSING_SUPPORT
```

Good: packet expansion did not silently repair actor identity provenance.

## 5.2 Affected system = Cursor codebase

```text
Cursor codebase
<- PARA 0004 + PARA 0011
```

Packet did not retrieve PARA 0005.

Result:

```text
INSUFFICIENT -> INSUFFICIENT
MISSING_SUPPORT -> MISSING_SUPPORT
```

This is the strongest observed negative control for provenance-repair leakage.

## 5.3 PARA 0005 attribution bridge

```text
Lauren Tan's merged PRs are not AI slop code
<- PARA 0005
```

Full cited container is still only PARA 0005 and does not identify Lauren / her PRs locally.

Result:

```text
INSUFFICIENT -> INSUFFICIENT
ATTRIBUTION_UNRESOLVED -> MISSING_SUPPORT
```

The diagnosis label changed, but the gate decision remained blocked.

---

# 6. Discourse-context candidate did NOT recover

Edge:

```text
Lauren Tan shared her workflow in a one-hour video,
explaining step-by-step how she achieved her efficiency.
```

Baseline short excerpt:

```text
Lauren 在这个一小时的视频里，几乎是手把手讲了她怎么走到这一步。
```

Packet added full cited PARA 0006:

```text
很多人，包括 Claude Code 的 Boris，都提过自己借助 coding agent 达到了类似的效率。
但真正愿意把工作方法完整分享出来的人并不多。
Lauren 在这个一小时的视频里，几乎是手把手讲了她怎么走到这一步。
```

Result remained:

```text
INSUFFICIENT -> INSUFFICIENT
MISSING_SUPPORT -> MISSING_SUPPORT
```

Auditor rationale focused on the phrase:

```text
“怎么走到这一步”
```

not strictly entailing:

```text
“how she achieved her efficiency”
```

Interpretation is still OPEN:

```text
A. semantic object is mildly overstrong;
B. full same-paragraph discourse context should support the paraphrase, but Auditor is too conservative;
C. both contribute.
```

Do not modify the Auditor or Sensor until this edge is explicitly human-adjudicated or isolated by a cleaner component test.

---

# 7. Unexpected regression: obvious positive edge flipped to INSUFFICIENT

Edge:

```text
Merged 1000 PRs in the previous month
and nearly 800 PRs in the first 12 days of the current month.
```

Baseline:

```text
SUFFICIENT / SUPPORTED
```

Packet:

```text
SUFFICIENT -> INSUFFICIENT
SUPPORTED -> OVERSTRONG_SCOPE
```

Important: this edge received no CITATION_CONTEXT expansion because the primary excerpt already equaled the full cited PARA 0004. The only new item was SOURCE_METADATA.

The new Auditor rationale argued that the semantic object lacked an explicit subject while the evidence used “她”. This appears logically weak for evidence sufficiency: the object does not assert a conflicting actor; it simply describes the action and quantities. Evidence containing additional subject information should not by itself make the smaller object unsupported.

Working attribution:

```text
likely Auditor false reject / prompt sensitivity / stochastic instability
possibly triggered by irrelevant added metadata
```

Do not treat one run as proof of a systematic metadata effect.

New open requirement:

```text
Audit Stability / Irrelevant-Evidence Invariance
```

Conceptually, adding irrelevant, non-contradictory evidence should not make an already-supported object unsupported.

---

# 8. What this experiment supports

Supported observations:

```text
1. Explicit source metadata can correctly resolve a metadata-dependent audit edge.
2. Same-citation-container policy did not leak adjacent provenance into known bad edges.
3. Packet v0.1 did not collapse into “make everything SUFFICIENT”.
4. Auditor v0.1.1 remains structurally stable: 17/17 first-pass valid.
```

Not yet supported:

```text
1. Full cited-container context reliably improves discourse-sensitive edges.
2. Adding metadata to every edge is harmless.
3. Auditor verdicts are stable under irrelevant evidence additions.
4. Packet v0.1 should become the production audit interface unchanged.
```

---

# 9. Occam interpretation

The current packet adds SOURCE_METADATA to all 17 edges.

The A/B shows a concrete benefit on the temporal metadata-dependent edge, but an unrelated positive-control edge also regressed in the same run.

Therefore the next step should not be “add more context everywhere”.

Prefer:

```text
minimal evidence needed for the object
```

over:

```text
maximal packet by default
```

Memorable principle:

> **More evidence is not automatically better evidence packaging; the goal is the smallest auditable packet sufficient for the object.**

---

# 10. Next experiment — component attribution + stability

Do not rerun all 17 edges across a large matrix.

Use only three diagnostic edges:

```text
Case A — obvious positive control
PR-count action
BASELINE vs METADATA_ONLY
Question: does irrelevant metadata reproducibly induce a false reject?

Case B — metadata-dependent case
Temporal uncertainty
BASELINE vs METADATA_ONLY
Question: does the beneficial recovery reproduce?

Case C — discourse-context case
One-hour workflow statement
BASELINE vs CONTEXT_ONLY
Question: does same-paragraph context reproducibly help?
```

Use repeated trials per condition to distinguish one-off model variation from a systematic packet effect.

Keep Auditor v0.1.1 unchanged during this attribution experiment.

---

# 11. Current status

```text
Semantic Sensor v0.2.2                  DEVELOPMENT / PARTIAL PASS
Semantic Evidence Auditor v0.1.1        LOCAL REAL-EDGE ROLE SUPPORTED
Evidence Packet v0.1                    FIRST CONTROLLED A/B COMPLETE
Metadata evidence utility               OBSERVED SUPPORT on temporal edge
Adjacent-provenance leakage              NOT OBSERVED
Discourse-context benefit               NOT YET DEMONSTRATED
Audit stability under irrelevant input  OPEN
Automatic retrieval / repair             NOT IMPLEMENTED
Fresh validation evidence               NONE
```

---

# 12. Recovery compression

```text
Packet v0.1 did one good thing cleanly:
metadata rescued the temporal uncertainty edge.

It also preserved three true negative controls.

But one obvious positive edge flipped to INSUFFICIENT after irrelevant metadata was added.
That opens an Auditor stability / irrelevant-evidence-invariance question.

The one-hour workflow context case stayed INSUFFICIENT and needs isolated attribution.

NEXT:
run a small repeated component/stability study on only three edges.
Do not change Auditor yet.
```
