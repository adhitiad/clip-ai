import { expect, test } from '@playwright/test'

import { mockProviders, mockSession } from '../tests/helpers/server-fn'

const routes = [
  { path: '/landing', heading: /Dari riset/ },
  { path: '/shorts', heading: /shorts/i },
  { path: '/niche', heading: 'Penemuan' },
  { path: '/history', heading: 'Riwayat clip' },
  { path: '/dashboard', heading: 'Dashboard' },
  { path: '/tools', heading: 'Alat' },
]

for (const route of routes) {
  test(`${route.path} merender judul dan shell`, async ({ page }) => {
    await mockProviders(page)
    await mockSession(page)
    await page.goto(route.path, { waitUntil: 'networkidle' })
    await expect(
      page.getByRole('heading', { name: route.heading }),
    ).toBeVisible()
    await expect(page.getByText(/clip ai/i).first()).toBeVisible()
  })
}

test('sidebar menuju rute yang ada', async ({ page }) => {
  await mockProviders(page)
  await mockSession(page)
  await page.goto('/', { waitUntil: 'networkidle' })
  await page
    .getByRole('navigation', { name: 'Navigasi utama' })
    .first()
    .getByRole('link', { name: 'Dashboard' })
    .click()
  await expect(page).toHaveURL(/\/dashboard$/)
  await expect(page.getByRole('heading', { name: 'Dashboard' })).toBeVisible()
})

test('avatar publik muncul saat login dan berisi Dashboard + Keluar', async ({
  page,
}) => {
  await mockProviders(page)
  await mockSession(page)
  await page.goto('/landing', { waitUntil: 'networkidle' })

  const menu = page.getByRole('button', { name: 'Menu akun' })
  await expect(menu).toBeVisible()
  await menu.click()
  await expect(page.getByRole('menuitem', { name: /Dashboard/ })).toBeVisible()
  await expect(page.getByRole('menuitem', { name: /Keluar/ })).toBeVisible()
})

test('tombol Masuk tampil di navbar publik saat belum login', async ({
  page,
}) => {
  await page.goto('/landing', { waitUntil: 'networkidle' })
  const nav = page.getByRole('navigation', { name: 'Navigasi publik' })
  await expect(nav.getByRole('link', { name: 'Masuk' })).toBeVisible()
  await expect(page.getByRole('button', { name: 'Menu akun' })).toHaveCount(0)
})

test('tombol simpan provider berubah status', async ({ page }) => {
  await mockProviders(page)
  await mockSession(page)
  await page.goto('/', { waitUntil: 'networkidle' })
  const button = page.getByRole('button', { name: 'Simpan' }).first()
  await expect(button).toBeVisible()
  await button.click()
  await expect(button).toHaveAttribute('aria-pressed', 'true')
})
