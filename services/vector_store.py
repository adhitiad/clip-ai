import os
from pinecone import Pinecone, ServerlessSpec
from langchain_huggingface import HuggingFaceInferenceAPIEmbeddings

# Inisialisasi API Keys
PINECONE_API_KEY = os.environ.get("PINECONE_API_KEY")
PINECONE_INDEX_NAME = os.environ.get("PINECONE_INDEX_NAME", "clip-ai-hooks")
HF_TOKEN = os.environ.get("HUGGINGFACEHUB_API_TOKEN")

pc = None
index = None
embeddings = None

def init_vector_store():
    global pc, index, embeddings
    if not PINECONE_API_KEY or not HF_TOKEN:
        print("⚠️ PINECONE_API_KEY atau HUGGINGFACEHUB_API_TOKEN belum diset. Vector Search dinonaktifkan.")
        return

    try:
        pc = Pinecone(api_key=PINECONE_API_KEY)
        
        # Cek apakah index ada
        existing_indexes = [index_info["name"] for index_info in pc.list_indexes()]
        
        if PINECONE_INDEX_NAME not in existing_indexes:
            print(f"Index {PINECONE_INDEX_NAME} tidak ditemukan, membuat index baru...")
            pc.create_index(
                name=PINECONE_INDEX_NAME,
                dimension=384, # Dimensi model all-MiniLM-L6-v2
                metric='cosine',
                spec=ServerlessSpec(cloud='aws', region='us-east-1')
            )
            
        index = pc.Index(PINECONE_INDEX_NAME)
        
        # Inisialisasi HF Embeddings
        embeddings = HuggingFaceInferenceAPIEmbeddings(
            api_key=HF_TOKEN, model_name="sentence-transformers/all-MiniLM-L6-v2"
        )
        
        print("✅ Pinecone Vector Store berhasil diinisialisasi.")
    except Exception as e:
        print(f"⚠️ Gagal inisialisasi Pinecone: {e}")

def upsert_clip_vector(clip_id: int, topic: str, title: str, desc: str):
    if not index or not embeddings: return
    text_to_embed = f"Topik: {topic}. Judul: {title}. Deskripsi: {desc}"
    
    try:
        vector = embeddings.embed_query(text_to_embed)
        index.upsert(
            vectors=[
                {
                    "id": str(clip_id),
                    "values": vector,
                    "metadata": {"clip_id": clip_id, "topic": topic}
                }
            ]
        )
    except Exception as e:
        print(f"Gagal upsert vektor: {e}")

def search_similar_clips(query: str, top_k=3):
    if not index or not embeddings: return []
    try:
        query_vector = embeddings.embed_query(query)
        result = index.query(
            vector=query_vector,
            top_k=top_k,
            include_metadata=True
        )
        
        matches = result.get("matches", [])
        return [match["metadata"]["clip_id"] for match in matches]
    except Exception as e:
        print(f"Gagal mencari vektor semantik: {e}")
        return []
