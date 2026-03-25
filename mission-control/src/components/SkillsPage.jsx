import { useState, useEffect, useCallback } from 'react'
import { skillsApi } from '../api'

const STATUS_BADGE = {
  active: 'bg-accent-green/15 text-accent-green border-accent-green/30',
  validated: 'bg-accent-blue/15 text-accent-blue border-accent-blue/30',
  draft: 'bg-text-muted/15 text-text-muted border-text-muted/30',
  archived: 'bg-accent-red/15 text-accent-red border-accent-red/30',
}

const SOURCE_BADGE = {
  database: 'bg-text-muted/15 text-text-muted border-text-muted/30',
  filesystem: 'bg-accent-amber/15 text-accent-amber border-accent-amber/30',
  workspace: 'bg-accent-purple/15 text-accent-purple border-accent-purple/30',
}

const RISK_COLOR = {
  low: 'text-accent-green',
  medium: 'text-accent-amber',
  high: 'text-accent-red',
  critical: 'text-accent-red font-bold',
}

const SAMPLE_SKILL = `You are a contract analysis assistant.

When the user provides a contract document, analyze it for:
1. Key terms and conditions
2. Payment/reimbursement rates
3. Escalation clauses
4. Notable exclusions or limitations

Format your analysis as a structured markdown report with sections for each area.`

// ── Installed Skills Tab ──────────────────────────────────────

