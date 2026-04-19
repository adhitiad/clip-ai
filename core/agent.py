from utils.db import get_top_clips, get_clip_by_id
from services.vector_store import search_similar_clips

def build_few_shot_prompt_context(user_query: str):
    # 1. Cari secara komprehensif via Pinecone (Semantic Search)
    similar_ids = search_similar_clips(user_query, top_k=3)
    
    # 2. Mapping hasil vektor ke data relasional di PostgreSQL
    top_clips = []
    if similar_ids:
        for cid in similar_ids:
            clip = get_clip_by_id(int(cid))
            if clip and clip["score"] >= 0: # Hanya mencontoh yang tidak direview buruk
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
