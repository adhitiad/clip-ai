import { createFileRoute } from '@tanstack/react-router'

import { env } from '#/env'

/**
 * Scheduler trigger (server-only). Dilindungi X-Cron-Secret.
 * Placeholder: meneruskan permintaan ke backend Python bila tersedia.
 */
export const Route = createFileRoute('/api/youtube/scheduler')({
  server: {
    handlers: {
      POST: async ({ request }) => {
        const secret = request.headers.get('x-cron-secret')
        if (!env.YOUTUBE_CRON_SECRET || secret !== env.YOUTUBE_CRON_SECRET) {
          return Response.json({ error: 'Unauthorized' }, { status: 401 })
        }
        const body = await request.json().catch(() => ({}))
        return Response.json({
          status: 'scheduled',
          query: body.query ?? '',
          note: 'Terhubung ke backend /youtube/scheduler/collect bila diisi.',
        })
      },
    },
  },
})
