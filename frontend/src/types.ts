// Mirror of CONTRACTS.md §Graph schema and §API endpoints

export type Layer = 'stress' | 'collab' | 'workload'

export type NodeStatus = 'green' | 'yellow' | 'red'
export type NodeType = 'Person' | 'Repo' | 'Task' | 'Meeting'

export interface GraphNode {
  id: string
  type: NodeType
  name: string
  role?: string
  avatar_url?: string
  // Только Person имеет overload_score/status/baseline_sentiment.
  // Task/Repo/Meeting приходят без этих полей на workload layer.
  overload_score?: number
  status?: NodeStatus
  baseline_sentiment?: number
  // Workload layer — Task-поля:
  title?: string
  priority?: string
  deadline?: string | null
  // Meeting-поля:
  datetime?: string
  duration_minutes?: number
}

export interface GraphLink {
  source: string
  target: string
  type: string
  weight: number
  metadata: Record<string, unknown>
}

export interface GraphResponse {
  layer: Layer
  nodes: GraphNode[]
  links: GraphLink[]
}

export interface PersonSignals {
  night_commits_ratio: number
  fix_revert_ratio: number
  commit_tone_delta: number
  pr_review_lag_hours: number
  bus_factor: number
  co_author_isolation: number
  weekend_activity: number
}

export interface PersonMockSignals {
  slack_silence_days: number
  velocity_delta: number
  back_to_back_meetings_pct: number
}

export interface PersonResponse {
  id: string
  name: string
  role: string
  avatar_url: string
  status: NodeStatus
  overload_score: number
  signals: PersonSignals
  mock_signals: PersonMockSignals
  neighbors: string[]
  recent_events_count: number
}

export interface InsightResponse {
  person_id: string
  generated_at: string
  model: string
  cached: boolean
  insights: string[]
  actions: string[]
}

export interface RecognitionResponse {
  person_id: string
  text: string
}
