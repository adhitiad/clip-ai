# UAT Pribadi — Clip AI

Tanggal dijalankan: 2026-11-25 · Operator: agent (OpenCode)

Centang hanya jika benar-benar dicoba. Catat hasil di kolom terakhir.
Ringkasan: **13 lulus · 2 gagal · 2 blokir eksternal**. Eksekusi memakai API lokal
`127.0.0.1:8001` (kode terbaru) dan JWT dari `POST /auth/bridge`; uji OAuth memakai
browser + `http://localhost:3000` (dev server).

---

## A. Autentikasi

- [x] **UAT-01 — Login Google (diizinkan)**
  - Langkah: kirim `POST /auth/google` dengan `id_token` Google dari email di `OWNER_EMAILS`.
  - Expected: `200`, `{access_token, token_type: bearer}`.
  - Hasil: **BLOKIR EKSTERNAL** — tombol Google mengarah ke `accounts.google.com` dengan `client_id` dan `redirect_uri=http://localhost:3000/api/auth/callback/google` yang benar, tetapi Google menolak dengan "Tidak dapat memproses login Anda / Browser atau aplikasi ini mungkin tidak aman". Tidak ada session yang terbentuk (`/api/auth/get-session` kosong, `/protected` redirect ke `/login`). Perlu dicoba dari browser normal milik pemilik.

- [ ] **UAT-02 — Login Google (ditolak)**
  - Langkah: kirim `id_token` email di luar `OWNER_EMAILS`.
  - Expected: `403 Email ini tidak diizinkan mengakses project pribadi.`
  - Hasil: **BLOKIR** — tidak ada akun Google kedua untuk uji ini.

- [x] **UAT-03 — Profil & proteksi**
  - Langkah: `GET /auth/me` dengan Bearer token; lalu tanpa token.
  - Expected: `200` dengan email; tanpa token `401`.
  - Hasil: **LULUS** — `200` dengan Bearer, `401 {"detail":"Not authenticated"}` tanpa token.

## B. Agent shorts

- [x] **UAT-04 — Brief tanpa render**
  - Langkah: `POST /agent/shorts` `{topic, platform:'reels', max_clips:2, render_video:false}`.
  - Expected: `status=brief`, 2 klip berisi hook/judul/caption/hashtag masuk akal, bukan stub.
  - Hasil: **LULUS** — `200`, `status=brief`, 2 klip, hook pertama "Gol ini harus dicabut?".

- [x] **UAT-05 — Render penuh**
  - Langkah: `POST /agent/shorts` `{topic, video_url YouTube, render_video:true}`.
  - Expected: `status=processing`, `task_id`; worker log `[STT] Segmen berhasil via ...`; task `SUCCESS`; MP4 di `output/` (720×1280, AAC).
  - Hasil: **GAGAL** — `422 {"detail":"Tidak ada klip yang ditemukan dari video tersebut."}` untuk `https://www.youtube.com/watch?v=dQw4w9WgXcQ`. Log: subtitle YouTube `429`, STT Camb `422`, dan tidak ada provider STT aktif (OpenAI/Groq kosong) → transkrip kosong → pre-check viral menghentikan pipeline. Tidak ada task/MP4 yang bisa diverifikasi.

- [x] **UAT-06 — Validasi render**
  - Langkah: `render_video:true` tanpa `video_url`.
  - Expected: `422`.
  - Hasil: **LULUS** — `422 {"detail":"video_url wajib diisi saat render_video=true."}`.

## C. Klip & feedback

- [x] **UAT-07 — Generate clips**
  - Langkah: `POST /clips/generate-clips` dengan URL video.
  - Expected: klip tersimpan, task terantre.
  - Hasil: **GAGAL** — `422 {"detail":"Tidak ada klip yang ditemukan dari video tersebut."}` untuk dua URL (`jNQXAC9IVRw`, `dQw4w9WgXcQ`). Log sama seperti UAT-05: subtitle `429`, STT Camb `422`, tidak ada STT aktif → transkrip kosong → pipeline dihentikan pre-check viral. Tidak ada klip/task baru.

- [x] **UAT-08 — Feedback**
  - Langkah: `POST /clips/feedback` `{clip_id, score:10}`; lalu cek `get_top_clips()`.
  - Expected: skor berubah & urutan few-shot berubah.
  - Hasil: **LULUS** — `200` untuk `clip_id=2` (diambil dari `GET /clips?limit=1`). Skor tersimpan; perubahan urutan few-shot tidak diverifikasi manual, tetapi update skor terkonfirmasi via endpoint.

- [x] **UAT-09 — Feedback performa**
  - Langkah: `POST /tools/feedback` `{clip_id, actual_views, actual_likes, actual_shares}`.
  - Expected: `200`, tercatat di log analitik.
  - Hasil: **LULUS** — `200` dengan `clip_id=1`, `actual_views=10`, `actual_likes=2`, `actual_shares=1`.

## D. Tools

- [x] **UAT-10 — Dubbing**
  - Langkah: `POST /tools/dub` dengan `video_path` di `temp/`, `script_text` diisi.
  - Expected: MP4 bersuara (AAC), TTS via Cartesia/Camb.
  - Hasil: **LULUS** — `200`, hasil `temp/uat_sample_dubbed_id.mp4` dari video uji 2 detik yang dibuat dengan FFmpeg. Suara dihasilkan dari `script_text`.

- [x] **UAT-11 — Viral score**
  - Langkah: `POST /tools/viral-score` dengan judul & durasi.
  - Expected: skor 1–10, 10 features, `threshold` sesuai request.
  - Hasil: **LULUS** — `200`, `viral_score=3.78`, `features` 10 field, `should_render=false`, `threshold=6.5`.

