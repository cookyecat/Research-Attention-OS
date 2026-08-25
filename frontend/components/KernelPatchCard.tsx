"use client";

import { useMemo, useState } from "react";
import { api } from "@/lib/api";

type Patch = {
  id: string;
  status: string;
  change_type: string;
  target_object_type: string;
  reasoning: string;
  proposed_state?: {
    title?: string;
    status?: string;
    payload?: Record<string, unknown>;
  };
};

export default function KernelPatchCard({
  patch,
  onCommitted,
}: {
  patch: Patch;
  onCommitted: () => Promise<void> | void;
}) {
  const payload = patch.proposed_state?.payload || {};
  const [open, setOpen] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [status, setStatus] = useState(String(patch.proposed_state?.status || payload.status || "ACTIVE"));
  const [proposition, setProposition] = useState(String(payload.proposition || ""));
  const [confidence, setConfidence] = useState(
    payload.confidence == null ? "" : String(payload.confidence)
  );
  const [scope, setScope] = useState(String(payload.scope || ""));
  const [description, setDescription] = useState(String(payload.description || ""));
  const [questionText, setQuestionText] = useState(String(payload.text || patch.proposed_state?.title || ""));
  const [rationale, setRationale] = useState(String(payload.rationale || patch.reasoning || ""));

  const proposed = useMemo(() => patch.proposed_state || {}, [patch.proposed_state]);

  async function act(action: "accept" | "reject") {
    setBusy(true);
    setError(null);
    try {
      await api(`/kernel/patches/${patch.id}/${action}`, { method: "POST" });
      await onCommitted();
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : String(e));
    } finally {
      setBusy(false);
    }
  }

  async function modify() {
    setBusy(true);
    setError(null);
    const nextPayload: Record<string, unknown> = { ...payload };
    if (proposition) nextPayload.proposition = proposition;
    if (confidence !== "") nextPayload.confidence = Number(confidence);
    if (scope) nextPayload.scope = scope;
    if (description) nextPayload.description = description;
    if (questionText) nextPayload.text = questionText;
    if (rationale) nextPayload.rationale = rationale;
    if (status) nextPayload.status = status;
    const modified_state: Record<string, unknown> = {
      ...proposed,
      status,
      payload: nextPayload,
    };
    if (questionText && patch.target_object_type === "QUESTION") {
      modified_state.title = questionText;
    }
    if (proposition && patch.target_object_type === "BELIEF") {
      modified_state.title = proposition;
    }
    if (description && patch.target_object_type === "MODEL") {
      modified_state.title = proposed.title || description.slice(0, 120);
    }
    try {
      await api(`/kernel/patches/${patch.id}/modify`, {
        method: "POST",
        body: JSON.stringify({ modified_state }),
      });
      await onCommitted();
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : String(e));
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="card">
      <div className="row">
        <span className="badge">{patch.status}</span>
        <span className="badge">{patch.change_type}</span>
        <span className="badge">{patch.target_object_type}</span>
      </div>
      <p>{patch.reasoning}</p>
      {proposed.title && <p className="lede">{String(proposed.title)}</p>}
      {error && <p className="error">{error}</p>}
      {patch.status === "PROPOSED" && (
        <>
          <div className="actions">
            <button disabled={busy} onClick={() => act("accept")}>Accept</button>
            <button disabled={busy} className="ghost" onClick={() => setOpen((v) => !v)}>
              {open ? "Hide modify" : "Modify"}
            </button>
            <button disabled={busy} className="danger" onClick={() => act("reject")}>Reject</button>
          </div>
          {open && (
            <div className="modify-form">
              <p className="lede">Modify then Human Commit. AI cannot write the Kernel directly.</p>
              <label>Status</label>
              <select value={status} onChange={(e) => setStatus(e.target.value)}>
                <option>ACTIVE</option>
                <option>OPEN</option>
                <option>CONTESTED</option>
                <option>PROPOSED</option>
                <option>WATCH</option>
              </select>
              {(patch.target_object_type === "BELIEF" || proposition) && (
                <>
                  <label>Proposed proposition</label>
                  <textarea value={proposition} onChange={(e) => setProposition(e.target.value)} />
                </>
              )}
              <label>Confidence</label>
              <input value={confidence} onChange={(e) => setConfidence(e.target.value)} placeholder="0–1" />
              <label>Scope</label>
              <input value={scope} onChange={(e) => setScope(e.target.value)} />
              {(patch.target_object_type === "MODEL" || description) && (
                <>
                  <label>Model description</label>
                  <textarea value={description} onChange={(e) => setDescription(e.target.value)} />
                </>
              )}
              {(patch.target_object_type === "QUESTION" || questionText) && (
                <>
                  <label>Question text</label>
                  <textarea value={questionText} onChange={(e) => setQuestionText(e.target.value)} />
                </>
              )}
              <label>Rationale</label>
              <textarea value={rationale} onChange={(e) => setRationale(e.target.value)} />
              <div className="actions">
                <button disabled={busy} onClick={modify}>Modify → Human Commit</button>
              </div>
            </div>
          )}
        </>
      )}
    </div>
  );
}
