# Delivery Gate: audit desain + aksesibilitas, 2026-11-25

Mode: DURING. Cakupan: tujuh layar app (`/`, `/shorts`, `/niche`, `/history`, `/dashboard`, `/tools`, `/finance`) plus shell, `DataTable`, `Card`, dan state.

## Arah yang dipakai

- `draw.mjs --app --kind creator --screens home,overview,list --style accent-ladder --keep palette,type`
- Seed: **689322416**, direction **accent-ladder**, light.
- `--keep palette,type` dipakai karena `DESIGN.md` sudah memuat palet dan tipografi yang ditulis pemilik. User mengizinkan redraw, tetapi pengukuran menunjukkan masalahnya bukan pada warna atau font: teks sidebar kalah dari aturan `a` yang tidak berlayer. Mengganti palet tidak akan memperbaiki kontras dan akan membuang arah pemilik. Tidak ada slot direction yang di-redraw.
- Design Read (dari `DESIGN.md`): ringkasan model dan provider AI untuk tim internal, bahasa visual maritim tenang, dial **ENERGY 1 / RHYTHM 3 / MOTION 2**.
- Idea: daftar provider dan alur pembuatan clip menjadi panel kerja yang bisa dipindai tanpa dekorasi.
- Live thing: tombol `Simpan` pada kartu provider yang berubah menjadi `Tersimpan` dan tercatat di koleksi lokal.

## Temuan Web Interface Guidelines

Format `file:line`, ringkas. Yang sudah diperbaiki ditandai DONE; yang tidak diubah ditandai OPEN dengan alasan.

### Accessibility

- `src/components/app-shell.tsx:161` DONE: skip link "Lewati ke konten" ditambahkan; sebelumnya tidak ada.
- `src/components/app-shell.tsx:170` DONE: target skip link memakai `<main id="main" tabIndex={-1}>`.
- `src/components/app-shell.tsx:134` DONE: tautan sidebar memakai `text-sidebar-foreground`, mengalahkan aturan `a` base dan menaikkan kontras dari 3.5:1 menjadi >4.5:1.
- `src/components/states.tsx:16` DONE: `role="status"` + `aria-live="polite"` untuk pembaruan async.
- `src/components/ui/sidebar.tsx:135` OK: ikon dekoratif memakai `aria-hidden="true"`.
- `src/components/app-shell.tsx:85` OK: `AvatarImage` memakai `alt={name}`.

### Forms

- `src/components/data-table.tsx:69` DONE: input pencarian diberi `name`, `autoComplete="off"`, dan placeholder `Cari data…`.
- `src/routes/niche.tsx:30` DONE: input wilayah diberi `name`, `autoComplete="off"`, `spellCheck={false}`.
- `src/routes/niche.tsx:50` DONE: input jumlah diberi `name`, `inputMode="numeric"`, `autoComplete="off"`.
- `src/routes/niche.tsx:27` OK: label memakai `htmlFor`.
- `src/components/data-table.tsx:64` OK: label memakai `htmlFor` ke input pencarian.
- `src/components/data-table.tsx:47` OPEN: filter, sort, dan pagination disimpan di store UI, bukan query param URL. Mengubahnya menyentuh kontrak rute dan berisiko bagi pekerjaan agent lain; dicatat sebagai utang, bukan diperbaiki di audit ini.

### Typography / Content Handling

- `src/components/states.tsx:12` DONE: teks loading berakhir dengan elipsis dan menyebut sumbernya.
- `src/components/data-table.tsx:109` DONE: sel angka memakai `tabular-nums`.

### Animation / Dark Mode

- `src/styles.css:266` DONE: `prefers-reduced-motion: reduce` mematikan animasi dan transisi.
- `src/styles.css:10` / `src/styles.css:66` DONE: `color-scheme: light` dan `color-scheme: dark` mengikuti tema.
- `src/routes/__root.tsx:69` DONE: `theme-color` mengikuti latar `#e7f3ec`.

### Performance

- `src/routes/__root.tsx:75` / `:79` DONE: `preconnect` untuk domain font Google.

### Navigation & State

- `src/routes/__root.tsx:66` DONE: judul `Clip AI` menggantikan `TanStack Start Starter`.
- `e2e/home.spec.ts:5` DONE: ekspektasi judul mengikuti identitas produk.

### Content & Copy

- `src/components/states.tsx:12` DONE: pesan loading menyebut tindakan dan sumber, bukan skeleton sunyi.
- `src/components/states.tsx:36` OK: pesan error menyediakan aksi `Coba lagi`.
- `src/components/states.tsx:50` OK: empty state menyebut isi dan memberi aksi lanjutan.

### Anti-patterns yang dicek dan tidak ditemukan

