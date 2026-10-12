import { FaceLandmarker } from '@mediapipe/tasks-vision';

// Cara del personaje como malla 2D sobre los 478 puntos de MediaPipe FaceLandmarker, y su
// animación con los gestos de la cara del video: parpadeo, mirada, cejas, boca y sonrisa.
// Solo matemáticas (sin DOM ni WebGL). Los giros de cabeza que no son de plano (izquierda,
// derecha, arriba, abajo) quedan en las diferencias y se ven como paralaje 2.5D.

const LM = 478;
const TESS = FaceLandmarker.FACE_LANDMARKS_TESSELATION;

// Contorno de la cara (bucle cerrado; 10 = frente, 152 = barbilla).
const OVAL = [
  10, 338, 297, 332, 284, 251, 389, 356, 454, 323, 361, 288, 397, 365, 379, 378, 400, 377,
  152, 148, 176, 149, 150, 136, 172, 58, 132, 93, 234, 127, 162, 21, 54, 103, 67, 109,
];

// Párpados de esquina a esquina y centro del iris. Los pares de párpado son up[k] / lo[k], k = 1..7.
const EYES = [
  { up: [33, 246, 161, 160, 159, 158, 157, 173, 133], lo: [33, 7, 163, 144, 145, 153, 154, 155, 133], iris: 468, blink: 'eyeBlinkRight' },
  { up: [263, 466, 388, 387, 386, 385, 384, 398, 362], lo: [263, 249, 390, 373, 374, 380, 381, 382, 362], iris: 473, blink: 'eyeBlinkLeft' },
];

// Labios interiores de comisura a comisura; los pares son LIP_UP[k] / LIP_LO[k], k = 1..9.
const LIP_LO = [78, 95, 88, 178, 87, 14, 317, 402, 318, 324, 308];
const LIP_UP = [78, 191, 80, 81, 82, 13, 312, 311, 310, 415, 308];
const INNER_LIP = [...LIP_LO, ...LIP_UP.slice(1, -1).reverse()];
const OUTER_LO = [146, 91, 181, 84, 17, 314, 405, 321, 375];
const OUTER_UP = [185, 40, 39, 37, 0, 267, 269, 270, 409];

// Puntos estables (casi no cambian con los gestos) para separar la pose de la expresión.
const ANCHORS = [33, 133, 362, 263, 168, 6, 197, 195, 10, 109, 338, 234, 454, 127, 356];
const NOSE = 1;

const RING = OVAL.length;
const MAX_DELTA = 0.35; // desplazamiento máximo, relativo al tamaño de la cara
const RING_FOLLOW = 0.35;
const UNFOLD_ITERS = 8;
const RIM_DAMP = 0.6; // fracción del movimiento lateral que se quita en el contorno
const JAW_CHIN = 0.6; // la barbilla baja ~0.6 veces lo que se separan los labios

const clamp = (v, a, b) => (v < a ? a : v > b ? b : v);
const smooth = (a, b, x) => {
  const t = clamp((x - a) / (b - a), 0, 1);
  return t * t * (3 - 2 * t);
};
const dist = (p, i, j) => Math.hypot(p[j * 2] - p[i * 2], p[j * 2 + 1] - p[i * 2 + 1]);

// Copia los landmarks ({x, y} o [x, y]) a un array plano. Sin iris (468 puntos) usa el centro del ojo.
function readPoints(lm, out) {
  const m = Math.min(lm.length, LM);
  for (let i = 0; i < m; i++) {
    const q = lm[i];
    const x = q.x ?? q[0], y = q.y ?? q[1];
    if (!Number.isFinite(x) || !Number.isFinite(y)) return false;
    out[i * 2] = x;
    out[i * 2 + 1] = y;
  }
  if (m < LM) {
    for (const E of EYES) {
      let sx = 0, sy = 0;
      for (let k = 0; k < 9; k++) { sx += out[E.up[k] * 2]; sy += out[E.up[k] * 2 + 1]; }
      for (let k = 1; k < 8; k++) { sx += out[E.lo[k] * 2]; sy += out[E.lo[k] * 2 + 1]; }
      for (let i = E.iris; i < E.iris + 5; i++) { out[i * 2] = sx / 16; out[i * 2 + 1] = sy / 16; }
    }
  }
  return true;
}

// Eje "abajo" de la cara (frente 10 -> barbilla 152), unitario.
function faceDown(p, out) {
  const x = p[304] - p[20], y = p[305] - p[21];
  const l = Math.hypot(x, y) || 1;
  out[0] = x / l;
  out[1] = y / l;
  return out;
}

// Signo de la orientación de la cara (cambia si la imagen está reflejada).
function orientation(p) {
  const ux = p[526] - p[66], uy = p[527] - p[67], vx = p[304] - p[66], vy = p[305] - p[67];
  return ux * vy - uy * vx >= 0 ? 1 : -1;
}

