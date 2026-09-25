"""Phase17.3-KS-E pairwise Direct-Answer Gate."""
from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Literal

from pydantic import BaseModel, Field, model_validator

from app.cognitive.client import chat_json_schema

from .adjudication import CandidateAdjudicationPlan

DIRECT_ANSWER_CONTRACT = "semantic-coordinate-direct-answer-v0.1"

DirectAnswerDecision = Literal["DIRECT", "NOT_DIRECT", "UNCERTAIN"]
AddressResolutionStatus = Literal[
    "REUSE_AUTHORIZED",
    "CREATE_ELIGIBLE",
    "UNRESOLVED",
]


class DirectAnswerDraftV01(BaseModel):
    decision: DirectAnswerDecision
    rationale: str = Field(min_length=1, max_length=2000)


class DirectAnswerBatchItemDraftV01(BaseModel):
    pair_key: str = Field(min_length=1, max_length=64)
    decision: DirectAnswerDecision
    rationale: str = Field(min_length=1, max_length=2000)


class DirectAnswerBatchDraftV01(BaseModel):
    judgments: tuple[DirectAnswerBatchItemDraftV01, ...]


class DirectAnswerJudgmentV01(BaseModel):
    contract: str = DIRECT_ANSWER_CONTRACT
    proposition_id: str
    slot_id: str
    decision: DirectAnswerDecision
    rationale: str

    @model_validator(mode="after")
    def validate_contract(self):
        if self.contract != DIRECT_ANSWER_CONTRACT:
            raise ValueError(
                f"contract must be {DIRECT_ANSWER_CONTRACT}"
            )
        return self


class DirectAnswerAddressResolutionV01(BaseModel):
    status: AddressResolutionStatus
    authorized_existing_slot_ids: tuple[str, ...] = ()
    authorized_existing_slot_id: str | None = None
    direct_slot_ids: tuple[str, ...] = ()
    uncertain_slot_ids: tuple[str, ...] = ()
    full_same_family_verified: bool
    rationale: str

    @model_validator(mode="after")
    def validate_authorized_set(self):
        authorized = tuple(sorted(set(self.authorized_existing_slot_ids)))
        direct = tuple(sorted(set(self.direct_slot_ids)))
        uncertain = tuple(sorted(set(self.uncertain_slot_ids)))
        object.__setattr__(self, "authorized_existing_slot_ids", authorized)
        object.__setattr__(self, "direct_slot_ids", direct)
        object.__setattr__(self, "uncertain_slot_ids", uncertain)

        if self.status == "REUSE_AUTHORIZED":
            if not authorized:
                raise ValueError(
                    "REUSE_AUTHORIZED requires at least one authorized existing slot"
                )
            if set(authorized) != set(direct):
                raise ValueError(
                    "authorized existing slots must equal DIRECT slot set"
                )
            object.__setattr__(
                self,
                "authorized_existing_slot_id",
                authorized[0] if len(authorized) == 1 else None,
            )
        elif self.authorized_existing_slot_id is not None or authorized:
            raise ValueError(
                "only REUSE_AUTHORIZED may carry authorized existing slots"
            )
        return self
