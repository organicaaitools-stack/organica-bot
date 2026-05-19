/* Organica Biotech - chat widget with guided flow (self-contained, brand-aligned).
   Embed: <script src="https://YOUR-BACKEND/widget.js" data-api="https://YOUR-BACKEND"></script> */
(function () {
  var S = document.currentScript;
  var API = ((S && S.getAttribute("data-api")) || window.ORGANICA_API || "").replace(/\/$/, "");
  var GREEN = "#9DC435", DEEP = "#447838", OFF = "#F0EBE1";

  var sid = localStorage.getItem("ob_sid");
  if (!sid) { sid = Math.random().toString(36).slice(2) + Date.now().toString(36); localStorage.setItem("ob_sid", sid); }

  var history = [], vertical = null, open = false, flow = null;
  var state = "idle", sel = { crop: null, problem: null };

  var css = `
  #ob-launch{position:fixed;right:22px;bottom:22px;width:60px;height:60px;border-radius:50%;
   background:${GREEN};box-shadow:0 6px 20px rgba(0,0,0,.25);cursor:pointer;z-index:2147483000;
   display:flex;align-items:center;justify-content:center;transition:transform .15s}
  #ob-launch:hover{transform:scale(1.06)} #ob-launch svg{width:30px;height:30px;fill:#fff}
  #ob-panel{position:fixed;right:22px;bottom:94px;width:380px;max-width:calc(100vw - 32px);
   height:560px;max-height:calc(100vh - 120px);background:#fff;border-radius:16px;display:none;
   flex-direction:column;overflow:hidden;z-index:2147483000;box-shadow:0 12px 40px rgba(0,0,0,.28);
   font-family:Roboto,Arial,sans-serif}
  #ob-panel.ob-on{display:flex}
  #ob-head{background:${DEEP};color:#fff;padding:14px 16px;font-family:Raleway,Arial,sans-serif}
  #ob-head b{font-size:16px;display:block} #ob-head span{font-size:12px;opacity:.85}
  #ob-msgs{flex:1;overflow-y:auto;padding:14px;background:${OFF}}
  .ob-m{margin:8px 0;display:flex} .ob-m.u{justify-content:flex-end}
  .ob-b{max-width:80%;padding:10px 13px;border-radius:14px;font-size:14px;line-height:1.45;white-space:pre-wrap}
  .ob-m.a .ob-b{background:#fff;color:#1f2a14;border-bottom-left-radius:4px}
  .ob-m.u .ob-b{background:${DEEP};color:#fff;border-bottom-right-radius:4px}
  #ob-chips{padding:8px 14px;display:flex;gap:8px;flex-wrap:wrap;background:${OFF};max-height:160px;overflow-y:auto}
  .ob-chip{border:1px solid ${DEEP};color:${DEEP};background:#fff;border-radius:18px;
   padding:7px 13px;font-size:13px;cursor:pointer}
  .ob-chip:hover{background:${DEEP};color:#fff}
  #ob-foot{display:flex;border-top:1px solid #e3e3e3;padding:8px}
  #ob-in{flex:1;border:0;outline:0;font-size:14px;padding:9px;font-family:Roboto,Arial}
  #ob-send{background:${GREEN};border:0;color:#fff;border-radius:10px;padding:0 16px;cursor:pointer;font-weight:600}
  #ob-tag{font-size:10px;color:#9aa;text-align:center;padding:4px}`;
  var st = document.createElement("style"); st.textContent = css; document.head.appendChild(st);

  var L = document.createElement("div"); L.id = "ob-launch";
  L.innerHTML = '<svg viewBox="0 0 24 24"><path d="M12 3C6.5 3 2 6.8 2 11.5c0 2.5 1.3 4.7 3.4 6.2L5 21l4-2.1c.95.25 1.95.4 3 .4 5.5 0 10-3.8 10-8.5S17.5 3 12 3z"/></svg>';
  document.body.appendChild(L);

  var P = document.createElement("div"); P.id = "ob-panel";
  P.innerHTML =
    '<div id="ob-head"><b>Ask Ora</b><span>Organica Biotech - Agriculture & Environment</span></div>' +
    '<div id="ob-msgs"></div><div id="ob-chips"></div>' +
    '<div id="ob-foot"><input id="ob-in" placeholder="Type your question..." autocomplete="off"/>' +
    '<button id="ob-send">Send</button></div>' +
    '<div id="ob-tag">Powered by Organica Biotech</div>';
  document.body.appendChild(P);

  var msgs = P.querySelector("#ob-msgs"), inp = P.querySelector("#ob-in"), chipBox = P.querySelector("#ob-chips");

  function bold(parent, s) {
    s.split(/\*\*/).forEach(function (seg, i) {
      if (i % 2 === 1) { var b = document.createElement("strong"); b.textContent = seg; parent.appendChild(b); }
      else parent.appendChild(document.createTextNode(seg));
    });
  }
  function renderRich(el, text) {
    el.textContent = ""; var ul = null;
    String(text).split(/\r?\n/).forEach(function (ln) {
      var t = ln.trim();
      if (/^[-*•]\s+/.test(t)) {
        if (!ul) { ul = document.createElement("ul"); ul.style.margin = "5px 0"; ul.style.paddingLeft = "18px"; el.appendChild(ul); }
        var li = document.createElement("li"); li.style.margin = "2px 0"; bold(li, t.replace(/^[-*•]\s+/, "")); ul.appendChild(li);
      } else {
        ul = null;
        if (!t) return;
        var p = document.createElement("div"); p.style.margin = "3px 0"; bold(p, t); el.appendChild(p);
      }
    });
  }
  function add(role, text) {
    var d = document.createElement("div"); d.className = "ob-m " + (role === "user" ? "u" : "a");
    var b = document.createElement("div"); b.className = "ob-b";
    if (role === "user") b.textContent = text; else renderRich(b, text);
    d.appendChild(b); msgs.appendChild(d); msgs.scrollTop = msgs.scrollHeight; return b;
  }
  function chips(items) {
    chipBox.innerHTML = "";
    items.forEach(function (it) {
      var c = document.createElement("div"); c.className = "ob-chip"; c.textContent = it.label;
      c.onclick = it.onClick; chipBox.appendChild(c);
    });
  }
  function clearChips() { chipBox.innerHTML = ""; }

  function verticalChips() {
    chips([
      { label: "🌱 Agriculture", onClick: function () { pickVertical("Agriculture"); } },
      { label: "🌍 Environment", onClick: function () { pickVertical("Environment"); } }
    ]);
  }

  function start() {
    if (msgs.children.length) return;
    add("a", "Hi! I'm Ora from Organica Biotech. Are you looking for Agriculture or Environment solutions?");
    verticalChips();
  }

  function pickVertical(v) {
    vertical = v; add("user", v);
    var f = flow && flow[v];
    if (v === "Agriculture" && f && f.crops) {
      state = "await_crop";
      add("a", f.ask_crop);
      var items = f.crops.map(function (c) {
        return { label: c.label, onClick: function () { pickCrop(c); } };
      });
      items.push({ label: f.other_crop_label, onClick: function () { otherCrop(); } });
      chips(items);
    } else {
      state = "chat"; clearChips();
      sendToBot("I'm interested in " + v + " solutions.");
    }
  }

  function pickCrop(c) {
    sel.crop = c.key; add("user", c.label.replace(/^[^\w]+/, "").trim() || c.key);
    var f = flow[vertical];
    state = "await_problem";
    add("a", f.ask_problem.replace("{crop}", sel.crop));
    var items = (c.problems || []).map(function (p) {
      return { label: p, onClick: function () { pickProblem(p); } };
    });
    items.push({ label: f.other_problem_label, onClick: function () { otherProblem(); } });
    chips(items);
  }

  function otherCrop() {
    var f = flow[vertical]; state = "await_custom_crop"; clearChips();
    add("a", f.other_crop_prompt); inp.focus();
  }
  function otherProblem() {
    var f = flow[vertical]; state = "await_custom_problem"; clearChips();
    add("a", f.other_problem_prompt); inp.focus();
  }

  function pickProblem(p) {
    sel.problem = p; add("user", p); recommend();
  }

  function recommend() {
    state = "chat"; clearChips();
    var q = "I grow " + sel.crop + ". The problem I'm facing is: " + sel.problem +
            ". Please recommend the right Organica product with key benefits and dosage.";
    sendToBot(q, true);
  }

  function sendToBot(text, silent) {
    if (!silent) add("user", text);
    history.push({ role: "user", content: text });
    var tb = add("a", "…");
    fetch(API + "/api/chat", {
      method: "POST", headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ session_id: sid, message: text, history: history.slice(0, -1),
        page_url: location.href, vertical: vertical })
    }).then(function (r) { return r.json(); }).then(function (d) {
      renderRich(tb, d.reply || "Sorry, something went wrong.");
      history.push({ role: "assistant", content: d.reply || "" });
      msgs.scrollTop = msgs.scrollHeight;
    }).catch(function () { tb.textContent = "Connection error. Please try again."; });
  }

  function onUserText() {
    var t = inp.value.trim(); if (!t) return; inp.value = "";
    if (state === "await_custom_crop") {
      sel.crop = t; add("user", t); state = "await_problem_text";
      add("a", (flow[vertical].ask_problem).replace("{crop}", t));
      return;
    }
    if (state === "await_custom_problem" || state === "await_problem_text") {
      sel.problem = t; add("user", t); recommend(); return;
    }
    add("user", t); sendToBot(t, true);
  }

  L.onclick = function () { open = !open; P.classList.toggle("ob-on", open); if (open) start(); };
  P.querySelector("#ob-send").onclick = onUserText;
  inp.addEventListener("keydown", function (e) { if (e.key === "Enter") onUserText(); });

  fetch(API + "/api/flow").then(function (r) { return r.json(); })
    .then(function (f) { flow = f; }).catch(function () { flow = {}; });
})();
