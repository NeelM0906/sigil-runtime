import { useState } from 'react'
import { useAuth } from './context/AuthContext'
import { BeingsProvider } from './context/BeingsContext'
import { LoginPage } from './components/LoginPage'
import { Header } from './components/Header'
import { BeingsRegistry } from './components/BeingsRegistry'
import { BeingDetail } from './components/BeingDetail'
import { TaskBoard } from './components/TaskBoard'
import { ChatWindow } from './components/ChatWindow'
import { SubAgentTracker } from './components/SubAgentTracker'
import { OrchestrationTracker } from './components/OrchestrationTracker'
import { AgentTeams } from './components/AgentTeams'
import { ProjectsHub } from './components/ProjectsHub'

const TABS = [
  { id: 'overview', label: 'Overview' },
  { id: 'tasks', label: 'Task Board' },
  { id: 'projects', label: 'Projects' },
  { id: 'chat', label: 'Comms' },
  { id: 'teams', label: 'Agent Teams' },
]

function Dashboard() {
  const { user, logout } = useAuth()
  const [activeTab, setActiveTab] = useState('overview')
  const [crossLinkTask, setCrossLinkTask] = useState(null)

  // Use CSS display toggling instead of conditional rendering
  // so components stay mounted (SSE connections persist, state preserved)
  const show = (tab) => activeTab === tab ? {} : { display: 'none' }

  return (
    <BeingsProvider>
      <div className="min-h-screen bg-bg-primary text-text-primary">
        <Header activeTab={activeTab} setActiveTab={setActiveTab} tabs={TABS} user={user} onLogout={logout} />
        <main className="p-3 max-w-[1920px] mx-auto">
          <div style={show('overview')}>
            <div className="grid grid-cols-1 lg:grid-cols-12 gap-3">
              <div className="lg:col-span-4 flex flex-col gap-3">
                <BeingsRegistry />
                <SubAgentTracker />
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
          <div style={show('teams')}>
            <AgentTeams />
          </div>
        </main>

        <BeingDetail onOpenTask={(task) => {
          setCrossLinkTask(task)
          setActiveTab('tasks')
        }} />
      </div>
    </BeingsProvider>
  )
}

export default function App() {
  const { user, loading } = useAuth()

  if (loading) return <div className="min-h-screen bg-bg-primary" />
  if (!user) return <LoginPage />
  return <Dashboard />
}
