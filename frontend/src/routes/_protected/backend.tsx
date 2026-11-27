import { createFileRoute } from '@tanstack/react-router'
import { useQuery } from '@tanstack/react-query'
import { useState } from 'react'

import { AppShell } from '#/components/app-shell'
import { EmptyState, ErrorState, LoadingState } from '#/components/states'
import { Button } from '#/components/ui/button'
import { Input } from '#/components/ui/input'
import {
  authMeQuery,
  calibrationQuery,
  clipDetailQuery,
  clipsQuery,
  findVideosQuery,
  opsAccessLogQuery,
  healthQuery,
  historyQuery,
  modelStatusQuery,
  opsAuditQuery,
  opsCacheQuery,
  opsExportQuery,
  opsQueueQuery,
  opsTasksQuery,
  opsTracesQuery,
  opsWorkersQuery,
  overviewQuery,
  platformsQuery,
  profileQuery,
  providersQuery,
  revenueAdviceQuery,
  revenueSummaryQuery,
  searchWebQuery,
  settingsMeQuery,
  settingsOwnerQuery,
  statsQuery,
  suggestQuery,
  taskDetailQuery,
  trendingQuery,
  youtubeSchedulerQuery,
} from '#/lib/queries'

type BlockState = {
  data: unknown
  isLoading: boolean
  isError: boolean
  error: { message: string } | null
  refetch: () => unknown
}

type AccessEntry = {
  timestamp: string
  level: string
  actor: string
  flag: string
  ip: string
  email: string
  user_type: string
  device_name: string
  browser: string
  http_version: string
  method: string
  path: string
  status: number
  line: string
}

// Flag berasal dari data backend (klasifikasi user/asing/hacker/error), bukan dekorasi UI.
const FLAG = {
  hacker: String.fromCodePoint(0x274c),
  error: String.fromCodePoint(0x1f6d1),
  warning: String.fromCodePoint(0x26a0, 0xfe0f),
}

const flagColor = (flag: string) => {
  if (flag === FLAG.hacker) return 'text-red-500'
  if (flag === FLAG.error) return 'text-red-600 font-bold'
  if (flag === FLAG.warning) return 'text-amber-500'
  return 'text-emerald-500'
}

const AccessLogBlock = ({
  state,
}: {
  state: {
    data: unknown
    isLoading: boolean
    isError: boolean
    error: { message: string } | null
    refetch: () => unknown
  }
}) => {
  const rows = (Array.isArray(state.data) ? state.data : []) as AccessEntry[]
  return (
    <section className="neon-panel rise-in rounded-xl p-4 lg:col-span-2">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <h2 className="text-base font-semibold">Access Log (MongoDB)</h2>
          <p className="mt-1 text-[13px] text-[var(--ink-muted)]">
            Identitas per request: IP, email, device, browser, HTTP version.
            Merah = IP asing / hacker, hijau = user dikenal.
          </p>
        </div>
        <Button
          type="button"
          variant="outline"
          size="sm"
          className="min-h-11"
          onClick={() => void state.refetch()}
        >
          Muat ulang
        </Button>
      </div>
      {state.isLoading ? <LoadingState label="Memuat access log…" /> : null}
      {state.isError ? (
        <ErrorState
          message={state.error?.message ?? 'Gagal memuat access log.'}
          onRetry={() => void state.refetch()}
        />
      ) : null}
      {!state.isLoading && !state.isError && rows.length === 0 ? (
        <EmptyState message="Belum ada access log. Set MONGODB_URL di .env." />
      ) : null}
      {rows.length > 0 ? (
        <ul className="mt-3 max-h-96 space-y-1 overflow-auto text-xs">
          {rows.map((row, index) => (
            <li
              key={`${row.timestamp}-${index}`}
              className="rounded border border-[var(--line)] bg-[var(--ground)] p-2"
            >
              <div className="flex flex-wrap items-center gap-2">
                <span className={flagColor(row.flag)}>{row.flag}</span>
                <span className="font-medium">{row.level}</span>
                <span className="text-[var(--ink-muted)]">{row.actor}</span>
                <span className="text-[var(--ink-muted)]">{row.timestamp}</span>
              </div>
              <div className="mt-1 break-words text-[var(--ink-muted)]">
                {row.line}
              </div>
              <div className="mt-1 text-[11px] text-[var(--ink-muted)]">
                email={row.email || '-'} · device={row.device_name} · browser=
                {row.browser} · http={row.http_version} · status={row.status}
              </div>
            </li>
          ))}
        </ul>
      ) : null}
    </section>
  )
}

