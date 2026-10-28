/* AuthAssist web app: landing, demo sign-in, workspace. Vanilla JS, hash routing, no build step. */
"use strict";

const $root = document.getElementById("root");
const S = { cfg: null, user: null, caseId: "case_04", payer: null, live: false, result: null, letter: null, pdf: null, letterTraces: [], tab: "criteria", busy: false };
const ROLE_ICON = { vision: "👁️", fast: "⚡", reasoning: "🧠", tavily: "🔎", code: "⚙️" };
const STATUS = { ready: ["Ready to submit", "#16a34a"], needs_attention: ["Needs attention", "#d29922"], not_ready: ["Not ready", "#dc2626"] };
const EXAMPLE_ADDENDA = {
  symptom_duration: "Low back pain for 9 weeks.",
  conservative_therapy: "Completed 8 weeks of physical therapy from 08/20/2026 to 10/15/2026 with minimal improvement.",
  neuro_exam: "Neuro exam: strength 5/5, reflexes 2+ symmetric, sensation intact, negative straight leg raise.",
  prior_imaging: "No prior lumbar imaging.",
};
const LOGO = `<span class="logo-mark"><svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="#fff" stroke-width="3" stroke-linecap="round" stroke-linejoin="round"><path d="M5 13l4 4L19 7"/></svg></span>`;

/* ---------------------------------------------------------------- utils */
const esc = (s) => String(s ?? "").replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
const $ = (sel, el = document) => el.querySelector(sel);
const $$ = (sel, el = document) => [...el.querySelectorAll(sel)];
const store = {
  get(k, area = localStorage) { try { return JSON.parse(area.getItem(k)); } catch { return null; } },
  set(k, v, area = localStorage) { try { area.setItem(k, JSON.stringify(v)); } catch { /* storage unavailable */ } },
  del(k, area = localStorage) { try { area.removeItem(k); } catch { /* ignore */ } },
};
function toast(msg) {
  const t = document.createElement("div");
  t.className = "toast"; t.textContent = msg; document.body.appendChild(t);
  setTimeout(() => t.remove(), 5000);
}
function go(path) { location.hash = "#/" + path; }
function persist() { store.set("aa_session", { caseId: S.caseId, payer: S.payer, result: S.result, letter: S.letter, letterTraces: S.letterTraces }, sessionStorage); }
function restore() {
  S.user = store.get("aa_user");
  const s = store.get("aa_session", sessionStorage);
  if (s) Object.assign(S, s);
}

/* ---------------------------------------------------------------- shared svg + helpers */
function ring(score, color, size = 120, label = "") {
  const r = 52, c = 2 * Math.PI * r, d = (c * score) / 100;
  return `<div style="text-align:center"><svg width="${size}" height="${size}" viewBox="0 0 130 130">
    <circle cx="65" cy="65" r="${r}" fill="none" stroke="rgba(128,128,128,.22)" stroke-width="12"/>
    <circle cx="65" cy="65" r="${r}" fill="none" stroke="${color}" stroke-width="12" stroke-linecap="round" stroke-dasharray="${d.toFixed(1)} ${c.toFixed(1)}" transform="rotate(-90 65 65)"/>
    <text x="65" y="74" text-anchor="middle" font-size="36" font-weight="800" fill="${color}">${score}</text></svg>
    ${label ? `<div style="font-weight:700;color:${color};margin-top:-.2rem">${label}</div>` : ""}</div>`;
}
const fmtSecs = (ms) => (ms / 1000).toFixed(1) + "s";
function requiredSet(a) {
  const excused = a.red_flag_bypass ? S.cfg.bypass_excuses : [];
  const crit = Object.fromEntries(a.criteria.map((c) => [c.id, c]));
  const required = a.results.filter((r) => !crit[r.criterion_id].bypass_group).map((r) => [crit[r.criterion_id], r]);
  const flags = a.results.filter((r) => crit[r.criterion_id].bypass_group).map((r) => [crit[r.criterion_id], r]);
  const counted = required.filter(([c]) => !excused.includes(c.category));
  const gaps = counted.filter(([, r]) => r.status !== "met");
  return { crit, excused, required, flags, counted, gaps };
}

