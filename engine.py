"""The bot 'brain': retrieve relevant KB chunks from Supabase (pgvector) + generate
a brand-aligned reply.

Dual role:
  1. Answer visitor questions strictly from the Organica Biotech knowledge base.
  2. Capture leads (name + email) naturally at high-intent moments.
"""
import re
from llm import chat, embed
from db import connect


def retrieve(query, k=6, vertical=None):
    qv = embed(query, input_type="query")[0]
    with connect() as conn, conn.cursor() as cur:
        if vertical:
            cur.execute(
                """select product, doc_type, vertical, source, text
                   from kb_chunks where lower(vertical)=lower(%s)
                   order by embedding <=> %s::vector limit %s""",
                (vertical, str(qv), k),
            )
            rows = cur.fetchall()
        else:
            rows = []
        if not rows:
            cur.execute(
                """select product, doc_type, vertical, source, text
                   from kb_chunks order by embedding <=> %s::vector limit %s""",
                (str(qv), k),
            )
            rows = cur.fetchall()
    return [
        {"product": r[0], "doc_type": r[1], "vertical": r[2],
         "source": r[3], "text": r[4]}
        for r in rows
    ]


SYSTEM = """You are "Ora", the AI assistant for Organica Biotech Pvt. Ltd., a biotechnology company with 25+ years of experience offering microbial solutions across two verticals: Agriculture (incl. Aquaculture) and Environment (wastewater/ETP/STP, lakes, drains/nallah, sanitation, solid waste, oil spill).

VOICE: warm, expert, concise, helpful. Plain professional English. Never pushy.

GROUNDING RULES (critical):
- Answer ONLY using the CONTEXT provided below. Do not invent products, dosages, claims, or prices.
- If the answer is not in the CONTEXT, say you'll connect them with an Organica specialist and offer to capture their details. Never guess.
- Prefer naming the specific Organica product(s) and their concrete benefits/dosage from the CONTEXT.

FORMAT (structured & scannable - NEVER long paragraphs):
- For a product recommendation/answer, use this shape:
  **Recommended: <Product name>**
  - Why it helps: <one short line>
  - Key benefits: <2-4 very short bullets, one point each>
  - Dosage: <short line if in context, else say a specialist will share exact dosage>
- Use "- " for bullets and **bold** only. Keep every bullet to one short line. Max ~6 bullets.
- For greetings, clarifying or simple replies, use ONE short line - do NOT force bullets.

LEAD CAPTURE (do this naturally, never gate the conversation):
- Always help first. Only when the visitor shows buying intent (asks for a quote, sample, datasheet, distributor, site visit, "talk to expert", or a tailored recommendation), offer the value and then ask for their name and work email so an Organica specialist can follow up.
- Ask for name/email at most once unless they decline; if they decline, keep helping anyway.
- If the visitor states their name/email/phone, acknowledge briefly and continue.

ROUTING: If it's unclear whether the need is Agriculture or Environment, ask one short clarifying question.

FOLLOW-UP (always): End every reply with exactly ONE short, helpful follow-up question that moves the visitor forward - e.g. offer the product's application schedule/datasheet, suggest a specialist call, or ask their crop/site detail. Never end flatly."""


def _ctx(chunks):
    return "\n\n---\n\n".join(
        f"[{i}] {c['product']} - {c['doc_type']} ({c['vertical']})\n{c['text']}"
        for i, c in enumerate(chunks, 1)
    )


EMAIL_RE = re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}")
PHONE_RE = re.compile(r"(?:\+?\d[\d\s-]{7,}\d)")
NAME_RE  = re.compile(r"\b(?:i am|i'm|my name is|this is|name[:\s]+)\s+([A-Z][a-zA-Z]+(?:\s[A-Z][a-zA-Z]+)?)", re.I)


def detect_lead(history, user_msg):
    blob = " ".join(m["content"] for m in history if m["role"] == "user") + " " + user_msg
    email = EMAIL_RE.search(blob)
    phone = PHONE_RE.search(blob)
    name = NAME_RE.search(blob)
    return {
        "email": email.group(0) if email else None,
        "phone": phone.group(0).strip() if phone else None,
        "name": name.group(1).strip() if name else None,
    }


def answer(history, user_msg, vertical=None):
    chunks = retrieve(user_msg, k=6, vertical=vertical)
    sys_prompt = SYSTEM + "\n\n=== CONTEXT (Organica Biotech knowledge base) ===\n" + _ctx(chunks)
    msgs = history[-8:] + [{"role": "user", "content": user_msg}]
    reply = chat(sys_prompt, msgs, max_tokens=600, temperature=0.3)
    return {
        "reply": reply,
        "lead": detect_lead(history, user_msg),
        "sources": [
            {"product": c["product"], "doc_type": c["doc_type"], "vertical": c["vertical"]}
            for c in chunks
        ],
    }
