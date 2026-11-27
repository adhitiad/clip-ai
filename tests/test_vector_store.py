"""Vector store: embeddings Ollama lokal, tanpa token Hugging Face."""

import pytest
import requests

from backend.services import vector_store as vs

DIM = 384


class FakeResponse:
    def __init__(self, status_code=200, data=None):
        self.status_code = status_code
        self.data = data or {}

    def raise_for_status(self):
        if self.status_code >= 400:
            raise requests.HTTPError(str(self.status_code))

    def json(self):
        return self.data


@pytest.fixture(autouse=True)
def restore_globals():
    old = (vs.pc, vs.index, vs.embeddings, vs.VECTOR_DIMENSION)
    yield
    vs.pc, vs.index, vs.embeddings, vs.VECTOR_DIMENSION = old


def test_embed_query_uses_ollama(monkeypatch):
    calls = []

    def fake_post(url, json=None, timeout=None):
        calls.append((url, json))
        return FakeResponse(data={"embeddings": [[0.1] * DIM]})

    monkeypatch.setattr(vs.requests, "post", fake_post)
    vector = vs.OllamaEmbeddings().embed_query("hook")
    assert len(vector) == DIM
    assert calls[0][0].endswith("/api/embed")
    assert calls[0][1]["model"] == vs.EMBED_MODEL


def test_embed_query_falls_back_to_legacy_endpoint(monkeypatch):
    urls = []

    def fake_post(url, json=None, timeout=None):
        urls.append(url)
        if url.endswith("/api/embed"):
            return FakeResponse(status_code=404)
        return FakeResponse(data={"embedding": [0.2] * DIM})

    monkeypatch.setattr(vs.requests, "post", fake_post)
    assert len(vs.OllamaEmbeddings().embed_query("hook")) == DIM
    assert urls[-1].endswith("/api/embeddings")


def test_init_works_without_huggingface_token(monkeypatch):
    class FakePinecone:
        last = None

        def __init__(self, api_key):
            self.api_key = api_key

        def list_indexes(self):
            return []

        def create_index(self, **kwargs):
            FakePinecone.last = kwargs

        def Index(self, _name):
            return object()

    monkeypatch.setattr(vs, "PINECONE_API_KEY", "dummy-key")
    monkeypatch.setattr(vs, "PINECONE_INDEX_NAME", "clip-ai-hooks")
    monkeypatch.setattr(vs, "VECTOR_DIMENSION", DIM)
    monkeypatch.setattr("pinecone.Pinecone", FakePinecone)
    monkeypatch.setattr("pinecone.ServerlessSpec", lambda **kwargs: kwargs)

    vs.init_vector_store()
    assert isinstance(vs.embeddings, vs.OllamaEmbeddings)
    assert FakePinecone.last["dimension"] == DIM


def test_search_and_upsert_use_ollama_vector(monkeypatch):
    class FakeEmbeddings:
        def embed_query(self, _text):
            return [0.3] * DIM

    class FakeIndex:
        def __init__(self):
            self.upserted = None

        def upsert(self, vectors):
            self.upserted = vectors

        def query(self, **kwargs):
            assert len(kwargs["vector"]) == DIM
            return {"matches": [{"metadata": {"clip_id": 7}}]}

    fake_index = FakeIndex()
    vs.index = fake_index
    vs.embeddings = FakeEmbeddings()
    vs.VECTOR_DIMENSION = DIM

    vs.upsert_clip_vector(7, "topic", "title", "desc")
    assert fake_index.upserted[0]["id"] == "7"
    assert vs.search_similar_clips("hook") == [7]


def test_dimension_mismatch_is_skipped(monkeypatch):
    class FakeEmbeddings:
        def embed_query(self, _text):
            return [0.1] * 12

    vs.index = object()
    vs.embeddings = FakeEmbeddings()
    vs.VECTOR_DIMENSION = DIM
    assert vs.search_similar_clips("hook") == []