// Semejanza (rotación + escala uniforme + traslación) por mínimos cuadrados que lleva los
// puntos `idx` de A sobre los de B. Con `flip` incluye un reflejo. out = [a, b, tx, ty]:
//   sin reflejo: x' = a·x − b·y + tx, y' = b·x + a·y + ty
//   con reflejo: x' = a·x + b·y + tx, y' = b·x − a·y + ty
function fitSimilarity(A, B, idx, flip, out) {
  let ax = 0, ay = 0, bx = 0, by = 0;
  for (const i of idx) { ax += A[i * 2]; ay += A[i * 2 + 1]; bx += B[i * 2]; by += B[i * 2 + 1]; }
  const k = idx.length;
  ax /= k; ay /= k; bx /= k; by /= k;
  let den = 0, c1 = 0, c2 = 0;
  for (const i of idx) {
    const px = A[i * 2] - ax, py = A[i * 2 + 1] - ay, qx = B[i * 2] - bx, qy = B[i * 2 + 1] - by;
    den += px * px + py * py;
    if (flip) { c1 += px * qx - py * qy; c2 += py * qx + px * qy; } else { c1 += px * qx + py * qy; c2 += px * qy - py * qx; }
  }
  const a = den > 1e-9 ? c1 / den : 1, b = den > 1e-9 ? c2 / den : 0;
  out[0] = a;
  out[1] = b;
  out[2] = flip ? bx - (a * ax + b * ay) : bx - (a * ax - b * ay);
  out[3] = flip ? by - (b * ax - a * ay) : by - (b * ax + a * ay);
  return out;
}

// Sistema local de un ojo: origen en la esquina up[0], eje u hacia la otra esquina y
// normal n hacia abajo de la cara. F = [ox, oy, ux, uy, nx, ny, ancho].
function eyeFrame(p, E, down, F) {
  const ox = p[E.up[0] * 2], oy = p[E.up[0] * 2 + 1];
  let ux = p[E.up[8] * 2] - ox, uy = p[E.up[8] * 2 + 1] - oy;
  const W = Math.hypot(ux, uy);
  if (W > 1e-9) { ux /= W; uy /= W; } else { ux = 1; uy = 0; }
  let nx = -uy, ny = ux;
  if (nx * down[0] + ny * down[1] < 0) { nx = -nx; ny = -ny; }
  F[0] = ox; F[1] = oy; F[2] = ux; F[3] = uy; F[4] = nx; F[5] = ny; F[6] = W;
  return W > 1e-9;
}

// Altura (en px, sobre la normal del ojo) del párpado `chain` en la posición s (0..1 entre esquinas).
function lidAt(p, chain, F, s) {
  const x = s * F[6];
  let pu = 0, pn = 0, best = 0, bd = Infinity;
  for (let k = 0; k < chain.length; k++) {
    const dx = p[chain[k] * 2] - F[0], dy = p[chain[k] * 2 + 1] - F[1];
    const u = dx * F[2] + dy * F[3], n = dx * F[4] + dy * F[5];
    if (k > 0 && (x - pu) * (x - u) <= 0 && u !== pu) return pn + ((n - pn) * (x - pu)) / (u - pu);
    const d = Math.abs(u - x);
    if (d < bd) { bd = d; best = n; }
    pu = u; pn = n;
  }
  return best;
}

// Interior de cada ojo: una línea media de esquina a esquina que pasa por el iris (borde,
// centro, borde) y dos franjas entre ella y cada párpado. Al mirar a un lado la línea media se
// desplaza entera, así el iris se mueve sin estirarse. Devuelve [borde, centro, borde] (en el
// sentido up[0] -> up[8]) y recoloca en reposo los puntos que no queden dentro del ojo.
function eyeMid(R, E, down, F) {
  const c = E.iris;
  let a = c + 1, b = c + 3;
  if (!eyeFrame(R, E, down, F)) return [a, c, b];
  const S = (i) => ((R[i * 2] - F[0]) * F[2] + (R[i * 2 + 1] - F[1]) * F[3]) / F[6];
  if (S(a) > S(b)) [a, b] = [b, a];
  const place = (i, s) => {
    const nu = lidAt(R, E.up, F, s), nl = lidAt(R, E.lo, F, s);
    const n = (R[i * 2] - F[0]) * F[4] + (R[i * 2 + 1] - F[1]) * F[5];
    const m = nl > nu ? clamp(n, nu + 0.1 * (nl - nu), nl - 0.1 * (nl - nu)) : (nu + nl) / 2;
    R[i * 2] = F[0] + F[2] * s * F[6] + F[4] * m;
    R[i * 2 + 1] = F[1] + F[3] * s * F[6] + F[5] * m;
  };
  const sc = clamp(S(c), 0.2, 0.8);
  place(c, sc);
  place(a, clamp(S(a), 0.04, sc - 0.04));
  place(b, clamp(S(b), sc + 0.04, 0.96));
  return [a, c, b];
}

// Triangula la franja entre dos cadenas con los mismos extremos, avanzando según s.
function zipper(A, sA, B, sB, idx) {
  let i = 0, j = 0;
  while (i < A.length - 1 || j < B.length - 1) {
    let t;
    if (j === B.length - 1 || (i < A.length - 1 && sA[i + 1] <= sB[j + 1])) t = [A[i], A[++i], B[j]];
    else t = [A[i], B[j], B[++j]];
    if (t[0] !== t[1] && t[1] !== t[2] && t[0] !== t[2]) idx.push(...t);
  }
}

// Punto en polígono (índices de vértices sobre el array plano p).
function inside(p, poly, x, y) {
  let inn = false;
  for (let k = 0, j = poly.length - 1; k < poly.length; j = k++) {
    const xi = p[poly[k] * 2], yi = p[poly[k] * 2 + 1], xj = p[poly[j] * 2], yj = p[poly[j] * 2 + 1];
    if (yi > y !== yj > y && x < ((xj - xi) * (y - yi)) / (yj - yi) + xi) inn = !inn;
  }
  return inn;
}

