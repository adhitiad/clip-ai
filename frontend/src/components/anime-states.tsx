import { Link } from '@tanstack/react-router'
import type { ErrorComponentProps } from '@tanstack/react-router'

import { Button } from '#/components/ui/button'
import { CompassIcon } from 'lucide-react'

const Frame = ({ children }: { children: React.ReactNode }) => (
  <div className="neon-panel rise-in mx-auto mt-16 flex max-w-md flex-col items-center gap-4 rounded-xl p-8 text-center">
    <CompassIcon
      className="anime-bob size-24 shrink-0 rounded-xl border border-[var(--line)] p-3 text-[var(--neon-soft)]"
      aria-label="Ikon navigator Clip AI"
    />
    {children}
  </div>
)

export const AnimeLoading = () => (
  <Frame>
    <p className="display-title text-lg font-semibold">Sedang berlayar.</p>
    <p className="text-sm text-[var(--ink-muted)]">
      Menyiapkan halaman untukmu.
    </p>
  </Frame>
)

export const AnimeNotFound = () => (
  <Frame>
    <h1 className="neon-text display-title text-2xl font-bold">
      Halaman tidak ditemukan.
    </h1>
    <p className="text-sm text-[var(--ink-muted)]">
      Rute ini tidak ada di daftar halaman Clip AI.
    </p>
    <Button asChild type="button" variant="outline" className="min-h-11">
      <Link to="/">Kembali ke beranda</Link>
    </Button>
  </Frame>
)

export const AnimeError = ({ error, reset }: ErrorComponentProps) => (
  <Frame>
    <h1 className="neon-text display-title text-2xl font-bold">
      Layar ini gagal dimuat.
    </h1>
    <p className="text-sm text-[var(--ink-muted)]">
      {error instanceof Error ? error.message : String(error)}
    </p>
    <div className="flex flex-wrap justify-center gap-2">
      <Button
        type="button"
        variant="outline"
        className="min-h-11"
        onClick={() => reset()}
      >
        Coba lagi
      </Button>
      <Button asChild type="button" variant="ghost" className="min-h-11">
        <Link to="/">Ke beranda</Link>
      </Button>
    </div>
  </Frame>
)
