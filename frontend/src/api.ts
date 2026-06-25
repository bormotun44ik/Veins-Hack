import type {
  Layer,
  GraphResponse,
  PersonResponse,
  InsightResponse,
  RecognitionResponse,
  DashboardResponse,
} from './types'

// Resolve API base:
//   1. VITE_API_BASE env override
//   2. localhost dev — direct :8000
//   3. Anything else (LAN, cloudflare tunnel) — same-origin /api proxy via Vite
//      (Vite proxies /api/* → backend:8000, so frontend и backend на одном origin)
function resolveApiBase(): string {
  const envBase = import.meta.env.VITE_API_BASE
  if (envBase && envBase !== 'http://localhost:8000') return envBase
  if (typeof window !== 'undefined') {
    if (window.location.hostname === 'localhost' || window.location.hostname === '127.0.0.1') {
      return 'http://localhost:8000'
    }
    return '/api'
  }
  return 'http://localhost:8000'
}

const API_BASE = resolveApiBase()
const IS_MOCK = import.meta.env.VITE_MOCK === 'true'

export async function fetchGraph(layer: Layer): Promise<GraphResponse> {
  if (IS_MOCK) {
    const res = await fetch('/samples/sample_graph.json')
    const data = await res.json() as GraphResponse
    return { ...data, layer }
  }
  const res = await fetch(`${API_BASE}/graph?layer=${layer}`)
  if (!res.ok) throw new Error(`fetchGraph failed: ${res.status}`)
  return res.json() as Promise<GraphResponse>
}

export async function fetchPerson(id: string): Promise<PersonResponse> {
  if (IS_MOCK) {
    const res = await fetch('/samples/sample_person.json')
    return res.json() as Promise<PersonResponse>
  }
  const res = await fetch(`${API_BASE}/person/${id}`)
  if (!res.ok) throw new Error(`fetchPerson failed: ${res.status}`)
  return res.json() as Promise<PersonResponse>
}

export async function fetchInsights(
  id: string,
  signal?: AbortSignal,
): Promise<InsightResponse> {
  if (IS_MOCK) {
    await new Promise(r => setTimeout(r, 800))
    const res = await fetch('/samples/sample_insight.json', { signal })
    return res.json() as Promise<InsightResponse>
  }
  const res = await fetch(`${API_BASE}/insights/${id}`, { signal })
  if (!res.ok) throw new Error(`fetchInsights failed: ${res.status}`)
  return res.json() as Promise<InsightResponse>
}

export async function fetchDashboard(signal?: AbortSignal): Promise<DashboardResponse> {
  const url = IS_MOCK ? '/samples/sample_dashboard.json' : `${API_BASE}/dashboard`
  const res = await fetch(url, { signal })
  if (!res.ok) throw new Error(`dashboard ${res.status}`)
  return res.json() as Promise<DashboardResponse>
}

export async function postRecognition(id: string): Promise<RecognitionResponse> {
  if (IS_MOCK) {
    await new Promise(r => setTimeout(r, 600))
    return {
      person_id: id,
      text: `${id}, спасибо за вклад в команду! Твоя работа ценится.`,
    }
  }
  const res = await fetch(`${API_BASE}/action/recognition/${id}`, { method: 'POST' })
  if (!res.ok) throw new Error(`postRecognition failed: ${res.status}`)
  return res.json() as Promise<RecognitionResponse>
}