// Cómo se mueve cada punto cuando hay que abrir o cerrar la boca. El labio superior no se mueve;
// el inferior sigue la corrección del par de labios que tiene encima (las comisuras quedan
// fijas, así los labios no se cruzan) y, hacia la barbilla, el movimiento pasa a ser el de
// toda la mandíbula (corrección central).
function jawRig(R) {
  const seg = new Int8Array(468).fill(-1), t = new Float32Array(468), wy = new Float32Array(468), wx = new Float32Array(468);
  const d = faceDown(R, [0, 0]);
  const ax = -d[1], ay = d[0];
  const mx = (R[26] + R[28]) / 2, my = (R[27] + R[29]) / 2;
  const across = (i) => (R[i * 2] - mx) * ax + (R[i * 2 + 1] - my) * ay;
  const along = (i) => (R[i * 2] - mx) * d[0] + (R[i * 2 + 1] - my) * d[1];
  const knots = LIP_LO.map(across), heights = LIP_LO.map(along);
  const hw = dist(R, 61, 291) / 2 || 1;
  const L = along(152) - along(14) || 1;
  const upperPoly = [61, ...OUTER_UP, 291, ...LIP_UP.slice(1, -1).reverse()];
  const upper = new Set([...OUTER_UP, ...LIP_UP.slice(1, -1)]), lowerLip = new Set(LIP_LO);
  for (let i = 0; i < 468; i++) {
    // Con la boca cerrada el labio inferior toca el superior: nunca se excluye por estar "dentro".
    if (upper.has(i) || (!lowerLip.has(i) && inside(R, upperPoly, R[i * 2], R[i * 2 + 1]))) continue;
    const x = across(i);
    let k = -1, f = 0;
    for (let j = 0; j < 10; j++) {
      const a = knots[j], b = knots[j + 1];
      if ((x - a) * (x - b) <= 0 && a !== b) { k = j; f = (x - a) / (b - a); break; }
    }
    if (k < 0) {
      const first = Math.abs(x - knots[0]) < Math.abs(x - knots[10]);
      k = first ? 0 : 9;
      f = first ? 0 : 1;
    }
    // Lo que queda por encima del labio inferior (nariz, mejillas) no se mueve.
    const yr = (along(i) - (heights[k] + (heights[k + 1] - heights[k]) * f)) / L;
    if (yr < -0.05) continue;
    seg[i] = k;
    t[i] = f;
    wy[i] = smooth(0.3, 1.0, yr);
    wx[i] = 1 - smooth(1.0, 2.2, Math.abs(x) / hw);
  }
  return { seg, t, wy, wx };
}

// Cercanía de cada punto al contorno de la cara (0 = centro, 1 = contorno), para amortiguar
// el desplazamiento lateral del borde en los giros de cabeza.
function rimWeights(R, cx, cy) {
  const w = new Float32Array(468);
  for (let i = 0; i < 468; i++) {
    const px = R[i * 2] - cx, py = R[i * 2 + 1] - cy, l = Math.hypot(px, py);
    if (l < 1e-9) continue;
    // Distancia del centro al contorno en la dirección del punto (rayo contra cada lado).
    let reach = Infinity;
    for (let k = 0; k < RING; k++) {
      const a = OVAL[k] * 2, b = OVAL[(k + 1) % RING] * 2;
      const ax = R[a] - cx, ay = R[a + 1] - cy, ex = R[b] - R[a], ey = R[b + 1] - R[a + 1];
      const den = px * ey - py * ex;
      if (Math.abs(den) < 1e-12) continue;
      const t = (ax * ey - ay * ex) / den, u = (ax * py - ay * px) / den;
      if (t > 0 && u >= 0 && u <= 1) reach = Math.min(reach, t);
    }
    w[i] = Number.isFinite(reach) ? smooth(0.6, 1.0, 1 / reach) : 1;
  }
  return w;
}

