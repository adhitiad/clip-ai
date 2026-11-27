import { createEnv } from '@t3-oss/env-core'
import { z } from 'zod'

const runtimeEnv =
  typeof process === 'undefined'
    ? import.meta.env
    : { ...import.meta.env, ...process.env }

export const env = createEnv({
  server: {
    SERVER_URL: z.url().optional(),
    RABBITMQ_URL: z.string().optional(),
    OTEL_EXPORTER_OTLP_ENDPOINT: z.url().optional(),
    GOOGLE_CLIENT_ID: z.string().optional(),
    GOOGLE_CLIENT_SECRET: z.string().optional(),
    GOOGLE_OAUTH_CLIENT_ID: z.string().optional(),
    AUTH_BRIDGE_TOKEN: z.string().optional(),
    BETTER_AUTH_URL: z.url().optional(),
    BETTER_AUTH_SECRET: z.string().min(32).optional(),
    BETTER_AUTH_TRUSTED_ORIGINS: z.string().optional(),
    YOUTUBE_DATA_API_KEY: z.string().optional(),
    YOUTUBE_CRON_SECRET: z.string().optional(),
    YOUTUBE_OAUTH_CLIENT_ID: z.string().optional(),
    YOUTUBE_OAUTH_CLIENT_SECRET: z.string().optional(),
    YOUTUBE_OAUTH_REDIRECT_URI: z.url().optional(),
    YOUTUBE_TOKEN_ENCRYPTION_KEY: z.string().min(32).optional(),
  },

  /**
   * The prefix that client-side variables must have. This is enforced both at
   * a type-level and at runtime.
   */
  clientPrefix: 'VITE_',

  client: {
    VITE_APP_TITLE: z.string().min(1).optional(),
    VITE_SITE_URL: z.url().optional(),
  },

  /**
   * What object holds the environment variables at runtime. This is usually
   * `process.env` or `import.meta.env`.
   */
  runtimeEnv,

  /**
   * By default, this library will feed the environment variables directly to
   * the Zod validator.
   *
   * This means that if you have an empty string for a value that is supposed
   * to be a number (e.g. `PORT=` in a ".env" file), Zod will incorrectly flag
   * it as a type mismatch violation. Additionally, if you have an empty string
   * for a value that is supposed to be a string with a default value (e.g.
   * `DOMAIN=` in an ".env" file), the default value will never be applied.
   *
   * In order to solve these issues, we recommend that all new projects
   * explicitly specify this option as true.
   */
  emptyStringAsUndefined: true,
})
