import { useEffect, useState } from 'react'
import { fetchPerson, fetchInsights } from '../api'
import type { PersonResponse, InsightResponse, NodeStatus } from '../types'
import ActionButtons from './ActionButtons'

interface Props {
  selectedId: string | null
}

function statusColor(status: NodeStatus): string {
  if (status === 'red') return '#ef4444'
  if (status === 'yellow') return '#f59e0b'
  return '#10b981'
}

const SIGNAL_LABELS: Record<string, string> = {
  night_commits_ratio:  'night commits',
  fix_revert_ratio:     'fix/revert ratio',
  commit_tone_delta:    'tone delta',
  pr_review_lag_hours:  'review lag (h)',
  bus_factor:           'bus factor',
  co_author_isolation:  'co-author isolation',
  weekend_activity:     'weekend activity',
}

export default function InsightPanel({ selectedId }: Props) {
  const [personData, setPersonData] = useState<PersonResponse | null>(null)
  const [insightData, setInsightData] = useState<InsightResponse | null>(null)
  const [isLoadingInsights, setIsLoadingInsights] = useState(false)

  useEffect(() => {
    if (!selectedId) {
      setPersonData(null)
      setInsightData(null)
      return
    }

    setPersonData(null)
    setInsightData(null)

    fetchPerson(selectedId).then(setPersonData).catch(() => {})

    const ctrl = new AbortController()
    setIsLoadingInsights(true)
    fetchInsights(selectedId, ctrl.signal)
      .then(data => {
        setInsightData(data)
        setIsLoadingInsights(false)
      })
      .catch(err => {
        if ((err as Error).name !== 'AbortError') setIsLoadingInsights(false)
      })

    return () => ctrl.abort()
  }, [selectedId])

  if (!selectedId) {
    return (
      <div className="flex flex-col items-center justify-center h-full gap-3" style={{ color: 'var(--text-tertiary)' }}>
        <span className="text-4xl" style={{ opacity: 0.3 }}>◈</span>
        <p className="text-sm font-mono">select a node to inspect</p>
      </div>
    )
  }

  if (!personData) {
    return (
      <div className="p-4 space-y-3">
        <div className="h-10 rounded animate-pulse" style={{ background: 'var(--bg-elevated)' }} />
        <div className="h-4 rounded animate-pulse w-3/4" style={{ background: 'var(--bg-elevated)' }} />
        <div className="h-4 rounded animate-pulse w-1/2" style={{ background: 'var(--bg-elevated)' }} />
      </div>
    )
  }

  const color = statusColor(personData.status)
  const signals = Object.entries(personData.signals).map(([key, value]) => ({
    key,
    label: SIGNAL_LABELS[key] ?? key,
    value: Math.abs(value as number),
  }))

  return (
    <div className="flex flex-col h-full overflow-y-auto">
      {/* Person Card */}
      <div className="p-4 border-b shrink-0" style={{ borderColor: 'var(--border)' }}>
        <div className="flex items-start gap-3">
          <img
            src={personData.avatar_url}
            alt={personData.name}
            className="w-10 h-10 rounded-full"
            style={{ opacity: 0.9 }}
          />
          <div className="flex-1">
            <div className="flex items-center justify-between">
              <span className="font-semibold text-base" style={{ color: 'var(--text-primary)' }}>
                {personData.name}
              </span>
              <span className="text-xs font-mono flex items-center gap-1" style={{ color }}>
                ⬤ {personData.status.toUpperCase()}
              </span>
            </div>
            <span className="text-xs font-mono" style={{ color: 'var(--text-secondary)' }}>
              {personData.role}
            </span>
          </div>
        </div>

        {/* Overload bar */}
        <div className="mt-3">
          <div className="flex justify-between text-xs font-mono mb-1" style={{ color: 'var(--text-tertiary)' }}>
            <span>overload</span>
            <span>{(personData.overload_score * 100).toFixed(0)}%</span>
          </div>
          <div className="h-1 rounded-full" style={{ background: 'var(--bg-elevated)' }}>
            <div
              className="h-1 rounded-full transition-all duration-500"
              style={{ width: `${personData.overload_score * 100}%`, backgroundColor: color }}
            />
          </div>
        </div>
      </div>

      {/* Signals */}
      <div className="p-4 border-b shrink-0" style={{ borderColor: 'var(--border)' }}>
        <h3 className="text-xs font-mono uppercase tracking-wider mb-3" style={{ color: 'var(--text-tertiary)' }}>
          signals
        </h3>
        {signals.map(({ key, label, value }) => (
          <div key={key} className="flex items-center gap-2 mb-2">
            <span className="text-xs font-mono shrink-0 w-36" style={{ color: 'var(--text-secondary)' }}>
              {label}
            </span>
            <div className="flex-1 h-1 rounded-full" style={{ background: 'var(--bg-elevated)' }}>
              <div
                className="h-1 rounded-full"
                style={{ width: `${Math.min(value * 100, 100)}%`, background: 'var(--accent)' }}
              />
            </div>
            <span className="text-xs font-mono w-8 text-right" style={{ color: 'var(--text-tertiary)' }}>
              {(value * 100).toFixed(0)}
            </span>
          </div>
        ))}
      </div>

      {/* Insights */}
      {isLoadingInsights && (
        <div className="p-4 space-y-2 shrink-0">
          {[85, 75, 65].map((w, i) => (
            <div
              key={i}
              className="h-3 rounded animate-pulse"
              style={{ width: `${w}%`, background: 'var(--bg-elevated)' }}
            />
          ))}
        </div>
      )}

      {!isLoadingInsights && insightData && (
        <div className="p-4 border-b shrink-0" style={{ borderColor: 'var(--border)' }}>
          <h3 className="text-xs font-mono uppercase tracking-wider mb-3" style={{ color: 'var(--text-tertiary)' }}>
            insights
          </h3>
          {insightData.insights.map((text, i) => (
            <div
              key={i}
              className="flex gap-2 mb-2 animate-fadeIn"
              style={{ animationDelay: `${i * 80}ms` }}
            >
              <span className="font-mono text-xs mt-0.5 shrink-0" style={{ color: 'var(--accent)' }}>›</span>
              <p className="text-sm leading-relaxed" style={{ color: 'var(--text-secondary)' }}>{text}</p>
            </div>
          ))}
        </div>
      )}

      {/* Action Buttons */}
      {personData && (
        <div className="mt-auto shrink-0">
          <ActionButtons person={personData} insights={insightData} />
        </div>
      )}
    </div>
  )
}
