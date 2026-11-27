import { expect, test } from '@playwright/test'

const pages = [
  { path: '/about', heading: 'Tentang Clip AI' },
  { path: '/tos', heading: 'Ketentuan penggunaan' },
  { path: '/privacy', heading: 'Kebijakan privasi' },
  { path: '/contact', heading: 'Kontak' },
]

for (const page of pages) {
  test(`${page.path} menampilkan judul`, async ({ page: browser }) => {
    await browser.goto(page.path)
    await expect(
      browser.getByRole('heading', { name: page.heading }),
    ).toBeVisible()
  })
}

test('meta SEO dan favicon tersedia', async ({ page }) => {
  await page.goto('/landing')
  expect(
    await page.locator('meta[name="description"]').getAttribute('content'),
  ).toBeTruthy()
  expect(
    await page.locator('meta[property="og:title"]').getAttribute('content'),
  ).toBe('Clip AI')
  expect(
    await page.locator('meta[name="twitter:card"]').getAttribute('content'),
  ).toBe('summary_large_image')
  expect(await page.locator('link[rel="icon"]').count()).toBeGreaterThan(0)
})

test('Better Auth health endpoint aktif', async ({ request }) => {
  const response = await request.get('/api/auth/ok')
  expect(response.ok()).toBeTruthy()
  const body = (await response.json().catch(() => ({}))) as Record<
    string,
    unknown
  >
  expect(body.status === 'ok' || body.ok === true).toBeTruthy()
})

test('robots dan sitemap tersedia', async ({ request }) => {
  const robots = await request.get('/robots.txt')
  expect(robots.ok()).toBeTruthy()
  expect(await robots.text()).toContain('Disallow: /protected')

  const sitemap = await request.get('/sitemap.xml')
  expect(sitemap.ok()).toBeTruthy()
  expect(await sitemap.text()).toContain('/privacy')
})