_DIRECT_ANSWER_SYSTEM = """You are the RAOS pairwise Direct-Answer Gate.

You receive exactly ONE already-grounded World proposition and ONE existing
CurrentSlot.

Your only question is:

If the proposition is true of the Event referent, does it materially change the
answer to this exact CurrentSlot.state_question?

Return JSON:
{
  "decision": "DIRECT | NOT_DIRECT | UNCERTAIN",
  "rationale": "short explanation"
}

Rules:
- Do not choose among multiple slots. You see only one pair.
- primitive_family and referent_scope are frozen upstream.
- REFERENT-SCOPE AUTHORITY: TARGET_INTRINSIC means FlatMap has already grounded
  the proposition as a property/value of the Event referent. Do not reclassify
  ownership merely because the normalized statement uses passive wording or
  names a task/object. TARGET_RELATION likewise remains relational. If the
  semantic content explicitly contradicts its frozen referent_scope, return
  UNCERTAIN rather than silently changing ownership.
- DIRECT requires that the proposition would update, extend, correct, contest,
  or otherwise materially change the answer to the exact state_question.
- ANSWER-SUBSTITUTION TEST: ask whether the proposition's semantic content can
  be inserted as a direct answer/value for the exact state_question without an
  extra bridge inference. If the reasoning needs "therefore", "this implies",
  "this suggests", or "this supports the idea that...", return NOT_DIRECT.
  Direct paraphrase/instantiation is allowed; inferred significance, suitability,
  causation, or capability is not.
- Same primitive family is necessary but not sufficient.
- KEY-VALUE SEPARATION: state_question is intentionally reusable/general while
  proposition evidence may be a concrete instance, task, environment, metric,
  or measurement. Do NOT reject merely because the evidence is specific. If
  that specific evidence is a value/example of the exact state dimension, it
  can be DIRECT.
- KEY-QUALIFIER LITERALITY: semantic qualifiers in the state_question matter.
  "demonstrated capability" is not the same coordinate as merely "designed or
  intended capability"; "integration performance" is not the same as the bare
  fact of external integration. Respect these qualifiers exactly.
- OBSERVED-REALIZATION RULE: a proposition about behavior actually exhibited in
  a demo, run, test, or observed execution directly answers a "demonstrated
  capability/behavior" coordinate when the described behavior is itself the
  demonstrated property. Wording such as "the demo behavior is controllable",
  "in the run it adapts", or "the test shows it can..." is realized evidence,
  not merely an intention. By contrast, "is designed to", "is intended to",
  "could be used to", or a claimed future role remains NOT_DIRECT unless the
  proposition also states actual demonstrated behavior.
- ENUMERATIVE-COORDINATE RULE: some state_questions intentionally ask for an
  open set/list, e.g. "What capabilities or behaviors has this system
  demonstrated?", "What use cases has it demonstrated?", or "What operational
  performance characteristics does it have?". A concrete realized member of
  that requested set is DIRECT when all qualifiers match, even if that member
  could later be studied as a finer-grained coordinate. Do not force key
  fragmentation merely because a concrete member has its own semantic name.
  The qualifier still governs the boundary: demonstrated/observed members are
  DIRECT for a demonstrated-* list; merely designed/intended/claimed members
  are NOT_DIRECT for that list.
- PERFORMANCE-FACET RULE: when the slot asks for operational performance
  characteristics, a target-grounded concrete measurement/example of speed,
  latency, throughput, call rate, or cost/efficiency is DIRECT even if measured
  in one task/demo. The concrete task belongs in the value, not in key identity.
  This does NOT absorb distinct QUALITY dimensions such as correctness/validity
  or reliability/failure behavior.
- END-TO-END TASK DURATION is not automatically the same coordinate as model
  operational performance. It may reflect task complexity or a composite
  workflow and can vary independently. Judge it from the exact state_question;
  if the representation boundary is genuinely unresolved, use UNCERTAIN.
- DIRECT ANSWER IS NOT EXPLANATORY SUPPORT: a proposition can provide evidence
  for why a slot's answer might be true without directly changing that answer.
  Example: an integration being ultra-fast may support a real-time-suitability
  claim, but it does not itself state which contexts/use cases the system is
  suited for. Such explanatory/causal support is NOT_DIRECT.
- Same topic, semantic similarity, causal relevance, shared source, shared
  application, or shared vocabulary is NOT enough.
- SAME-FAMILY FACET COHESION: independent variation by itself is NOT sufficient
  reason to split a new coordinate. First read the exact state_question. If that
  question already semantically covers the proposition as one of its facets,
  examples, measurements, or realized behaviors, return DIRECT even if that
  facet could vary independently. Example: prompt-controllable behavior shown
  in an actual demo is a demonstrated behavior when the slot asks what
  capabilities or behaviors have been demonstrated.
- Return NOT_DIRECT for a same-family proposition only when the existing
  state_question asks a materially different semantic axis or qualifier, not
  merely because the new facet is specific or independently variable. Examples:
  correctness != reliability; demonstrated behavior != merely intended/design
  role; integration performance != the bare fact of integration.
- Do not invent property transfer across entities. However, this gate is not an
  entity re-grounder: do not override frozen referent_scope merely from passive
  wording or a named task/object. Explicit scope contradiction -> UNCERTAIN.
- Use UNCERTAIN only when the pair cannot be decided from the supplied grounded
  semantics; do not use it merely because the claim itself is epistemically
  uncertain.
- Example DIRECT: "Jev plays DOOM in real time" against "What capabilities or
  behaviors has this system demonstrated?"
- Example NOT_DIRECT: an agent's per-step design against "What underlying model
  or architecture is this system based on?"
- Example NOT_DIRECT: trading-workflow integration details against a generic
  base-model architecture question.
"""

_DIRECT_ANSWER_RULES_TEXT = _DIRECT_ANSWER_SYSTEM.split("Rules:\n", 1)[1]
_DIRECT_ANSWER_BATCH_SYSTEM = """You are the RAOS batched pairwise Direct-Answer Gate.

You receive a LIST of independent proposition-slot pairs.

For EACH pair, answer exactly the same local question:
If that proposition is true of the Event referent, does it materially change
the answer to that exact CurrentSlot.state_question?

Do not choose among pairs, rank slots, compare alternatives, or let one pair's
answer influence another pair.

Return JSON:
{
  "judgments": [
    {
      "pair_key": "J001",
      "decision": "DIRECT | NOT_DIRECT | UNCERTAIN",
      "rationale": "short explanation"
    }
  ]
}

You must return each supplied pair_key exactly once and no unknown pair_key.

Rules:
- Judge every pair independently.
""" + _DIRECT_ANSWER_RULES_TEXT


def _field(value, name: str):
    if isinstance(value, dict):
        return value.get(name)
    return getattr(value, name, None)
