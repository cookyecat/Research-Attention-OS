"""Developer-dogfood cognition provider that executes the frozen research contract directly."""
from __future__ import annotations

from uuid import UUID

from app.cognitive.model_provider import ModelBackedCognitiveProvider
from app.cognitive.research_aligned_contract import (
    CONTRACT_VERSION,
    BindingResponse,
    GroundingResponse,
    JurisdictionResponse,
    RelationResponse,
    GROUNDING_SYSTEM,
    JURISDICTION_SYSTEM,
    RELATION_MAPPING_SYSTEM,
    SUPPORT_BINDING_SYSTEM,
    authority_outcome,
    canonical_semantic_units,
    contract_snapshot,
    grounding_items,
    grounding_user_prompt,
    jurisdiction_items,
    jurisdiction_user_prompt,
    relation_rows,
    relation_user_prompt,
    support_user_prompt,
    validated_bindings,
    validated_grounding,
    validated_jurisdiction,
)
from app.enums import CognitiveEffectKind
from app.services.cognitive_impact import (
    CognitiveEffect,
    CognitiveImpactAssessment,
    features_from_impact,
)
from app.services.deltas import (
    model_delta_from_decision_effect,
    propose_patches_for_decision_effect,
)


class ResearchAlignedCognitiveProvider(ModelBackedCognitiveProvider):
    """Run research Relation -> Binding -> Grounding/Jurisdiction -> Authority online.

    There is intentionally no legacy-impact fallback inside this provider. A model/schema
    failure fails the AnalysisRun rather than silently changing cognition semantics.
    """

    requires_audited_semantics = True
    cognition_contract_version = CONTRACT_VERSION

    def __init__(self, *args, **kwargs):
        kwargs.setdefault("impact_system_prompt", RELATION_MAPPING_SYSTEM)
        kwargs.setdefault("impact_contract_version", CONTRACT_VERSION)
        super().__init__(*args, **kwargs)
        self.last_cognition_trace: dict = {}
        self.stage_provenance: dict = {}

    def cognition_contract_snapshot(self) -> dict:
        return contract_snapshot()

    def match_kernel(self, *args, **kwargs):
        result = super().match_kernel(*args, **kwargs)
        self.stage_provenance["matching"] = {
            "provider": "model",
            "status": "success",
            "contract": CONTRACT_VERSION,
        }
        return result

    @staticmethod
    def _target_node(nodes, raw_id):
        wanted = str(raw_id or "")
        return next((node for node in nodes or [] if str(node.id) == wanted), None)

    def assess_cognitive_impact(
        self,
        text,
        extraction,
        matches,
        *,
        is_duplicate=False,
        independent_source_count=1,
        secondary_report_count=0,
        threatens_active_work=None,
        nodes=None,
    ) -> CognitiveImpactAssessment:
        del text
        nodes = list(nodes or [])
        units = canonical_semantic_units(extraction)

        relation_parsed = self._complete(
            RELATION_MAPPING_SYSTEM,
            relation_user_prompt(units, matches, nodes),
            RelationResponse,
            stage="impact",
        )
        relations = relation_rows(relation_parsed, matches, nodes)

        bindings: dict[str, dict] = {}
        if relations:
            binding_parsed = self._complete(
                SUPPORT_BINDING_SYSTEM,
                support_user_prompt(relations, units, matches, nodes),
                BindingResponse,
                stage="impact",
            )
            bindings = validated_bindings(binding_parsed, relations, units, matches)

        g_items = grounding_items(relations, bindings, units, nodes) if relations else []
        grounding: dict[str, dict] = {}
        if g_items:
            grounding_parsed = self._complete(
                GROUNDING_SYSTEM,
                grounding_user_prompt(g_items),
                GroundingResponse,
                stage="impact",
            )
            grounding = validated_grounding(grounding_parsed, g_items)

        j_items = jurisdiction_items(relations, bindings, units, matches, nodes) if relations else []
        jurisdiction: dict[str, dict] = {}
        if j_items:
            jurisdiction_parsed = self._complete(
                JURISDICTION_SYSTEM,
                jurisdiction_user_prompt(j_items),
                JurisdictionResponse,
                stage="impact",
            )
            jurisdiction = validated_jurisdiction(jurisdiction_parsed, j_items)

        raw_effects: list[CognitiveEffect] = []
        authorized: list[CognitiveEffect] = []
        authority_trace: list[dict] = []
        for relation in relations:
            rid = relation["relation_id"]
            binding = bindings[rid]
            op = CognitiveEffectKind(relation["operation"])
            raw_target = relation.get("target_kernel_node_id")
            target_id = UUID(str(raw_target)) if raw_target else None
            target_node = self._target_node(nodes, raw_target)
            target_type = getattr(target_node, "node_type", None) if target_node is not None else None
            gclass = (grounding.get(rid) or {}).get("grounding_class")
            jclass = (jurisdiction.get(rid) or {}).get("jurisdiction_class")
            outcome = authority_outcome(
                relation,
                binding,
                grounding_class=gclass,
                jurisdiction_class=jclass,
                units=units,
                extraction=extraction,
                nodes=nodes,
            )
            base_kwargs = dict(
                target_kernel_node_id=target_id,
                operation=op,
                change_magnitude=0.0,
                reason=relation.get("reason") or "",
                exploration_candidate=op == CognitiveEffectKind.OPEN_NEW,
                target_node_type=target_type,
                support_unit_ids=list(binding.get("support_unit_ids") or []),
                jurisdiction_anchor_ids=list(binding.get("jurisdiction_anchor_ids") or []),
                grounding_class=gclass,
                provenance_role=outcome["provenance_role"],
                authority_reason=outcome["authority_reason"],
            )
            raw_effects.append(
                CognitiveEffect(
                    **base_kwargs,
                    epistemic_strength=0.0,
                    target_importance=float(outcome["importance_band"]),
                )
            )
            trace = {
                "relation_id": rid,
                "operation": relation["operation"],
                "target_kernel_node_id": raw_target,
                "support_unit_ids": list(binding.get("support_unit_ids") or []),
                "jurisdiction_anchor_ids": list(binding.get("jurisdiction_anchor_ids") or []),
                "grounding_class": gclass,
                "jurisdiction_class": jclass,
                **outcome,
            }
            authority_trace.append(trace)
            if outcome["keep"]:
                authorized.append(
                    CognitiveEffect(
                        **base_kwargs,
                        epistemic_strength=float(outcome["epistemic_band"]),
                        target_importance=float(outcome["importance_band"]),
                    )
                )

        assessment = CognitiveImpactAssessment(
            effects=authorized,
            raw_effects=raw_effects,
            exploration_candidate=any(e.operation == CognitiveEffectKind.OPEN_NEW for e in authorized),
        )
        assessment.features = features_from_impact(
            assessment,
            matches,
            extraction,
            attention_cost=assessment.attention_cost,
            exploration_candidate=assessment.exploration_candidate,
            is_duplicate=is_duplicate,
            independent_source_count=independent_source_count,
            secondary_report_count=secondary_report_count,
            threatens_active_work=bool(threatens_active_work),
            marketing_heavy=extraction.marketing_heavy,
            evidence_maturity=extraction.evidence_maturity,
        )
        self.last_raw_effects = list(raw_effects)
        self.last_impact = assessment
        self.last_cognition_trace = {
            "contract": contract_snapshot(),
            "semantic_units": units,
            "relations": relations,
            "bindings": bindings,
            "grounding": grounding,
            "jurisdiction": jurisdiction,
            "authority": authority_trace,
        }
        self.stage_provenance["impact"] = {
            "provider": "model",
            "status": "success",
            "contract": CONTRACT_VERSION,
            "relation_count": len(relations),
            "authorized_effect_count": len(authorized),
            "fallback": False,
        }
        return assessment

    def propose_model_delta(
        self,
        text,
        extraction,
        matches,
        features,
        nodes,
        *,
        assessment=None,
    ):
        del text, matches, features, nodes
        effects = list(getattr(assessment, "effects", []) or []) if assessment is not None else []
        if len(effects) > 1:
            raise ValueError("research-aligned artifact synthesis requires one projected Decision Cause")
        self._set_stage_runtime("delta", llm_called=False)
        return model_delta_from_decision_effect(effects[0] if effects else None, extraction)

    def propose_patches(
        self,
        text,
        delta,
        matches,
        features,
        nodes,
        evidence_link_ids,
        *,
        assessment=None,
        extraction=None,
    ):
        del text, matches, features
        effects = list(getattr(assessment, "effects", []) or []) if assessment is not None else []
        if len(effects) > 1:
            raise ValueError("research-aligned patch synthesis requires one projected Decision Cause")
        self._set_stage_runtime("patches", llm_called=False)
        return propose_patches_for_decision_effect(
            effects[0] if effects else None,
            delta=delta,
            nodes=nodes,
            extraction=extraction,
            evidence_link_ids=evidence_link_ids,
        )
