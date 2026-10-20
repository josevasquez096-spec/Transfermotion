"""Partes comunes de los juegos HTML: estilos, sonido, confeti, marcador por equipos, temporizador y ventanas."""

CSS = r"""
:root{--primary:#0B3D91;--accent:#00A3E0;--bg:#EEF3FB;--text:#0F172A;--surface:#fff;--muted:#64748b;
--ok:#16a34a;--bad:#dc2626;--radius:18px;--shadow:0 10px 30px rgba(15,23,42,.12)}
*{box-sizing:border-box}
html{font-size:clamp(14px,1.05vw + 6px,24px)}
body{margin:0;min-height:100vh;font-family:"Segoe UI",system-ui,-apple-system,Roboto,Arial,sans-serif;color:var(--text);
background:radial-gradient(circle at 15% 10%,var(--accent-a),transparent 40%),
radial-gradient(circle at 85% 90%,var(--primary-a),transparent 45%),var(--bg);
display:flex;flex-direction:column}
body.dark{--surface:#1e293b;--muted:#94a3b8;--shadow:0 10px 30px rgba(0,0,0,.45)}
.emoji,.big-emoji,.prompt.emoji,.token,.medal{font-family:"Segoe UI Emoji","Apple Color Emoji","Noto Color Emoji",sans-serif}
header.top{display:flex;align-items:center;justify-content:space-between;gap:1rem;padding:.6rem 1.2rem;
background:var(--primary);color:#fff;box-shadow:0 4px 16px rgba(0,0,0,.18)}
.brand{display:flex;align-items:center;gap:.8rem;min-width:0}
.brand .logo{font-size:2rem;line-height:1}
.brand h1{margin:0;font-size:1.25rem;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
.brand p{margin:0;opacity:.85;font-size:.8rem}
.tools{display:flex;gap:.4rem}
.tools button{background:rgba(255,255,255,.16);color:#fff;border:0;border-radius:10px;padding:.35rem .6rem;
font-size:.95rem;cursor:pointer}
.tools button:hover{background:rgba(255,255,255,.3)}
main{flex:1;display:grid;grid-template-columns:1fr auto;gap:1rem;padding:1rem 1.2rem;min-height:0}
#stage{min-width:0;display:flex;flex-direction:column}
.screen{flex:1;display:flex;flex-direction:column;align-items:center;gap:.8rem;animation:fade .35s ease}
[hidden]{display:none!important}
@keyframes fade{from{opacity:0;transform:translateY(8px)}to{opacity:1;transform:none}}
.card{background:var(--surface);border-radius:var(--radius);box-shadow:var(--shadow);padding:1.4rem 1.8rem}
.intro{text-align:center;max-width:46rem;margin:auto}
.intro h2{font-size:2.1rem;margin:.3rem 0}
.big-emoji{font-size:4.5rem;line-height:1.1}
.muted{color:var(--muted)}
.pill{display:inline-block;background:var(--primary-soft);color:var(--primary);
border-radius:999px;padding:.25rem .9rem;font-weight:600;font-size:.9rem}
body.dark .pill{color:var(--accent)}
.row{display:flex;gap:.7rem;justify-content:center;flex-wrap:wrap;align-items:center}
.btn{border:0;border-radius:12px;padding:.65rem 1.2rem;font-size:1rem;font-weight:600;cursor:pointer;
background:var(--surface);color:var(--text);box-shadow:0 2px 0 rgba(0,0,0,.12),0 4px 12px rgba(0,0,0,.08);
transition:transform .08s}
.btn:hover{transform:translateY(-1px)}
.btn:active{transform:translateY(1px)}
.btn.primary{background:var(--accent);color:#fff}
.btn.big{font-size:1.25rem;padding:.8rem 1.8rem}
.btn:disabled{opacity:.45;cursor:default;transform:none}
.mini{border:0;border-radius:8px;width:1.7rem;height:1.7rem;cursor:pointer;font-weight:700;
background:rgba(127,127,127,.16);color:var(--text)}
.qhead{width:100%;display:flex;align-items:center;justify-content:space-between;gap:1rem}
.question{font-size:1.85rem;text-align:center;margin:.2rem 0;max-width:60rem;line-height:1.22}
.after{display:flex;flex-direction:column;align-items:center;gap:.8rem;width:100%}
.answer-box{background:var(--ok);color:#fff;font-size:1.6rem;font-weight:700;border-radius:14px;padding:.6rem 1.4rem;
animation:pop .35s ease}
.answer-box.bad{background:var(--bad)}
.explain,.hint{background:var(--surface);border-left:6px solid var(--accent);border-radius:12px;padding:.7rem 1rem;
max-width:56rem;font-size:1.05rem;box-shadow:var(--shadow)}
@keyframes pop{0%{transform:scale(.7);opacity:0}70%{transform:scale(1.06)}100%{transform:scale(1);opacity:1}}
.timer{position:relative;flex:0 0 14rem;height:2.2rem;border-radius:999px;background:rgba(127,127,127,.18);overflow:hidden}
.timer-fill{position:absolute;inset:0 auto 0 0;width:100%;background:var(--accent);transition:width 1s linear}
.timer-num{position:absolute;inset:0;display:grid;place-items:center;font-weight:800}
.timer.done .timer-fill{background:var(--bad)}
.award{display:flex;flex-direction:column;align-items:center;gap:.6rem}
.award-q{margin:0;font-weight:600}
.chips{display:flex;flex-wrap:wrap;gap:.5rem;justify-content:center}
.chip{border:3px solid var(--team);background:var(--surface);color:var(--text);border-radius:999px;
padding:.4rem 1rem;font-weight:700;cursor:pointer;font-size:1rem}
.chip.on{background:var(--team);color:#fff}
aside#score{width:15rem;align-self:start;position:sticky;top:1rem}
aside#score h2{font-size:1rem;margin:0 0 .6rem;text-transform:uppercase;letter-spacing:.05em;color:var(--muted)}
.team{display:grid;grid-template-columns:1fr auto;align-items:center;gap:.2rem .5rem;background:var(--surface);
border-left:8px solid var(--team);border-radius:12px;padding:.5rem .7rem;margin-bottom:.5rem;box-shadow:var(--shadow)}
.team .tname{font-weight:600;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}
.team .tscore{font-size:1.4rem;text-align:right}
.team .adj{grid-column:1/-1;display:flex;gap:.3rem;justify-content:flex-end;opacity:.0;transition:opacity .2s}
.team:hover .adj{opacity:1}
.team.bump{animation:pop .4s ease}
.overlay{position:fixed;inset:0;background:rgba(15,23,42,.55);display:grid;place-items:center;z-index:50;
animation:fade .2s ease;padding:1rem}
.modal{background:var(--surface);color:var(--text);border-radius:var(--radius);box-shadow:var(--shadow);
padding:1.4rem 1.8rem;max-width:min(64rem,94vw);max-height:92vh;overflow:auto;position:relative;
display:flex;flex-direction:column;gap:.9rem;align-items:center}
.modal .x{position:absolute;top:.5rem;right:.6rem}
.modal ul{text-align:left;font-size:1.05rem;line-height:1.6}
.podium{text-align:center;min-width:24rem;margin:auto}
.ranking{list-style:none;padding:0;margin:1rem 0;display:flex;flex-direction:column;gap:.5rem}
.ranking li{display:grid;grid-template-columns:3rem 1fr auto;align-items:center;gap:.6rem;font-size:1.4rem;
border-left:10px solid var(--team);background:var(--surface);border-radius:12px;
padding:.5rem 1rem;animation:pop .5s ease both}
.ranking li:nth-child(1){font-size:1.8rem}
.confetti{position:fixed;inset:0;pointer-events:none;z-index:100}
footer{text-align:center;font-size:.7rem;color:var(--muted);padding:.3rem}
@media (max-width:900px){main{grid-template-columns:1fr}aside#score{width:auto;position:static}}
"""

