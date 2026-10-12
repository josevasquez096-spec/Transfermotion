import { N, PARENT, J, dist } from './skeleton.js';

// El personaje se divide en capas independientes (cuerpo, brazos y piernas), como un
// recortable de papel. Así un brazo pegado al cuerpo puede separarse sin arrastrar
// piel del torso, y el hueco que deja en el torso se rellena con colores vecinos.

const PART = { none: 0, body: 1, larm: 2, rarm: 3, lleg: 4, rleg: 5 };
const PARTS = 6;

// Huesos (índice = articulación hija) que deforman cada capa.
const PART_BONES = {
  [PART.body]: [J.chest, J.head, J.lsh, J.rsh, J.lhip, J.rhip],
  [PART.larm]: [J.lsh, J.lel, J.lwr, J.lhand],
  [PART.rarm]: [J.rsh, J.rel, J.rwr, J.rhand],
  [PART.lleg]: [J.lhip, J.lkn, J.lan, J.lft],
  [PART.rleg]: [J.rhip, J.rkn, J.ran, J.rft],
};

// Capa a la que pertenece cada hueso.
const BONE_PART = new Uint8Array(N).fill(PART.body);
for (const p of [PART.larm, PART.rarm, PART.lleg, PART.rleg]) {
  for (const b of PART_BONES[p].slice(1)) BONE_PART[b] = p;
}

// Grosor aproximado de cada extremidad, relativo a la longitud del torso.
const RADIUS = {
  [J.lel]: 0.14, [J.rel]: 0.14, [J.lwr]: 0.11, [J.rwr]: 0.11, [J.lhand]: 0.17, [J.rhand]: 0.17,
  [J.lkn]: 0.2, [J.rkn]: 0.2, [J.lan]: 0.15, [J.ran]: 0.15, [J.lft]: 0.14, [J.rft]: 0.14,
};
const ARM_BONES = [J.lel, J.rel, J.lwr, J.rwr, J.lhand, J.rhand];
const LEG_BONES = [J.lkn, J.rkn, J.lan, J.ran, J.lft, J.rft];

// Orden de dibujo: cuerpo detrás, luego piernas y brazos delante.
const DRAW_ORDER = [PART.body, PART.lleg, PART.rleg, PART.larm, PART.rarm];

function segDist(px, py, A, B) {
  const ux = B.x - A.x, uy = B.y - A.y;
  const l2 = ux * ux + uy * uy;
  let t = l2 > 0 ? ((px - A.x) * ux + (py - A.y) * uy) / l2 : 0;
  t = Math.max(0, Math.min(1, t));
  return Math.hypot(px - (A.x + t * ux), py - (A.y + t * uy));
}

// Cuadrilátero del torso (hombros-caderas) escalado respecto a su centro.
function torsoQuad(rest, scale) {
  const q = [J.lsh, J.rsh, J.rhip, J.lhip].map((i) => rest[i]);
  const cx = q.reduce((s, p) => s + p.x, 0) / 4, cy = q.reduce((s, p) => s + p.y, 0) / 4;
  return q.map((p) => ({ x: cx + (p.x - cx) * scale, y: cy + (p.y - cy) * scale }));
}

// Silueta aproximada del torso: los hombros y sobre todo las caderas (cuyas
// articulaciones quedan dentro del cuerpo) se ensanchan hacia fuera.
function torsoShape(rest) {
  const out = (j, c, k) => ({ x: rest[c].x + (rest[j].x - rest[c].x) * k, y: rest[c].y + (rest[j].y - rest[c].y) * k });
  return [out(J.lsh, J.chest, 1.2), out(J.rsh, J.chest, 1.2), out(J.rhip, J.pelvis, 1.8), out(J.lhip, J.pelvis, 1.8)];
}

