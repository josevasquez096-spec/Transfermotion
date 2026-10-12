// Filtros temporales: One-Euro (suavizado adaptativo de landmarks) y detector de cortes de escena.

const TAU = 2 * Math.PI;

// Factor de suavizado exponencial para una frecuencia de corte (Hz) y un paso dt (s).
// cutoff = Infinity → 1 (sin filtrar); cutoff = 0 → 0 (congelado).
const alphaFor = (cutoff, dt) => 1 / (1 + 1 / (TAU * cutoff * dt));

// ---------- One-Euro (Casiez et al. 2012) ----------
// Paso bajo cuya frecuencia de corte sube con la velocidad: quieto = muy suave, rápido = poco retraso.
// Corte = minCutoff + beta·|velocidad|; beta va en 1/(unidades del valor), p. ej. 1/px si filtras píxeles.
// `dims` agrupa componentes consecutivas (2 = puntos x,y): el grupo comparte corte según su rapidez,
// así un punto no se deforma distinto en x que en y.
export class OneEuro {
  constructor({ minCutoff = 1.2, beta = 0.03, dCutoff = 1.0, dims = 1 } = {}) {
    this.minCutoff = minCutoff;
    this.beta = beta;
    this.dCutoff = dCutoff;
    this.dims = Math.max(1, dims | 0);
    this.n = -1;
    this.t = NaN;
    this.dt = 1 / 30;
  }

  // Cambia parámetros en caliente (p. ej. al mover el deslizador) sin perder el estado.
  setParams({ minCutoff, beta, dCutoff } = {}) {
    if (minCutoff !== undefined) this.minCutoff = minCutoff;
    if (beta !== undefined) this.beta = beta;
    if (dCutoff !== undefined) this.dCutoff = dCutoff;
    return this;
  }

  // Mapea el deslizador "Suavizado" (0..0.95) a parámetros: 0 ≈ crudo, 0.95 = muy suave.
  // Calibrado para píxeles de un video de ~720 px. `scale` = tamaño de esa referencia en las unidades
  // de tus valores: srcH / 720 para píxeles de otra resolución, 1 / 720 para valores normalizados 0..1.
  // En reposo, s = 0.5 quita ~60 % del temblor (corte 1.5 Hz); en movimiento beta abre el corte y el
  // retraso es menor que con el suavizado exponencial fijo anterior.
  static fromSmoothing(s, scale = 1) {
    const k = Math.pow(Math.min(1, Math.max(0, (Number(s) || 0) / 0.95)), 0.75);
    return {
      minCutoff: 40 * Math.pow(0.2 / 40, k), // 40 Hz → 0.2 Hz (log)
      beta: (0.08 * Math.pow(0.004 / 0.08, k)) / (scale > 0 ? scale : 1),
      dCutoff: 1.0,
    };
  }

  // Olvida el historial (corte de escena, nueva fuente). La siguiente muestra sale tal cual.
  reset() {
    this.t = NaN;
    if (this.ok) this.ok.fill(0);
  }

  // values: Float32Array | number[]; t: segundos, monótono. Devuelve un Float32Array INTERNO que se
  // reutiliza en cada llamada (cópialo si lo necesitas después). Si cambia la longitud se reinicia.
  // Un valor no finito (NaN = "sin dato") no toca el estado: sale el último filtrado de esa componente.
  filter(values, t) {
    const n = values.length;
    if (n !== this.n) {
      this.n = n;
      this.x = new Float64Array(n);
      this.dx = new Float64Array(n);
      this.ok = new Uint8Array(n);
      this.out = new Float32Array(n);
      this.t = NaN;
    }
    const { x, dx, ok, out } = this;
    let dt = t - this.t;
    if (dt > 0) this.dt = Math.min(dt, 0.1);
    else dt = this.dt; // tiempo repetido, ausente o hacia atrás: usa el último paso válido
    if (Number.isFinite(t)) this.t = t;
    const ad = alphaFor(this.dCutoff, dt);
    const D = this.dims;
    for (let g = 0; g < n; g += D) {
      const end = Math.min(n, g + D);
      // Velocidad filtrada del grupo.
      let sp = 0;
      for (let i = g; i < end; i++) {
        const v = values[i];
        if (!Number.isFinite(v) || !ok[i]) continue;
        dx[i] += ad * ((v - x[i]) / dt - dx[i]);
        sp += dx[i] * dx[i];
      }
      const a = alphaFor(this.minCutoff + this.beta * Math.sqrt(sp), dt);
      for (let i = g; i < end; i++) {
        const v = values[i];
        if (!Number.isFinite(v)) {
          out[i] = ok[i] ? x[i] : v;
          continue;
        }
        if (ok[i]) x[i] += a * (v - x[i]);
        else {
          x[i] = v;
          dx[i] = 0;
          ok[i] = 1;
        }
        out[i] = x[i];
      }
    }
    return out;
  }
}

