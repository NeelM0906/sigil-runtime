import { useState } from 'react'
import { Header } from './components/Header'
import { BeingsRegistry } from './components/BeingsRegistry'
import { TaskBoard } from './components/TaskBoard'
import { ChatWindow } from './components/ChatWindow'
import { SubAgentTracker } from './components/SubAgentTracker'

const TABS = [
  { id: 'overview', label: 'Overview' },
  { id: 'tasks', label: 'Task Board' },
  { id: 'chat', label: 'Comms' },
]

export default function App() {
  const [activeTab, setActiveTab] = useState('overview')

  return (
    <div className="min-h-screen bg-bg-primary text-text-primary">
      <Header activeTab={activeTab} setActiveTab={setActiveTab} tabs={TABS} />
      <main className="p-3 max-w-[1920px] mx-auto">
        {activeTab === 'overview' && (
          <div className="grid grid-cols-1 lg:grid-cols-12 gap-3">
            {/* Left: Beings + Sub-Agents stacked */}
            <div className="lg:col-span-4 flex flex-col gap-3">
              <BeingsRegistry />
              <SubAgentTracker />
            </div>
            {/* Right: Task Board */}
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
      </main>
    </div>
  )
}
