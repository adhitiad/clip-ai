import { test } from '@playwright/test'

test('debug provider requests', async ({ page }) => {
  page.on('request', (r) => {
    if (r.url().includes('_serverFn')) {
      const seg = new URL(r.url()).pathname.split('/').pop() ?? ''
      console.log(
        'FN',
        r.method(),
        Buffer.from(seg, 'base64').toString().slice(0, 160),
        'URL',
        r.url().slice(0, 260),
      )
    }
  })
  await page.goto('/landing', { waitUntil: 'networkidle' })
  await page.waitForTimeout(3500)
  console.log(
    'BODY',
    (await page.locator('body').innerText())
      .replace(/\n/g, ' | ')
      .slice(0, 800),
  )
})
