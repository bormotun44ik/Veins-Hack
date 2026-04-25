import { useState } from 'react'
import ViewToggle from './components/ViewToggle'
import Dashboard from './components/Dashboard'
import GraphPage from './components/GraphPage'

export default function App() {
  const [view, setView] = useState<'dashboard' | 'graph'>('dashboard')
  const [selectedId, setSelectedId] = useState<string | null>(null)

  return (
    <div className="flex flex-col" style={{ height: '100vh', background: 'var(--bg-primary)' }}>
      {/* Header */}
      <header
        className="flex items-center justify-between px-4 shrink-0"
        style={{ height: 48, borderBottom: '1px solid var(--border)' }}
      >
        <div className="flex items-center gap-4">
          <span className="font-mono text-sm" style={{ color: 'var(--accent)' }}>◈ veins</span>
          <ViewToggle view={view} onChange={setView} />
        </div>
        <span className="font-mono text-xs" style={{ color: 'var(--text-tertiary)' }}>v0.1.0</span>
      </header>

      {/* Body */}
      <div className="flex flex-1 overflow-hidden">
        {view === 'dashboard' ? (
          <Dashboard
            onSelectPerson={(id) => {
              setSelectedId(id)
              setView('graph')
            }}
          />
        ) : (
          <GraphPage selectedId={selectedId} setSelectedId={setSelectedId} />
        )}
      </div>
    </div>
  )
}
