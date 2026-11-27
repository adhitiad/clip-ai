import { useState } from 'react'

import { createFileRoute, Link } from '@tanstack/react-router'
import { ClapperboardIcon, FilmIcon } from 'lucide-react'

import { Button } from '#/components/ui/button'
import { PublicFooter, PublicNav } from '#/components/public-page'

const platforms = ['shorts', 'reels', 'tiktok'] as const

const briefSamples: Record<(typeof platforms)[number], string[]> = {
  shorts: ['Hook 3 detik', 'Judul pendek', 'Caption + hashtag'],
  reels: ['Hook visual', 'Judul editorial', 'Caption padat'],
  tiktok: ['Hook percakapan', 'Judul pendek', 'Caption tren'],
}

const steps = [
  'Riset niche dari endpoint trending.',
  'Analisis video dan trend.',
  'Brief plus skor viral rule-based.',
  'Render MP4 lewat antrean shorts-render.',
]

const Landing = () => {
  const [platform, setPlatform] = useState<(typeof platforms)[number]>('shorts')

  return (
    <main className="page-wrap pb-16">
      <header className="flex flex-wrap items-center justify-between gap-3 py-6">
        <Link to="/landing" className="flex items-center gap-2">
          <ClapperboardIcon
            className="size-8 text-[var(--neon-soft)]"
            aria-hidden="true"
          />
          <span className="neon-text text-sm font-semibold">Clip AI</span>
        </Link>
        <PublicNav />
      </header>

      <section className="rise-in flex flex-col gap-6 sm:flex-row sm:items-center">
        <div className="min-w-0 flex-1">
          <h1 className="neon-text display-title text-3xl font-bold sm:text-5xl">
            Dari riset sampai klip siap unggah.
          </h1>
          <p className="mt-3 max-w-xl text-[15px] leading-relaxed text-[var(--ink-muted)]">
            Agent menyusun hook, judul, dan caption untuk Shorts, Reels, atau
            TikTok.
          </p>
          <Button asChild type="button" className="mt-5 min-h-11">
            <Link to="/login">Masuk ke studio</Link>
          </Button>
        </div>
        <FilmIcon
          className="size-40 shrink-0 rounded-xl border border-[var(--line)] p-6 text-[var(--neon-soft)]"
          aria-label="Ikon klip video Clip AI"
        />
      </section>

      <section className="neon-panel rise-in mt-10 rounded-xl p-5">
        <h2 className="display-title text-lg font-semibold">
          Contoh format brief dari backend
        </h2>
        <div
          className="mt-3 flex flex-wrap gap-2"
          role="group"
          aria-label="Platform"
        >
          {platforms.map((item) => (
            <Button
              key={item}
              type="button"
              variant={item === platform ? 'default' : 'outline'}
              className="min-h-11"
              onClick={() => setPlatform(item)}
            >
              {item}
            </Button>
          ))}
        </div>
        <ul className="mt-4 space-y-2 text-sm">
          {briefSamples[platform].map((line) => (
            <li key={line} className="text-[var(--ink)]">
              {line}
            </li>
          ))}
        </ul>
      </section>

      <section className="mt-12">
        <h2 className="display-title text-lg font-semibold">Alur kerja</h2>
        <ol className="mt-3 space-y-2 text-[15px] text-[var(--ink-muted)]">
          {steps.map((step, index) => (
            <li key={step}>
              {index + 1}. {step}
            </li>
          ))}
        </ol>
      </section>

      <section className="mt-12">
        <h2 className="display-title text-lg font-semibold">Kedaulatan data</h2>
        <p className="mt-2 text-[15px] leading-relaxed text-[var(--ink-muted)]">
          Data bisa diekspor, dihapus dengan konfirmasi, dan setiap panggilan AI
          dicatat. Detailnya ada di halaman backend setelah masuk.
        </p>
      </section>

      <PublicFooter />
    </main>
  )
}

export const Route = createFileRoute('/landing')({ component: Landing })