// Construye la malla de la cara del personaje. lm: 478 puntos en píxeles de su imagen.
// Vértices: 0..477 = landmarks, luego dos anillos alrededor del contorno (pelo y orejas).
export function buildFaceRig(lm, imgW, imgH) {
  const n = LM + RING * 2;
  const rest = new Float32Array(n * 2);
  if (!lm || lm.length < 468 || !readPoints(lm, rest)) throw new Error('Puntos de la cara no válidos.');
  const down = faceDown(rest, [0, 0]);
  const faceSize = dist(rest, 33, 263) || 1;
  const eyeAngle = Math.atan2(rest[527] - rest[67], rest[526] - rest[66]);

  // Pares de labios o párpados cruzados en la foto (ruido de la detección): se juntan.
  for (let k = 1; k < 10; k++) uncross(rest, LIP_UP[k], LIP_LO[k], down[0], down[1]);
  for (const E of EYES) for (let k = 1; k < 8; k++) uncross(rest, E.up[k], E.lo[k], down[0], down[1]);
  const F = new Float64Array(7);
  const mids = EYES.map((E) => eyeMid(rest, E, down, F));

  // Anillos para pelo y orejas: el contorno escalado desde su centro. Por encima de los ojos
  // crece más (pelo, orejas) y hacia la barbilla menos, para no arrastrar cuello ni hombros.
  let cx = 0, cy = 0;
  for (const i of OVAL) { cx += rest[i * 2]; cy += rest[i * 2 + 1]; }
  cx /= RING; cy /= RING;
  const yEye = ((rest[66] + rest[526]) / 2) * down[0] + ((rest[67] + rest[527]) / 2) * down[1];
  const yMouth = ((rest[26] + rest[28]) / 2) * down[0] + ((rest[27] + rest[29]) / 2) * down[1];
  for (let k = 0; k < RING; k++) {
    const o = OVAL[k];
    const dx = rest[o * 2] - cx, dy = rest[o * 2 + 1] - cy;
    const t = smooth(yEye, yEye + 0.8 * (yMouth - yEye), rest[o * 2] * down[0] + rest[o * 2 + 1] * down[1]);
    // Límite radial para no salir de la imagen (no se pliega: misma dirección desde el centro).
    let lim = Infinity;
    if (dx > 1e-9) lim = Math.min(lim, (imgW - cx) / dx); else if (dx < -1e-9) lim = Math.min(lim, -cx / dx);
    if (dy > 1e-9) lim = Math.min(lim, (imgH - cy) / dy); else if (dy < -1e-9) lim = Math.min(lim, -cy / dy);
    const f1 = Math.max(1, Math.min(1.3 + (1.08 - 1.3) * t, lim));
    const f2 = Math.max(f1, Math.min(1.75 + (1.18 - 1.75) * t, lim));
    rest[(LM + k) * 2] = cx + dx * f1;
    rest[(LM + k) * 2 + 1] = cy + dy * f1;
    rest[(LM + RING + k) * 2] = cx + dx * f2;
    rest[(LM + RING + k) * 2 + 1] = cy + dy * f2;
  }

  const uv = new Float32Array(n * 2);
  for (let i = 0; i < n; i++) {
    uv[i * 2] = rest[i * 2] / imgW;
    uv[i * 2 + 1] = rest[i * 2 + 1] / imgH;
  }

  // Triángulos: teselado de MediaPipe (con huecos en ojos y boca), interior de los ojos y
  // franjas de los anillos. La boca queda como hueco.
  const idx = [];
  for (let k = 0; k + 2 < TESS.length; k += 3) idx.push(TESS[k].start, TESS[k + 1].start, TESS[k + 2].start);
  EYES.forEach((E, e) => {
    eyeFrame(rest, E, down, F);
    const S = (i) => ((rest[i * 2] - F[0]) * F[2] + (rest[i * 2 + 1] - F[1]) * F[3]) / (F[6] || 1);
    const mid = [E.up[0], ...mids[e], E.up[8]];
    const sMid = [0, S(mids[e][0]), S(mids[e][1]), S(mids[e][2]), 1];
    zipper(E.up, E.up.map(S), mid, sMid, idx);
    zipper(E.lo, E.lo.map(S), mid, sMid, idx);
  });
  const strip = (inner, outer) => {
    for (let k = 0; k < RING; k++) {
      const k1 = (k + 1) % RING;
      const a = inner(k), b = inner(k1), c = outer(k), d = outer(k1);
      idx.push(a, b, d, a, d, c);
    }
  };
  strip((k) => OVAL[k], (k) => LM + k);
  strip((k) => LM + k, (k) => LM + RING + k);

  return {
    n,
    rest,
    uv,
    indices: new Uint16Array(idx),
    innerLip: INNER_LIP.slice(),
    faceSize,
    eyeAngle,
    oval: OVAL.slice(),
    ring1: OVAL.map((_, k) => LM + k),
    ring2: OVAL.map((_, k) => LM + RING + k),
    jaw: jawRig(rest),
    rim: rimWeights(rest, cx, cy),
    eyeMid: mids,
  };
}

// Lee un blendshape de {nombre: valor}, de la lista de categorías de MediaPipe o de {categories}.
function bsGet(bs, name) {
  if (!bs) return undefined;
  const list = Array.isArray(bs) ? bs : bs.categories;
  if (list) {
    for (const c of list) if (c.categoryName === name) return c.score;
    return undefined;
  }
  return bs[name];
}

// Cuánto se aleja un fotograma de una cara neutra mirando de frente (más bajo = más neutro).
function neutralScore(p, bs) {
  const e = dist(p, 33, 263) || 1;
  const ux = (p[526] - p[66]) / e, uy = (p[527] - p[67]) / e;
  let dx = -uy, dy = ux;
  if (dx * (p[304] - p[20]) + dy * (p[305] - p[21]) < 0) { dx = -dx; dy = -dy; }
  const mx = (p[66] + p[526]) / 2, my = (p[67] + p[527]) / 2;
  const nx = p[NOSE * 2] - mx, ny = p[NOSE * 2 + 1] - my;
  // Giro de cabeza: la punta de la nariz se separa del centro de los ojos.
  const turn = Math.abs((nx * ux + ny * uy) / e) + 0.6 * Math.abs((nx * dx + ny * dy) / e - 0.5);
  const jaw = bsGet(bs, 'jawOpen');
  if (jaw !== undefined) {
    return jaw + 0.5 * ((bsGet(bs, 'eyeBlinkLeft') ?? 0) + (bsGet(bs, 'eyeBlinkRight') ?? 0))
      + 0.5 * ((bsGet(bs, 'mouthSmileLeft') ?? 0) + (bsGet(bs, 'mouthSmileRight') ?? 0))
      + 0.3 * (bsGet(bs, 'browInnerUp') ?? 0) + turn
      // Labios separados aunque jawOpen sea bajo: tampoco es una cara neutra.
      + clamp((2 * gapAlong(p, 13, 14, dx, dy)) / e, 0, 1);
  }
  // Sin blendshapes: apertura de labios, párpados y comisuras elevadas medidas en la malla.
  const mouth = clamp((2 * gapAlong(p, 13, 14, dx, dy)) / e, 0, 1);
  const blinkB = clamp((0.28 - gapAlong(p, 159, 145, dx, dy) / (dist(p, 33, 133) || 1)) / 0.2, 0, 1);
  const blinkA = clamp((0.28 - gapAlong(p, 386, 374, dx, dy) / (dist(p, 263, 362) || 1)) / 0.2, 0, 1);
  const lift = (((p[26] + p[28] - p[122] - p[582]) / 2) * dx + ((p[27] + p[29] - p[123] - p[583]) / 2) * dy) / e;
  const smile = clamp((lift - 0.03) / 0.06, 0, 1);
  return mouth + 0.5 * (blinkA + blinkB) + smile + turn;
}

