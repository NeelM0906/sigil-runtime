// ============================================================
// Mission Control Data Store
// Static constants only — all data now lives in BOMBA SR runtime.
// ============================================================

export const TASK_STATUSES = ['backlog', 'in_progress', 'in_review', 'done'];

// Helper to format relative time
export function timeAgo(dateStr) {
  const now = new Date();
  const date = new Date(dateStr);
  const diff = Math.floor((now - date) / 1000);
  if (diff < 60) return 'just now';
  if (diff < 3600) return `${Math.floor(diff / 60)}m ago`;
  if (diff < 86400) return `${Math.floor(diff / 3600)}h ago`;
  return `${Math.floor(diff / 86400)}d ago`;
}
