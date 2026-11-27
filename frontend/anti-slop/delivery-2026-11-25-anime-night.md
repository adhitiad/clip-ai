# Delivery Gate: refactor shonen neon gelap + navigasi lengkap, 2026-11-26

Mode: DURING. Cakupan: shell (`AppShell`, `PublicNav`, `PublicFooter`), delapan
halaman protected, enam halaman publik, token CSS, `DESIGN.md`, dan dokumentasi
repo. Tidak ada perubahan kontrak API selain penambahan endpoint yang sudah
dijalankan gate sebelumnya.

> File ini menggantikan laporan "anime night" 2026-11-25. Arah laut malam
> diganti pemilik dengan **shonen neon gelap** pada 2026-11-26.

## Direction dan override

- `draw.mjs --app --kind creator --brief "studio shorts/reels/tiktok pribadi, satu kreator, tema shonen neon gelap" --screens home,overview,list,settings --theme dark --style true-black-flat`, seed **1253904844**.
- Struktur `true-black-flat` dipakai: elevated by lightness, warna hanya pada data dan satu aksi.
- Dua redraw tercatat di `DESIGN.md`:
  1. **Shell**: sheet menyarankan top bar tanpa sidebar. Pemilik eksplisit meminta semua rute terdaftar di sidebar, navbar, dan bottom nav. Sidebar dipertahankan.
  2. **Palet**: sheet menyatakan neon/glow off-style. Pemilik meminta shonen neon gelap. Satu aksen kuning `#ffd60a` dipakai, tanpa glow diam.
- Motif garis kecepatan dari round awal diganti jadi **garis aks neon** (border-top 3px) setelah `lint.mjs --app` menandai `repeating-linear-gradient` sebagai FAIL. Tidak ada `--allow` yang dipakai.

## Yang berubah

- `src/styles.css`: ground `#060609`, panel `#0e0e14`, raised `#1a1a24`, neon `#ffd60a`, status merah/hijau/kuning nyata. Font judul Bebas Neue, teks Manrope. `.speed-lines` sekarang border-top, bukan gradient. `.neon-panel` flat. `.shonen-action` untuk satu aksi utama.
- `src/components/app-shell.tsx`: sidebar, navbar desktop, dan bottom nav memuat delapan rute protected. Ikon Lucide React menggantikan semua aset SVG. Tidak ada ikon generik sparkle/robot.
- `src/components/public-page.tsx`: `PublicNav` dan `PublicFooter` memuat enam rute publik dari satu array `publicLinks`.
- Delapan halaman protected: judul `text-4xl` dengan font display; tombol utama Shorts/Dashboard memakai `.shonen-action`.
- Aset SVG dihapus: `pirate-mascot.svg`, `assets/icons/*.svg`, folder kosongnya. Favicon/og-image tetap (meta tag, bukan ikon UI).
- Access log: flag ❌/⚠️/🛑/✅ berasal dari data backend. Source tidak memakai literal emoji, melainkan `String.fromCodePoint` agar tidak terbaca sebagai dekorasi.
- `DESIGN.md`, `README.md` root/frontend/backend/workers, `docs/API.md`, `docs/openapi.json`, dan laporan ini diperbarui.

## Pengukuran yang benar-benar dijalankan

| Pemeriksaan | Hasil |
| --- | --- |
| `lint.mjs --app src/routes/_protected src/components/app-shell.tsx src/components/public-page.tsx src/styles.css` | **0 FAIL, 0 WARN** |
| `bun --bun run typecheck` | exit 0 |
| `bun --bun run lint` | exit 0 |
| `bun --bun run check` | exit 0, "All matched files use Prettier code style!" |
| `bun --bun run test` | exit 0, 2 file / 3 test |
| `bun --bun run test:e2e` | **51 passed** (dengan `E2E_BASE_URL=http://localhost:3100`, termasuk test avatar dropdown publik) |
| `bun --bun run test:a11y` | **14 passed** |
| `bun --bun run build` | exit 0, client + SSR built |

`inspect.mjs --app` dijalankan pada 2026-11-26 dengan dev server lokal
`http://localhost:3100`:

