"""Server-side OpenAI chat and embedding requests."""
import json
import os
from urllib.request import Request, urlopen


def selected():
    return os.getenv("AI_PROVIDER", "ollama").strip().lower() == "openai"


def configured():
    return bool(os.getenv("OPENAI_API_KEY", "").strip())


def chat_model():
    return os.getenv("OPENAI_MODEL", "gpt-4o-mini")


def embedding_model():
    return os.getenv("OPENAI_EMBED_MODEL", "text-embedding-3-small")


def post(path, payload):
    key = os.getenv("OPENAI_API_KEY", "").strip()
    if not key:
        raise ValueError("OPENAI_API_KEY is missing.")
    req = Request(
        f"https://api.openai.com/v1/{path}",
        method="POST",
        headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"},
        data=json.dumps(payload).encode("utf-8"),
    )
    with urlopen(req, timeout=90) as response:
        data = json.load(response)
    if not isinstance(data, dict):
        raise ValueError("OpenAI returned an invalid response")
    return data


def generate(messages, model):
    data = post("chat/completions", {"model": model, "messages": messages,
                                    "max_completion_tokens": 650})
    try:
        content = data["choices"][0]["message"]["content"]
    except (IndexError, KeyError, TypeError) as exc:
        raise ValueError("OpenAI returned an invalid chat response") from exc
    if not isinstance(content, str) or not content.strip():
        raise ValueError("OpenAI returned an empty response")
    return content.strip()


def embed(texts):
    data = post("embeddings", {"model": embedding_model(), "input": texts})
    try:
        rows = sorted(data["data"], key=lambda row: row["index"])
        vectors = [row["embedding"] for row in rows]
    except (KeyError, TypeError) as exc:
        raise ValueError("OpenAI returned invalid embeddings") from exc
    if [row["index"] for row in rows] != list(range(len(texts))) or not all(vectors):
        raise ValueError("OpenAI returned incomplete embeddings")
    return vectors
