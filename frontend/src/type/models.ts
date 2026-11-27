export type ProviderKind = 'llm' | 'tts' | 'stt'

export interface Provider {
  id: string
  kind: ProviderKind
  free: boolean
  models: string[]
  latency_hint?: string
  cost_tier?: string
  healthy?: boolean
}

export interface ProviderCatalog {
  status: string
  providers: Provider[]
  tts: string[]
  stt: string[]
}

export interface PlatformCatalog {
  status: string
  platforms: string[]
  default: string
}
