"""Create schema and load the 376 KB vectors into Supabase. Run once string is set."""
import json, sys
from pathlib import Path
from db import connect

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

INDEX  = Path(__file__).with_name("kb_index.json")
SCHEMA = Path(__file__).with_name("schema.sql")

def main():
    rows = json.loads(INDEX.read_text(encoding="utf-8"))
    print(f"Loading {len(rows)} chunks...")
    with connect() as conn, conn.cursor() as cur:
        cur.execute(SCHEMA.read_text(encoding="utf-8"))
        cur.execute("truncate kb_chunks;")
        for r in rows:
            cur.execute(
                """insert into kb_chunks
                   (id, vertical, sub_category, product, doc_type, source, text, embedding)
                   values (%s,%s,%s,%s,%s,%s,%s,%s)""",
                (r["id"], r["vertical"], r["sub_category"], r["product"],
                 r["doc_type"], r["source"], r["text"], str(r["embedding"])),
            )
        conn.commit()
        cur.execute("select count(*), count(distinct product) from kb_chunks;")
        n, p = cur.fetchone()
    print(f"Done. kb_chunks rows={n}, distinct products={p}")

if __name__ == "__main__":
    main()
