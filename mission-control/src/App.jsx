import { useState } from 'react'
import { BeingsProvider } from './context/BeingsContext'
import { Header } from './components/Header'
import { BeingsRegistry } from './components/BeingsRegistry'
import { BeingDetail } from './components/BeingDetail'
import { TaskBoard } from './components/TaskBoard'
import { ChatWindow } from './components/ChatWindow'
import { SubAgentTracker } from './components/SubAgentTracker'
import { AgentTeams } from './components/AgentTeams'

const TABS = [
  { id: 'overview', label: 'Overview' },
  { id: 'tasks', label: 'Task Board' },
  { id: 'chat', label: 'Comms' },
  { id: 'teams', label: 'Agent Teams' },
]

export default function App() {
  const [activeTab, setActiveTab] = useState('overview')
  // For cross-linking: task detail opened from being detail
  const [crossLinkTask, setCrossLinkTask] = useState(null)

  return (
    <BeingsProvider>
      <div className="min-h-screen bg-bg-primary text-text-primary">
        <Header activeTab={activeTab} setActiveTab={setActiveTab} tabs={TABS} />
        <main className="p-3 max-w-[1920px] mx-auto">
          {activeTab === 'overview' && (
            <div className="grid grid-cols-1 lg:grid-cols-12 gap-3">
              <div className="lg:col-span-4 flex flex-col gap-3">
                <BeingsRegistry />
                <SubAgentTracker />
              </div>
              <div className="lg:col-span-8">
                <TaskBoard />
              </div>
            </div>
          )}
          {activeTab === 'tasks' && (
            <TaskBoard fullWidth />
          )}
          {activeTab === 'chat' && (
            <div className="grid grid-cols-1 lg:grid-cols-12 gap-3">
              <div className="lg:col-span-8">
                <ChatWindow />
              </div>
              <div className="lg:col-span-4 flex flex-col gap-3">
                <BeingsRegistry compact />
                <SubAgentTracker />
              </div>
            </div>
          )}
          {activeTab === 'teams' && (
            <AgentTeams />
          )}
        </main>

        {/* Global Being Detail slide-out — available on all tabs */}
        <BeingDetail onOpenTask={(task) => {
          setCrossLinkTask(task)
          setActiveTab('tasks')
        }} />
      </div>
    </BeingsProvider>
  )
}
