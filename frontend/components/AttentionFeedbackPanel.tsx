"use client";

import { useEffect, useMemo, useState } from "react";
import { api } from "@/lib/api";

type CognitiveUpdate = {
  operation?: string | null;
  target_node_id?: string | null;
};

type Prediction = {
  disposition?: string;
  update?: CognitiveUpdate;
  delta_content?: string;
};

type Feedback = {
  id: string;
  kind: "CONFIRM" | "CORRECT";
  system_prediction: Prediction;
  user_correction: Prediction;
  corrected_fields: string[];
  created_at?: string;
};

type KernelNode = { id: string; title: string; node_type?: string };

const DISPOSITIONS = ["DROP", "AWARE", "WATCH", "ENGAGE"];
const OPERATIONS = ["REINFORCE", "CHALLENGE", "OPEN_NEW"];

function predictionFromAnalysis(analysis: Record<string, unknown>): Prediction {
  const plan = (analysis.attention_plan || {}) as Record<string, unknown>;
  const update = (analysis.update || plan.update || {}) as CognitiveUpdate;
  const delta =
    (analysis.delta_content as string) ||
    ((analysis.model_delta as Record<string, unknown> | undefined)?.summary as string) ||
    "";
  return {
    disposition: (analysis.disposition as string) || (plan.disposition as string),
    update: {
      operation: update.operation || null,
      target_node_id: update.target_node_id || null,
    },
    delta_content: delta,
  };
}

export default function AttentionFeedbackPanel({
  planId,
  analysis,
  onSubmitted,
}: {
  planId: string;
  analysis: Record<string, unknown>;
  onSubmitted: () => Promise<void> | void;
}) {
  const system = useMemo(() => predictionFromAnalysis(analysis), [analysis]);
  const latest = analysis.latest_attention_feedback as Feedback | null | undefined;

  const [open, setOpen] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [disposition, setDisposition] = useState(system.disposition || "AWARE");
  const [operation, setOperation] = useState(system.update?.operation || "OPEN_NEW");
  const [targetNodeId, setTargetNodeId] = useState(system.update?.target_node_id || "");
  const [deltaContent, setDeltaContent] = useState(system.delta_content || "");
  const [kernelNodes, setKernelNodes] = useState<KernelNode[]>([]);

  useEffect(() => {
    setDisposition(system.disposition || "AWARE");
    setOperation(system.update?.operation || "OPEN_NEW");
    setTargetNodeId(system.update?.target_node_id || "");
    setDeltaContent(system.delta_content || "");
  }, [system]);

  useEffect(() => {
    api<Record<string, KernelNode[]>>("/kernel")
      .then((k) => {
        const flat: KernelNode[] = [];
        for (const [nodeType, nodes] of Object.entries(k)) {
          for (const n of nodes || []) {
            flat.push({ id: n.id, title: n.title, node_type: nodeType });
          }
        }
        setKernelNodes(flat);
      })
      .catch(() => undefined);
  }, []);

  const matchNodes = useMemo(() => {
    const matches = (analysis.kernel_matches as Array<{ node_id: string; title: string; node_type?: string }>) || [];
    const byId = new Map(kernelNodes.map((n) => [n.id, n]));
    for (const m of matches) {
      if (!byId.has(m.node_id)) {
        byId.set(m.node_id, { id: m.node_id, title: m.title, node_type: m.node_type });
      }
    }
    return [...byId.values()];
  }, [analysis.kernel_matches, kernelNodes]);

  async function submit(kind: "CONFIRM" | "CORRECT") {
    setBusy(true);
    setError(null);
    try {
      const body: Record<string, unknown> = { kind };
      if (kind === "CORRECT") {
        if (disposition !== system.disposition) body.disposition = disposition;
        const sysOp = system.update?.operation || null;
        const sysTarget = system.update?.target_node_id || null;
        const opChanged = operation !== sysOp;
        const targetChanged =
          (operation === "REINFORCE" || operation === "CHALLENGE") &&
          (targetNodeId || null) !== (sysTarget || null);
        const opSwitchToOpenNew = operation === "OPEN_NEW" && sysOp !== "OPEN_NEW";
        if (opChanged || targetChanged || opSwitchToOpenNew) {
          body.update = {
            operation,
            target_node_id: operation === "OPEN_NEW" ? null : targetNodeId || null,
          };
        }
        if ((deltaContent || "") !== (system.delta_content || "")) {
          body.delta_content = deltaContent;
        }
      }
      await api(`/analysis/attention-plans/${planId}/feedback`, {
        method: "POST",
        body: JSON.stringify(body),
      });
      setOpen(false);
      await onSubmitted();
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : String(e));
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="card">
      <h3>Human feedback</h3>
      <p className="lede">
        Confirm or correct the system judgment. Corrections are stored alongside the original prediction — they do not rewrite the AnalysisRun or mutate the Kernel.
      </p>
      <div className="row">
        <span className="badge">{system.disposition}</span>
        {system.update?.operation && (
          <span className="badge">
            {system.update.operation}
            {system.update.target_node_id ? ` → ${system.update.target_node_id.slice(0, 8)}…` : ""}
          </span>
        )}
      </div>
      {system.delta_content && <p>{system.delta_content}</p>}
      {latest && (
        <p className="lede">
          Recorded {latest.kind.toLowerCase()}
          {latest.corrected_fields.length > 0 && ` · changed ${latest.corrected_fields.join(", ")}`}
          {latest.created_at ? ` · ${new Date(latest.created_at).toLocaleString()}` : ""}
        </p>
      )}
      {error && <p className="error">{error}</p>}
      <div className="actions">
        <button disabled={busy} onClick={() => submit("CONFIRM")}>
          Confirm
        </button>
        <button disabled={busy} className="ghost" onClick={() => setOpen((v) => !v)}>
          {open ? "Hide correct" : "Correct it"}
        </button>
      </div>
      {open && (
        <div className="modify-form">
          <label>Disposition</label>
          <select value={disposition} onChange={(e) => setDisposition(e.target.value)}>
            {DISPOSITIONS.map((d) => (
              <option key={d} value={d}>
                {d}
              </option>
            ))}
          </select>
          <label>Update operation</label>
          <select value={operation} onChange={(e) => setOperation(e.target.value)}>
            {OPERATIONS.map((o) => (
              <option key={o} value={o}>
                {o}
              </option>
            ))}
          </select>
          {(operation === "REINFORCE" || operation === "CHALLENGE") && (
            <>
              <label>Target node</label>
              <select value={targetNodeId} onChange={(e) => setTargetNodeId(e.target.value)}>
                <option value="">Select kernel node…</option>
                {matchNodes.map((n) => (
                  <option key={n.id} value={n.id}>
                    [{n.node_type}] {n.title}
                  </option>
                ))}
              </select>
            </>
          )}
          <label>Delta content</label>
          <textarea value={deltaContent} onChange={(e) => setDeltaContent(e.target.value)} rows={4} />
          <div className="actions">
            <button disabled={busy} onClick={() => submit("CORRECT")}>
              Save correction
            </button>
          </div>
        </div>
      )}
    </div>
  );
}
