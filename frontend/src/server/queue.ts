import { spawn } from 'node:child_process'
import { resolve } from 'node:path'

import { connect } from 'amqplib'
import type { Channel, ChannelModel, ConsumeMessage } from 'amqplib'

import { env } from '#/env'
import {
  createSpan,
  createTrace,
  logEvent,
  traceparent,
} from '#/server/telemetry'
import type { Trace } from '#/server/telemetry'

export type RenderJobData = {
  video_url: string
  topic?: string
  platform?: string
  clips: Array<Record<string, unknown>>
  brief?: Record<string, unknown> | null
  trend_terms?: string[]
  viral_threshold?: number
  lang: string
  request_id: string
  traceparent?: string
}

const QUEUE_NAME = 'shorts-render'
const url = env.RABBITMQ_URL ?? 'amqp://guest:guest@localhost:5672//'

let connection: ChannelModel | null = null
let channel: Channel | null = null

const getChannel = async (): Promise<Channel> => {
  if (!connection) connection = await connect(url)
  if (!channel) {
    channel = await connection.createChannel()
    await channel.assertQueue(QUEUE_NAME, { durable: true })
  }
  return channel
}

export const enqueueRender = async (data: RenderJobData, trace?: Trace) => {
  const span = createSpan(trace ?? createTrace(data.traceparent))
  logEvent('rabbitmq.enqueue', span, {
    request_id: data.request_id,
    clips: data.clips.length,
  })
  const queue = await getChannel()
  const messageId = crypto.randomUUID()
  const sent = queue.sendToQueue(
    QUEUE_NAME,
    Buffer.from(JSON.stringify(data)),
    { persistent: true, messageId },
  )
  if (!sent) throw new Error('RabbitMQ menolak pesan (backpressure)')
  return { id: messageId }
}

const runPythonRender = (data: RenderJobData) =>
  new Promise<Record<string, unknown>>((resolvePromise, reject) => {
    const root = resolve(
      process.cwd(),
      process.cwd().endsWith('frontend') ? '..' : '.',
    )
    const child = spawn(
      'uv',
      ['run', 'python', 'backend/scripts/render_job.py'],
      {
        cwd: root,
        env: {
          ...process.env,
          TRACEPARENT: traceparent(createSpan(createTrace(data.traceparent))),
          REQUEST_ID: data.request_id,
        },
      },
    )
    child.stdin.end(JSON.stringify(data))
    let stdout = ''
    let stderr = ''
    child.stdout.on('data', (chunk) => (stdout += String(chunk)))
    child.stderr.on('data', (chunk) => (stderr += String(chunk)))
    child.on('error', reject)
    child.on('close', (code) => {
      if (code !== 0)
        return reject(new Error(stderr || `render_job exit ${code}`))
      try {
        resolvePromise(JSON.parse(stdout) as Record<string, unknown>)
      } catch (error) {
        reject(error)
      }
    })
  })

export const startRenderWorker = async () => {
  const queue = await getChannel()
  await queue.prefetch(1)

  await queue.consume(QUEUE_NAME, async (message: ConsumeMessage | null) => {
    if (!message) return
    const data = JSON.parse(message.content.toString()) as RenderJobData
    const span = createSpan(createTrace(data.traceparent))
    logEvent('rabbitmq.job.start', span, {
      message_id: message.properties.messageId,
    })
    try {
      const result = await runPythonRender(data)
      logEvent('rabbitmq.job.done', span, {
        message_id: message.properties.messageId,
        cached: result.cached ?? false,
      })
      queue.ack(message)
    } catch (error) {
      logEvent('rabbitmq.job.failed', span, {
        message_id: message.properties.messageId,
        error: String(error),
      })
      queue.nack(message, false, false)
    }
  })

  return { name: QUEUE_NAME }
}