def judge_direct_answer(
    *,
    event_identity: dict,
    proposition,
    slot,
    chat_fn,
) -> DirectAnswerJudgmentV01:
    proposition_id = (
        _field(proposition, "proposition_id")
        or _field(proposition, "proposition_key")
        or "unknown-proposition"
    )
    slot_id = (
        _field(slot, "slot_id")
        or _field(slot, "slot_key")
        or "unknown-slot"
    )
    proposition_family = _field(proposition, "primitive_family")
    slot_family = _field(slot, "primitive_family")
    if not proposition_family or not slot_family:
        raise ValueError(
            "direct-answer gate requires proposition and slot primitive_family"
        )

    if proposition_family != slot_family:
        return DirectAnswerJudgmentV01(
            proposition_id=str(proposition_id),
            slot_id=str(slot_id),
            decision="NOT_DIRECT",
            rationale="primitive-family hard mismatch",
        )

    statement = (
        _field(proposition, "statement")
        or _field(proposition, "proposition")
        or _field(proposition, "text")
    )
    state_question = _field(slot, "state_question")
    if not statement or not state_question:
        raise ValueError(
            "direct-answer gate requires proposition statement and slot state_question"
        )

    payload = {
        "contract": DIRECT_ANSWER_CONTRACT,
        "event_identity": dict(event_identity),
        "proposition": {
            "proposition_id": str(proposition_id),
            "statement": statement,
            "primitive_family": proposition_family,
            "referent_scope": _field(proposition, "referent_scope"),
        },
        "current_slot": {
            "slot_id": str(slot_id),
            "primitive_family": slot_family,
            "slot_label": _field(slot, "slot_label"),
            "state_question": state_question,
            "current_value": _field(slot, "value"),
        },
    }
    obj, _meta, _validation = chat_json_schema(
        [
            {"role": "system", "content": _DIRECT_ANSWER_SYSTEM},
            {
                "role": "user",
                "content": (
                    "Judge this one proposition-slot pair only.\n\n"
                    + __import__("json").dumps(
                        payload,
                        ensure_ascii=False,
                        sort_keys=True,
                        default=str,
                    )
                ),
            },
        ],
        DirectAnswerDraftV01,
        chat_fn=chat_fn,
        timeout=45.0,
        thinking="disabled",
        reasoning_effort=None,
    )
    draft = DirectAnswerDraftV01.model_validate(obj)
    return DirectAnswerJudgmentV01(
        proposition_id=str(proposition_id),
        slot_id=str(slot_id),
        decision=draft.decision,
        rationale=draft.rationale,
    )


def judge_direct_answer_batch(
    *,
    event_identity: dict,
    pairs: list[tuple[object, object]],
    chat_fn,
) -> list[DirectAnswerJudgmentV01]:
    """Judge many proposition-slot pairs in one transport call.

    Semantics remain pairwise. Batching changes only transport, not the
    independent Direct-Answer decision contract.
    """
    if not pairs:
        return []

    results: list[DirectAnswerJudgmentV01 | None] = [
        None for _ in pairs
    ]
    llm_payload_rows = []
    llm_pair_meta: dict[str, tuple[int, str, str]] = {}

    for index, (proposition, slot) in enumerate(pairs, start=1):
        pair_key = f"J{index:03d}"
        proposition_id = str(
            _field(proposition, "proposition_id")
            or _field(proposition, "proposition_key")
            or f"unknown-proposition-{index}"
        )
        slot_id = str(
            _field(slot, "slot_id")
            or _field(slot, "slot_key")
            or f"unknown-slot-{index}"
        )
        proposition_family = _field(proposition, "primitive_family")
        slot_family = _field(slot, "primitive_family")
        if not proposition_family or not slot_family:
            raise ValueError(
                "batched direct-answer gate requires primitive_family "
                "on proposition and slot"
            )

        if proposition_family != slot_family:
            results[index - 1] = DirectAnswerJudgmentV01(
                proposition_id=proposition_id,
                slot_id=slot_id,
                decision="NOT_DIRECT",
                rationale="primitive-family hard mismatch",
            )
            continue

        statement = (
            _field(proposition, "statement")
            or _field(proposition, "proposition")
            or _field(proposition, "text")
        )
        state_question = _field(slot, "state_question")
        if not statement or not state_question:
            raise ValueError(
                "batched direct-answer gate requires proposition statement "
                "and slot state_question"
            )

        llm_pair_meta[pair_key] = (
            index - 1,
            proposition_id,
            slot_id,
        )
        llm_payload_rows.append({
            "pair_key": pair_key,
            "proposition": {
                "proposition_id": proposition_id,
                "statement": statement,
                "primitive_family": proposition_family,
                "referent_scope": _field(
                    proposition,
                    "referent_scope",
                ),
            },
            "current_slot": {
                "slot_id": slot_id,
                "primitive_family": slot_family,
                "slot_label": _field(slot, "slot_label"),
                "state_question": state_question,
                "current_value": _field(slot, "value"),
            },
        })

    if llm_payload_rows:
        payload = {
            "contract": DIRECT_ANSWER_CONTRACT,
            "event_identity": dict(event_identity),
            "pairs": llm_payload_rows,
        }
        obj, _meta, _validation = chat_json_schema(
            [
                {
                    "role": "system",
                    "content": _DIRECT_ANSWER_BATCH_SYSTEM,
                },
                {
                    "role": "user",
                    "content": (
                        "Judge every supplied pair independently.\n\n"
                        + __import__("json").dumps(
                            payload,
                            ensure_ascii=False,
                            sort_keys=True,
                            default=str,
                        )
                    ),
                },
            ],
            DirectAnswerBatchDraftV01,
            chat_fn=chat_fn,
            timeout=60.0,
            thinking="disabled",
            reasoning_effort=None,
        )
        draft = DirectAnswerBatchDraftV01.model_validate(obj)
        observed_keys = [row.pair_key for row in draft.judgments]
        expected_keys = set(llm_pair_meta)
        if len(observed_keys) != len(set(observed_keys)):
            raise ValueError(
                "batched direct-answer output contains duplicate pair_key"
            )
        if set(observed_keys) != expected_keys:
            raise ValueError(
                "batched direct-answer output must exactly cover pair keys; "
                f"missing={sorted(expected_keys-set(observed_keys))} "
                f"unknown={sorted(set(observed_keys)-expected_keys)}"
            )

        for row in draft.judgments:
            output_index, proposition_id, slot_id = llm_pair_meta[
                row.pair_key
            ]
            results[output_index] = DirectAnswerJudgmentV01(
                proposition_id=proposition_id,
                slot_id=slot_id,
                decision=row.decision,
                rationale=row.rationale,
            )

    if any(row is None for row in results):
        raise RuntimeError(
            "batched direct-answer failed to produce all judgments"
        )
    return [row for row in results if row is not None]


