import type { AttentionPerson, NodeStatus } from '../types'

interface AttentionCardProps {
  person: AttentionPerson
  onSelectPerson: (id: string) => void
  onRecognition: (id: string) => void
}

function statusColor(status: NodeStatus): string {
  if (status === 'red') return 'var(--status-red)'
  if (status === 'yellow') return 'var(--status-yellow)'
  return 'var(--status-green)'
}

function statusLabel(status: NodeStatus): string {
  return status.toUpperCase()
}

export default function AttentionCard({ person, onSelectPerson, onRecognition }: AttentionCardProps) {
  const color = statusColor(person.status)
  const pct = (person.overload_score * 100).toFixed(0)

  return (
    <div
      className="rounded p-4 mb-3"
      style={{ background: 'var(--bg-elevated)', border: '1px solid var(--border)' }}
    >
      {/* Header row */}
      <div className="flex items-start gap-3 mb-3">
        <img
          src={person.avatar_url}
          alt={person.name}
          className="w-10 h-10 rounded-full opacity-90 shrink-0"
        />
        <div className="flex-1 min-w-0">
          <div className="flex items-center justify-between gap-2">
            <span className="font-semibold text-sm" style={{ color: 'var(--text-primary)' }}>
              {person.name}
            </span>
            <span
              className="font-mono text-xs px-2 py-0.5 rounded shrink-0"
              style={{ color, background: `${color}22`, border: `1px solid ${color}55` }}
            >
              ⬤ {statusLabel(person.status)} {pct}%
            </span>
          </div>
          <span className="font-mono text-xs" style={{ color: 'var(--text-secondary)' }}>
            {person.role}
          </span>
        </div>
      </div>

      {/* Overload bar */}
      <div className="mb-3">
        <div className="h-1 rounded-full" style={{ background: 'var(--bg-secondary)' }}>
          <div
            className="h-1 rounded-full transition-all duration-500"
            style={{ width: `${person.overload_score * 100}%`, background: color }}
          />
        </div>
      </div>

      {/* Primary reason */}
      {person.primary_reason && (
        <p className="text-xs font-mono mb-2 italic" style={{ color: 'var(--text-tertiary)' }}>
          "{person.primary_reason}"
        </p>
      )}

      {/* Insight & action */}
      <div className="mb-3 space-y-1">
        {person.top_insight ? (
          <div className="flex gap-2">
            <span className="font-mono text-xs shrink-0" style={{ color: 'var(--text-secondary)' }}>›</span>
            <p className="text-xs leading-relaxed" style={{ color: 'var(--text-secondary)' }}>
              {person.top_insight}
            </p>
          </div>
        ) : (
          <div className="flex gap-2">
            <span className="font-mono text-xs shrink-0" style={{ color: 'var(--text-tertiary)' }}>›</span>
            <p className="text-xs italic" style={{ color: 'var(--text-tertiary)' }}>
              warm cache via prewarm
            </p>
          </div>
        )}
        {person.top_action && (
          <div className="flex gap-2">
            <span className="font-mono text-xs shrink-0" style={{ color: 'var(--accent)' }}>→</span>
            <p className="text-xs leading-relaxed" style={{ color: 'var(--accent)' }}>
              {person.top_action}
            </p>
          </div>
        )}
      </div>

      {/* Buttons */}
      <div className="flex gap-2">
        <button
          onClick={() => onSelectPerson(person.person_id)}
          className="flex-1 py-1.5 px-3 rounded text-xs font-semibold transition-colors"
          style={{ background: 'var(--accent)', color: '#000' }}
        >
          View details
        </button>
        <button
          onClick={() => onRecognition(person.person_id)}
          className="flex-1 py-1.5 px-3 rounded text-xs font-mono transition-colors"
          style={{ border: '1px solid var(--accent-dim)', color: 'var(--accent)' }}
        >
          ✦ Recognition
        </button>
      </div>
    </div>
  )
}
