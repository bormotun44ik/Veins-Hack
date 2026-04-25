import type { HeatmapSignals } from '../types'

interface HeatmapMatrixProps {
  heatmap: Record<string, HeatmapSignals>
}

const SIGNAL_KEYS: (keyof HeatmapSignals)[] = [
  'night_commits_ratio',
  'fix_revert_ratio',
  'commit_tone_delta',
  'pr_review_lag_hours',
  'bus_factor',
  'co_author_isolation',
  'weekend_activity',
]

const SIGNAL_LABELS: Record<keyof HeatmapSignals, string> = {
  night_commits_ratio: 'night',
  fix_revert_ratio: 'fix',
  commit_tone_delta: 'tone',
  pr_review_lag_hours: 'lag',
  bus_factor: 'bus',
  co_author_isolation: 'iso',
  weekend_activity: 'wknd',
}

function cellColor(value: number): string {
  if (value > 0.7) return 'var(--status-red)'
  if (value > 0.4) return 'var(--status-yellow)'
  if (value > 0.1) return 'var(--accent-dim)'
  return 'transparent'
}

export default function HeatmapMatrix({ heatmap }: HeatmapMatrixProps) {
  const people = Object.keys(heatmap)

  return (
    <div className="overflow-x-auto">
      <table className="text-xs font-mono border-collapse">
        <thead>
          <tr>
            <th className="w-16 text-left pr-2" style={{ color: 'var(--text-tertiary)' }}></th>
            {SIGNAL_KEYS.map(k => (
              <th key={k} className="px-1 pb-1 text-center" style={{ color: 'var(--text-tertiary)' }}>
                {SIGNAL_LABELS[k]}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {people.map(personId => {
            const signals = heatmap[personId]
            return (
              <tr key={personId}>
                <td
                  className="pr-2 py-0.5 text-right truncate"
                  style={{ color: 'var(--text-secondary)', width: '64px', maxWidth: '64px' }}
                >
                  {personId}
                </td>
                {SIGNAL_KEYS.map(k => {
                  const val = signals[k]
                  return (
                    <td key={k} className="px-1 py-0.5">
                      <div
                        style={{
                          width: 24,
                          height: 24,
                          background: cellColor(val),
                          borderRadius: 3,
                          border: '1px solid var(--border)',
                        }}
                        title={`${personId} / ${SIGNAL_LABELS[k]}: ${(val * 100).toFixed(0)}%`}
                      />
                    </td>
                  )
                })}
              </tr>
            )
          })}
        </tbody>
      </table>
    </div>
  )
}
