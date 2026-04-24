import { useState, useEffect } from 'react'
import { fetchGraph } from './api'
import type { Layer, GraphResponse } from './types'
import GraphView from './components/GraphView'
import LayerToggle from './components/LayerToggle'
import InsightPanel from './components/InsightPanel'

export default function App() {
  const [layer, setLayer] = useState<Layer>('collab')
  const [graphData, setGraphData] = useState<GraphResponse | null>(null)
  const [selectedId, setSelectedId] = useState<string | null>(null)

  useEffect(() => {
    fetchGraph(layer).then(setGraphData).catch(console.error)
  }, [layer])

  return (
    <div className="flex flex-col" style={{ height: '100vh', background: 'var(--bg-primary)' }}>
      {/* Header */}
      <header
        className="flex items-center justify-between px-4 shrink-0"
        style={{ height: 48, borderBottom: '1px solid var(--border)' }}
      >
        <span className="font-mono text-sm" style={{ color: 'var(--accent)' }}>◈ veins</span>
        <LayerToggle active={layer} onChange={setLayer} />
        <span className="font-mono text-xs" style={{ color: 'var(--text-tertiary)' }}>v0.1.0</span>
      </header>

      {/* Body */}
      <div className="flex flex-1 overflow-hidden">
        {/* Graph */}
        {graphData ? (
          <GraphView
            data={graphData}
            selectedId={selectedId}
            onNodeClick={(node) => {
              // InsightPanel умеет только Person. Task/Repo/Meeting просто выделяем визуально.
              if (node.type === 'Person') setSelectedId(node.id)
              else setSelectedId(null)
            }}
          />
        ) : (
          <div className="flex-1 flex items-center justify-center" style={{ color: 'var(--text-tertiary)' }}>
            <span className="font-mono text-sm animate-pulse">loading graph...</span>
          </div>
        )}

        {/* Sidebar */}
        <div
          className="shrink-0 overflow-hidden"
          style={{
            width: 420,
            borderLeft: '1px solid var(--border)',
            background: 'var(--bg-secondary)',
          }}
        >
          <InsightPanel selectedId={selectedId} />
        </div>
      </div>
    </div>
  )
}
