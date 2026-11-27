import axios from 'axios'
import { createServerFn } from '@tanstack/react-start'
import { getRequest } from '@tanstack/react-start/server'

import { auth } from '#/lib/auth'
import { env } from '#/env'
import { apiGetDynamicSchema, apiGetSchema } from '#/validation/api'
import type { ApiPath } from '#/validation/api'

type JsonValue =
  string | number | boolean | null | JsonValue[] | { [key: string]: JsonValue }

type GetData = {
  path: string
  query?: Record<string, string>
}

const BACKEND_URL = env.SERVER_URL ?? 'http://127.0.0.1:8000'

const backendHttp = axios.create({
  adapter: 'fetch',
  baseURL: BACKEND_URL,
  timeout: 15000,
  paramsSerializer: (params) =>
    Object.entries(params)
      .filter(([, value]) => value !== undefined && value !== null)
      .map(
        ([key, value]) =>
          `${encodeURIComponent(key)}=${encodeURIComponent(String(value))}`,
      )
      .join('&'),
})

const bridgeHttp = axios.create({
  adapter: 'fetch',
  baseURL: BACKEND_URL,
  timeout: 10000,
})

const errorMessage = (error: unknown, fallback: string) => {
  if (axios.isAxiosError(error)) {
    const detail = error.response?.data?.detail
    if (typeof detail === 'string') return detail
  }
  return fallback
}

const backendToken = async (headers: Headers) => {
  const session = await auth.api.getSession({ headers })
  if (!session?.user.email) {
    throw new Error('Silakan login dengan Google dulu.')
  }

  try {
    const response = await bridgeHttp.post<{ access_token: string }>(
      '/auth/bridge',
      {
        email: session.user.email,
        bridge_token: env.AUTH_BRIDGE_TOKEN,
      },
    )
    return response.data.access_token
  } catch (error) {
    throw new Error(errorMessage(error, 'Gagal membuat token backend.'))
  }
}

const getFromBackend = async (data: GetData) => {
  const token = await backendToken(getRequest().headers)
  const headers: Record<string, string> = {
    Authorization: `Bearer ${token}`,
  }
  if (data.path.startsWith('/youtube/scheduler')) {
    headers['x-cron-secret'] = env.YOUTUBE_CRON_SECRET ?? ''
  }

  try {
    const response = await backendHttp.get<JsonValue>(data.path, {
      params: data.query,
      headers,
    })
    return response.data
  } catch (error) {
    throw new Error(errorMessage(error, 'Permintaan backend gagal.'))
  }
}

export const apiGet = createServerFn({ method: 'GET' })
  .validator(apiGetSchema)
  .handler(async ({ data }) => getFromBackend(data))

export const apiGetDynamic = createServerFn({ method: 'GET' })
  .validator(apiGetDynamicSchema)
  .handler(async ({ data }) => getFromBackend(data))

export const apiPath = (path: ApiPath, query?: Record<string, string>) => ({
  path,
  query,
})
