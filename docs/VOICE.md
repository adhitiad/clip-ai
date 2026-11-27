# TTS vs STT vs LLM — Definisi Resmi

> **Baca ini dulu sebelum menyentuh kode suara.** Tertukar arah = fitur tidak jalan.

## 1. Definisi paling sederhana

| Singkatan | Nama lengkap | Arti | Arah | Input → Output |
| --- | --- | --- | --- | --- |
| **TTS** | *Text-to-Speech* | **Teks diubah jadi suara** (mesin bicara) | `TEKS → AUDIO` | `"Halo dunia"` → `halo.mp3` |
| **STT** | *Speech-to-Text* | **Suara diubah jadi teks** (mesin mendengar lalu menulis) | `AUDIO → TEKS` | `rekaman.mp3` → `"Halo dunia"` |
| **LLM** | *Large Language Model* | **Otak teks**: memahami/membuat teks, terjemahan, ringkasan | `TEKS → TEKS` | prompt → jawaban/JSON |

Cara ingat cepat:

```
TTS = Text  to Speech  →  "T" di depan = TEKS masuk
STT = Speech to Text   →  "S" di depan = SUARA masuk
LLM = otak, bukan suara
```

## 2. Di project ini dipakai untuk apa

| Kebutuhan | Jalur yang dipakai | Modul | Fungsi |
| --- | --- | --- | --- |
| Caption/subtitle video dari audio klip | **STT** | `backend/core/transcription.py` | `transcribe_words()` |
| Terjemah hook ke bahasa lain | **LLM** | `backend/services/model_discovery.py` | `get_text_model()` |
| Mentor/suara narasi dubbing | **TTS** | `backend/services/tts.py` | `generate_tts()` |
| Riset topik / bikin judul & hashtag | **LLM** | `backend/services/model_discovery.py` | `get_text_model()` |

Alur dubbing lengkap (`backend/services/dubbing.py`):

```
video.mp4
  │
  ├─(ekstrak audio)─▶ audio.mp3
  │                     │
  │                [STT] transcribe_segments()  → teks asli + timestamp
  │                     │
  │                [LLM] translate_segments()   → teks terjemahan
  │                     │
  │                [TTS] generate_tts()         → audio narasi baru (.mp3)
  │                     │
  └───────────────▶ [FFmpeg] gabung audio+video → video_dubbed.mp4
```

**`dubbing.py` tidak berisi implementasi TTS/STT/LLM.** Ia hanya menyambungkan ketiga modul di atas.

## 3. Provider & env (jangan tertukar)

| Jalur | Env selector | Nilai | Katalog |
| --- | --- | --- | --- |
| LLM | `AGENT_PROVIDER` + `AGENT_MODEL` | `nvidia`, `openai`, `gemini`, … | `MODEL_CATALOG` (17 LLM) |
| TTS | `TTS_PROVIDER` | `cartesia`, `camb`, `gtts`, `auto` | `TTS_PROVIDERS` di `backend/services/tts.py` |
| STT | `STT_PROVIDER` | `camb`, `openai`, `groq`, `auto` | `STT_PROVIDERS` di `backend/core/transcription.py` |

`auto` = coba provider berurutan sampai ada yang berhasil.

### Kenapa `cartesia`/`camb` tetap muncul di `MODEL_CATALOG`?

Karena katalog adalah **daftar semua provider**, bukan daftar chat model.
Keduanya ditandai `PROVIDER_KIND = "tts"` supaya tidak dipilih sebagai `AGENT_MODEL`.

```python
PROVIDER_KIND["cartesia"] == "tts"   # benar
PROVIDER_KIND["nvidia"]   == "llm"   # benar
```

Selector `scripts/select_agent_model.py` otomatis menyembunyikan provider `tts`
dari pilihan `AGENT_MODEL` dan menampilkan tiga grup terpisah.

## 4. Kesalahan umum (DILARANG)

| ❌ Jangan | ✅ Sebabnya / yang benar |
| --- | --- |
| Memanggil `init_chat_model("sonic-2", model_provider="cartesia")` | Cartesia itu TTS, bukan chat. Pakai `backend.services.tts.tts_cartesia()` |
| Memasukkan `cartesia`/`camb` ke `AGENT_MODEL` | Itu bukan LLM. Pilih dari provider `kind == "llm"` |
| Memakai `generate_tts()` untuk membuat subtitle | Itu TTS (teks→suara). Subtitle butuh `transcribe_words()` (STT) |
| Memakai `transcribe()` untuk membuat suara narasi | Itu STT (suara→teks). Narasi butuh `generate_tts()` |
| Menaruh implementasi TTS di `dubbing.py` | Sudah pindah ke `backend/services/tts.py` |
| Menghapus `cartesia`/`camb` dari katalog karena "bukan LLM" | Tetap daftarkan, tapi beri `PROVIDER_KIND = "tts"` |

## 5. Contoh kode yang benar

```python
# STT: audio -> teks
from backend.core.transcription import transcribe_words
words = transcribe_words("temp/audio.mp3")       # [{text, start, end}, ...]

# LLM: teks -> teks
from backend.services.model_discovery import get_text_model
judul = get_text_model().invoke("Buat judul viral untuk klip bola")

# TTS: teks -> audio
from backend.services.tts import generate_tts
mp3 = generate_tts("Bola masuk di menit terakhir!", "id")
```

## 6. Ringkasan satu kalimat

> **STT mendengarkan, LLM berpikir, TTS berbicara.**

## 7. Test pengingat

- `tests/test_voice_providers.py` — tiga registri terpisah & kategori benar.
- `tests/test_dubbing_providers.py` — TTS memakai provider terpilih.
- `tests/test_camb_transcription.py` — STT Camb menghasilkan segmen & kata.