/* ---------------------------------------------------------------- landing */
function landing() {
  const feats = [
    ["👁️", "Reads faxed notes", "Nemotron vision turns a scanned fax into clean text, with about 99% character accuracy on our test faxes."],
    ["🔎", "Finds the live policy", "Tavily searches and extracts the insurer's own medical policy, so criteria come from the source, with a link."],
    ["🛡️", "Proves every quote", "Each piece of evidence is checked word-for-word against the note in code. Made-up quotes are downgraded automatically."],
    ["🎯", "Scores readiness in code", "The 0-100 score is plain arithmetic over verified criteria. It is never a number the model invented."],
    ["🩹", "Closes the gaps", "Add what's missing as a clinician addendum and re-check in seconds. Watch the score climb."],
    ["📄", "Drafts the letter", "A letter of medical necessity plus a request PDF with the checklist. A draft for a clinician to review and sign."],
  ];
  const steps = [
    ["Pick a note", "A typed note or a scanned fax."],
    ["Review the score", "Every policy criterion, with evidence you can verify."],
    ["Fill the gaps", "Add the missing documentation and re-check."],
    ["Get the letter", "Download the letter and request PDF."],
  ];
  const note = `HPI: 54-year-old with low back pain for <mark class="met">9 weeks</mark>.
Completed <mark class="met">8 weeks of physical therapy</mark> with
minimal improvement. NSAIDs trialed.
Exam: <mark class="met">strength 5/5, reflexes 2+ symmetric</mark>.
<mark class="missing">No documented prior lumbar imaging.</mark>`;
  return `
  <header class="nav"><div class="wrap">
    <a class="logo" href="#/">${LOGO} AuthAssist</a>
    <div class="links"><a data-scroll="features">Features</a><a data-scroll="how">How it works</a><a data-scroll="proof">Results</a></div>
    <div class="spacer"></div>
    <a class="btn ghost sm" href="#/login">Sign in</a><a class="btn primary sm" href="#/login">Try the demo</a>
  </div></header>
  <section class="hero"><div class="wrap">
    <div>
      <span class="pill">NVIDIA Nemotron · Nebius Token Factory · Tavily</span>
      <h1>Catch the missing evidence <em>before</em> the insurer does.</h1>
      <p class="lead">Check a clinical note against the payer's current policy, see exactly what's missing, fix it, and draft the prior-authorization letter. For MRI lumbar spine (CPT 72148).</p>
      <div class="cta-row"><a class="btn primary lg" href="#/login">Try the live demo →</a><a class="btn lg" data-scroll="how">See how it works</a></div>
      <div class="trust"><span>Every quote verified</span><span>Score computed in code</span><span>Never submits to insurers</span></div>
    </div>
    <div class="mock">
      <div class="mock-top"><span class="dot"></span><span class="dot"></span><span class="dot"></span><span class="t">Readiness review · Case 04</span></div>
      <div class="mock-score">${ring(33, "#dc2626", 124, "Not ready")}<div class="mock-arrow">→</div>${ring(100, "#16a34a", 124, "Ready")}</div>
      <div class="mrow bad"><span>✗ 6+ weeks of symptoms</span><small>missing</small></div>
      <div class="mrow bad"><span>✗ Conservative therapy trial</span><small>missing</small></div>
      <div class="mrow ok"><span>✓ Neuro exam documented</span><small>verified in note</small></div>
    </div>
  </div></section>
  <div class="strip wrap">Built for the Nebius × NVIDIA Global AI Hackathon<div class="logos"><span>NVIDIA Nemotron</span><span>Nebius Token Factory</span><span>Tavily</span><span>FastAPI</span></div></div>
  <section class="block" id="features"><div class="wrap">
    <div class="eyebrow">Why AuthAssist</div><h2 class="sec-title">Evidence you can check, not a score you have to trust.</h2>
    <p class="sec-sub">Language models read and reason. Code verifies and counts. That split is the whole design.</p>
    <div class="grid3">${feats.map(([i, t, d]) => `<div class="card feat"><div class="ic">${i}</div><h3>${t}</h3><p>${d}</p></div>`).join("")}</div>
  </div></section>
  <section class="block alt" id="how"><div class="wrap">
    <div class="eyebrow">How it works</div><h2 class="sec-title">From a messy note to a clean request in four steps.</h2>
    <div class="grid4">${steps.map(([t, d], i) => `<div class="card step"><div class="n">${i + 1}</div><h3>${t}</h3><p>${d}</p></div>`).join("")}</div>
  </div></section>
  <section class="block"><div class="wrap split">
    <div><div class="eyebrow">Verified evidence</div><h2 class="sec-title">Every highlight is a real quote.</h2>
      <p class="sec-sub">The model proposes a quote for each criterion. Code then searches the note for those exact words. If they aren't there, the criterion is downgraded, no matter how confident the model sounded.</p></div>
    <div class="card note-demo">${note}</div>
  </div></section>
  <section class="block alt" id="proof"><div class="wrap">
    <div class="eyebrow">Results</div><h2 class="sec-title">Measured on 8 synthetic cases, including 2 scanned faxes.</h2>
    <div class="stats">
      <div class="card stat"><b>8/8</b><span>outcomes correct</span></div><div class="card stat"><b>57/57</b><span>quotes verified</span></div>
      <div class="card stat"><b>23/24</b><span>criteria correct</span></div><div class="card stat"><b>~99%</b><span>fax read accuracy</span></div>
    </div>
    <p class="muted small" style="margin-top:1rem">Small synthetic set, one procedure. Results vary slightly run to run. Full evaluation and known failures are in the <a href="https://github.com/codergirl73/authassist" target="_blank" rel="noopener">repository</a>.</p>
  </div></section>
  <section class="block" style="padding-bottom:0"><div class="wrap"><div class="cta-band">
    <h2>See your first readiness score in under a minute.</h2><p>No account, no real patient data. Pick a synthetic note and run it.</p>
    <a class="btn primary lg" href="#/login">Open the demo workspace →</a></div></div></section>
  <footer class="site"><div class="wrap"><span>© AuthAssist · MIT licensed · Synthetic data only. Drafts require clinician review. Never submits anything to an insurer.</span>
    <span><a href="https://github.com/codergirl73/authassist" target="_blank" rel="noopener">Source on GitHub</a></span></div></footer>`;
}

