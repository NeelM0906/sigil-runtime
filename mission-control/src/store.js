// ============================================================
// Mission Control Data Store
// Static data only — beings, tasks, and chat now live in API/JSON.
// ============================================================

export const TASK_STATUSES = ['backlog', 'in_progress', 'in_review', 'done'];

export const SUBAGENTS = [
  {
    id: 'sa-001',
    parentTask: 'task-002',
    name: 'Market Scanner Alpha',
    spawnedBy: 'athena',
    status: 'running',
    progress: 65,
    goal: 'Scan competitor pricing pages and changelog feeds',
    started: '2026-03-02T13:00:00Z',
    depth: 1,
  },
  {
    id: 'sa-002',
    parentTask: 'task-002',
    name: 'Feature Diff Analyzer',
    spawnedBy: 'athena',
    status: 'running',
    progress: 42,
    goal: 'Compare feature matrices across top 5 competitors',
    started: '2026-03-02T13:05:00Z',
    depth: 1,
  },
  {
    id: 'sa-003',
    parentTask: 'task-001',
    name: 'Component Scaffolder',
    spawnedBy: 'callie',
    status: 'complete',
    progress: 100,
    goal: 'Generate base React components for dashboard panels',
    started: '2026-03-02T10:30:00Z',
    depth: 1,
  },
  {
    id: 'sa-004',
    parentTask: 'task-003',
    name: 'Voice Test Runner',
    spawnedBy: 'callie',
    status: 'waiting',
    progress: 0,
    goal: 'Execute voice pipeline integration test suite',
    started: '2026-03-02T12:00:00Z',
    depth: 1,
  },
  {
    id: 'sa-005',
    parentTask: 'task-002',
    name: 'Deep Pricing Crawler',
    spawnedBy: 'athena',
    status: 'failed',
    progress: 23,
    goal: 'Crawl archived pricing snapshots from Wayback Machine',
    started: '2026-03-02T13:10:00Z',
    depth: 2,
  },
];

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
