import { useState } from 'react'
import type { ShoutoutPerson } from '../types'
import { postRecognition } from '../api'

interface ShoutoutCardProps {
  person: ShoutoutPerson
}

export default function ShoutoutCard({ person }: ShoutoutCardProps) {
  const [sent, setSent] = useState(false)

  const handleRecognition = async () => {
    setSent(false)
    try {
      await postRecognition(person.person_id)
      setSent(true)
      setTimeout(() => setSent(false), 2000)
    } catch (e) {
      console.error('recognition failed:', e)
    }
  }

  const pct = (person.overload_score * 100).toFixed(0)

  return (
    <div
      className="flex flex-col items-center p-3 rounded"
      style={{
        background: 'var(--bg-elevated)',
        border: '1px solid var(--border)',
        minWidth: '100px',
        flex: '1',
      }}
    >
      <img
        src={person.avatar_url}
        alt={person.name}
        className="w-8 h-8 rounded-full opacity-90 mb-1"
      />
      <span className="text-xs font-semibold mb-0.5 text-center" style={{ color: 'var(--text-primary)' }}>
        {person.name.split(' ')[0]}
      </span>
      <span className="font-mono text-xs mb-2" style={{ color: 'var(--status-green)' }}>
        {pct}%
      </span>
      <button
        onClick={handleRecognition}
        className="text-xs font-mono px-2 py-1 rounded transition-colors w-full text-center"
        style={{
          border: '1px solid var(--accent-dim)',
          color: sent ? 'var(--status-green)' : 'var(--accent)',
        }}
      >
        {sent ? '✓ Sent' : 'Recognition'}
      </button>
    </div>
  )
}