JS = r"""
"use strict";
const G = JSON.parse(document.getElementById("game-data").textContent);
const T = G.ui;
const stage = document.getElementById("stage");
function el(tag, props, ...kids) {
  const e = document.createElement(tag);
  if (props) for (const [k, v] of Object.entries(props)) {
    if (v === null || v === undefined || v === false) continue;
    if (k === "class") e.className = v;
    else if (k === "style") e.style.cssText = v;
    else if (k.startsWith("on")) e.addEventListener(k.slice(2), v);
    else e.setAttribute(k, v === true ? "" : v);
  }
  for (const kid of kids.flat()) {
    if (kid === null || kid === undefined || kid === false) continue;
    e.append(kid.nodeType ? kid : document.createTextNode(String(kid)));
  }
  return e;
}
function clear(node) { while (node.firstChild) node.removeChild(node.firstChild); }
function fmt(text, params) { return String(text).replace(/\{(\w+)\}/g, (m, k) => (k in params ? params[k] : m)); }
function shuffle(list) { for (let i = list.length - 1; i > 0; i--) { const j = Math.floor(Math.random() * (i + 1)); [list[i], list[j]] = [list[j], list[i]]; } return list; }

const Sound = {
  on: !!G.sound, ctx: null,
  tone(freq, dur, type = "sine", delay = 0, vol = 0.12) {
    if (!this.on) return;
    try {
      this.ctx = this.ctx || new (window.AudioContext || window.webkitAudioContext)();
      const t = this.ctx.currentTime + delay, o = this.ctx.createOscillator(), g = this.ctx.createGain();
      o.type = type; o.frequency.value = freq;
      g.gain.setValueAtTime(vol, t); g.gain.exponentialRampToValueAtTime(0.001, t + dur);
      o.connect(g).connect(this.ctx.destination); o.start(t); o.stop(t + dur + 0.02);
    } catch (e) { /* sin audio */ }
  },
  ok() { [523, 659, 784].forEach((f, i) => this.tone(f, 0.2, "triangle", i * 0.09)); },
  bad() { this.tone(220, 0.3, "sawtooth", 0, 0.07); this.tone(150, 0.4, "sawtooth", 0.14, 0.07); },
  tick() { this.tone(880, 0.05, "square", 0, 0.035); },
  pop() { this.tone(700, 0.09, "triangle"); },
  win() { [523, 659, 784, 1047, 784, 1047].forEach((f, i) => this.tone(f, 0.24, "triangle", i * 0.12)); },
};

function confetti() {
  const c = el("canvas", { class: "confetti" }); document.body.append(c);
  const ctx = c.getContext("2d"); c.width = innerWidth; c.height = innerHeight;
  const colors = [G.colors.primary, G.colors.accent].concat(G.team_colors);
  const parts = Array.from({ length: 180 }, () => ({ x: Math.random() * c.width, y: -20 - Math.random() * c.height * 0.5,
    vx: (Math.random() - 0.5) * 4, vy: 2 + Math.random() * 4, s: 6 + Math.random() * 9, r: Math.random() * 6,
    vr: (Math.random() - 0.5) * 0.3, c: colors[Math.floor(Math.random() * colors.length)] }));
  const start = performance.now();
  (function frame(t) {
    ctx.clearRect(0, 0, c.width, c.height);
    for (const p of parts) {
      p.x += p.vx; p.y += p.vy; p.vy += 0.05; p.r += p.vr;
      ctx.save(); ctx.translate(p.x, p.y); ctx.rotate(p.r); ctx.fillStyle = p.c; ctx.fillRect(-p.s / 2, -p.s / 4, p.s, p.s / 2); ctx.restore();
    }
    if (t - start < 3800) requestAnimationFrame(frame); else c.remove();
  })(start);
}

const Teams = {
  list: (G.teams || []).map((name, i) => ({ name, score: 0, color: G.team_colors[i % G.team_colors.length], token: G.tokens[i % G.tokens.length] })),
  visible: true,
  render() {
    const box = document.getElementById("score");
    if (!this.list.length || !this.visible) { box.hidden = true; return; }
    box.hidden = false; clear(box);
    box.append(el("h2", null, T.scoreboard));
    this.list.forEach((t, i) => box.append(el("div", { class: "team", style: "--team:" + t.color },
      el("span", { class: "tname" }, t.name), el("b", { class: "tscore" }, t.score),
      el("span", { class: "adj" }, el("button", { class: "mini", title: "-10", onclick: () => this.add(i, -10) }, "−"),
        el("button", { class: "mini", title: "+10", onclick: () => this.add(i, 10) }, "+")))));
  },
  add(i, pts) {
    this.list[i].score += pts; this.render();
    const node = document.querySelectorAll("#score .team")[i];
    if (node) { node.classList.add("bump"); setTimeout(() => node.classList.remove("bump"), 450); }
  },
};

function awardBar(points, onDone) {
  const next = el("button", { class: "btn primary big", onclick: () => { chosen.forEach(i => Teams.add(i, points)); if (chosen.size) Sound.pop(); onDone(); } }, T.next + " ▶");
  const chosen = new Set();
  if (!Teams.list.length) return el("div", { class: "row" }, next);
  const chips = el("div", { class: "chips" });
  Teams.list.forEach((t, i) => {
    const b = el("button", { class: "chip", style: "--team:" + t.color, onclick: () => { if (chosen.has(i)) chosen.delete(i); else chosen.add(i); b.classList.toggle("on"); } }, t.name);
    chips.append(b);
  });
  return el("div", { class: "award" }, el("p", { class: "award-q" }, fmt(T.who_scored, { points })), chips, next);
}

function Timer(seconds, onEnd) {
  const fill = el("div", { class: "timer-fill" }), num = el("span", { class: "timer-num" }, seconds);
  const node = el("div", { class: "timer" }, fill, num);
  let left = seconds, id = null;
  const stop = () => { if (id) { clearInterval(id); id = null; } };
  if (seconds > 0) {
    id = setInterval(() => {
      left -= 1; num.textContent = Math.max(0, left); fill.style.width = (100 * Math.max(0, left) / seconds) + "%";
      if (left <= 5 && left > 0) Sound.tick();
      if (left <= 0) { stop(); node.classList.add("done"); num.textContent = T.time_up; Sound.bad(); if (onEnd) onEnd(); }
    }, 1000);
  } else node.hidden = true;
  return { node, stop };
}

let current = null;
function screen(...kids) {
  if (current && current.cleanup) current.cleanup();
  clear(stage);
  current = el("section", { class: "screen" }, ...kids);
  stage.append(current);
  return current;
}

function modal(content, persistent) {
  const box = el("div", { class: "modal" }), overlay = el("div", { class: "overlay" }, box);
  const close = () => overlay.remove();
  box.append(el("button", { class: "mini x", title: T.close, onclick: close }, "✕"), content);
  if (!persistent) overlay.addEventListener("click", e => { if (e.target === overlay) close(); });
  document.body.append(overlay);
  return { close, box };
}

function showRules() {
  modal(el("div", null, el("h2", null, "📖 " + T.how_to_play), el("ul", null, G.rules.map(r => el("li", null, r)))));
}

function intro(count, start, extra) {
  screen(el("div", { class: "intro card" }, el("div", { class: "big-emoji" }, G.emoji), el("h2", null, G.title),
    G.subtitle ? el("p", { class: "muted" }, G.subtitle) : null,
    count !== null ? el("p", null, el("span", { class: "pill" }, fmt(T.count_items, { n: count }))) : null,
    extra || null,
    el("div", { class: "row" }, start ? el("button", { class: "btn primary big", onclick: start }, T.start + " ▶") : null,
      el("button", { class: "btn", onclick: showRules }, "📖 " + T.how_to_play))));
}

function podium() {
  Sound.win(); confetti();
  const sorted = Teams.list.slice().sort((a, b) => b.score - a.score);
  screen(el("div", { class: "card podium" }, el("h2", null, sorted.length ? "🏆 " + T.final : "🎉 " + T.thanks),
    sorted.length ? el("ol", { class: "ranking" }, sorted.map((t, i) => el("li", { style: "--team:" + t.color + ";animation-delay:" + (i * 0.12) + "s" },
      el("span", { class: "medal" }, ["🥇", "🥈", "🥉"][i] || (i + 1) + "."), el("span", null, t.name), el("b", null, t.score)))) : el("div", { class: "big-emoji" }, "🎊"),
    el("button", { class: "btn", onclick: () => location.reload() }, "↺ " + T.play_again)));
}

function setupChrome() {
  document.title = G.title;
  if (G.dark) document.body.classList.add("dark");
  const soundBtn = document.getElementById("btn-sound");
  const paintSound = () => { soundBtn.textContent = Sound.on ? "🔊" : "🔇"; soundBtn.title = T.sound; };
  soundBtn.addEventListener("click", () => { Sound.on = !Sound.on; paintSound(); });
  paintSound();
  const full = document.getElementById("btn-full");
  full.title = T.fullscreen;
  full.addEventListener("click", () => { if (document.fullscreenElement) document.exitFullscreen(); else document.documentElement.requestFullscreen().catch(() => {}); });
  const rules = document.getElementById("btn-rules");
  rules.title = T.rules; rules.addEventListener("click", showRules);
  document.getElementById("offline").textContent = "✔ " + T.offline + " · IcePilot";
  Teams.render();
}
"""
