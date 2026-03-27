import { useState, useEffect, useCallback } from 'react'
import { teamsApi } from '../api'
import { useAuth } from '../context/AuthContext'

const ROLE_BADGE = {
  admin: 'bg-accent-amber/15 text-accent-amber border-accent-amber/30',
  member: 'bg-text-muted/15 text-text-muted border-text-muted/30',
}

export function TeamPage() {
  const { user } = useAuth()
  const [teams, setTeams] = useState([])
  const [activeTeam, setActiveTeam] = useState(null)
  const [channels, setChannels] = useState([])
  const [loading, setLoading] = useState(true)
  const [showAddMember, setShowAddMember] = useState(false)
  const [allUsers, setAllUsers] = useState([])
  const [newChannelName, setNewChannelName] = useState('')
  const [showNewChannel, setShowNewChannel] = useState(false)

  const fetchTeams = useCallback(async () => {
    try {
      const { teams: t } = await teamsApi.list()
      setTeams(t || [])
      if (t?.length > 0 && !activeTeam) setActiveTeam(t[0])
    } catch { /* ignore */ }
    finally { setLoading(false) }
  }, [])

  useEffect(() => { fetchTeams() }, [fetchTeams])

  useEffect(() => {
    if (!activeTeam) return
    teamsApi.listChannels(activeTeam.id).then(({ channels: c }) => setChannels(c || [])).catch(() => {})
  }, [activeTeam?.id])

  const isAdmin = activeTeam?.members?.some(m => m.user_id === user?.user_id && m.role === 'admin')

  const loadAllUsers = async () => {
    try {
      const res = await fetch('/api/mc/auth/users', {
        headers: { 'Authorization': `Bearer ${JSON.parse(localStorage.getItem('mc_auth') || '{}').token}` }
      })
      if (res.ok) {
        const { users } = await res.json()
        setAllUsers(users || [])
      }
    } catch { /* ignore */ }
    setShowAddMember(true)
  }

  const handleAddMember = async (userId) => {
    try {
      await teamsApi.addMember(activeTeam.id, userId)
      setShowAddMember(false)
      fetchTeams()
    } catch (err) { alert('Failed: ' + err.message) }
  }

  const handleRemoveMember = async (userId) => {
    if (!confirm('Remove this member from the team?')) return
    try {
      await teamsApi.removeMember(activeTeam.id, userId)
      fetchTeams()
    } catch (err) { alert('Failed: ' + err.message) }
  }

  const handleCreateChannel = async () => {
    if (!newChannelName.trim()) return
    try {
      await teamsApi.createChannel(activeTeam.id, newChannelName.trim())
      setNewChannelName('')
      setShowNewChannel(false)
      teamsApi.listChannels(activeTeam.id).then(({ channels: c }) => setChannels(c || [])).catch(() => {})
    } catch (err) { alert('Failed: ' + err.message) }
  }

  if (loading) return <div className="text-text-muted text-sm p-4">Loading...</div>

  if (teams.length === 0) {
    return (
      <div className="flex flex-col items-center justify-center py-20 text-center">
        <div className="text-4xl mb-3">👥</div>
        <h2 className="text-lg font-semibold text-text-primary mb-1">No team yet</h2>
        <p className="text-sm text-text-muted max-w-md">
          You're not part of any team. Ask your admin to add you, or create one.
        </p>
      </div>
    )
  }

  const team = activeTeam || teams[0]
  const members = team?.members || []
  const existingIds = new Set(members.map(m => m.user_id))
  const availableUsers = allUsers.filter(u => !existingIds.has(u.id))

  return (
    <div className="max-w-4xl mx-auto">
      {/* Team selector (if multiple teams) */}
      {teams.length > 1 && (
        <div className="flex gap-2 mb-4">
          {teams.map(t => (
            <button
              key={t.id}
              onClick={() => setActiveTeam(t)}
              className={`px-3 py-1.5 text-xs font-medium rounded transition-colors ${
                team.id === t.id ? 'bg-accent-blue/15 text-accent-blue border border-accent-blue/30' : 'text-text-muted hover:text-text-primary'
              }`}
            >
              {t.name}
            </button>
          ))}
        </div>
      )}

      {/* Team Header */}
      <div className="bg-bg-secondary border border-border rounded-lg p-4 mb-4">
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-lg font-semibold text-text-primary">{team.name}</h1>
            {team.description && <p className="text-sm text-text-secondary mt-0.5">{team.description}</p>}
          </div>
          <span className="px-2 py-1 text-xs bg-bg-card border border-border rounded font-mono">
            {members.length} member{members.length !== 1 ? 's' : ''}
          </span>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
        {/* Members */}
        <div className="bg-bg-secondary border border-border rounded-lg p-4">
          <div className="flex items-center justify-between mb-3">
            <h2 className="text-xs font-semibold uppercase tracking-wider text-text-muted">Members</h2>
            {isAdmin && (
              <button
                onClick={loadAllUsers}
                className="text-[10px] px-2 py-1 text-accent-blue hover:bg-accent-blue/10 rounded transition-colors"
              >
                + Add Member
              </button>
            )}
          </div>

          {showAddMember && (
            <div className="mb-3 p-2 bg-bg-card border border-border rounded space-y-1 max-h-40 overflow-y-auto">
              {availableUsers.length === 0 ? (
                <p className="text-[10px] text-text-muted">No users available to add</p>
              ) : availableUsers.map(u => (
                <button
                  key={u.id}
                  onClick={() => handleAddMember(u.id)}
                  className="w-full flex items-center gap-2 px-2 py-1.5 text-xs text-text-secondary hover:bg-bg-hover rounded transition-colors text-left"
                >
                  <div className="w-6 h-6 rounded-full bg-accent-blue/20 flex items-center justify-center text-[10px] font-bold text-accent-blue">
                    {(u.name || u.email || '?')[0].toUpperCase()}
                  </div>
                  <div>
                    <div className="font-medium">{u.name || 'Unknown'}</div>
                    <div className="text-[10px] text-text-muted">{u.email}</div>
                  </div>
                </button>
              ))}
              <button onClick={() => setShowAddMember(false)} className="text-[10px] text-text-muted hover:text-text-primary w-full text-center pt-1">Cancel</button>
            </div>
          )}

          <div className="space-y-2">
            {members.map(m => (
              <div key={m.user_id} className="flex items-center gap-3 p-2 bg-bg-card border border-border rounded">
                <div className="w-8 h-8 rounded-full bg-accent-purple/20 flex items-center justify-center text-sm font-bold text-accent-purple shrink-0">
                  {(m.name || m.email || '?')[0].toUpperCase()}
                </div>
                <div className="flex-1 min-w-0">
                  <div className="text-sm font-medium text-text-primary truncate">{m.name || 'Unknown'}</div>
                  <div className="text-[10px] text-text-muted truncate">{m.email}</div>
                </div>
                <span className={`px-1.5 py-0.5 text-[9px] font-bold rounded border shrink-0 ${ROLE_BADGE[m.role] || ROLE_BADGE.member}`}>
                  {m.role?.toUpperCase()}
                </span>
                {isAdmin && m.role !== 'admin' && (
                  <button
                    onClick={() => handleRemoveMember(m.user_id)}
                    className="text-[10px] text-text-muted hover:text-accent-red transition-colors shrink-0"
                    title="Remove"
                  >✕</button>
                )}
              </div>
            ))}
          </div>
        </div>

        {/* Channels */}
        <div className="bg-bg-secondary border border-border rounded-lg p-4">
          <div className="flex items-center justify-between mb-3">
            <h2 className="text-xs font-semibold uppercase tracking-wider text-text-muted">Team Channels</h2>
            {isAdmin && (
              <button
                onClick={() => setShowNewChannel(!showNewChannel)}
                className="text-[10px] px-2 py-1 text-accent-blue hover:bg-accent-blue/10 rounded transition-colors"
              >
                + New Channel
              </button>
            )}
          </div>

          {showNewChannel && (
            <div className="mb-3 flex gap-2">
              <span className="text-sm text-text-muted py-1">#</span>
              <input
                autoFocus
                value={newChannelName}
                onChange={e => setNewChannelName(e.target.value)}
                onKeyDown={e => { if (e.key === 'Enter') handleCreateChannel(); if (e.key === 'Escape') setShowNewChannel(false) }}
                placeholder="channel-name"
                className="flex-1 px-2 py-1 bg-bg-card border border-border rounded text-xs text-text-primary placeholder:text-text-muted focus:outline-none focus:border-accent-blue font-mono"
              />
              <button onClick={handleCreateChannel} className="px-2 py-1 text-xs bg-accent-blue text-white rounded hover:bg-accent-blue/80">Create</button>
            </div>
          )}

          {channels.length === 0 ? (
            <p className="text-xs text-text-muted py-2">No channels yet.</p>
          ) : (
            <div className="space-y-1.5">
              {channels.map(ch => (
                <div key={ch.id} className="flex items-center gap-2 px-2 py-2 bg-bg-card border border-border rounded hover:border-border-bright transition-colors cursor-pointer">
                  <span className="text-sm font-bold text-accent-purple">#</span>
                  <span className="text-xs font-medium text-text-primary">{ch.name}</span>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  )
}