def judge_direct_answer_batch_consensus(
    *,
    event_identity: dict,
    pairs: list[tuple[object, object]],
    chat_fn,
    repeats: int = 2,
) -> list[DirectAnswerJudgmentV01]:
    if repeats < 1:
        raise ValueError("repeats must be >= 1")
    if not pairs:
        return []

    runs = [
        judge_direct_answer_batch(
            event_identity=event_identity,
            pairs=pairs,
            chat_fn=chat_fn,
        )
        for _ in range(repeats)
    ]
    width = len(pairs)
    if any(len(run) != width for run in runs):
        raise ValueError(
            "batched direct-answer repeat cardinality mismatch"
        )
    return [
        consensus_direct_answer([
            run[index]
            for run in runs
        ])
        for index in range(width)
    ]


def judge_direct_answer_parallel_consensus(
    *,
    event_identity: dict,
    pairs: list[tuple[object, object]],
    chat_fn,
    repeats: int = 2,
    max_workers: int = 6,
) -> list[DirectAnswerJudgmentV01]:
    """Run the original one-pair contract concurrently.

    Unlike prompt batching, every LLM request still sees exactly one
    proposition-slot pair. Concurrency changes scheduling only, not semantics.
    """
    if repeats < 1:
        raise ValueError("repeats must be >= 1")
    if max_workers < 1:
        raise ValueError("max_workers must be >= 1")
    if not pairs:
        return []

    total_tasks = len(pairs) * repeats
    workers = min(max_workers, total_tasks)
    judgments_by_pair: list[list[DirectAnswerJudgmentV01 | None]] = [
        [None for _ in range(repeats)]
        for _ in pairs
    ]

    with ThreadPoolExecutor(max_workers=workers) as executor:
        future_meta = {}
        for pair_index, (proposition, slot) in enumerate(pairs):
            for repeat_index in range(repeats):
                future = executor.submit(
                    judge_direct_answer,
                    event_identity=event_identity,
                    proposition=proposition,
                    slot=slot,
                    chat_fn=chat_fn,
                )
                future_meta[future] = (
                    pair_index,
                    repeat_index,
                )

        for future in as_completed(future_meta):
            pair_index, repeat_index = future_meta[future]
            judgments_by_pair[pair_index][repeat_index] = (
                future.result()
            )

    consensus = []
    for rows in judgments_by_pair:
        if any(row is None for row in rows):
            raise RuntimeError(
                "parallel direct-answer execution lost a judgment"
            )
        consensus.append(
            consensus_direct_answer([
                row
                for row in rows
                if row is not None
            ])
        )
    return consensus


def resolve_pairwise_address(
    *,
    judgments: list[DirectAnswerJudgmentV01],
    full_same_family_verified: bool,
) -> DirectAnswerAddressResolutionV01:
    direct = tuple(sorted({
        row.slot_id
        for row in judgments
        if row.decision == "DIRECT"
    }))
    uncertain = tuple(sorted({
        row.slot_id
        for row in judgments
        if row.decision == "UNCERTAIN"
    }))

    if uncertain:
        return DirectAnswerAddressResolutionV01(
            status="UNRESOLVED",
            direct_slot_ids=direct,
            uncertain_slot_ids=uncertain,
            full_same_family_verified=full_same_family_verified,
            rationale="pairwise verification contains UNCERTAIN candidates",
        )
    if direct:
        return DirectAnswerAddressResolutionV01(
            status="REUSE_AUTHORIZED",
            authorized_existing_slot_ids=direct,
            direct_slot_ids=direct,
            full_same_family_verified=full_same_family_verified,
            rationale=(
                "one or more existing coordinates passed the independent "
                "direct-answer gate; joint KeyBy may update only this set"
            ),
        )
    if full_same_family_verified:
        return DirectAnswerAddressResolutionV01(
            status="CREATE_ELIGIBLE",
            full_same_family_verified=True,
            rationale="no existing same-family coordinate directly answers proposition",
        )
    return DirectAnswerAddressResolutionV01(
        status="UNRESOLVED",
        full_same_family_verified=False,
        rationale=(
            "no retrieved candidate passed, but hidden same-family coordinates "
            "have not yet been verified"
        ),
    )


