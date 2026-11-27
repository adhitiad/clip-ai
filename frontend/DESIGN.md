# DESIGN.md: Frontend Clip AI

Arah desain ditulis oleh pemilik, lalu diformat oleh agen. Pemilik: tim internal. Versi ini menggantikan arah "anime petualangan laut pada malam yang tenang" (25 Nov 2026). Perubahan diminta pemilik pada 26 Nov 2026: **shonen neon gelap**, karena arah laut malam terasa terlalu tenang.

## Design Read

Reading this as: studio short-form pribadi untuk satu kreator, bahasa visual **shonen neon gelap**, dial ENERGY 3 / RHYTHM 3 / MOTION 1.

Artinya: hitam pekat sebagai kanvas, satu aksi kuning-neon sebagai "electric" shonen, tipografi judul bertubuh komik, dan satu motif garis kecepatan. Bukan gradien, bukan glow di semua elemen, bukan tujuh warna. Neon hanya di satu aksi dan pada data yang benar-benar penting.

Struktur app screen memakai `draw.mjs --app --kind creator --screens home,overview,list,settings --theme dark --style true-black-flat`, seed **1253904844**. Dua redraw dicatat:

1. **Shell**: sheet menyarankan top bar tanpa sidebar. Pemilik eksplisit meminta semua rute protected terdaftar di sidebar, navbar, dan bottom nav. Sidebar dipertahankan, navbar dan bottom nav tetap ada.
2. **Palet**: sheet menyatakan neon dan glow off-style. Pemilik meminta "shonen neon gelap". Satu aksen kuning-neon dipakai sebagai identitas, tetapi tetap satu warna saja, tidak menyentuh nav/tab, dan tanpa glow diam.

## Dials

- ENERGY 3: menyapa keras. Judul besar, satu aksi terang, motif garis kecepatan.
- RHYTHM 3: tiap halaman punya komposisi berbeda, bukan satu template delapan kali.
- MOTION 1: transisi singkat, reveal sekali saat masuk, tanpa gerak terus-menerus.

## Override aturan yang disetujui pemilik

- **R-01**: tidak ada gradien dekoratif. Hitam flat, satu aksen kuning-neon.
- **R-04**: Lucide React dipakai karena perintah eksplisit pemilik, bukan karena library-nya. Ikon dipilih yang relevan dengan fungsinya.
- **R-13**: glow hanya saat hover atau focus, tidak pada elemen diam.
- **R-21**: satu tema gelap karena identitas shonen malam, bukan default "tech". Tanpa toggle terang.
- **R-29**: satu aksen kuning-neon. Merah dan hijau hanya untuk status nyata dari backend.
- Lembar `true-black-flat` menyatakan navy/slate dan neon off-style. Keduanya ditimpa oleh perintah pemilik; elevasi tetap memakai level kecerahan, bukan navy.

Semua teks memenuhi kontras AA 4.5:1 terhadap ground dan surface. Glow tidak menurunkan keterbacaan.

## Palet

| Token         | Nilai     | Peran                                           |
| ------------- | --------- | ----------------------------------------------- |
| `--ground`    | `#060609` | kanvas hitam pekat                              |
| `--panel`     | `#0e0e14` | permukaan kartu, satu langkah lebih terang      |
| `--raised`    | `#1a1a24` | permukaan bersarang, input                      |
| `--line`      | `#2a2a38` | batas elemen                                    |
| `--ink`       | `#f6f6f8` | teks utama                                      |
| `--ink-muted` | `#b9b9c7` | teks sekunder                                   |
| `--ink-faint` | `#9292a4` | meta, masih 4.5:1 di panel                      |
| `--neon`      | `#ffd60a` | kuning shonen, satu-satunya aksi dan aksen data |
| `--neon-soft` | `#ffe97a` | judul besar tanpa glow                          |
| `--neon-ink`  | `#140f00` | teks di atas kuning                             |
| `--magenta`   | `#ff4d6d` | status GRATIS & error nyata                     |
| `--warning`   | `#ffb020` | peringatan nyata dari backend                   |
| `--negative`  | `#ff4d6d` | nilai negatif nyata                             |
| `--positive`  | `#7ee787` | nilai positif nyata                             |

Nama variabel lama (`--neon`, `--neon-soft`, `--neon-ink`, `--magenta`, `--warning`, `--negative`, `--glow-cyan`, `--rope-line`) dipertahankan supaya komponen tidak perlu diganti nama.

## Tipografi

- Judul: **Fraunces** (serif bertubuh, bobot 700), tracking -0.03em, leading 0.95. Alasan: memberi suara komik/editorial yang membedakan shonen dari dashboard SaaS.
- Teks: **Manrope** (sans geometris), bobot 400/500/600/700/800. Alasan: keterbacaan data pada layar gelap dan ketersediaan sudah di repo.
- Angka: `font-variant-numeric: tabular-nums`.

## Motif identitas

Satu motif **garis kecepatan**: empat garis miring tipis di sudut kanan atas sidebar dan header. Bukan grid, bukan dot pattern. Maknanya: arah dan momentum, sesuai shonen. Dipakai sekali per layar, tidak mengulang di tiap kartu.

## Focal point per layar

| Halaman      | Pertanyaan yang dijawab         | Focal point                         |
| ------------ | ------------------------------- | ----------------------------------- |
| `/`          | Provider apa yang dipakai?      | Kartu model aktif, satu baris besar |
| `/shorts`    | Apa brief berikutnya?           | Form topik + tombol neon            |
| `/niche`     | Topik apa yang layak?           | Daftar trending dengan skor         |
| `/history`   | Klip mana yang terbaik?         | Tabel skor terurut                  |
| `/dashboard` | Seberapa sehat studio hari ini? | Angka total klip terbesar           |
| `/tools`     | Alat apa yang siap?             | Status model rule-based             |
| `/backend`   | Apa yang bisa diperiksa?        | Daftar blok data                    |
| `/protected` | Siapa pemiliknya?               | Kartu profil                        |

## Teks

Singkat, Inggris/Indonesia campur sesuai konteks existing. Tanpa "Welcome back", tanpa emoji dekoratif, tanpa buzzword. CTA menyebut aksi nyata: "Buat brief", "Cari video", "Muat ulang".
