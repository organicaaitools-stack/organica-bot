"""Embed all KB chunks once and cache to kb_index.json (the bot's searchable memory)."""
import json, sys, time
from pathlib import Path
from llm import embed, EMBED_MODEL

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

CHUNKS = Path(r"Z:\Web\_build\kb_chunks.jsonl")
INDEX  = Path(__file__).with_name("kb_index.json")
BATCH  = 32

recs = [json.loads(l) for l in CHUNKS.open(encoding="utf-8")]
print(f"Chunks to embed: {len(recs)} (model: {EMBED_MODEL})")

vectors = []
for i in range(0, len(recs), BATCH):
    batch = recs[i:i + BATCH]
    embs = embed([r["text"] for r in batch], input_type="passage")
    vectors.extend(embs)
    print(f"  embedded {min(i+BATCH,len(recs))}/{len(recs)}")
    time.sleep(0.3)

assert len(vectors) == len(recs)
out = []
for r, v in zip(recs, vectors):
    out.append({
        "id": r["id"], "vertical": r["vertical"],
        "sub_category": r["sub_category"], "product": r["product"],
        "doc_type": r["doc_type"], "source": r["source"],
        "text": r["text"], "embedding": v,
    })
INDEX.write_text(json.dumps(out), encoding="utf-8")
print(f"Wrote index: {INDEX}  ({len(out)} vectors, dim {len(out[0]['embedding'])})")
