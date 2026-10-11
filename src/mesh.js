import { N, PARENT, LAYER, LAYERS, J, dist } from './skeleton.js';

// Distancia de un punto a un segmento.
function segDist(px, py, A, B) {
  const ux = B.x - A.x, uy = B.y - A.y;
  const l2 = ux * ux + uy * uy;
  let t = l2 > 0 ? ((px - A.x) * ux + (py - A.y) * uy) / l2 : 0;
  t = Math.max(0, Math.min(1, t));
  return Math.hypot(px - (A.x + t * ux), py - (A.y + t * uy));
}

// Cuadrilátero del torso (hombros-caderas) escalado respecto a su centro.
function torsoQuad(rest, shrink) {
  const q = [J.lsh, J.rsh, J.rhip, J.lhip].map((i) => rest[i]);
  const cx = q.reduce((s, p) => s + p.x, 0) / 4, cy = q.reduce((s, p) => s + p.y, 0) / 4;
  return q.map((p) => ({ x: cx + (p.x - cx) * shrink, y: cy + (p.y - cy) * shrink }));
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

const ARM_BONES = [J.lel, J.rel, J.lwr, J.rwr, J.lhand, J.rhand];

// Construye una malla en rejilla sobre la imagen del personaje, con pesos de
// "skinning" (hasta 4 huesos por vértice) según la distancia a cada hueso.
// Solo se conservan las celdas con píxeles visibles (alfa > 0).
export function buildMesh(imageData, rest) {
  const { width: w, height: h, data } = imageData;
  const cell = Math.max(3, Math.ceil(Math.max(w, h) / 110));
  const cols = Math.ceil(w / cell), rows = Math.ceil(h / cell);
  const vx = cols + 1, vy = rows + 1, nv = vx * vy;

  const pos = new Float32Array(nv * 2);
  const uv = new Float32Array(nv * 2);
  const idx = new Float32Array(nv * 4);
  const wts = new Float32Array(nv * 4);

  const scale = dist(rest[J.pelvis], rest[J.chest]) || h / 3;
  const d = new Float32Array(N);
  const torso = torsoQuad(rest, 1.12);
  const nearestBone = (x, y) => {
    for (let b = 1; b < N; b++) d[b] = segDist(x, y, rest[PARENT[b]], rest[b]);
    // Dentro del torso, los brazos influyen menos: evita que la camiseta se estire con ellos.
    if (insideConvex(torso, x, y)) for (const b of ARM_BONES) d[b] = d[b] * 3 + 0.2 * scale;
    let best = 1;
    for (let b = 2; b < N; b++) if (d[b] < d[best]) best = b;
    return best;
  };

  for (let j = 0; j < vy; j++) {
    for (let i = 0; i < vx; i++) {
      const v = j * vx + i;
      const x = Math.min(i * cell, w), y = Math.min(j * cell, h);
      pos[v * 2] = x; pos[v * 2 + 1] = y;
      uv[v * 2] = x / w; uv[v * 2 + 1] = y / h;
      nearestBone(x, y);
      // Peso inverso a la distancia con caída pronunciada; nos quedamos con los 4 mayores.
      const cand = [];
      for (let b = 1; b < N; b++) {
        const r = d[b] / scale;
        cand.push([b, 1 / Math.pow(r * r + 0.003, 2)]);
      }
      cand.sort((a, b) => b[1] - a[1]);
      let sum = 0;
      for (let k = 0; k < 4; k++) sum += cand[k][1];
      for (let k = 0; k < 4; k++) {
        idx[v * 4 + k] = cand[k][0];
        wts[v * 4 + k] = cand[k][1] / sum;
      }
    }
  }

  const alphaAt = (x, y) => {
    const xi = Math.min(w - 1, Math.max(0, Math.round(x)));
    const yi = Math.min(h - 1, Math.max(0, Math.round(y)));
    return data[(yi * w + xi) * 4 + 3];
  };

  // Triángulos agrupados por capa para controlar qué parte queda delante.
  const buckets = Array.from({ length: LAYERS }, () => []);
  for (let j = 0; j < rows; j++) {
    for (let i = 0; i < cols; i++) {
      const x0 = i * cell, y0 = j * cell;
      let visible = false;
      for (let sy = 0; sy <= 2 && !visible; sy++) {
        for (let sx = 0; sx <= 2 && !visible; sx++) {
          if (alphaAt(x0 + (sx * cell) / 2, y0 + (sy * cell) / 2) > 12) visible = true;
        }
      }
      if (!visible) continue;
      const layer = LAYER[nearestBone(x0 + cell / 2, y0 + cell / 2)];
      const a = j * vx + i, b = a + 1, c = a + vx, e = c + 1;
      buckets[layer].push(a, b, c, b, e, c);
    }
  }
  const indices = new Uint16Array(buckets.flat());
  return { pos, uv, idx, wts, indices, width: w, height: h };
}