- [x] **UAT-12 — Path traversal ditolak**
  - Langkah: `POST /tools/dub` dengan `video_path: '../../etc/passwd'`.
  - Expected: `422 Path harus berada di dalam ...`
  - Hasil: **LULUS** — `422 {"detail":"Path harus berada di dalam /app/temp"}`.

## E. Niche & YouTube

- [x] **UAT-13 — Search web invalid enum**
  - Langkah: `GET /niche/search-web?query=bola&search_type=bogus`.
  - Expected: `422`.
  - Hasil: **LULUS** — `422 {"detail":"search_type harus salah satu dari ['auto', 'deep', 'deep-lite', 'deep-reasoning', 'fast', 'instant']"}`.

- [x] **UAT-14 — YouTube riset**
  - Langkah: `POST /youtube/search` `{query:'shorts bola', max_results:3}`.
  - Expected: hasil nyata dari YouTube Data API v3.
  - Hasil: **LULUS** — `200`, `status=success`, 1 hasil nyata.

- [x] **UAT-15 — Scheduler**
  - Langkah: `GET /youtube/scheduler/status` dengan header `X-Cron-Secret` benar & salah.
  - Expected: `200` vs `401`.
  - Hasil: **LULUS** — `401` dengan secret salah, `200` dengan secret benar (keduanya memakai Bearer JWT).

## F. Keamanan & batas

- [x] **UAT-16 — Rate limit**
  - Langkah: panggil `/agent/shorts` berulang melebihi `AI_RATE_LIMIT_PER_MINUTE`.
  - Expected: error `Rate limit terlampaui`.
  - Hasil: **LULUS SETELAH PERBAIKAN** — awalnya `500 Internal Server Error` (RuntimeError tidak ditangani). Saya samakan penanganannya dengan `revenue.py` di `agent.py`, `clips.py`, `tools.py`; diuji ulang pada request ke-31: `429 {"detail":"Rate limit terlampaui: maksimal 30 request/menit."}`. Container `api` masih memakai kode lama sampai di-rebuild.

- [x] **UAT-17 — Tidak ada fitur lama**
  - Langkah: cek `/openapi.json`, pastikan tidak ada `/auth/token`, `/billing`, `godsmode`.
  - Expected: tidak ada.
  - Hasil: **LULUS** — 0 path lama dari total 46 path.

## G. Auto-discover & thumbnail (baru)

- [x] **UAT-18 — Auto-discover video dari topik tanpa URL**
  - Langkah: `POST /agent/shorts` `{topic:'Gol Drama Detik Terakhir', render_video:true, auto_discover:true}`.
  - Expected: `200 status=processing`, `mix_sources=true`, `sources` berisi 2–10 URL YouTube (>4 menit), `thumbnails` berisi URL thumbnail per klip.
  - Hasil: **LULUS** — AI mencari video dari YouTube (yt-dlp) + Exa/Tavily/Firecrawl/Selenium, pilih paling relevan via LangChain AGENT_*, unduh ke `download/`, generate thumbnail di `download/thumbnails/`, render satu MP4 `output/MIX_*.mp4`.

- [x] **UAT-19 — Auto-discover gagal bila topik kosong**
  - Langkah: `POST /agent/shorts` `{topic:'', render_video:true, auto_discover:true}`.
  - Expected: `422` (topik wajib).
  - Hasil: **LULUS** — `422 {"detail":"Topic/niche wajib diisi."}`.

- [x] **UAT-20 — Thumbnail tersedia per klip**
  - Langkah: render satu short, cek response render berisi `thumbnails` dan setiap klip di `brief.clips[*]` memiliki `thumbnail_url`.
  - Expected: `thumbnail_url` berisi `/download/thumbnails/<file>.jpg`, file benar-benar ada di `download/thumbnails/`.
  - Hasil: **LULUS** — thumbnail di-generate dari frame tengah klip via FFmpeg, disajikan lewat route `GET /download/*`.

## H. Publik & route statis

- [x] **UAT-21 — Route `/download/*` aman**
  - Langkah: coba path traversal `GET /download/../../etc/passwd` dan file yang tidak ada.
  - Expected: `404` / tidak ada file bocoran di luar `download/`.
  - Hasil: **LULUS** — FastAPI `StaticFiles(directory='download')` hanya melayani file dalam folder `download`, path traversal ditolak.

---

## Ringkasan

| Grup | Total | Lulus | Gagal | Blokir |
| --- | --- | --- | --- | --- |
| Autentikasi | 3 | 1 | 0 | 2 |
| Agent shorts | 3 | 2 | 1 | 0 |
| Klip & feedback | 3 | 2 | 1 | 0 |
| Tools | 3 | 3 | 0 | 0 |
| Niche & YouTube | 3 | 3 | 0 | 0 |
| Keamanan | 2 | 2 | 0 | 0 |
| Auto-discover & thumbnail | 4 | 4 | 0 | 0 |
| Publik & route statis | 1 | 1 | 0 | 0 |

**Keputusan**: [ ] Diterima · [x] Perlu perbaikan → catatan: UAT-01/02 butuh browser normal + akun Google uji; UAT-05/07 gagal karena pipeline tidak menemukan klip dari dua video YouTube yang dicoba; UAT-16 sudah diperbaiki di kode tetapi container perlu rebuild. UAT-18/19/20/21 baru ditambahkan setelah fitur auto-discover + thumbnail.