/* ---------------------------------------------------------------- login */
function login() {
  return `<div class="login">
    <div class="login-side">
      <a class="logo" href="#/">${LOGO} AuthAssist</a>
      <div><h2>Prior auth, without the back-and-forth.</h2>
        <ul><li>Reads typed notes and scanned faxes</li><li>Pulls the payer's current policy live</li><li>Verifies every quote in code</li><li>Drafts the letter and request PDF</li></ul></div>
      <div class="small" style="opacity:.7">Powered by NVIDIA Nemotron on Nebius Token Factory, with Tavily.</div>
    </div>
    <div class="login-main"><form class="login-card" id="loginForm">
      <h1>Enter the demo workspace</h1><p class="muted">No account or password needed. This is a hackathon demo.</p>
      <label class="f" for="nm">Your name</label><input id="nm" placeholder="Dr. Alex Rivera" value="${esc(S.user?.name || "")}" autocomplete="off">
      <label class="f" for="rl">Role</label>
      <select id="rl"><option>Clinician</option><option>Prior-auth coordinator</option><option>Practice manager</option></select>
      <button class="btn primary lg" style="width:100%;margin-top:1.3rem" type="submit">Continue to workspace →</button>
      <div class="notice" style="margin-top:1.2rem">Synthetic data only. Your name is kept in this browser to personalize the screen and is never sent to a server. Don't enter real patient information.</div>
      <p class="small muted" style="margin-top:1rem"><a href="#/">← Back to home</a></p>
    </form></div></div>`;
}
function bindLogin() {
  $("#loginForm").addEventListener("submit", (e) => {
    e.preventDefault();
    S.user = { name: $("#nm").value.trim() || "Demo Clinician", role: $("#rl").value };
    store.set("aa_user", S.user);
    go("app");
  });
}

/* ---------------------------------------------------------------- app shell */
const NAV = [["app", "🏠", "Dashboard"], ["app/new", "➕", "New check"], ["app/how", "🧭", "How it works"]];
function shell(active, inner) {
  const initials = (S.user?.name || "D").split(/\s+/).map((w) => w[0]).slice(0, 2).join("").toUpperCase();
  const links = NAV.map(([p, i, l]) => `<a class="navlink ${active === p ? "active" : ""}" href="#/${p}">${i} ${l}</a>`).join("");
  return `<div class="shell">
    <aside class="side"><a class="logo" href="#/">${LOGO} AuthAssist</a><nav>${links}</nav>
      <div class="userchip"><div class="avatar">${esc(initials)}</div><div style="min-width:0"><div class="nm">${esc(S.user?.name)}</div><div class="rl">${esc(S.user?.role)}</div></div></div>
      <button class="navlink" id="signout">↩︎ Sign out</button></aside>
    <div style="min-width:0"><div class="mobilebar"><a class="logo" href="#/">${LOGO}</a>${links}<button class="navlink" id="signout2">Sign out</button></div>
      <main class="main">${inner}</main></div></div>`;
}
function bindShell() {
  const out = () => { store.del("aa_user"); store.del("aa_session", sessionStorage); S.user = null; S.result = null; go(""); };
  $("#signout")?.addEventListener("click", out); $("#signout2")?.addEventListener("click", out);
}
function stepper(active) {
  const labels = ["Choose note", "Review", "Fix gaps", "Letter"];
  return `<div class="steps">${labels.map((l, i) => {
    const n = i + 1, cls = n < active ? "done" : n === active ? "active" : "";
    return `<div class="spill ${cls}"><span class="n">${n < active ? "✓" : n}</span>${l}</div>`;
  }).join("")}</div>`;
}

/* ---------------------------------------------------------------- dashboard */
function history() { return store.get("aa_history") || []; }
function saveHistory(result) {
  const a = result.assessment;
  const h = history().filter((x) => !(x.caseId === result.case_id && x.payer === result.payer_key));
  h.unshift({ ts: Date.now(), caseId: result.case_id, payer: result.payer_key, score: a.readiness_score, status: a.status, result });
  store.set("aa_history", h.slice(0, 5));
}
function dashboard() {
  const h = history();
  const first = (S.user?.name || "there").split(" ").slice(-2)[0];
  const rows = h.length
    ? `<table class="t"><thead><tr><th>Note</th><th>Payer</th><th>Score</th><th>Status</th><th>When</th><th></th></tr></thead><tbody>${h.map((x, i) => {
      const [lab, col] = STATUS[x.status];
      return `<tr><td><b>${esc(x.caseId.replace("_", " "))}</b></td><td>${esc(S.cfg.payers[x.payer] || x.payer)}</td><td><b style="color:${col}">${x.score}</b>/100</td>
        <td><span class="badge" style="color:${col}">${lab}</span></td><td class="muted small">${new Date(x.ts).toLocaleString([], { dateStyle: "medium", timeStyle: "short" })}</td>
        <td><button class="btn sm" data-open="${i}">Open</button></td></tr>`;
    }).join("")}</tbody></table>`
    : `<div class="empty">No checks yet. Run your first one, it takes under a minute.</div>`;
  return shell("app", `
    <div class="page-title">Welcome, ${esc(first)} 👋</div><div class="page-sub">Check a note against the payer's policy, fix the gaps, and get the letter.</div>
    <div class="card" style="display:grid;grid-template-columns:1fr auto;gap:1.2rem;align-items:center;background:linear-gradient(120deg,var(--brand-soft),var(--blue-soft))">
      <div><h3 style="font-size:1.3rem;margin-bottom:.3rem">Start a readiness check</h3>
        <div class="muted">${esc(S.cfg.procedure)}. Pick a synthetic note, or run the one-click demo with a scanned fax.</div></div>
      <div class="cta-row"><button class="btn primary" id="demoRun">▶ One-click demo</button><a class="btn" href="#/app/new">Choose a note</a></div></div>
    <h3 style="margin:2rem 0 .8rem;font-size:1.15rem">Recent checks</h3><div class="card" style="padding:.4rem 1rem">${rows}</div>
    <div class="notice" style="margin-top:1.4rem">Demo workspace: synthetic notes only. Recent checks are stored in this browser only.</div>`);
}
function bindDashboard() {
  $("#demoRun")?.addEventListener("click", () => { S.caseId = "case_04"; S.payer = null; S.live = false; startAssess(); });
  $$("[data-open]").forEach((b) => b.addEventListener("click", () => {
    const x = history()[+b.dataset.open]; S.result = x.result; S.letter = null; persist(); go("app/review");
  }));
}

