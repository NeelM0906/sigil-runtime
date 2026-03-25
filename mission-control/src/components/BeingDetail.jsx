import { useState, useEffect, useCallback } from 'react'
import { useBeings } from '../context/BeingsContext'
import { tasksApi } from '../api'
import { timeAgo } from '../store'

const STATUS_COLORS = {
  online: 'bg-accent-green',
  busy: 'bg-accent-amber',
  idle: 'bg-accent-cyan',
  offline: 'bg-text-muted',
}

const STATUS_CYCLE = ['online', 'busy', 'idle', 'offline']

const TYPE_BADGES = {
  runtime: { label: 'PRIMARY', color: 'text-accent-orange bg-accent-orange/10 border-accent-orange/20' },
  sister: { label: 'SISTER', color: 'text-accent-purple bg-accent-purple/10 border-accent-purple/20' },
  voice: { label: 'VOICE', color: 'text-accent-pink bg-accent-pink/10 border-accent-pink/20' },
  subagent: { label: 'SUB-AGENT', color: 'text-accent-amber bg-accent-amber/10 border-accent-amber/20' },
  acti: { label: 'ACT-I', color: 'text-accent-cyan bg-accent-cyan/10 border-accent-cyan/20' },
}

const PRIORITY_CONFIG = {
  critical: { label: 'CRIT', bg: 'bg-accent-red/15', text: 'text-accent-red', border: 'border-accent-red/30' },
  high: { label: 'HIGH', bg: 'bg-accent-amber/15', text: 'text-accent-amber', border: 'border-accent-amber/30' },
  medium: { label: 'MED', bg: 'bg-accent-blue/15', text: 'text-accent-blue', border: 'border-accent-blue/30' },
  low: { label: 'LOW', bg: 'bg-bg-hover', text: 'text-text-muted', border: 'border-border' },
  normal: { label: 'NORM', bg: 'bg-bg-hover', text: 'text-text-secondary', border: 'border-border' },
}

const STATUS_DOT = {
  backlog: 'bg-text-muted',
  todo: 'bg-text-muted',
  in_progress: 'bg-accent-blue',
  in_review: 'bg-accent-amber',
  done: 'bg-accent-green',
}

function formatBytes(bytes) {
  if (!bytes) return '0 B'
  const k = 1024
  const sizes = ['B', 'KB', 'MB', 'GB']
  const i = Math.floor(Math.log(bytes) / Math.log(k))
  return `${(bytes / Math.pow(k, i)).toFixed(i > 0 ? 1 : 0)} ${sizes[i]}`
}

function formatDate(isoStr) {
  if (!isoStr) return 'Unknown'
  try {
    return new Date(isoStr).toLocaleDateString('en-US', {
      year: 'numeric', month: 'short', day: 'numeric',
      hour: '2-digit', minute: '2-digit',
    })
  } catch {
    return isoStr
  }
}

// ── Collapsible Section ─────────────────────────────────────

const COUNT_COLORS = {
  'accent-orange': 'text-accent-amber',
  'accent-green': 'text-accent-green',
  'accent-blue': 'text-accent-blue',
  'accent-purple': 'text-accent-purple',
  'accent-cyan': 'text-accent-cyan',
  'accent-amber': 'text-accent-amber',
}

function Section({ title, count, icon, defaultOpen = false, children, accentColor = 'accent-blue' }) {
  const [open, setOpen] = useState(defaultOpen)
  const countColorClass = COUNT_COLORS[accentColor] || 'text-accent-blue'

  return (
    <div className="border border-border rounded-lg overflow-hidden">
      <button
        onClick={() => setOpen(!open)}
        className="w-full flex items-center gap-2 px-3 py-2 bg-bg-card hover:bg-bg-hover transition-colors text-left"
      >
        <span className="text-xs">{icon}</span>
        <span className="text-[11px] font-semibold uppercase tracking-wider flex-1">{title}</span>
        {count !== undefined && (
          <span className={`text-[10px] font-mono ${countColorClass}`}>{count}</span>
        )}
        <svg
          className={`w-3.5 h-3.5 text-text-muted transition-transform ${open ? 'rotate-180' : ''}`}
          fill="none" viewBox="0 0 24 24" stroke="currentColor"
        >
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
        </svg>
      </button>
      {open && (
        <div className="p-3 border-t border-border">
          {children}
        </div>
      )}
    </div>
  )
}

