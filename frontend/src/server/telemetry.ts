import { appendFileSync, mkdirSync } from 'node:fs'

import { env } from '#/env'

export type Trace = {
  traceId: string
  parentSpanId: string
}

export type Span = {
  traceId: string
  spanId: string
  parentSpanId: string
}

const hex = (length: number) =>
  crypto.randomUUID().replaceAll('-', '').slice(0, length)

export const parseTraceparent = (incoming?: string | null): Trace | null => {
  const parts = (incoming ?? '').split('-')
  if (
    parts.length !== 4 ||
    parts[0] !== '00' ||
    parts[1].length !== 32 ||
    parts[2].length !== 16
  ) {
    return null
  }
  return { traceId: parts[1], parentSpanId: parts[2] }
}

export const createTrace = (incoming?: string | null): Trace =>
  parseTraceparent(incoming) ?? { traceId: hex(32), parentSpanId: '' }

export const createSpan = (trace: Trace): Span => ({
  traceId: trace.traceId,
  spanId: hex(16),
  parentSpanId: trace.parentSpanId,
})

export const traceparent = (span: Span) =>
  `00-${span.traceId}-${span.spanId}-01`

export const logEvent = (
  event: string,
  span: Span,
  fields: Record<string, unknown> = {},
) => {
  const record = {
    timestamp: new Date().toISOString(),
    event,
    trace_id: span.traceId,
    span_id: span.spanId,
    parent_span_id: span.parentSpanId,
    ...fields,
  }

  try {
    mkdirSync('logs', { recursive: true })
    appendFileSync('logs/trace.jsonl', `${JSON.stringify(record)}\n`)
  } catch {
    // log lokal gagal tidak boleh menggagalkan job
  }

  const endpoint = env.OTEL_EXPORTER_OTLP_ENDPOINT
  if (endpoint) {
    void fetch(`${endpoint}/v1/traces`, {
      method: 'POST',
      headers: { 'content-type': 'application/json' },
      body: JSON.stringify({
        resourceSpans: [
          {
            resource: {
              attributes: [
                { key: 'service.name', value: { stringValue: 'clip-ai-web' } },
              ],
            },
            scopeSpans: [
              {
                spans: [
                  {
                    traceId: span.traceId,
                    spanId: span.spanId,
                    parentSpanId: span.parentSpanId,
                    name: event,
                    startTimeUnixNano: String(Date.now() * 1_000_000),
                    endTimeUnixNano: String(Date.now() * 1_000_000),
                    status: { code: 1 },
                  },
                ],
              },
            ],
          },
        ],
      }),
      signal: AbortSignal.timeout(1000),
    }).catch(() => {})
  }

  return record
}
