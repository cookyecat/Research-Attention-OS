export const VISIT_CONTINUITY_EVENT = "raos:visit-continuity";

const LAST_ACTIVE_KEY = "raos-user-space-last-active-at";
const PREVIOUS_VISIT_KEY = "raos-user-space-previous-visit-at";
const SESSION_START_KEY = "raos-user-space-session-start-at";
const LEGACY_TODAY_VISIT_KEY = "raos-today-last-visit";
const SESSION_GAP_MS = 30 * 60 * 1000;

export type VisitContinuity = {
  previousVisitAt: number | null;
  sessionStartAt: number | null;
  lastActiveAt: number | null;
};

function numberValue(value: string | null) {
  const parsed = Number(value || 0);
  return Number.isFinite(parsed) && parsed > 0 ? parsed : null;
}

export function readVisitContinuity(): VisitContinuity {
  if (typeof window === "undefined") return { previousVisitAt: null, sessionStartAt: null, lastActiveAt: null };
  return {
    previousVisitAt: numberValue(localStorage.getItem(PREVIOUS_VISIT_KEY)),
    sessionStartAt: numberValue(localStorage.getItem(SESSION_START_KEY)),
    lastActiveAt: numberValue(localStorage.getItem(LAST_ACTIVE_KEY)),
  };
}
export function touchVisitContinuity(now = Date.now()): VisitContinuity {
  if (typeof window === "undefined") return { previousVisitAt: null, sessionStartAt: null, lastActiveAt: null };
  let { previousVisitAt, sessionStartAt, lastActiveAt } = readVisitContinuity();
  const legacyVisit = numberValue(localStorage.getItem(LEGACY_TODAY_VISIT_KEY));
  if (!previousVisitAt && !lastActiveAt && legacyVisit) {
    previousVisitAt = legacyVisit;
    localStorage.setItem(PREVIOUS_VISIT_KEY, String(legacyVisit));
  }
  const startsNewSession = !sessionStartAt || !lastActiveAt || now - lastActiveAt > SESSION_GAP_MS;

  if (startsNewSession) {
    if (lastActiveAt) {
      previousVisitAt = lastActiveAt;
      localStorage.setItem(PREVIOUS_VISIT_KEY, String(lastActiveAt));
    }
    sessionStartAt = now;
    localStorage.setItem(SESSION_START_KEY, String(now));
  }

  lastActiveAt = now;
  localStorage.setItem(LAST_ACTIVE_KEY, String(now));
  const state = { previousVisitAt, sessionStartAt, lastActiveAt };
  window.dispatchEvent(new CustomEvent(VISIT_CONTINUITY_EVENT, { detail: state }));
  return state;
}

export function formatVisitClock(timestamp: number | null) {
  if (!timestamp) return null;
  return new Intl.DateTimeFormat(undefined, { hour: "2-digit", minute: "2-digit" }).format(new Date(timestamp));
}