import numpy as np
from pydantic import BaseModel, Field

from backend.core.models import ShortsClipPlan as ShortsClipData
from backend.core.models import ShortsPlan as ShortsPlanData
from backend.services.vector_store import search_similar_clips
from backend.utils.db import get_clip_by_id, get_top_clips


class ShortsClipPlan(BaseModel):
    """Satu segmen short/reel/tiktok yang siap dirender."""

    start_time: int = Field(ge=0, description="Detik mulai dari video sumber")
    end_time: int = Field(gt=0, description="Detik selesai dari video sumber")
    hook: str = Field(description="Kalimat pembuka 1-2 detik pertama")
    title: str = Field(description="Judul overlay maksimal 8 kata")
    caption: str = Field(description="Naskah/teks pendek di layar")
    hashtags: list[str] = Field(default_factory=list)
    thumbnail_path: str | None = Field(
        default=None, description="Path file thumbnail (di-generate saat render)"
    )
    thumbnail_url: str | None = Field(
        default=None, description="URL publik thumbnail (diisi frontend)"
    )


class ShortsPlan(BaseModel):
    """Rencana lengkap agent shorts/reels/tiktok (tanpa training model)."""

    platform: str
    topic: str
    clips: list[ShortsClipPlan]
    style_notes: str = ""


def build_few_shot_prompt_context(user_query: str):
    # 1. Cari secara komprehensif via Pinecone (Semantic Search)
    similar_ids = search_similar_clips(user_query, top_k=3)

    # 2. Mapping hasil vektor ke data relasional di PostgreSQL
    top_clips = []
    if similar_ids:
        for cid in similar_ids:
            clip = get_clip_by_id(int(cid))
            if clip and clip["score"] >= 0:  # Hanya mencontoh yang tidak direview buruk
                top_clips.append(clip)

    # 3. Fallback: Jika Pinecone belum punya data atau error, gunakan skor tertinggi global
    if not top_clips:
        top_clips = get_top_clips(limit=3)

    if not top_clips:
        return "Belum ada contoh masa lalu. Lakukan yang terbaik sesuai insting analitis Anda."

    context = "Berikut adalah contoh momen terbaik yang dinilai sukses tinggi di masa lalu dan SANGAT RELEVAN dengan topik saat ini. Gunakan sebagai PENGALAMAN BELAJAR:\n\n"
    for idx, c in enumerate(top_clips, 1):
        context += f"💡 Contoh Sukses {idx}:\n- Topik Relevan: {c['topic']}\n- Judul yang Menarik: {c['title']}\n- Deskripsi Detail: {c['desc']}\n"

    context += "\nPelajari pola kesuksesan di atas (seperti panjang judul, gaya penulisan, dan pemicu emosi hashtag) untuk momen yang akan Anda analisis berikut ini.\n"
    return context


def agent_llm(
    interactive: bool = True,
    provider: str | None = None,
    model: str | None = None,
):
    """
    Return a LangChain ChatModel untuk agent-grade work (short/reel/tiktok
    research & copy). Model ditemukan via langchain_* terpasang + catalog
    statik; input manual bila interactif dan tidak ada yang ditemukan.
    """
    from backend.services.model_discovery import select_chat_model

    return select_chat_model(interactive=interactive, provider=provider, model=model)


def build_shorts_prompt(
    topic: str,
    platform: str,
    few_shot: str,
    max_clips: int,
    target_language: str,
    transcript: str = "",
) -> str:
    """Buat prompt plan short/reel/tiktok (murni, tanpa LLM/network).

    Prompt sekarang menuntun LLM agar hasil judul/deskripsi/hook:
    - relevan dengan topik (tidak clickbait bohong),
    - berhenti-scroll di 1,5 detik pertama,
    - memicu like, komentar, dan subscribe/follow.
    """
    language = {"id": "Bahasa Indonesia", "en": "English"}.get(
        target_language, target_language
    )
    return (
        "Kamu adalah editor short-form video (TikTok/Reels/YouTube Shorts) "
        "yang ahli membuat video yang bagus, selesai ditonton, dan "
        "mengundang interaksi penonton.\n"
        f"Platform: {platform}. Bahasa: {language}. Topik: {topic}.\n"
        f"Maksimal {max_clips} klip. Setiap klip 7-30 detik, beri hook kuat "
        "di 1,5 detik pertama, judul overlay ≤8 kata, caption pendek, dan "
        "hashtag relevan.\n"
        "PENTING: tiap klip harus punya:\n"
        "1. Judul yang relevan & ingin di-klik (jangan bohong soal isi video).\n"
        "2. Deskripsi yang mengajak penonton like, komentar, dan "
        "subscribe/follow (contoh: 'Like jika setuju! Komentar pendapatmu.')\n"
        "3. Hashtag relevan dengan topik.\n"
        "Hindari klaim seksual/kekerasan/hoaks.\n"
        f"Contoh performa masa lalu:\n{few_shot}\n"
        f"Transkrip sumber (boleh kosong):\n{transcript[:6000]}\n"
        "Keluarkan JSON sesuai skema ShortsPlan."
    )


def to_dataclass(plan: ShortsPlan) -> ShortsPlanData:
    """Konversi hasil LLM (Pydantic) → model internal @dataclass."""
    return ShortsPlanData(
        platform=plan.platform,
        topic=plan.topic,
        clips=tuple(
            ShortsClipData(
                start_time=clip.start_time,
                end_time=clip.end_time,
                hook=clip.hook,
                title=clip.title,
                caption=clip.caption,
                hashtags=tuple(clip.hashtags),
                thumbnail_path=clip.thumbnail_path,
                thumbnail_url=clip.thumbnail_url,
            )
            for clip in plan.clips
        ),
        style_notes=plan.style_notes,
    )


def clip_duration_stats(plan: ShortsPlanData) -> dict:
    """Statistik durasi klip memakai numpy."""
    durations = np.array(
        [clip.end_time - clip.start_time for clip in plan.clips], dtype=float
    )
    if durations.size == 0:
        return {"mean": 0.0, "min": 0.0, "max": 0.0}
    return {
        "mean": float(np.mean(durations)),
        "min": float(np.min(durations)),
        "max": float(np.max(durations)),
    }


def plan_shorts(
    topic: str,
    platform: str = "shorts",
    max_clips: int = 3,
    target_language: str = "id",
    few_shot: str = "",
    transcript: str = "",
    provider: str | None = None,
    model: str | None = None,
) -> ShortsPlanData:
    """
    Rancang hook/script/caption via LangChain LLM (tanpa training model).
    Provider/model diambil dari argumen, lalu env AGENT_*/discovery.
    """
    from langchain_core.output_parsers import JsonOutputParser
    from langchain_core.prompts import PromptTemplate

    llm = agent_llm(interactive=False, provider=provider, model=model)
    prompt = build_shorts_prompt(
        topic, platform, few_shot, max_clips, target_language, transcript
    )
    try:
        parsed = llm.with_structured_output(ShortsPlan).invoke(prompt)
    except AttributeError, NotImplementedError, ValueError:
        parser = JsonOutputParser(pydantic_object=ShortsPlan)
        template = PromptTemplate(
            template="{query}\n{format_instructions}",
            input_variables=["query"],
            partial_variables={"format_instructions": parser.get_format_instructions()},
        )
        parsed = ShortsPlan.model_validate(
            (template | llm | parser).invoke({"query": prompt})
        )
    # Model boleh saja mengembalikan lebih banyak klip dari yang diminta.
    if len(parsed.clips) > max_clips:
        parsed.clips = parsed.clips[:max_clips]
    return to_dataclass(parsed)
