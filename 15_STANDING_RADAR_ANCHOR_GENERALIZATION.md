# Research Attention OS — Standing Radar Anchor Generalization

Status: **SEMANTIC CALIBRATION — RECORDED**  
Date: 2026-09-06  
Phase: II-B Attention Policy Calibration  
Related: `12_STANDING_RADAR_FIT_ESTIMATOR_STUDY.md`, `14_STANDING_RADAR_FIT_V2_SEMANTIC_REPAIR.md`

---

## 1. Why this note exists

Fresh Human labeling after the v2 topic/facet repair exposed a broader but simpler interpretation of D.

D is not only a domain/topic-membership test. Stable standing radar can also be anchored by persistent monitored entities, places, and personal affiliations.

Counterfactual calibration examples showed that keeping event content approximately fixed while changing only the user's persistent relationship to the event can flip D.

Examples in abstract form:

- an event at an institution with a direct-family standing affiliation may be IN, while the same event at a non-affiliated institution is OUT;
- an event concerning the user's hometown/local government may be IN, while the same event in an unrelated city is OUT;
- a commercial-space event may be IN when a standing-monitored AI lab is a substantive actor, while an unknown commercial-space startup remains OUT.

These examples are calibration evidence, not fresh benchmark evidence.

No identifying institution or place names should be committed to the public research profile merely to encode this principle.

---

## 2. Refined semantic definition

The earlier wording:

$$
D=Standing\ Interest\ Fit
$$

is too narrow if read as domain preference only.

The preferred definition is now:

$$
\boxed{
D=Standing\ Radar\ Fit\ independent\ of\ event\ significance
}
$$

Human-language contract:

> **Ignoring how important this particular event is, does the event contain a substantive semantic anchor that belongs to a world, entity, place, or stable affiliation the user wants RAOS to monitor on a standing basis?**

This remains independent of S and P.

---

## 3. Minimal anchor model

Let:

$$
A_s(E)=\{substantive\ radar\ anchors\ in\ event\ E\}
$$

and let:

$$
R_u=UserStandingRadarProfile
$$

Then:

$$
\boxed{
D(E,u)=IN
\iff
\exists a\in A_s(E): Match(a,R_u)
}
$$

A radar anchor is a semantic concept, not a required ontology class. In natural language it may correspond to a topic, actor/entity, place, or stable personal affiliation.

The implementation must not require a typed hierarchy merely because these examples exist.

---

## 4. Substantive-anchor rule

An anchor must be substantively involved in the event.

Incidental mention is not enough.

Thus:

$$
Mention(standing\ anchor)\neq SubstantiveMatch
$$

and the earlier invariant remains:

$$
Using\ AI\ method\neq Being\ an\ AI\ event
$$

Examples:

- a routine fusion experiment using a neural-network utility remains OUT when AI is merely a tool;
- a commercial-space company developing an autonomous robot may be IN because robotics is itself a substantive event object;
- a commercial-space company substantively partnering with a standing-monitored AI organization may be IN because the monitored organization is an event actor, not incidental context.

---

## 5. Standing versus temporary relevance

D must remain a **standing** radar signal.

Stable topic/entity/place/affiliation anchors belong in D.

Temporary situational relevance does not automatically belong in D. For example, a location that matters only because of a one-off trip or an organization that matters only because of a short-lived task should remain runtime/project context rather than silently expanding the standing radar.

This preserves the separation:

$$
StandingRadar\neq CurrentProjectContext
$$

---

## 6. Relation to exclusions

The v2 exclusion interpretation still holds:

$$
\boxed{
Exclusion=scope\ guard,\ not\ veto
}
$$

A broad excluded domain must not erase an independently substantive standing anchor.

Equally, an included broad domain must not make every local operational update IN if the user's standing profile is narrower than that.

---

## 7. Consequence for the current v2 validation

The FV1-FV8 labels and the new standing-anchor calibration evidence were supplied in the same calibration turn, before any scored v2 model run.

Because the standing-radar semantic contract is being generalized after the FV labels are already known, FV1-FV8 must not be reported as a pristine fresh holdout for an anchor-aware repair made afterward.

Therefore:

```text
FV1-FV8 = CALIBRATION / DEVELOPMENT EVIDENCE
```

Do not run them and report the resulting score as fresh evidence for a model that has been changed using this calibration.

The next estimator claim, if measured, requires a new fresh holdout created after the anchor-aware semantic contract/prompt/profile are frozen.

---

## 8. Research decision

Do not introduce:

- domain weights;
- an entity ontology;
- a relationship ontology;
- a place taxonomy;
- a new D sub-variable.

The minimal model remains one semantic matching variable:

$$
\boxed{
Event\rightarrow SubstantiveRadarAnchors\rightarrow StandingRadarMatch
}
$$

This is an extension of the substantive-facet model, not a replacement with a weighted recommendation score.

---

## 9. Current pointer

```text
D semantic meaning                 STANDING RADAR FIT
Topic-only interpretation          TOO NARROW
Substantive-facet repair            SUPPORTED
Persistent entity/place/affiliation anchors  CALIBRATED
Weights / ontology                  NOT JUSTIFIED
Anchor-aware estimator freeze       NEXT
Fresh final D validation            AFTER FREEZE
S estimator study                   AFTER D closure
```

The D study must remain narrow. The next change should be a minimal anchor-aware semantic repair, followed by one final small fresh validation. If that passes without a new systematic residual, close D for Phase II-B and move to S.