// ── File Viewer Modal ───────────────────────────────────────

function FileViewer({ fileName, content, onClose }) {
  return (
    <div className="fixed inset-0 z-[60] flex items-center justify-center bg-black/50" onClick={onClose}>
      <div
        className="bg-bg-secondary border border-border-bright rounded-lg w-full max-w-2xl max-h-[80vh] flex flex-col shadow-2xl mx-4"
        onClick={e => e.stopPropagation()}
      >
        <div className="flex items-center justify-between px-4 py-2 border-b border-border">
          <span className="text-xs font-mono text-accent-cyan">{fileName}</span>
          <button onClick={onClose} className="text-text-muted hover:text-text-primary text-lg">&times;</button>
        </div>
        <div className="p-4 overflow-auto flex-1">
          <pre className="text-xs text-text-secondary font-mono whitespace-pre-wrap leading-relaxed">
            {content}
          </pre>
        </div>
      </div>
    </div>
  )
}

// ── File Tree Node ──────────────────────────────────────────

function FileTreeNode({ node, depth = 0, onFileClick }) {
  const [open, setOpen] = useState(depth < 1)
  const isDir = node.type === 'dir'
  const indent = depth * 16

  return (
    <div>
      <button
        className="w-full flex items-center gap-1.5 py-0.5 hover:bg-bg-hover rounded px-1 text-left"
        style={{ paddingLeft: `${indent + 4}px` }}
        onClick={() => {
          if (isDir) setOpen(!open)
          else onFileClick?.(node)
        }}
      >
        {isDir ? (
          <svg className={`w-3 h-3 text-text-muted shrink-0 transition-transform ${open ? 'rotate-90' : ''}`} fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5l7 7-7 7" />
          </svg>
        ) : (
          <svg className="w-3 h-3 text-text-muted shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M7 21h10a2 2 0 002-2V9.414a1 1 0 00-.293-.707l-5.414-5.414A1 1 0 0012.586 3H7a2 2 0 00-2 2v14a2 2 0 002 2z" />
          </svg>
        )}
        <span className={`text-[11px] font-mono truncate ${isDir ? 'text-accent-cyan' : 'text-text-secondary'}`}>
          {node.name}
        </span>
        {!isDir && node.size !== undefined && (
          <span className="text-[9px] text-text-muted ml-auto shrink-0">{formatBytes(node.size)}</span>
        )}
      </button>
      {isDir && open && node.children?.map((child, i) => (
        <FileTreeNode key={child.name + i} node={child} depth={depth + 1} onFileClick={onFileClick} />
      ))}
    </div>
  )
}

// ── Main Component ──────────────────────────────────────────

