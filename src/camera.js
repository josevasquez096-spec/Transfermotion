// Cámara de encuadre: el resultado muestra lo mismo que el video fuente (primer plano, plano medio, general).
// Se ajusta posado ≈ k·fuente + t (escala uniforme y traslación, sin rotación) con pares de puntos
// anatómicos, y el rectángulo del cuadro fuente llevado al espacio posado es lo que debe verse.

const MIN_PAIRS = 3;
// Reponderación de Huber: un punto mal detectado (una mano que salta) no tuerce el ajuste.
const IRLS = 2;
const HUBER = 2.5;

const clamp = (v, a, b) => Math.max(a, Math.min(b, v));

// Memoria de trabajo reutilizada entre llamadas (sin reservas por cuadro).
let base = new Float64Array(64);
let wts = new Float64Array(64);
let res = new Float64Array(64);

// Ajuste por mínimos cuadrados ponderados de d ≈ k·s + t. Función pura.
// pairs: [{sx, sy, dx, dy, w}]; se ignoran los pares con valores no finitos o w <= 0.
// Devuelve { k, tx, ty, sx, sy, dx, dy, n, spread } (sx..dy = centroides ponderados fuente/posado,
// spread = dispersión RMS de la fuente), o null con menos de 3 pares o puntos casi coincidentes
// (dispersión < minSpread, en px de la fuente). k puede salir absurdo: lo valida quien llama.
export function fitPairs(pairs, minSpread = 1e-6) {
  const n = pairs ? pairs.length : 0;
  if (n > base.length) {
    base = new Float64Array(n * 2);
    wts = new Float64Array(n * 2);
    res = new Float64Array(n * 2);
  }
  let m = 0;
  for (let i = 0; i < n; i++) {
    const p = pairs[i];
    const ok = p && p.w > 0 && Number.isFinite(p.w) && Number.isFinite(p.sx) && Number.isFinite(p.sy) &&
      Number.isFinite(p.dx) && Number.isFinite(p.dy);
    base[i] = wts[i] = ok ? p.w : 0;
    if (ok) m++;
  }
  if (m < MIN_PAIRS) return null;

  let fit = null;
  for (let it = 0; it <= IRLS; it++) {
    let sw = 0, msx = 0, msy = 0, mdx = 0, mdy = 0;
    for (let i = 0; i < n; i++) {
      const w = wts[i];
      if (!w) continue;
      const p = pairs[i];
      sw += w;
      msx += w * p.sx;
      msy += w * p.sy;
      mdx += w * p.dx;
      mdy += w * p.dy;
    }
    msx /= sw; msy /= sw; mdx /= sw; mdy /= sw;
    let sss = 0, ssd = 0;
    for (let i = 0; i < n; i++) {
      const w = wts[i];
      if (!w) continue;
      const p = pairs[i];
      const ax = p.sx - msx, ay = p.sy - msy;
      sss += w * (ax * ax + ay * ay);
      ssd += w * (ax * (p.dx - mdx) + ay * (p.dy - mdy));
    }
    const spread = Math.sqrt(sss / sw);
    // Puntos casi en el mismo sitio: la escala no se puede medir (si pasa al reponderar, vale el ajuste previo).
    if (!(spread >= minSpread) || !(spread > 0)) break;
    const k = ssd / sss;
    fit = { k, tx: mdx - k * msx, ty: mdy - k * msy, sx: msx, sy: msy, dx: mdx, dy: mdy, n: m, spread };
    if (it === IRLS) break;

    // Residuos del ajuste y umbral robusto: 2.5 × mediana, con un mínimo del 3 % del tamaño posado.
    let r = 0;
    for (let i = 0; i < n; i++) {
      if (!base[i]) continue;
      const p = pairs[i];
      res[r++] = Math.hypot(k * p.sx + fit.tx - p.dx, k * p.sy + fit.ty - p.dy);
    }
    const sorted = res.subarray(0, r).sort();
    const med = r & 1 ? sorted[r >> 1] : 0.5 * (sorted[r / 2 - 1] + sorted[r / 2]);
    const c = Math.max(HUBER * med, 0.03 * Math.abs(k) * spread, 1e-9);
    for (let i = 0; i < n; i++) {
      if (!base[i]) continue;
      const p = pairs[i];
      const e = Math.hypot(k * p.sx + fit.tx - p.dx, k * p.sy + fit.ty - p.dy);
      wts[i] = base[i] * (e > c ? c / e : 1);
    }
  }
  return fit;
}

