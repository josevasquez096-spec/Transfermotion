"""Motores de cada juego HTML (estilos + JavaScript). Se combinan con web_base en build.build_html()."""

QUIZ_CSS = r"""
.options{display:grid;grid-template-columns:1fr 1fr;gap:.9rem;width:100%;max-width:64rem}
.options.n2{grid-template-columns:1fr 1fr}
.option{display:flex;align-items:center;gap:.9rem;background:var(--opt);color:#fff;border-radius:16px;padding:.8rem 1.1rem;
font-size:1.3rem;font-weight:700;min-height:4.2rem;box-shadow:0 5px 0 rgba(0,0,0,.2);transition:opacity .3s,transform .3s}
.option .shape{font-size:1.8rem;width:2.4rem;text-align:center;opacity:.9}
.option.wrong{opacity:.25;transform:scale(.97)}
.option.right{outline:6px solid #fff;box-shadow:0 0 0 10px var(--ok),0 5px 0 rgba(0,0,0,.2);animation:pop .4s ease}
.option.right::after{content:"✔";margin-left:auto;font-size:2rem}
"""
QUIZ_JS = r"""
function runQuiz() {
  const qs = G.data.questions;
  const SHAPES = ["▲", "◆", "●", "■"], COLORS = ["#E21B3C", "#1368CE", "#D89E00", "#26890C"];
  let i = 0;
  intro(qs.length, show);
  function show() {
    if (i >= qs.length) return podium();
    const q = qs[i]; let revealed = false;
    const after = el("div", { class: "after" });
    const tiles = q.options.map((o, k) => el("div", { class: "option", style: "--opt:" + COLORS[k % 4] }, el("span", { class: "shape" }, SHAPES[k % 4]), el("span", null, o)));
    const timer = Timer(G.options.seconds || 0, reveal);
    const btn = el("button", { class: "btn primary big", onclick: reveal }, "👁 " + T.reveal);
    screen(el("div", { class: "qhead" }, el("span", { class: "pill" }, fmt(T.question_of, { n: i + 1, total: qs.length })), timer.node),
      el("h2", { class: "question" }, q.q),
      tiles.length ? el("div", { class: "options n" + tiles.length }, tiles) : null,
      el("div", { class: "row" }, btn), after).cleanup = timer.stop;
    function reveal() {
      if (revealed) return; revealed = true; timer.stop(); btn.remove(); Sound.ok();
      if (tiles.length) tiles.forEach((t, k) => t.classList.add(k === q.correct ? "right" : "wrong"));
      else after.append(el("div", { class: "answer-box" }, "✔ " + q.answer));
      if (G.options.show_explain !== false && q.explain) after.append(el("div", { class: "explain" }, "💡 " + q.explain));
      after.append(awardBar(G.options.points || 100, () => { i += 1; show(); }));
    }
  }
}
"""

TRIVIA_CSS = r"""
.tboard{display:grid;grid-template-columns:repeat(var(--cols),1fr);gap:.6rem;width:100%;max-width:72rem;margin:auto}
.tcat{background:var(--primary);color:#fff;border-radius:12px;padding:.8rem .5rem;text-align:center;font-weight:800;
font-size:1.05rem;display:grid;place-items:center;min-height:4.2rem;text-transform:uppercase}
.tcell{border:0;border-radius:12px;background:var(--surface);color:var(--primary);font-size:2rem;font-weight:900;
min-height:5rem;cursor:pointer;box-shadow:var(--shadow);transition:transform .1s}
body.dark .tcell{color:var(--accent)}
.tcell:hover:not(:disabled){transform:scale(1.04);background:var(--accent);color:#fff}
.tcell.used{opacity:.25;cursor:default}
.tcell.empty{visibility:hidden}
.tawards{display:flex;flex-wrap:wrap;gap:.5rem;justify-content:center}
.tchip{display:flex;align-items:center;gap:.4rem;border:3px solid var(--team);border-radius:999px;padding:.25rem .4rem .25rem .9rem;font-weight:700}
.tchip .mini{width:auto;padding:0 .5rem}
.tchip .ok{background:var(--ok);color:#fff}.tchip .bad{background:var(--bad);color:#fff}
"""
TRIVIA_JS = r"""
function runTrivia() {
  const board = G.data.board, used = new Set();
  const total = board.reduce((s, c) => s + c.questions.length, 0);
  intro(total, draw);
  function draw() {
    const grid = el("div", { class: "tboard", style: "--cols:" + board.length });
    board.forEach(c => grid.append(el("div", { class: "tcat" }, c.category)));
    const rows = Math.max(...board.map(c => c.questions.length));
    for (let r = 0; r < rows; r++) board.forEach((c, ci) => {
      const q = c.questions[r], key = ci + "-" + r;
      if (!q) { grid.append(el("div", { class: "tcell empty" })); return; }
      grid.append(el("button", { class: "tcell" + (used.has(key) ? " used" : ""), disabled: used.has(key), onclick: () => open(c, q, key) }, used.has(key) ? "✓" : q.points));
    });
    screen(grid, used.size === total ? el("div", { class: "row" }, el("button", { class: "btn primary big", onclick: podium }, "🏆 " + T.final)) : null);
  }
  function open(c, q, key) {
    const after = el("div", { class: "after" });
    const btn = el("button", { class: "btn primary big", onclick: () => { btn.remove(); after.prepend(el("div", { class: "answer-box" }, "✔ " + q.a)); Sound.ok(); } }, "👁 " + T.reveal);
    const awards = el("div", { class: "tawards" });
    Teams.list.forEach((t, i) => awards.append(el("div", { class: "tchip", style: "--team:" + t.color }, el("span", null, t.name),
      el("button", { class: "mini ok", onclick: () => { Teams.add(i, q.points); Sound.pop(); } }, "+" + q.points),
      G.options.negative ? el("button", { class: "mini bad", onclick: () => { Teams.add(i, -q.points); Sound.bad(); } }, "−" + q.points) : null)));
    const m = modal(el("div", { class: "after" }, el("span", { class: "pill" }, c.category + " · " + q.points),
      el("h2", { class: "question" }, q.q), btn, after, awards,
      el("button", { class: "btn", onclick: () => { used.add(key); m.close(); draw(); } }, "↩ " + T.back_to_board)), true);
  }
}
"""