function InstalledTab() {
  const [skills, setSkills] = useState([])
  const [search, setSearch] = useState('')
  const [expanded, setExpanded] = useState(null)
  const [loading, setLoading] = useState(true)

  const fetchSkills = useCallback(async () => {
    try {
      const { skills: s } = await skillsApi.list()
      setSkills(s || [])
    } catch (err) {
      console.error('Failed to fetch skills:', err)
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => { fetchSkills() }, [fetchSkills])

  const filtered = skills.filter(s =>
    !search || s.name?.toLowerCase().includes(search.toLowerCase()) ||
    s.description?.toLowerCase().includes(search.toLowerCase()) ||
    s.skill_id?.toLowerCase().includes(search.toLowerCase())
  )

  if (loading) return <div className="text-text-muted text-sm p-4">Loading skills...</div>

  return (
    <div>
      <div className="flex items-center gap-2 mb-4">
        <input
          type="text"
          value={search}
          onChange={e => setSearch(e.target.value)}
          placeholder="Search installed skills..."
          className="flex-1 px-3 py-2 bg-bg-card border border-border rounded text-sm text-text-primary placeholder:text-text-muted focus:outline-none focus:border-accent-blue"
        />
        <span className="text-xs text-text-muted">{filtered.length} skills</span>
      </div>

      {filtered.length === 0 ? (
        <div className="text-center py-12 text-text-muted">
          <p className="text-sm">No skills installed yet.</p>
          <p className="text-xs mt-1">Create one or browse the catalog.</p>
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-3">
          {filtered.map(skill => (
            <div
              key={skill.skill_id}
              className="bg-bg-card border border-border rounded-lg p-3 hover:border-border-bright transition-colors cursor-pointer"
              onClick={() => setExpanded(expanded === skill.skill_id ? null : skill.skill_id)}
            >
              <div className="flex items-center justify-between mb-2">
                <h3 className="text-sm font-semibold truncate">{skill.name || skill.skill_id}</h3>
                <div className="flex items-center gap-1.5">
                  <span className={`px-1.5 py-0.5 text-[10px] font-bold rounded border ${STATUS_BADGE[skill.status] || STATUS_BADGE.draft}`}>
                    {skill.status?.toUpperCase()}
                  </span>
                  {skill.risk_level && (
                    <span className={`text-[10px] ${RISK_COLOR[skill.risk_level] || ''}`}>
                      {skill.risk_level}
                    </span>
                  )}
                </div>
              </div>
              <p className="text-xs text-text-secondary line-clamp-2 mb-2">{skill.description}</p>
              <div className="flex items-center justify-between text-[10px] text-text-muted">
                <span className={`px-1.5 py-0.5 rounded border ${SOURCE_BADGE[skill.source] || SOURCE_BADGE.database}`}>
                  {skill.source}
                </span>
                <span className="font-mono">v{skill.version || '1.0.0'}</span>
              </div>

              {expanded === skill.skill_id && (
                <div className="mt-3 pt-3 border-t border-border">
                  <div className="text-[10px] text-text-muted mb-1 uppercase tracking-wider">Skill ID</div>
                  <code className="text-xs text-text-secondary font-mono">{skill.skill_id}</code>
                  {skill.intent_tags?.length > 0 && (
                    <div className="mt-2">
                      <div className="text-[10px] text-text-muted mb-1 uppercase tracking-wider">Intent Tags</div>
                      <div className="flex flex-wrap gap-1">
                        {skill.intent_tags.map(t => (
                          <span key={t} className="px-1.5 py-0.5 text-[10px] bg-bg-hover rounded text-text-secondary">{t}</span>
                        ))}
                      </div>
                    </div>
                  )}
                </div>
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  )
}

// ── Create Tab ──────────────────────────────────────────────

function CreateTab({ onCreated }) {
  const [form, setForm] = useState({
    name: '',
    description: '',
    body: '',
    user_invocable: true,
    disable_model_invocation: false,
    risk_level: 'low',
  })
  const [copied, setCopied] = useState(false)

  const skillId = form.name.trim().toLowerCase().replace(/[^a-z0-9_-]+/g, '-').replace(/^-|-$/g, '') || 'new-skill'

  const generatedMd = `---
name: ${skillId}
description: ${form.description}
user-invocable: ${form.user_invocable}
disable-model-invocation: ${form.disable_model_invocation}
risk-level: ${form.risk_level}
---
${form.body}`

  const handleCopy = () => {
    navigator.clipboard.writeText(generatedMd).then(() => {
      setCopied(true)
      setTimeout(() => setCopied(false), 2000)
    })
  }

  const loadTemplate = () => {
    setForm({
      name: 'contract-analysis',
      description: 'Analyze provider-carrier contracts for reimbursement rates, terms, and escalation clauses.',
      body: SAMPLE_SKILL,
      user_invocable: true,
      disable_model_invocation: false,
      risk_level: 'low',
    })
  }

  return (
    <div className="max-w-2xl">
      <div className="flex items-center justify-between mb-4">
        <h3 className="text-sm font-semibold">Create New Skill</h3>
        <button
          onClick={loadTemplate}
          className="px-3 py-1 text-xs text-accent-purple hover:text-accent-purple/80 border border-accent-purple/30 rounded transition-colors"
        >
          Load Template
        </button>
      </div>

      <div className="flex flex-col gap-3">
        <div>
          <label className="text-[10px] uppercase tracking-wider text-text-muted block mb-1">Name</label>
          <input
            type="text"
            value={form.name}
            onChange={e => setForm({ ...form, name: e.target.value })}
            placeholder="e.g. contract-analysis"
            className="w-full px-3 py-2 bg-bg-card border border-border rounded text-sm text-text-primary placeholder:text-text-muted focus:outline-none focus:border-accent-blue"
          />
          <span className="text-[10px] text-text-muted mt-0.5 block">Skill ID: {skillId}</span>
        </div>

        <div>
          <label className="text-[10px] uppercase tracking-wider text-text-muted block mb-1">Description</label>
          <input
            type="text"
            value={form.description}
            onChange={e => setForm({ ...form, description: e.target.value })}
            placeholder="What does this skill do?"
            className="w-full px-3 py-2 bg-bg-card border border-border rounded text-sm text-text-primary placeholder:text-text-muted focus:outline-none focus:border-accent-blue"
          />
        </div>

        <div>
          <label className="text-[10px] uppercase tracking-wider text-text-muted block mb-1">Body (Instructions)</label>
          <textarea
            value={form.body}
            onChange={e => setForm({ ...form, body: e.target.value })}
            placeholder="Write the skill instructions in markdown..."
            rows={12}
            className="w-full px-3 py-2 bg-bg-card border border-border rounded text-sm text-text-primary placeholder:text-text-muted focus:outline-none focus:border-accent-blue font-mono resize-y"
          />
        </div>

        <div className="flex items-center gap-4">
          <label className="flex items-center gap-2 text-xs text-text-secondary cursor-pointer">
            <input
              type="checkbox"
              checked={form.user_invocable}
              onChange={e => setForm({ ...form, user_invocable: e.target.checked })}
              className="rounded"
            />
            User Invocable
          </label>
          <label className="flex items-center gap-2 text-xs text-text-secondary cursor-pointer">
            <input
              type="checkbox"
              checked={form.disable_model_invocation}
              onChange={e => setForm({ ...form, disable_model_invocation: e.target.checked })}
              className="rounded"
            />
            Disable Model Invocation
          </label>
          <select
            value={form.risk_level}
            onChange={e => setForm({ ...form, risk_level: e.target.value })}
            className="px-2 py-1 bg-bg-card border border-border rounded text-xs text-text-primary"
          >
            <option value="low">Low Risk</option>
            <option value="medium">Medium Risk</option>
            <option value="high">High Risk</option>
          </select>
        </div>

        {/* SKILL.md Preview */}
        {form.name && (
          <div>
            <label className="text-[10px] uppercase tracking-wider text-text-muted block mb-1">SKILL.md Preview</label>
            <pre className="w-full px-3 py-2 bg-bg-primary border border-border rounded text-[11px] text-text-secondary font-mono overflow-x-auto max-h-48 overflow-y-auto">
              {generatedMd}
            </pre>
          </div>
        )}

        <div className="flex justify-between items-center">
          <p className="text-xs text-text-muted">
            Copy the SKILL.md below, or ask a being to create it using skill_create.
          </p>
          <button
            onClick={handleCopy}
            disabled={!form.name.trim() || !form.description.trim()}
            className="px-4 py-2 text-xs font-medium bg-accent-blue text-white rounded hover:bg-accent-blue/80 disabled:opacity-30 transition-colors"
          >
            {copied ? 'Copied!' : 'Copy SKILL.md'}
          </button>
        </div>
      </div>
    </div>
  )
}

// ── Main Page ───────────────────────────────────────────────

const TAB_CONFIG = [
  { id: 'installed', label: 'Installed' },
  { id: 'create', label: 'Create' },
]

export function SkillsPage() {
  const [tab, setTab] = useState('installed')

  return (
    <div>
      {/* Tab bar */}
      <div className="flex items-center gap-1 mb-4 border-b border-border pb-2">
        {TAB_CONFIG.map(t => (
          <button
            key={t.id}
            onClick={() => setTab(t.id)}
            className={`px-3 py-1.5 text-xs font-medium rounded-t transition-colors ${
              tab === t.id
                ? 'text-accent-purple border-b-2 border-accent-purple'
                : 'text-text-muted hover:text-text-primary'
            }`}
          >
            {t.label}
          </button>
        ))}
      </div>

      {/* Tab content */}
      {tab === 'installed' && <InstalledTab />}
      {tab === 'create' && <CreateTab onCreated={() => setTab('installed')} />}
    </div>
  )
}
