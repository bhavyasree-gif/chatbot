"""Retrieve curated defensive guidance from MongoDB using local embeddings."""
import json
import math
import os
from urllib.request import Request, urlopen

from backend.services import openai_api

PLATFORMS = ("Windows", "Linux")
STAGES = ("Anticipated", "Active", "Evolving", "Resolved")
DEFAULT_EMBED_MODEL = "nomic-embed-text"


def embedding_model():
    if openai_api.selected():
        return openai_api.embedding_model()
    return os.getenv("OLLAMA_EMBED_MODEL", DEFAULT_EMBED_MODEL)


def embed(texts):
    if openai_api.selected():
        return openai_api.embed(texts)
    base = os.getenv("OLLAMA_BASE_URL", "http://127.0.0.1:11434").rstrip("/")
    request = Request(f"{base}/api/embed", method="POST",
                      headers={"Content-Type": "application/json"},
                      data=json.dumps({"model": embedding_model(), "input": texts}).encode())
    with urlopen(request, timeout=60) as response:
        vectors = json.load(response)["embeddings"]
    if len(vectors) != len(texts) or any(not vector for vector in vectors):
        raise ValueError("Embedding service returned incomplete vectors")
    return vectors


def similarity(a, b):
    if len(a) != len(b):
        return -1
    norm = math.hypot(*a) * math.hypot(*b)
    return sum(x * y for x, y in zip(a, b)) / norm if norm else -1


def retrieve(db, question, platform, stage):
    rows = list(db.threat_knowledge.find(
        {"platform": platform, "stage": stage, "embedding_model": embedding_model()},
        {"_id": 0},
    ).sort("_id", 1).limit(200))
    if not rows:
        return []
    vector, = embed([question])
    ranked = sorted(rows, key=lambda row: similarity(vector, row["embedding"]), reverse=True)
    return [{key: row[key] for key in ("title", "text", "url", "platform", "stage")}
            for row in ranked[:3] if similarity(vector, row["embedding"]) >= 0.35]