HANGMAN_CSS = r"""
.hangman{display:grid;grid-template-columns:minmax(10rem,16rem) 1fr;gap:1.5rem;align-items:center;width:100%;max-width:70rem}
.gallows{width:100%;height:auto}
.gallows .part{stroke:var(--text);stroke-width:6;stroke-linecap:round;fill:none;opacity:0;transition:opacity .3s}
.gallows .part.on{opacity:1}
.gallows .frame{stroke:var(--muted);stroke-width:7;stroke-linecap:round;fill:none}
.slots{display:flex;flex-wrap:wrap;gap:1rem 2rem;justify-content:center}
.word{display:flex;gap:.35rem}
.slot{width:2.4rem;height:3.1rem;border-bottom:5px solid var(--primary);display:grid;place-items:center;font-size:2rem;font-weight:800}
body.dark .slot{border-color:var(--accent)}
.slot.fixed{border-color:transparent}
.keyboard{display:flex;flex-wrap:wrap;gap:.4rem;justify-content:center;max-width:56rem}
.key{width:2.8rem;height:2.8rem;border:0;border-radius:10px;font-size:1.2rem;font-weight:800;cursor:pointer;
background:var(--surface);color:var(--text);box-shadow:0 3px 0 rgba(0,0,0,.15)}
.key.hit{background:var(--ok);color:#fff}.key.miss{background:var(--bad);color:#fff;opacity:.6}
.keyboard.locked .key{pointer-events:none}
.hm-info{font-weight:700}
"""
HANGMAN_JS = r"""
function gallowsSvg() {
  const ns = "http://www.w3.org/2000/svg";
  const svg = document.createElementNS(ns, "svg"); svg.setAttribute("viewBox", "0 0 200 240"); svg.setAttribute("class", "gallows");
  const add = (tag, attrs, cls) => { const n = document.createElementNS(ns, tag); for (const k in attrs) n.setAttribute(k, attrs[k]); n.setAttribute("class", cls); svg.append(n); return n; };
  add("path", { d: "M20 230 H120 M50 230 V20 H140 V45" }, "frame");
  const parts = [add("circle", { cx: 140, cy: 67, r: 22 }, "part"), add("path", { d: "M140 89 V155" }, "part"),
    add("path", { d: "M140 105 L112 135" }, "part"), add("path", { d: "M140 105 L168 135" }, "part"),
    add("path", { d: "M140 155 L115 200" }, "part"), add("path", { d: "M140 155 L165 200" }, "part")];
  svg.paint = (errors, max) => { const n = Math.ceil(errors * parts.length / max); parts.forEach((p, k) => p.classList.toggle("on", k < n)); };
  return svg;
}
function runHangman() {
  const words = G.data.words, max = G.options.max_errors || 6, LETTERS = G.alphabet.split("");
  const isLetter = ch => /\p{L}/u.test(ch);
  const norm = ch => (ch === "ñ" || ch === "Ñ") && LETTERS.includes("Ñ") ? "Ñ" : ch.normalize("NFD").replace(/[̀-ͯ]/g, "").toUpperCase();
  let i = 0;
  intro(words.length, show);
  function show() {
    if (i >= words.length) return podium();
    const w = words[i], guessed = new Set(); let errors = 0, done = false;
    const slots = el("div", { class: "slots" }), kb = el("div", { class: "keyboard" }), after = el("div", { class: "after" });
    const info = el("div", { class: "hm-info" }), svg = gallowsSvg();
    const render = () => {
      clear(slots);
      w.answer.split(/\s+/).forEach(word => slots.append(el("div", { class: "word" }, [...word].map(ch =>
        el("span", { class: "slot" + (isLetter(ch) ? "" : " fixed") }, !isLetter(ch) || done || guessed.has(norm(ch)) ? ch : " ")))));
      info.textContent = fmt(T.errors_left, { n: max - errors }); svg.paint(errors, max);
    };
    const finish = win => {
      done = true; render(); kb.classList.add("locked"); hintRow.remove();
      if (win) { Sound.ok(); confetti(); after.append(el("div", { class: "answer-box" }, "🎉 " + T.solved), awardBar(G.options.points || 100, next)); }
      else { Sound.bad(); after.append(el("div", { class: "answer-box bad" }, fmt(T.was, { answer: w.answer })), el("div", { class: "row" }, el("button", { class: "btn primary big", onclick: next }, T.next + " ▶"))); }
    };
    const guess = L => {
      if (done || guessed.has(L)) return;
      guessed.add(L);
      const hit = [...w.answer].some(ch => isLetter(ch) && norm(ch) === L);
      const key = kb.querySelector('[data-l="' + L + '"]');
      if (key) { key.disabled = true; key.classList.add(hit ? "hit" : "miss"); }
      if (hit) Sound.pop(); else { errors += 1; Sound.bad(); }
      if ([...w.answer].every(ch => !isLetter(ch) || guessed.has(norm(ch)))) finish(true);
      else if (errors >= max) finish(false); else render();
    };
    const next = () => { i += 1; show(); };
    LETTERS.forEach(L => kb.append(el("button", { class: "key", "data-l": L, onclick: () => guess(L) }, L)));
    const onKey = e => { if (e.ctrlKey || e.altKey || e.metaKey || !e.key || e.key.length !== 1) return; const L = norm(e.key); if (LETTERS.includes(L)) guess(L); };
    document.addEventListener("keydown", onKey);
    const hintRow = el("div", { class: "row" },
      w.hint ? el("button", { class: "btn", onclick: e => e.currentTarget.replaceWith(el("div", { class: "hint" }, "💡 " + w.hint)) }, "💡 " + T.hint) : null,
      el("button", { class: "btn", onclick: () => finish(false) }, "👁 " + T.reveal));
    screen(el("div", { class: "qhead" }, el("span", { class: "pill" }, fmt(T.word_of, { n: i + 1, total: words.length })), info),
      el("div", { class: "hangman" }, svg, el("div", { class: "after" }, slots, hintRow)), kb, after).cleanup = () => document.removeEventListener("keydown", onKey);
    render();
  }
}
"""

