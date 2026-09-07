# Semantic Evidence Packet v0.1 — Controlled A/B Checkpoint

Status: **IMPLEMENTED / DEVELOPMENT-ONLY / CONTROLLED A/B PENDING**  
Date: 2026-09-07

> Recovery purpose: resume the Semantic Sensor / Auditor frontier here. Do not reopen CLOSED Auditor-role questions unless new evidence requires it.

---

# 1. RAOS north star

```text
Massive Information
      ↓
Minimal Human Attention
      ↓
Maximum Useful Cognitive Progress
```

The Evidence Packet is not a new cognitive module. It is the explicit dossier presented to the Semantic Evidence Auditor so the Auditor can make a bounded, auditable support judgment without gaining search or repair authority.

Core role split:

> **Sensor 负责看清；Auditor 负责不让没证据的语义污染系统；D/S/P/Delta 负责理解意义；Attention Policy 负责花你的注意力。**

---

# 2. Why this step exists

The first real-edge Auditor v0.1.1 run audited 17 actual Semantic Sensor v0.2.2 provenance edges:

```text
17 scorable
17 first-pass valid
12 SUFFICIENT
5 INSUFFICIENT
```

The five failures did not all mean the same thing.

Observed classes included:

```text
A. genuine provenance incompleteness
B. semantic object / excerpt discourse-context mismatch
C. legal evidence omitted from the audit packet (source metadata)
```

This creates a new engineering question:

> **Can a better explicit evidence dossier reduce packet-induced false failures without hiding genuine Sensor provenance defects?**

---

# 3. Epistemic boundary

Canonical Auditor role remains in:

```text
50_SEMANTIC_EVIDENCE_AUDITOR_ROLE_AND_BOUNDARIES.md
```

Important invariants:

$$
\boxed{INSUFFICIENT \neq FALSE}
$$

$$
\boxed{INSUFFICIENT = Not\ proven\ by\ current\ evidence\ packet}
$$

and:

> **在明确、有限、可审计的证据条件下，尽可能判断当前语义对象是否被充分支持，并把判断依据留下来。**

The current research step improves the packet, not Auditor authority.

> **Auditor 不应该拥有更多权力，但可以获得更完整的卷宗。**

$$
\boxed{Better\ Context \neq More\ Auditor\ Authority}
$$

---

# 4. Evidence Packet v0.1

The packet contains only three explicit evidence kinds:

```text
PRIMARY_EXCERPT
  Sensor's existing support excerpt

CITATION_CONTEXT
  full container named by that same existing support_pointer
  e.g. full PARA 0006 when the Sensor cited PARA 0006

SOURCE_METADATA
  deterministic pinned metadata
  published_at / updated_at / captured_at / path / media_type
```

The packet MUST NOT:

```text
retrieve adjacent paragraphs/pages
search the full source
find a better paragraph
rewrite semantic objects
add inferred facts
repair provenance
use outside-world evidence
```

Critical negative control:

```text
If Sensor cited PARA 0004,
Evidence Packet may expand PARA 0004,
but MUST NOT retrieve PARA 0005.
```

This distinction is what separates **context preservation** from **provenance repair**.

---

# 5. Why full cited-container context is allowed

The support pointer already names a source container such as:

```text
PARA 0006
PAGE 0003
```

A short diagnostic excerpt may omit discourse material that exists inside that already-cited container.

Example RS02:

Sensor excerpt:

```text
Lauren 在这个一小时的视频里，几乎是手把手讲了她怎么走到这一步。
```

Full cited PARA 0006 also contains:

```text
很多人……借助 coding agent 达到了类似的效率。
但真正愿意把工作方法完整分享出来的人并不多。
```

Providing the full already-cited paragraph does not search for replacement evidence. It makes the existing citation container explicit to the Auditor.

---

# 6. Why source metadata is allowed

Some semantic objects are derived partly from deterministic source metadata rather than prose.

Known RS02 example:

```text
Absolute calendar dates are unresolved because source publication time is unknown.
```

The prose evidence contains relative dates, while the hard basis:

```text
published_at = unknown
```

comes from pinned source metadata.

Therefore:

```text
Evidence != TextExcerpt only
```

Metadata is valid audit evidence only when explicitly included in the packet.

The Auditor still does not fetch it itself.

---

# 7. Controlled A/B design

Keep fixed:

```text
Semantic Sensor artifact      fixed: v0.2.2 RS02
semantic objects              fixed
Auditor                       fixed: v0.1.1
Auditor prompt / schema       fixed
model configuration           fixed
```

Change only:

```text
A: baseline cited excerpts

B: Evidence Packet v0.1
   baseline excerpts
   + full same-pointer citation container
   + deterministic source metadata
```

Runner:

```text
eval/live/run_semantic_evidence_auditor_packet_ab_v0_1.py
```

This allows causal attribution to packet completeness rather than Auditor redesign.

---

# 8. Pre-run development expectations

