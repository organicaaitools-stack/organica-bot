"""Organica Biotech Website Bot - backend web API.

Endpoints:
  GET  /                health/info
  GET  /demo            standalone demo page with the widget
  GET  /widget.js       the embeddable chat widget
  POST /api/chat        chat turn: retrieve + answer + persist + lead capture
  GET  /admin           password-protected leads & transcripts view
"""
import os, json, secrets, urllib.request
from pathlib import Path
from fastapi import FastAPI, Request, Response, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, FileResponse, JSONResponse
from fastapi.security import HTTPBasic, HTTPBasicCredentials

from db import connect
from engine import answer

BASE = Path(__file__).parent
ADMIN_USER = os.environ.get("ADMIN_USER", "organica")
ADMIN_PASS = os.environ.get("ADMIN_PASSWORD", "changeme")
ALLOW = os.environ.get("ALLOW_ORIGINS", "*")

app = FastAPI(title="Organica Biotech Bot")
app.add_middleware(
    CORSMiddleware,
    allow_origins=[o.strip() for o in ALLOW.split(",")] if ALLOW != "*" else ["*"],
    allow_methods=["*"], allow_headers=["*"],
)
security = HTTPBasic()


def client_ip(req: Request) -> str:
    xff = req.headers.get("x-forwarded-for")
    return (xff.split(",")[0].strip() if xff else (req.client.host if req.client else "")) or ""


def geo(ip: str) -> dict:
    if not ip or ip.startswith(("127.", "10.", "192.168.", "::1")):
        return {"ip": ip}
    try:
        u = f"http://ip-api.com/json/{ip}?fields=status,country,regionName,city"
        d = json.loads(urllib.request.urlopen(u, timeout=4).read())
        if d.get("status") == "success":
            return {"ip": ip, "city": d.get("city"),
                    "region": d.get("regionName"), "country": d.get("country")}
    except Exception:
        pass
    return {"ip": ip}


@app.get("/")
def root():
    return {"service": "organica-bot", "status": "ok"}


@app.get("/widget.js")
def widget_js():
    return FileResponse(BASE / "static" / "widget.js", media_type="application/javascript")


@app.get("/demo", response_class=HTMLResponse)
def demo():
    return (BASE / "static" / "demo.html").read_text(encoding="utf-8")


@app.post("/api/chat")
async def api_chat(req: Request):
    body = await req.json()
    session_id = (body.get("session_id") or secrets.token_hex(8))[:64]
    message = (body.get("message") or "").strip()
    history = body.get("history") or []
    page_url = (body.get("page_url") or "")[:500]
    vertical = body.get("vertical")
    if not message:
        raise HTTPException(400, "empty message")

    loc = geo(client_ip(req))
    ua = req.headers.get("user-agent", "")[:300]

    with connect() as conn, conn.cursor() as cur:
        cur.execute("select id from conversations where session_id=%s", (session_id,))
        row = cur.fetchone()
        if row:
            conv_id = row[0]
        else:
            cur.execute(
                """insert into conversations (session_id, vertical, page_url, user_agent, location)
                   values (%s,%s,%s,%s,%s) returning id""",
                (session_id, vertical, page_url, ua, json.dumps(loc)),
            )
            conv_id = cur.fetchone()[0]
        cur.execute(
            "insert into messages (conversation_id, role, content) values (%s,'user',%s)",
            (conv_id, message),
        )
        conn.commit()

    result = answer(history, message, vertical=vertical)

    with connect() as conn, conn.cursor() as cur:
        cur.execute(
            "insert into messages (conversation_id, role, content) values (%s,'assistant',%s)",
            (conv_id, result["reply"]),
        )
        ld = result["lead"]
        if ld.get("email") or ld.get("phone"):
            cur.execute("select id from leads where conversation_id=%s", (conv_id,))
            ex = cur.fetchone()
            if ex:
                cur.execute(
                    """update leads set name=coalesce(%s,name), email=coalesce(%s,email),
                       phone=coalesce(%s,phone) where id=%s""",
                    (ld.get("name"), ld.get("email"), ld.get("phone"), ex[0]),
                )
            else:
                cur.execute(
                    """insert into leads (conversation_id, name, email, phone, vertical, location)
                       values (%s,%s,%s,%s,%s,%s)""",
                    (conv_id, ld.get("name"), ld.get("email"), ld.get("phone"),
                     vertical, json.dumps(loc)),
                )
        conn.commit()

    return JSONResponse({"reply": result["reply"], "session_id": session_id,
                         "sources": result["sources"]})


def check_admin(c: HTTPBasicCredentials = Depends(security)):
    ok = secrets.compare_digest(c.username, ADMIN_USER) and secrets.compare_digest(c.password, ADMIN_PASS)
    if not ok:
        raise HTTPException(401, "unauthorized", {"WWW-Authenticate": "Basic"})
    return True


@app.get("/admin", response_class=HTMLResponse)
def admin(_: bool = Depends(check_admin)):
    with connect() as conn, conn.cursor() as cur:
        cur.execute("""select l.created_at, l.name, l.email, l.phone, l.vertical,
                              l.location, c.session_id
                       from leads l left join conversations c on c.id=l.conversation_id
                       order by l.created_at desc limit 200""")
        leads = cur.fetchall()
        cur.execute("""select c.started_at, c.session_id, c.location,
                              count(m.id) filter (where m.role='user') as q
                       from conversations c left join messages m on m.conversation_id=c.id
                       group by c.id order by c.started_at desc limit 100""")
        convs = cur.fetchall()

    def esc(x): return (str(x) if x is not None else "").replace("<", "&lt;")
    lr = "".join(
        f"<tr><td>{esc(a)}</td><td>{esc(b)}</td><td>{esc(c)}</td><td>{esc(d)}</td>"
        f"<td>{esc(e)}</td><td>{esc((f or {}).get('city'))}, {esc((f or {}).get('country'))}</td></tr>"
        for a, b, c, d, e, f, g in leads
    )
    cr = "".join(
        f"<tr><td>{esc(a)}</td><td>{esc(b)}</td><td>{esc((c or {}).get('city'))}, "
        f"{esc((c or {}).get('country'))}</td><td>{esc(d)}</td></tr>"
        for a, b, c, d in convs
    )
    return f"""<!doctype html><html><head><meta charset=utf-8>
<title>Organica Bot - Admin</title><style>
body{{font-family:Roboto,Arial,sans-serif;margin:24px;color:#1f2a14}}
h2{{color:#447838}} table{{border-collapse:collapse;width:100%;margin:10px 0 30px}}
th,td{{border:1px solid #d8e0c8;padding:6px 9px;font-size:13px;text-align:left}}
th{{background:#9DC435;color:#fff}}</style></head><body>
<h1 style="color:#447838">Organica Biotech - Bot Dashboard</h1>
<h2>Captured Leads ({len(leads)})</h2>
<table><tr><th>When</th><th>Name</th><th>Email</th><th>Phone</th><th>Vertical</th><th>Location</th></tr>{lr}</table>
<h2>Recent Conversations ({len(convs)})</h2>
<table><tr><th>Started</th><th>Session</th><th>Location</th><th>Questions</th></tr>{cr}</table>
</body></html>"""