def consensus_direct_answer(
    judgments: list[DirectAnswerJudgmentV01],
) -> DirectAnswerJudgmentV01:
    """Collapse repeated judgments for the same pair; disagreement fails closed."""
    if not judgments:
        raise ValueError("consensus requires at least one judgment")

    proposition_ids = {row.proposition_id for row in judgments}
    slot_ids = {row.slot_id for row in judgments}
    if len(proposition_ids) != 1 or len(slot_ids) != 1:
        raise ValueError("consensus judgments must refer to one proposition-slot pair")

    decisions = {row.decision for row in judgments}
    proposition_id = judgments[0].proposition_id
    slot_id = judgments[0].slot_id

    if decisions == {"DIRECT"}:
        return DirectAnswerJudgmentV01(
            proposition_id=proposition_id,
            slot_id=slot_id,
            decision="DIRECT",
            rationale="all repeated pairwise judgments agree on DIRECT",
        )
    if decisions == {"NOT_DIRECT"}:
        return DirectAnswerJudgmentV01(
            proposition_id=proposition_id,
            slot_id=slot_id,
            decision="NOT_DIRECT",
            rationale="all repeated pairwise judgments agree on NOT_DIRECT",
        )
    return DirectAnswerJudgmentV01(
        proposition_id=proposition_id,
        slot_id=slot_id,
        decision="UNCERTAIN",
        rationale=(
            "repeated pairwise judgments disagree or contain UNCERTAIN; "
            "fail closed"
        ),
    )


class PairwisePropositionAddressV01(BaseModel):
    proposition_id: str
    resolution: DirectAnswerAddressResolutionV01
    initial_candidate_slot_ids: tuple[str, ...] = ()
    expanded_slot_ids: tuple[str, ...] = ()
    consensus_judgments: tuple[DirectAnswerJudgmentV01, ...] = ()

    @property
    def expansion_triggered(self) -> bool:
        return bool(self.expanded_slot_ids)


class PairwiseAuthorizationPlanV01(BaseModel):
    propositions: tuple[PairwisePropositionAddressV01, ...]

    @property
    def authorized_existing_slot_ids(self) -> tuple[str, ...]:
        return tuple(sorted({
            slot_id
            for row in self.propositions
            for slot_id in row.resolution.authorized_existing_slot_ids
        }))

    @property
    def unresolved_proposition_ids(self) -> tuple[str, ...]:
        return tuple(sorted(
            row.proposition_id
            for row in self.propositions
            if row.resolution.status == "UNRESOLVED"
        ))

    @property
    def create_eligible_proposition_ids(self) -> tuple[str, ...]:
        return tuple(sorted(
            row.proposition_id
            for row in self.propositions
            if row.resolution.status == "CREATE_ELIGIBLE"
        ))


def _verify_one_pair_consensus(
    *,
    event_identity: dict,
    proposition,
    slot,
    chat_fn,
    repeats: int,
) -> DirectAnswerJudgmentV01:
    if repeats < 1:
        raise ValueError("repeats must be >= 1")
    judgments = [
        judge_direct_answer(
            event_identity=event_identity,
            proposition=proposition,
            slot=slot,
            chat_fn=chat_fn,
        )
        for _ in range(repeats)
    ]
    return consensus_direct_answer(judgments)


def verify_proposition_address(
    *,
    event_identity: dict,
    proposition,
    same_family_slots: list,
    initial_candidate_slot_ids: tuple[str, ...],
    chat_fn,
    repeats: int = 2,
    verify_full_family_on_reuse: bool = False,
) -> PairwisePropositionAddressV01:
    proposition_id = str(
        _field(proposition, "proposition_id")
        or _field(proposition, "proposition_key")
        or "unknown-proposition"
    )
    slots_by_id = {
        str(_field(slot, "slot_id") or _field(slot, "slot_key")): slot
        for slot in same_family_slots
    }
    initial_ids = tuple(
        slot_id
        for slot_id in initial_candidate_slot_ids
        if slot_id in slots_by_id
    )
    hidden_ids = tuple(
        sorted(set(slots_by_id) - set(initial_ids))
    )

    consensus_rows: list[DirectAnswerJudgmentV01] = []
    for slot_id in initial_ids:
        consensus_rows.append(
            _verify_one_pair_consensus(
                event_identity=event_identity,
                proposition=proposition,
                slot=slots_by_id[slot_id],
                chat_fn=chat_fn,
                repeats=repeats,
            )
        )

    initial_resolution = resolve_pairwise_address(
        judgments=consensus_rows,
        full_same_family_verified=not hidden_ids,
    )
    if initial_resolution.status == "UNRESOLVED" and any(
        row.decision == "UNCERTAIN"
        for row in consensus_rows
    ):
        return PairwisePropositionAddressV01(
            proposition_id=proposition_id,
            resolution=initial_resolution,
            initial_candidate_slot_ids=initial_ids,
            consensus_judgments=tuple(consensus_rows),
        )
    if (
        initial_resolution.status == "REUSE_AUTHORIZED"
        and not verify_full_family_on_reuse
    ):
        return PairwisePropositionAddressV01(
            proposition_id=proposition_id,
            resolution=initial_resolution,
            initial_candidate_slot_ids=initial_ids,
            consensus_judgments=tuple(consensus_rows),
        )
    if (
        initial_resolution.status == "CREATE_ELIGIBLE"
        or not hidden_ids
    ):
        return PairwisePropositionAddressV01(
            proposition_id=proposition_id,
            resolution=initial_resolution,
            initial_candidate_slot_ids=initial_ids,
            consensus_judgments=tuple(consensus_rows),
        )

    for slot_id in hidden_ids:
        consensus_rows.append(
            _verify_one_pair_consensus(
                event_identity=event_identity,
                proposition=proposition,
                slot=slots_by_id[slot_id],
                chat_fn=chat_fn,
                repeats=repeats,
            )
        )

    final_resolution = resolve_pairwise_address(
        judgments=consensus_rows,
        full_same_family_verified=True,
    )
    return PairwisePropositionAddressV01(
        proposition_id=proposition_id,
        resolution=final_resolution,
        initial_candidate_slot_ids=initial_ids,
        expanded_slot_ids=hidden_ids,
        consensus_judgments=tuple(consensus_rows),
    )


