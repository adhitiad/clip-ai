import { useQuery } from '@tanstack/react-query'
import { eq, useLiveQuery } from '@tanstack/react-db'

import { savedProvidersCollection } from '#/db-collections'
import { providersQuery } from '#/lib/queries'
import type { Provider, ProviderCatalog } from '#/type/models'
import { EmptyState, ErrorState, LoadingState } from '#/components/states'
import { Badge } from '#/components/ui/badge'
import { Button } from '#/components/ui/button'

type Props = {
  provider: string
  model?: string
  showFree?: boolean
}

/** Badge model AI: id provider + model + penanda GRATIS dari backend. */
export const ModelBadge = ({ provider, model, showFree = true }: Props) => {
  const query = useQuery(providersQuery())
  const catalog = query.data as ProviderCatalog | undefined
  const info = catalog?.providers.find((p) => p.id === provider)
  const free = showFree && (info?.free ?? false)

  return (
    <span className="inline-flex items-center gap-1.5 rounded-full border border-[var(--line)] bg-[var(--raised)] px-3 py-1 text-sm">
      <span className="font-medium">{provider}</span>
      {model ? (
        <span className="text-[var(--ink-muted)]">/ {model}</span>
      ) : null}
      {free ? (
        <Badge
          variant="outline"
          className="neon-glow-magenta border-[var(--magenta)] text-[var(--magenta)]"
        >
          GRATIS
        </Badge>
      ) : null}
    </span>
  )
}

const ProviderCard = ({ provider }: { provider: Provider }) => {
  const { data: savedRows } = useLiveQuery({
    query: (q) =>
      q
        .from({ saved: savedProvidersCollection })
        .where(({ saved }) => eq(saved.id, provider.id)),
  })
  const isSaved = savedRows.length > 0

  const toggleSaved = () => {
    if (isSaved) {
      savedProvidersCollection.delete(provider.id)
      return
    }
    savedProvidersCollection.insert({ id: provider.id, name: provider.id })
  }

  return (
    <div
      className={`neon-panel rise-in rounded-xl p-4 ${
        isSaved ? 'neon-glow' : ''
      }`}
    >
      <div className="flex items-center gap-3">
        <div>
          <div className="font-medium">{provider.id}</div>
          <div className="text-xs text-[var(--ink-muted)]">{provider.kind}</div>
          <div className="mt-1 flex flex-wrap gap-1 text-[10px]">
            {provider.cost_tier ? (
              <span className="rounded-full border border-white/15 px-2 py-0.5">
                {provider.cost_tier}
              </span>
            ) : null}
            {provider.latency_hint ? (
              <span className="rounded-full border border-white/15 px-2 py-0.5">
                {provider.latency_hint}
              </span>
            ) : null}
            {provider.healthy === false ? (
              <span className="rounded-full bg-destructive/15 px-2 py-0.5 text-destructive">
                MATI
              </span>
            ) : null}
          </div>
        </div>
        <Button
          type="button"
          onClick={toggleSaved}
          aria-pressed={isSaved}
          variant="outline"
          size="sm"
          className={`ml-auto min-h-11 ${isSaved ? 'neon-glow' : ''}`}
        >
          {isSaved ? 'Tersimpan' : 'Simpan'}
        </Button>
      </div>
      <ul className="mt-3 space-y-1 text-xs text-[var(--ink-muted)]">
        {provider.models.map((m) => (
          <li key={m} className="truncate">
            • {m}
          </li>
        ))}
      </ul>
    </div>
  )
}

const ProviderRow = ({ provider }: { provider: Provider }) => (
  <li className="flex flex-wrap items-baseline justify-between gap-2 border-b border-[var(--line)] py-2 last:border-b-0">
    <span className="font-medium">{provider.id}</span>
    <span className="text-xs text-[var(--ink-muted)]">
      {provider.models.join(', ')}
    </span>
  </li>
)

/** Daftar provider dikelompokkan menurut kind dari backend. */
export const ModelProviderGrid = () => {
  const query = useQuery(providersQuery())
  const catalog = query.data as ProviderCatalog | undefined

  if (query.isLoading) return <LoadingState />
  if (query.error) {
    return (
      <ErrorState
        message={query.error.message}
        onRetry={() => void query.refetch()}
      />
    )
  }
  if (!catalog || catalog.providers.length === 0) {
    return (
      <EmptyState
        message="Backend belum mengembalikan daftar provider."
        action={{ label: 'Muat ulang', onClick: () => void query.refetch() }}
      />
    )
  }

  const llm = catalog.providers.filter((p) => p.kind === 'llm')
  const tts = catalog.providers.filter((p) => p.kind === 'tts')
  const stt = catalog.providers.filter((p) => p.kind === 'stt')

  return (
    <div className="space-y-10">
      <section>
        <h2 className="text-xl font-semibold">LLM</h2>
        <p className="mt-1 text-sm text-[var(--ink-muted)]">
          Model chat lewat LangChain.
        </p>
        <ul className="mt-4 grid grid-cols-1 gap-3 sm:grid-cols-2 lg:grid-cols-3">
          {llm.map((p) => (
            <li key={p.id}>
              <ProviderCard provider={p} />
            </li>
          ))}
        </ul>
      </section>
      <section>
        <h2 className="text-xl font-semibold">Audio</h2>
        <p className="mt-1 text-sm text-[var(--ink-muted)]">
          Jalur teks menjadi suara dan suara menjadi teks.
        </p>
        <div className="mt-4 grid grid-cols-1 gap-8 md:grid-cols-2">
          <div>
            <h3 className="text-sm font-semibold">Text to speech</h3>
            <ul className="mt-2">
              {tts.map((p) => (
                <ProviderRow key={p.id} provider={p} />
              ))}
            </ul>
          </div>
          <div>
            <h3 className="text-sm font-semibold">Speech to text</h3>
            <ul className="mt-2">
              {stt.map((p) => (
                <ProviderRow key={p.id} provider={p} />
              ))}
            </ul>
          </div>
        </div>
      </section>
    </div>
  )
}