// Anima la cara del personaje con la cara del video. Cada fotograma se compara con un
// fotograma de referencia (el más neutro de la toma actual) tras quitar la pose de la cabeza;
// esas diferencias se trasladan al personaje a su escala.
export class FaceDriver {
  constructor(rig) {
    this.rig = rig;
    this.cur = new Float32Array(LM * 2); // fotograma actual (px del video)
    this.ref = new Float32Array(LM * 2); // referencia neutra de la toma
    this.al = new Float32Array(LM * 2); // actual alineado con la referencia
    this.lip = new Float32Array(INNER_LIP.length * 2);
    this.sim = new Float64Array(4);
    this.M = new Float64Array(4); // parte lineal referencia -> personaje
    this.F = new Float64Array(7);
    this.dRef = [0, 1];
    this.dCur = [0, 1];
    this.dChar = faceDown(rig.rest, [0, 0]);
    this.charOrient = orientation(rig.rest);
    this.refGap = new Float64Array(2); // apertura total de cada ojo en la referencia
    this.refBlink = new Float64Array(2);
    this.curBlink = new Float64Array(2);
    this.cLip = new Float64Array(11); // corrección de cada par de labios (0 en las comisuras)
    // Apertura de cada par de párpados del personaje en reposo.
    this.lidRest = EYES.map((E) => {
      const g = new Float64Array(8);
      for (let k = 1; k < 8; k++) {
        const u = E.up[k], l = E.lo[k];
        const v = (rig.rest[l * 2] - rig.rest[u * 2]) * this.dChar[0] + (rig.rest[l * 2 + 1] - rig.rest[u * 2 + 1]) * this.dChar[1];
        g[k] = Math.max(0, v);
      }
      return g;
    });
    // Orientación en reposo de los triángulos del teselado (0 = degenerado, no se revisa) y
    // puntos que el suavizado de pliegues no mueve (ojos, iris y labios interiores).
    const T = 852;
    this.triSign = new Int8Array(T);
    for (let t = 0; t < T; t++) {
      const [a, b, c] = [rig.indices[t * 3] * 2, rig.indices[t * 3 + 1] * 2, rig.indices[t * 3 + 2] * 2];
      const cr = (rig.rest[b] - rig.rest[a]) * (rig.rest[c + 1] - rig.rest[a + 1]) - (rig.rest[c] - rig.rest[a]) * (rig.rest[b + 1] - rig.rest[a + 1]);
      this.triSign[t] = Math.abs(cr) > 1e-3 * rig.faceSize ** 2 ? Math.sign(cr) : 0;
    }
    this.pinned = new Uint8Array(rig.n);
    for (const E of EYES) for (const i of [...E.up, ...E.lo]) this.pinned[i] = 1;
    for (let i = 468; i < LM; i++) this.pinned[i] = 1;
    for (const i of INNER_LIP) this.pinned[i] = 1;
    // Dirección hacia fuera de cada punto del contorno y separación de los anillos en reposo.
    this.ringDir = new Float32Array(RING * 2);
    this.ringGap = new Float32Array(RING * 2);
    let cx = 0, cy = 0;
    for (const i of OVAL) { cx += rig.rest[i * 2]; cy += rig.rest[i * 2 + 1]; }
    cx /= RING; cy /= RING;
    for (let k = 0; k < RING; k++) {
      const o = OVAL[k] * 2, r1 = (LM + k) * 2, r2 = (LM + RING + k) * 2;
      const dx = rig.rest[o] - cx, dy = rig.rest[o + 1] - cy, l = Math.hypot(dx, dy) || 1;
      this.ringDir[k * 2] = dx / l;
      this.ringDir[k * 2 + 1] = dy / l;
      this.ringGap[k * 2] = Math.hypot(rig.rest[r1] - rig.rest[o], rig.rest[r1 + 1] - rig.rest[o + 1]);
      this.ringGap[k * 2 + 1] = Math.hypot(rig.rest[r2] - rig.rest[r1], rig.rest[r2 + 1] - rig.rest[r1 + 1]);
    }
    // Línea media de cada ojo en reposo (s a lo largo del ojo, n hacia abajo) y ancho del ojo.
    this.eyeRest = EYES.map((E, e) => {
      const L = new Float64Array(7), F = this.F;
      if (!eyeFrame(rig.rest, E, this.dChar, F)) return L;
      rig.eyeMid[e].forEach((i, k) => {
        const dx = rig.rest[i * 2] - F[0], dy = rig.rest[i * 2 + 1] - F[1];
        L[k * 2] = (dx * F[2] + dy * F[3]) / F[6];
        L[k * 2 + 1] = dx * F[4] + dy * F[5];
      });
      L[6] = F[6];
      return L;
    });
    this.reset();
  }

  get ready() {
    return this.hasRef && this.hasCur;
  }

