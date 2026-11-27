import { createFileRoute } from '@tanstack/react-router'

import { PublicPage } from '#/components/public-page'

const About = () => (
  <PublicPage
    title="Tentang Clip AI"
    intro="Studio pribadi untuk mengubah riset topik menjadi klip pendek yang siap diunggah."
  >
    <section className="neon-panel rise-in rounded-xl p-5">
      <h2 className="display-title text-lg font-semibold">Yang dilakukan</h2>
      <ul className="mt-3 space-y-2 text-[15px] text-[var(--ink-muted)]">
        <li>Mencari topik dan video dari endpoint riset backend.</li>
        <li>Menyusun brief berisi hook, judul, caption, dan hashtag.</li>
        <li>Menilai potensi viral dengan aturan, bukan model terlatih.</li>
        <li>Merender MP4 lewat antrean RabbitMQ.</li>
      </ul>
    </section>
    <section className="neon-panel rise-in rounded-xl p-5">
      <h2 className="display-title text-lg font-semibold">
        Bukan layanan publik
      </h2>
      <p className="mt-2 text-[15px] leading-relaxed text-[var(--ink-muted)]">
        Clip AI dipakai oleh satu pemilik. Tidak ada paket, tagihan, kredit,
        atau pendaftaran terbuka. Login hanya dengan Google dan email yang
        diizinkan pemilik.
      </p>
    </section>
  </PublicPage>
)

export const Route = createFileRoute('/about')({ component: About })
