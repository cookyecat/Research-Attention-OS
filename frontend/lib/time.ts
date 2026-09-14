const BACKEND_NAIVE = /^\d{4}-\d{2}-\d{2}[ T]\d{2}:\d{2}:\d{2}(?:\.\d+)?$/;

export function parseRaosTime(value?: string | null) {
  if (!value) return null;
  const normalized = BACKEND_NAIVE.test(value)
    ? `${value.replace(" ", "T")}Z`
    : value;
  const date = new Date(normalized);
  return Number.isNaN(date.getTime()) ? null : date;
}

export function formatBeijingTime(value?: string | null) {
  const date = parseRaosTime(value);
  if (!date) return value || "";
  return new Intl.DateTimeFormat("zh-CN", {
    timeZone: "Asia/Shanghai",
    year: "numeric",
    month: "numeric",
    day: "numeric",
    hour: "2-digit",
    minute: "2-digit",
    hour12: false,
  }).format(date);
}

export function formatRelativeTime(value?: string | null) {
  const date = parseRaosTime(value);
  if (!date) return "";
  const delta = Date.now() - date.getTime();
  const minutes = Math.round(delta / 60000);
  if (Math.abs(minutes) < 1) return "just now";
  if (minutes < 60 && minutes >= 0) return `${minutes}m ago`;
  const hours = Math.round(minutes / 60);
  if (hours < 24 && hours >= 0) return `${hours}h ago`;
  const days = Math.round(hours / 24);
  if (days < 7 && days >= 0) return `${days}d ago`;
  return formatBeijingTime(value);
}

export function timestampMs(value?: string | null) {
  return parseRaosTime(value)?.getTime() || 0;
}
