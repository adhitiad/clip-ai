## 2026-05-10 - Optimized N+1 Database and Vector Store operations in Clip Generation
**Learning:** Calling database save operations and vector embedding/upsert operations inside a loop for multiple items causes significant performance overhead due to repeated session setup and network roundtrips.
**Action:** Use SQLAlchemy's `add_all()` and `flush()` for batch database inserts to retrieve primary keys efficiently, and batch embedding generation with `embed_documents()` followed by a single Pinecone `upsert()` for vector stores.
