import os
import logging
import asyncio
import numpy as np
from typing import List

import httpx

logger = logging.getLogger(__name__)

OPENROUTER_KEY = os.environ.get("OPENROUTER_API_KEY", "")
OPENROUTER_BASE = os.environ.get("OPENROUTER_BASE_URL", "https://openrouter.ai/api/v1")
EMBED_MODEL = os.environ.get("EMBEDDING_MODEL", "qwen/qwen3-embedding-8b")
EMBED_DIM = 4096


async def embed_text(text: str, timeout: int = 30) -> np.ndarray:
    """Single text → 4096-d numpy array. Returns zeros on failure."""
    if not OPENROUTER_KEY or not text:
        logger.warning("embed_text: no API key or empty text, returning zeros")
        return np.zeros(EMBED_DIM, dtype=np.float32)

    try:
        async with httpx.AsyncClient(timeout=timeout) as client:
            r = await client.post(
                f"{OPENROUTER_BASE}/embeddings",
                headers={
                    "Authorization": f"Bearer {OPENROUTER_KEY}",
                    "HTTP-Referer": "https://github.com/bormotun44ik/Veins-Hack",
                    "X-Title": "Veins-Hack",
                    "Content-Type": "application/json",
                },
                json={"model": EMBED_MODEL, "input": text},
            )
            r.raise_for_status()
            data = r.json()
            vec = np.array(data["data"][0]["embedding"], dtype=np.float32)
            if vec.shape[0] != EMBED_DIM:
                logger.warning(
                    f"unexpected embedding dim {vec.shape[0]}, expected {EMBED_DIM} — returning zeros"
                )
                return np.zeros(EMBED_DIM, dtype=np.float32)
            return vec
    except Exception as e:
        logger.error(f"embed_text failed: {e}")
        return np.zeros(EMBED_DIM, dtype=np.float32)


async def embed_texts(texts: List[str]) -> List[np.ndarray]:
    """Sequential embed with rate-limiting (~60 RPM free tier)."""
    results = []
    for i, t in enumerate(texts):
        v = await embed_text(t)
        results.append(v)
        if i < len(texts) - 1:
            await asyncio.sleep(1.1)
    return results
