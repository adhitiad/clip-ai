import { createFileRoute, redirect } from '@tanstack/react-router'

import { env } from '#/env'

const SCOPES = [
  'https://www.googleapis.com/auth/youtube.readonly',
  'https://www.googleapis.com/auth/yt-analytics.readonly',
  'https://www.googleapis.com/auth/yt-analytics-monetary.readonly',
].join(' ')

export const Route = createFileRoute('/api/youtube/oauth/start')({
  server: {
    handlers: {
      GET: () => {
        if (!env.YOUTUBE_OAUTH_CLIENT_ID || !env.YOUTUBE_OAUTH_REDIRECT_URI) {
          return Response.json(
            { error: 'OAuth YouTube belum dikonfigurasi' },
            { status: 503 },
          )
        }
        const url = new URL('https://accounts.google.com/o/oauth2/v2/auth')
        url.searchParams.set('client_id', env.YOUTUBE_OAUTH_CLIENT_ID)
        url.searchParams.set('redirect_uri', env.YOUTUBE_OAUTH_REDIRECT_URI)
        url.searchParams.set('response_type', 'code')
        url.searchParams.set('scope', SCOPES)
        url.searchParams.set('access_type', 'offline')
        url.searchParams.set('prompt', 'consent')
        url.searchParams.set('state', crypto.randomUUID())
        throw redirect({ href: url.toString() })
      },
    },
  },
})
