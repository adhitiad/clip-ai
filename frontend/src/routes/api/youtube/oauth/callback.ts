import { createFileRoute } from '@tanstack/react-router'

import { env } from '#/env'
import { saveEncryptedToken } from '#/lib/youtube-token'

export const Route = createFileRoute('/api/youtube/oauth/callback')({
  server: {
    handlers: {
      GET: async ({ request }) => {
        const url = new URL(request.url)
        const code = url.searchParams.get('code')
        const error = url.searchParams.get('error')

        if (error) {
          return Response.json({ status: 'error', error }, { status: 400 })
        }
        if (!code) {
          return Response.json(
            { status: 'error', error: 'code tidak ada' },
            { status: 400 },
          )
        }
        if (
          !env.YOUTUBE_OAUTH_CLIENT_ID ||
          !env.YOUTUBE_OAUTH_CLIENT_SECRET ||
          !env.YOUTUBE_OAUTH_REDIRECT_URI ||
          !env.YOUTUBE_TOKEN_ENCRYPTION_KEY
        ) {
          return Response.json(
            { error: 'OAuth belum dikonfigurasi' },
            { status: 503 },
          )
        }

        try {
          const response = await fetch('https://oauth2.googleapis.com/token', {
            method: 'POST',
            headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
            body: new URLSearchParams({
              code,
              client_id: env.YOUTUBE_OAUTH_CLIENT_ID,
              client_secret: env.YOUTUBE_OAUTH_CLIENT_SECRET,
              redirect_uri: env.YOUTUBE_OAUTH_REDIRECT_URI,
              grant_type: 'authorization_code',
            }),
            signal: AbortSignal.timeout(15000),
          })
          if (!response.ok) {
            return Response.json(
              { status: 'error', error: 'token exchange gagal' },
              { status: 400 },
            )
          }
          const data = (await response.json()) as {
            access_token: string
            refresh_token?: string
            expires_in?: number
            scope?: string
          }
          await saveEncryptedToken(
            {
              access_token: data.access_token,
              refresh_token: data.refresh_token,
              expiry_date: data.expires_in
                ? Date.now() + data.expires_in * 1000
                : undefined,
              scope: data.scope,
              updated_at: new Date().toISOString(),
            },
            env.YOUTUBE_TOKEN_ENCRYPTION_KEY,
          )
          // Response TIDAK mengandung token.
          return Response.json({
            status: 'ok',
            message: 'Token YouTube tersimpan terenkripsi.',
          })
        } catch {
          return Response.json(
            { status: 'error', error: 'token exchange gagal' },
            { status: 500 },
          )
        }
      },
    },
  },
})