function insideConvex(poly, x, y) {
  let sign = 0;
  for (let i = 0; i < poly.length; i++) {
    const a = poly[i], b = poly[(i + 1) % poly.length];
    const c = (b.x - a.x) * (y - a.y) - (b.y - a.y) * (x - a.x);
    if (c !== 0) {
      if (sign && Math.sign(c) !== sign) return false;
      sign = Math.sign(c);
    }
  }
  return true;
}

function blockVisible(data, w, h, x, y, st) {
  for (let j = y; j < Math.min(h, y + st); j++) {
    for (let i = x; i < Math.min(w, x + st); i++) if (data[(j * w + i) * 4 + 3] > 12) return true;
  }
  return false;
}

function fill(labels, w, h, x, y, st, v) {
  for (let j = y; j < Math.min(h, y + st); j++) {
    for (let i = x; i < Math.min(w, x + st); i++) labels[j * w + i] = v;
  }
}

// Asigna cada píxel visible a una capa.
function labelPixels(imageData, rest, scale) {
  const { width: w, height: h, data } = imageData;
  const labels = new Uint8Array(w * h);
  const torso = torsoShape(rest);
  const seg = [];
  for (let b = 1; b < N; b++) seg[b] = [rest[PARENT[b]], rest[b]];
  const d = new Float32Array(N);
  // En imágenes grandes se etiqueta 1 de cada 2×2 píxeles y se copia al bloque (4 veces más rápido).
  const st = w * h > 700000 ? 2 : 1;
  for (let y = 0; y < h; y += st) {
    for (let x = 0; x < w; x += st) {
      const i = y * w + x;
      if (data[i * 4 + 3] <= 12 && (st === 1 || !blockVisible(data, w, h, x, y, st))) continue;
      for (let b = 1; b < N; b++) d[b] = segDist(x, y, seg[b][0], seg[b][1]);
      // 1) Dentro del grosor de un brazo o pierna: es extremidad (los brazos tienen prioridad).
      let best = 0, bq = 1;
      for (const b of ARM_BONES) { const q = d[b] / (RADIUS[b] * scale); if (q < bq) { bq = q; best = b; } }
      if (!best) for (const b of LEG_BONES) { const q = d[b] / (RADIUS[b] * scale); if (q < bq) { bq = q; best = b; } }
      if (best) { fill(labels, w, h, x, y, st, BONE_PART[best]); continue; }
      // 2) Cerca (pero fuera) del grosor estimado de una extremidad y fuera del torso:
      //    probablemente una manga ancha. Lo demás (pelo, torso, cabeza) es cuerpo.
      let nb = 1;
      for (let b = 2; b < N; b++) if (d[b] < d[nb]) nb = b;
      const limb = BONE_PART[nb] !== PART.body;
      if (limb && d[nb] < 1.8 * RADIUS[nb] * scale && !insideConvex(torso, x, y)) {
        fill(labels, w, h, x, y, st, BONE_PART[nb]);
        continue;
      }
      let bb = 1;
      for (let b = 2; b < N; b++) if (BONE_PART[b] === PART.body && d[b] < d[bb]) bb = b;
      fill(labels, w, h, x, y, st, BONE_PART[bb]);
    }
  }
  return labels;
}

