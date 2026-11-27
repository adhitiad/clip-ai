import { expect, test } from '@playwright/test'

import {
  mockApiGet,
  mockProviders,
  mockSession,
  platformCatalog,
  shortsBrief,
  stubServerFn,
} from '../tests/helpers/server-fn'

const stubCatalogs = async (page: import('@playwright/test').Page) => {
  await mockProviders(page)
  await mockSession(page)
  await mockApiGet(page, '/tools/platforms', platformCatalog)
}

test('/shorts membuat brief dari UI', async ({ page }) => {
  await stubCatalogs(page)
  await page.goto('/shorts', { waitUntil: 'networkidle' })
  await stubServerFn(page, 'createShorts', {
    status: 'brief',
    brief: shortsBrief,
  })

  await page.getByRole('textbox', { name: 'Topik' }).fill('tips editing video')
  await page.getByRole('button', { name: /Buat brief/ }).click()

  await expect(page.getByRole('heading', { name: 'Brief' })).toBeVisible()
  await expect(page.getByText('Edit Cepat')).toBeVisible()
  await expect(page.getByText('Jangan skip!')).toBeVisible()
  await expect(page.getByText(/#shorts/)).toBeVisible()
  await expect(page.getByText(/#editing/)).toBeVisible()
})

test('/shorts mengantre render dan polling status task', async ({ page }) => {
  await stubCatalogs(page)
  await page.goto('/shorts', { waitUntil: 'networkidle' })
  await stubServerFn(page, 'createShorts', {
    status: 'processing',
    task_id: 'task-e2e',
    request_id: 'req-e2e',
    brief: shortsBrief,
  })
  await stubServerFn(page, 'getTask', () => ({
    task_id: 'task-e2e',
    status: 'SUCCESS',
    progress: null,
    error: null,
  }))

  await page.getByRole('textbox', { name: 'Topik' }).fill('tips editing video')
  await page
    .getByRole('textbox', { name: /URL video sumber/ })
    .fill('https://youtube.com/watch?v=demo')
  await page.getByRole('checkbox', { name: /Render video/ }).check()
  await page.getByRole('button', { name: /Buat brief/ }).click()

  await expect(page.getByText('task-e2e')).toBeVisible()
  await expect(page.getByText('SUCCESS', { exact: true })).toBeVisible({
    timeout: 12000,
  })
  await expect(page.getByText(/^Error:/)).toHaveCount(0)
})

test('/shorts menampilkan progres render', async ({ page }) => {
  await stubCatalogs(page)
  await page.goto('/shorts', { waitUntil: 'networkidle' })
  await stubServerFn(page, 'createShorts', {
    status: 'processing',
    task_id: 'task-progress',
    brief: shortsBrief,
  })
  await stubServerFn(page, 'getTask', () => ({
    task_id: 'task-progress',
    status: 'PROGRESS',
    progress: { current: 2, total: 3, percent: 67 },
    error: null,
  }))

  await page.getByRole('textbox', { name: 'Topik' }).fill('tips editing video')
  await page
    .getByRole('textbox', { name: /URL video sumber/ })
    .fill('https://youtube.com/watch?v=demo')
  await page.getByRole('checkbox', { name: /Render video/ }).check()
  await page.getByRole('button', { name: /Buat brief/ }).click()

  const progress = page.getByRole('progressbar', { name: 'Progres render' })
  await expect(progress).toBeVisible({ timeout: 12000 })
  await expect(progress).toHaveAttribute('aria-valuenow', '67')
  await expect(page.getByText('2 / 3', { exact: false })).toBeVisible()
})
