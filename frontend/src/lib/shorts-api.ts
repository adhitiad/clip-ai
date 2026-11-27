import { createServerFn } from '@tanstack/react-start'
import { getRequest } from '@tanstack/react-start/server'
import { z } from 'zod'

import { auth } from '#/lib/auth'
import { env } from '#/env'
import { enqueueRender } from '#/server/queue'
import {
  createSpan,
  createTrace,
  logEvent,
  traceparent as toTraceparent,
} from '#/server/telemetry'

const SHORTS_INPUT = z.object({
  topic: z.string().min(3).max(300),
  platform: z.enum(['shorts', 'reels', 'tiktok']).default('shorts'),
  videoUrls: z.array(z.string().min(1)).max(5).default([]),
  renderVideo: z.boolean().default(false),
  maxClips: z.number().int().min(1).max(5).default(3),
  autoDiscover: z.boolean().default(true),
})

async function backendToken(headers: Headers) {
  const session = await auth.api.getSession({ headers })
  if (!session || !session.user.email) {
    throw new Error('Silakan login dengan Google dulu.')
  }
  const response = await fetch(
    `${env.SERVER_URL ?? 'http://127.0.0.1:8000'}/auth/bridge`,
    {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        email: session.user.email,
        bridge_token: env.AUTH_BRIDGE_TOKEN,
      }),
      signal: AbortSignal.timeout(10000),
    },
  )
  if (!response.ok) throw new Error('Gagal membuat token backend.')
  const data = (await response.json()) as { access_token: string }
  return data.access_token
}

type ShortsBrief = {
  clips: Array<{
    start_time?: number
    end_time?: number
    hook: string
    title: string
    caption: string
    hashtags: string[]
  }>
}

type ShortsResult = {
  status: string
  task_id?: string
  request_id?: string
  queue?: 'rabbitmq' | 'taskiq'
  brief?: ShortsBrief
  queued_clips?: number
  mix_sources?: boolean
  sources?: string[]
}

const fetchTrendTerms = async (
  token: string,
  traceparentValue?: string | null,
): Promise<string[]> => {
  try {
    const response = await fetch(
      `${env.SERVER_URL ?? 'http://127.0.0.1:8000'}/niche/trending?geo=id&max_items=5`,
      {
        headers: {
          Authorization: `Bearer ${token}`,
          ...(traceparentValue ? { traceparent: traceparentValue } : {}),
        },
        signal: AbortSignal.timeout(10000),
      },
    )
    if (!response.ok) return []
    const data = (await response.json()) as {
      trending?: Array<Record<string, unknown>>
    }
    return (data.trending ?? [])
      .map((item) => item.keyword ?? item.title ?? item.query ?? item.topic)
      .filter((value): value is string => typeof value === 'string')
      .slice(0, 5)
  } catch {
    return []
  }
}

const callAgent = async (
  token: string,
  body: Record<string, unknown>,
  traceparent?: string | null,
  timeoutMs = 300000,
) => {
  const response = await fetch(
    `${env.SERVER_URL ?? 'http://127.0.0.1:8000'}/agent/shorts`,
    {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        Authorization: `Bearer ${token}`,
        ...(traceparent ? { traceparent } : {}),
      },
      body: JSON.stringify(body),
      signal: AbortSignal.timeout(timeoutMs),
    },
  )
  const payload = (await response.json()) as ShortsResult
  if (!response.ok) {
    throw new Error(
      (payload as unknown as { detail?: string }).detail ?? 'Agent gagal.',
    )
  }
  return { payload, traceparent: response.headers.get('traceparent') }
}

