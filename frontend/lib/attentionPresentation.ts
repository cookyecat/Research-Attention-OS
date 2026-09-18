export function attentionLabel(disposition?: string | null) {
  if (disposition === "ENGAGE") return "Needs you";
  if (disposition === "WATCH") return "Being watched";
  if (disposition === "AWARE") return "Worth knowing";
  if (disposition === "DROP") return "Filtered";
  return "Not analyzed";
}

export function attentionAction(disposition?: string | null) {
  if (disposition === "ENGAGE") return "This deserves focused attention now.";
  if (disposition === "WATCH") return "RAOS owns the next check. You do not need to monitor it yourself.";
  if (disposition === "AWARE") return "Know this once, then move on.";
  if (disposition === "DROP") return "No attention needed right now.";
  return "RAOS has not made an attention judgment yet.";
}

function truncate(value: string, limit: number) {
  const text = value.trim();
  return text.length > limit ? `${text.slice(0, limit - 1).trim()}…` : text;
}

function sentenceCase(value: string) {
  const text = value.trim();
  return text ? `${text.charAt(0).toUpperCase()}${text.slice(1)}` : text;
}

function cleanRadarClause(value?: string | null) {
  return String(value || "")
    .replace(/^Monitor\s+/i, "")
    .replace(/^substantive\s+/i, "")
    .replace(/[.]$/, "")
    .trim();
}

function causeTargetLabel(type?: string | null) {
  const labels: Record<string, string> = {
    QUESTION: "open question",
    BELIEF: "current belief",
    BOTTLENECK: "active bottleneck",
    MODEL: "working model",
    PROJECT: "active project",
    GOAL: "current goal",
  };
  return labels[String(type || "").toUpperCase()] || "current context";
}

export function closestContext(plan: any) {
  const matches = plan?.score_debug?.matches;
  const first = Array.isArray(matches) ? matches.find((match) => match?.title) : null;
  return first?.title ? String(first.title) : null;
}
export function decisionWhy(plan: any) {
  const debug = plan?.score_debug || {};
  const cause = debug.decision_cause;
  const matches = Array.isArray(debug.matches) ? debug.matches : [];
  if (cause?.reason) {
    const target = matches.find((match: any) => match?.node_id === cause.target_kernel_node_id) || matches[0];
    const targetTitle = target?.title ? `“${truncate(String(target.title), 92)}”` : "your current context";
    const targetLabel = causeTargetLabel(target?.node_type || cause?.target_node_type);
    const relation = cause.operation === "CHALLENGE"
      ? `This may revise your ${targetLabel} ${targetTitle}.`
      : cause.operation === "REINFORCE"
        ? `This adds evidence to your ${targetLabel} ${targetTitle}.`
        : cause.operation === "OPEN_NEW"
          ? `This may open a new line of inquiry around your ${targetLabel} ${targetTitle}.`
          : `This bears directly on your ${targetLabel} ${targetTitle}.`;
    return `${truncate(String(cause.reason), 190)} ${relation}`;
  }

  const awareness = debug.no_delta_awareness;
  if (awareness?.applicable) {
    const events = Array.isArray(awareness.events) ? awareness.events : [];
    const event = events.find((item: any) => item?.event_id === awareness.witness_event_id) || events[0];
    const dIn = event?.D?.standing_radar_fit === "IN";
    const sMaterial = event?.S?.material_consequence === "MATERIAL";
    const p = event?.P?.collective_attention_salience;
    const radar = cleanRadarClause(event?.D?.matched_clauses?.[0]);
    const materialChange = String(event?.S?.material_changes?.[0] || "").trim();
    const sharedSystem = String(event?.S?.affected_shared_systems?.[0] || "").trim();
    const currentContext = closestContext(plan);
    if (dIn && sMaterial) {
      const concrete = materialChange
        ? `${sentenceCase(truncate(materialChange, 175)).replace(/[.]$/, "")}.`
        : sharedSystem
          ? `This materially changes ${truncate(sharedSystem, 110)}.`
          : "This materially changes a shared system you care about.";
      const standingScope = radar ? `your standing radar for ${truncate(radar, 92)}` : "your standing monitoring scope";
      const personal = currentContext
        ? `It sits inside ${standingScope} and is closest to your current context “${truncate(currentContext, 82)}”.`
        : `It sits inside ${standingScope}.`;
      const salience = p ? " It is also drawing meaningful external attention." : "";
      return `${concrete} ${personal}${salience} RAOS found no reason to revise your current working model.`;
    }
    if (sMaterial) {
      return materialChange
        ? `${truncate(materialChange, 195)} RAOS found no reason to revise your current working model.`
        : "This materially changes a shared system you care about, but RAOS found no reason to revise your current working model.";
    }
  }

  const context = closestContext(plan);
  if (context) return `RAOS kept this because it is meaningfully connected to “${truncate(context, 110)}”.`;
  return attentionAction(plan?.disposition);
}
export function briefWhy(plan: any) {
  const debug = plan?.score_debug || {};
  const awareness = debug.no_delta_awareness;
  if (awareness?.applicable) {
    const events = Array.isArray(awareness.events) ? awareness.events : [];
    const event = events.find((item: any) => item?.event_id === awareness.witness_event_id) || events[0];
    const dIn = event?.D?.standing_radar_fit === "IN";
    const sMaterial = event?.S?.material_consequence === "MATERIAL";
    const materialChange = String(event?.S?.material_changes?.[0] || "").trim();
    const sharedSystem = String(event?.S?.affected_shared_systems?.[0] || "").trim();
    const radar = cleanRadarClause(event?.D?.matched_clauses?.[0]);
    if (dIn && sMaterial && materialChange) return truncate(materialChange, 118);
    if (dIn && sMaterial && sharedSystem) return `Material change in ${truncate(sharedSystem, 92)}`;
    if (sMaterial && materialChange) return truncate(materialChange, 118);
    if (dIn && radar) return `Inside your standing radar for ${truncate(radar, 88)}`;
  }
  if (debug.decision_cause?.reason) {
    return truncate(String(debug.decision_cause.reason), 118);
  }
  return truncate(decisionWhy(plan), 112);
}

export function watchTriggerLabel(trigger: string) {
  const labels: Record<string, string> = {
    NEW_EVIDENCE: "new evidence",
    PAPER_RELEASE: "a paper release",
    CODE_RELEASE: "a code release",
    INDEPENDENT_REPLICATION: "independent replication",
  };
  return labels[trigger] || trigger.toLowerCase().replaceAll("_", " ");
}
