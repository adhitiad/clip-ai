import { useState } from 'react'

import { createFileRoute } from '@tanstack/react-router'

import { authClient } from '#/lib/auth-client'
import { Button } from '#/components/ui/button'
import { ClapperboardIcon } from 'lucide-react'
import { PublicFooter, PublicNav } from '#/components/public-page'

const Login = () => {
  const [busy, setBusy] = useState(false)
  const [message, setMessage] = useState('')

  const signIn = async () => {
    setBusy(true)
    setMessage('')
    try {
      await authClient.signIn.social({
        provider: 'google',
        callbackURL: '/protected',
      })
    } catch {
      setMessage('Gagal menghubungkan Google. Coba lagi.')
      setBusy(false)
    }
  }

  return (
    <main className="page-wrap flex min-h-screen flex-col py-12">
      <header className="flex flex-wrap items-center justify-between gap-3">
        <span className="neon-text text-sm font-semibold">Clip AI — Masuk</span>
        <PublicNav />
      </header>
      <section className="neon-panel rise-in mx-auto mt-12 w-full max-w-sm rounded-xl p-6 text-center">
        <ClapperboardIcon
          className="mx-auto size-12 text-[var(--neon-soft)]"
          aria-hidden="true"
        />
        <h1 className="neon-text display-title mt-4 text-2xl font-bold">
          Masuk ke studio.
        </h1>
        <p className="mt-2 text-sm leading-relaxed text-[var(--ink-muted)]">
          Hanya email yang terdaftar di OWNER_EMAILS yang bisa masuk.
        </p>
        <Button
          type="button"
          className="mt-6 min-h-11 w-full"
          disabled={busy}
          onClick={() => void signIn()}
        >
          {busy ? 'Menghubungkan Google…' : 'Lanjut dengan Google'}
        </Button>
        {message ? (
          <p role="alert" className="mt-3 text-sm text-[var(--negative)]">
            {message}
          </p>
        ) : null}
      </section>
      <div className="mt-auto">
        <PublicFooter />
      </div>
    </main>
  )
}

export const Route = createFileRoute('/login')({ component: Login })