// ---------- Detector de cortes ----------
// Se compara una miniatura gris de 32×18 con la del cuadro anterior:
//  - mad: diferencia absoluta media de luminancia (0..1);
//  - hist: distancia entre histogramas de 8 niveles con reparto lineal entre niveles (variación total, 0..1);
//  - comp: diferencia con el mejor desplazamiento global (±2 px de miniatura en pasos de medio píxel,
//    ≈ ±6 % del cuadro) ÷ diferencia sin desplazar. Bajo = el cambio lo explica un paneo o un temblor;
//  - corr: correlación de estructura (−1..1). Alta con mucho cambio = solo cambió el brillo (destello).
// score = (mad + 0.5·hist) · min(1, comp / 0.8).
// Medido con videos reales (primeros planos con cámara en mano, webcam, baile) a 30, 15 y 10 fps:
// sin corte, score ≤ 0.13 en el peor caso (cara riendo con cámara en mano a 15 fps) y casi siempre < 0.08;
// cortes reales ≥ 0.19, incluido el cambio de plano de la misma escena (acercamiento o alejamiento 1.4×)
// y ≈ 0.14 entre escenas oscuras. Un salto dentro del mismo plano fijo (mismo encuadre) no se detecta,
// y no hace falta: el encuadre y la referencia de la cara siguen valiendo.
export const THUMB_W = 32;
export const THUMB_H = 18;
const SHIFT = 2;
const HIST_W = 0.5;
const COMP_K = 0.8;

const histA = new Float64Array(8);
const histB = new Float64Array(8);
const phase = new Float32Array(THUMB_W * THUMB_H);

function addHist(h, v) {
  // Reparto lineal entre los dos niveles vecinos: un cambio leve de brillo no salta de nivel.
  const p = Math.min(7, Math.max(0, v / 32 - 0.5));
  const i = Math.min(6, p | 0), f = p - i;
  h[i] += 1 - f;
  h[i + 1] += f;
}

