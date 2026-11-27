/**
 * Enkripsi token YouTube (AES-256-GCM) + penyimpanan lokal terenkripsi.
 *
 * - Kunci: YOUTUBE_TOKEN_ENCRYPTION_KEY (32+ karakter) dari env server.
 * - Token TIDAK pernah dikembalikan ke client atau dicatat di log.
 * - File disimpan di frontend/.data/youtube_tokens.json (gitignored).
 */

import {
  createCipheriv,
  createDecipheriv,
  createHash,
  randomBytes,
} from 'node:crypto'
import { mkdir, readFile, writeFile } from 'node:fs/promises'
import { dirname, join } from 'node:path'

const DATA_FILE = join(process.cwd(), '.data', 'youtube_tokens.json')

export type StoredToken = {
  access_token: string
  refresh_token?: string
  expiry_date?: number
  scope?: string
  updated_at: string
}

export function deriveKey(secret: string): Buffer {
  if (!secret || secret.length < 32) {
    throw new Error('YOUTUBE_TOKEN_ENCRYPTION_KEY harus minimal 32 karakter')
  }
  // sha256 menghasilkan 32 byte untuk AES-256
  return createHash('sha256').update(secret).digest()
}

export function encryptToken(token: StoredToken, secret: string): string {
  const iv = randomBytes(12)
  const cipher = createCipheriv('aes-256-gcm', deriveKey(secret), iv)
  const payload = Buffer.from(JSON.stringify(token), 'utf8')
  const encrypted = Buffer.concat([cipher.update(payload), cipher.final()])
  const tag = cipher.getAuthTag()
  return [iv, tag, encrypted].map((b) => b.toString('base64')).join('.')
}

export function decryptToken(encrypted: string, secret: string): StoredToken {
  const [ivPart, tagPart, dataPart] = encrypted.split('.')
  if (!ivPart || !tagPart || !dataPart) {
    throw new Error('Format token terenkripsi tidak valid')
  }
  const decipher = createDecipheriv(
    'aes-256-gcm',
    deriveKey(secret),
    Buffer.from(ivPart, 'base64'),
  )
  decipher.setAuthTag(Buffer.from(tagPart, 'base64'))
  const plain = Buffer.concat([
    decipher.update(Buffer.from(dataPart, 'base64')),
    decipher.final(),
  ])
  return JSON.parse(plain.toString('utf8')) as StoredToken
}

export async function saveEncryptedToken(token: StoredToken, secret: string) {
  await mkdir(dirname(DATA_FILE), { recursive: true })
  const payload = {
    version: 1,
    encrypted: encryptToken(token, secret),
  }
  await writeFile(DATA_FILE, JSON.stringify(payload), {
    encoding: 'utf8',
    mode: 0o600,
  })
}

export async function readEncryptedToken(
  secret: string,
): Promise<StoredToken | null> {
  try {
    const raw = await readFile(DATA_FILE, 'utf8')
    const payload = JSON.parse(raw) as { encrypted?: string }
    if (!payload.encrypted) return null
    return decryptToken(payload.encrypted, secret)
  } catch {
    return null
  }
}
