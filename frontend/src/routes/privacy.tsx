import { createFileRoute } from '@tanstack/react-router'

import { PublicPage } from '#/components/public-page'

const Privacy = () => (
  <PublicPage
    title="Kebijakan privasi"
    intro="Data apa yang disimpan Clip AI dan untuk apa."
  >
    <section className="neon-panel rise-in rounded-xl p-5">
      <h2 className="display-title text-lg font-semibold">Login</h2>
      <p className="mt-2 text-[15px] leading-relaxed text-[var(--ink-muted)]">
        Login memakai Google. Backend menyimpan email dan identitas Google untuk
        memverifikasi bahwa email termasuk daftar pemilik. Tidak ada kata sandi
        yang disimpan.
      </p>
    </section>
    <section className="neon-panel rise-in rounded-xl p-5">
      <h2 className="display-title text-lg font-semibold">Data kerja</h2>
      <p className="mt-2 text-[15px] leading-relaxed text-[var(--ink-muted)]">
        Clip, brief, skor, feedback performa, dan hasil task disimpan di
        database lokal PostgreSQL milik pemilik. File render disimpan di
        direktori output pada host yang sama.
      </p>
    </section>
    <section className="neon-panel rise-in rounded-xl p-5">
      <h2 className="display-title text-lg font-semibold">Layanan eksternal</h2>
      <p className="mt-2 text-[15px] leading-relaxed text-[var(--ink-muted)]">
        Saat fitur AI dipakai, teks dikirim ke penyedia model yang dipilih
        pemilik melalui konfigurasi backend. Token OAuth YouTube disimpan
        terenkripsi di perangkat host dan dipakai hanya untuk membaca data
        analitik yang diizinkan.
      </p>
    </section>
    <section className="neon-panel rise-in rounded-xl p-5">
      <h2 className="display-title text-lg font-semibold">Kedaulatan data</h2>
      <p className="mt-2 text-[15px] leading-relaxed text-[var(--ink-muted)]">
        Pemilik bisa mengekspor data lewat endpoint ekspor dan menghapusnya
        lewat endpoint hapus dengan konfirmasi. Audit panggilan AI dicatat tanpa
        kunci API atau token.
      </p>
    </section>
  </PublicPage>
)

export const Route = createFileRoute('/privacy')({ component: Privacy })
