import type { Page } from '@playwright/test'
import { toJSONAsync } from 'seroval'

export const providerCatalog = {
  status: 'success',
  providers: [
    {
      id: 'nvidia',
      name: 'NVIDIA NIM',
      kind: 'llm',
      free: true,
      models: ['nvidia/nemotron-3.5-super-vl-120b-a12b'],
    },
  ],
  tts: [],
  stt: [],
}

export const platformCatalog = {
  status: 'success',
  platforms: ['shorts', 'reels', 'tiktok'],
  default: 'shorts',
}

export const shortsBrief = {
  platform: 'shorts',
  topic: 'tips editing video',
  clips: [
    {
      start_time: 0,
      end_time: 15,
      hook: 'Jangan skip!',
      title: 'Edit Cepat',
      caption: 'Potong di beat',
      hashtags: ['#shorts', '#editing'],
    },
  ],
  style_notes: '',
}

type StubValue = unknown | (() => unknown)

type StubOptions = {
  /** Untuk server fn GET (apiGet), path ada di query `payload`, bukan body. */
  payloadIncludes?: string
}

const isServerFn = (url: URL) => url.pathname.includes('/_serverFn/')
const payloadOf = (url: URL) => url.searchParams.get('payload') ?? ''

/** GET memakai query `payload`; POST memakai body dengan skema seroval yang sama. */
const payloadFromRequest = (request: import('@playwright/test').Request) =>
  `${payloadOf(new URL(request.url()))} ${
    request.method() === 'GET' ? '' : (request.postData() ?? '')
  }`

/**
 * ID server fn sekarang berupa hash SHA-256, bukan nama export yang di-base64.
 * Karena itu stub dicocokkan dari kunci validator Zod di payload/body.
 */
const matchesExport = (payload: string, exportName: string) => {
  if (exportName === 'apiGet') return payload.includes('"path"')
  if (exportName === 'createShorts') return payload.includes('"topic"')
  if (exportName === 'getTask') return payload.includes('"taskId"')
  return true
}

/** Stub server fn TanStack Start: butuh header x-tss-serialized + tree seroval. */
export const stubServerFn = async (
  page: Page,
  exportName: string,
  value: StubValue,
  options: StubOptions = {},
) => {
  await page.route(isServerFn, async (route) => {
    const payload = payloadFromRequest(route.request())
    if (options.payloadIncludes) {
      if (!payload.includes(options.payloadIncludes)) return route.fallback()
    } else if (!matchesExport(payload, exportName)) {
      return route.fallback()
    }
    const result = typeof value === 'function' ? value() : value
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      headers: { 'x-tss-serialized': 'true' },
      body: JSON.stringify((await toJSONAsync({ result })).t),
    })
  })
}

export const mockApiGet = async (page: Page, path: string, value: unknown) =>
  stubServerFn(page, 'apiGet', value, { payloadIncludes: path })

export const mockApiGets = async (
  page: Page,
  values: Record<string, unknown>,
) => {
  await page.route(
    (url) => isServerFn(url) && payloadOf(url).includes('"path"'),
    async (route) => {
      const payload =
        new URL(route.request().url()).searchParams.get('payload') ?? ''
      const path = Object.keys(values).find((key) => payload.includes(key))
      const result = path ? values[path] : { status: 'success' }
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        headers: { 'x-tss-serialized': 'true' },
        body: JSON.stringify((await toJSONAsync({ result })).t),
      })
    },
  )
}

export const mockSession = async (page: Page) =>
  page.route('**/api/auth/get-session*', async (route) => {
    const now = new Date()
    const expires = new Date(now.getTime() + 3_600_000)
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({
        user: {
          id: '1',
          email: 'owner@example.com',
          name: 'Owner',
          image: null,
          emailVerified: true,
          createdAt: now.toISOString(),
          updatedAt: now.toISOString(),
        },
        session: {
          id: 'session-1',
          userId: '1',
          token: 'mock-token',
          expiresAt: expires.toISOString(),
          createdAt: now.toISOString(),
          updatedAt: now.toISOString(),
        },
      }),
    })
  })

export const mockProviders = async (page: Page) =>
  mockApiGet(page, '/tools/providers', providerCatalog)
