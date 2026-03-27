import { useState, useEffect } from 'react'
import { useBeings } from '../context/BeingsContext'
import { codeApi } from '../api'

export function Header({ activeTab, setActiveTab, tabs, user, onLogout }) {
  const { beings } = useBeings()
  const sseCtx = useContext(SSEContext)
  const onlineCount = beings.filter(b => b.status === 'online').length
  const busyCount = beings.filter(b => b.status === 'busy').length

  // Code agent status polling
  const [codeStatus, setCodeStatus] = useState(null)
  useEffect(() => {
    const check = () => codeApi.health().then(setCodeStatus).catch(() => setCodeStatus(null))
    check()
    const interval = setInterval(check, 10000)
    return () => clearInterval(interval)
  }, [])

  return (
    <header className="bg-bg-secondary border-b border-border sticky top-0 z-50">
      <div className="max-w-[1920px] mx-auto px-4 h-12 flex items-center justify-between">
        {/* Left: Logo + Title */}
        <div className="flex items-center gap-3">
          <div className="w-7 h-7 rounded bg-accent-blue flex items-center justify-center text-xs font-bold tracking-wider">
            SAI
          </div>
          <span className="font-semibold text-sm tracking-wide">MISSION CONTROL</span>
        </div>

        {/* Center: Tabs */}
        <nav className="flex gap-1">
          {tabs.map(tab => (
            <button
              key={tab.id}
              onClick={() => setActiveTab(tab.id)}
              className={`px-3 py-1.5 text-xs font-medium rounded transition-colors flex items-center gap-1.5 ${
                activeTab === tab.id
                  ? 'bg-accent-blue/20 text-accent-blue'
                  : 'text-text-secondary hover:text-text-primary hover:bg-bg-hover'
              }`}
            >
              {tab.label}
              {tab.id === 'code' && codeStatus?.running && (
                <span className="w-1.5 h-1.5 rounded-full bg-accent-green animate-pulse" />
              )}
            </button>
          ))}
        </nav>

        {/* Right: Status + User */}
        <div className="flex items-center gap-4 text-xs">
          <div className="flex items-center gap-1.5">
            <span
              className={`w-2 h-2 rounded-full ${sseCtx?.connected ? 'bg-accent-green' : 'bg-red-500 animate-pulse'}`}
              title={sseCtx?.connected ? 'Connected' : 'Reconnecting...'}
            />
            <span className="text-text-secondary">{onlineCount} online</span>
          </div>
          {busyCount > 0 && (
            <div className="flex items-center gap-1.5">
              <div className="w-2 h-2 rounded-full bg-accent-amber" />
              <span className="text-text-secondary">{busyCount} busy</span>
            </div>
          )}
          {codeStatus && (
            <div className="flex items-center gap-1.5">
              <div className={`w-2 h-2 rounded-full ${codeStatus.running ? 'bg-accent-purple animate-pulse' : 'bg-text-muted'}`} />
              <span className="text-text-secondary">code {codeStatus.running ? 'active' : 'idle'}</span>
            </div>
          )}
          {user && (
            <div className="flex items-center gap-2 ml-2 pl-2 border-l border-border">
              <span className="text-text-secondary font-medium">{user.name}</span>
              <button
                onClick={onLogout}
                className="text-text-muted hover:text-accent-red transition-colors"
                title="Sign out"
              >
                Exit
              </button>
            </div>
          )}
        </div>
      </div>
    </header>
  )
}
