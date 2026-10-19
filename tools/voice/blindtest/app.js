"use strict";
// Blind voice test. Round 1: same or different person? Round 2: would I believe this coworker?
// Audio only ever starts from a click or a key press the person makes.

const app = document.getElementById("app");
const LINE_LABEL = { long: "Long line", short: "Short line", tech: "Technical line" };
const CHIPS = [
  ["robotic", "Too robotic", "Q"],
  ["age", "Wrong age", "W"],
  ["energy", "Wrong energy", "E"],
];
const ROUND1_LINES = ["long", "long", "long", "long", "long", "tech", "tech", "tech", "tech", "short", "short", "short"];

let casting, manifest;
let state = null; // {phase, trials, i, ...}
let player = null;

const rand = (n) => Math.floor(Math.random() * n);
function shuffle(a) {
  a = a.slice();
  for (let i = a.length - 1; i > 0; i--) { const j = rand(i + 1); [a[i], a[j]] = [a[j], a[i]]; }
  return a;
}
const sampleUrl = (cid, line) => `/samples/${encodeURIComponent(cid)}__${line}.ogg`;
const esc = (s) => String(s).replace(/[&<>"]/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c]));

function stopAudio() {
  if (player) { player.pause(); player = null; }
  document.querySelectorAll("button.play.playing").forEach((b) => b.classList.remove("playing"));
}
function play(url, btn, onEnd) {
  stopAudio();
  btn.blur(); // so Space/Enter don't also re-click the focused button
  player = new Audio(url);
  btn.classList.add("playing");
  const done = () => { btn.classList.remove("playing"); btn.classList.add("heard"); if (onEnd) onEnd(); };
  player.addEventListener("ended", done);
  player.addEventListener("error", () => { btn.classList.remove("playing"); btn.textContent = "Missing clip"; });
  player.play().catch(() => {});
}

// ---------- build the pool and trials ----------

function buildPool() {
  const pool = [];
  for (const [pid, p] of Object.entries(casting.personas)) {
    const slots = [["primary", p.primary], ...p.alternates.map((a, i) => ["alt" + (i + 1), a])];
    for (const [role, v] of slots) pool.push({ cid: v.candidate, persona: pid, name: p.name, role, gender: p.gender });
  }
  return pool;
}

function buildTrials(pool) {
  const key = (a, b) => [a.cid, b.cid].sort().join("|");
  const used = new Set();
  const pairs = [];
  const take = (kind, ok, count) => {
    for (let guard = 0, n = 0; n < count && guard < 2000; guard++) {
      const a = pool[rand(pool.length)], b = pool[rand(pool.length)];
      if (a.cid === b.cid || used.has(key(a, b)) || !ok(a, b)) continue;
      used.add(key(a, b)); pairs.push({ kind, a, b }); n++;
    }
  };
  // controls: the very same voice twice
  shuffle(pool).slice(0, 3).forEach((v) => pairs.push({ kind: "control", a: v, b: v }));
  take("same-gender", (a, b) => a.gender === b.gender && a.persona !== b.persona, 6);
  take("cross-gender", (a, b) => a.gender !== b.gender, 3);
  const lines = shuffle(ROUND1_LINES);
  return shuffle(pairs).map((p, i) => ({ ...p, line: lines[i], flip: Math.random() < 0.5 }));
}

// ---------- screens ----------

function header(title, i, n, extra = "") {
  return `<div class="progress"><div style="width:${Math.round((i / n) * 100)}%"></div></div>
    <div class="meta"><span>${esc(title)}</span><span>${i} of ${n}${extra}</span></div>`;
}

function intro() {
  stopAudio();
  app.innerHTML = `
    <h1>Voice test</h1>
    <p class="muted">About ten minutes. Headphones help. Nothing plays until you press a button.</p>
    <div class="card">
      <h2>Round 1: same person or different?</h2>
      <p class="muted">12 pairs. Each plays the same sentence, twice. Say whether one person spoke both, or two people. Some pairs really are the same voice.</p>
      <h2>Round 2: would I believe this coworker?</h2>
      <p class="muted">6 voices, one clip each. Rate 1 (never) to 5 (completely) and flag what is off.</p>
    </div>
    <button class="primary" id="start" style="width:100%">Start <kbd>Enter</kbd></button>`;
  state = { phase: "intro" };
  document.getElementById("start").onclick = startRound1;
}

function startRound1() {
  const pool = buildPool();
  state = { phase: "r1", pool, trials: buildTrials(pool), i: 0, answers: [], t0: Date.now() };
  showTrial();
}

function showTrial() {
  stopAudio();
  const t = state.trials[state.i];
  state.heard = { A: false, B: false };
  app.innerHTML = `
    ${header("Round 1: same or different?", state.i + 1, state.trials.length)}
    <div class="card">
      <div class="line">${LINE_LABEL[t.line]}: both voices say the same sentence.</div>
      <div class="row">
        <button class="play" id="pa">Play A <kbd>A</kbd></button>
        <button class="play" id="pb">Play B <kbd>B</kbd></button>
      </div>
    </div>
    <div class="row">
      <button class="same" id="same" disabled>Same person <kbd>S</kbd></button>
      <button class="diff" id="diff" disabled>Different person <kbd>D</kbd></button>
    </div>
    <p class="muted status" id="hint">Listen to both first.</p>`;
  document.getElementById("pa").onclick = () => playSlot("A");
  document.getElementById("pb").onclick = () => playSlot("B");
  document.getElementById("same").onclick = () => answer("same");
  document.getElementById("diff").onclick = () => answer("different");
}

function playSlot(slot) {
  const t = state.trials[state.i];
  const side = (slot === "A") !== t.flip ? t.a : t.b;
  const btn = document.getElementById(slot === "A" ? "pa" : "pb");
  play(sampleUrl(side.cid, t.line), btn, () => {
    state.heard[slot] = true;
    if (state.heard.A && state.heard.B) {
      document.getElementById("same").disabled = false;
      document.getElementById("diff").disabled = false;
      document.getElementById("hint").textContent = "Same person or different?";
    }
  });
}

function answer(choice) {
  const t = state.trials[state.i];
  if (!(state.heard.A && state.heard.B)) return;
  state.answers.push({
    a: t.a.cid, b: t.b.cid, a_persona: t.a.persona, b_persona: t.b.persona, kind: t.kind,
    line: t.line, answered: choice, correct: (choice === "same") === (t.kind === "control"),
  });
  state.i++;
  state.i < state.trials.length ? showTrial() : startRound2();
}

function startRound2() {
  const items = shuffle(Object.entries(casting.personas).map(([pid, p]) => ({ pid, p })));
  state = { ...state, phase: "r2", items, i: 0, ratings: [] };
  showRate();
}

function showRate() {
  stopAudio();
  const { pid, p } = state.items[state.i];
  state.heardR = false; state.chips = new Set(); state.rating = null;
  app.innerHTML = `
    ${header("Round 2: would I believe this coworker?", state.i + 1, state.items.length)}
    <div class="card">
      <h2 class="persona">${esc(p.name)}</h2>
      <p class="muted">${esc(p.role)}. ${esc(p.age)}. ${esc(p.personality)}</p>
      <div class="row"><button class="play" id="pl">Play <kbd>Space</kbd></button></div>
    </div>
    <div class="row">
      ${[1, 2, 3, 4, 5].map((n) => `<button class="rate" data-n="${n}" disabled>${n} <kbd>${n}</kbd></button>`).join("")}
    </div>
    <p class="muted status">1 = never a coworker, 5 = completely.</p>
    <div class="chips"><p class="muted">What is off? (optional)</p><div class="row">
      ${CHIPS.map(([k, label, key]) => `<button class="chip" data-chip="${k}">${label}<kbd>${key}</kbd></button>`).join("")}
    </div></div>`;
  document.getElementById("pl").onclick = playRate;
  app.querySelectorAll(".rate").forEach((b) => (b.onclick = () => rate(+b.dataset.n)));
  app.querySelectorAll(".chip").forEach((b) => (b.onclick = () => toggleChip(b.dataset.chip)));
}

function playRate() {
  const { p } = state.items[state.i];
  play(sampleUrl(p.primary.candidate, "long"), document.getElementById("pl"), () => {
    state.heardR = true;
    app.querySelectorAll(".rate").forEach((b) => (b.disabled = false));
  });
}
function toggleChip(k) {
  state.chips.has(k) ? state.chips.delete(k) : state.chips.add(k);
  app.querySelectorAll(".chip").forEach((b) => b.classList.toggle("on", state.chips.has(b.dataset.chip)));
}
function rate(n) {
  if (!state.heardR) return;
  const { pid, p } = state.items[state.i];
  state.ratings.push({ persona: pid, candidate: p.primary.candidate, rating: n, chips: [...state.chips] });
  state.i++;
  state.i < state.items.length ? showRate() : finish();
}

// ---------- results ----------

const pct = (n, d) => (d ? Math.round((100 * n) / d) + "%" : "n/a");

async function finish() {
  stopAudio();
  const A = state.answers, R = state.ratings;
  const ctl = A.filter((x) => x.kind === "control");
  const sg = A.filter((x) => x.kind === "same-gender");
  const cg = A.filter((x) => x.kind === "cross-gender");
  const said = (xs) => xs.filter((x) => x.answered === "same").length;
  const confusable = A.filter((x) => x.kind !== "control" && x.answered === "same");
  const avg = (xs) => (xs.length ? (xs.reduce((s, r) => s + r.rating, 0) / xs.length).toFixed(1) : "n/a");

  const run = {
    seconds: Math.round((Date.now() - state.t0) / 1000),
    summary: {
      control_said_same: `${said(ctl)}/${ctl.length}`,
      same_gender_said_same: `${said(sg)}/${sg.length}`,
      cross_gender_said_same: `${said(cg)}/${cg.length}`,
    },
    round1: A, round2: R,
  };
  const rows = R.map((r) => `<tr><td>${esc(casting.personas[r.persona].name)}</td><td>${esc(r.candidate)}</td>
    <td class="${r.rating >= 4 ? "good" : r.rating <= 2 ? "bad" : "warn"}">${r.rating}</td><td>${esc(r.chips.join(", ") || "-")}</td></tr>`).join("");
  const conf = confusable.length
    ? confusable.map((x) => `<tr><td>${esc(x.a)}</td><td>${esc(x.b)}</td><td>${esc(x.kind)}</td></tr>`).join("")
    : `<tr><td colspan="3" class="good">None. Every pair of different voices sounded different.</td></tr>`;

  app.innerHTML = `
    <h1>Results</h1>
    <p class="muted">Took ${Math.round(run.seconds / 60)} min. Average believability: <b>${avg(R)}</b> of 5.</p>
    <div class="card">
      <h2>Round 1</h2>
      <table>
        <tr><th>Pair type</th><th>You said "same"</th><th>Should be</th></tr>
        <tr><td>Control (same voice twice)</td><td>${run.summary.control_said_same} (${pct(said(ctl), ctl.length)})</td><td>all</td></tr>
        <tr><td>Different voice, same gender</td><td class="${said(sg) ? "bad" : "good"}">${run.summary.same_gender_said_same} (${pct(said(sg), sg.length)})</td><td>none</td></tr>
        <tr><td>Different voice, cross gender</td><td class="${said(cg) ? "bad" : "good"}">${run.summary.cross_gender_said_same} (${pct(said(cg), cg.length)})</td><td>none</td></tr>
      </table>
      <p class="muted">Different voices you took for one person (these need a change):</p>
      <table><tr><th>Voice A</th><th>Voice B</th><th>Type</th></tr>${conf}</table>
    </div>
    <div class="card">
      <h2>Round 2</h2>
      <table><tr><th>Teammate</th><th>Voice</th><th>Rating</th><th>Flags</th></tr>${rows}</table>
    </div>
    <p class="status muted" id="save">Saving...</p>
    <button id="again" style="width:100%">Run again</button>`;
  document.getElementById("again").onclick = intro;
  state.phase = "done";
  try {
    const res = await fetch("/results", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(run) });
    if (!res.ok) throw new Error(res.status);
    document.getElementById("save").innerHTML = '<span class="good">Saved to tools/voice/results.json.</span>';
  } catch (e) {
    document.getElementById("save").innerHTML = `<span class="bad">Could not save (${esc(e.message)}). Copy this:</span>
      <textarea style="width:100%;height:120px;background:#181825;color:#cdd6f4">${esc(JSON.stringify(run))}</textarea>`;
  }
}

// ---------- keyboard ----------

document.addEventListener("keydown", (e) => {
  if (e.ctrlKey || e.metaKey || e.altKey || !state) return;
  const k = e.key.toLowerCase();
  const click = (id) => { const b = document.getElementById(id); if (b && !b.disabled) b.click(); };
  if (state.phase === "intro" && k === "enter") click("start");
  else if (state.phase === "r1") {
    if (k === "a") click("pa"); else if (k === "b") click("pb");
    else if (k === "s") click("same"); else if (k === "d") click("diff");
  } else if (state.phase === "r2") {
    if (k === " " || k === "p") { e.preventDefault(); click("pl"); }
    else if (/^[1-5]$/.test(k)) { const b = app.querySelector(`.rate[data-n="${k}"]`); if (b && !b.disabled) b.click(); }
    else { const c = CHIPS.find(([, , key]) => key.toLowerCase() === k); if (c) toggleChip(c[0]); }
  }
});

// ---------- boot ----------

(async function boot() {
  try {
    [casting, manifest] = await Promise.all([
      fetch("/casting.json").then((r) => { if (!r.ok) throw new Error("casting.json"); return r.json(); }),
      fetch("/manifest.json").then((r) => { if (!r.ok) throw new Error("manifest.json"); return r.json(); }),
    ]);
    intro();
  } catch (e) {
    app.innerHTML = `<h1>Not ready</h1><p class="bad">Could not load ${esc(e.message)}. Run tools/voice/render.py first.</p>`;
  }
})();
