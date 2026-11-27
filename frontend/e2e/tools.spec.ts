import { expect, test } from '@playwright/test'

import {
  mockApiGet,
  mockProviders,
  mockSession,
} from '../tests/helpers/server-fn'

test('alat menampilkan status model rule-based', async ({ page }) => {
  await mockSession(page)
  await mockProviders(page)
  await mockApiGet(page, '/tools/model-status', {
    status: 'success',
    model: { trained: false, enabled: false, confidence_mode: 'rule_based' },
    message: 'Scoring viral sepenuhnya rule-based.',
  })

  await page.goto('/tools')
  await expect(page.getByRole('heading', { name: 'Alat' })).toBeVisible()
  await expect(page.getByText('Nonaktif')).toBeVisible()
  await expect(page.getByText('rule_based')).toBeVisible()
  await expect(
    page.getByText('Scoring viral sepenuhnya rule-based.'),
  ).toBeVisible()
})