// Cámara que sigue el encuadre de la fuente con suavizado temporal.
// Estado: escala k y traslación t (el rectángulo es { x: tx, y: ty, w: k·srcW, h: k·srcH }).
//  - La escala (zoom) se suaviza en escala logarítmica con constante `tau` (0.25 s).
//  - La posición se suaviza con `tauPos` (0.08 s, más corta): dice dónde está la persona en el cuadro y
//    con 0.25 s se quedaría atrás al bailar. El zoom se hace alrededor del centro de la persona.
//  - Un salto de más del 40 % (`maxStep`) en un cuadro sin corte se limita a ese 40 % (ajuste atípico).
//  - k fuera de [minK, maxK] se descarta y se mantiene el encuadre anterior.
//  - Sin ajuste válido (pocos pares) se mantiene el último encuadre `hold` segundos y luego se
//    devuelve null; el siguiente ajuste válido se aplica de golpe.
export class FramingCamera {
  constructor({ tau = 0.25, tauPos = 0.08, maxStep = 0.4, minK = 0.05, maxK = 50, hold = 0.25 } = {}) {
    this.tau = tau;
    this.tauPos = tauPos;
    this.maxStep = maxStep;
    this.minK = minK;
    this.maxK = maxK;
    this.hold = hold;
    this.reset();
  }

  // Olvida el encuadre: el próximo ajuste válido se aplica sin suavizar.
  reset() {
    this.valid = false;
    this.k = 1;
    this.tx = 0;
    this.ty = 0;
    this.missing = 0;
    this.rect = null;
  }

  // pairs: [{sx, sy, dx, dy, w}] (punto en px de la fuente y el mismo punto en el espacio posado, peso w > 0).
  // Devuelve el cuadro fuente en el espacio posado { x, y, w, h } (x, y = esquina superior izquierda),
  // suavizado en el tiempo, o null si no hay ajuste fiable (quien llama muestra la vista completa).
  // snap = true (corte de escena): se aplica el nuevo ajuste al instante y no se reutiliza nada anterior.
  update(pairs, srcW, srcH, dt, snap = false) {
    const step = Number.isFinite(dt) && dt > 0 ? Math.min(dt, 1) : 0;
    const fit = srcW > 0 && srcH > 0 ? fitPairs(pairs, 0.002 * Math.max(srcW, srcH)) : null;
    const sane = fit && fit.k >= this.minK && fit.k <= this.maxK;
    if (!sane) {
      // Sin dato fiable: tras un corte no sirve el encuadre viejo; si no, se aguanta un momento.
      this.missing += step;
      if (snap || !this.valid || this.missing > this.hold || !(srcW > 0 && srcH > 0)) {
        this.valid = false;
        this.rect = null;
        return null;
      }
      return this.output(srcW, srcH);
    }
    this.missing = 0;
    if (snap || !this.valid) {
      this.valid = true;
      this.k = fit.k;
      this.tx = fit.tx;
      this.ty = fit.ty;
      return this.output(srcW, srcH);
    }

    // Zoom: hacia el k ajustado, como mucho un 40 % del actual, alrededor del centro de la persona
    // (el punto de la fuente sx,sy sigue cayendo en el mismo sitio del espacio posado).
    const lim = Math.log1p(this.maxStep);
    const dl = clamp(Math.log(fit.k / this.k), -lim, lim);
    const k = this.k * Math.exp(dl * (1 - Math.exp(-step / this.tau)));
    this.tx += (this.k - k) * fit.sx;
    this.ty += (this.k - k) * fit.sy;
    this.k = k;

    // Posición: lo que falta para que la persona quede donde debe, limitado al 40 % del cuadro.
    let ex = fit.dx - k * fit.sx - this.tx, ey = fit.dy - k * fit.sy - this.ty;
    const rel = Math.max(Math.abs(ex) / (k * srcW), Math.abs(ey) / (k * srcH));
    if (rel > this.maxStep) {
      ex *= this.maxStep / rel;
      ey *= this.maxStep / rel;
    }
    const a = 1 - Math.exp(-step / this.tauPos);
    this.tx += a * ex;
    this.ty += a * ey;
    return this.output(srcW, srcH);
  }

  output(srcW, srcH) {
    this.rect = { x: this.tx, y: this.ty, w: this.k * srcW, h: this.k * srcH };
    return { ...this.rect };
  }
}

// Vista { scale, ox, oy } (lienzo = posado·scale + [ox, oy]) para que `rect` quepa entero en el lienzo,
// centrado (contain). Con un rectángulo inválido devuelve la identidad.
export function fitView(rect, canvasW, canvasH) {
  if (!rect || !(rect.w > 0 && rect.h > 0) || !Number.isFinite(rect.x) || !Number.isFinite(rect.y) ||
    !(canvasW > 0 && canvasH > 0) || !Number.isFinite(rect.w) || !Number.isFinite(rect.h)) {
    return { scale: 1, ox: 0, oy: 0 };
  }
  const scale = Math.min(canvasW / rect.w, canvasH / rect.h);
  return {
    scale,
    ox: canvasW / 2 - (rect.x + rect.w / 2) * scale,
    oy: canvasH / 2 - (rect.y + rect.h / 2) * scale,
  };
}
