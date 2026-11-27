# API Key — Status Pemakaian

Audit pemakaian env var API key di repo (per 24 Nov 2026).
Terkait: [`.env.example`](../.env.example), [`GOAL.md`](GOAL.md) Bab 5, [`TASKS.md`](TASKS.md) T-01.

## 0. Login Google (tanpa password)

- Backend: `GOOGLE_CLIENT_ID` (wajib) dipakai `POST /auth/google` untuk verifikasi ID token.
- Frontend: `GOOGLE_CLIENT_ID` + `GOOGLE_CLIENT_SECRET` dipakai Better Auth (`socialProviders.google`), `emailAndPassword` dinonaktifkan.
- Endpoint password `/auth/token` & `/auth/register` **dihapus**. Kolom `hashed_password` berisi sentinel `GOOGLE_OAUTH` (bukan hash password).
- Revisi DB: `0002_google_auth` menambah `users.google_sub`.

## 1. Prinsip: satu LLM, provider bebas (LangChain)

Untuk UI `/shorts`, frontend memakai `AUTH_BRIDGE_TOKEN` (server-only) agar
server function Better Auth dapat menukar session menjadi JWT backend lewat
`POST /auth/bridge` (endpoint tersembunyi, tidak ada di OpenAPI). Jangan
expose token ini via `VITE_`.

**Tidak ada lagi key vendor yang di-hardcode sebagai "wajib".** Semua otak AI
(hook, terjemahan, viral score, niche, agent) lewat
`backend/services/model_discovery.py::get_text_model()` → `init_chat_model()`.

Pilih provider lewat `AGENT_PROVIDER` + `AGENT_MODEL` dan isi key provider itu.
Default repo: **`nvidia` / `nvidia/nemotron-3.5-super-vl-120b-a12b`** (gratis, NIM).

### Daftar model AI (katalog backend + penanda gratis)

| Icon | Provider | Model contoh | Status |
| --- | --- | --- | --- |
| 🎬 | **NVIDIA NIM** | `nvidia/nemotron-3.5-super-vl-120b-a12b`, `google/gemma-7b`, `qwen/qwen2.5-coder-32b-instruct` | 🆓 **GRATIS** (default) |
| 🤖 | OpenAI | `gpt-4o-mini`, `gpt-5`, `gpt-5-mini` | berbayar (sebagian gratis) |
| 🧠 | Google Gemini | `gemini-2.5-flash`, `gemini-2.0-flash` | 🆓 **GRATIS** |
| 🦜 | Anthropic | `claude-haiku-4-5`, `claude-sonnet-4-5` | berbayar |
| 🔀 | OpenRouter | `meta/llama-3.1-8b-instruct:free` | 🆓 **GRATIS** (suffix `:free`) |
| ☁️ | Cloudflare | `@cf/meta/llama-3.3-70b-instruct` | 🆓 **GRATIS** |
| 𝕏 | Grok (xAI) | `grok-4`, `grok-3` | berbayar |
| ⚡ | Groq | `llama-3.3-70b-versatile`, `llama-3.1-8b-instant` | 🆓 **GRATIS** |
| ∞ | Meta / Muse | `meta-llama/Llama-3.3-70B-Instruct` | berbayar |
| 🧮 | GLM (Zhipu) | `glm-3-turbo`, `glm-4` | 🆓 **GRATIS** |
| 🎧 | MiniMax | `minimax-01` | berbayar |
| 🌙 | Kimi (Moonshot) | `moonshot-v1-8k`, `kimi-k2-instruct` | 🆓 **GRATIS** |
| 🔍 | DeepSeek | `deepseek-chat`, `deepseek-reasoner` | 🆓 **GRATIS** |
| 🌬️ | Mistral | `mistral-small-latest` | 🆓 **GRATIS** |
| 🦙 | Ollama | `llama3.3`, `qwen3:8b` | 🆓 **GRATIS** (lokal) |
| 🤗 | Hugging Face | `meta-llama/Llama-3.1-8B-Instruct` | 🆓 **GRATIS** |
| 🗣️ | Cartesia | `sonic-2` | TTS berbayar |
| 🎙️ | Camb AI | `mars-8.1-flash-beta` | TTS berbayar |

Daftar provider/model di frontend berasal dari `GET /tools/providers` (backend), bukan hardcode di `frontend/src/lib/models.ts`. Tabel di atas adalah referensi katalog backend; UI menampilkan `id` provider, `kind`, dan penanda GRATIS dari respons backend.