def build_pairwise_authorization_plan(
    *,
    event_identity: dict,
    propositions,
    current_slots,
    candidate_plan: CandidateAdjudicationPlan,
    chat_fn,
    repeats: int = 2,
    verify_full_family_on_reuse: bool = False,
) -> PairwiseAuthorizationPlanV01:
    proposition_by_id = {
        str(
            _field(row, "proposition_id")
            or _field(row, "proposition_key")
        ): row
        for row in propositions
    }
    slot_by_id = {
        str(_field(row, "slot_id") or _field(row, "slot_key")): row
        for row in current_slots
    }

    rows = []
    for candidate_row in candidate_plan.propositions:
        proposition = proposition_by_id.get(candidate_row.proposition_id)
        if proposition is None:
            raise ValueError(
                "candidate plan proposition missing from pairwise input: "
                f"{candidate_row.proposition_id}"
            )
        family = _field(proposition, "primitive_family")
        same_family_slots = [
            slot_by_id[slot_id]
            for slot_id in candidate_row.same_family_slot_ids
            if slot_id in slot_by_id
            and _field(slot_by_id[slot_id], "primitive_family") == family
        ]
        rows.append(
            verify_proposition_address(
                event_identity=event_identity,
                proposition=proposition,
                same_family_slots=same_family_slots,
                initial_candidate_slot_ids=candidate_row.candidate_slot_ids,
                chat_fn=chat_fn,
                repeats=repeats,
                verify_full_family_on_reuse=verify_full_family_on_reuse,
            )
        )

    return PairwiseAuthorizationPlanV01(
        propositions=tuple(rows),
    )



def build_pairwise_authorization_plan_batched(
    *,
    event_identity: dict,
    propositions,
    current_slots,
    candidate_plan: CandidateAdjudicationPlan,
    chat_fn,
    repeats: int = 2,
    verify_full_family_on_reuse: bool = False,
) -> PairwiseAuthorizationPlanV01:
    """Two-wave batched implementation of pairwise address authorization.

    Wave 1 judges every retrieved Top-K proposition-slot pair.
    Wave 2 judges only hidden same-family slots required by fail-safe expansion.
    Each pair remains semantically independent; batching changes transport only.
    """
    proposition_by_id = {
        str(
            _field(row, "proposition_id")
            or _field(row, "proposition_key")
        ): row
        for row in propositions
    }
    slot_by_id = {
        str(_field(row, "slot_id") or _field(row, "slot_key")): row
        for row in current_slots
    }

    states: dict[str, dict] = {}
    initial_pairs: list[tuple[object, object]] = []

    for candidate_row in candidate_plan.propositions:
        proposition_id = candidate_row.proposition_id
        proposition = proposition_by_id.get(proposition_id)
        if proposition is None:
            raise ValueError(
                "candidate plan proposition missing from batched pairwise input: "
                f"{proposition_id}"
            )
        family = _field(proposition, "primitive_family")
        same_family_ids = tuple(
            slot_id
            for slot_id in candidate_row.same_family_slot_ids
            if slot_id in slot_by_id
            and _field(slot_by_id[slot_id], "primitive_family") == family
        )
        initial_ids = tuple(
            slot_id
            for slot_id in candidate_row.candidate_slot_ids
            if slot_id in same_family_ids
        )
        hidden_ids = tuple(
            slot_id
            for slot_id in same_family_ids
            if slot_id not in set(initial_ids)
        )
        states[proposition_id] = {
            "proposition": proposition,
            "initial_ids": initial_ids,
            "hidden_ids": hidden_ids,
            "initial_judgments": [],
            "expanded_judgments": [],
            "expand": False,
        }
        initial_pairs.extend(
            (proposition, slot_by_id[slot_id])
            for slot_id in initial_ids
        )

    initial_judgments = judge_direct_answer_batch_consensus(
        event_identity=event_identity,
        pairs=initial_pairs,
        chat_fn=chat_fn,
        repeats=repeats,
    )
    for judgment in initial_judgments:
        state = states.get(judgment.proposition_id)
        if state is None:
            raise ValueError(
                "batched initial judgment references unknown proposition: "
                f"{judgment.proposition_id}"
            )
        state["initial_judgments"].append(judgment)

    expansion_pairs: list[tuple[object, object]] = []
    for proposition_id, state in states.items():
        hidden_ids = state["hidden_ids"]
        initial_rows = state["initial_judgments"]
        initial_resolution = resolve_pairwise_address(
            judgments=initial_rows,
            full_same_family_verified=not hidden_ids,
        )
        has_uncertain = any(
            row.decision == "UNCERTAIN"
            for row in initial_rows
        )
        should_expand = bool(hidden_ids) and (
            (
                initial_resolution.status == "UNRESOLVED"
                and not has_uncertain
            )
            or (
                initial_resolution.status == "REUSE_AUTHORIZED"
                and verify_full_family_on_reuse
            )
        )
        state["initial_resolution"] = initial_resolution
        state["expand"] = should_expand
        if should_expand:
            expansion_pairs.extend(
                (
                    state["proposition"],
                    slot_by_id[slot_id],
                )
                for slot_id in hidden_ids
            )

    expanded_judgments = judge_direct_answer_batch_consensus(
        event_identity=event_identity,
        pairs=expansion_pairs,
        chat_fn=chat_fn,
        repeats=repeats,
    )
    for judgment in expanded_judgments:
        state = states.get(judgment.proposition_id)
        if state is None:
            raise ValueError(
                "batched expansion judgment references unknown proposition: "
                f"{judgment.proposition_id}"
            )
        state["expanded_judgments"].append(judgment)

    rows = []
    for candidate_row in candidate_plan.propositions:
        proposition_id = candidate_row.proposition_id
        state = states[proposition_id]
        all_rows = [
            *state["initial_judgments"],
            *state["expanded_judgments"],
        ]
        if state["expand"]:
            resolution = resolve_pairwise_address(
                judgments=all_rows,
                full_same_family_verified=True,
            )
            expanded_ids = state["hidden_ids"]
        else:
            resolution = state["initial_resolution"]
            expanded_ids = ()

        rows.append(
            PairwisePropositionAddressV01(
                proposition_id=proposition_id,
                resolution=resolution,
                initial_candidate_slot_ids=state["initial_ids"],
                expanded_slot_ids=expanded_ids,
                consensus_judgments=tuple(all_rows),
            )
        )

    return PairwiseAuthorizationPlanV01(
        propositions=tuple(rows),
    )



