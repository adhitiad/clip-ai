import { describe, expect, it } from 'vitest'

import { decryptToken, encryptToken } from './youtube-token'

const SECRET = 'a-very-long-test-encryption-key-0123456789'

describe('youtube token encryption', () => {
  it('mengenkripsi dan mendekripsi token', () => {
    const token = {
      access_token: 'ya29.secret-access',
      refresh_token: 'secret-refresh',
      expiry_date: 1234567890,
      scope: 'youtube.readonly',
      updated_at: '2026-11-24T00:00:00.000Z',
    }
    const encrypted = encryptToken(token, SECRET)
    expect(encrypted).not.toContain('secret-access')
    expect(encrypted.split('.')).toHaveLength(3)
    expect(decryptToken(encrypted, SECRET)).toEqual(token)
  })

  it('menolak kunci pendek & format rusak', () => {
    expect(() =>
      encryptToken({ access_token: 'x', updated_at: '' }, 'short'),
    ).toThrow()
    expect(() => decryptToken('rusak', SECRET)).toThrow()
  })
})
