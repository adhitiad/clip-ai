import { createFileRoute } from '@tanstack/react-router'

import { auth } from '#/lib/auth'

type RequestWithIp = Request & { ip?: string }

// srvx exposes the peer address as `request.ip`; Better Auth reads
// `x-forwarded-for`. Overwrite any client-supplied value so the peer is authoritative.
// Mutate headers in place: cloning a srvx Request breaks its native private state.
const withClientIp = (request: Request): Request => {
  const peerIp = (request as RequestWithIp).ip
  if (peerIp) request.headers.set('x-forwarded-for', peerIp)
  return request
}

export const Route = createFileRoute('/api/auth/$')({
  server: {
    handlers: {
      GET: ({ request }) => auth.handler(withClientIp(request)),
      POST: ({ request }) => auth.handler(withClientIp(request)),
    },
  },
})
