import {
  HeadContent,
  Scripts,
  createRootRouteWithContext,
} from '@tanstack/react-router'
import { TanStackRouterDevtoolsPanel } from '@tanstack/react-router-devtools'
import { TanStackDevtools } from '@tanstack/react-devtools'

import TanStackQueryDevtools from '../integrations/tanstack-query/devtools'

import { getLocale } from '#/paraglide/runtime'
import { env } from '#/env'

import appCss from '../styles.css?url'

import type { QueryClient } from '@tanstack/react-query'

interface MyRouterContext {
  queryClient: QueryClient
}

const site = (env.VITE_SITE_URL ?? 'http://localhost:3000/').replace(/\/$/, '')
const description =
  'Dari riset sampai klip siap unggah. Studio short-form pribadi dengan agent LangChain.'

const RootDocument = ({ children }: { children: React.ReactNode }) => {
  return (
    <html lang={getLocale()} className="dark">
      <head>
        <HeadContent />
      </head>
      <body className="school-night">
        {children}
        <TanStackDevtools
          config={{
            position: 'bottom-right',
          }}
          plugins={[
            {
              name: 'Tanstack Router',
              render: <TanStackRouterDevtoolsPanel />,
            },
            TanStackQueryDevtools,
          ]}
        />
        <Scripts />
      </body>
    </html>
  )
}

export const Route = createRootRouteWithContext<MyRouterContext>()({
  beforeLoad: async () => {
    // Other redirect strategies are possible; see
    // https://github.com/TanStack/router/tree/main/examples/react/i18n-paraglide#offline-redirect
    if (typeof document !== 'undefined') {
      document.documentElement.setAttribute('lang', getLocale())
    }
  },

  head: () => ({
    meta: [
      {
        charSet: 'utf-8',
      },
      {
        name: 'viewport',
        content: 'width=device-width, initial-scale=1',
      },
      {
        title: 'Clip AI',
      },
      {
        name: 'description',
        content: description,
      },
      {
        property: 'og:title',
        content: 'Clip AI',
      },
      {
        property: 'og:description',
        content: description,
      },
      {
        property: 'og:image',
        content: `${site}/assets/og-image.png`,
      },
      {
        property: 'og:url',
        content: site,
      },
      {
        property: 'og:type',
        content: 'website',
      },
      {
        name: 'twitter:card',
        content: 'summary_large_image',
      },
      {
        name: 'twitter:title',
        content: 'Clip AI',
      },
      {
        name: 'twitter:description',
        content: description,
      },
      {
        name: 'twitter:image',
        content: `${site}/assets/og-image.png`,
      },
      {
        name: 'twitter:url',
        content: site,
      },
      {
        name: 'theme-color',
        content: '#07111f',
      },
    ],
    links: [
      {
        rel: 'icon',
        href: '/assets/favicon.ico',
        type: 'image/x-icon',
      },
      {
        rel: 'icon',
        href: '/assets/pirate-emblem.svg',
        type: 'image/svg+xml',
      },
      {
        rel: 'apple-touch-icon',
        href: '/assets/og-image.png',
      },
      {
        rel: 'preconnect',
        href: 'https://fonts.googleapis.com',
      },
      {
        rel: 'preconnect',
        href: 'https://fonts.gstatic.com',
        crossOrigin: 'anonymous',
      },
      {
        rel: 'stylesheet',
        href: appCss,
      },
    ],
  }),
  shellComponent: RootDocument,
})