GUESS_CSS = r"""
.prompt{background:var(--surface);border-radius:24px;box-shadow:var(--shadow);padding:1.5rem 2.5rem;text-align:center;
max-width:64rem;word-break:break-word;animation:pop .4s ease}
.prompt.emoji{font-size:5rem;letter-spacing:.3rem;line-height:1.3}
.prompt.scramble{font-size:3.4rem;font-weight:900;letter-spacing:.5rem;color:var(--primary);font-family:Consolas,"Courier New",monospace}
body.dark .prompt.scramble{color:var(--accent)}
"""
GUESS_JS = r"""
function runGuess() {
  const rounds = G.data.rounds; let i = 0;
  intro(rounds.length, show);
  function show() {
    if (i >= rounds.length) return podium();
    const r = rounds[i]; let revealed = false;
    const after = el("div", { class: "after" }), timer = Timer(G.options.seconds || 0, reveal);
    const btn = el("button", { class: "btn primary big", onclick: reveal }, "👁 " + T.reveal);
    screen(el("div", { class: "qhead" }, el("span", { class: "pill" }, fmt(T.round_of, { n: i + 1, total: rounds.length })), timer.node),
      el("div", { class: "prompt " + (G.type === "emoji" ? "emoji" : "scramble") }, r.prompt),
      el("div", { class: "row" }, r.hint ? el("button", { class: "btn", onclick: e => e.currentTarget.replaceWith(el("div", { class: "hint" }, "💡 " + r.hint)) }, "💡 " + T.hint) : null, btn),
      after).cleanup = timer.stop;
    function reveal() {
      if (revealed) return; revealed = true; timer.stop(); btn.remove(); Sound.ok();
      after.append(el("div", { class: "answer-box" }, "✔ " + r.answer), awardBar(G.options.points || 100, () => { i += 1; show(); }));
    }
  }
}
"""

