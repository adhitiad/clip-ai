"""Vector store Pinecone dengan embeddings Ollama lokal (offline).

Tidak ada pemanggilan embedding ke layanan eksternal. Model dijalankan oleh
Ollama di ``OLLAMA_HOST`` (default ``http://localhost:11434``), misalnya
``ollama pull all-minilm`` (384 dimensi, cocok dengan index lama).
"""

import os

import requests

from backend.log import logger

PINECONE_API_KEY = os.environ.get("PINECONE_API_KEY")
PINECONE_INDEX_NAME = os.environ.get("PINECONE_INDEX_NAME", "clip-ai-hooks")
OLLAMA_HOST = os.environ.get("OLLAMA_HOST", "http://localhost:11434").rstrip("/")
EMBED_MODEL = os.environ.get("OLLAMA_EMBED_MODEL", "all-minilm").strip() or "all-minilm"
VECTOR_DIMENSION = int(os.environ.get("PINECONE_DIMENSION", "384"))

pc = None
index = None
embeddings = None

EMBED_TIMEOUT = 15


class OllamaEmbeddings:
    """Bungkus REST Ollama agar API pemakaian sama seperti LangChain."""

    def embed_query(self, text: str) -> list[float]:
        response = requests.post(
            f"{OLLAMA_HOST}/api/embed",
            json={"model": EMBED_MODEL, "input": text},
            timeout=EMBED_TIMEOUT,
        )
        if response.status_code == 404:
            # Ollama lama memakai /api/embeddings.
            response = requests.post(
                f"{OLLAMA_HOST}/api/embeddings",
                json={"model": EMBED_MODEL, "prompt": text},
                timeout=EMBED_TIMEOUT,
            )
        response.raise_for_status()
        data = response.json()
        values = data.get("embeddings") or [data.get("embedding")]
        vector = values[0] if values else None
        if not isinstance(vector, list) or not vector:
            raise ValueError("Respons embedding Ollama kosong.")
        return [float(value) for value in vector]


def init_vector_store() -> None:
    global pc, index, embeddings, VECTOR_DIMENSION

    if not PINECONE_API_KEY:
        logger.warning("⚠️ PINECONE_API_KEY belum diset. Vector Search dinonaktifkan.")
        return

    try:
        from pinecone import Pinecone

        pc = Pinecone(api_key=PINECONE_API_KEY)
        existing = [item["name"] for item in pc.list_indexes()]
        if PINECONE_INDEX_NAME not in existing:
            from pinecone import ServerlessSpec

            logger.info(
                f"Index {PINECONE_INDEX_NAME} tidak ditemukan, membuat index "
                f"({VECTOR_DIMENSION} dimensi)..."
            )
            pc.create_index(
                name=PINECONE_INDEX_NAME,
                dimension=VECTOR_DIMENSION,
                metric="cosine",
                spec=ServerlessSpec(cloud="aws", region="us-east-1"),
            )
        else:
            try:
                info = pc.describe_index(PINECONE_INDEX_NAME)
                actual = getattr(info, "dimension", None)
                if isinstance(actual, int) and actual > 0:
                    VECTOR_DIMENSION = actual
            except Exception:
                pass  # Index lama tetap dipakai dengan dimensi dari env.

        index = pc.Index(PINECONE_INDEX_NAME)
        embeddings = OllamaEmbeddings()
        logger.info(
            f"✅ Pinecone aktif (index={PINECONE_INDEX_NAME}, "
            f"embed=Ollama:{EMBED_MODEL}, dim={VECTOR_DIMENSION})."
        )
    except Exception as exc:
        logger.warning(f"⚠️ Gagal inisialisasi Pinecone: {type(exc).__name__}")
        pc = index = embeddings = None


def _vector_or_none(text: str) -> list[float] | None:
    if not index or not embeddings:
        return None
    try:
        vector = embeddings.embed_query(text)
    except (requests.RequestException, ValueError, TypeError) as exc:
        logger.warning(f"[Vector] Embedding Ollama gagal: {type(exc).__name__}")
        return None
    if len(vector) != VECTOR_DIMENSION:
        logger.warning(
            f"[Vector] Dimensi embedding {len(vector)} != index {VECTOR_DIMENSION}; "
            f"cek OLLAMA_EMBED_MODEL / PINECONE_DIMENSION."
        )
        return None
    return vector


def upsert_clip_vector(clip_id: int, topic: str, title: str, desc: str) -> None:
    text_to_embed = f"Topik: {topic}. Judul: {title}. Deskripsi: {desc}"
    vector = _vector_or_none(text_to_embed)
    if vector is None:
        return
    try:
        index.upsert(
            vectors=[
                {
                    "id": str(clip_id),
                    "values": vector,
                    "metadata": {"clip_id": clip_id, "topic": topic},
                }
            ]
        )
    except Exception as exc:
        logger.warning(f"[Vector] Gagal upsert: {type(exc).__name__}")


def search_similar_clips(query: str, top_k: int = 3) -> list[int]:
    vector = _vector_or_none(query)
    if vector is None:
        return []
    try:
        result = index.query(vector=vector, top_k=top_k, include_metadata=True)
        if isinstance(result, dict):
            matches = result.get("matches", [])
        else:
            matches = getattr(result, "matches", [])
        return [match["metadata"]["clip_id"] for match in matches]
    except Exception as exc:
        logger.warning(f"[Vector] Gagal cari vektor: {type(exc).__name__}")
        return []
