import { useState } from 'react'
import { postRecognition } from '../api'
import type { InsightResponse, PersonResponse } from '../types'

interface Props {
  person: PersonResponse
  insights: InsightResponse | null
}

export default function ActionButtons({ person, insights }: Props) {
  const [showActions, setShowActions] = useState(false)
  const [showWriteModal, setShowWriteModal] = useState(false)
  const [recognitionText, setRecognitionText] = useState<string | null>(null)
  const [recognitionLoading, setRecognitionLoading] = useState(false)

  async function handleRecognition(e: React.MouseEvent<HTMLButtonElement>) {
    e.preventDefault()
    setRecognitionLoading(true)
    try {
      const result = await postRecognition(person.id)
      setRecognitionText(result.text)
    } finally {
      setRecognitionLoading(false)
    }
  }

  return (
    <div className="p-4 flex flex-col gap-2">
      <button
        onClick={() => setShowActions(v => !v)}
        className="w-full py-2 px-4 text-sm font-semibold rounded transition-colors"
        style={{ background: 'var(--accent)', color: '#000' }}
      >
        {showActions ? 'Скрыть действия' : 'Что делать'}
      </button>

      {showActions && insights && (
        <div className="rounded border p-3 space-y-2" style={{ borderColor: 'var(--border)', background: 'var(--bg-elevated)' }}>
          {insights.actions.map((action, i) => (
            <div key={i} className="flex gap-2 animate-fadeIn" style={{ animationDelay: `${i * 80}ms` }}>
              <span className="font-mono text-xs mt-0.5" style={{ color: 'var(--accent)' }}>›</span>
              <p className="text-sm leading-relaxed" style={{ color: 'var(--text-secondary)' }}>{action}</p>
            </div>
          ))}
        </div>
      )}

      <button
        onClick={() => setShowWriteModal(true)}
        className="w-full py-2 px-4 text-sm rounded border transition-colors"
        style={{
          borderColor: 'var(--border)',
          color: 'var(--text-secondary)',
        }}
      >
        Написать {person.name.split(' ')[0]}
      </button>

      <button
        onClick={handleRecognition}
        disabled={recognitionLoading}
        className="w-full py-2 px-4 text-sm rounded border font-mono transition-colors"
        style={{
          borderColor: 'var(--accent-dim)',
          color: 'var(--accent)',
        }}
      >
        {recognitionLoading ? '...' : '✦ Recognition'}
      </button>

      {recognitionText && (
        <div
          className="rounded border p-3 text-sm leading-relaxed animate-fadeIn"
          style={{ borderColor: 'var(--accent-dim)', color: 'var(--text-secondary)', background: 'var(--bg-elevated)' }}
        >
          {recognitionText}
        </div>
      )}

      {showWriteModal && (
        <div
          className="fixed inset-0 flex items-center justify-center z-50"
          style={{ background: 'rgba(0,0,0,0.7)' }}
          onClick={() => setShowWriteModal(false)}
        >
          <div
            className="rounded border p-6 w-96 max-w-[90vw]"
            style={{ background: 'var(--bg-secondary)', borderColor: 'var(--border)' }}
            onClick={e => e.stopPropagation()}
          >
            <p className="font-mono text-xs mb-3" style={{ color: 'var(--text-tertiary)' }}>
              Написать {person.name}
            </p>
            <textarea
              className="w-full rounded border p-2 text-sm resize-none"
              style={{
                background: 'var(--bg-input)',
                borderColor: 'var(--border)',
                color: 'var(--text-primary)',
                height: 120,
              }}
              defaultValue={`Привет, ${person.name.split(' ')[0]}! Хотел обсудить нагрузку — давай синхронизируемся.`}
            />
            <div className="flex gap-2 mt-3">
              <button
                onClick={() => setShowWriteModal(false)}
                className="flex-1 py-1.5 text-sm rounded border transition-colors"
                style={{ borderColor: 'var(--border)', color: 'var(--text-secondary)' }}
              >
                Отмена
              </button>
              <button
                onClick={() => setShowWriteModal(false)}
                className="flex-1 py-1.5 text-sm font-semibold rounded transition-colors"
                style={{ background: 'var(--accent)', color: '#000' }}
              >
                Отправить
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
