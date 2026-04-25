interface ViewToggleProps {
  view: 'dashboard' | 'graph'
  onChange: (view: 'dashboard' | 'graph') => void
}

export default function ViewToggle({ view, onChange }: ViewToggleProps) {
  const buttons: { id: 'dashboard' | 'graph'; label: string }[] = [
    { id: 'dashboard', label: 'Dashboard' },
    { id: 'graph', label: 'Graph' },
  ]

  return (
    <div className="flex items-center gap-1 p-0.5 rounded border border-[--border]"
      style={{ background: 'var(--bg-input)' }}>
      {buttons.map(btn => (
        <button
          key={btn.id}
          onClick={() => onChange(btn.id)}
          className="px-3 py-1 rounded text-xs font-mono transition-colors"
          style={
            view === btn.id
              ? { background: 'var(--accent-dim)', color: 'var(--accent)', border: '1px solid var(--accent)' }
              : { background: 'transparent', color: 'var(--text-secondary)', border: '1px solid transparent' }
          }
        >
          {btn.label}
        </button>
      ))}
    </div>
  )
}