export const createShorts = createServerFn({ method: 'POST' })
  .validator(SHORTS_INPUT)
  .handler(async ({ data }): Promise<ShortsResult> => {
    const token = await backendToken(getRequest().headers)
    const incoming = getRequest().headers.get('traceparent')
    const sources = data.videoUrls.map((url) => url.trim()).filter(Boolean)
    const trace = createTrace(incoming)
    const span = createSpan(trace)
    logEvent('shorts.request', span, {
      topic: data.topic,
      render: data.renderVideo,
      sources: sources.length,
    })

    if (data.renderVideo && !sources.length && !data.autoDiscover) {
      throw new Error('Minimal satu URL video sumber untuk render.')
    }

    // Multi-sumber: analisis tiap video + gabung jadi satu MP4 via Taskiq.
    if (data.renderVideo && sources.length > 1) {
      const mixed = await callAgent(
        token,
        {
          topic: data.topic,
          platform: data.platform,
          video_urls: sources,
          max_clips: data.maxClips,
          render_video: true,
          auto_discover: false,
          mix_sources: true,
          min_source_seconds: 240,
        },
        incoming,
        900000,
      )
      logEvent('shorts.enqueued', span, {
        queue: 'taskiq',
        sources: sources.length,
        mix: true,
      })
      return { ...mixed.payload, queue: 'taskiq' }
    }

    const briefCall = await callAgent(
      token,
      {
        topic: data.topic,
        platform: data.platform,
        max_clips: data.maxClips,
        render_video: false,
        auto_discover: data.autoDiscover,
      },
      incoming,
    )
    const brief = briefCall.payload.brief
    if (!data.renderVideo) return briefCall.payload

    // Auto-discover: bila tidak ada URL dan auto-discover aktif, biarkan backend
    // mencari video dari topik lalu render/mix.
    if (!sources.length && data.autoDiscover) {
      const discovered = await callAgent(
        token,
        {
          topic: data.topic,
          platform: data.platform,
          video_urls: [],
          max_clips: data.maxClips,
          render_video: true,
          auto_discover: true,
          mix_sources: true,
          min_source_seconds: 240,
        },
        incoming,
        900000,
      )
      return { ...discovered.payload, queue: 'taskiq' }
    }

    try {
      const trendTerms = await fetchTrendTerms(token, incoming)
      const job = await enqueueRender(
        {
          video_url: sources[0],
          topic: data.topic,
          platform: data.platform,
          clips: brief?.clips ?? [],
          brief,
          trend_terms: trendTerms,
          lang: 'id',
          request_id: briefCall.payload.request_id ?? '',
          traceparent: toTraceparent(span),
        },
        trace,
      )
      logEvent('shorts.enqueued', span, {
        queue: 'rabbitmq',
        job_id: job.id,
        trends: trendTerms.length,
      })
      return {
        status: 'processing',
        task_id: String(job.id),
        request_id: briefCall.payload.request_id,
        queue: 'rabbitmq',
        brief,
        queued_clips: brief?.clips.length ?? 0,
      }
    } catch {
      // RabbitMQ tidak tersedia → Taskiq via backend.
      logEvent('shorts.fallback', span, { queue: 'taskiq' })
      const fallback = await callAgent(
        token,
        {
          topic: data.topic,
          platform: data.platform,
          video_url: sources[0],
          max_clips: data.maxClips,
          render_video: true,
        },
        incoming,
      )
      return { ...fallback.payload, queue: 'taskiq' }
    }
  })

export type TaskStatus = {
  task_id: string
  status: string
  progress: { current: number; total: number; percent: number } | null
  error: string | null
}

export const getTask = createServerFn({ method: 'GET' })
  .validator(z.object({ taskId: z.string().min(1).max(64) }))
  .handler(async ({ data }) => {
    const token = await backendToken(getRequest().headers)
    const response = await fetch(
      `${env.SERVER_URL ?? 'http://127.0.0.1:8000'}/tasks/${data.taskId}`,
      {
        method: 'GET',
        headers: { Authorization: `Bearer ${token}` },
        signal: AbortSignal.timeout(10000),
      },
    )
    const payload = await response.json()
    if (!response.ok) {
      throw new Error(payload?.detail ?? 'Gagal cek status task.')
    }
    return payload as TaskStatus
  })