SNAKES_CSS = r"""
.snakes{display:grid;grid-template-columns:minmax(0,1fr) 19rem;gap:1.2rem;width:100%;align-items:start}
.sboard-wrap{position:relative;width:100%;max-width:calc((100vh - 9rem) * var(--cols) / var(--rows));margin:auto}
.sboard{display:grid;grid-template-columns:repeat(var(--cols),1fr);aspect-ratio:var(--cols)/var(--rows);
border-radius:14px;overflow:hidden;box-shadow:var(--shadow)}
.scell{position:relative;background:var(--surface);border:1px solid rgba(127,127,127,.15);font-size:.75rem}
.scell.alt{background:var(--cell-alt)}
.scell .snum{position:absolute;top:.15rem;left:.3rem;font-weight:700;color:var(--muted)}
.scell.goal{background:var(--accent)}.scell.goal .snum{color:#fff}
.soverlay{position:absolute;inset:0;width:100%;height:100%;pointer-events:none}
.token{position:absolute;font-size:clamp(1rem,3.2vw,2.1rem);transform:translate(-50%,-50%);transition:left .22s,top .22s;
filter:drop-shadow(0 2px 2px rgba(0,0,0,.35));z-index:3}
.spanel{display:flex;flex-direction:column;gap:.8rem}
.turn{border-left:10px solid var(--team);text-align:center}
.turn .who{font-size:1.4rem;font-weight:800}
.die{font-size:4.6rem;line-height:1;text-align:center;font-family:"Segoe UI Symbol","Segoe UI Emoji",sans-serif}
.slog{font-size:.85rem;max-height:9rem;overflow:auto;display:flex;flex-direction:column;gap:.2rem}
.standings{list-style:none;margin:0;padding:0;display:flex;flex-direction:column;gap:.3rem}
.standings li{display:flex;justify-content:space-between;gap:.5rem;border-left:6px solid var(--team);padding:.15rem .5rem;
background:var(--surface);border-radius:8px}
.qopts{display:flex;flex-direction:column;gap:.4rem;width:100%;max-width:44rem}
.qopt{border-radius:10px;padding:.5rem .9rem;background:rgba(127,127,127,.12);font-size:1.15rem}
.qopt.right{background:var(--ok);color:#fff;font-weight:700}
@media (max-width:1100px){.snakes{grid-template-columns:1fr}}
"""
SNAKES_JS = r"""
function runSnakes() {
  const B = G.data.board, Q = G.data.questions || [], mode = Q.length ? G.options.mode : "dice";
  const players = Teams.list.length ? Teams.list : [{ name: "1", color: G.team_colors[0], token: G.tokens[0] }, { name: "2", color: G.team_colors[1], token: G.tokens[1] }];
  Teams.visible = false; Teams.render();
  const pos = players.map(() => 1); let turn = 0, busy = false, over = false, qi = 0;
  const jumps = {};
  B.ladders.forEach(([a, b]) => { jumps[a] = { to: b, kind: "ladder" }; });
  B.snakes.forEach(([a, b]) => { jumps[a] = { to: b, kind: "snake" }; });
  const rc = n => { const r = Math.floor((n - 1) / B.cols), k = (n - 1) % B.cols; return [r, r % 2 === 0 ? k : B.cols - 1 - k]; };
  const center = n => { const [r, c] = rc(n); return [(c + 0.5) * 100, (B.rows - 1 - r + 0.5) * 100]; };
  const board = el("div", { class: "sboard" });
  for (let r = B.rows - 1; r >= 0; r--) for (let c = 0; c < B.cols; c++) {
    const n = r % 2 === 0 ? r * B.cols + c + 1 : r * B.cols + (B.cols - c);
    board.append(el("div", { class: "scell" + ((r + c) % 2 ? " alt" : "") + (n === B.total ? " goal" : "") }, el("span", { class: "snum" }, n === B.total ? "🏁 " + n : n)));
  }
  const ns = "http://www.w3.org/2000/svg";
  const svg = document.createElementNS(ns, "svg");
  svg.setAttribute("viewBox", "0 0 " + B.cols * 100 + " " + B.rows * 100); svg.setAttribute("class", "soverlay"); svg.setAttribute("preserveAspectRatio", "none");
  const add = (tag, attrs) => { const n = document.createElementNS(ns, tag); for (const k in attrs) n.setAttribute(k, attrs[k]); svg.append(n); return n; };
  B.ladders.forEach(([a, b]) => {
    const [x1, y1] = center(a), [x2, y2] = center(b), dx = x2 - x1, dy = y2 - y1, len = Math.hypot(dx, dy);
    const ox = -dy / len * 16, oy = dx / len * 16;
    add("line", { x1: x1 + ox, y1: y1 + oy, x2: x2 + ox, y2: y2 + oy, stroke: "#8B5A2B", "stroke-width": 8, "stroke-linecap": "round" });
    add("line", { x1: x1 - ox, y1: y1 - oy, x2: x2 - ox, y2: y2 - oy, stroke: "#8B5A2B", "stroke-width": 8, "stroke-linecap": "round" });
    const steps = Math.max(2, Math.floor(len / 45));
    for (let s = 1; s < steps; s++) { const t = s / steps; add("line", { x1: x1 + dx * t + ox, y1: y1 + dy * t + oy, x2: x1 + dx * t - ox, y2: y1 + dy * t - oy, stroke: "#C08A4B", "stroke-width": 6 }); }
  });
  const SNAKE_COLORS = ["#16a34a", "#dc2626", "#7c3aed", "#ea580c", "#0891b2", "#be185d"];
  B.snakes.forEach(([a, b], k) => {
    const [x1, y1] = center(a), [x2, y2] = center(b), dx = x2 - x1, dy = y2 - y1, len = Math.hypot(dx, dy);
    const nx = -dy / len * 70, ny = dx / len * 70, col = SNAKE_COLORS[k % SNAKE_COLORS.length];
    const d = "M" + x1 + " " + y1 + " C" + (x1 + dx * 0.3 + nx) + " " + (y1 + dy * 0.3 + ny) + " " + (x1 + dx * 0.7 - nx) + " " + (y1 + dy * 0.7 - ny) + " " + x2 + " " + y2;
    add("path", { d, stroke: "rgba(0,0,0,.25)", "stroke-width": 24, fill: "none", "stroke-linecap": "round" });
    add("path", { d, stroke: col, "stroke-width": 18, fill: "none", "stroke-linecap": "round" });
    add("path", { d, stroke: "rgba(255,255,255,.5)", "stroke-width": 4, fill: "none", "stroke-dasharray": "6 14" });
    add("circle", { cx: x1, cy: y1, r: 17, fill: col });
    add("circle", { cx: x1 - 6, cy: y1 - 4, r: 4, fill: "#fff" }); add("circle", { cx: x1 + 6, cy: y1 - 4, r: 4, fill: "#fff" });
  });
  const tokens = players.map(p => el("div", { class: "token", title: p.name }, p.token));
  const wrap = el("div", { class: "sboard-wrap", style: "--cols:" + B.cols + ";--rows:" + B.rows }, board, svg, ...tokens);
  const place = () => players.forEach((p, i) => {
    const [x, y] = center(pos[i]), same = players.map((_, j) => j).filter(j => pos[j] === pos[i]), k = same.indexOf(i), off = (k - (same.length - 1) / 2) * 22;
    tokens[i].style.left = (x + off) / B.cols + "%"; tokens[i].style.top = (y + (same.length > 1 ? 12 : 0)) / B.rows + "%";
  });
  const FACES = ["⚀", "⚁", "⚂", "⚃", "⚄", "⚅"];
  const die = el("div", { class: "die" }, "🎲"), who = el("div", { class: "who" }), turnBox = el("div", { class: "card turn" }, el("div", { class: "muted" }, T.turn), who);
  const log = el("div", { class: "slog" }), standings = el("ol", { class: "standings" });
  const logCard = el("div", { class: "card", hidden: true }, log);
  const actBtn = el("button", { class: "btn primary big", onclick: () => act() });
  const say = text => { logCard.hidden = false; log.prepend(el("div", null, text)); };
  const paint = () => {
    const p = players[turn];
    turnBox.style.setProperty("--team", p.color); who.textContent = p.token + " " + p.name;
    actBtn.textContent = mode === "question" ? "❓ " + T.question : "🎲 " + T.roll; actBtn.disabled = busy || over;
    clear(standings);
    players.map((p, i) => [p, pos[i]]).sort((a, b) => b[1] - a[1]).forEach(([p, n]) => standings.append(el("li", { style: "--team:" + p.color }, el("span", null, p.token + " " + p.name), el("b", null, n))));
    place();
  };
  screen(el("div", { class: "snakes" }, wrap, el("div", { class: "spanel" }, turnBox, el("div", { class: "card" }, die, el("div", { class: "row" }, actBtn)),
    el("div", { class: "card" }, el("b", null, T.standings), standings), logCard)));
  paint();
  const sleep = ms => new Promise(res => setTimeout(res, ms));
  async function rollDie() {
    let face = 1;
    for (let k = 0; k < 10; k++) { face = 1 + Math.floor(Math.random() * 6); die.textContent = FACES[face - 1]; Sound.tick(); await sleep(70); }
    return face;
  }
  function ask(title) {
    return new Promise(resolve => {
      const q = Q[qi++ % Q.length];
      const opts = el("div", { class: "qopts" }, q.options.map((o, k) => el("div", { class: "qopt" }, "ABCD"[k] + ") " + o)));
      const after = el("div", { class: "after" });
      const reveal = el("button", { class: "btn", onclick: () => { reveal.remove(); if (q.options.length) opts.children[q.correct].classList.add("right"); else after.prepend(el("div", { class: "answer-box" }, "✔ " + q.answer)); } }, "👁 " + T.reveal);
      const m = modal(el("div", { class: "after" }, el("span", { class: "pill" }, players[turn].token + " " + players[turn].name + " · " + title),
        el("h2", { class: "question" }, q.q), q.options.length ? opts : null, reveal, after,
        el("div", { class: "row" }, el("button", { class: "btn", style: "background:var(--ok);color:#fff", onclick: () => { m.close(); Sound.ok(); resolve(true); } }, "✔ " + T.correct),
          el("button", { class: "btn", style: "background:var(--bad);color:#fff", onclick: () => { m.close(); Sound.bad(); resolve(false); } }, "✖ " + T.wrong))), true);
    });
  }
  async function walk(i, from, to) {
    const step = to > from ? 1 : -1;
    for (let n = from; n !== to; n += step) { pos[i] = n + step; place(); Sound.tick(); await sleep(170); }
  }
  async function act() {
    if (busy || over) return;
    busy = true; paint();
    const i = turn, p = players[i];
    if (mode === "question") {
      const ok = await ask(T.answer_to_move);
      if (!ok) { say(fmt(T.lost_turn, { team: p.name })); return endTurn(false); }
    }
    const n = await rollDie();
    let target = pos[i] + n;
    if (target > B.total) target = G.options.exact_finish ? B.total - (target - B.total) : B.total;
    await walk(i, pos[i], Math.min(pos[i] + n, B.total));
    if (pos[i] !== target) { await walk(i, pos[i], target); say(fmt(T.bounce, { n: target })); }
    say(fmt(T.rolled, { team: p.token + " " + p.name, n, cell: target }));
    const jump = jumps[target];
    if (jump) {
      let follow = true;
      if (mode === "challenge") {
        const ok = await ask(jump.kind === "ladder" ? T.answer_to_climb : T.answer_to_escape);
        follow = jump.kind === "ladder" ? ok : !ok;
        if (!follow) say(jump.kind === "ladder" ? fmt(T.no_climb, { team: p.name }) : fmt(T.saved, { team: p.name }));
      }
      if (follow) {
        await sleep(250); pos[i] = jump.to; place();
        if (jump.kind === "ladder") Sound.ok(); else Sound.bad();
        say(fmt(jump.kind === "ladder" ? T.ladder : T.snake, { from: target, to: jump.to }));
        await sleep(300);
      }
    }
    if (pos[i] >= B.total) {
      over = true; busy = false; paint(); Sound.win(); confetti();
      players.forEach((pl, k) => { pl.score = pos[k]; });
      modal(el("div", { class: "after" }, el("div", { class: "big-emoji" }, p.token), el("h2", null, "🏆 " + fmt(T.wins, { team: p.name })),
        el("button", { class: "btn primary", onclick: () => location.reload() }, "↺ " + T.play_again)));
      return;
    }
    endTurn(n === 6 && G.options.six_again);
  }
  function endTurn(again) {
    if (again) say(T.again); else turn = (turn + 1) % players.length;
    busy = false; paint();
  }
}
"""