def verify_proposition_address_batched(
    *,
    event_identity: dict,
    proposition,
    same_family_slots: list,
    initial_candidate_slot_ids: tuple[str, ...],
    chat_fn,
    repeats: int = 2,
    verify_full_family_on_reuse: bool = False,
) -> PairwisePropositionAddressV01:
    """Pairwise semantics with proposition-scoped batched transport.

    Only slots for ONE proposition are ever co-batched. This avoids the
    cross-proposition context contamination observed with global batching.
    """
    proposition_id = str(
        _field(proposition, "proposition_id")
        or _field(proposition, "proposition_key")
        or "unknown-proposition"
    )
    slots_by_id = {
        str(_field(slot, "slot_id") or _field(slot, "slot_key")): slot
        for slot in same_family_slots
    }
    initial_ids = tuple(
        slot_id
        for slot_id in initial_candidate_slot_ids
        if slot_id in slots_by_id
    )
    hidden_ids = tuple(
        sorted(set(slots_by_id) - set(initial_ids))
    )

    initial_pairs = [
        (proposition, slots_by_id[slot_id])
        for slot_id in initial_ids
    ]
    initial_rows = judge_direct_answer_batch_consensus(
        event_identity=event_identity,
        pairs=initial_pairs,
        chat_fn=chat_fn,
        repeats=repeats,
    )
    initial_resolution = resolve_pairwise_address(
        judgments=initial_rows,
        full_same_family_verified=not hidden_ids,
    )
    has_uncertain = any(
        row.decision == "UNCERTAIN"
        for row in initial_rows
    )
    if initial_resolution.status == "UNRESOLVED" and has_uncertain:
        return PairwisePropositionAddressV01(
            proposition_id=proposition_id,
            resolution=initial_resolution,
            initial_candidate_slot_ids=initial_ids,
            consensus_judgments=tuple(initial_rows),
        )

    should_expand = bool(hidden_ids) and (
        initial_resolution.status == "UNRESOLVED"
        or (
            initial_resolution.status == "REUSE_AUTHORIZED"
            and verify_full_family_on_reuse
        )
    )
    if not should_expand:
        return PairwisePropositionAddressV01(
            proposition_id=proposition_id,
            resolution=initial_resolution,
            initial_candidate_slot_ids=initial_ids,
            consensus_judgments=tuple(initial_rows),
        )

    expansion_pairs = [
        (proposition, slots_by_id[slot_id])
        for slot_id in hidden_ids
    ]
    expanded_rows = judge_direct_answer_batch_consensus(
        event_identity=event_identity,
        pairs=expansion_pairs,
        chat_fn=chat_fn,
        repeats=repeats,
    )
    all_rows = [*initial_rows, *expanded_rows]
    final_resolution = resolve_pairwise_address(
        judgments=all_rows,
        full_same_family_verified=True,
    )
    return PairwisePropositionAddressV01(
        proposition_id=proposition_id,
        resolution=final_resolution,
        initial_candidate_slot_ids=initial_ids,
        expanded_slot_ids=hidden_ids,
        consensus_judgments=tuple(all_rows),
    )


def build_pairwise_authorization_plan_proposition_batched(
    *,
    event_identity: dict,
    propositions,
    current_slots,
    candidate_plan: CandidateAdjudicationPlan,
    chat_fn,
    repeats: int = 2,
    verify_full_family_on_reuse: bool = False,
) -> PairwiseAuthorizationPlanV01:
    """Safe batching boundary: one proposition per batch."""
    proposition_by_id = {
        str(
            _field(row, "proposition_id")
            or _field(row, "proposition_key")
        ): row
        for row in propositions
    }
    slot_by_id = {
        str(_field(row, "slot_id") or _field(row, "slot_key")): row
        for row in current_slots
    }

    rows = []
    for candidate_row in candidate_plan.propositions:
        proposition = proposition_by_id.get(
            candidate_row.proposition_id
        )
        if proposition is None:
            raise ValueError(
                "candidate plan proposition missing from proposition-batched "
                f"input: {candidate_row.proposition_id}"
            )
        family = _field(proposition, "primitive_family")
        same_family_slots = [
            slot_by_id[slot_id]
            for slot_id in candidate_row.same_family_slot_ids
            if slot_id in slot_by_id
            and _field(slot_by_id[slot_id], "primitive_family") == family
        ]
        rows.append(
            verify_proposition_address_batched(
                event_identity=event_identity,
                proposition=proposition,
                same_family_slots=same_family_slots,
                initial_candidate_slot_ids=(
                    candidate_row.candidate_slot_ids
                ),
                chat_fn=chat_fn,
                repeats=repeats,
                verify_full_family_on_reuse=(
                    verify_full_family_on_reuse
                ),
            )
        )

    return PairwiseAuthorizationPlanV01(
        propositions=tuple(rows),
    )