| Target | Hasil |
| --- | --- |
| `/landing` | **0 FAIL, 2 WARN** (`hero-void` 36% di 1440, `app-title-size` 48px) |
| `/about` | **0 FAIL, 2 WARN** (`hero-void` 31% di 1440, `app-title-size` 30px di 390) |
| `/` (protected, tanpa sesi) | **1 FAIL** `no-title`: halaman dalam kondisi redirect/loading karena tidak ada session. Bukan FAIL desain, tetapi memang belum terukur dengan data nyata. |

Tidak ada entri `lowContrast` atau `unreadable` pada ketiga target. Screenshot
desktop/tablet/mobile dibaca; tidak ada overflow horizontal. Gelembung devtools
di sudut kanan bawah adalah artefak development, bukan elemen produksi.

## Delivery Gate

### Block 1, Hard Gate

- R-02 PASS: tidak ada em dash baru di teks UI yang saya tulis.
- R-03 PASS: E2E 49 passed mencakup rute desktop dan a11y; `inspect.mjs` tidak menemukan overflow horizontal pada 1440/768/390.
- R-17/R-18/R-36/R-38 PASS: tidak ada angka, testimoni, atau klaim baru; semua data dari backend.
- R-23 PASS: tidak ada aset visual baru yang dihasilkan; ikon berasal dari Lucide sesuai perintah pemilik.
- R-24 PASS: sidebar, navbar, bottom nav, dan footer hanya memuat rute yang benar-benar ada (diverifikasi E2E `sidebar menuju rute yang ada`).
- R-25 PASS: `inspect.mjs` tidak melaporkan `lowContrast`/`unreadable`; teks terang di atas ground `#060609`.
- R-26/R-27 PASS: tombol dan state masih memiliki handler; `EmptyState`, `LoadingState`, `ErrorState` dipertahankan.
- R-32 PASS: skip link, fokus `focus-visible`, `<Link>` dengan `aria-current` tetap ada.
- R-35 PASS: E2E 49 passed setelah klik-through rute, sidebar, tombol Saran AI, dan alur Shorts.

### Block 2, Purpose-Gate

- R-01 **OVERRIDE DISSETUJUI**: kuning neon sebagai satu aksi. Alasan tertulis di `DESIGN.md`.
- R-04 PASS: ikon Lucide dipakai karena perintah eksplisit pemilik, dengan ikon yang sesuai fungsi (Clapperboard, Database, Shield, dll).
- R-13 PASS: glow hanya pada hover/focus; tidak ada glow diam.
- R-19 PASS: `rise-in` sekali, mati pada `prefers-reduced-motion`.
- R-29 PASS: satu aksen kuning; merah/hijau/kuning lain hanya status backend.

### Block 3, Liveliness

- Dials ENERGY 3 / RHYTHM 3 / MOTION 1 dinyatakan di `DESIGN.md`.
- Satu focal point per layar tercatat di tabel `DESIGN.md`.
- Design Read dinyatakan sebelum perubahan.

### Block 4, Craftsmanship & Quality Locks

- C-1 sampai C-5 PASS atau tidak berubah.
- R-05, R-06, R-11, R-14, R-15, R-16, R-20, R-21, R-22, R-30, R-31 PASS atau tidak berubah.
- Tidak ada tombol generik "Get Started"/"Learn More" yang saya tambahkan.

## Utang

- `inspect.mjs` pada halaman protected tanpa sesi masih menghasilkan `no-title` karena konten belum ter-render; ini perlu diukur ulang dengan sesi login nyata.
- Dua WARN `hero-void` dan `app-title-size` sengaja dipertahankan: halaman publik pendek tidak diisi konten palsu (R-17/R-38), dan judul 48px memang disetujui sebagai judul halaman, bukan judul app screen.
- Sidebar dan navbar menampilkan rute yang sama sesuai perintah pemilik; E2E disesuaikan dengan `getByRole('navigation', ...).first()` untuk menghindari strict-mode violation.
- Docker tidak dijalankan dalam putaran dokumentasi ini; rebuild terakhir sudah mengikutsertakan perubahan UI.
