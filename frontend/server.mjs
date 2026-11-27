import { resolve } from 'node:path'

import { serve } from 'srvx/node'
import { staticMiddleware } from 'srvx/static'

import serverEntry from './dist/server/server.js'

const clientDir = resolve(import.meta.dirname, 'dist/client')
const port = Number(process.env.PORT ?? 3000)
const hostname = process.env.HOST ?? '0.0.0.0'

const hashedAssets = staticMiddleware({
  dir: clientDir,
  maxAge: 31536000,
  immutable: true,
})

const publicFiles = staticMiddleware({ dir: clientDir })

const staticFiles = (request, next) =>
  new URL(request.url).pathname.startsWith('/assets/')
    ? hashedAssets(request, next)
    : publicFiles(request, next)

const health = (request, next) =>
  new URL(request.url).pathname === '/health/live'
    ? new Response('ok', {
        headers: { 'content-type': 'text/plain; charset=utf-8' },
      })
    : next()

serve({
  fetch: serverEntry.fetch,
  middleware: [health, staticFiles],
  port,
  hostname,
  gracefulShutdown: true,
})
