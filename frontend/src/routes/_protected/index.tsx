import type { CSSProperties } from 'react'

import { Suspense, lazy, useEffect, useRef, useState } from 'react'

import { createFileRoute, Link } from '@tanstack/react-router'
import { CompassIcon } from 'lucide-react'

import { AppShell } from '#/components/app-shell'
import { LoadingState } from '#/components/states'
import { Button } from '#/components/ui/button'
import { Card, CardContent, CardHeader, CardTitle } from '#/components/ui/card'

// Daftar provider memakai TanStack DB (~280 kB). Tidak perlu ikut initial bundle.
const ModelProviderGrid = lazy(async () => {
  const module = await import('#/components/ModelBadge')
  return { default: module.ModelProviderGrid }
})

const ProviderSection = () => {
  const sentinel = useRef<HTMLDivElement>(null)
  const [visible, setVisible] = useState(false)

  useEffect(() => {
    const node = sentinel.current
    if (!node || typeof IntersectionObserver === 'undefined') {
      setVisible(true)
      return
    }
    const observer = new IntersectionObserver((entries) => {
      if (entries.some((entry) => entry.isIntersecting)) {
        setVisible(true)
        observer.disconnect()
      }
    })
    observer.observe(node)
    return () => observer.disconnect()
  }, [])

  return (
    <div ref={sentinel}>
      {visible ? (
        <Suspense fallback={<LoadingState />}>
          <ModelProviderGrid />
        </Suspense>
      ) : (
        <LoadingState label="Daftar model dimuat saat dibuka…" />
      )}
    </div>
  )
}

const quickStarts = [
  {
    title: 'Buat brief clip',
    action: 'Buat clip',
    to: '/shorts',
    note: 'Rencanakan konten dan antre render.',
  },
  {
    title: 'Lihat riwayat',
    action: 'Lihat clip',
    to: '/history',
    note: 'Buka clip yang sudah dibuat.',
  },
  {
    title: 'Periksa alat',
    action: 'Cek alat',
    to: '/tools',
    note: 'Cek status penilaian viral.',
  },
] as const

const Home = () => {
  return (
    <AppShell>
      <h1 className="neon-text display-title rise-in text-4xl">
        Clip AI: Model Provider
      </h1>
      <div className="mt-4 flex flex-col items-start gap-4 sm:flex-row sm:items-center">
        <CompassIcon
          className="size-24 shrink-0 rounded-xl border border-[var(--line)] p-3 text-[var(--neon-soft)]"
          aria-label="Ikon navigator Clip AI"
        />
        <p className="text-[15px] leading-relaxed text-muted-foreground">
          Semua model AI lewat LangChain. Model gratis ditandai GRATIS dan
          didahulukan.
        </p>
      </div>

      <section className="mt-6" aria-labelledby="mulai-cepat">
        <h2
          id="mulai-cepat"
          className="display-title rise-in text-lg font-semibold"
        >
          Mulai cepat
        </h2>
        <div className="mt-3 grid grid-cols-1 gap-3 sm:grid-cols-3">
          {quickStarts.map((item, index) => (
            <Card
              key={item.to}
              className="neon-panel rise-in"
              style={{ '--rise-delay': `${index * 70}ms` } as CSSProperties}
            >
              <CardHeader>
                <CardTitle className="text-base font-semibold">
                  {item.title}
                </CardTitle>
              </CardHeader>
              <CardContent className="space-y-3">
                <p className="text-[15px] leading-relaxed text-[var(--ink-muted)]">
                  {item.note}
                </p>
                <Button asChild variant="outline" className="min-h-11 w-full">
                  <Link to={item.to}>{item.action}</Link>
                </Button>
              </CardContent>
            </Card>
          ))}
        </div>
      </section>

      <section className="mt-8" aria-labelledby="daftar-provider">
        <h2 id="daftar-provider" className="sr-only">
          Daftar model dan provider
        </h2>
        <ProviderSection />
      </section>
    </AppShell>
  )
}

export const Route = createFileRoute('/_protected/')({ component: Home })
