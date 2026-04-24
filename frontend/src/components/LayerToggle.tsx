import type { Layer } from '../types'

const LAYERS: { id: Layer; label: string; icon: string }[] = [
  { id: 'stress',   label: 'Stress',   icon: '⬤' },
  { id: 'collab',   label: 'Collab',   icon: '⬡' },
  { id: 'workload', label: 'Workload', icon: '▦' },
]

interface Props {
  active: Layer
  onChange: (layer: Layer) => void
}

export default function LayerToggle({ active, onChange }: Props) {
  return (
    <div className="flex gap-1 p-1 rounded" style={{ background: 'var(--bg-secondary)' }}>
      {LAYERS.map(({ id, label, icon }) => {
        const isActive = id === active
        return (
          <button
            key={id}
            onClick={() => onChange(id)}
            className={[
              'flex items-center gap-1.5 px-3 py-1 text-xs font-mono rounded border transition-colors',
              isActive
                ? 'border-[--accent] text-[--accent]'
                : 'border-[--border] text-[--text-secondary] hover:border-[--border-hover] hover:text-[--text-primary]',
            ].join(' ')}
            style={isActive ? { background: 'var(--accent-dim)' } : {}}
          >
            <span className="text-[10px]">{icon}</span>
            {label}
          </button>
        )
      })}
    </div>
  )
}
