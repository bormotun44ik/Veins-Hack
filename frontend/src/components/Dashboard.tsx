import { useState, useEffect } from 'react'
import type { DashboardResponse } from '../types'
import { fetchDashboard, postRecognition } from '../api'
import AttentionCard from './AttentionCard'
import ShoutoutCard from './ShoutoutCard'
import HeatmapMatrix from './HeatmapMatrix'

interface DashboardProps {
  onSelectPerson: (id: string) => void
}

export default function Dashboard({ onSelectPerson }: DashboardProps) {
  const [dashboard, setDashboard] = useState<DashboardResponse | null>(null)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    const ctrl = new AbortController()
    let timer: ReturnType<typeof setInterval>

    const tick = async () => {
      try {
        const data = await fetchDashboard(ctrl.signal)
        setDashboard(data)
        setError(null)
      } catch (e) {
        if (!ctrl.signal.aborted) {
          console.error('dashboard fetch:', e)
          setError('Failed to load dashboard')
        }
      }
    }

    tick()
    timer = setInterval(() => {
      if (!document.hidden) tick()
    }, 10000)

    return () => { clearInterval(timer); ctrl.abort() }
  }, [])

  if (error && !dashboard) {
    return (
      <div className="flex-1 flex items-center justify-center">
        <p className="font-mono text-xs" style={{ color: 'var(--status-red)' }}>{error}</p>
      </div>
    )
  }

  if (!dashboard) {
    return (
      <div className="flex-1 p-4 overflow-y-auto">
        {/* Skeleton */}
        <div className="max-w-3xl mx-auto space-y-4">
          <div className="animate-pulse h-16 rounded" style={{ background: 'var(--bg-elevated)' }} />
          <div className="animate-pulse h-24 w-full rounded" style={{ background: 'var(--bg-elevated)' }} />
          <div className="flex gap-3">
            <div className="animate-pulse h-20 w-28 rounded" style={{ background: 'var(--bg-elevated)' }} />
            <div className="animate-pulse h-20 w-28 rounded" style={{ background: 'var(--bg-elevated)' }} />
            <div className="animate-pulse h-20 w-28 rounded" style={{ background: 'var(--bg-elevated)' }} />
          </div>
          <div className="animate-pulse h-32 w-full rounded" style={{ background: 'var(--bg-elevated)' }} />
        </div>
      </div>
    )
  }

  const { summary, attention, shoutouts, heatmap } = dashboard

  return (
    <div className="flex-1 overflow-y-auto p-4">
      <div className="max-w-3xl mx-auto space-y-6">

        {/* Summary row */}
        <div className="grid grid-cols-2 gap-3">
          {/* Team Health */}
          <div className="p-4 rounded" style={{ background: 'var(--bg-elevated)', border: '1px solid var(--border)' }}>
            <p className="font-mono text-xs uppercase tracking-wider mb-3" style={{ color: 'var(--text-tertiary)' }}>
              Team Health
            </p>
            <div className="space-y-1">
              <div className="flex items-center gap-2">
                <span className="text-sm" style={{ color: 'var(--status-red)' }}>⬤</span>
                <span className="font-mono text-xs" style={{ color: 'var(--text-secondary)' }}>{summary.red_count} red</span>
              </div>
              <div className="flex items-center gap-2">
                <span className="text-sm" style={{ color: 'var(--status-yellow)' }}>⬤</span>
                <span className="font-mono text-xs" style={{ color: 'var(--text-secondary)' }}>{summary.yellow_count} yellow</span>
              </div>
              <div className="flex items-center gap-2">
                <span className="text-sm" style={{ color: 'var(--status-green)' }}>⬤</span>
                <span className="font-mono text-xs" style={{ color: 'var(--text-secondary)' }}>{summary.green_count} green</span>
              </div>
            </div>
          </div>

          {/* Week Summary */}
          <div className="p-4 rounded" style={{ background: 'var(--bg-elevated)', border: '1px solid var(--border)' }}>
            <p className="font-mono text-xs uppercase tracking-wider mb-3" style={{ color: 'var(--text-tertiary)' }}>
              Week Summary
            </p>
            <div className="space-y-1">
              <div className="font-mono text-xs" style={{ color: 'var(--text-secondary)' }}>
                Avg: <span style={{ color: 'var(--text-primary)' }}>{(summary.avg_overload * 100).toFixed(0)}%</span>
              </div>
              <div className="font-mono text-xs" style={{ color: 'var(--text-secondary)' }}>
                Peak:{' '}
                <span style={{ color: 'var(--status-red)' }}>
                  {summary.peak.person_id} {(summary.peak.overload_score * 100).toFixed(0)}%
                </span>
              </div>
            </div>
          </div>
        </div>

        {/* Attention */}
        {attention.length > 0 && (
          <div>
            <p className="font-mono text-xs uppercase tracking-wider mb-3" style={{ color: 'var(--text-tertiary)' }}>
              Attention ({attention.length})
            </p>
            {attention.map(person => (
              <AttentionCard
                key={person.person_id}
                person={person}
                onSelectPerson={onSelectPerson}
                onRecognition={(id) => postRecognition(id).catch(console.error)}
              />
            ))}
          </div>
        )}

        {/* Shoutouts */}
        {shoutouts.length > 0 && (
          <div>
            <p className="font-mono text-xs uppercase tracking-wider mb-3" style={{ color: 'var(--text-tertiary)' }}>
              Shoutouts 🎉
            </p>
            <div className="flex gap-3">
              {shoutouts.map(person => (
                <ShoutoutCard key={person.person_id} person={person} />
              ))}
            </div>
          </div>
        )}

        {/* Heatmap */}
        <div>
          <p className="font-mono text-xs uppercase tracking-wider mb-3" style={{ color: 'var(--text-tertiary)' }}>
            Signal Heatmap
          </p>
          <div className="p-3 rounded" style={{ background: 'var(--bg-elevated)', border: '1px solid var(--border)' }}>
            <HeatmapMatrix heatmap={heatmap} />
          </div>
        </div>

        {/* Generated at */}
        <p className="font-mono text-xs pb-4" style={{ color: 'var(--text-tertiary)' }}>
          generated {new Date(dashboard.generated_at).toLocaleString()}
        </p>

      </div>
    </div>
  )
}