WHEEL_CSS = r"""
.wheel-wrap{position:relative;width:min(72vh,92vw);aspect-ratio:1;margin:auto}
.wheel-wrap canvas{width:100%;height:100%;filter:drop-shadow(0 12px 24px rgba(0,0,0,.25))}
.pointer{position:absolute;top:-.6rem;left:50%;transform:translateX(-50%);width:0;height:0;border-left:1.3rem solid transparent;
border-right:1.3rem solid transparent;border-top:2.6rem solid var(--text);z-index:2}
.wheel-hub{position:absolute;inset:0;margin:auto;width:18%;height:18%;border-radius:50%;background:var(--surface);
border:6px solid var(--primary);display:grid;place-items:center;font-size:2rem;cursor:pointer;z-index:2}
.picked{font-size:2.4rem;font-weight:800;text-align:center;max-width:52rem;line-height:1.3}
"""
WHEEL_JS = r"""
function runWheel() {
  let entries = G.data.entries.slice(), angle = 0, spinning = false;
  const COLORS = [G.colors.primary, G.colors.accent].concat(G.team_colors);
  const canvas = el("canvas", { width: 900, height: 900 });
  const hub = el("div", { class: "wheel-hub", title: T.spin, onclick: () => spin() }, "🎯");
  const btn = el("button", { class: "btn primary big", onclick: () => spin() }, "🎡 " + T.spin);
  const draw = () => {
    const ctx = canvas.getContext("2d"), n = entries.length, R = 440, cx = 450, cy = 450;
    ctx.clearRect(0, 0, 900, 900);
    if (!n) { ctx.fillStyle = "#999"; ctx.font = "bold 40px Segoe UI"; ctx.textAlign = "center"; ctx.fillText(T.empty_wheel, cx, cy - 80); return; }
    const seg = 2 * Math.PI / n;
    for (let k = 0; k < n; k++) {
      ctx.beginPath(); ctx.moveTo(cx, cy); ctx.arc(cx, cy, R, angle + k * seg, angle + (k + 1) * seg); ctx.closePath();
      ctx.fillStyle = COLORS[k % COLORS.length]; ctx.fill(); ctx.strokeStyle = "#fff"; ctx.lineWidth = 4; ctx.stroke();
      ctx.save(); ctx.translate(cx, cy); ctx.rotate(angle + (k + 0.5) * seg); ctx.textAlign = "right"; ctx.fillStyle = "#fff";
      const size = n > 18 ? 20 : n > 10 ? 26 : 32; ctx.font = "bold " + size + "px Segoe UI, sans-serif";
      const max = n > 18 ? 24 : 30, text = entries[k].length > max ? entries[k].slice(0, max - 1) + "…" : entries[k];
      ctx.fillText(text, R - 26, size / 3); ctx.restore();
    }
  };
  const indexAt = () => { const n = entries.length, seg = 2 * Math.PI / n; const a = ((-Math.PI / 2 - angle) % (2 * Math.PI) + 4 * Math.PI) % (2 * Math.PI); return Math.floor(a / seg) % n; };
  function spin() {
    if (spinning || !entries.length) return;
    spinning = true; btn.disabled = true;
    const start = angle, total = 2 * Math.PI * (5 + Math.random() * 3) + Math.random() * 2 * Math.PI, dur = (G.options.spin_seconds || 5) * 1000, t0 = performance.now();
    let last = indexAt();
    (function frame(t) {
      const p = Math.min(1, (t - t0) / dur), e = 1 - Math.pow(1 - p, 3);
      angle = start + total * e; draw();
      const idx = indexAt(); if (idx !== last) { last = idx; Sound.tick(); }
      if (p < 1) requestAnimationFrame(frame); else done();
    })(t0);
  }
  function done() {
    spinning = false; btn.disabled = false; Sound.ok();
    const k = indexAt(), text = entries[k];
    const m = modal(el("div", { class: "after" }, el("div", { class: "big-emoji" }, "🎯"), el("div", { class: "picked" }, text),
      el("div", { class: "row" }, G.options.remove ? el("button", { class: "btn primary", onclick: () => { entries.splice(k, 1); m.close(); draw(); } }, "✔ " + T.remove_entry) : null,
        el("button", { class: "btn", onclick: () => m.close() }, T.close))), !!G.options.remove);
  }
  screen(el("div", { class: "wheel-wrap" }, el("div", { class: "pointer" }), canvas, hub), el("div", { class: "row" }, btn));
  draw();
}
"""