Tidak ada `transition: all`, `outline-none` tanpa pengganti, `onPaste` + `preventDefault`, `<div onClick>` untuk navigasi, gambar tanpa dimensi/alt, `autoFocus`, emoji dekoratif, atau em dash di `src/`.

## Perubahan desain lain

- `src/styles.css:170` gradient garis bawah nav diganti warna datar `--lagoon`. Alasan: gradient tidak membawa hierarki, dan `--lagoon` sudah merupakan satu aksen resmi.
- `src/styles.css:172` radial gradient latar dipertahankan sebagai satu-satunya motif latar sesuai `DESIGN.md`. Ditandai `taste-skill-ignore` dan `prettier-ignore` agar pengecualiannya tercatat di sumber.
- `src/components/ui/card.tsx:9` `shadow-sm` dihapus. Alasan: keputusan pemilik "tetap datar", dan `DESIGN.md` diperbarui agar tidak bertentangan.
- `DESIGN.md` diperbarui untuk warna tautan, kartu datar, reduced motion, metadata, skip link, dan teks loading.

## Pengukuran sebelum dan sesudah

| Layar | Sebelum | Sesudah |
| --- | --- | --- |
| `/` | 0 FAIL, 4 WARN (kontras, hero-void, unused-canvas, panel-void) | 0 FAIL, 2 WARN (hero-void, panel-void) |
| `/shorts` | 0 FAIL | 0 FAIL |
| `/niche` | 0 FAIL | 0 FAIL |
| `/history` | 0 FAIL | 0 FAIL |
| `/dashboard` | 0 FAIL, 3 WARN | 0 FAIL, 2 WARN |
| `/tools` | 0 FAIL | 0 FAIL |
| `/finance` | 0 FAIL | 0 FAIL |

`lint.mjs --app`: sebelum 2 FAIL (gradient) + 1 WARN, sesudah **0 FAIL + 1 WARN**. WARN tersisa adalah deteksi palsu: `ModelBadge.tsx:31` memakai variabel `--kicker` untuk warna badge GRATIS, bukan eyebrow di atas judul. Badge itu melabeli status nyata dari backend, jadi dipertahankan (R-09).

WARN `hero-void` dan `panel-void` dipertahankan dengan alasan yang bisa dipertahankan di depan desainer: layar diambil tanpa sesi login, sehingga semua query berada pada state loading dan tidak ada data nyata yang boleh direkayasa untuk mengisi ruang. Mengisi ruang dengan angka atau kartu rekaan akan melanggar R-17, R-36, dan R-38. Saat backend mengembalikan data, ruang itu diisi oleh daftar provider dan tabel yang sudah ada.

## Critique

ROUND 1 (sebelum perbaikan, screenshot `.taste-skill/before/**`)

Seen in one second: panel kerja dengan sidebar gelap-terang dan satu judul kecil di kanan atas; hampir seluruh layar kosong.
Idea (one sentence): daftar provider dan alur clip sebagai panel scan, bukan landing page.
Live thing: tombol Simpan pada kartu provider, tetapi tidak tampil tanpa data.
Layout words by section: sidebar=navigasi / header=identitas / content=judul + skeleton.
Scores: design 5.5 · usability 6 · creativity 5 · content 4 → overall **5.4**.
Caps applied: decorative gradient, lebih dari dua layar kosong, skeleton placeholder, tidak ada tombol aksi utama di layar pertama.
Top three problems:
1. Tautan sidebar berwarna teal 3.5:1, gagal WCAG AA. Fix: pindahkan aturan `a` ke `@layer base` dan beri `text-sidebar-foreground` pada tautan.
2. Gradient pada garis bawah nav dan latar tidak tercatat sebagai keputusan. Fix: garis bawah jadi warna datar; latar diberi alasan tertulis dan `taste-skill-ignore`.
3. Loading state hanya dua batang abu tanpa keterangan. Fix: teks "Memuat data dari backend…" dengan `aria-live`.

ROUND 2 (sesudah perbaikan, screenshot `.taste-skill/after/**` dan `.taste-skill/final/**`)