type DataBlockProps = {
  title: string
  description: string
  state: BlockState
  wide?: boolean
}

const DataBlock = ({
  title,
  description,
  state,
  wide = false,
}: DataBlockProps) => (
  <section
    className={`neon-panel rise-in rounded-xl p-4 ${wide ? 'lg:col-span-2' : ''}`}
  >
    <div className="flex flex-wrap items-start justify-between gap-3">
      <div className="min-w-0">
        <h2 className="text-base font-semibold">{title}</h2>
        <p className="mt-1 text-[13px] text-[var(--ink-muted)]">
          {description}
        </p>
      </div>
      <Button
        type="button"
        variant="outline"
        size="sm"
        className="min-h-11"
        onClick={() => void state.refetch()}
      >
        Muat ulang
      </Button>
    </div>
    {state.isLoading ? (
      <div className="mt-3">
        <LoadingState label={`Memuat ${title.toLowerCase()} dari backend…`} />
      </div>
    ) : null}
    {state.isError ? (
      <div className="mt-3">
        <ErrorState
          message={
            state.error?.message ?? `Gagal memuat ${title.toLowerCase()}.`
          }
          onRetry={() => void state.refetch()}
        />
      </div>
    ) : null}
    {!state.isLoading && !state.isError ? (
      state.data === undefined ? (
        <div className="mt-3">
          <EmptyState
            message={`Backend belum mengembalikan data untuk ${title.toLowerCase()}.`}
            action={{
              label: 'Muat ulang',
              onClick: () => void state.refetch(),
            }}
          />
        </div>
      ) : (
        <pre className="mt-3 max-h-80 overflow-auto whitespace-pre-wrap break-words rounded-md border border-[var(--line)] bg-[var(--ground)] p-3 text-xs">
          {JSON.stringify(state.data, null, 2)}
        </pre>
      )
    ) : null}
  </section>
)