export function BeingDetail({ onOpenTask }) {
  const {
    selectedBeingId, closeBeingDetail, getBeingById, updateBeingStatus,
    beingDetail, detailLoading, fetchBeingFile, openBeingDetail,
  } = useBeings()

  const [assignedTasks, setAssignedTasks] = useState([])
  const [loadingTasks, setLoadingTasks] = useState(false)
  const [viewingFile, setViewingFile] = useState(null)
  const [fileContent, setFileContent] = useState(null)
  const [fileLoading, setFileLoading] = useState(false)
  const [memoryBrowsing, setMemoryBrowsing] = useState(false)
  const [memoryFiles, setMemoryFiles] = useState([])

  const being = selectedBeingId ? getBeingById(selectedBeingId) : null

  // Close on Escape key
  useEffect(() => {
    if (!selectedBeingId) return
    const handleKey = (e) => { if (e.key === 'Escape') closeBeingDetail() }
    window.addEventListener('keydown', handleKey)
    return () => window.removeEventListener('keydown', handleKey)
  }, [selectedBeingId, closeBeingDetail])

  // Fetch assigned tasks
  useEffect(() => {
    if (!being) return
    setLoadingTasks(true)
    tasksApi.list({ assignee: being.id })
      .then(({ tasks }) => setAssignedTasks(tasks))
      .catch(() => setAssignedTasks([]))
      .finally(() => setLoadingTasks(false))
  }, [being?.id])

  // Reset state on close
  useEffect(() => {
    if (!selectedBeingId) {
      setViewingFile(null)
      setFileContent(null)
      setMemoryBrowsing(false)
      setMemoryFiles([])
    }
  }, [selectedBeingId])

  const handleViewFile = useCallback(async (fileName, relPath) => {
    setViewingFile(fileName)
    setFileLoading(true)
    setFileContent(null)
    const content = await fetchBeingFile(selectedBeingId, relPath)
    setFileContent(content || '[Unable to load file content]')
    setFileLoading(false)
  }, [selectedBeingId, fetchBeingFile])

  const handleBrowseMemory = useCallback(async () => {
    if (!beingDetail?.memory?.files) return
    setMemoryBrowsing(true)
    setMemoryFiles(beingDetail.memory.files)
  }, [beingDetail])

  if (!being) return null

  const detail = beingDetail
  const identity = detail?.identity
  const memory = detail?.memory
  const tools = detail?.tools || []
  const skills = detail?.skills || []
  const fileTree = detail?.file_tree || []
  const typeBadge = TYPE_BADGES[being.type] || TYPE_BADGES.runtime

  const handleStatusToggle = () => {
    const currentIdx = STATUS_CYCLE.indexOf(being.status)
    const nextStatus = STATUS_CYCLE[(currentIdx + 1) % STATUS_CYCLE.length]
    updateBeingStatus(being.id, nextStatus)
  }

  const activeTasks = assignedTasks.filter(t => t.status === 'in_progress' || t.status === 'in_review')
  const otherTasks = assignedTasks.filter(t => t.status !== 'in_progress' && t.status !== 'in_review')

  return (
    <>
      <div className="fixed inset-0 z-50 flex justify-end bg-black/40" onClick={closeBeingDetail}>
        <div
          className="w-full max-w-lg bg-bg-secondary border-l border-border-bright h-full overflow-y-auto shadow-2xl"
          onClick={e => e.stopPropagation()}
        >
          {/* ── Header ────────────────────────────────────── */}
          <div className="sticky top-0 bg-bg-secondary border-b border-border z-10">
            <div className="px-4 py-3 flex items-center justify-between">
              <div className="flex items-center gap-3">
                <div
                  className="w-11 h-11 rounded-lg flex items-center justify-center text-lg font-bold"
                  style={{ backgroundColor: being.color + '22', color: being.color }}
                >
                  {being.avatar}
                </div>
                <div>
                  <div className="flex items-center gap-2">
                    <h2 className="text-sm font-semibold">{being.name}</h2>
                    <span className={`px-1.5 py-0 text-[9px] font-bold rounded border ${typeBadge.color}`}>
                      {typeBadge.label}
                    </span>
                  </div>
                  <div className="text-xs text-text-secondary mt-0.5">{being.role}</div>
                </div>
              </div>
              <button onClick={closeBeingDetail} className="text-text-muted hover:text-text-primary text-xl leading-none">&times;</button>
            </div>

            {/* Status bar */}
            <div className="px-4 pb-3 flex items-center gap-3 flex-wrap">
              <button
                onClick={handleStatusToggle}
                className="flex items-center gap-1.5 px-2 py-1 rounded border border-border bg-bg-card hover:bg-bg-hover transition-colors text-xs"
                title="Click to toggle status"
              >
                <div className={`w-2 h-2 rounded-full ${STATUS_COLORS[being.status]}`} />
                <span className="uppercase text-[10px] font-mono">{being.status}</span>
              </button>
              {being.model_id && (
                <span className="text-[10px] font-mono text-text-muted">{being.model_id}</span>
              )}
              {being.tenant_id && (
                <span className="text-[10px] font-mono text-text-muted px-1.5 py-0.5 rounded bg-bg-card border border-border">
                  {being.tenant_id}
                </span>
              )}
            </div>
          </div>

          {/* ── Loading state ─────────────────────────────── */}
          {detailLoading && (
            <div className="p-8 text-center">
              <div className="inline-block w-5 h-5 border-2 border-accent-blue border-t-transparent rounded-full animate-spin" />
              <div className="text-xs text-text-muted mt-2">Loading being detail...</div>
            </div>
          )}

          {/* ── Content ───────────────────────────────────── */}
          {!detailLoading && (
            <div className="p-3 flex flex-col gap-3">

              {/* ── Identity Section ──────────────────────── */}
              <Section title="Identity" icon="ID" defaultOpen={true} accentColor="accent-orange"
                count={identity?.files?.length || 0}>
                {identity ? (
                  <div className="flex flex-col gap-3">
                    {/* Description */}
                    {identity.description && (
                      <p className="text-xs text-text-secondary leading-relaxed">{identity.description}</p>
                    )}

                    {/* Key details grid */}
                    <div className="grid grid-cols-2 gap-x-4 gap-y-1.5 text-[11px]">
                      <MetaRow label="Workspace" value={identity.workspace || 'Not configured'} mono />
                      <MetaRow label="Tenant" value={identity.tenant_id || 'Not configured'} mono />
                      <MetaRow label="Model" value={identity.model_id || 'Not configured'} mono />
                      <MetaRow label="First Contact" value={identity.first_contact ? formatDate(identity.first_contact) : 'Unknown'} />
                      {identity.creature_type && (
                        <MetaRow label="Creature Type" value={identity.creature_type} />
                      )}
                      {identity.agent_id && (
                        <MetaRow label="Agent ID" value={identity.agent_id} mono />
                      )}
                      {identity.phone && (
                        <MetaRow label="Phone" value={identity.phone} mono />
                      )}
                      <MetaRow label="Auto-Start" value={identity.auto_start ? 'Yes' : 'No'} />
                    </div>

                    {/* Personality traits */}
                    {identity.personality_traits?.length > 0 && (
                      <div>
                        <div className="text-[10px] text-text-muted uppercase tracking-wider mb-1">Personality</div>
                        <div className="flex flex-wrap gap-1">
                          {identity.personality_traits.map(trait => (
                            <span key={trait} className="px-1.5 py-0.5 text-[10px] rounded bg-accent-purple/10 text-accent-purple border border-accent-purple/20">
                              {trait}
                            </span>
                          ))}
                        </div>
                      </div>
                    )}

                    {/* Core functions */}
                    {identity.core_functions?.length > 0 && (
                      <div>
                        <div className="text-[10px] text-text-muted uppercase tracking-wider mb-1">Core Functions</div>
                        <div className="flex flex-wrap gap-1">
                          {identity.core_functions.map(fn => (
                            <span key={fn} className="px-1.5 py-0.5 text-[10px] rounded bg-accent-cyan/10 text-accent-cyan border border-accent-cyan/20">
                              {fn}
                            </span>
                          ))}
                        </div>
                      </div>
                    )}

                    {/* Identity files */}
                    {identity.files?.length > 0 && (
                      <div>
                        <div className="text-[10px] text-text-muted uppercase tracking-wider mb-1.5">Identity Files</div>
                        <div className="flex flex-col gap-1">
                          {identity.files.map(f => (
                            <button
                              key={f.rel_path}
                              onClick={() => handleViewFile(f.name, f.rel_path)}
                              className="flex items-center justify-between px-2 py-1.5 rounded bg-bg-card border border-border hover:bg-bg-hover hover:border-border-bright transition-colors text-left group"
                            >
                              <div className="flex items-center gap-2">
                                <svg className="w-3 h-3 text-accent-cyan shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M7 21h10a2 2 0 002-2V9.414a1 1 0 00-.293-.707l-5.414-5.414A1 1 0 0012.586 3H7a2 2 0 00-2 2v14a2 2 0 002 2z" />
                                </svg>
                                <span className="text-[11px] font-mono text-accent-cyan group-hover:text-text-primary">{f.name}</span>
                              </div>
                              <div className="flex items-center gap-2 text-[9px] text-text-muted">
                                <span>{formatBytes(f.size)}</span>
                                <span>{timeAgo(f.modified)}</span>
                              </div>
                            </button>
                          ))}
                        </div>
                      </div>
                    )}
                  </div>
                ) : (
                  <div className="text-xs text-text-muted italic">No identity data available</div>
                )}
              </Section>

              {/* ── Memory Section ────────────────────────── */}
              <Section title="Memory" icon="MEM" accentColor="accent-green"
                count={memory?.file_count || 0}>
                {memory ? (
                  <div className="flex flex-col gap-2">
                    <div className="grid grid-cols-2 gap-x-4 gap-y-1.5 text-[11px]">
                      <MetaRow label="Path" value={memory.path || 'No memory directory'} mono />
                      <MetaRow label="Files" value={String(memory.file_count)} />
                      <MetaRow label="Total Size" value={formatBytes(memory.total_size)} />
                      <MetaRow label="Last Updated" value={memory.last_updated ? formatDate(memory.last_updated) : 'Never'} />
                    </div>

                    {memory.file_count > 0 && !memoryBrowsing && (
                      <button
                        onClick={handleBrowseMemory}
                        className="self-start flex items-center gap-1.5 px-2.5 py-1 rounded border border-accent-green/30 bg-accent-green/10 text-accent-green text-[10px] font-medium hover:bg-accent-green/20 transition-colors mt-1"
                      >
                        <svg className="w-3 h-3" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 6h16M4 10h16M4 14h16M4 18h16" />
                        </svg>
                        Browse Memory
                      </button>
                    )}

                    {memoryBrowsing && memoryFiles.length > 0 && (
                      <div className="flex flex-col gap-1 mt-1">
                        <div className="flex items-center justify-between mb-1">
                          <span className="text-[10px] text-text-muted uppercase tracking-wider">Memory Files</span>
                          <button
                            onClick={() => setMemoryBrowsing(false)}
                            className="text-[10px] text-text-muted hover:text-text-primary"
                          >
                            Collapse
                          </button>
                        </div>
                        {memoryFiles.map(f => (
                          <button
                            key={f.rel_path}
                            onClick={() => handleViewFile(f.name, f.rel_path)}
                            className="flex items-center justify-between px-2 py-1.5 rounded bg-bg-card border border-border hover:bg-bg-hover transition-colors text-left group"
                          >
                            <span className="text-[11px] font-mono text-accent-green group-hover:text-text-primary truncate">{f.name}</span>
                            <div className="flex items-center gap-2 text-[9px] text-text-muted shrink-0">
                              <span>{formatBytes(f.size)}</span>
                              <span>{timeAgo(f.modified)}</span>
                            </div>
                          </button>
                        ))}
                      </div>
                    )}

                    {memory.file_count === 0 && (
                      <div className="text-xs text-text-muted italic">No memory files found</div>
                    )}
                  </div>
                ) : (
                  <div className="text-xs text-text-muted italic">No memory data available</div>
                )}
              </Section>

              {/* ── Tools Section ─────────────────────────── */}
              <Section title="Tools" icon="T" accentColor="accent-blue" count={tools.length}>
                {tools.length > 0 ? (
                  <div className="flex flex-col gap-1">
                    {tools.map(tool => (
                      <div
                        key={tool.name}
                        className="flex items-start gap-2 px-2 py-1.5 rounded bg-bg-card border border-border"
                      >
                        <div className="flex items-center gap-1.5 shrink-0 mt-0.5">
                          <div className={`w-1.5 h-1.5 rounded-full ${tool.status === 'active' ? 'bg-accent-green' : 'bg-text-muted'}`} />
                          <span className="text-[11px] font-mono text-accent-blue">{tool.name}</span>
                        </div>
                        {tool.description && (
                          <span className="text-[10px] text-text-muted flex-1">{tool.description}</span>
                        )}
                        <span className={`text-[9px] px-1 py-0 rounded shrink-0 ${
                          tool.status === 'active'
                            ? 'bg-accent-green/10 text-accent-green'
                            : 'bg-bg-hover text-text-muted'
                        }`}>
                          {tool.status}
                        </span>
                      </div>
                    ))}
                  </div>
                ) : (
                  <div className="text-xs text-text-muted italic">No tools configured</div>
                )}
              </Section>

              {/* ── Skills Section ────────────────────────── */}
              <Section title="Skills" icon="S" accentColor="accent-purple" count={skills.length}>
                {skills.length > 0 ? (
                  <div className="flex flex-col gap-1">
                    {skills.map(skill => (
                      <div
                        key={skill.name}
                        className="flex items-start gap-2 px-2 py-1.5 rounded bg-bg-card border border-border"
                      >
                        <span className="text-[11px] font-mono text-accent-purple shrink-0 mt-0.5">{skill.name}</span>
                        {skill.description && (
                          <span className="text-[10px] text-text-muted flex-1">{skill.description}</span>
                        )}
                        {skill.path && (
                          <span className="text-[9px] font-mono text-text-muted shrink-0">{skill.path}</span>
                        )}
                      </div>
                    ))}
                  </div>
                ) : (
                  <div className="text-xs text-text-muted italic">No skills configured</div>
                )}
              </Section>

              {/* ── ACT-I Profile Section ──────────────────── */}
              {detail?.acti && (
                <Section title="ACT-I Profile" icon="⚡" accentColor="accent-cyan"
                  count={`${detail.acti.positions_total}p`}>
                  <div className="flex flex-col gap-2">
                    {/* Summary */}
                    <div className="grid grid-cols-3 gap-2 text-center">
                      <div className="px-2 py-1.5 rounded bg-bg-card border border-border">
                        <div className="text-sm font-bold font-mono text-accent-cyan">{detail.acti.beings.length}</div>
                        <div className="text-[9px] text-text-muted uppercase">Beings</div>
                      </div>
                      <div className="px-2 py-1.5 rounded bg-bg-card border border-border">
                        <div className="text-sm font-bold font-mono text-accent-cyan">{detail.acti.clusters.length}</div>
                        <div className="text-[9px] text-text-muted uppercase">Clusters</div>
                      </div>
                      <div className="px-2 py-1.5 rounded bg-bg-card border border-border">
                        <div className="text-sm font-bold font-mono text-accent-cyan">{detail.acti.levers.length}</div>
                        <div className="text-[9px] text-text-muted uppercase">Levers</div>
                      </div>
                    </div>

                    {/* Beings operated */}
                    <div>
                      <div className="text-[10px] text-text-muted uppercase tracking-wider mb-1">Beings Operated</div>
                      <div className="flex flex-col gap-1">
                        {detail.acti.beings.map(ab => (
                          <div key={ab.id} className="flex items-center justify-between px-2 py-1 rounded bg-bg-card border border-border">
                            <div className="flex items-center gap-2 min-w-0">
                              <span className="text-[11px] font-medium text-text-primary truncate">{ab.name}</span>
                              <span className="text-[9px] text-text-muted truncate">{ab.domain}</span>
                            </div>
                            <span className="text-[10px] font-mono text-accent-cyan shrink-0">{ab.positions}p</span>
                          </div>
                        ))}
                      </div>
                    </div>

                    {/* Lever coverage */}
                    <div>
                      <div className="text-[10px] text-text-muted uppercase tracking-wider mb-1">Lever Coverage</div>
                      <div className="flex flex-wrap gap-1">
                        {detail.acti.levers.map(lv => (
                          <span key={lv} className="px-1.5 py-0.5 text-[9px] bg-accent-blue/10 text-accent-blue rounded border border-accent-blue/20">
                            L{lv}
                          </span>
                        ))}
                      </div>
                    </div>

                    {/* Heart skills */}
                    {detail.acti.shared_heart_skills && (
                      <div>
                        <div className="text-[10px] text-text-muted uppercase tracking-wider mb-1">Heart Skills</div>
                        <div className="flex flex-wrap gap-1">
                          {detail.acti.shared_heart_skills.map(s => (
                            <span key={s} className="px-1.5 py-0.5 text-[9px] bg-accent-purple/10 text-accent-purple rounded border border-accent-purple/20">
                              {s}
                            </span>
                          ))}
                        </div>
                      </div>
                    )}
                  </div>
                </Section>
              )}

              {/* ── ACT-I Being Detail Section ─────────────── */}
              {detail?.acti_being && (
                <Section title="ACT-I Being" icon="🎯" accentColor="accent-cyan"
                  count={`${detail.acti_being.positions}p`}>
                  <div className="flex flex-col gap-2">
                    {/* Domain */}
                    {detail.acti_being.domain && (
                      <div>
                        <div className="text-[10px] text-text-muted uppercase tracking-wider mb-1">Domain</div>
                        <p className="text-xs text-text-secondary leading-relaxed">{detail.acti_being.domain}</p>
                      </div>
                    )}

                    {/* Clusters */}
                    {detail.acti_being.clusters?.length > 0 && (
                      <div>
                        <div className="text-[10px] text-text-muted uppercase tracking-wider mb-1">Clusters Owned ({detail.acti_being.clusters.length})</div>
                        <div className="flex flex-col gap-0.5">
                          {detail.acti_being.clusters.map((c, i) => (
                            <div key={i} className="flex items-center justify-between text-[11px] px-2 py-0.5 rounded bg-bg-card border border-border">
                              <div className="flex items-center gap-1.5 min-w-0">
                                <span className="text-text-primary font-medium truncate">{c.name}</span>
                                <span className="text-text-muted truncate">— {c.function}</span>
                              </div>
                              <div className="flex items-center gap-2 shrink-0 ml-2">
                                <span className="text-[9px] text-text-muted">{c.family}</span>
                                <span className="text-[10px] font-mono text-accent-cyan">{c.positions}p</span>
                              </div>
                            </div>
                          ))}
                        </div>
                      </div>
                    )}

                    {/* Lever coverage */}
                    {detail.acti_being.levers?.length > 0 && (
                      <div>
                        <div className="text-[10px] text-text-muted uppercase tracking-wider mb-1">Lever Coverage</div>
                        <div className="flex flex-wrap gap-1">
                          {detail.acti_being.levers.map(lv => (
                            <span key={lv} className="px-1.5 py-0.5 text-[9px] bg-accent-blue/10 text-accent-blue rounded border border-accent-blue/20">
                              L{lv}
                            </span>
                          ))}
                        </div>
                      </div>
                    )}

                    {/* Heart skills */}
                    {detail.acti_being.shared_heart_skills?.length > 0 && (
                      <div>
                        <div className="text-[10px] text-text-muted uppercase tracking-wider mb-1">Heart Skills</div>
                        <div className="flex flex-wrap gap-1">
                          {detail.acti_being.shared_heart_skills.map(s => (
                            <span key={s} className="px-1.5 py-0.5 text-[9px] bg-accent-purple/10 text-accent-purple rounded border border-accent-purple/20">
                              {s}
                            </span>
                          ))}
                        </div>
                      </div>
                    )}

                    {/* Parent sister */}
                    {detail.acti_being.sister_id && (
                      <div className="flex items-center gap-2 mt-1">
                        <span className="text-[10px] text-text-muted">Parent Sister:</span>
                        <button
                          onClick={() => openBeingDetail(detail.acti_being.sister_id)}
                          className="text-[10px] text-accent-blue hover:underline"
                        >
                          {detail.acti_being.sister_id}
                        </button>
                      </div>
                    )}
                  </div>
                </Section>
              )}

              {/* ── Workspace Section ─────────────────────── */}
              {fileTree.length > 0 && (
                <Section title="Workspace" icon="WS" accentColor="accent-cyan" count={fileTree.length}>
                  <div className="flex flex-col">
                    {fileTree.map((node, i) => (
                      <FileTreeNode
                        key={node.name + i}
                        node={node}
                        depth={0}
                        onFileClick={(n) => handleViewFile(n.name, n.rel_path)}
                      />
                    ))}
                  </div>
                </Section>
              )}

              {/* ── Assigned Tasks ────────────────────────── */}
              <Section title="Assigned Tasks" icon="TSK" accentColor="accent-amber" count={assignedTasks.length}>
                {loadingTasks && (
                  <div className="text-xs text-text-muted">Loading tasks...</div>
                )}

                {!loadingTasks && assignedTasks.length === 0 && (
                  <div className="text-xs text-text-muted italic">No tasks assigned</div>
                )}

                {!loadingTasks && activeTasks.length > 0 && (
                  <div className="mb-2">
                    <div className="text-[10px] text-accent-blue mb-1">Active</div>
                    {activeTasks.map(task => (
                      <TaskRow key={task.id || task.task_id} task={task} onClick={() => { closeBeingDetail(); onOpenTask?.(task) }} />
                    ))}
                  </div>
                )}

                {!loadingTasks && otherTasks.length > 0 && (
                  <div>
                    <div className="text-[10px] text-text-muted mb-1">Other</div>
                    {otherTasks.map(task => (
                      <TaskRow key={task.id || task.task_id} task={task} onClick={() => { closeBeingDetail(); onOpenTask?.(task) }} />
                    ))}
                  </div>
                )}
              </Section>
            </div>
          )}
        </div>
      </div>

      {/* File Viewer Overlay */}
      {viewingFile && (
        <FileViewer
          fileName={viewingFile}
          content={fileLoading ? 'Loading...' : (fileContent || '')}
          onClose={() => { setViewingFile(null); setFileContent(null) }}
        />
      )}
    </>
  )
}

// ── Helper sub-components ───────────────────────────────────

function MetaRow({ label, value, mono = false }) {
  return (
    <div className="flex flex-col gap-0.5">
      <span className="text-text-muted text-[10px]">{label}</span>
      <span className={`text-text-secondary truncate ${mono ? 'font-mono' : ''}`}>{value}</span>
    </div>
  )
}

function TaskRow({ task, onClick }) {
  const prio = PRIORITY_CONFIG[task.priority] || PRIORITY_CONFIG.normal
  return (
    <button
      onClick={onClick}
      className="w-full flex items-center gap-2 px-2 py-1.5 rounded border border-border bg-bg-card hover:bg-bg-hover transition-colors text-left mb-1"
    >
      <div className={`w-1.5 h-1.5 rounded-full shrink-0 ${STATUS_DOT[task.status] || 'bg-text-muted'}`} />
      <span className="text-xs flex-1 truncate">{task.title}</span>
      <span className={`px-1 py-0 text-[9px] font-bold rounded border ${prio.bg} ${prio.text} ${prio.border}`}>
        {prio.label}
      </span>
      <span className="text-[9px] text-text-muted font-mono">{timeAgo(task.updated || task.updated_at)}</span>
    </button>
  )
}