BINGO_CSS = r"""
.modes{display:grid;grid-template-columns:1fr 1fr;gap:1rem;width:100%;max-width:52rem}
.mode{text-align:center;display:flex;flex-direction:column;gap:.6rem;align-items:center}
.mode input{font-size:1.4rem;width:7rem;text-align:center;border-radius:10px;border:2px solid rgba(127,127,127,.4);padding:.3rem;background:var(--surface);color:var(--text)}
.current{font-size:3rem;font-weight:900;text-align:center;min-height:6rem;display:grid;place-items:center;padding:1rem 2rem;
background:var(--primary);color:#fff;border-radius:24px;box-shadow:var(--shadow);max-width:60rem;width:100%}
.called{display:flex;flex-wrap:wrap;gap:.4rem;justify-content:center;max-width:70rem}
.called span{background:var(--surface);border-radius:999px;padding:.2rem .7rem;font-size:.85rem;box-shadow:0 1px 3px rgba(0,0,0,.1)}
.called span:first-child{background:var(--accent);color:#fff}
.bcard{display:grid;grid-template-columns:repeat(var(--size),1fr);gap:.4rem;width:min(92vw,40rem)}
.bcell{aspect-ratio:1;border:0;border-radius:12px;background:var(--surface);color:var(--text);box-shadow:var(--shadow);
font-weight:700;font-size:clamp(.6rem,1.6vw,1rem);padding:.3rem;display:grid;place-items:center;text-align:center;cursor:pointer;word-break:break-word}
.bcell.on{background:var(--accent);color:#fff;transform:scale(.96)}
.bcell.free{background:var(--primary);color:#fff}
.bcell.hit{outline:4px solid var(--ok)}
.bhead{display:grid;grid-template-columns:repeat(var(--size),1fr);gap:.4rem;width:min(92vw,40rem);text-align:center;font-weight:900;
font-size:1.6rem;color:var(--primary)}
.banner{font-size:2.6rem;font-weight:900;color:var(--ok);animation:pop .4s ease}
"""
BINGO_JS = r"""
function runBingo() {
  const terms = G.data.terms, cards = G.data.cards, size = G.data.size;
  const label = idx => idx < 0 ? "⭐ " + T.free : terms[idx];
  const status = (card, marked) => {
    const lines = [];
    for (let r = 0; r < size; r++) lines.push([...Array(size).keys()].map(c => r * size + c));
    for (let c = 0; c < size; c++) lines.push([...Array(size).keys()].map(r => r * size + c));
    lines.push([...Array(size).keys()].map(k => k * size + k)); lines.push([...Array(size).keys()].map(k => k * size + size - 1 - k));
    const ok = k => card[k] < 0 || marked.has(card[k]);
    return { lines: lines.filter(l => l.every(ok)).length, full: card.every((_, k) => ok(k)) };
  };
  const winText = st => (G.options.win === "full" ? st.full : st.lines > 0) ? (st.full ? T.bingo : T.line) : "";
  const header = () => size === 5 ? el("div", { class: "bhead", style: "--size:5" }, [..."BINGO"].map(ch => el("span", null, ch))) : null;
  const input = el("input", { type: "number", min: 1, max: cards.length, value: 1 });
  screen(el("div", { class: "intro card" }, el("div", { class: "big-emoji" }, G.emoji), el("h2", null, G.title), G.subtitle ? el("p", { class: "muted" }, G.subtitle) : null,
    el("p", null, el("b", null, T.bingo_mode)),
    el("div", { class: "modes" },
      el("div", { class: "card mode" }, el("div", { class: "big-emoji" }, "🎙"), el("b", null, T.moderator), el("span", { class: "muted" }, T.moderator_desc), el("button", { class: "btn primary", onclick: caller }, T.start + " ▶")),
      el("div", { class: "card mode" }, el("div", { class: "big-emoji" }, "🎟"), el("b", null, T.player), el("span", { class: "muted" }, T.player_desc), el("label", null, T.card_number + " ", input),
        el("button", { class: "btn primary", onclick: () => player(parseInt(input.value, 10)) }, T.open_card))),
    el("div", { class: "row" }, el("button", { class: "btn", onclick: showRules }, "📖 " + T.how_to_play))));

  function player(n) {
    if (!(n >= 1 && n <= cards.length)) { alert(T.invalid_card); return; }
    const card = cards[n - 1], marked = new Set(), banner = el("div", { class: "banner" });
    const grid = el("div", { class: "bcard", style: "--size:" + size }, card.map(idx => {
      const b = el("button", { class: "bcell" + (idx < 0 ? " free" : "") }, label(idx));
      if (idx >= 0) b.addEventListener("click", () => {
        if (marked.has(idx)) marked.delete(idx); else marked.add(idx);
        b.classList.toggle("on"); Sound.pop();
        const text = winText(status(card, marked));
        if (text && banner.textContent !== text) { Sound.win(); confetti(); }
        banner.textContent = text;
      });
      return b;
    }));
    screen(el("span", { class: "pill" }, fmt(T.card_of, { n, total: cards.length })), header(), grid, banner);
  }
  function caller() {
    const order = shuffle([...terms.keys()]), called = [];
    const current = el("div", { class: "current" }, "🎱"), counter = el("span", { class: "pill" }), list = el("div", { class: "called" });
    const drawBtn = el("button", { class: "btn primary big", onclick: drawNext }, "🎱 " + T.draw);
    const check = el("input", { type: "number", min: 1, max: cards.length, placeholder: "#" });
    const paint = () => { counter.textContent = called.length + " / " + terms.length; clear(list); called.slice().reverse().forEach(i => list.append(el("span", null, terms[i]))); };
    screen(counter, current, el("div", { class: "row" }, drawBtn, el("span", null, T.card_number + " "), check, el("button", { class: "btn", onclick: verify }, "🔍 " + T.check_card)),
      el("b", null, T.called), list);
    paint();
    function drawNext() {
      if (!order.length) { current.textContent = T.drawn_all; return; }
      drawBtn.disabled = true; let k = 0;
      const id = setInterval(() => {
        current.textContent = terms[Math.floor(Math.random() * terms.length)]; Sound.tick();
        if (++k > 12) { clearInterval(id); const idx = order.pop(); called.push(idx); current.textContent = terms[idx]; Sound.ok(); drawBtn.disabled = false; paint(); }
      }, 70);
    }
    function verify() {
      const n = parseInt(check.value, 10);
      if (!(n >= 1 && n <= cards.length)) { alert(T.invalid_card); return; }
      const card = cards[n - 1], marked = new Set(called), st = status(card, marked), text = winText(st);
      modal(el("div", { class: "after" }, el("span", { class: "pill" }, fmt(T.card_of, { n, total: cards.length })), header(),
        el("div", { class: "bcard", style: "--size:" + size }, card.map(idx => el("div", { class: "bcell" + (idx < 0 ? " free" : marked.has(idx) ? " on hit" : "") }, label(idx)))),
        el("div", { class: "banner", style: text ? "" : "color:var(--muted)" }, text || T.no_line)));
      if (text) { Sound.win(); confetti(); }
    }
  }
}
"""