const BackendPage = () => {
  const [clipId, setClipId] = useState('')
  const [taskId, setTaskId] = useState('')
  const [loaded, setLoaded] = useState(false)

  const auth = useQuery({ ...authMeQuery(), enabled: loaded })
  const overview = useQuery({ ...overviewQuery(), enabled: loaded })
  const profile = useQuery({ ...profileQuery(), enabled: loaded })
  const stats = useQuery({ ...statsQuery(), enabled: loaded })
  const health = useQuery({ ...healthQuery(), enabled: loaded })
  const history = useQuery({
    ...historyQuery({
      page: 1,
      pageSize: 5,
      search: '',
      sortBy: 'id',
      sortDir: 'desc',
    }),
    enabled: loaded,
  })
  const clips = useQuery({ ...clipsQuery(), enabled: loaded })
  const clipDetail = useQuery({ ...clipDetailQuery(clipId), enabled: loaded })
  const taskDetail = useQuery({ ...taskDetailQuery(taskId), enabled: loaded })

  const trending = useQuery({ ...trendingQuery('id', 5), enabled: loaded })
  const suggest = useQuery({ ...suggestQuery('id', 10), enabled: loaded })
  const findVideos = useQuery({
    ...findVideosQuery('editing video', 5),
    enabled: loaded,
  })
  const searchWeb = useQuery({
    ...searchWebQuery('short form video', 'fast'),
    enabled: loaded,
  })

  const providers = useQuery({ ...providersQuery(), enabled: loaded })
  const platforms = useQuery({ ...platformsQuery(), enabled: loaded })
  const modelStatus = useQuery({ ...modelStatusQuery(), enabled: loaded })
  const calibration = useQuery({ ...calibrationQuery(), enabled: loaded })

  const revenue = useQuery({ ...revenueSummaryQuery(), enabled: loaded })
  const advice = useQuery({ ...revenueAdviceQuery(), enabled: loaded })

  const tasks = useQuery({ ...opsTasksQuery(), enabled: loaded })
  const queue = useQuery({ ...opsQueueQuery(), enabled: loaded })
  const workers = useQuery({ ...opsWorkersQuery(), enabled: loaded })
  const cache = useQuery({ ...opsCacheQuery(), enabled: loaded })
  const traces = useQuery({ ...opsTracesQuery(), enabled: loaded })
  const exportData = useQuery({ ...opsExportQuery(), enabled: loaded })
  const audit = useQuery({ ...opsAuditQuery(), enabled: loaded })
  const accessLog = useQuery({ ...opsAccessLogQuery(), enabled: loaded })

  const settingsMe = useQuery({ ...settingsMeQuery(), enabled: loaded })
  const settingsOwner = useQuery({ ...settingsOwnerQuery(), enabled: loaded })
  const scheduler = useQuery({ ...youtubeSchedulerQuery(), enabled: loaded })

  return (
    <AppShell>
      <h1 className="neon-text display-title rise-in text-4xl">Data Backend</h1>
      <p className="mt-1 text-[15px] leading-relaxed text-muted-foreground">
        Semua endpoint GET yang dipakai aplikasi, dibaca langsung dari backend.
      </p>

      {!loaded ? (
        <section className="neon-panel rise-in mt-6 rounded-xl p-5">
          <h2 className="display-title text-lg font-semibold">
            Muat data backend
          </h2>
          <p className="mt-1 text-sm text-[var(--ink-muted)]">
            Halaman ini mengambil semua endpoint GET hanya setelah Anda
            memintanya.
          </p>
          <Button
            type="button"
            className="mt-3 min-h-11"
            onClick={() => setLoaded(true)}
          >
            Muat data backend
          </Button>
        </section>
      ) : (
        <div className="mt-6 grid grid-cols-1 gap-4 pb-24 lg:grid-cols-2 lg:pb-0">
          <DataBlock
            title="Identitas"
            description="Profil owner yang sedang login."
            state={auth}
          />
          <DataBlock
            title="Profil dashboard"
            description="Data user dari endpoint dashboard."
            state={profile}
          />
          <DataBlock
            title="Ringkasan clip"
            description="Total, rata-rata skor, dan skor tertinggi."
            state={overview}
          />
          <DataBlock
            title="Statistik 7 hari"
            description="Jumlah clip per hari dari backend."
            state={stats}
          />
          <DataBlock
            title="Kesehatan layanan"
            description="Status database dan RabbitMQ dari backend."
            state={health}
            wide
          />
          <DataBlock
            title="Riwayat clip"
            description="Lima clip terbaru lewat endpoint history."
            state={history}
            wide
          />

          <DataBlock
            title="Daftar clip"
            description="Seluruh clip yang tersimpan."
            state={clips}
          />
          <DataBlock
            title="Trending"
            description="Topik trending dari niche discovery."
            state={trending}
          />
          <DataBlock
            title="Saran niche"
            description="Rekomendasi niche dari backend."
            state={suggest}
          />
          <DataBlock
            title="Pencarian video"
            description="Contoh pencarian video YouTube."
            state={findVideos}
          />
          <DataBlock
            title="Pencarian web"
            description="Contoh pencarian web lewat backend."
            state={searchWeb}
            wide
          />

          <DataBlock
            title="Katalog provider"
            description="Provider dan model dari backend, bukan hardcode UI."
            state={providers}
          />
          <DataBlock
            title="Platform"
            description="Daftar platform shorts dari backend."
            state={platforms}
          />
          <DataBlock
            title="Status model viral"
            description="Konfirmasi bahwa scoring bersifat rule-based."
            state={modelStatus}
          />
          <DataBlock
            title="Kalibrasi skor"
            description="Korelasi prediksi dan feedback nyata."
            state={calibration}
          />

          <DataBlock
            title="Pendapatan"
            description="Ringkasan pendapatan per platform."
            state={revenue}
          />
          <section className="neon-panel rise-in rounded-xl p-4">
            <div className="flex flex-wrap items-start justify-between gap-3">
              <div className="min-w-0">
                <h2 className="text-base font-semibold">Saran pendapatan</h2>
                <p className="mt-1 text-[13px] text-[var(--ink-muted)]">
                  Diambil dari model gratis saat tombol ditekan.
                </p>
              </div>
              <Button
                type="button"
                variant="outline"
                size="sm"
                className="min-h-11"
                onClick={() => void advice.refetch()}
              >
                Ambil saran
              </Button>
            </div>
            {advice.isError ? (
              <div className="mt-3">
                <ErrorState
                  message={advice.error.message}
                  onRetry={() => void advice.refetch()}
                />
              </div>
            ) : null}
            {advice.isFetching ? (
              <div className="mt-3">
                <LoadingState label="Meminta saran dari backend…" />
              </div>
            ) : null}
            {advice.data !== undefined && !advice.isFetching ? (
              <pre className="mt-3 max-h-80 overflow-auto whitespace-pre-wrap break-words rounded-md border border-[var(--line)] bg-[var(--ground)] p-3 text-xs">
                {JSON.stringify(advice.data, null, 2)}
              </pre>
            ) : null}
          </section>

          <DataBlock
            title="Task"
            description="Daftar hasil task render."
            state={tasks}
          />
          <DataBlock
            title="Antrean"
            description="Kesehatan broker dan jumlah task per status."
            state={queue}
          />
          <DataBlock
            title="Worker"
            description="Jumlah worker yang disarankan dan terkonfigurasi."
            state={workers}
          />
          <DataBlock
            title="Cache render"
            description="Entren cache dari manifest artefak."
            state={cache}
          />
          <DataBlock
            title="Trace"
            description="Riwayat jejak request backend."
            state={traces}
          />
          <DataBlock
            title="Ekspor data"
            description="Seluruh data pribadi yang bisa diekspor."
            state={exportData}
          />
          <DataBlock
            title="Audit AI"
            description="Catatan panggilan LLM, TTS, dan STT."
            state={audit}
            wide
          />
          <AccessLogBlock state={accessLog} />

          <DataBlock
            title="Pengaturan user"
            description="Preferensi profil pribadi."
            state={settingsMe}
          />
          <DataBlock
            title="Pengaturan owner"
            description="Pengaturan monitoring dan notifikasi."
            state={settingsOwner}
          />
          <DataBlock
            title="Scheduler YouTube"
            description="Status penjadwalan riset video."
            state={scheduler}
            wide
          />

          <section className="neon-panel rise-in rounded-xl p-4 lg:col-span-2">
            <h2 className="text-base font-semibold">Detail berdasarkan ID</h2>
            <p className="mt-1 text-[13px] text-[var(--ink-muted)]">
              Masukkan ID clip atau task untuk memanggil endpoint detail.
            </p>
            <div className="mt-3 grid grid-cols-1 gap-3 md:grid-cols-2">
              <div className="min-w-0">
                <label className="text-xs" htmlFor="clip-id">
                  ID clip
                </label>
                <Input
                  id="clip-id"
                  inputMode="numeric"
                  value={clipId}
                  onChange={(event) => setClipId(event.target.value)}
                  placeholder="1"
                  className="mt-1 min-h-11"
                />
              </div>
              <div className="min-w-0">
                <label className="text-xs" htmlFor="task-id">
                  ID task
                </label>
                <Input
                  id="task-id"
                  value={taskId}
                  onChange={(event) => setTaskId(event.target.value)}
                  placeholder="task-id"
                  className="mt-1 min-h-11"
                />
              </div>
            </div>
            <div className="mt-3 grid grid-cols-1 gap-3 md:grid-cols-2">
              <div className="min-w-0">
                <DataBlock
                  title="Detail clip"
                  description="Respons GET /clips/{id}."
                  state={clipDetail}
                />
              </div>
              <div className="min-w-0">
                <DataBlock
                  title="Detail task"
                  description="Respons GET /tasks/{id}."
                  state={taskDetail}
                />
              </div>
            </div>
          </section>
        </div>
      )}
    </AppShell>
  )
}

export const Route = createFileRoute('/_protected/backend')({
  component: BackendPage,
})