  // Olvida la referencia (cambio de plano o de video).
  reset() {
    this.hasRef = false;
    this.hasCur = false;
    this.refScore = Infinity;
    this.mirrored = false;
  }

  // lm: 478 puntos en px del video; blendshapes: {nombre: valor} o null.
  // Devuelve true si este fotograma pasa a ser la nueva referencia.
  update(lm, blendshapes) {
    if (!lm || lm.length < 468 || !readPoints(lm, this.cur)) return false;
    this.hasCur = true;
    this.mirrored = orientation(this.cur) !== this.charOrient;
    for (let e = 0; e < 2; e++) this.curBlink[e] = bsGet(blendshapes, EYES[e].blink) ?? -1;
    const score = neutralScore(this.cur, blendshapes);
    if (this.hasRef && !(score < this.refScore - 0.03)) return false;
    this.setReference(score);
    return true;
  }

  setReference(score) {
    const { cur, ref, rig } = this;
    ref.set(cur);
    this.hasRef = true;
    this.refScore = score;
    this.refBlink.set(this.curBlink);
    faceDown(ref, this.dRef);
    // Referencia -> personaje (con reflejo si el video está en espejo respecto al personaje).
    const flip = orientation(ref) !== this.charOrient;
    const s = fitSimilarity(ref, rig.rest, ANCHORS, flip, this.sim);
    this.M[0] = s[0];
    this.M[1] = flip ? s[1] : -s[1];
    this.M[2] = s[1];
    this.M[3] = flip ? -s[0] : s[0];
    for (let e = 0; e < 2; e++) this.refGap[e] = this.lidSum(ref, EYES[e]);
  }

  // Suma de las aperturas de los pares de párpados medidas sobre el eje abajo de la referencia.
  lidSum(p, E) {
    let s = 0;
    for (let k = 1; k < 8; k++) {
      const u = E.up[k], l = E.lo[k];
      s += (p[l * 2] - p[u * 2]) * this.dRef[0] + (p[l * 2 + 1] - p[u * 2 + 1]) * this.dRef[1];
    }
    return s;
  }