These are development hypotheses, not fresh validation labels.

## Expected to remain INSUFFICIENT

### Actor identity / role edge

```text
Lauren Tan / Cursor engineer
<- PARA 0004 + PARA 0011
```

Those cited containers still do not establish all identity/role material. Packet v0.1 must not retrieve PARA 0003.

### Cursor codebase affected-system edge

```text
Cursor codebase
<- PARA 0004 + PARA 0011
```

Packet v0.1 must not retrieve PARA 0005. This is the strongest negative control for provenance-repair leakage.

### PARA 0005 attribution edge

```text
Lauren Tan's merged PRs are not AI slop code
<- PARA 0005
```

If full PARA 0005 still lacks the required attribution bridge, it should remain insufficient.

## Expected candidate INSUFFICIENT -> SUFFICIENT transitions

### Temporal uncertainty

Packet now explicitly includes:

```text
published_at=unknown
```

so the metadata-dependent uncertainty may become supportable.

### One-hour workflow/efficiency statement

Packet expands the already-cited PARA 0006 to its full paragraph, restoring the discourse context that the short excerpt omitted.

## Expected stable SUFFICIENT controls

```text
1000 PR / nearly 800 PR action <- PARA 0004
verification bottleneck statement <- PARA 0007
```

Obvious good edges should not regress.

---

# 9. What would count as a good result

The goal is NOT to maximize the number of SUFFICIENT edges.

A good result looks more like:

```text
packet-induced failures can recover
true provenance gaps stay blocked
obvious supported edges stay supported
```

In transition language:

```text
some justified INSUFFICIENT -> SUFFICIENT
known bad INSUFFICIENT -> INSUFFICIENT
obvious good SUFFICIENT -> SUFFICIENT
```

A result where every edge suddenly becomes SUFFICIENT would be suspicious, not desirable.

---

# 10. Implementation

Files:

```text
eval/live/semantic_evidence_packet_v0_1.py
eval/live/run_semantic_evidence_auditor_packet_ab_v0_1.py
backend/tests/eval/test_semantic_evidence_packet_v0_1.py
```

Commits:

```text
4575448a6f5d28fa3994f160447b93938e67b436
feat: add bounded semantic evidence packet v0.1

33d913c4e67aed7d05236561e2c8dee548eba344
feat: add evidence packet real-edge controlled ab runner

0f6b40d3531c2efdb138d301034b1ba26f86d4f8
test: lock bounded evidence packet v0.1
```

Auditor v0.1.1 itself is unchanged.

---

# 11. Exact next commands

Sync:

```bash
git pull --rebase
```

Focused tests:

```bash
cd backend
.venv/bin/pytest \
  tests/eval/test_semantic_evidence_auditor_v0_1_1.py \
  tests/eval/test_semantic_evidence_packet_v0_1.py -q
cd ..
```

Then run the controlled packet A/B:

```bash
backend/.venv/bin/python \
  eval/live/run_semantic_evidence_auditor_packet_ab_v0_1.py \
  --sensor-artifact eval/live/results/semantic_evidence_dev_v0_2_2/semantic_evidence_dev_v0_2_2_20260907T103010Z.json \
  --baseline-audit-artifact eval/live/results/semantic_evidence_auditor_real_edges_v0_1_1/semantic_evidence_auditor_real_edges_v0_1_1_20260907T125803Z.json
```

Console output includes:

```text
n_edges
n_scorable
n_first_pass_valid
verdict_transitions
reason_transitions
packet_item_totals
```

---

# 12. What to inspect after the run

Do not stop at aggregate transitions.

Inspect at least:

```text
1. affected-system Cursor codebase negative control
2. actor identity/role negative control
3. temporal uncertainty metadata case
4. one-hour video / workflow discourse-context case
5. PR-count action stable positive control
6. verification statement stable positive control
```

Primary scientific question:

> **Can bounded explicit context improve audit quality without turning evidence packaging into hidden provenance repair?**

---

# 13. Current status

```text
Semantic Sensor v0.2.2                  DEVELOPMENT / PARTIAL PASS
Semantic Evidence Auditor v0.1.1        LOCAL REAL-EDGE ROLE SUPPORTED
Auditor role/boundary definition        CANONICAL in document 50
Evidence Packet v0.1                    IMPLEMENTED
Packet policy                           SAME-CITED-CONTAINER + METADATA ONLY
Packet controlled A/B                   PENDING
Automatic adjacent retrieval            NOT IMPLEMENTED
Automatic evidence repair               NOT IMPLEMENTED
Fresh validation evidence               NONE
```

---

# 14. Recovery compression

```text
Sensor reads.
Auditor checks the evidence edge.
Evidence Packet is the dossier presented to the Auditor.

Better dossier != more Auditor authority.
Same cited container may be expanded.
Adjacent evidence may not be silently retrieved.
Metadata must be explicit.

NEXT:
run Packet v0.1 controlled A/B on the same 17 real RS02 edges.
```
