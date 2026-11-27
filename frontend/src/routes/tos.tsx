import { createFileRoute } from '@tanstack/react-router'

import { PublicPage } from '#/components/public-page'

const Tos = () => (
  <PublicPage
    title="Ketentuan penggunaan"
    intro="Aturan singkat untuk satu studio milik pemilik."
  >
    <section className="neon-panel rise-in rounded-xl p-5">
      <h2 className="display-title text-lg font-semibold">Akses</h2>
      <p className="mt-2 text-[15px] leading-relaxed text-[var(--ink-muted)]">
        Hanya pemilik dengan email yang diizinkan yang boleh masuk. Akun dibuat
        dari Google. Tidak ada kata sandi, peran, atau paket berbayar.
      </p>
    </section>
    <section className="neon-panel rise-in rounded-xl p-5">
      <h2 className="display-title text-lg font-semibold">
        Konten yang dihasilkan
      </h2>
      <p className="mt-2 text-[15px] leading-relaxed text-[var(--ink-muted)]">
        Clip, brief, dan metadata dihasilkan untuk penggunaan pemilik. Sebelum
        mempublikasikan ke platform pihak ketiga, periksa kembali bahan, judul,
        dan hak cipta sumber video.
      </p>
    </section>
    <section className="neon-panel rise-in rounded-xl p-5">
      <h2 className="display-title text-lg font-semibold">Batasan</h2>
      <p className="mt-2 text-[15px] leading-relaxed text-[var(--ink-muted)]">
        Saran pendapatan bersifat informasi, bukan jaminan hasil. Skor viral
        berasal dari aturan, bukan model yang dilatih dari data Anda.
      </p>
    </section>
    <section className="neon-panel rise-in rounded-xl p-5">
      <h2 className="display-title text-lg font-semibold">Perubahan</h2>
      <p className="mt-2 text-[15px] leading-relaxed text-[var(--ink-muted)]">
        Ketentuan dapat berubah mengikuti fitur yang benar-benar ada di
        aplikasi. Versi tertulis ini menggambarkan keadaan saat halaman dibaca.
      </p>
    </section>
  </PublicPage>
)

export const Route = createFileRoute('/tos')({ component: Tos })