// prevGray, curGray: luminancia 0..255, filas de THUMB_W (mismo tamaño). Función pura.
// Devuelve (y rellena `out` si se pasa) { mad, hist, comp, corr, score }.
export function frameDistance(prevGray, curGray, out = {}) {
  const W = THUMB_W;
  const n = Math.min(prevGray.length, curGray.length);
  const H = Math.floor(n / W);
  histA.fill(0);
  histB.fill(0);
  let sad = 0, sa = 0, sb = 0, saa = 0, sbb = 0, sab = 0;
  for (let i = 0; i < n; i++) {
    const a = prevGray[i], b = curGray[i];
    sad += Math.abs(a - b);
    addHist(histA, a);
    addHist(histB, b);
    sa += a;
    sb += b;
    saa += a * a;
    sbb += b * b;
    sab += a * b;
  }
  let hist = 0;
  for (let k = 0; k < 8; k++) hist += Math.abs(histA[k] - histB[k]);
  const mad = n ? sad / (255 * n) : 0;
  hist = n ? hist / (2 * n) : 0;
  const va = saa - (sa * sa) / n, vb = sbb - (sb * sb) / n;
  // Imagen casi plana: la estructura no es comparable (0 = neutro).
  const corr = va > n * 4 && vb > n * 4 ? (sab - (sa * sb) / n) / Math.sqrt(va * vb) : 0;

  // Compensación de movimiento global en una ventana interior fija (igual para todos los desplazamientos).
  let comp = 1;
  const S = SHIFT;
  if (H > 2 * S + 2 && W > 2 * S + 2) {
    let zero = 0;
    for (let y = S; y < H - S; y++) {
      for (let x = S; x < W - S; x++) zero += Math.abs(prevGray[y * W + x] - curGray[y * W + x]);
    }
    let best = zero;
    for (let ph = 0; ph < 4; ph++) {
      const px = ph & 1, py = ph >> 1;
      // Fase de medio píxel: promedio con el vecino derecho / inferior.
      for (let y = 0; y < H; y++) {
        const r0 = y * W, r1 = Math.min(H - 1, y + py) * W;
        for (let x = 0; x < W; x++) {
          const x1 = Math.min(W - 1, x + px);
          phase[r0 + x] = (prevGray[r0 + x] + prevGray[r0 + x1] + prevGray[r1 + x] + prevGray[r1 + x1]) * 0.25;
        }
      }
      for (let dy = -S; dy <= S - py; dy++) {
        for (let dx = -S; dx <= S - px; dx++) {
          if (ph === 0 && dx === 0 && dy === 0) continue;
          let s = 0;
          // Se abandona en cuanto supera al mejor (la mayoría de desplazamientos acaban pronto).
          for (let y = S; y < H - S && s < best; y++) {
            const rp = (y + dy) * W + dx, rc = y * W;
            for (let x = S; x < W - S; x++) s += Math.abs(phase[rp + x] - curGray[rc + x]);
          }
          if (s < best) best = s;
        }
      }
    }
    comp = zero > 0 ? Math.min(1, best / zero) : 1;
  }
  out.mad = mad;
  out.hist = hist;
  out.comp = comp;
  out.corr = corr;
  out.score = (mad + HIST_W * hist) * Math.min(1, comp / COMP_K);
  return out;
}

// Detector en línea. Umbrales (ver medidas arriba):
//  - threshold (0.13): score mínimo de un corte;
//  - ratio (3): además debe superar ratio × el nivel reciente del score (media exponencial, α = 0.35,
//    que baja como mucho a la mitad por cuadro para no hundirse con cuadros repetidos). El movimiento
//    rápido sostenido (baile, cámara en mano) sube la exigencia; un corte real es un pico aislado;
//  - minFrames (5): cuadros mínimos entre dos cortes (un fundido no dispara varias veces).
// Un candidato que solo cambia el brillo (corr ≥ 0.85, posible destello) se confirma un cuadro después,
// si el siguiente no vuelve a parecerse al de antes. Un salto de `t` hacia atrás (bucle o búsqueda en el
// video) también cuenta como corte. Nunca devuelve true en el primer cuadro, y en el segundo solo por un
// salto de `t` (aún no hay nivel de referencia).
// Limitación conocida: un paneo que arranca de golpe a más de ~6 % del cuadro por muestra puede contar
// como corte (efecto leve: solo reinicia suavizados y referencias).
export class CutDetector {
  constructor({ threshold = 0.13, ratio = 3, minFrames = 5 } = {}) {
    this.threshold = threshold;
    this.ratio = ratio;
    this.minFrames = minFrames;
    const size = THUMB_W * THUMB_H;
    this.prev = new Uint8Array(size);
    this.pre = new Uint8Array(size);
    this.gray = new Uint8Array(size);
    this.last = { mad: 0, hist: 0, comp: 1, corr: 0, score: 0 }; // métricas del último par (depuración)
    this.tmp = {};
    this.ctx = null;
    this.broken = false;
    this.reset();
  }

  reset() {
    this.frames = 0;
    this.base = 0;
    this.since = Infinity;
    this.pending = false;
    this.tPrev = NaN;
  }