Seen in one second: panel kerja tenang, sidebar dengan label gelap terbaca, judul di kiri atas konten, satu baris keterangan loading.
Idea (one sentence): sama seperti Round 1, kini konsisten di tujuh layar.
Live thing: tombol Simpan / Tersimpan pada kartu provider, terverifikasi oleh e2e.
Layout words by section: sidebar=navigasi bergrup / header=identitas / content=judul + satu blok data / footer=sesi pengguna.
Scores: design 6.0 · usability 7 · creativity 6 · content 5 → overall **6.2**.
Caps applied: gradient latar (brand), lebih dari dua layar desktop sebagian besar kosong, skeleton sebagai placeholder, tidak ada tombol aksi utama sebelum data hadir, halaman bisa menjadi milik produk lain (creativity ≤6), placeholder skeleton (content ≤5).
Top three problems (yang tersisa, most visible first):
1. Enam dari tujuh layar menampilkan 61% ruang kosong karena tidak ada sesi login saat inspect. Fix memerlukan data backend nyata, bukan ornamen; sengaja tidak direkayasa.
2. Judul 24px terasa kecil pada canvas 1440px sehingga hirarki lemah. Fix akan mengubah skala tipografi yang ditetapkan pemilik; tidak dilakukan tanpa persetujuan redraw.
3. Gelembung devtools di pojok kanan bawah menimpa ruang kosong pada screenshot dev. Ini artefak lingkungan pengembangan, bukan elemen produksi.

ROUND 3 tidak dijalankan: masalah nomor satu dan dua memerlukan data nyata atau persetujuan perubahan tipografi, bukan perbaikan UI yang bisa dibuktikan dengan inspect ulang.

## Delivery Gate

### Block 1, Hard Gate

- R-03 PASS: inspect 1440/768/390 pada tujuh layar menunjukkan `horizontalOverflow: 0`; screenshot mobile `/shorts` dan `/` tidak ada teks keluar kontainer atau tabrakan kartu.
- R-25 PASS: `lowContrast` kosong pada inspect akhir; enam entri kontras 3.5-3.7:1 hilang setelah perbaikan layer.
- R-27 PASS: empty, loading, dan error state semuanya menyebut penyebab dan aksi; `states.tsx` memakai `Empty`, `role="alert"`, dan `aria-live`.
- R-32 PASS: skip link ditambahkan, fokus terlihat lewat `focus-visible` shadcn, dan tombol sort serta aksi tabel memakai `<button>` dengan `aria-label`.
- R-35 PASS: gate `test:e2e` 14 passed, exit 0; klik-through mencakup tujuh rute, sidebar, toggle, dropdown, state error, provider Simpan, dan tiga alur `/shorts`.
- R-02, R-17, R-18, R-23, R-24, R-26, R-28, R-33, R-34, R-36, R-37, R-38 PASS atau tidak berubah dari audit sebelumnya.

### Block 2, Purpose-Gate

- R-01 PASS: gradient nav dihapus; gradient latar adalah motif tunggal yang tertulis di `DESIGN.md` dan diberi `taste-skill-ignore`.
- R-04 PASS: ikon nav `House`, `Video`, `Search`, `History`, `LayoutDashboard`, `ChartNoAxesCombined`, `Wallet` menggambarkan fungsi halaman; `aria-hidden` dipakai.
- R-09 PASS: badge GRATIS dan badge status kesehatan melabeli data backend nyata.
- R-10, R-12, R-13 PASS: tanpa glass dekoratif; shadow pada card dihapus; tidak ada glow.
- R-19 PASS: MOTION 2 hanya transisi 180ms, dengan fallback reduced motion.

### Block 3, Liveliness

- Dials ENERGY 1 / RHYTHM 3 / MOTION 2 dinyatakan di `DESIGN.md` dan konsisten dengan implementasi.
- Satu fokus per layar: judul halaman + satu blok data. Whitespace bersifat struktural; aksen lagoon hanya pada aksi dan penanda status.
- Design Read dinyatakan sebelum perubahan.

### Block 4, Craftsmanship & Quality Locks

- C-1 sampai C-5 PASS.
- R-05, R-06, R-11, R-14, R-15, R-16, R-20, R-21, R-22, R-29, R-30, R-31 PASS atau tidak berubah.
- UI Skill Checklist: semua ya, kecuali URL-sync untuk state tabel (dicatat OPEN di bagian Guidelines).

## Gate yang dijalankan

Dari `frontend/`, semuanya exit 0:

| Perintah | Hasil |
| --- | --- |
| `bun --bun run typecheck` | exit 0 |
| `bun --bun run lint` | exit 0 |
| `bun --bun run check` | exit 0, "All matched files use Prettier code style!" |
| `bun --bun run test` | exit 0, 2 file / 3 test |
| `bun --bun run test:e2e -- --reporter=line` | exit 0, 14 passed |
| `bun --bun run build` | exit 0 |
| `lint.mjs --app ...` | exit 0, 0 FAIL, 1 WARN (false positive) |
| `inspect.mjs --app` tujuh rute | 0 FAIL di semua rute |

Catatan: log WebServer masih menampilkan `TypeError: First argument must be an Error object` dari `follow-redirects` pada `src/lib/shorts-api.ts`. Itu log sisi server dan tidak membuat Playwright gagal; file tersebut bukan bagian dari perubahan ini.