WORDSEARCH_CSS = r"""
.ws{display:grid;grid-template-columns:auto minmax(14rem,22rem);gap:1.5rem;align-items:start;justify-content:center;width:100%}
.wsgrid{display:grid;grid-template-columns:repeat(var(--n),1fr);gap:2px;width:min(calc(100vh - 10rem),62vw);aspect-ratio:1;
background:var(--surface);padding:.5rem;border-radius:16px;box-shadow:var(--shadow);user-select:none;touch-action:none}
.wscell{display:grid;place-items:center;font-weight:800;font-size:clamp(.7rem,calc(46vh / var(--n)),1.9rem);border-radius:6px;
cursor:pointer;font-family:Consolas,"Courier New",monospace}
.wscell.sel{background:var(--accent);color:#fff}
.wscell.found{color:#fff}
.wscell.sol{outline:2px dashed var(--bad)}
.wslist{list-style:none;margin:0;padding:0;display:flex;flex-direction:column;gap:.35rem}
.wslist li{background:var(--surface);border-radius:10px;padding:.35rem .7rem;box-shadow:0 1px 4px rgba(0,0,0,.08)}
.wslist li.done{text-decoration:line-through;opacity:.55}
@media (max-width:1000px){.ws{grid-template-columns:1fr}.wsgrid{width:92vw}}
"""
WORDSEARCH_JS = r"""
function runWordsearch() {
  const grid = G.data.grid, P = G.data.placements, words = G.data.words, n = grid.length;
  const HUES = [0, 30, 55, 120, 170, 200, 230, 270, 300, 330];
  const cells = [], found = new Set(); let start = null, dragging = false, t0 = Date.now(), finished = false;
  const clock = el("span", { class: "pill" });
  const tickId = setInterval(() => { if (!finished) clock.textContent = "⏱ " + mmss(); }, 1000);
  const mmss = () => { const s = Math.floor((Date.now() - t0) / 1000); return Math.floor(s / 60) + ":" + String(s % 60).padStart(2, "0"); };
  const box = el("div", { class: "wsgrid", style: "--n:" + n });
  for (let r = 0; r < n; r++) for (let c = 0; c < n; c++) {
    const cell = el("div", { class: "wscell", "data-r": r, "data-c": c }, grid[r][c]); cells.push(cell); box.append(cell);
  }
  const at = (r, c) => cells[r * n + c];
  const line = (a, b) => {
    const dr = Math.sign(b.r - a.r), dc = Math.sign(b.c - a.c), len = Math.max(Math.abs(b.r - a.r), Math.abs(b.c - a.c));
    if (!(a.r === b.r || a.c === b.c || Math.abs(b.r - a.r) === Math.abs(b.c - a.c))) return null;
    return [...Array(len + 1).keys()].map(k => ({ r: a.r + dr * k, c: a.c + dc * k }));
  };
  const items = words.map(w => el("li", null, G.options.use_clues && w.clue ? w.clue : w.label));
  const list = el("ul", { class: "wslist" }, items);
  const counter = el("span", { class: "pill" });
  const paintCount = () => { counter.textContent = T.found + ": " + found.size + " / " + P.length; };
  const clearSel = () => cells.forEach(x => x.classList.remove("sel"));
  const cellOf = e => { const t = document.elementFromPoint(e.clientX, e.clientY); return t && t.classList.contains("wscell") ? { r: +t.dataset.r, c: +t.dataset.c } : null; };
  const preview = b => { clearSel(); const l = start && b ? line(start, b) : null; (l || [start]).forEach(p => p && at(p.r, p.c).classList.add("sel")); };
  const tryWord = (a, b) => {
    const l = line(a, b); if (!l || l.length < 2) return false;
    const last = l[l.length - 1];
    const k = P.findIndex(p => { const er = p.r + p.dr * (p.word.length - 1), ec = p.c + p.dc * (p.word.length - 1);
      return (p.r === a.r && p.c === a.c && er === last.r && ec === last.c) || (p.r === last.r && p.c === last.c && er === a.r && ec === a.c); });
    if (k < 0 || found.has(k)) return false;
    found.add(k); mark(k, false); Sound.ok(); paintCount();
    if (found.size === P.length) { finished = true; Sound.win(); confetti(); modal(el("div", { class: "after" }, el("div", { class: "big-emoji" }, "🏆"), el("h2", null, fmt(T.all_found, { time: mmss() })))); }
    return true;
  };
  const mark = (k, solution) => {
    const p = P[k], color = "hsl(" + HUES[k % HUES.length] + " 70% 45%)";
    for (let i = 0; i < p.word.length; i++) { const x = at(p.r + p.dr * i, p.c + p.dc * i); if (solution) x.classList.add("sol"); else { x.classList.add("found"); x.style.background = color; } }
    const w = words.findIndex(w => w.word === p.word); if (w >= 0 && !solution) { items[w].classList.add("done"); items[w].textContent = words[w].label; }
  };
  box.addEventListener("pointerdown", e => { const p = cellOf(e); if (!p) return; e.preventDefault();
    if (start && !(start.r === p.r && start.c === p.c)) { const ok = tryWord(start, p); if (!ok) Sound.bad(); start = null; clearSel(); return; }
    start = p; dragging = true; preview(p); });
  box.addEventListener("pointermove", e => { if (dragging && start) preview(cellOf(e)); });
  box.addEventListener("pointerup", e => { if (!dragging) return; dragging = false; const p = cellOf(e);
    if (p && start && !(p.r === start.r && p.c === start.c)) { const ok = tryWord(start, p); if (!ok) Sound.bad(); start = null; clearSel(); } });
  intro(P.length, () => {
    t0 = Date.now(); paintCount();
    screen(el("div", { class: "qhead" }, counter, el("span", { class: "muted" }, T.select_hint), clock),
      el("div", { class: "ws" }, box, el("div", { class: "after" }, list, el("button", { class: "btn", onclick: () => P.forEach((_, k) => { if (!found.has(k)) mark(k, true); }) }, "👁 " + T.show_solutions)))).cleanup = () => clearInterval(tickId);
  });
}
"""

