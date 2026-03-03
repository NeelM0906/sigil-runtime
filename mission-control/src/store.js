// ============================================================
// Mission Control Data Store
// Static data only — beings and tasks now live in API/JSON.
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

export const CHAT_MESSAGES = [
  {
    id: 'msg-001',
    sender: 'user',
    targets: [],
    content: 'Good morning team. Status update on all active tasks?',
    timestamp: '2026-03-02T09:00:00Z',
    mode: null,
  },
  {
    id: 'msg-002',
    sender: 'prime',
    targets: [],
    content: 'Morning. We have 2 tasks in progress, 1 in review, 2 in backlog, and 2 completed. The Mission Control dashboard build is our top priority today. Athena is running the Q1 competitive sweep with 3 sub-agents active.',
    timestamp: '2026-03-02T09:01:00Z',
    mode: null,
  },
  {
    id: 'msg-003',
    sender: 'user',
    targets: ['athena'],
    content: '@athena How\'s the competitive report looking? Any early signals?',
    timestamp: '2026-03-02T09:05:00Z',
    mode: null,
  },
  {
    id: 'msg-004',
    sender: 'athena',
    targets: [],
    content: 'Two sub-agents running: Market Scanner at 65% (pricing data), Feature Diff at 42% (feature comparison). Early signal: Competitor B dropped enterprise pricing 15% last week. Deep Pricing Crawler hit a rate limit and failed — I\'ll retry with staggered requests.',
    timestamp: '2026-03-02T09:06:00Z',
    mode: null,
  },
  {
    id: 'msg-005',
    sender: 'user',
    targets: ['callie', 'mylo'],
    content: '@callie @mylo Can you two work on the voice pipeline tests in parallel? Callie handles the integration harness, Mylo tests the actual call flows.',
    timestamp: '2026-03-02T09:10:00Z',
    mode: 'parallel',
  },
  {
    id: 'msg-006',
    sender: 'callie',
    targets: [],
    content: 'On it. I\'ll set up the test harness with mock Twilio endpoints. Should have the framework ready in 30 minutes.',
    timestamp: '2026-03-02T09:11:00Z',
    mode: null,
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
