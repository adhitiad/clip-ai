import { z } from 'zod'

/** Google-only auth: tidak ada email/password di aplikasi ini. */
export const googleSignInSchema = z.object({
  idToken: z.string().min(1, 'ID token wajib diisi'),
})

export type GoogleSignInInput = z.infer<typeof googleSignInSchema>