| Key | Status | Dipakai di | Jika kosong |
| --- | --- | --- | --- |
| **`NVIDIA_API_KEY`** | **Default** | LLM NIM gratis (`nvapi-...` dari build.nvidia.com) | Pilih provider lain di `.env` |
| **`OPENAI_API_KEY`** | Opsional | LLM LangChain + transkripsi Whisper via REST | Ganti provider/model lain di `.env` |
| **`CARTESIA_API_KEY`** + `CARTESIA_VOICE_ID` | Opsional | TTS primary via `POST https://api.cartesia.ai/tts/bytes` | Lanjut ke Camb → gTTS |
| **`CAMB_API_KEY`** | Opsional | TTS fallback via `POST https://client.camb.ai/apis/tts-stream` | Lanjut ke gTTS |
| **`EXA_API_KEY`** | Opsional per fitur | `utils/exa_search.py` → `/niche/search-web`, `/niche/analyze-and-queue` | Endpoint Exa → 500 |
| **`PEXELS_API_KEY`** | Opsional | `utils/broll.py::download_broll()` | B-Roll diskip, render tetap jalan |
| **`PINECONE_API_KEY`** | Opsional | `services/vector_store.py` (vector store) | Vector search mati → fallback DB |
| **`OLLAMA_HOST` + `OLLAMA_EMBED_MODEL`** | Opsional | embeddings lokal/offline untuk Pinecone; default `embeddinggemma-2:570m` (768 dimensi). Set `PINECONE_DIMENSION=768` dan buat index baru bila ganti model. | Vector search mati → fallback DB |
| **`MONGODB_URL` + `MONGODB_DB`** | Opsional | Access log identitas per-request (Atlas/eksternal) via `pymongo`; koleksi `access_logs` + `known_ips` | Access log nonaktif, API tetap jalan |
| `HUGGINGFACEHUB_API_TOKEN` | Opsional | tidak lagi dipakai untuk embeddings; key lama boleh dibiarkan | Tidak berpengaruh ke vector search |
| **`GROQ_API_KEY`** | **Opsional (cadangan)** | Transkripsi Whisper cadangan + provider `groq` bila dipilih | Tidak menghentikan aplikasi |

> **ElevenLabs tidak dipakai.** Urutan TTS: **Cartesia → Camb AI → gTTS**.
> Transkripsi juga tidak terikat vendor: **Camb AI batch STT → OpenAI Whisper → Groq Whisper → VTT/manual**.
> `CAMB_API_KEY` dipakai untuk **dua hal**: TTS fallback dan STT utama — jadi tidak perlu
> `OPENAI_API_KEY`/`GROQ_API_KEY` untuk transkrip. Opsi: `CAMB_STT_LANGUAGE=auto`, `CAMB_STT_MODE=fast`.

## 2. Key penyedia LangChain lain (untuk agent)

`AGENT_PROVIDER` + `AGENT_MODEL` menentukan provider yang dipakai `/agent/shorts`.
`backend/services/model_discovery.py` meneruskan `model_provider` ke `init_chat_model`, jadi key yang dibutuhkan bergantung pada provider:

| Provider | Env yang dibaca LangChain |
| --- | --- |
| `groq` | `GROQ_API_KEY` |
| `openai` | `OPENAI_API_KEY` |
| `anthropic` | `ANTHROPIC_API_KEY` |
| `gemini` | `GOOGLE_API_KEY` |
| `xai` / `grok` | `XAI_API_KEY` |
| `deepseek` | `DEEPSEEK_API_KEY` |
| `mistral` | `MISTRALAI_API_KEY` |
| `openroute`/`openrouter` | `OPENROUTER_API_KEY` |
| `cartesia`, `camb`, `cloudflare`, `glm`, `minmax`, `kimi`, `meta/muse` | via `litellm` → `CARTESIA_API_KEY`, `CAMB_API_KEY`, `CLOUDFLARE_API_KEY`, `ZHIPU_API_KEY`, `MINIMAX_API_KEY`, `MOONSHOT_API_KEY`, `META_API_KEY` |
| `ollama` | lokal: `OLLAMA_HOST` (tanpa key); cloud: `OLLAMA_API_KEY` |
| `huggingface` | `HUGGINGFACEHUB_API_TOKEN` |

Katalog **19 provider** ada di `backend/services/model_discovery.py::MODEL_CATALOG`, termasuk **`nvidia` (NVIDIA NIM di build.nvidia.com)** lewat `langchain-nvidia-ai-endpoints`. Default: `AGENT_PROVIDER=nvidia`, `AGENT_MODEL=nvidia/nemotron-3.5-super-vl-120b-a12b` (gratis). Isi `NVIDIA_API_KEY` (format `nvapi-...`, gratis dari build.nvidia.com).

