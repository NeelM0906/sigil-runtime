import { useState } from 'react'
import { useAuth } from './context/AuthContext'
import { BeingsProvider } from './context/BeingsContext'
import { SSEProvider } from './context/SSEContext'
import { LoginPage } from './components/LoginPage'
import { Header } from './components/Header'
import { BeingsRegistry } from './components/BeingsRegistry'
import { BeingDetail } from './components/BeingDetail'
import { TaskBoard } from './components/TaskBoard'
import { ChatWindow } from './components/ChatWindow'
// SubAgentTracker removed — not needed
import { OrchestrationTracker } from './components/OrchestrationTracker'
import { TeamPage } from './components/TeamPage'
import { ProjectsHub } from './components/ProjectsHub'
import { SkillsPage } from './components/SkillsPage'
import { CronPanel } from './components/CronPanel'
import { SessionProvider } from './context/SessionContext'

const TABS = [
  { id: 'overview', label: 'Overview' },
  { id: 'tasks', label: 'Task Board' },
  { id: 'projects', label: 'Projects' },
  { id: 'chat', label: 'Comms' },
  { id: 'team', label: 'Team' },
  { id: 'skills', label: 'Skills' },
]

function Dashboard() {
  const { user, logout } = useAuth()
  const [activeTab, setActiveTab] = useState('overview')
  const [crossLinkTask, setCrossLinkTask] = useState(null)

  // Use CSS display toggling instead of conditional rendering
  // so components stay mounted (SSE connections persist, state preserved)
  const show = (tab) => activeTab === tab ? {} : { display: 'none' }

  return (
    <SessionProvider>
    <SSEProvider>
    <BeingsProvider>
      <div className="min-h-screen bg-bg-primary text-text-primary">
        <Header activeTab={activeTab} setActiveTab={setActiveTab} tabs={TABS} user={user} onLogout={logout} />
        <main className="p-3 max-w-[1920px] mx-auto">
          <div style={show('overview')}>
            <div className="grid grid-cols-1 lg:grid-cols-12 gap-3">
              <div className="lg:col-span-4 flex flex-col gap-3">
                <BeingsRegistry />
                <CronPanel />
              </div>
              <div className="lg:col-span-8">
                <TaskBoard />
              </div>
            </div>
          </div>
          <div style={show('tasks')}>
            <TaskBoard fullWidth />
          </div>
          <div style={show('projects')}>
            <ProjectsHub />
          </div>
          <div style={show('chat')}>
            <div className="grid grid-cols-1 lg:grid-cols-12 gap-3">
              <div className="lg:col-span-8">
                <ChatWindow />
              </div>
              <div className="lg:col-span-4 flex flex-col gap-3">
                <OrchestrationTracker />
              </div>
            </div>
          </div>
          <div style={show('team')}>
            <TeamPage />
          </div>
          <div style={show('skills')}>
            <SkillsPage />
          </div>
        </main>

        <BeingDetail onOpenTask={(task) => {
          setCrossLinkTask(task)
          setActiveTab('tasks')
        }} />
      </div>
    </BeingsProvider>
    </SSEProvider>
    </SessionProvider>
  )
}

import { Component } from 'react'

class ErrorBoundary extends Component {
  state = { error: null }
  static getDerivedStateFromError(error) { return { error } }
  componentDidCatch(error, info) { console.error('[CRASH]', error, info) }
  render() {
    if (this.state.error) {
      return (
        <div className="min-h-screen bg-bg-primary flex items-center justify-center">
          <div className="text-center p-8">
            <div className="text-2xl mb-2">Something went wrong</div>
            <div className="text-text-muted text-sm mb-4">{this.state.error.message}</div>
            <button
              onClick={() => { this.setState({ error: null }); window.location.reload() }}
              className="px-4 py-2 bg-accent-blue text-white rounded hover:bg-accent-blue/80"
            >Reload</button>
          </div>
        </div>
      )
    }
    return this.props.children
  }
}

export default function App() {
  const { user, loading } = useAuth()

  if (loading) return <div className="min-h-screen bg-bg-primary" />
  if (!user) return <LoginPage />
  return <ErrorBoundary><Dashboard /></ErrorBoundary>
}
