import { useBeings } from '../context/BeingsContext'

export function Header({ activeTab, setActiveTab, tabs }) {
  const { beings } = useBeings()
  const onlineCount = beings.filter(b => b.status === 'online').length
  const busyCount = beings.filter(b => b.status === 'busy').length

  return (
    <header className="bg-bg-secondary border-b border-border sticky top-0 z-50">
      <div className="max-w-[1920px] mx-auto px-4 h-12 flex items-center justify-between">
        {/* Left: Logo + Title */}
        <div className="flex items-center gap-3">
          <div className="w-7 h-7 rounded bg-accent-blue flex items-center justify-center text-xs font-bold tracking-wider">
            MC
          </div>
          <span className="font-semibold text-sm tracking-wide">MISSION CONTROL</span>
          <span className="text-text-muted text-xs font-mono ml-1">SIGIL</span>
        </div>

        {/* Center: Tabs */}
        <nav className="flex gap-1">
          {tabs.map(tab => (
            <button
              key={tab.id}
              onClick={() => setActiveTab(tab.id)}
              className={`px-3 py-1.5 text-xs font-medium rounded transition-colors ${
                activeTab === tab.id
                  ? 'bg-accent-blue/20 text-accent-blue'
                  : 'text-text-secondary hover:text-text-primary hover:bg-bg-hover'
              }`}
            >
              {tab.label}
            </button>
          ))}
        </nav>

        {/* Right: Status indicators */}
        <div className="flex items-center gap-4 text-xs">
          <div className="flex items-center gap-1.5">
            <div className="w-2 h-2 rounded-full bg-accent-green animate-pulse" />
            <span className="text-text-secondary">{onlineCount} online</span>
          </div>
          {busyCount > 0 && (
            <div className="flex items-center gap-1.5">
              <div className="w-2 h-2 rounded-full bg-accent-amber" />
              <span className="text-text-secondary">{busyCount} busy</span>
            </div>
          )}
          <div className="text-text-muted font-mono">
            {new Date().toLocaleTimeString('en-US', { hour12: false })}
          </div>
        </div>
      </div>
    </header>
  )
}