// Rellena los huecos (known=0) con los colores vecinos usando "push-pull" multiescala.
function fillHoles(rgb, known, w, h) {
  const levels = [{ rgb, wt: known, w, h }];
  while (levels.at(-1).w > 1 || levels.at(-1).h > 1) {
    const L = levels.at(-1);
    const nw = Math.max(1, Math.ceil(L.w / 2)), nh = Math.max(1, Math.ceil(L.h / 2));
    const c = new Float32Array(nw * nh * 3), wt = new Float32Array(nw * nh);
    for (let y = 0; y < L.h; y++) {
      for (let x = 0; x < L.w; x++) {
        const s = y * L.w + x, t = (y >> 1) * nw + (x >> 1), k = L.wt[s];
        if (!k) continue;
        wt[t] += k;
        c[t * 3] += L.rgb[s * 3] * k; c[t * 3 + 1] += L.rgb[s * 3 + 1] * k; c[t * 3 + 2] += L.rgb[s * 3 + 2] * k;
      }
    }
    for (let t = 0; t < nw * nh; t++) {
      if (wt[t] > 0) { c[t * 3] /= wt[t]; c[t * 3 + 1] /= wt[t]; c[t * 3 + 2] /= wt[t]; }
      wt[t] = Math.min(1, wt[t]);
    }
    levels.push({ rgb: c, wt, w: nw, h: nh });
  }
  for (let l = levels.length - 2; l >= 0; l--) {
    const L = levels[l], C = levels[l + 1];
    for (let y = 0; y < L.h; y++) {
      for (let x = 0; x < L.w; x++) {
        const s = y * L.w + x, k = L.wt[s];
        if (k >= 1) continue;
        const t = (y >> 1) * C.w + (x >> 1);
        for (let ch = 0; ch < 3; ch++) L.rgb[s * 3 + ch] = L.rgb[s * 3 + ch] * k + C.rgb[t * 3 + ch] * (1 - k);
        L.wt[s] = 1;
      }
    }
  }
}

// Crea las texturas por capa en un atlas: mitad izquierda = cuerpo (con huecos
// rellenados), mitad derecha = solo extremidades.
function buildAtlas(imageData, labels, rest) {
  const { width: w, height: h, data } = imageData;
  const n = w * h;
  const torso = torsoQuad(rest, 1.0);
  const body = new Uint8ClampedArray(n * 4);
  const limbs = new Uint8ClampedArray(n * 4);
  const rgb = new Float32Array(n * 3);
  const known = new Float32Array(n);
  const hole = new Uint8Array(n);
  for (let i = 0; i < n; i++) {
    rgb[i * 3] = data[i * 4]; rgb[i * 3 + 1] = data[i * 4 + 1]; rgb[i * 3 + 2] = data[i * 4 + 2];
    const lab = labels[i];
    if (lab === PART.body) {
      known[i] = 1;
      body.set(data.subarray(i * 4, i * 4 + 4), i * 4);
    } else if (lab) {
      limbs.set(data.subarray(i * 4, i * 4 + 4), i * 4);
      // Lo que la extremidad tapaba dentro del torso se rellena y se vuelve opaco.
      if (insideConvex(torso, i % w, (i / w) | 0)) hole[i] = 1;
    }
  }
  fillHoles(rgb, known, w, h);
  for (let i = 0; i < n; i++) {
    if (!hole[i]) continue;
    body[i * 4] = rgb[i * 3]; body[i * 4 + 1] = rgb[i * 3 + 1]; body[i * 4 + 2] = rgb[i * 3 + 2]; body[i * 4 + 3] = 255;
  }
  // Textura de la cara: la imagen original sin las extremidades (una mano en la mejilla se
  // rellena con los colores de alrededor; si no, quedaría pintada en la cabeza al moverse).
  const faceImg = new Uint8ClampedArray(data);
  for (let i = 0; i < n; i++) {
    if (labels[i] <= PART.body) continue;
    faceImg[i * 4] = rgb[i * 3]; faceImg[i * 4 + 1] = rgb[i * 3 + 1]; faceImg[i * 4 + 2] = rgb[i * 3 + 2];
  }
  const face = document.createElement('canvas');
  face.width = w;
  face.height = h;
  face.getContext('2d').putImageData(new ImageData(faceImg, w, h), 0, 0);
  const atlas = document.createElement('canvas');
  atlas.width = w * 2;
  atlas.height = h;
  const g = atlas.getContext('2d');
  g.putImageData(new ImageData(body, w, h), 0, 0);
  g.putImageData(new ImageData(limbs, w, h), w, 0);
  return { atlas, bodyAlpha: body, face };
}

