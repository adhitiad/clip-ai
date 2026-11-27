import { createFileRoute } from '@tanstack/react-router'

import { PublicPage } from '#/components/public-page'

const Contact = () => (
  <PublicPage
    title="Kontak"
    intro="Clip AI adalah project pribadi, bukan layanan dengan dukungan publik."
  >
    <section className="neon-panel rise-in rounded-xl p-5">
      <h2 className="display-title text-lg font-semibold">
        Belum ada alamat publik
      </h2>
      <p className="mt-2 text-[15px] leading-relaxed text-[var(--ink-muted)]">
        Tidak ada alamat kontak yang dipublikasikan di halaman ini. Untuk
        keperluan internal, gunakan kanal yang sudah disepakati pemilik di luar
        aplikasi.
      </p>
    </section>
    <section className="neon-panel rise-in rounded-xl p-5">
      <h2 className="display-title text-lg font-semibold">Masuk ke studio</h2>
      <p className="mt-2 text-[15px] leading-relaxed text-[var(--ink-muted)]">
        Pemilik dapat melanjutkan ke halaman masuk Google lalu membuka ruang
        kerja yang berisi status antrean dan task terbaru.
      </p>
    </section>
  </PublicPage>
)

export const Route = createFileRoute('/contact')({ component: Contact })
