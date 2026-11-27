import { createFileRoute, Navigate, Outlet } from '@tanstack/react-router'

import { AnimeLoading } from '#/components/anime-states'
import { authClient } from '#/lib/auth-client'

const ProtectedLayout = () => {
  const { data: session, isPending } = authClient.useSession()

  if (isPending) return <AnimeLoading />
  if (!session?.user) return <Navigate to="/login" replace />

  return <Outlet />
}

export const Route = createFileRoute('/_protected')({
  component: ProtectedLayout,
})
