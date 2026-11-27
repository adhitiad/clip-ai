import { createFileRoute } from '@tanstack/react-router'
import { useQuery } from '@tanstack/react-query'
import { Suspense, lazy, useEffect, useState } from 'react'

import { AppShell } from '#/components/app-shell'
import { ErrorState, LoadingState } from '#/components/states'
import { Badge } from '#/components/ui/badge'
import { Button } from '#/components/ui/button'
import { Card, CardContent, CardHeader, CardTitle } from '#/components/ui/card'
import { Checkbox } from '#/components/ui/checkbox'
import { Input } from '#/components/ui/input'
import { Label } from '#/components/ui/label'
import { Progress } from '#/components/ui/progress'
import { Textarea } from '#/components/ui/textarea'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '#/components/ui/select'
import { platformsQuery } from '#/lib/queries'
import { createShorts, getTask } from '#/lib/shorts-api'
import type { PlatformCatalog } from '#/type/models'

// Sama seperti halaman /: TanStack DB tidak ikut preload rute shorts.
const ModelProviderGrid = lazy(async () => {
  const module = await import('#/components/ModelBadge')
  return { default: module.ModelProviderGrid }
})

type Result = Awaited<ReturnType<typeof createShorts>>
type Task = Awaited<ReturnType<typeof getTask>>

