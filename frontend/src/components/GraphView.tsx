import { useRef, useEffect, useState } from 'react'
import ForceGraph3D from 'react-force-graph-3d'
import type { GraphResponse, GraphNode } from '../types'

interface Props {
  data: GraphResponse
  selectedId: string | null
  onNodeClick: (node: GraphNode) => void
}

function nodeColor(node: GraphNode, selectedId: string | null): string {
  if (node.id === selectedId) return '#ffffff'
  // Non-Person nodes (Task/Repo/Meeting) — нейтральный серый
  if (node.type !== 'Person') return '#55556a'
  if (node.status === 'red') return '#ef4444'
  if (node.status === 'yellow') return '#f59e0b'
  return '#10b981'
}

function nodeVal(node: GraphNode, selectedId: string | null): number {
  const score = node.overload_score ?? 0
  const base = score * 10 + 4
  return node.id === selectedId ? base * 1.6 : base
}

export default function GraphView({ data, selectedId, onNodeClick }: Props) {
  const containerRef = useRef<HTMLDivElement>(null)
  const [dims, setDims] = useState({ width: 0, height: 0 })

  useEffect(() => {
    const el = containerRef.current
    if (!el) return
    const obs = new ResizeObserver(entries => {
      const { width, height } = entries[0].contentRect
      setDims({ width, height })
    })
    obs.observe(el)
    return () => obs.disconnect()
  }, [])

  return (
    <div ref={containerRef} className="flex-1 relative" style={{ background: '#0a0a0a' }}>
      {dims.width > 0 && (
        <ForceGraph3D
          graphData={data}
          width={dims.width}
          height={dims.height}
          backgroundColor="#0a0a0a"
          nodeVal={(node) => nodeVal(node as GraphNode, selectedId)}
          nodeColor={(node) => nodeColor(node as GraphNode, selectedId)}
          nodeOpacity={0.9}
          nodeLabel={(node) => {
            const n = node as GraphNode
            return `${n.name} (${n.role ?? n.type})`
          }}
          linkColor={() => 'rgba(255,255,255,0.12)'}
          linkWidth={(link) => {
            const l = link as { weight?: number }
            return (l.weight ?? 1) * 0.5 + 0.5
          }}
          onNodeClick={(node) => onNodeClick(node as GraphNode)}
        />
      )}
    </div>
  )
}
