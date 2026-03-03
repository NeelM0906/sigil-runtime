// ============================================================
// Mission Control Data Store
// All dummy data lives here. Swap with real API calls later.
// ============================================================

export const BEINGS = [
  {
    id: 'prime',
    name: 'Prime',
    role: 'Core Orchestrator',
    avatar: 'P',
    status: 'online',
    description: 'The central runtime intelligence. Orchestrates all beings, manages task delegation, and maintains system coherence.',
    tools: ['web_search', 'web_fetch', 'code_edit', 'file_read', 'file_write', 'memory_store', 'memory_recall', 'subagent_spawn'],
    skills: ['Task Orchestration', 'Code Intelligence', 'Memory Management', 'Context Assembly', 'Self-Evaluation'],
    color: '#3b82f6',
    metrics: { tasksCompleted: 47, uptime: '12d 4h', successRate: 94 }
  },
  {
    id: 'athena',
    name: 'Athena',
    role: 'Research & Analysis',
    avatar: 'A',
    status: 'busy',
    description: 'Deep research specialist. Handles competitive intelligence, market analysis, and information synthesis across multiple sources.',
    tools: ['web_search', 'web_fetch', 'pinecone_query', 'memory_store', 'memory_recall'],
    skills: ['Prove-Ahead CI', 'Market Research', 'Data Synthesis', 'Report Generation', 'Semantic Search'],
    color: '#8b5cf6',
    metrics: { tasksCompleted: 23, uptime: '8d 12h', successRate: 89 }
  },
  {
    id: 'mylo',
    name: 'Mylo',
    role: 'Creative & Communications',
    avatar: 'M',
    status: 'online',
    description: 'Creative intelligence focused on content generation, brand voice, and communication strategy across all channels.',
    tools: ['web_search', 'web_fetch', 'memory_store', 'voice_make_call', 'voice_list_calls'],
    skills: ['Content Creation', 'Brand Voice', 'Email Drafting', 'Voice Calls', 'Social Strategy'],
    color: '#ec4899',
    metrics: { tasksCompleted: 31, uptime: '10d 2h', successRate: 91 }
  },
  {
    id: 'callie',
    name: 'Callie',
    role: 'Engineering & DevOps',
    avatar: 'C',
    status: 'online',
    description: 'Engineering specialist handling code reviews, deployments, infrastructure management, and automated testing pipelines.',
    tools: ['code_edit', 'file_read', 'file_write', 'shell_exec', 'git_ops', 'deploy_trigger'],
    skills: ['Code Review', 'CI/CD Pipelines', 'Infrastructure', 'Testing', 'Performance Optimization'],
    color: '#10b981',
    metrics: { tasksCompleted: 56, uptime: '12d 4h', successRate: 97 }
  },
  {
    id: 'sentinel',
    name: 'Sentinel',
    role: 'Security & Governance',
    avatar: 'S',
    status: 'offline',
    description: 'Security and governance watchdog. Monitors tool usage patterns, enforces policies, and performs risk assessments on high-impact operations.',
    tools: ['memory_recall', 'policy_check', 'audit_log', 'risk_assess'],
    skills: ['Policy Enforcement', 'Risk Assessment', 'Audit Trails', 'Anomaly Detection', 'Compliance'],
    color: '#f59e0b',
    metrics: { tasksCompleted: 12, uptime: '0d 0h', successRate: 100 }
  }
];

export const TASK_STATUSES = ['backlog', 'in_progress', 'in_review', 'done'];

export const TASKS = [
  {
    id: 'task-001',
    title: 'Implement Mission Control Dashboard',
    description: 'Build a React + Tailwind mission control dashboard with beings registry, task board, chat, and sub-agent tracker.',
    status: 'in_progress',
    priority: 'critical',
    assignees: ['prime', 'callie'],
    created: '2026-03-02T10:00:00Z',
    updated: '2026-03-02T14:30:00Z',
  },
  {
    id: 'task-002',
    title: 'Prove-Ahead Q1 Competitive Report',
    description: 'Run full competitive intelligence sweep for Q1 2026. Analyze top 5 competitors, pricing shifts, and feature launches.',
    status: 'in_progress',
    priority: 'high',
    assignees: ['athena'],
    created: '2026-02-28T09:00:00Z',
    updated: '2026-03-01T16:00:00Z',
  },
  {
    id: 'task-003',
    title: 'Voice Pipeline Integration Tests',
    description: 'Write and run integration tests for the ElevenLabs + Twilio voice pipeline. Cover inbound/outbound call flows.',
    status: 'in_review',
    priority: 'medium',
    assignees: ['callie', 'mylo'],
    created: '2026-02-27T11:00:00Z',
    updated: '2026-03-01T10:00:00Z',
  },
  {
    id: 'task-004',
    title: 'Memory Consolidation Optimization',
    description: 'Optimize semantic memory consolidation to reduce contradiction detection latency from 200ms to under 50ms.',
    status: 'backlog',
    priority: 'medium',
    assignees: ['prime'],
    created: '2026-03-01T08:00:00Z',
    updated: '2026-03-01T08:00:00Z',
  },
  {
    id: 'task-005',
    title: 'Brand Voice Guidelines v2',
    description: 'Update brand voice guidelines based on Q4 feedback. Include new tone variants for technical vs casual contexts.',
    status: 'backlog',
    priority: 'low',
    assignees: ['mylo'],
    created: '2026-02-25T14:00:00Z',
    updated: '2026-02-25T14:00:00Z',
  },
  {
    id: 'task-006',
    title: 'Governance Policy Audit',
    description: 'Audit all tool governance policies. Verify risk thresholds, approval flows, and logging compliance.',
    status: 'done',
    priority: 'high',
    assignees: ['sentinel', 'prime'],
    created: '2026-02-20T10:00:00Z',
    updated: '2026-02-26T17:00:00Z',
  },
  {
    id: 'task-007',
    title: 'Colosseum Tournament Results Analysis',
    description: 'Analyze results from Colosseum v2 tournament run. Extract being performance rankings and judge calibration data.',
    status: 'done',
    priority: 'medium',
    assignees: ['athena'],
    created: '2026-02-22T09:00:00Z',
    updated: '2026-02-24T15:00:00Z',
  },
];

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

// Helper to get being by ID
export function getBeingById(id) {
  return BEINGS.find(b => b.id === id) || null;
}

// Helper to get tasks by status
export function getTasksByStatus(status) {
  return TASKS.filter(t => t.status === status);
}

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
