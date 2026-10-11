// Esqueleto simplificado de 19 articulaciones derivado de MediaPipe Pose (33 puntos).
// Convención: "l" = izquierda de la persona (aparece a la derecha de la pantalla si mira a cámara).

export const J = {
  pelvis: 0, chest: 1, head: 2,
  lsh: 3, rsh: 4, lel: 5, rel: 6, lwr: 7, rwr: 8, lhand: 9, rhand: 10,
  lhip: 11, rhip: 12, lkn: 13, rkn: 14, lan: 15, ran: 16, lft: 17, rft: 18,
};
export const N = 19;

// Padre de cada articulación. El hueso i une PARENT[i] -> i (el hueso 0 no existe).
// Siempre PARENT[i] < i, así que recorrer en orden equivale a recorrer el árbol.
export const PARENT = [-1, 0, 1, 1, 1, 3, 4, 5, 6, 7, 8, 0, 0, 11, 12, 13, 14, 15, 16];

// Capa de dibujo por hueso: lo de atrás primero (torso), luego piernas, cabeza y brazos.
export const LAYER = [0, 0, 2, 2, 2, 3, 3, 3, 3, 3, 3, 0, 0, 1, 1, 1, 1, 1, 1];
export const LAYERS = 4;

export const VIS = 0.5;

// Índices de MediaPipe usados para cada articulación (pelvis y pecho son puntos medios).
const MP = {
  head: 0, lsh: 11, rsh: 12, lel: 13, rel: 14, lwr: 15, rwr: 16, lhand: 19, rhand: 20,
  lhip: 23, rhip: 24, lkn: 25, rkn: 26, lan: 27, ran: 28, lft: 31, rft: 32,
};
const MIRROR_SWAP = {
  11: 12, 12: 11, 13: 14, 14: 13, 15: 16, 16: 15, 19: 20, 20: 19,
  23: 24, 24: 23, 25: 26, 26: 25, 27: 28, 28: 27, 31: 32, 32: 31,
};

// Convierte landmarks normalizados de MediaPipe a articulaciones en píxeles.
// Con `mirror` se refleja horizontalmente y se intercambian lados (vista tipo espejo).
export function fromLandmarks(lm, w, h, mirror = false) {
  const pt = (i) => {
    const p = lm[mirror ? (MIRROR_SWAP[i] ?? i) : i];
    return { x: (mirror ? 1 - p.x : p.x) * w, y: p.y * h, v: p.visibility ?? 1 };
  };
  const mid = (a, b) => ({ x: (a.x + b.x) / 2, y: (a.y + b.y) / 2, v: Math.min(a.v, b.v) });
  const out = new Array(N);
  for (const [name, idx] of Object.entries(MP)) out[J[name]] = pt(idx);
  out[J.pelvis] = mid(out[J.lhip], out[J.rhip]);
  out[J.chest] = mid(out[J.lsh], out[J.rsh]);
  return out;
}

export const dist = (a, b) => Math.hypot(a.x - b.x, a.y - b.y);

// Datos de la pose de reposo del personaje: longitud y ángulo de cada hueso.
export function restInfo(rest) {
  const len = new Float32Array(N);
  const ang = new Float32Array(N);
  for (let i = 1; i < N; i++) {
    const p = rest[PARENT[i]];
    len[i] = dist(p, rest[i]);
    ang[i] = Math.atan2(rest[i].y - p.y, rest[i].x - p.x);
  }
  return { len, ang, torso: len[J.chest] || 1 };
}

// Retargeting: toma la dirección de cada hueso del video fuente y la aplica
// con las longitudes de hueso del personaje, conservando sus proporciones.
export function retarget(rest, info, src, root) {
  const out = new Array(N);
  const delta = new Float32Array(N);
  out[0] = root;
  const girdle = {
    [J.lsh]: lineTilt(rest, src, J.rsh, J.lsh),
    [J.rsh]: lineTilt(rest, src, J.rsh, J.lsh),
    [J.lhip]: lineTilt(rest, src, J.rhip, J.lhip),
    [J.rhip]: lineTilt(rest, src, J.rhip, J.lhip),
  };
  for (let i = 1; i < N; i++) {
    const p = PARENT[i];
    const dx = src[i].x - src[p].x;
    const dy = src[i].y - src[p].y;
    let a;
    if (girdle[i]) {
      // Hombros y caderas: siguen la columna y se inclinan con la línea de hombros/caderas
      // solo en la medida en que esa línea sea fiable (si la persona gira, se acorta).
      const spine = delta[J.chest];
      const { tilt, conf } = girdle[i];
      a = info.ang[i] + spine + conf * wrap(tilt - spine);
    } else if (src[i].v >= VIS && src[p].v >= VIS && dx * dx + dy * dy > 1e-6) {
      a = Math.atan2(dy, dx);
    } else {
      // Articulación no visible: hereda la rotación del hueso padre.
      a = info.ang[i] + delta[p];
    }
    delta[i] = a - info.ang[i];
    out[i] = { x: out[p].x + Math.cos(a) * info.len[i], y: out[p].y + Math.sin(a) * info.len[i], v: 1 };
  }
  return out;
}

