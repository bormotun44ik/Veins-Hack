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

// Semantic edge palette — see DESIGN.md.
// Visible against #0a0a0a background, distinguishable per edge type.
function linkColor(link: { type?: string; source?: unknown; target?: unknown }, selectedId: string | null): string {
  const t = link.type ?? ''
  const isFocused =
    selectedId !== null &&
    ((typeof link.source === 'object' && (link.source as { id?: string })?.id === selectedId) ||
     (typeof link.target === 'object' && (link.target as { id?: string })?.id === selectedId) ||
     link.source === selectedId ||
     link.target === selectedId)

  // Focused link (touches selected node) — bright emerald
  if (isFocused) return 'rgba(16,185,129,0.9)'

  // By type
  switch (t) {
    case 'co_authored':
      return 'rgba(16,185,129,0.55)'   // emerald — collaboration is the headline edge
    case 'reviews_pr':
      return 'rgba(139,92,246,0.55)'   // violet — reviews/mentorship
    case 'assigned_to':
      return 'rgba(245,158,11,0.55)'   // amber — workload edges
    case 'attended':
      return 'rgba(99,102,241,0.45)'   // indigo — meeting attendance
    case 'commits_to':
      return 'rgba(180,180,200,0.40)'  // neutral — commits-to-repo (background relationship)
    default:
      return 'rgba(200,200,220,0.45)'
  }
}

function linkWidth(link: { weight?: number; type?: string }): number {
  const w = link.weight ?? 1
  return Math.min(w * 0.6 + 1.2, 4) // 1.2..4 px
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
          linkColor={(link) => linkColor(link as { type?: string; source?: unknown; target?: unknown }, selectedId)}
          linkWidth={(link) => linkWidth(link as { weight?: number; type?: string })}
          linkOpacity={1}
          linkDirectionalParticles={(link) => {
            const t = (link as { type?: string }).type
            // Particles на co_authored / reviews_pr — показывают "поток" в этих рёбрах
            return t === 'co_authored' || t === 'reviews_pr' ? 2 : 0
          }}
          linkDirectionalParticleSpeed={0.005}
          linkDirectionalParticleWidth={2}
          linkDirectionalParticleColor={(link) => {
            const t = (link as { type?: string }).type
            if (t === 'co_authored') return '#10b981'
            if (t === 'reviews_pr') return '#8b5cf6'
            return '#ffffff'
          }}
          onNodeClick={(node) => onNodeClick(node as GraphNode)}
        />
      )}
    </div>
  )
}