// Los 4 huesos (de `bones`) con más influencia sobre el punto (x, y), con pesos normalizados.
// La usan las mallas de las capas y el borde de la malla de la cara, para que coincidan.
export const BODY_BONES = PART_BONES[PART.body];
export function skinWeights(rest, scale, x, y, bones = BODY_BONES) {
  const ws = bones
    .map((bone) => {
      const r = segDist(x, y, rest[PARENT[bone]], rest[bone]) / scale;
      return [bone, 1 / Math.pow(r * r + 0.003, 2)];
    })
    .sort((p, q) => q[1] - p[1])
    .slice(0, 4);
  const sum = ws.reduce((acc, [, wt]) => acc + wt, 0);
  return ws.map(([b, wt]) => [b, wt / sum]);
}

// Construye las mallas (una por capa, sin vértices compartidos) con pesos de skinning.
export function buildRig(imageData, rest) {
  const { width: w, height: h } = imageData;
  const scale = dist(rest[J.pelvis], rest[J.chest]) || h / 3;
  const labels = labelPixels(imageData, rest, scale);
  const { atlas, bodyAlpha, face } = buildAtlas(imageData, labels, rest);

  const cell = Math.max(3, Math.ceil(Math.max(w, h) / 100));
  const cols = Math.ceil(w / cell), rows = Math.ceil(h / cell);

  // Celdas ocupadas por cada capa (más un margen de una celda para tapar costuras).
  const occ = Array.from({ length: PARTS }, () => new Uint8Array(cols * rows));
  for (let y = 0; y < h; y++) {
    for (let x = 0; x < w; x++) {
      const i = y * w + x;
      const c = ((y / cell) | 0) * cols + ((x / cell) | 0);
      if (labels[i] > PART.body) occ[labels[i]][c] = 1;
      if (bodyAlpha[i * 4 + 3] > 12) occ[PART.body][c] = 1;
    }
  }
  const cells = occ.map((o) => {
    const out = new Uint8Array(o.length);
    for (let j = 0; j < rows; j++) {
      for (let i = 0; i < cols; i++) {
        if (!o[j * cols + i]) continue;
        for (let dj = -1; dj <= 1; dj++) {
          for (let di = -1; di <= 1; di++) {
            const ii = i + di, jj = j + dj;
            if (ii >= 0 && jj >= 0 && ii < cols && jj < rows) out[jj * cols + ii] = 1;
          }
        }
      }
    }
    return out;
  });

  const pos = [], uv = [], idx = [], wts = [], indices = [];
  let bodyCount = 0;
  for (const part of DRAW_ORDER) {
    const bones = PART_BONES[part];
    const uOff = part === PART.body ? 0 : 0.5;
    const vmap = new Map();
    const vertex = (gi, gj) => {
      const key = gj * (cols + 1) + gi;
      if (vmap.has(key)) return vmap.get(key);
      const x = Math.min(gi * cell, w), y = Math.min(gj * cell, h);
      const id = pos.length / 2;
      pos.push(x, y);
      uv.push(uOff + x / w / 2, y / h);
      const ws = skinWeights(rest, scale, x, y, bones);
      for (let k = 0; k < 4; k++) {
        idx.push(ws[k]?.[0] ?? 0);
        wts.push(ws[k]?.[1] ?? 0);
      }
      vmap.set(key, id);
      return id;
    };
    const o = cells[part];
    for (let j = 0; j < rows; j++) {
      for (let i = 0; i < cols; i++) {
        if (!o[j * cols + i]) continue;
        const a = vertex(i, j), b = vertex(i + 1, j), c = vertex(i, j + 1), e = vertex(i + 1, j + 1);
        indices.push(a, b, c, b, e, c);
      }
    }
    if (part === PART.body) bodyCount = indices.length;
  }
  if (pos.length / 2 > 65535) throw new Error('La malla es demasiado grande.');
  return {
    atlas,
    face,
    mesh: {
      pos: new Float32Array(pos), uv: new Float32Array(uv),
      idx: new Float32Array(idx), wts: new Float32Array(wts),
      indices: new Uint16Array(indices),
      bodyCount,
    },
  };
}
