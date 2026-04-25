import { useState, useEffect } from 'react'
import { fetchGraph } from '../api'
import type { Layer, GraphResponse } from '../types'
import GraphView from './GraphView'
import LayerToggle from './LayerToggle'
import InsightPanel from './InsightPanel'

interface GraphPageProps {
  selectedId: string | null
  setSelectedId: (id: string | null) => void
}

export default function GraphPage({ selectedId, setSelectedId }: GraphPageProps) {
  const [layer, setLayer] = useState<Layer>('collab')
  const [graphData, setGraphData] = useState<GraphResponse | null>(null)

  useEffect(() => {
    // Polling 5s: при live ingest новые события появятся автоматом без F5.
    // Pause when tab hidden — экономим LLM-кэш-lookups и сеть.
    const ctrl = new AbortController()
    let timer: number | undefined

    const tick = async () => {
      if (document.hidden) return
      try {
        const data = await fetchGraph(layer)
        if (!ctrl.signal.aborted) setGraphData(data)
      } catch (e) {
        if (!ctrl.signal.aborted) console.error('graph poll:', e)
      }
    }

    tick()  // immediate
    timer = window.setInterval(tick, 5000)

    return () => {
      ctrl.abort()
      if (timer !== undefined) window.clearInterval(timer)
    }
  }, [layer])

  return (
    <div className="flex flex-col flex-1 overflow-hidden">
      {/* Layer sub-bar */}
      <div
        className="flex items-center justify-center px-4 shrink-0"
        style={{ height: 40, borderBottom: '1px solid var(--border)', background: 'var(--bg-secondary)' }}
      >
        <LayerToggle active={layer} onChange={setLayer} />
      </div>

      {/* Graph + Sidebar */}
      <div className="flex flex-1 overflow-hidden">
        {graphData ? (
          <GraphView
            data={graphData}
            selectedId={selectedId}
            onNodeClick={(node) => {
              if (node.type === 'Person') setSelectedId(node.id)
              else setSelectedId(null)
            }}
          />
        ) : (
          <div className="flex-1 flex items-center justify-center" style={{ color: 'var(--text-tertiary)' }}>
            <span className="font-mono text-sm animate-pulse">loading graph...</span>
          </div>
        )}

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