  // Posiciones objetivo de los vértices en el espacio de reposo del personaje (sin el
  // movimiento rígido de la cabeza, que aplica el hueso de la cabeza).
  computeTargets(out = new Float32Array(this.rig.n * 2)) {
    const { rig, cur, ref, al, M } = this;
    const R = rig.rest;
    if (!this.ready) {
      out.set(R);
      return out;
    }
    const F = rig.faceSize;
    const dcx = this.dChar[0], dcy = this.dChar[1];

    // 1) Quitar la pose: semejanza del fotograma actual a la referencia y diferencias.
    const S = fitSimilarity(cur, ref, ANCHORS, false, this.sim);
    const a = S[0], b = S[1], tx = S[2], ty = S[3];
    //    Cerca del contorno se amortigua la parte lateral: al girar la cabeza, los rasgos se
    //    desplazan dentro de la cara (paralaje) sin arrastrar el borde ni el pelo.
    const lim = MAX_DELTA * F, rim = rig.rim, hx = -dcy, hy = dcx;
    for (let i = 0; i < LM; i++) {
      const x = cur[i * 2], y = cur[i * 2 + 1];
      const ax = a * x - b * y + tx, ay = b * x + a * y + ty;
      al[i * 2] = ax;
      al[i * 2 + 1] = ay;
      const dx = ax - ref[i * 2], dy = ay - ref[i * 2 + 1];
      let mx = M[0] * dx + M[1] * dy, my = M[2] * dx + M[3] * dy;
      if (i < 468 && rim[i] > 0) {
        const h = (mx * hx + my * hy) * RIM_DAMP * rim[i];
        mx -= hx * h;
        my -= hy * h;
      }
      const l = Math.hypot(mx, my);
      if (l > lim) { mx *= lim / l; my *= lim / l; }
      out[i * 2] = R[i * 2] + mx;
      out[i * 2 + 1] = R[i * 2 + 1] + my;
    }

    // 2) Boca: la separación de los labios interiores copia la del video (a escala), aunque la
    //    referencia o el personaje tengan la boca abierta. La mandíbula acompaña.
    const c = this.cLip;
    let any = false;
    for (let k = 1; k < 10; k++) {
      const u = LIP_UP[k], l = LIP_LO[k];
      c[k] = clamp(mappedGap(al, M, u, l, dcx, dcy) - gapAlong(out, u, l, dcx, dcy), -0.4 * F, 0.4 * F);
      any ||= Math.abs(c[k]) > 1e-6;
    }
    if (any) {
      const { seg, t, wy, wx } = rig.jaw;
      const mid = (c[4] + c[5] + c[6]) / 3; // pares centrales: 82/87, 13/14, 312/317
      for (let i = 0; i < 468; i++) {
        const k = seg[i];
        if (k < 0) continue;
        const m = (c[k] + (c[k + 1] - c[k]) * t[i]) * (1 - wy[i]) + JAW_CHIN * mid * wx[i] * wy[i];
        out[i * 2] += dcx * m;
        out[i * 2 + 1] += dcy * m;
      }
    }

    // 3) Párpados: la apertura de cada ojo es proporcional a la del video respecto a la
    //    referencia, así un parpadeo cierra el ojo aunque sea más grande que el del video.
    for (let e = 0; e < 2; e++) {
      const E = EYES[e];
      let f = 1;
      if (this.refGap[e] > 0.07 * dist(ref, 33, 263)) {
        // Fiel hasta medio cerrar; por debajo cierra antes (MediaPipe rara vez junta los párpados).
        const r = this.lidSum(al, E) / this.refGap[e];
        f = r >= 0.5 ? Math.min(r, 1.4) : Math.max(0, (r - 0.2) / 0.6);
      }
      const bl = this.curBlink[e];
      if (bl >= 0) {
        const base = Math.max(this.refBlink[e], 0.15);
        f = Math.min(f, 1 - clamp((bl - base - 0.2) / 0.2, 0, 1));
      }
      const rest = this.lidRest[e];
      for (let k = 1; k < 8; k++) {
        const u = E.up[k] * 2, l = E.lo[k] * 2;
        let vx = out[l] - out[u], vy = out[l + 1] - out[u + 1];
        const g = vx * dcx + vy * dcy, want = rest[k] * f;
        if (want <= g && g > 1e-6) {
          vx *= want / g; vy *= want / g;
        } else {
          vx += dcx * (want - g); vy += dcy * (want - g);
        }
        // El párpado superior hace la mayor parte del recorrido.
        const px = out[u] + 0.7 * (out[l] - out[u]), py = out[u + 1] + 0.7 * (out[l + 1] - out[u + 1]);
        out[u] = px - 0.7 * vx; out[u + 1] = py - 0.7 * vy;
        out[l] = px + 0.3 * vx; out[l + 1] = py + 0.3 * vy;
      }
      // Ojo casi cerrado: los párpados se aplanan sobre la línea entre las esquinas, así
      // los triángulos del ojo (y el iris, que va entre ellos) no dejan ninguna rendija.
      const w = 1 - smooth(0, 0.25, f);
      if (w > 0 && eyeFrame(out, E, this.dChar, this.F)) {
        for (let k = 1; k < 8; k++) {
          flatten(out, E.up[k], this.F, w);
          flatten(out, E.lo[k], this.F, w);
        }
      }
    }

    // 4) Ni el labio inferior por encima del superior ni el párpado superior por debajo del inferior.
    for (let k = 1; k < 10; k++) uncross(out, LIP_UP[k], LIP_LO[k], dcx, dcy);
    for (const E of EYES) for (let k = 1; k < 8; k++) uncross(out, E.up[k], E.lo[k], dcx, dcy);

    // 5) Iris: la mirada del video, colocada dentro del ojo del personaje.
    for (let e = 0; e < 2; e++) this.placeIris(out, e);

    // 6) Giros de cabeza fuertes pliegan triángulos de la mejilla lejana (como en la proyección
    //    del video); se suavizan acercando sus vértices al desplazamiento medio del triángulo.
    this.unfold(out);

    // 7) Anillos: el interior sigue en parte al contorno y el exterior queda fijo, salvo que el
    //    contorno se les eche encima (mandíbula muy abierta): entonces se apartan hacia fuera.
    const D = this.ringDir, G = this.ringGap;
    for (let k = 0; k < RING; k++) {
      const o = OVAL[k] * 2, r1 = (LM + k) * 2, r2 = (LM + RING + k) * 2;
      const dx = out[o] - R[o], dy = out[o + 1] - R[o + 1], rx = D[k * 2], ry = D[k * 2 + 1];
      const radial = dx * rx + dy * ry;
      const push1 = Math.max(0, (1 - RING_FOLLOW) * radial - 0.7 * G[k * 2]);
      const push2 = Math.max(0, RING_FOLLOW * radial + push1 - 0.7 * G[k * 2 + 1]);
      out[r1] = R[r1] + RING_FOLLOW * dx + rx * push1;
      out[r1 + 1] = R[r1 + 1] + RING_FOLLOW * dy + ry * push1;
      out[r2] = R[r2] + rx * push2;
      out[r2 + 1] = R[r2 + 1] + ry * push2;
    }
    return out;
  }

  unfold(out) {
    const R = this.rig.rest, ix = this.rig.indices, sign = this.triSign, pin = this.pinned;
    const eps = -1e-4 * this.rig.faceSize ** 2;
    for (let it = 0; it < UNFOLD_ITERS; it++) {
      let folded = false;
      for (let t = 0, k = 0; k < sign.length; t += 3, k++) {
        if (!sign[k]) continue;
        const a = ix[t] * 2, b = ix[t + 1] * 2, c = ix[t + 2] * 2;
        const cr = (out[b] - out[a]) * (out[c + 1] - out[a + 1]) - (out[c] - out[a]) * (out[b + 1] - out[a + 1]);
        if (cr * sign[k] >= eps) continue;
        folded = true;
        const mx = (out[a] - R[a] + out[b] - R[b] + out[c] - R[c]) / 3;
        const my = (out[a + 1] - R[a + 1] + out[b + 1] - R[b + 1] + out[c + 1] - R[c + 1]) / 3;
        if (!pin[a >> 1]) relax(out, R, a, mx, my);
        if (!pin[b >> 1]) relax(out, R, b, mx, my);
        if (!pin[c >> 1]) relax(out, R, c, mx, my);
      }
      if (!folded) break;
    }
  }