/* ---------------------------------------------------------------- new check */
function newCheck() {
  const cases = S.cfg.cases;
  const cur = cases.find((c) => c.id === S.caseId) || cases[0];
  if (!S.payer) S.payer = cur.payer;
  const cards = cases.map((c) => `<button class="case ${c.id === cur.id ? "sel" : ""}" data-case="${c.id}">
      <b>${esc(c.id.replace("_", " ").replace(/^./, (m) => m.toUpperCase()))}${c.id === cur.id ? '<span class="ok">✓</span>' : ""}</b>
      <div class="sc">${esc(c.scenario)}</div><span class="tag">${c.note_text ? "📝 Typed note" : "📠 Scanned fax"}</span><span class="tag">${esc(S.cfg.payers[c.payer])}</span></button>`).join("");
  const prev = cur.note_text ? `<pre>${esc(cur.note_text)}</pre>` : `<img src="${cur.image_url}" alt="Scanned fax"><div class="tiny muted" style="margin-top:.4rem">Scanned fax: read by the Nemotron vision model.</div>`;
  return shell("app/new", `${stepper(1)}
    <div class="page-title">Choose a clinical note</div><div class="page-sub">Pick a synthetic example, confirm the payer, then run the check.</div>
    <div class="cols"><div class="cases">${cards}</div>
      <div class="card sticky"><div class="small muted" style="margin-bottom:.5rem">Selected: <b style="color:var(--ink)">${esc(cur.id.replace("_", " "))}</b></div>
        <div class="preview">${prev}</div>
        <label class="f" for="payer">Insurance payer</label>
        <select id="payer">${Object.entries(S.cfg.payers).map(([k, n]) => `<option value="${k}" ${k === S.payer ? "selected" : ""}>${esc(n)}</option>`).join("")}</select>
        <div class="small muted" style="margin:.5rem 0 0">Procedure: ${esc(S.cfg.procedure)}</div>
        <details style="margin-top:.8rem"><summary class="small" style="cursor:pointer;font-weight:600">Advanced options</summary>
          <label class="small" style="display:flex;gap:.5rem;margin-top:.6rem;align-items:flex-start"><input type="checkbox" id="live" style="width:auto;margin-top:.25rem" ${S.live ? "checked" : ""}>
          <span>Fetch the payer policy live via Tavily (ignore saved copy). Adds ~30-40s.</span></label></details>
        ${S.cfg.app_env === "demo" ? '<div class="tiny muted" style="margin-top:.6rem">⚡ Fast mode uses the saved policy criteria (originally fetched with Tavily).</div>' : ""}
        <button class="btn primary lg" id="run" style="width:100%;margin-top:1rem">Run readiness check →</button></div></div>`);
}
function bindNew() {
  $$("[data-case]").forEach((b) => b.addEventListener("click", () => { S.caseId = b.dataset.case; S.payer = null; route(); }));
  $("#payer").addEventListener("change", (e) => { S.payer = e.target.value; });
  $("#live").addEventListener("change", (e) => { S.live = e.target.checked; });
  $("#run").addEventListener("click", startAssess);
}

/* ---------------------------------------------------------------- streaming jobs */
async function streamJob(url, body, onProgress) {
  const res = await fetch(url, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(body) });
  if (!res.ok) { let m = res.statusText; try { m = (await res.json()).detail || m; } catch { /* keep */ } throw new Error(m); }
  const reader = res.body.getReader(), dec = new TextDecoder();
  let buf = "", result = null;
  for (;;) {
    const { value, done } = await reader.read();
    if (done) break;
    buf += dec.decode(value, { stream: true });
    let i;
    while ((i = buf.indexOf("\n")) >= 0) {
      const line = buf.slice(0, i).trim(); buf = buf.slice(i + 1);
      if (!line) continue;
      const ev = JSON.parse(line);
      if (ev.type === "progress") onProgress(ev);
      else if (ev.type === "error") throw new Error(ev.message);
      else if (ev.type === "result") result = ev.data;
    }
  }
  if (!result) throw new Error("The run ended without a result.");
  return result;
}
function runningView(title, sub) {
  return shell("app/new", `<div class="runbox"><div class="spin" style="width:44px;height:44px;margin:0 auto 1.2rem"></div>
    <h2 style="font-size:1.7rem;font-weight:800">${esc(title)}</h2><p class="muted">${esc(sub)}</p>
    <div class="card" style="text-align:left;margin-top:1.4rem" id="steps"><div class="run-step"><div class="spin"></div><span class="muted">Starting…</span></div></div></div>`);
}
function addProgress(ev) {
  const box = $("#steps"); if (!box) return;
  $$(".spin", box).forEach((s) => { const c = document.createElement("div"); c.className = "check"; c.textContent = "✓"; s.replaceWith(c); });
  const start = $(".run-step span.muted", box); if (start && start.textContent === "Starting…") start.closest(".run-step").remove();
  box.insertAdjacentHTML("beforeend", `<div class="run-step"><div class="check">✓</div><div><b>${esc(ev.label)}</b><div class="small muted">${esc(ev.detail)}</div></div></div>`);
  box.insertAdjacentHTML("beforeend", `<div class="run-step" data-tail><div class="spin"></div><span class="muted">Working…</span></div>`);
  $$("[data-tail]", box).slice(0, -1).forEach((n) => n.remove());
}
async function startAssess() {
  if (S.busy) return; S.busy = true;
  $root.innerHTML = runningView("Checking readiness", S.live ? "Fetching the policy live with Tavily, so this takes 30-40 seconds." : "Usually 10-20 seconds.");
  try {
    const result = await streamJob("/assess/stream", { example_case: S.caseId, payer: S.payer, force_refresh: S.live }, addProgress);
    S.result = result; S.letter = null; S.letterTraces = []; saveHistory(result); persist(); S.busy = false; go("app/review"); route();
  } catch (err) { S.busy = false; toast("Something went wrong: " + err.message); go("app/new"); route(); }
}
async function startRecheck(text) {
  if (S.busy) return; S.busy = true;
  $root.innerHTML = runningView("Re-checking with your addendum", "Facts and evidence are re-checked against the same policy.");
  try {
    const result = await streamJob("/recheck/stream", { result: S.result, addendum: text }, addProgress);
    S.result = result; S.letter = null; saveHistory(result); persist(); S.busy = false; go("app/review"); route();
  } catch (err) { S.busy = false; toast("Something went wrong: " + err.message); go("app/fix"); route(); }
}

