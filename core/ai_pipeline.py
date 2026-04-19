import os
from groq import Groq
from langchain_groq import ChatGroq
from langchain_huggingface import HuggingFaceEndpoint
from langchain_core.prompts import PromptTemplate
from langchain_core.output_parsers import JsonOutputParser
from pydantic import BaseModel, Field

from core.agent import build_few_shot_prompt_context

from log import logger

# Inisialisasi API Keys
GROQ_API_KEY = os.environ.get("GROQ_API_KEY")
HF_TOKEN = os.environ.get("HUGGINGFACEHUB_API_TOKEN")

# Standar Client Groq untuk Audio
groq_client = Groq(api_key=GROQ_API_KEY) if GROQ_API_KEY else None


# --- SKEMA DATA LANGCHAIN ---
class HookSchema(BaseModel):
    start_time: int = Field(description="Detik mulai klip")
    end_time: int = Field(description="Detik selesai klip")
    title_id: str = Field(description="Judul viral TikTok/Reels dalam Bahasa Indonesia")
    desc_id: str = Field(
        description="Deskripsi singkat + hashtag dalam Bahasa Indonesia"
    )


# --- FASE 1: TRANSKRIPSI (GROQ WHISPER) ---
def get_transcript(audio_path: str) -> str:
    if not groq_client:
        return ""
    logger.info("1. Mentranskrip audio dengan Groq Whisper (Super Cepat)...")
    with open(audio_path, "rb") as file:
        transcription = groq_client.audio.transcriptions.create(
            file=(audio_path, file.read()),
            model="whisper-large-v3",
            response_format="verbose_json",
        )
    return transcription.text


# --- FASE 2: CARI HOOK (LANGCHAIN + GROQ LLM) ---
def find_hooks_with_groq(transcript_text: str, user_query: str):
    logger.info(
        f"2. Menganalisis Hook untuk topik: '{user_query}' MENGGUNAKAN Continuous Learning..."
    )

    llm = ChatGroq(model="llama3-70b-8192", temperature=0.7, api_key=GROQ_API_KEY)
    parser = JsonOutputParser(pydantic_object=HookSchema)

    # Ambil konteks belajar terbaru via Semantic Search Pinecone
    learning_context = build_few_shot_prompt_context(user_query)

    # Prompt dinamis dengan {user_query} dan konteks
    prompt = PromptTemplate(
        template="""Anda adalah agen AI yang terus belajar menjadi ahli konten viral. Analisis transkrip video berikut.
        Topik pencarian pengguna: "{user_query}"
        
        {learning_context}
        
        Temukan 2 momen paling menarik berdurasi 30-60 detik yang PALING RELEVAN dengan topik tersebut.
        
        Transkrip: {transcript}
        
        {format_instructions}
        """,
        input_variables=["transcript", "user_query"],
        partial_variables={
            "format_instructions": parser.get_format_instructions(),
            "learning_context": learning_context,
        },
    )

    chain = prompt | llm | parser

    try:
        hooks = chain.invoke({"transcript": transcript_text, "user_query": user_query})
        return hooks if isinstance(hooks, list) else [hooks]
    except Exception as e:
        logger.error(f"Error parsing Groq: {e}")
        return []


# --- FASE 3: TERJEMAHAN GLOBAL (LANGCHAIN + HUGGING FACE) ---
def translate_metadata_with_hf(hooks: list):
    logger.info(
        "3. Menerjemahkan ke Bahasa Inggris dengan Hugging Face (Pengganti DeepL)..."
    )

    # Menggunakan model spesifik penerjemah dari Hugging Face Hub (Gratis)
    hf_translator = HuggingFaceEndpoint(
        repo_id="Helsinki-NLP/opus-mt-id-en",  # Model spesifik Indo ke English
        task="translation",
        max_new_tokens=512,
        huggingfacehub_api_token=HF_TOKEN,
        temperature=0.2,
    )

    for hook in hooks:
        try:
            # Terjemahkan Judul
            eng_title = hf_translator.invoke(hook["title_id"])
            # Terjemahkan Deskripsi
            eng_desc = hf_translator.invoke(hook["desc_id"])

            # Tambahkan ke dictionary
            hook["title_en"] = eng_title.strip()
            hook["desc_en"] = eng_desc.strip()
        except Exception as e:
            logger.error(f"Format HF eror saat menerjemahkan: {str(e)[:50]}")
            hook["title_en"] = hook["title_id"]
            hook["desc_en"] = hook["desc_id"]

    return hooks


# --- FUNGSI UTAMA UNTUK DI PANGGIL OLEH FASTAPI ---
def process_video_ai_logic(
    audio_path: str,
    user_query: str,
    transcript_text: str = "",
    use_ml_filter: bool = True,
    ml_threshold: float = 6.5,
):
    """
    Pipeline AI utama:
      1. Transkripsi (Groq Whisper)
      2. Temukan hook (LangChain + Groq LLaMA)
      3. Terjemahkan (HuggingFace)
      4. Hitung viral score (Groq LLM)
      5. [NEW] Filter ML — hanya klip skor >= threshold yang lolos
    """
    # Jika transcript_text sudah didapat dari YouTube VTT, lewati Groq Whisper
    if not transcript_text and audio_path:
        transcript_text = get_transcript(audio_path)

    hooks = find_hooks_with_groq(transcript_text, user_query)
    translated_metadata = translate_metadata_with_hf(hooks)

    from utils.ai_extras import calculate_viral_score

    scored_metadata = [calculate_viral_score(hook) for hook in translated_metadata]

    # ML Viral Filter — skip klip yang diprediksi tidak viral
    if use_ml_filter and scored_metadata:
        try:
            from services.viral_predictor import batch_predict_and_filter

            final_metadata = batch_predict_and_filter(
                clips=scored_metadata,
                audio_path=audio_path,
                threshold=ml_threshold,
                always_keep_best=1,
            )
        except Exception as e:
            logger.error(f"[ViralML] Filter error (skip filter): {e}")
            final_metadata = scored_metadata
    else:
        final_metadata = scored_metadata

    return final_metadata