  placeIris(out, e) {
    const E = EYES[e], F = this.F, R = this.rig.rest, cur = this.cur, mid = this.rig.eyeMid[e], L = this.eyeRest[e];
    const c = E.iris;
    // Posición del iris en el ojo del video: a lo largo del eje entre esquinas y entre párpados.
    let h = 0, t = 0.5;
    if (eyeFrame(cur, E, faceDown(cur, this.dCur), F)) {
      const s = ((cur[c * 2] - F[0]) * F[2] + (cur[c * 2 + 1] - F[1]) * F[3]) / F[6];
      h = clamp(s - 0.5, -0.3, 0.3);
      const nu = lidAt(cur, E.up, F, s), nl = lidAt(cur, E.lo, F, s);
      if (nl - nu > 0.05 * F[6]) {
        const nc = (cur[c * 2] - F[0]) * F[4] + (cur[c * 2 + 1] - F[1]) * F[5];
        t = 0.5 + clamp((nc - nu) / (nl - nu) - 0.5, -0.25, 0.25);
      }
    }
    if (eyeFrame(out, E, this.dChar, F) && L[6] > 0) {
      // Centro entre los párpados; los bordes conservan su posición respecto al centro, sin
      // salirse del ojo (con el ojo cerrado quedan todos sobre la línea del párpado).
      const sc = 0.5 + h;
      let nu = lidAt(out, E.up, F, sc), nl = Math.max(nu, lidAt(out, E.lo, F, sc));
      const nc = nu + (nl - nu) * t;
      put(out, c, F, sc, nc);
      for (let k = 0; k < 3; k += 2) {
        const s = k ? clamp(sc + L[4] - L[2], sc + 0.03, 0.97) : clamp(sc + L[0] - L[2], 0.03, sc - 0.03);
        nu = lidAt(out, E.up, F, s);
        nl = Math.max(nu, lidAt(out, E.lo, F, s));
        const n = clamp(nc + ((L[k * 2 + 1] - L[3]) * F[6]) / L[6], nu + 0.05 * (nl - nu), nl - 0.05 * (nl - nu));
        put(out, mid[k], F, s, n);
      }
    } else {
      for (const i of mid) { out[i * 2] = R[i * 2]; out[i * 2 + 1] = R[i * 2 + 1]; }
    }
    // El resto del anillo del iris (no forma parte de la malla) acompaña al centro.
    const dx = out[c * 2] - R[c * 2], dy = out[c * 2 + 1] - R[c * 2 + 1];
    for (let i = c + 1; i <= c + 4; i++) {
      if (i === mid[0] || i === mid[2]) continue;
      out[i * 2] = R[i * 2] + dx;
      out[i * 2 + 1] = R[i * 2 + 1] + dy;
    }
  }

  // Ángulo de la línea de los ojos del video (33 -> 263), para el giro de la cabeza en el plano.
  // Si el video está en espejo respecto al personaje se mide al revés (263 -> 33) para que
  // una cabeza derecha dé el mismo ángulo que en el personaje.
  eyeAngle() {
    if (!this.hasCur) return 0;
    const c = this.cur, k = this.mirrored ? -1 : 1;
    return Math.atan2((c[527] - c[67]) * k, (c[526] - c[66]) * k);
  }

  // Puntos de los labios interiores del video (px), en el mismo orden que rig.innerLip.
  // Devuelve siempre el mismo array (se sobrescribe en cada llamada).
  sourceInnerLip() {
    for (let k = 0; k < INNER_LIP.length; k++) {
      this.lip[k * 2] = this.cur[INNER_LIP[k] * 2];
      this.lip[k * 2 + 1] = this.cur[INNER_LIP[k] * 2 + 1];
    }
    return this.lip;
  }
}

// Coloca el punto i en las coordenadas (s, n) del ojo F.
function put(p, i, F, s, n) {
  p[i * 2] = F[0] + F[2] * s * F[6] + F[4] * n;
  p[i * 2 + 1] = F[1] + F[3] * s * F[6] + F[5] * n;
}

// Separación de los puntos u -> l sobre el eje (dx, dy).
function gapAlong(p, u, l, dx, dy) {
  return (p[l * 2] - p[u * 2]) * dx + (p[l * 2 + 1] - p[u * 2 + 1]) * dy;
}

// Separación de u -> l en el video (alineado con la referencia), llevada a la escala del personaje.
function mappedGap(al, M, u, l, dx, dy) {
  const x = al[l * 2] - al[u * 2], y = al[l * 2 + 1] - al[u * 2 + 1];
  return Math.max(0, (M[0] * x + M[1] * y) * dx + (M[2] * x + M[3] * y) * dy);
}

// Acerca el punto i a la línea entre las esquinas del ojo (F de eyeFrame) en la fracción w.
function flatten(p, i, F, w) {
  const dn = ((p[i * 2] - F[0]) * F[4] + (p[i * 2 + 1] - F[1]) * F[5]) * w;
  p[i * 2] -= F[4] * dn;
  p[i * 2 + 1] -= F[5] * dn;
}

// Lleva el desplazamiento del vértice v (índice x en el array plano) a medio camino de (mx, my).
function relax(p, R, v, mx, my) {
  p[v] = R[v] + (p[v] - R[v] + mx) / 2;
  p[v + 1] = R[v + 1] + (p[v + 1] - R[v + 1] + my) / 2;
}

// Si el punto inferior `l` queda por encima del superior `u` (sobre el eje abajo), ambos van al medio.
function uncross(p, u, l, dx, dy) {
  if ((p[l * 2] - p[u * 2]) * dx + (p[l * 2 + 1] - p[u * 2 + 1]) * dy > -1e-3) return;
  const mx = (p[l * 2] + p[u * 2]) / 2, my = (p[l * 2 + 1] + p[u * 2 + 1]) / 2;
  p[u * 2] = p[l * 2] = mx;
  p[u * 2 + 1] = p[l * 2 + 1] = my;
}