  // source: HTMLVideoElement | HTMLCanvasElement (o cualquier imagen dibujable). t: tiempo del cuadro,
  // idealmente video.currentTime; con el mismo t que la llamada anterior el cuadro se ignora.
  // Llamar en cada cuadro nuevo del video aunque la detección de pose vaya más lenta. Coste: el análisis
  // ~0.05 ms; dibujar el cuadro en el canvas de lectura, 1–3 ms según el navegador (lectura de GPU).
  // Si ya dibujas el cuadro en un canvas 2D propio, puedes pasar ese canvas como `source`.
  check(source, t) {
    const g = this.grab(source);
    return g ? this.checkGray(g, t) : false;
  }

  // Miniatura gris 32×18 (Uint8Array interno, se reutiliza) del cuadro, o null si aún no se puede leer.
  grab(source) {
    if (this.broken || !source) return null;
    if (source.readyState !== undefined && source.readyState < 2) return null;
    const sw = source.videoWidth || source.width, sh = source.videoHeight || source.height;
    if (!sw || !sh) return null;
    // Se dibuja a 64×36 (bilineal 'low': en un canvas de CPU 'high' recalcula mipmaps del cuadro entero)
    // y se promedia 2×2: menos aliasing que reducir de golpe a 32×18.
    const w = THUMB_W * 2, h = THUMB_H * 2;
    if (!this.ctx) {
      let c = null;
      if (typeof document !== 'undefined') c = document.createElement('canvas');
      else if (typeof OffscreenCanvas !== 'undefined') c = new OffscreenCanvas(w, h);
      if (!c) {
        this.broken = true;
        return null;
      }
      c.width = w;
      c.height = h;
      this.ctx = c.getContext('2d', { willReadFrequently: true });
      this.ctx.imageSmoothingEnabled = true;
      this.ctx.imageSmoothingQuality = 'low';
    }
    let d;
    try {
      this.ctx.drawImage(source, 0, 0, w, h);
      d = this.ctx.getImageData(0, 0, w, h).data;
    } catch (err) {
      // Video de otro origen (canvas contaminado): no se puede leer nunca, se desactiva.
      if (err && err.name === 'SecurityError') this.broken = true;
      return null;
    }
    const g = this.gray;
    for (let y = 0; y < THUMB_H; y++) {
      for (let x = 0; x < THUMB_W; x++) {
        let s = 0;
        for (let k = 0; k < 4; k++) {
          const p = ((2 * y + (k >> 1)) * w + 2 * x + (k & 1)) * 4;
          s += 77 * d[p] + 150 * d[p + 1] + 29 * d[p + 2];
        }
        g[y * THUMB_W + x] = s >> 10;
      }
    }
    return g;
  }

  // Núcleo puro (sin DOM): gray = luminancia 0..255 de 32×18. Devuelve true si hay corte.
  checkGray(gray, t) {
    if (this.frames > 0 && t === this.tPrev) return false;
    const jumped = this.frames > 0 && t < this.tPrev;
    if (Number.isFinite(t)) this.tPrev = t;
    if (this.frames++ === 0) {
      this.prev.set(gray);
      return false;
    }
    const d = frameDistance(this.prev, gray, this.last);
    const s = d.score;
    this.since++;
    let cut = jumped;
    const wasPending = this.pending;
    this.pending = false;
    if (wasPending) {
      // Candidato tipo destello: corte si sigue distinto del cuadro previo y el nuevo cuadro es estable.
      const back = frameDistance(this.pre, gray, this.tmp).score;
      cut = cut || (back >= this.threshold && s < 0.5 * back);
    }
    if (this.frames === 2) {
      if (!cut) this.base = s;
    } else if (!cut && !wasPending && this.since >= this.minFrames &&
      s >= this.threshold && s >= this.ratio * this.base) {
      if (d.corr < 0.85) cut = true;
      else {
        this.pending = true;
        this.pre.set(this.prev);
      }
    }
    if (cut) this.since = 0;
    else if (!this.pending && !wasPending) this.base += 0.35 * (Math.max(s, 0.5 * this.base) - this.base);
    this.prev.set(gray);
    return cut;
  }
}