/* ---------------------------------------------------------------- review */
function citationLink(c) {
  const p = c.split(" - ");
  const url = p.length > 1 ? p[p.length - 1] : "";
  return url.startsWith("http") ? `${esc(p.slice(0, -1).join(" - "))} — <a href="${esc(url)}" target="_blank" rel="noopener">source</a>` : esc(c);
}
function critCard(c, r, excused) {
  let icon, cls, label, edge;
  if (c.bypass_group) [icon, cls, label, edge] = r.status === "met" ? ["🚩", "bad", "Present", "flag"] : ["◻️", "", "Not present", "neutral"];
  else [icon, cls, label] = { met: ["✅", "ok", "Met"], unclear: ["⚠️", "warn", "Unclear"], missing: ["❌", "bad", "Missing"] }[r.status], edge = r.status;
  const q = r.evidence_quote ? `<div style="margin:.35rem 0"><q>${esc(r.evidence_quote)}</q><span class="badge ${r.quote_verified ? "ok" : "bad"}">${r.quote_verified ? "✓ verified in note" : "✗ not found in note"}</span></div>` : "";
  return `<div class="crit ${edge}" ${excused ? 'style="opacity:.55"' : ""}><div class="ttl">${icon} ${esc(c.description)}<span class="badge ${cls}">${label}</span></div>${q}
    <div class="small muted">${esc(r.reasoning)}</div><div class="small muted" style="margin-top:.25rem">📄 ${citationLink(c.policy_citation)}</div>${excused ? '<div class="tiny muted">Excused by red-flag bypass</div>' : ""}</div>`;
}
function annotate(note, results, crit) {
  const spans = [];
  for (const r of results) {
    if (!(r.evidence_quote && r.quote_verified)) continue;
    const toks = r.evidence_quote.trim().replace(/^[\s.,;:"'“”]+|[\s.,;:"'“”]+$/g, "").split(/\s+/).filter(Boolean);
    if (!toks.length) continue;
    const m = new RegExp(toks.map((t) => t.replace(/[.*+?^${}()|[\]\\]/g, "\\$&")).join("\\s+"), "i").exec(note);
    if (!m) continue;
    const c = crit[r.criterion_id], kind = c.bypass_group ? (r.status === "met" ? "flag" : null) : r.status;
    if (kind) spans.push([m.index, m.index + m[0].length, kind, c.description]);
  }
  spans.sort((a, b) => a[0] - b[0]);
  let out = "", pos = 0, used = 0;
  for (const [s, e, kind, desc] of spans) {
    if (s < pos) continue;
    out += esc(note.slice(pos, s)) + `<mark class="${kind}" title="${esc(desc)}">${esc(note.slice(s, e))}</mark>`; pos = e; used++;
  }
  return [out + esc(note.slice(pos)), used];
}
function review() {
  const res = S.result;
  if (!res) return null;
  const a = res.assessment, { crit, excused, required, flags, counted, gaps } = requiredSet(a), p = a.policy;
  const quotes = a.results.filter((r) => r.evidence_quote), vq = quotes.filter((r) => r.quote_verified).length;
  const secs = res.traces.reduce((n, e) => n + e.latency_ms, 0), toks = res.traces.reduce((n, e) => n + (e.prompt_tokens || 0) + (e.completion_tokens || 0), 0);
  const [label, color] = STATUS[a.status];
  const src = { tavily: "Found live via Tavily", cache: "Cached Tavily result", snapshot: "Cached snapshot" }[p.source];
  const delta = res.previous_score != null ? `<div class="delta">📈 After your addendum the score went from ${res.previous_score} to <b>${a.readiness_score}</b> (${a.readiness_score - res.previous_score >= 0 ? "+" : ""}${a.readiness_score - res.previous_score}).</div>` : "";
  const next = gaps.length
    ? `<div><b>Next: fix ${gaps.length} gap${gaps.length > 1 ? "s" : ""}.</b> <span class="muted">Add the missing evidence and re-check. Takes seconds.</span></div><div class="cta-row"><a class="btn primary" href="#/app/fix">Fix ${gaps.length} gap${gaps.length > 1 ? "s" : ""} →</a><a class="btn" href="#/app/letter">Skip to letter</a></div>`
    : `<div><b>Next: draft the letter.</b> <span class="muted">${a.status === "ready" ? "Every criterion is documented with verified evidence." : "Remaining items are unclear, review them before submitting."}</span></div><div class="cta-row"><a class="btn primary" href="#/app/letter">Draft the letter →</a></div>`;
  const [noteHtml, nHl] = annotate(res.note_text, a.results, crit), f = res.facts;
  const tabs = {
    criteria: required.map(([c, r]) => critCard(c, r, excused.includes(c.category))).join("") +
      `<details ${a.red_flag_bypass ? "open" : ""} style="margin-top:.8rem"><summary style="cursor:pointer;font-weight:600;margin-bottom:.6rem">Red-flag indications (${flags.filter(([, r]) => r.status === "met").length} present)</summary>${flags.map(([c, r]) => critCard(c, r)).join("")}</details>` +
      (a.results.some((r) => r.evidence_quote && !r.quote_verified) ? `<div class="notice" style="margin-top:.8rem">🛡️ Some model-proposed quotes were not found verbatim in the note and were downgraded automatically.</div>` : ""),
    note: `<div class="small muted" style="margin-bottom:.6rem">${nHl} verified quote(s) highlighted in place: green met, amber unclear, red missing or red flag. Hover a highlight for the criterion.</div><div class="notebox">${noteHtml}</div>` +
      (res.ingest_method === "vision" ? `<div class="small muted" style="margin-top:.5rem">Text transcribed from the scanned image by the Nemotron vision model.</div>` : ""),
    facts: `<div class="card"><p><b>Chief complaint:</b> ${esc(f.chief_complaint || "—")}</p><p><b>Age / sex:</b> ${esc(f.patient_age ?? "—")} / ${esc(f.sex || "—")}</p>
      <p><b>Symptom duration:</b> ${f.symptom_duration_weeks ? f.symptom_duration_weeks + " weeks" : "—"}</p><p><b>Diagnoses:</b> ${esc(f.diagnoses.join(", ") || "—")}</p>
      <p><b>Prior imaging:</b> ${esc(f.prior_imaging.join("; ") || "—")}</p><p><b>Conservative treatments:</b></p><ul>${f.conservative_treatments.map((t) => `<li>${esc([t.treatment, t.duration_weeks ? t.duration_weeks + " wk" : "", t.dates].filter(Boolean).join(" · "))}</li>`).join("") || "<li>none documented</li>"}</ul>
      <p><b>Red flags:</b> ${esc(f.red_flags.join("; ") || "none documented")}</p><p><b>Neuro exam:</b> ${esc(f.neuro_exam_findings.join("; ") || "not documented")}</p></div>`,
    log: `<div class="card">${res.traces.map((e) => `<div class="trace"><span>${ROLE_ICON[e.role] || "•"}</span><div>${esc(e.step)}${e.success ? "" : " ❌"}<div class="m">${esc(e.model)}</div></div><span class="small muted">${(e.prompt_tokens || 0) + (e.completion_tokens || 0) || ""}${(e.prompt_tokens || e.completion_tokens) ? " tok" : ""}</span><span class="small">${fmtSecs(e.latency_ms)}</span></div>`).join("")}</div>` +
      (res.traces.some((e) => e.role === "tavily") ? `<div class="notice" style="margin-top:.8rem;background:var(--brand-soft)">🔎 Live Tavily calls were made in this run (search + extract).</div>` : `<div class="small muted" style="margin-top:.6rem">No Tavily call in this run: the policy came from the saved copy. Tick “Fetch the payer policy live” under Advanced options to run one.</div>`),
  };
  return shell("app/new", `${stepper(2)}
    <div class="page-title">Readiness review</div><div class="page-sub">${esc(a.payer)} · ${esc(a.procedure)} · ${esc(res.case_id.replace("_", " "))}</div>${delta}
    <div class="card score-card"><div>${ring(a.readiness_score, color, 190, label)}</div><div>
      <div class="kpis"><div class="kpi"><div class="l">Criteria met</div><div class="v">${counted.filter(([, r]) => r.status === "met").length}/${counted.length}</div><div class="s">required</div></div>
        <div class="kpi"><div class="l">Quotes verified</div><div class="v">${vq}/${quotes.length}</div><div class="s">verbatim in note</div></div>
        <div class="kpi"><div class="l">Run</div><div class="v">${(secs / 1000).toFixed(0)}s</div><div class="s">${toks.toLocaleString()} tokens · ${res.traces.length} calls</div></div>
        <div class="kpi"><div class="l">Policy</div><div class="v">${p.source === "tavily" ? "🔎 Live" : "🗂️ Saved"}</div><div class="s">${esc(src)}</div></div></div>
      ${a.red_flag_bypass ? `<div class="notice" style="margin-top:.9rem;background:var(--bad-soft)">🚩 <b>Red-flag indication documented.</b> Conservative-therapy requirements are excused; imaging is justified now.</div>` : ""}
      ${a.missing_items.length ? `<div style="margin-top:.9rem"><b>What's missing</b><ul style="margin:.3rem 0 0;padding-left:1.2rem">${a.missing_items.map((m) => `<li>${esc(m)}</li>`).join("")}</ul></div>` : a.status === "ready" ? `<div class="notice" style="margin-top:.9rem;background:var(--brand-soft)">All required criteria are documented with verified evidence.</div>` : ""}
      <div class="small muted" style="margin-top:.9rem">Policy: ${esc(p.payer)} — <a href="${esc(p.url)}" target="_blank" rel="noopener">${esc(p.title)}</a> · retrieved ${esc(String(p.retrieved_at).slice(0, 10))}${res.policy_notice ? ` · ${esc(res.policy_notice)}` : ""}</div></div></div>
    <div class="next">${next}</div>
    <div class="tabs">${[["criteria", "Criteria checklist"], ["note", "Annotated note"], ["facts", "Extracted facts"], ["log", "Run log"]].map(([k, l]) => `<button class="tab ${S.tab === k ? "active" : ""}" data-tab="${k}">${l}</button>`).join("")}</div>
    <div id="tabbody">${tabs[S.tab]}</div>`);
}
function bindReview() { $$("[data-tab]").forEach((b) => b.addEventListener("click", () => { S.tab = b.dataset.tab; route(); })); }

/* ---------------------------------------------------------------- fix gaps */
function fix() {
  if (!S.result) return null;
  const { gaps } = requiredSet(S.result.assessment);
  if (!gaps.length) { go("app/review"); return null; }
  return shell("app/new", `${stepper(3)}
    <div class="page-title">Fill the gaps</div><div class="page-sub">Your text is appended to the note as a labeled clinician addendum, then facts and evidence are re-checked.</div>
    <div class="card" style="max-width:820px"><button class="btn sm" id="example" type="button">✨ Fill with example answers</button>
      <form id="gapForm">${gaps.map(([c]) => `<label class="f" for="g_${c.id}">${esc(c.description)}</label><textarea id="g_${c.id}" data-cat="${c.category}" rows="2" placeholder="e.g. Completed 8 weeks of physical therapy from 08/20/2026 to 10/15/2026."></textarea>`).join("")}
      <div class="cta-row" style="margin-top:1.2rem"><button class="btn primary" type="submit">Add to note & re-check →</button><a class="btn" href="#/app/review">← Back to review</a></div></form></div>`);
}
function bindFix() {
  $("#example")?.addEventListener("click", () => $$("#gapForm textarea").forEach((t) => { if (EXAMPLE_ADDENDA[t.dataset.cat]) t.value = EXAMPLE_ADDENDA[t.dataset.cat]; }));
  $("#gapForm")?.addEventListener("submit", (e) => {
    e.preventDefault();
    const text = $$("#gapForm textarea").map((t) => t.value.trim()).filter(Boolean).join("\n");
    if (!text) return toast("Enter at least one addition.");
    startRecheck(text);
  });
}

/* ---------------------------------------------------------------- letter */
function md(src) {
  const inline = (s) => esc(s).replace(/\*\*(.+?)\*\*/g, "<b>$1</b>").replace(/\*(.+?)\*/g, "<i>$1</i>").replace(/\[([^\]]+)\]\((https?:[^)\s]+)\)/g, '<a href="$2" target="_blank" rel="noopener">$1</a>');
  return src.split(/\n{2,}/).map((block) => {
    const lines = block.split("\n");
    if (/^#{1,3}\s/.test(lines[0])) return `<h3>${inline(lines[0].replace(/^#+\s*/, ""))}</h3>` + (lines.length > 1 ? `<p>${lines.slice(1).map(inline).join("<br>")}</p>` : "");
    if (lines.every((l) => /^\s*[-*]\s/.test(l))) return `<ul>${lines.map((l) => `<li>${inline(l.replace(/^\s*[-*]\s/, ""))}</li>`).join("")}</ul>`;
    return `<p>${lines.map(inline).join("<br>")}</p>`;
  }).join("");
}
function letterView() {
  if (!S.result) return null;
  const a = S.result.assessment, [label, color] = STATUS[a.status];
  const head = `${stepper(4)}<div class="page-title">Letter & request PDF</div><div class="page-sub">A draft letter of medical necessity plus a request PDF with the evidence checklist.</div>
    <div style="margin-bottom:1rem"><span class="badge" style="color:${color};margin:0">${label} · ${a.readiness_score}/100</span><span class="tag" style="margin-left:.5rem">${esc(a.payer)}</span><span class="tag">CPT 72148</span></div>
    ${a.status !== "ready" ? `<div class="notice" style="margin-bottom:1rem;max-width:820px">This request is not ready yet — the letter will only cite criteria with verified evidence.</div>` : ""}`;
  if (!S.letter) return shell("app/new", head + `<div class="card" style="max-width:820px;text-align:center"><div class="spin" style="width:34px;height:34px;margin:0 auto 1rem"></div><b>Drafting your letter…</b><div class="small muted">Nemotron reasoning writes the letter and the PDF is built in code. About 10-20 seconds.</div></div>`);
  return shell("app/new", head + `<div class="cta-row" style="margin-bottom:1rem"><button class="btn primary" id="dlPdf">⬇ Download PDF</button><button class="btn" id="dlMd">⬇ Letter (.md)</button><button class="btn ghost" id="regen">↻ Regenerate</button></div>
    <div class="letter">${md(S.letter.body_markdown)}</div>
    <div class="small muted" style="margin:.8rem 0;max-width:820px">Citations: ${S.letter.citations.map(esc).join(" · ")}<br>Draft only: requires clinician review and signature. Nothing is sent to any insurer.</div>
    <div class="cta-row"><a class="btn" href="#/app/review">← Back to review</a><a class="btn" href="#/app/new">Check another note</a></div>`);
}
async function loadLetter() {
  if (S.letter || S.busy || !S.result) return;
  S.busy = true;
  try {
    const res = await fetch("/letter", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(S.result) });
    if (!res.ok) throw new Error((await res.json().catch(() => ({}))).detail || res.statusText);
    const j = await res.json();
    S.letter = j.letter; S.pdf = j.pdf_base64; S.letterTraces = j.traces; persist();
  } catch (err) { toast("Could not draft the letter: " + err.message); }
  S.busy = false; if (location.hash === "#/app/letter") route();
}
function download(name, blob) { const a = document.createElement("a"); a.href = URL.createObjectURL(blob); a.download = name; a.click(); setTimeout(() => URL.revokeObjectURL(a.href), 2000); }
function bindLetter() {
  $("#dlPdf")?.addEventListener("click", () => {
    const bin = atob(S.pdf), bytes = Uint8Array.from(bin, (c) => c.charCodeAt(0));
    download(`authassist_${S.result.case_id}.pdf`, new Blob([bytes], { type: "application/pdf" }));
  });
  $("#dlMd")?.addEventListener("click", () => download(`authassist_${S.result.case_id}_letter.md`, new Blob([S.letter.body_markdown], { type: "text/markdown" })));
  $("#regen")?.addEventListener("click", () => { S.letter = null; route(); });
}

/* ---------------------------------------------------------------- how it works */
function how() {
  const m = S.cfg.models;
  const trace = S.result ? [...S.result.traces, ...S.letterTraces] : [];
  return shell("app/how", `<div class="page-title">How it works</div><div class="page-sub">Which model does what, and where the guardrails are.</div>
    <div class="card"><table class="t"><thead><tr><th>Role</th><th>Model</th><th>Used for</th></tr></thead><tbody>
      <tr><td>👁️ Vision</td><td>${esc(m.vision)}</td><td>Reading scanned notes and fax images</td></tr>
      <tr><td>⚡ Fast</td><td>${esc(m.fast)}</td><td>Fact extraction, search queries, missing-item asks</td></tr>
      <tr><td>🧠 Reasoning</td><td>${esc(m.reasoning)}</td><td>Policy → criteria, evidence matching, letter drafting</td></tr>
      <tr><td>🔎 Tavily</td><td>search (advanced) + extract</td><td>Finding and reading the payer's current policy</td></tr></tbody></table></div>
    <p class="small muted">All LLM calls go to Nebius Token Factory (NVIDIA Nemotron). The readiness score and quote verification are computed in code, not by the model.</p>
    ${trace.length ? `<h3 style="margin:1.6rem 0 .6rem">Trace of your last run</h3><div class="card">${trace.map((e) => `<div class="trace"><span>${ROLE_ICON[e.role] || "•"}</span><div>${esc(e.step)}<div class="m">${esc(e.model)}</div></div><span class="small muted">${(e.prompt_tokens || 0) + (e.completion_tokens || 0) || ""}</span><span class="small">${fmtSecs(e.latency_ms)}</span></div>`).join("")}</div>` : `<div class="notice">Run a check to see the live model trace here.</div>`}
    <h3 style="margin:1.6rem 0 .6rem">Limitations</h3><div class="card"><ul style="margin:0;padding-left:1.2rem;line-height:1.8">
      <li><b>Synthetic data only</b> in this demo. Uploads are disabled on the public deployment.</li><li><b>Not HIPAA-compliant yet.</b> Not legal or medical advice.</li>
      <li><b>One procedure</b> (MRI lumbar spine without contrast, CPT 72148), tested on 2-3 payers plus Medicare/CMS fallback.</li>
      <li><b>Human in the loop:</b> every output is a draft for clinician review. Nothing is ever submitted to an insurer.</li>
      <li><b>Quotes are verified</b> to appear verbatim in the note; unverifiable quotes are downgraded automatically.</li>
      <li><b>Policies change.</b> Every criterion shows its policy source and retrieval date; verify before submission.</li>
      <li>Extraction and matching are model-based and can be wrong. See the evaluation in the repository for known failures.</li></ul></div>`);
}

/* ---------------------------------------------------------------- router */
function route() {
  if (!S.cfg) return;
  const path = location.hash.replace(/^#\/?/, "");
  const guarded = path.startsWith("app");
  if (guarded && !S.user) return go("login");
  let html = null, bind = null;
  if (path === "") { html = landing(); }
  else if (path === "login") { if (S.user) return go("app"); html = login(); bind = bindLogin; }
  else if (path === "app") { html = dashboard(); bind = bindDashboard; }
  else if (path === "app/new") { html = newCheck(); bind = bindNew; }
  else if (path === "app/review") { html = review(); bind = bindReview; if (!html) return go("app/new"); }
  else if (path === "app/fix") { html = fix(); bind = bindFix; if (!html) return; }
  else if (path === "app/letter") { html = letterView(); bind = bindLetter; if (!html) return go("app/new"); }
  else if (path === "app/how") { html = how(); }
  else return go("");
  if (S.busy && path !== "app/letter") { /* a job is rendering its own progress view */ return; }
  $root.innerHTML = html;
  if (path === "") $$("[data-scroll]").forEach((a) => a.addEventListener("click", () => document.getElementById(a.dataset.scroll)?.scrollIntoView({ behavior: "smooth" })));
  else { if (guarded) bindShell(); if (bind) bind(); }
  if (path === "app/letter") loadLetter();
  if (!(path === "app/fix" || path === "app/new")) window.scrollTo(0, 0);
}

async function boot() {
  restore();
  try {
    S.cfg = await (await fetch("/api/config")).json();
  } catch {
    $root.innerHTML = `<div class="runbox"><h2>Can't reach the AuthAssist API</h2><p class="muted">Start it with <code>uvicorn api.main:app</code> and reload.</p></div>`; return;
  }
  window.addEventListener("hashchange", route);
  route();
}
boot();
