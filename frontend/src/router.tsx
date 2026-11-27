import { createRouter as createTanStackRouter } from '@tanstack/react-router'
import { routeTree } from './routeTree.gen'

import { setupRouterSsrQueryIntegration } from '@tanstack/react-router-ssr-query'

import {
  AnimeError,
  AnimeLoading,
  AnimeNotFound,
} from '#/components/anime-states'
import { getContext } from './integrations/tanstack-query/root-provider'

export const getRouter = () => {
  const context = getContext()

  const router = createTanStackRouter({
    routeTree,
    context,
    scrollRestoration: true,
    defaultPreload: 'intent',
    defaultPreloadStaleTime: 0,
    defaultPendingMs: 200,
    defaultPendingComponent: AnimeLoading,
    defaultNotFoundComponent: AnimeNotFound,
    defaultErrorComponent: AnimeError,
  })

  setupRouterSsrQueryIntegration({ router, queryClient: context.queryClient })

  return router
}

declare module '@tanstack/react-router' {
  interface Register {
    router: ReturnType<typeof getRouter>
  }
}