const ShortsPage = () => {
  const [topic, setTopic] = useState('momen seru bola')
  const [platform, setPlatform] = useState('')
  const [videoUrlsText, setVideoUrlsText] = useState('')
  const [renderVideo, setRenderVideo] = useState(false)
  const [autoDiscover, setAutoDiscover] = useState(true)
  const [maxClips, setMaxClips] = useState(2)
  const [result, setResult] = useState<Result | null>(null)
  const [task, setTask] = useState<Task | null>(null)
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(false)

  const platforms = useQuery(platformsQuery())
  const catalog = platforms.data as PlatformCatalog | undefined

  useEffect(() => {
    if (catalog && !platform) setPlatform(catalog.default)
  }, [catalog, platform])

  const taskId = result?.task_id ?? null
  const shouldPoll = taskId !== null && result?.status === 'processing'

  useEffect(() => {
    if (!shouldPoll || !taskId) return
    let cancelled = false
    const poll = async () => {
      const taskStatus = await getTask({ data: { taskId } })
      if (cancelled) return
      setTask(taskStatus)
      if (taskStatus.status === 'SUCCESS' || taskStatus.status === 'FAILURE') {
        clearInterval(timer)
      }
    }
    const timer = setInterval(poll, 5000)
    return () => {
      cancelled = true
      clearInterval(timer)
    }
  }, [shouldPoll, taskId])

  const submit = async (event: React.FormEvent) => {
    event.preventDefault()
    setLoading(true)
    setError('')
    setResult(null)
    setTask(null)
    const videoUrls = videoUrlsText
      .split(/\r?\n/)
      .map((url) => url.trim())
      .filter(Boolean)
    try {
      setResult(
        await createShorts({
          data: {
            topic,
            platform: platform as 'shorts' | 'reels' | 'tiktok',
            videoUrls,
            renderVideo,
            maxClips,
            autoDiscover: autoDiscover,
          },
        }),
      )
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err))
    } finally {
      setLoading(false)
    }
  }

  return (
    <AppShell>
      <div className="mx-auto max-w-6xl space-y-8">
        <header>
          <h1 className="neon-text display-title rise-in text-4xl">
            Agent Shorts / Reels / TikTok
          </h1>
          <p className="text-[var(--ink-muted)]">
            Rencanakan konten, lalu opsional render MP4 9:16 lewat pipeline yang
            sudah ada.
          </p>
        </header>

        <form onSubmit={submit} className="grid gap-4 md:grid-cols-2">
          <Card className="md:col-span-2">
            <CardHeader>
              <CardTitle>Rencana konten</CardTitle>
            </CardHeader>
            <CardContent className="grid gap-4 md:grid-cols-2">
              <div className="space-y-1">
                <Label htmlFor="topic">Topik</Label>
                <Input
                  id="topic"
                  value={topic}
                  onChange={(event) => setTopic(event.target.value)}
                  minLength={3}
                  required
                />
              </div>
              <div className="space-y-1">
                <Label htmlFor="platform">Platform</Label>
                {platforms.isLoading ? <LoadingState /> : null}
                {platforms.error ? (
                  <ErrorState
                    message={platforms.error.message}
                    onRetry={() => void platforms.refetch()}
                  />
                ) : null}
                <Select value={platform} onValueChange={setPlatform}>
                  <SelectTrigger id="platform" className="min-h-11">
                    <SelectValue placeholder="Pilih platform" />
                  </SelectTrigger>
                  <SelectContent>
                    {(catalog?.platforms ?? []).map((item) => (
                      <SelectItem key={item} value={item}>
                        {item}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>
              <div className="space-y-1 md:col-span-2">
                <Label htmlFor="videoUrls">
                  URL video sumber (satu per baris, opsional)
                </Label>
                <Textarea
                  id="videoUrls"
                  value={videoUrlsText}
                  onChange={(event) => setVideoUrlsText(event.target.value)}
                  placeholder={
                    'https://youtube.com/watch?v=...\nhttps://youtu.be/...'
                  }
                  rows={3}
                />
                <p className="text-xs text-[var(--ink-muted)]">
                  Kosongkan bila ingin AI mencari otomatis dari topik (2-10
                  video &gt;4 menit). Isi 2 URL berbeda atau lebih untuk mix
                  menjadi satu short. Satu URL → render biasa.
                </p>
              </div>
              <div className="space-y-1">
                <Label htmlFor="maxClips">Jumlah klip</Label>
                <Input
                  id="maxClips"
                  type="number"
                  min={1}
                  max={5}
                  className="min-h-11"
                  value={maxClips}
                  onChange={(event) => setMaxClips(Number(event.target.value))}
                />
              </div>
              <div className="flex items-center gap-2 self-end">
                <Checkbox
                  id="renderVideo"
                  checked={renderVideo}
                  onCheckedChange={(checked) =>
                    setRenderVideo(checked === true)
                  }
                />
                <Label htmlFor="renderVideo">Render video (antre Taskiq)</Label>
              </div>
              <div className="flex items-center gap-2 self-end">
                <Checkbox
                  id="autoDiscover"
                  checked={autoDiscover}
                  onCheckedChange={(checked) =>
                    setAutoDiscover(checked === true)
                  }
                />
                <Label htmlFor="autoDiscover">
                  Cari video otomatis dari topik bila URL kosong
                </Label>
              </div>
              <Button
                type="submit"
                disabled={loading || !platform}
                className="shonen-action min-h-11 md:col-span-2"
              >
                {loading ? 'Memproses...' : 'Buat brief / render'}
              </Button>
            </CardContent>
          </Card>
        </form>

        {error ? <ErrorState message={error} /> : null}

        {result?.brief ? (
          <section className="space-y-3">
            <h2 className="text-xl font-semibold">Brief</h2>
            {result.brief.clips.map((clip, index) => (
              <Card key={index}>
                <CardHeader>
                  <CardTitle>{clip.title}</CardTitle>
                </CardHeader>
                <CardContent className="space-y-2">
                  <p>{clip.hook}</p>
                  <p className="text-sm opacity-70">{clip.caption}</p>
                  <div className="flex flex-wrap gap-2">
                    {clip.hashtags.map((tag) => (
                      <Badge key={tag} variant="outline">
                        {tag}
                      </Badge>
                    ))}
                  </div>
                </CardContent>
              </Card>
            ))}
            {result.task_id ? (
              <p className="text-sm">
                Task: <code>{result.task_id}</code> · Request:{' '}
                <code>{result.request_id}</code>
              </p>
            ) : null}
            {task ? (
              <div className="space-y-2 text-sm">
                <p>
                  Status task: <code>{task.status}</code>
                  {task.error ? (
                    <span className="text-destructive"> · {task.error}</span>
                  ) : null}
                </p>
                {task.progress ? (
                  <div className="space-y-1">
                    <Progress
                      value={task.progress.percent}
                      aria-label="Progres render"
                    />
                    <span className="text-xs text-[var(--ink-muted)]">
                      {task.progress.current} / {task.progress.total} (
                      {task.progress.percent}%)
                    </span>
                  </div>
                ) : null}
              </div>
            ) : null}
          </section>
        ) : null}

        <section>
          <h2 className="mb-3 text-xl font-semibold">Provider yang tersedia</h2>
          <Suspense fallback={<LoadingState />}>
            <ModelProviderGrid />
          </Suspense>
        </section>
      </div>
    </AppShell>
  )
}

export const Route = createFileRoute('/_protected/shorts')({
  component: ShortsPage,
})