def build_pairwise_authorization_plan_parallel(
    *,
    event_identity: dict,
    propositions,
    current_slots,
    candidate_plan: CandidateAdjudicationPlan,
    chat_fn,
    repeats: int = 2,
    verify_full_family_on_reuse: bool = False,
    max_workers: int = 6,
) -> PairwiseAuthorizationPlanV01:
    """Two-wave parallel execution of the original single-pair contract."""
    proposition_by_id = {
        str(
            _field(row, "proposition_id")
            or _field(row, "proposition_key")
        ): row
        for row in propositions
    }
    slot_by_id = {
        str(_field(row, "slot_id") or _field(row, "slot_key")): row
        for row in current_slots
    }

    states: dict[str, dict] = {}
    initial_pairs: list[tuple[object, object]] = []

    for candidate_row in candidate_plan.propositions:
        proposition_id = candidate_row.proposition_id
        proposition = proposition_by_id.get(proposition_id)
        if proposition is None:
            raise ValueError(
                "candidate plan proposition missing from parallel pairwise "
                f"input: {proposition_id}"
            )
        family = _field(proposition, "primitive_family")
        same_family_ids = tuple(
            slot_id
            for slot_id in candidate_row.same_family_slot_ids
            if slot_id in slot_by_id
            and _field(slot_by_id[slot_id], "primitive_family") == family
        )
        initial_ids = tuple(
            slot_id
            for slot_id in candidate_row.candidate_slot_ids
            if slot_id in same_family_ids
        )
        hidden_ids = tuple(
            slot_id
            for slot_id in same_family_ids
            if slot_id not in set(initial_ids)
        )
        states[proposition_id] = {
            "proposition": proposition,
            "initial_ids": initial_ids,
            "hidden_ids": hidden_ids,
            "initial_judgments": [],
            "expanded_judgments": [],
            "expand": False,
        }
        initial_pairs.extend(
            (proposition, slot_by_id[slot_id])
            for slot_id in initial_ids
        )

    initial_judgments = judge_direct_answer_parallel_consensus(
        event_identity=event_identity,
        pairs=initial_pairs,
        chat_fn=chat_fn,
        repeats=repeats,
        max_workers=max_workers,
    )
    for judgment in initial_judgments:
        state = states.get(judgment.proposition_id)
        if state is None:
            raise ValueError(
                "parallel initial judgment references unknown proposition: "
                f"{judgment.proposition_id}"
            )
        state["initial_judgments"].append(judgment)

    expansion_pairs: list[tuple[object, object]] = []
    for state in states.values():
        hidden_ids = state["hidden_ids"]
        initial_rows = state["initial_judgments"]
        initial_resolution = resolve_pairwise_address(
            judgments=initial_rows,
            full_same_family_verified=not hidden_ids,
        )
        has_uncertain = any(
            row.decision == "UNCERTAIN"
            for row in initial_rows
        )
        should_expand = bool(hidden_ids) and (
            (
                initial_resolution.status == "UNRESOLVED"
                and not has_uncertain
            )
            or (
                initial_resolution.status == "REUSE_AUTHORIZED"
                and verify_full_family_on_reuse
            )
        )
        state["initial_resolution"] = initial_resolution
        state["expand"] = should_expand
        if should_expand:
            expansion_pairs.extend(
                (
                    state["proposition"],
                    slot_by_id[slot_id],
                )
                for slot_id in hidden_ids
            )

    expanded_judgments = judge_direct_answer_parallel_consensus(
        event_identity=event_identity,
        pairs=expansion_pairs,
        chat_fn=chat_fn,
        repeats=repeats,
        max_workers=max_workers,
    )
    for judgment in expanded_judgments:
        state = states.get(judgment.proposition_id)
        if state is None:
            raise ValueError(
                "parallel expansion judgment references unknown proposition: "
                f"{judgment.proposition_id}"
            )
        state["expanded_judgments"].append(judgment)

    rows = []
    for candidate_row in candidate_plan.propositions:
        proposition_id = candidate_row.proposition_id
        state = states[proposition_id]
        all_rows = [
            *state["initial_judgments"],
            *state["expanded_judgments"],
        ]
        if state["expand"]:
            resolution = resolve_pairwise_address(
                judgments=all_rows,
                full_same_family_verified=True,
            )
            expanded_ids = state["hidden_ids"]
        else:
            resolution = state["initial_resolution"]
            expanded_ids = ()

        rows.append(
            PairwisePropositionAddressV01(
                proposition_id=proposition_id,
                resolution=resolution,
                initial_candidate_slot_ids=state["initial_ids"],
                expanded_slot_ids=expanded_ids,
                consensus_judgments=tuple(all_rows),
            )
        )

    return PairwiseAuthorizationPlanV01(
        propositions=tuple(rows),
    )
