"""Provider-agnostic LLM + embedding layer.

Swap providers by changing env vars only (NVIDIA free now -> Claude later).
No SDK dependency: plain HTTPS so it runs anywhere with zero install.
"""
import os, json, time, urllib.request, urllib.error
from pathlib import Path

def _load_env():
    p = Path(__file__).with_name(".env")
    if p.exists():
        for line in p.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, v = line.split("=", 1)
                os.environ.setdefault(k.strip(), v.strip())

_load_env()

PROVIDER   = os.environ.get("LLM_PROVIDER", "nvidia")
NV_KEY     = os.environ.get("NVIDIA_API_KEY", "")
NV_BASE    = os.environ.get("NVIDIA_BASE_URL", "https://integrate.api.nvidia.com/v1")
CHAT_MODEL = os.environ.get("LLM_CHAT_MODEL", "meta/llama-3.3-70b-instruct")
EMBED_MODEL= os.environ.get("LLM_EMBED_MODEL", "nvidia/nv-embedqa-e5-v5")
EMBED_DIM  = int(os.environ.get("LLM_EMBED_DIM", "1024"))

# Claude config (used when LLM_PROVIDER=anthropic in Phase 2)
ANTHROPIC_KEY   = os.environ.get("ANTHROPIC_API_KEY", "")
ANTHROPIC_MODEL = os.environ.get("ANTHROPIC_MODEL", "claude-sonnet-4-6")


def _post(url, payload, headers, timeout=60, retries=3):
    data = json.dumps(payload).encode()
    last = None
    for attempt in range(retries):
        try:
            req = urllib.request.Request(url, data=data, headers=headers)
            with urllib.request.urlopen(req, timeout=timeout) as r:
                return json.loads(r.read())
        except urllib.error.HTTPError as e:
            body = e.read().decode()[:300]
            last = f"HTTP {e.code}: {body}"
            if e.code in (429, 500, 502, 503):
                time.sleep(2 * (attempt + 1)); continue
            raise RuntimeError(last)
        except Exception as e:
            last = f"{type(e).__name__}: {e}"
            time.sleep(2 * (attempt + 1))
    raise RuntimeError(f"request failed after {retries} tries: {last}")


def embed(texts, input_type="passage"):
    """Return list[list[float]] embeddings. input_type: 'passage' (docs) or 'query'."""
    if isinstance(texts, str):
        texts = [texts]
    if PROVIDER == "nvidia":
        out = _post(
            NV_BASE + "/embeddings",
            {"model": EMBED_MODEL, "input": texts,
             "input_type": input_type, "encoding_format": "float"},
            {"Authorization": "Bearer " + NV_KEY, "Content-Type": "application/json"},
        )
        return [d["embedding"] for d in out["data"]]
    raise NotImplementedError(f"embed not implemented for provider {PROVIDER}")


def chat(system, messages, max_tokens=700, temperature=0.3):
    """messages: list of {role, content}. Returns assistant text."""
    if PROVIDER == "nvidia":
        out = _post(
            NV_BASE + "/chat/completions",
            {"model": CHAT_MODEL,
             "messages": [{"role": "system", "content": system}] + messages,
             "max_tokens": max_tokens, "temperature": temperature},
            {"Authorization": "Bearer " + NV_KEY, "Content-Type": "application/json"},
        )
        return out["choices"][0]["message"]["content"].strip()

    if PROVIDER == "anthropic":
        out = _post(
            "https://api.anthropic.com/v1/messages",
            {"model": ANTHROPIC_MODEL, "system": system,
             "messages": messages, "max_tokens": max_tokens,
             "temperature": temperature},
            {"x-api-key": ANTHROPIC_KEY,
             "anthropic-version": "2023-06-01",
             "Content-Type": "application/json"},
        )
        return "".join(b.get("text", "") for b in out["content"]).strip()

    raise NotImplementedError(f"chat not implemented for provider {PROVIDER}")
