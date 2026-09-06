# Research Attention OS — Boundary with Recommendation Systems

Status: **PRODUCT / ARCHITECTURE THESIS — RECORDED**  
Date: 2026-09-06  
Related: `01_PRODUCT.md`, `10_ATTENTION_POLICY_ELICITATION_AND_CALIBRATION.md`, `11_ROADMAP_AND_PROGRESS.md`

---

## 1. Investor-level contrast

A useful short pitch is:

> **Consumer recommendation systems often try to earn more of the user's attention. RAOS tries to spend less of it: use less screen time to produce more useful cognitive progress, then get the user back to doing the work.**

Chinese:

> **很多推荐系统的产品目标，是争取用户更多的注意力和停留时间；RAOS 的目标恰恰相反：用更少的屏幕时间，完成更多有价值的认知、判断和决策，然后让用户离开屏幕去真正做事情。**

The rigorous version is about the **objective function**, not a claim that every recommendation algorithm in existence optimizes screen time.

RAOS north star:

$$
\boxed{
Massive\ Information
\rightarrow
Minimal\ Human\ Attention
\rightarrow
Maximum\ Useful\ Cognitive\ Progress
}
$$

Directional objective:

$$
CROA = \frac{Useful\ Cognitive\ Change}{Human\ Attention\ Cost}
$$

A conventional recommender may ask:

> Which item is the user most likely to click, watch, engage with, or consume next?

RAOS asks:

> What, if anything, deserves scarce human attention given the user's current cognition and the state of the world?

These objectives can point in opposite directions. A high-engagement item can still deserve `DROP`; a major external event outside the user's normal interests can still deserve `AWARE`.

---

## 2. Why D / S / P are not one recommendation score

For the no-cognitive-change AWARE gap:

$$
\boxed{AWARE\iff S\land(D\lor P)}
$$

where:

$$
D=Standing\ Interest\ Fit
$$

$$
S=Material\ Consequence\ of\ the\ Underlying\ Event
$$

$$
P=Current/Emerging\ Public\ Attention\ Salience
$$

These answer different physical questions:

- `D`: Is this part of a world the user wants monitored on a standing basis?
- `S`: Did the underlying event actually have material consequence?
- `P`: Has the event entered, or is it clearly entering, public / industry attention?

Do not collapse these into one opaque relevance / engagement score merely because a recommender can rank content.

Examples:

```text
Trivial celebrity gossip:
D may be 1
P may be 1
S = 0
=> no-Delta AWARE gate says DROP
```

```text
Major public-health event outside normal standing interests:
D = 0
S = 1
P = 1
=> AWARE
```

A single personalized engagement score can easily blur popularity, personal interest, intrinsic consequence, and attention allocation. RAOS keeps them causally separable.

---

## 3. Recommendation techniques can still be useful machinery

The distinction is:

$$
\boxed{D/S/P = Attention\ Semantics}
$$

$$
\boxed{Recommendation\ Techniques = Possible\ Estimation/Ranking\ Machinery}
$$

A possible future architecture is:

$$
E\rightarrow SemanticRepresentation
$$

Then estimate the semantic variables separately.

### D — Standing Radar Fit

$$
\boxed{D=f_D(E,UserStandingProfile)}
$$

Potential machinery later:

- user / item embeddings;
- semantic similarity;
- two-tower retrieval;
- multi-interest representations;
- learned preference representations.

This may eventually reduce the need to call an LLM for every D judgment. The machinery does not change what D means.

### P — Public Attention Salience

$$
\boxed{P=f_P(E,WorldAttention_t)}
$$

Potential evidence / machinery:

- number of independent sources;
- number and diversity of discussants;
- propagation speed;
- cross-community spread;
- current attention level;
- persistence;
- acceleration / growth;
- trend-detection methods.

P is structurally closer to social-platform trend detection than D or S.

### S — Material Consequence

$$
\boxed{S=MaterialConsequence(E)}
$$

S is the least recommendation-like variable. It asks:

> **What did this event actually change?**

not:

> How many people like or discuss it?

S may be technical, scientific, economic, social, cultural, political, institutional, or otherwise materially consequential. Popularity and novelty alone must not manufacture S.

---

## 4. Recommended separation of concerns

Future system shape:

```text
Event / information
      ↓
Semantic / event representation
      ↓
 ┌──────────┬──────────┬──────────┐
 │ D        │ S        │ P        │
 │ personal │ material │ public   │
 │ radar    │ impact   │ radar    │
 └──────────┴──────────┴──────────┘
      ↓
Attention Policy
      ↓
DROP / AWARE / WATCH / ENGAGE
      ↓
Ranking / scheduling among already-legitimate candidates
```

Recommendation/ranking technology is especially appropriate **after** semantics are preserved, for questions such as:

> If there are 20 legitimate ENGAGE/WATCH/AWARE candidates, which should be surfaced first under a bounded attention budget?

That later ranking layer may use learned weights, embeddings, cost models, runtime context, or other recommender machinery.

Do not use it to erase the semantic distinction among cognition, personal standing interest, intrinsic event consequence, and public attention.

---

## 5. Product principle

A concise product boundary:

> **Recommendation systems optimize what to show next. RAOS optimizes what the human should not have to look at at all.**

Or, more operationally:

> **Recommendation systems compete for attention; RAOS budgets attention.**

This is a product thesis, not a claim that all recommender-system research has the same commercial objective.

---

## 6. Research decision

Current D/S/P definitions remain the active semantic model.

Recommendation-system techniques are recorded as a **future implementation avenue**, not a replacement for D/S/P and not a reason to redesign the current Phase II-B study.

Current priority remains:

```text
Preserve semantic variables
→ measure them
→ attribute residuals
→ only later optimize estimation/ranking machinery
```
