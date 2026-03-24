import { useState, useCallback } from 'react'
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
import { CodeWorkspace } from './components/CodeWorkspace'
import { CodeStatusCard } from './components/CodeStatusCard'

const TABS = [
  { id: 'overview', label: 'Overview' },
  { id: 'tasks', label: 'Task Board' },
  { id: 'projects', label: 'Projects' },
  { id: 'chat', label: 'Comms' },
  { id: 'teams', label: 'Agent Teams' },
  { id: 'code', label: 'Code' },
]

function Dashboard() {
  const { user, logout } = useAuth()
  const [activeTab, setActiveTab] = useState('overview')
  const [crossLinkTask, setCrossLinkTask] = useState(null)
  const [codeInitialPrompt, setCodeInitialPrompt] = useState(null)

  const openInCode = useCallback((prompt) => {
    setCodeInitialPrompt(prompt)
    setActiveTab('code')
  }, [])

  return (
    <BeingsProvider>
      <div className="min-h-screen bg-bg-primary text-text-primary">
        <Header activeTab={activeTab} setActiveTab={setActiveTab} tabs={TABS} user={user} onLogout={logout} />
        <main className="p-3 max-w-[1920px] mx-auto">
          {activeTab === 'overview' && (
            <div className="grid grid-cols-1 lg:grid-cols-12 gap-3">
              <div className="lg:col-span-4 flex flex-col gap-3">
                <BeingsRegistry />
                <SubAgentTracker />
                <CodeStatusCard onOpenCode={() => setActiveTab('code')} />
              </div>
              <div className="lg:col-span-8">
                <TaskBoard onOpenInCode={openInCode} />
              </div>
            </div>
          )}
          {activeTab === 'tasks' && (
            <TaskBoard fullWidth onOpenInCode={openInCode} />
          )}
          {activeTab === 'projects' && (
            <ProjectsHub />
          )}
          {activeTab === 'chat' && (
            <div className="grid grid-cols-1 lg:grid-cols-12 gap-3">
              <div className="lg:col-span-8">
                <ChatWindow userId={user?.id} onOpenInCode={openInCode} />
              </div>
              <div className="lg:col-span-4 flex flex-col gap-3">
                <OrchestrationTracker />
              </div>
            </div>
          )}
          {activeTab === 'teams' && (
            <AgentTeams />
          )}
          {activeTab === 'code' && (
            <CodeWorkspace
              initialPrompt={codeInitialPrompt}
              onConsumePrompt={() => setCodeInitialPrompt(null)}
            />
          )}
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
