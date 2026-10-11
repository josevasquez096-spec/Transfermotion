import { J, N } from './skeleton.js';

const add = (p, a, len) => ({ x: p.x + Math.cos(a) * len, y: p.y + Math.sin(a) * len, v: 1 });

export const DEMO_SIZE = { w: 640, h: 480 };

// Coreografía procedimental (no requiere video ni IA) para probar la app al instante.
export function demoPose(t) {
  const P = Math.PI;
  const beat = t * 3.2;
  const out = new Array(N);
  const bounce = Math.abs(Math.sin(beat)) * 12;
  const pelvis = { x: 320 + Math.sin(t * 1.6) * 60, y: 280 - bounce, v: 1 };
  const spine = -P / 2 + Math.sin(t * 1.6) * 0.18;
  out[J.pelvis] = pelvis;
  out[J.chest] = add(pelvis, spine, 105);
  out[J.head] = add(out[J.chest], spine + Math.sin(beat) * 0.25, 52);
  out[J.lsh] = add(out[J.chest], spine + P / 2, 38);
  out[J.rsh] = add(out[J.chest], spine - P / 2, 38);

  // Brazos: suben y bajan en alternancia, con codos flexionados.
  const la = 1.3 + 1.2 * Math.sin(beat);
  const ra = 1.3 + 1.2 * Math.sin(beat + P);
  const lUpper = P / 2 - la, rUpper = P / 2 + ra;
  const lFore = lUpper - 0.5 - 0.5 * Math.sin(beat * 2);
  const rFore = rUpper + 0.5 + 0.5 * Math.sin(beat * 2 + P);
  out[J.lel] = add(out[J.lsh], lUpper, 62);
  out[J.rel] = add(out[J.rsh], rUpper, 62);
  out[J.lwr] = add(out[J.lel], lFore, 56);
  out[J.rwr] = add(out[J.rel], rFore, 56);
  out[J.lhand] = add(out[J.lwr], lFore, 18);
  out[J.rhand] = add(out[J.rwr], rFore, 18);

  // Piernas: flexión rítmica y paso lateral.
  const kick = Math.sin(beat) * 0.35;
  out[J.lhip] = add(pelvis, spine + P / 2, 22);
  out[J.rhip] = add(pelvis, spine - P / 2, 22);
  const lTh = P / 2 - 0.12 - Math.max(0, kick);
  const rTh = P / 2 + 0.12 + Math.max(0, -kick);
  out[J.lkn] = add(out[J.lhip], lTh, 78);
  out[J.rkn] = add(out[J.rhip], rTh, 78);
  out[J.lan] = add(out[J.lkn], lTh + Math.max(0, kick) * 1.4, 76);
  out[J.ran] = add(out[J.rkn], rTh - Math.max(0, -kick) * 1.4, 76);
  out[J.lft] = add(out[J.lan], 0.3, 20);
  out[J.rft] = add(out[J.ran], P - 0.3, 20);
  return out;
}

// Personaje de ejemplo dibujado en un canvas, con su esqueleto de reposo conocido.
export function demoCharacter() {
  const w = 420, h = 640;
  const c = document.createElement('canvas');
  c.width = w; c.height = h;
  const g = c.getContext('2d');
  const R = (x, y) => ({ x, y, v: 1 });
  const rest = new Array(N);
  Object.assign(rest, {
    [J.pelvis]: R(210, 340), [J.chest]: R(210, 175), [J.head]: R(210, 95),
    [J.lsh]: R(262, 182), [J.rsh]: R(158, 182), [J.lel]: R(292, 262), [J.rel]: R(128, 262),
    [J.lwr]: R(310, 340), [J.rwr]: R(110, 340), [J.lhand]: R(316, 366), [J.rhand]: R(104, 366),
    [J.lhip]: R(238, 352), [J.rhip]: R(182, 352), [J.lkn]: R(244, 465), [J.rkn]: R(176, 465),
    [J.lan]: R(246, 575), [J.ran]: R(174, 575), [J.lft]: R(270, 600), [J.rft]: R(150, 600),
  });

  const limb = (a, b, width, color) => {
    g.strokeStyle = color; g.lineWidth = width; g.lineCap = 'round';
    g.beginPath(); g.moveTo(rest[a].x, rest[a].y); g.lineTo(rest[b].x, rest[b].y); g.stroke();
  };
  const skin = '#f2c29b', shirt = '#ff5d8f', pants = '#3b4cca', shoe = '#22252e';

  // Piernas y zapatos
  for (const [hip, kn, an, ft] of [[J.lhip, J.lkn, J.lan, J.lft], [J.rhip, J.rkn, J.ran, J.rft]]) {
    limb(hip, kn, 44, pants); limb(kn, an, 38, pants);
    limb(an, ft, 26, shoe);
  }
  // Torso
  g.fillStyle = shirt;
  g.beginPath();
  g.roundRect(150, 160, 120, 200, 34);
  g.fill();
  g.fillStyle = 'rgba(255,255,255,0.9)';
  g.font = 'bold 34px system-ui, sans-serif';
  g.textAlign = 'center';
  g.fillText('TM', 210, 270);
  // Cuello
  limb(J.chest, J.head, 30, skin);
  // Brazos
  for (const [sh, el, wr, hand] of [[J.lsh, J.lel, J.lwr, J.lhand], [J.rsh, J.rel, J.rwr, J.rhand]]) {
    limb(sh, el, 32, shirt);
    limb(el, wr, 26, skin);
    g.fillStyle = skin;
    g.beginPath(); g.arc(rest[hand].x, rest[hand].y, 16, 0, Math.PI * 2); g.fill();
  }
  // Cabeza
  g.fillStyle = skin;
  g.beginPath(); g.arc(210, 92, 56, 0, Math.PI * 2); g.fill();
  g.fillStyle = '#3a2418';
  g.beginPath(); g.arc(210, 80, 58, Math.PI * 1.05, Math.PI * 1.95); g.fill();
  g.fillStyle = '#22252e';
  g.beginPath(); g.arc(190, 95, 6, 0, Math.PI * 2); g.arc(230, 95, 6, 0, Math.PI * 2); g.fill();
  g.strokeStyle = '#22252e'; g.lineWidth = 4; g.lineCap = 'round';
  g.beginPath(); g.arc(210, 108, 16, 0.15 * Math.PI, 0.85 * Math.PI); g.stroke();

  return { canvas: c, rest };
}