Untuk `openrouter`/`openroute`, bila paket `langchain-openrouter` belum terpasang, `select_chat_model()` memakai `ChatOpenAI` dengan `base_url` dari `OPENROUTER_BASE_URL` (default `https://openrouter.ai/api/v1`) — tetap satu jalur LLM LangChain.

> Embeddings vector sekarang **lokal via Ollama**: `ollama pull all-minilm`
> (384 dimensi, cocok dengan index `clip-ai-hooks` yang lama). Bila memakai
> `nomic-embed-text` (768), set `PINECONE_DIMENSION=768` dan buat index baru.

## 3. Revenue (read-only)

| Key | Status | Dipakai di | Jika kosong |
| --- | --- | --- | --- |
| API key provider `AGENT_*` (mis. `NVIDIA_API_KEY`) | Opsional, dipakai `GET /revenue/advice` | model `AGENT_PROVIDER`/`AGENT_MODEL`; override opsional `REVENUE_AI_MODEL=provider/model` | endpoint advice → `503` |
| `YOUTUBE_TOKEN_ENCRYPTION_KEY` + `YOUTUBE_OAUTH_*` | Opsional | dekripsi/refresh token YouTube untuk Analytics | YouTube ditandai `available:false` |
| `TIKTOK_ACCESS_TOKEN`, `META_ACCESS_TOKEN` | Opsional (placeholder adapter) | penanda adapter TikTok/Meta Reels | platform ditandai "Dilewati" |

**Prioritas gratis:** `FREE_MODELS` + `_sort_free_first()` menaruh model gratis lebih dulu untuk semua provider (NIM, Groq, Gemini flash, OpenRouter `:free`, DeepSeek, Ollama lokal, dll). Urutan provider juga diurutkan berdasarkan jumlah model gratis — NIM paling depan.

Untuk mencari model yang benar-benar tersedia dan memilihnya:

```powershell
uv run python scripts/select_agent_model.py
```

Perintah ini menanyakan API provider (OpenAI, Groq, Anthropic, Gemini, OpenRouter, DeepSeek,
Mistral, xAI, Ollama lokal) lalu menampilkan daftar bernomor. Pilih nomor, atau ketik manual
`provider/model` bila model yang diinginkan tidak ada. Hasilnya ditulis ke `.env` sebagai
`AGENT_PROVIDER` dan `AGENT_MODEL`.

## 3. Key yang TIDAK dipakai / belum aktif

| Env | Status |
| --- | --- |
| `STRIPE_API_KEY`, `STRIPE_WEBHOOK_SECRET` | **Tidak dipakai** — router `/billing` dan `backend/routes/billing.py` sudah dihapus (project pribadi, tanpa billing). Keduanya tetap commented di `.env.example`. |
| `HF_MODEL_REPO` | Sudah dihapus bersama jalur model ML — jangan dipakai lagi |

## 4. Rekomendasi isi minimal

Supaya sistem fungsional dengan fitur inti (shorts agent + render + subtitle):

```dotenv
# WAJIB: default gratis (NVIDIA NIM)
AGENT_PROVIDER=nvidia
AGENT_MODEL=nvidia/nemotron-3.5-super-vl-120b-a12b
NVIDIA_API_KEY=nvapi-...

# Opsional
CARTESIA_API_KEY=
CARTESIA_VOICE_ID=
CAMB_API_KEY=
EXA_API_KEY=
PEXELS_API_KEY=
PINECONE_API_KEY=
HUGGINGFACEHUB_API_TOKEN=
# GROQ_API_KEY hanya cadangan transkripsi
```

Boleh ganti ke `anthropic`/`gemini`/`grok`/`deepseek`/`mistral`/`ollama`/dll asal key-nya diisi.
Yang kosong hanya mengurangi fitur; tidak menghentikan aplikasi.

## 5. Cara cek cepat

```powershell
uv run python -c "
import os
from backend.core.env import load_env
load_env('backend')
for k in ['NVIDIA','OPENAI','GROQ','EXA','PEXELS','PINECONE','HUGGINGFACEHUB','CARTESIA','CAMB']:
    key = k + ('_API_TOKEN' if k=='HUGGINGFACEHUB' else '_API_KEY')
    print(key, 'SET' if os.getenv(key,'').strip() else 'KOSONG')
"
```