const wrap = (a) => Math.atan2(Math.sin(a), Math.cos(a));

// Rotación de la línea a->b (hombros o caderas) respecto al reposo, y cuán fiable es.
function lineTilt(rest, src, a, b) {
  const ra = Math.atan2(rest[b].y - rest[a].y, rest[b].x - rest[a].x);
  if (src[a].v < VIS || src[b].v < VIS) return { tilt: 0, conf: 0 };
  const sa = Math.atan2(src[b].y - src[a].y, src[b].x - src[a].x);
  const srcTorso = dist(src[J.pelvis], src[J.chest]) || 1;
  const restTorso = dist(rest[J.pelvis], rest[J.chest]) || 1;
  const ratio = dist(src[a], src[b]) / srcTorso / (dist(rest[a], rest[b]) / restTorso || 1);
  const conf = Math.min(1, Math.max(0, (ratio - 0.35) / 0.4));
  return { tilt: wrap(sa - ra), conf };
}

// Transformación 2D (rotación + escala + traslación) de cada hueso, de reposo a pose.
// Formato por hueso: [k·cos, k·sin, tx, ty].
export function boneTransforms(rest, posed, out = new Float32Array(N * 4)) {
  out[0] = 1; out[1] = 0;
  out[2] = posed[0].x - rest[0].x;
  out[3] = posed[0].y - rest[0].y;
  for (let i = 1; i < N; i++) {
    const A = rest[PARENT[i]], B = rest[i], A2 = posed[PARENT[i]], B2 = posed[i];
    const ux = B.x - A.x, uy = B.y - A.y, vx = B2.x - A2.x, vy = B2.y - A2.y;
    const l2 = ux * ux + uy * uy || 1;
    // Número complejo v/u = k·e^{iθ}
    const c = (vx * ux + vy * uy) / l2;
    const s = (vy * ux - vx * uy) / l2;
    out[i * 4] = c;
    out[i * 4 + 1] = s;
    out[i * 4 + 2] = A2.x - (c * A.x - s * A.y);
    out[i * 4 + 3] = A2.y - (s * A.x + c * A.y);
  }
  return out;
}

// Conexiones para dibujar el esqueleto.
export const EDGES = PARENT.map((p, i) => [p, i]).filter(([p]) => p >= 0);

export function drawSkeleton(ctx, joints, { ox = 0, oy = 0, scale = 1, color = '#7cf3c6', radius = 4, highlight = -1 } = {}) {
  ctx.save();
  ctx.lineCap = 'round';
  ctx.lineWidth = Math.max(2, radius * 0.75);
  for (const [a, b] of EDGES) {
    const A = joints[a], B = joints[b];
    if ((A.v ?? 1) < VIS || (B.v ?? 1) < VIS) continue;
    const left = [3, 5, 7, 9, 11, 13, 15, 17].includes(b);
    ctx.strokeStyle = left ? '#ffb347' : color;
    ctx.beginPath();
    ctx.moveTo(ox + A.x * scale, oy + A.y * scale);
    ctx.lineTo(ox + B.x * scale, oy + B.y * scale);
    ctx.stroke();
  }
  joints.forEach((p, i) => {
    if ((p.v ?? 1) < VIS) return;
    ctx.fillStyle = i === highlight ? '#ffffff' : '#0d0f14';
    ctx.strokeStyle = i === highlight ? '#ff5d8f' : color;
    ctx.lineWidth = 2;
    ctx.beginPath();
    ctx.arc(ox + p.x * scale, oy + p.y * scale, i === highlight ? radius * 1.6 : radius, 0, Math.PI * 2);
    ctx.fill();
    ctx.stroke();
  });
  ctx.restore();
}