TRUTHS_CSS = r"""
.person{font-size:2.4rem;font-weight:900;color:var(--primary)}
body.dark .person{color:var(--accent)}
.stmts{display:grid;grid-template-columns:repeat(3,1fr);gap:1rem;width:100%;max-width:76rem}
.stmt{display:flex;flex-direction:column;gap:.8rem;justify-content:space-between;font-size:1.35rem;font-weight:600;min-height:12rem;
border-top:10px solid var(--accent);transition:transform .3s}
.stmt .num{font-size:2.4rem;font-weight:900;color:var(--accent)}
.stmt .vote{display:flex;align-items:center;gap:.5rem;justify-content:flex-end;font-size:1rem}
.stmt.lie{border-color:var(--bad);transform:scale(1.04)}.stmt.truth{border-color:var(--ok);opacity:.7}
.stmt .tag{font-weight:900;font-size:1.6rem}
.stmt.lie .tag{color:var(--bad)}.stmt.truth .tag{color:var(--ok)}
@media (max-width:900px){.stmts{grid-template-columns:1fr}}
"""
TRUTHS_JS = r"""
function runTruths() {
  const people = G.data.people; let i = 0;
  intro(people.length, show);
  function show() {
    if (i >= people.length) return podium();
    const p = people[i], after = el("div", { class: "after" });
    const cards = p.statements.map((s, k) => { let votes = 0; const count = el("b", null, "0");
      const card = el("div", { class: "card stmt" }, el("span", { class: "num" }, k + 1), el("span", null, s), el("span", { class: "tag" }),
        el("div", { class: "vote" }, el("span", { class: "muted" }, "🗳"), count, el("button", { class: "mini", title: T.votes, onclick: () => { votes += 1; count.textContent = votes; Sound.pop(); } }, "+")));
      return card; });
    const btn = el("button", { class: "btn primary big", onclick: () => {
      btn.remove(); cards.forEach((c, k) => { c.classList.add(k === p.lie ? "lie" : "truth"); c.querySelector(".tag").textContent = k === p.lie ? "🤥 " + T.lie : "✔ " + T.truth; });
      Sound.ok(); after.append(el("button", { class: "btn primary big", onclick: () => { i += 1; show(); } }, T.next + " ▶")); } }, "🤥 " + T.reveal_lie);
    screen(el("div", { class: "qhead" }, el("span", { class: "pill" }, fmt(T.person_of, { n: i + 1, total: people.length })), el("span", { class: "muted" }, T.two_truths)),
      el("div", { class: "person" }, "🙋 " + p.person), el("div", { class: "stmts" }, cards), el("div", { class: "row" }, btn), after);
  }
}
"""

WOULDRATHER_CSS = r"""
.wr{display:grid;grid-template-columns:1fr auto 1fr;gap:1rem;align-items:stretch;width:100%;max-width:80rem}
.wrside{border:0;border-radius:24px;color:#fff;font-size:1.9rem;font-weight:800;padding:2rem 1.5rem;min-height:15rem;cursor:pointer;
display:flex;flex-direction:column;justify-content:space-between;gap:1rem;box-shadow:var(--shadow);text-align:center;transition:transform .1s}
.wrside:active{transform:scale(.98)}
.wrside.a{background:var(--primary)}.wrside.b{background:var(--accent)}
.wrside .count{font-size:1.1rem;opacity:.9}
.vs{align-self:center;font-size:2rem;font-weight:900;background:var(--surface);border-radius:50%;width:4.5rem;height:4.5rem;display:grid;place-items:center;box-shadow:var(--shadow)}
.bars{width:100%;max-width:60rem;display:flex;flex-direction:column;gap:.5rem}
.bar{position:relative;height:2.6rem;border-radius:12px;background:rgba(127,127,127,.15);overflow:hidden}
.bar .fill{position:absolute;inset:0 auto 0 0;width:0;transition:width .8s ease}
.bar .label{position:relative;display:flex;align-items:center;height:100%;padding:0 1rem;font-weight:800;white-space:nowrap;
color:var(--text);text-shadow:0 0 6px var(--surface),0 0 2px var(--surface)}
@media (max-width:900px){.wr{grid-template-columns:1fr}.vs{justify-self:center}}
"""
WOULDRATHER_JS = r"""
function runWouldRather() {
  const pairs = G.data.pairs; let i = 0;
  intro(pairs.length, show);
  function show() {
    if (i >= pairs.length) return podium();
    const p = pairs[i], votes = [0, 0], after = el("div", { class: "after" });
    const counts = [el("span", { class: "count" }, "🗳 0"), el("span", { class: "count" }, "🗳 0")];
    const vote = k => { votes[k] += 1; counts[k].textContent = "🗳 " + votes[k]; Sound.pop(); };
    const onKey = e => { if (e.key === "a" || e.key === "A" || e.key === "1") vote(0); if (e.key === "b" || e.key === "B" || e.key === "2") vote(1); };
    document.addEventListener("keydown", onKey);
    const btn = el("button", { class: "btn primary big", onclick: () => {
      btn.remove(); const total = votes[0] + votes[1] || 1;
      const bars = el("div", { class: "bars" }, [0, 1].map(k => el("div", { class: "bar" },
        el("span", { class: "fill", style: "background:" + (k ? "var(--accent)" : "var(--primary)") + ";opacity:.85" }),
        el("span", { class: "label" }, Math.round(100 * votes[k] / total) + "% · " + (k ? "B" : "A") + " · " + (k ? p.b : p.a)))));
      after.append(bars, el("button", { class: "btn primary big", onclick: () => { i += 1; show(); } }, T.next + " ▶"));
      requestAnimationFrame(() => setTimeout(() => [...bars.querySelectorAll(".fill")].forEach((s, k) => { s.style.width = (100 * votes[k] / total) + "%"; }), 30));
      Sound.ok(); } }, "📊 " + T.show_results);
    screen(el("div", { class: "qhead" }, el("span", { class: "pill" }, fmt(T.round_of, { n: i + 1, total: pairs.length })), el("b", null, T.would_you_rather)),
      el("div", { class: "wr" }, el("button", { class: "wrside a", onclick: () => vote(0) }, el("span", null, "A"), el("span", null, p.a), counts[0]),
        el("div", { class: "vs" }, "VS"), el("button", { class: "wrside b", onclick: () => vote(1) }, el("span", null, "B"), el("span", null, p.b), counts[1])),
      el("div", { class: "row" }, btn), after).cleanup = () => document.removeEventListener("keydown", onKey);
  }
}
"""

ENGINES = {
    "quiz": (QUIZ_CSS, QUIZ_JS, "runQuiz"),
    "trivia": (TRIVIA_CSS, TRIVIA_JS, "runTrivia"),
    "hangman": (HANGMAN_CSS, HANGMAN_JS, "runHangman"),
    "guess": (GUESS_CSS, GUESS_JS, "runGuess"),
    "snakes": (SNAKES_CSS + QUIZ_CSS, SNAKES_JS, "runSnakes"),
    "wheel": (WHEEL_CSS, WHEEL_JS, "runWheel"),
    "bingo": (BINGO_CSS, BINGO_JS, "runBingo"),
    "wordsearch": (WORDSEARCH_CSS, WORDSEARCH_JS, "runWordsearch"),
    "truths": (TRUTHS_CSS, TRUTHS_JS, "runTruths"),
    "wouldrather": (WOULDRATHER_CSS, WOULDRATHER_JS, "runWouldRather"),
}
