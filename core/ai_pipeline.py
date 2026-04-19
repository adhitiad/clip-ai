import os
from groq import Groq
from langchain_groq import ChatGroq
from langchain_huggingface import HuggingFaceEndpoint
from langchain_core.prompts import PromptTemplate
from langchain_core.output_parsers import JsonOutputParser
from pydantic import BaseModel, Field

# Inisialisasi API Keys
GROQ_API_KEY = os.environ.get("GROQ_API_KEY")
HF_TOKEN = os.environ.get("HUGGINGFACEHUB_API_TOKEN")

# Standar Client Groq untuk Audio
groq_client = Groq(api_key=GROQ_API_KEY)


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
    print("1. Mentranskrip audio dengan Groq Whisper (Super Cepat)...")
    with open(audio_path, "rb") as file:
        transcription = groq_client.audio.transcriptions.create(
            file=(audio_path, file.read()),
            model="whisper-large-v3",
            response_format="verbose_json",
        )
    return transcription.text


# --- FASE 2: CARI HOOK (LANGCHAIN + GROQ LLM) ---
def find_hooks_with_groq(transcript_text: str):
    print("2. Menganalisis Hook dengan LangChain & Groq (Llama-3)...")

    # Menggunakan LLM dari Groq via LangChain
    llm = ChatGroq(model="llama3-70b-8192", temperature=0.7, api_key=GROQ_API_KEY)

    parser = JsonOutputParser(pydantic_object=HookSchema)

    prompt = PromptTemplate(
        template="""Anda adalah ahli konten viral. Analisis transkrip video bola berikut.
        Temukan 2 momen paling penuh aksi, emosi, atau konflik (bola fighting) berdurasi 30-60 detik.
        
        Transkrip: {transcript}
        
        {format_instructions}
        """,
        input_variables=["transcript"],
        partial_variables={"format_instructions": parser.get_format_instructions()},
    )

    chain = prompt | llm | parser

    try:
        hooks = chain.invoke({"transcript": transcript_text})
        return hooks if isinstance(hooks, list) else [hooks]
    except Exception as e:
        print(f"Error parsing Groq: {e}")
        return []


# --- FASE 3: TERJEMAHAN GLOBAL (LANGCHAIN + HUGGING FACE) ---
def translate_metadata_with_hf(hooks: list):
    print("3. Menerjemahkan ke Bahasa Inggris dengan Hugging Face (Pengganti DeepL)...")

    # Menggunakan model spesifik penerjemah dari Hugging Face Hub (Gratis)
    hf_translator = HuggingFaceEndpoint(
        repo_id="Helsinki-NLP/opus-mt-id-en",  # Model spesifik Indo ke English
        task="translation",
        max_new_tokens=512,
        huggingfacehub_api_token=HF_TOKEN,
    )

    for hook in hooks:
        # Terjemahkan Judul
        eng_title = hf_translator.invoke(hook["title_id"])
        # Terjemahkan Deskripsi
        eng_desc = hf_translator.invoke(hook["desc_id"])

        # Tambahkan ke dictionary
        hook["title_en"] = eng_title.strip()
        hook["desc_en"] = eng_desc.strip()

    return hooks


# --- FUNGSI UTAMA UNTUK DI PANGGIL OLEH FASTAPI ---
def process_video_ai_logic(audio_path: str):
    # 1. Transkripsi via Groq
    transcript = get_transcript(audio_path)

    # 2. Cari momen viral via Groq + Langchain
    hooks = find_hooks_with_groq(transcript)

    # 3. Terjemahkan metadata via Hugging Face + Langchain
    final_metadata = translate_metadata_with_hf(hooks)

    return final_metadata
