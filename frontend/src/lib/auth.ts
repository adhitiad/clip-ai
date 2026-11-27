import { betterAuth } from 'better-auth'
import { tanstackStartCookies } from 'better-auth/tanstack-start'

import { env } from '#/env'

const baseURL =
  env.BETTER_AUTH_URL ?? env.VITE_SITE_URL ?? 'http://localhost:3000'
const extraOrigins = (env.BETTER_AUTH_TRUSTED_ORIGINS ?? '')
  .split(',')
  .map((origin) => origin.trim())
  .filter(Boolean)

/** Google-only auth: tanpa email/password, satu owner. */
export const auth = betterAuth({
  appName: 'Clip AI',
  baseURL,
  secret: env.BETTER_AUTH_SECRET,
  socialProviders: {
    google: {
      clientId: env.GOOGLE_CLIENT_ID ?? '',
      clientSecret: env.GOOGLE_CLIENT_SECRET ?? '',
    },
  },
  plugins: [tanstackStartCookies()],
  trustedOrigins: [baseURL, ...extraOrigins],
  rateLimit: {
    enabled: true,
    storage: 'memory',
    window: 10,
    max: 100,
  },
  session: {
    expiresIn: 60 * 60 * 24 * 7,
    updateAge: 60 * 60 * 24,
    cookieCache: {
      enabled: true,
      maxAge: 60 * 5,
      strategy: 'jwe',
    },
  },
  account: {
    encryptOAuthTokens: true,
    storeStateStrategy: 'cookie',
  },
  advanced: {
    ipAddress: {
      ipAddressHeaders: ['x-forwarded-for', 'x-real-ip'],
    },
  },
})
