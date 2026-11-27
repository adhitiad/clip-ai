import AxeBuilder from '@axe-core/playwright'
import { expect, test } from '@playwright/test'
import type { Page, TestInfo } from '@playwright/test'

import {
  mockApiGets,
  mockSession,
  platformCatalog,
  providerCatalog,
} from '../tests/helpers/server-fn'

const publicRoutes = [
  '/landing',
  '/login',
  '/about',
  '/contact',
  '/privacy',
  '/tos',
]
const protectedRoutes = [
  '/',
  '/protected',
  '/dashboard',
  '/history',
  '/niche',
  '/shorts',
  '/tools',
  '/backend',
]

const fixtures: Record<string, unknown> = {
  '/dashboard/health': {
    status: 'success',
    health: { database: { ok: true }, rabbitmq: { ok: true } },
  },
  '/dashboard/overview': {
    status: 'success',
    clips: { total: 0, average_score: 0, max_score: 0 },
    recent: [],
  },
  '/dashboard/history': { status: 'success', total: 0, items: [] },
  '/dashboard/stats': { status: 'success', daily: {}, total: 0, peak: 0 },
  '/ops/queue': {
    status: 'success',
    broker: { ok: true },
    counts: { SUCCESS: 0 },
    dead_letter_queue: 'shorts-render-dlq',
  },
  '/ops/tasks': [],
  '/niche/trending': { status: 'success', trending: [] },
  '/niche/suggest': { status: 'success', niches_recommended: [] },
  '/niche/find-videos': { status: 'success', videos: [] },
  '/revenue/summary': {
    status: 'success',
    total_available: 0,
    currency: 'USD',
    platforms: [],
  },
  '/revenue/advice': {
    status: 'success',
    provider: 'openrouter',
    model: 'free',
    recommendations: [],
    generated_at: '2026-11-25T00:00:00+00:00',
    note: '',
  },
  '/tools/providers': providerCatalog,
  '/tools/platforms': platformCatalog,
  '/tools/model-status': {
    status: 'success',
    model: { trained: false, enabled: false, confidence_mode: 'rule_based' },
  },
}

const audit = async (page: Page, testInfo: TestInfo, path: string) => {
  await page.goto(path)
  await expect(page.locator('body')).toBeVisible()
  await page.addStyleTag({
    content:
      '*, *::before, *::after { animation-duration: 0s !important; animation-delay: 0s !important; transition-duration: 0s !important; }',
  })
  await page.evaluate(
    () =>
      new Promise<void>((resolve) => {
        void document.fonts.ready.then(() =>
          requestAnimationFrame(() => resolve()),
        )
      }),
  )

  const slug = path === '/' ? 'root' : path.slice(1).replaceAll('/', '-')
  const screenshot = await page.screenshot({
    fullPage: true,
    animations: 'disabled',
  })
  expect(screenshot.length).toBeGreaterThan(0)
  await testInfo.attach(`screenshot-${slug}`, {
    body: screenshot,
    contentType: 'image/png',
  })

  const results = await new AxeBuilder({ page })
    .withTags(['wcag2a', 'wcag2aa'])
    .analyze()
  const blocking = results.violations.filter(
    (violation) =>
      violation.impact === 'critical' || violation.impact === 'serious',
  )
  await testInfo.attach('axe-violations', {
    body: JSON.stringify(blocking, null, 2),
    contentType: 'application/json',
  })
  expect(
    blocking.map((violation) => `${violation.id} (${violation.nodes.length})`),
  ).toEqual([])
}

for (const path of publicRoutes) {
  test(`@a11y publik ${path}`, async ({ page }, testInfo) => {
    await audit(page, testInfo, path)
  })
}

for (const path of protectedRoutes) {
  test(`@a11y protected ${path}`, async ({ page }, testInfo) => {
    await mockSession(page)
    await mockApiGets(page, fixtures)
    await audit(page, testInfo, path)
  })
}
