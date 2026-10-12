import { J, N, VIS, fromLandmarks, restInfo, retarget, boneTransforms, drawSkeleton, dist } from './skeleton.js';
import { buildRig } from './mesh.js';
import { Renderer } from './renderer.js';
import { demoPose, demoCharacter, DEMO_SIZE } from './demo.js';
import { getVideoLandmarker, getImageLandmarker, getFaceVideoLandmarker, getFaceImageLandmarker } from './pose.js';
import { buildFaceRig, FaceDriver } from './face.js';
import { OneEuro, CutDetector } from './filters.js';
import { FramingCamera, fitView } from './camera.js';

const $ = (id) => document.getElementById(id);
const el = {
  status: $('status'),
  video: $('video'),
  videoInput: $('videoInput'),
  webcamBtn: $('webcamBtn'),
  demoMotionBtn: $('demoMotionBtn'),
  imageInput: $('imageInput'),
  demoCharBtn: $('demoCharBtn'),
  srcCanvas: $('srcCanvas'),
  charCanvas: $('charCanvas'),
  glCanvas: $('glCanvas'),
  overlay: $('overlayCanvas'),
  resultStage: $('resultStage'),
  cutout: $('cutout'),
  playBtn: $('playBtn'),
  recBtn: $('recBtn'),
  showSkel: $('showSkel'),
  showWire: $('showWire'),
  followRoot: $('followRoot'),
  framing: $('framing'),
  animateFace: $('animateFace'),
  transparent: $('transparent'),
  bgColor: $('bgColor'),
  smoothing: $('smoothing'),
  recalBtn: $('recalBtn'),
};

const srcCtx = el.srcCanvas.getContext('2d');
const charCtx = el.charCanvas.getContext('2d');
const overlayCtx = el.overlay.getContext('2d');

let renderer;
try {
  renderer = new Renderer(el.glCanvas);
} catch (err) {
  setStatus(err.message, 'error');
  throw err;
}

// iOS exige estas propiedades (no solo los atributos) para reproducir en línea.
el.video.muted = true;
el.video.playsInline = true;

const DEMO = demoCharacter();
const bones = new Float32Array(19 * 4);

// Fotograma actual de la fuente, reducido y (en la cámara) reflejado como un espejo.
// Todo se calcula sobre él: pose, cara, cortes de plano y textura de la boca.
const MAX_SRC = 720;
const frameCanvas = document.createElement('canvas');
const frameCtx = frameCanvas.getContext('2d');

// Puntos de la cara usados para encuadrar la cámara (ojos, nariz, mentón, frente, mejillas, boca).
const FACE_FRAMING = [33, 263, 1, 152, 10, 234, 454, 61, 291];
// Puntos de la cara que se dibujan sobre el video fuente.
const FACE_DOTS = [10, 338, 297, 332, 284, 251, 389, 356, 454, 323, 361, 288, 397, 365, 379, 378, 400, 377, 152,
  148, 176, 149, 150, 136, 172, 58, 132, 93, 234, 127, 162, 21, 54, 103, 67, 109, 33, 160, 158, 133, 153, 144, 362,
  385, 387, 263, 373, 380, 61, 40, 37, 0, 267, 270, 291, 321, 314, 17, 84, 91, 13, 14, 1, 468, 473];
const LOST_LIMIT = 6;
const wrap = (a) => Math.atan2(Math.sin(a), Math.cos(a));

const state = {
  source: 'demo', // 'demo' | 'video' | 'webcam'
  mirror: false,
  playing: true,
  t: 0,
  lastTick: performance.now(),
  srcSize: { ...DEMO_SIZE },
  src: null, // articulaciones fuente suavizadas
  srcRef: null, // referencia para el desplazamiento global
  landmarker: null,
  lastVideoTime: -1,
  stream: null,
  target: null,
  posed: null,
  recorder: null,
  drag: -1,
  needsTap: false,
  poseLost: 0,
  faceLandmarker: null,
  face: null, // { lm: [{x,y,z}] en px de la fuente, blend, lost }
  jointFilter: null,
  faceFilter: null,
  cuts: new CutDetector(),
  camera: new FramingCamera(),
  snapCamera: true,
  view: { scale: 1, ox: 0, oy: 0 },
};
resetFilters();

function setStatus(text, kind = '') {
  el.status.textContent = text;
  el.status.className = `status ${kind}`;
}

// ---------- Personaje ----------

const cloneJoints = (js) => js.map((p) => ({ x: p.x, y: p.y, v: 1 }));

function setTarget(base, rest, mask, faceLm = null) {
  state.target = { base, rest: cloneJoints(rest), mask, faceLm, w: base.width, h: base.height };
  state.srcRef = null;
  rebuildTexture();
  setupFace();
}

// Malla de la cara del personaje (si se detectó): ojos, cejas, boca, y un anillo para pelo y orejas.
function setupFace() {
  const t = state.target;
  t.face = null;
  if (!t.faceLm) return;
  const rig = buildFaceRig(t.faceLm, t.w, t.h);
  // El anillo exterior no debe salirse de la imagen (repetiría los píxeles del borde).
  for (let i = 478; i < rig.n; i++) {
    rig.rest[i * 2] = Math.min(t.w, Math.max(0, rig.rest[i * 2]));
    rig.rest[i * 2 + 1] = Math.min(t.h, Math.max(0, rig.rest[i * 2 + 1]));
    rig.uv[i * 2] = rig.rest[i * 2] / t.w;
    rig.uv[i * 2 + 1] = rig.rest[i * 2 + 1] / t.h;
  }
  renderer.setFaceMesh({ uv: rig.uv, indices: rig.indices });
  t.face = {
    rig,
    driver: new FaceDriver(rig),
    targets: new Float32Array(rig.n * 2),
    pos: new Float32Array(rig.n * 2),
    mouthPos: new Float32Array(rig.innerLip.length * 6),
    mouthUv: new Float32Array(rig.innerLip.length * 6),
  };
}

function rebuildTexture() {
  const t = state.target;
  const c = document.createElement('canvas');
  c.width = t.w;
  c.height = t.h;
  const g = c.getContext('2d', { willReadFrequently: true });
  g.drawImage(t.base, 0, 0);
  const img = g.getImageData(0, 0, t.w, t.h);
  if (t.mask && el.cutout.checked) {
    const d = img.data;
    for (let i = 0; i < t.mask.length; i++) {
      // Borde suave entre persona y fondo.
      const m = Math.min(1, Math.max(0, (t.mask[i] - 0.3) / 0.4));
      d[i * 4 + 3] *= m;
    }
    g.putImageData(img, 0, 0);
  }
  t.composite = c;
  t.imageData = img;
  renderer.setFaceTexture(c);
  rebuildMesh();
}

function rebuildMesh() {
  const t = state.target;
  t.info = restInfo(t.rest);
  const rig = buildRig(t.imageData, t.rest);
  renderer.setTexture(rig.atlas);
  renderer.setMesh(rig.mesh);
  // Margen para que brazos y piernas extendidos quepan, incluso en imágenes estrechas.
  t.padY = Math.round(0.22 * Math.max(t.w, t.h));
  t.padX = Math.max(t.padY, Math.round(0.6 * t.h - t.w / 2));
  layout();
  el.charCanvas.width = t.w;
  el.charCanvas.height = t.h;
  drawCharacter();
}

// "Como el video": el resultado copia el encuadre de la fuente (primer plano, plano medio...).
const autoFraming = () => el.framing.value === 'auto' && state.source !== 'demo';

function layout() {
  const t = state.target;
  if (!t) return;
  let W, H;
  if (autoFraming()) {
    const k = 960 / Math.max(state.srcSize.w, state.srcSize.h);
    W = Math.round(state.srcSize.w * k);
    H = Math.round(state.srcSize.h * k);
  } else {
    W = t.w + 2 * t.padX;
    H = t.h + 2 * t.padY;
  }
  renderer.resize(W, H);
  el.overlay.width = W;
  el.overlay.height = H;
  state.view = fullView();
  state.camera.reset();
  state.snapCamera = true;
}

// Vista con el personaje completo (y su margen) dentro del lienzo.
function fullView() {
  const t = state.target;
  const rect = { x: -t.padX, y: -t.padY, w: t.w + 2 * t.padX, h: t.h + 2 * t.padY };
  return fitView(rect, el.glCanvas.width, el.glCanvas.height);
}

const charScale = () => state.target.w / (el.charCanvas.getBoundingClientRect().width || state.target.w);

function drawCharacter() {
  const t = state.target;
  charCtx.clearRect(0, 0, t.w, t.h);
  charCtx.drawImage(t.composite, 0, 0);
  drawSkeleton(charCtx, t.rest, { radius: 6 * charScale(), highlight: state.drag });
}

// Si no se detecta a nadie, colocamos un esqueleto plantilla para ajustar a mano.
function templateRest(w, h) {
  const s = Math.min(w / DEMO.canvas.width, h / DEMO.canvas.height) * 0.9;
  const ox = (w - DEMO.canvas.width * s) / 2, oy = (h - DEMO.canvas.height * s) / 2;
  return DEMO.rest.map((p) => ({ x: ox + p.x * s, y: oy + p.y * s, v: 1 }));
}

function resampleMask(src, sw, sh, w, h) {
  if (sw === w && sh === h) return Float32Array.from(src);
  const out = new Float32Array(w * h);
  for (let y = 0; y < h; y++) {
    const sy = Math.min(sh - 1, Math.floor((y * sh) / h));
    for (let x = 0; x < w; x++) out[y * w + x] = src[sy * sw + Math.min(sw - 1, Math.floor((x * sw) / w))];
  }
  return out;
}

function loadImage(url) {
  return new Promise((resolve, reject) => {
    const img = new Image();
    img.onload = () => resolve(img);
    img.onerror = () => reject(new Error('No se pudo leer la imagen.'));
    img.src = url;
  });
}

async function loadCharacter(file) {
  const url = URL.createObjectURL(file);
  try {
    const img = await loadImage(url);
    const s = Math.min(1, 1280 / Math.max(img.naturalWidth, img.naturalHeight));
    const base = document.createElement('canvas');
    base.width = Math.round(img.naturalWidth * s);
    base.height = Math.round(img.naturalHeight * s);
    base.getContext('2d').drawImage(img, 0, 0, base.width, base.height);

    setStatus('Cargando IA y detectando la pose del personaje…', 'busy');
    const landmarker = await getImageLandmarker();
    const res = landmarker.detect(base);
    let mask = null;
    const m = res.segmentationMasks?.[0];
    if (m) {
      mask = resampleMask(m.getAsFloat32Array(), m.width, m.height, base.width, base.height);
      m.close();
    }
    const joints = res.landmarks?.[0] ? fromLandmarks(res.landmarks[0], base.width, base.height) : null;
    setStatus('Buscando la cara del personaje…', 'busy');
    const faceLm = await detectCharacterFace(base, joints);
    if (joints) {
      setTarget(base, joints, mask, faceLm);
      setStatus(faceLm
        ? 'Personaje listo ✓ — cuerpo y cara detectados'
        : 'Personaje listo ✓ — no se encontró la cara, solo se animará el cuerpo');
    } else {
      setTarget(base, templateRest(base.width, base.height), null, faceLm);
      setStatus('No se detectó el cuerpo: coloca los puntos del esqueleto a mano', 'error');
    }
  } catch (err) {
    console.error(err);
    setStatus(`Error al procesar la imagen: ${err.message}`, 'error');
  } finally {
    URL.revokeObjectURL(url);
  }
}

// Busca la malla facial del personaje. Si la persona sale de cuerpo entero la cara es pequeña,
// así que primero se prueba con un recorte ampliado alrededor de la cabeza.
async function detectCharacterFace(base, joints) {
  const landmarker = await getFaceImageLandmarker();
  const toPx = (lm, x0, y0, sw, sh) => lm.map((p) => ({ x: x0 + p.x * sw, y: y0 + p.y * sh, z: p.z * sw }));
  if (joints) {
    const sw = dist(joints[J.lsh], joints[J.rsh]);
    const size = Math.max(1.7 * sw, 0.9 * dist(joints[J.chest], joints[J.head]), 64);
    const cx = joints[J.head].x, cy = joints[J.head].y - size * 0.1;
    const crop = document.createElement('canvas');
    crop.width = crop.height = 512;
    crop.getContext('2d').drawImage(base, cx - size / 2, cy - size / 2, size, size, 0, 0, 512, 512);
    const r = landmarker.detect(crop);
    if (r.faceLandmarks?.[0]) return toPx(r.faceLandmarks[0], cx - size / 2, cy - size / 2, size, size);
  }
  const r = landmarker.detect(base);
  return r.faceLandmarks?.[0] ? toPx(r.faceLandmarks[0], 0, 0, base.width, base.height) : null;
}

// Edición manual del esqueleto del personaje arrastrando sus puntos.
function charPoint(e) {
  const r = el.charCanvas.getBoundingClientRect();
  return { x: ((e.clientX - r.left) * state.target.w) / r.width, y: ((e.clientY - r.top) * state.target.h) / r.height };
}

el.charCanvas.addEventListener('pointerdown', (e) => {
  const p = charPoint(e);
  const reach = 16 * charScale();
  let best = -1, bd = reach;
  state.target.rest.forEach((j, i) => {
    const d = dist(j, p);
    if (d < bd) { bd = d; best = i; }
  });
  if (best < 0) return;
  state.drag = best;
  el.charCanvas.setPointerCapture(e.pointerId);
  el.charCanvas.classList.add('dragging');
  drawCharacter();
});
el.charCanvas.addEventListener('pointermove', (e) => {
  if (state.drag < 0) return;
  const p = charPoint(e);
  const t = state.target;
  t.rest[state.drag] = { x: Math.max(0, Math.min(t.w, p.x)), y: Math.max(0, Math.min(t.h, p.y)), v: 1 };
  t.info = restInfo(t.rest);
  drawCharacter();
});
const endDrag = () => {
  if (state.drag < 0) return;
  state.drag = -1;
  el.charCanvas.classList.remove('dragging');
  rebuildMesh();
};
el.charCanvas.addEventListener('pointerup', endDrag);
el.charCanvas.addEventListener('pointercancel', endDrag);

// ---------- Fuente de movimiento ----------

function stopStream() {
  state.stream?.getTracks().forEach((t) => t.stop());
  state.stream = null;
  el.video.srcObject = null;
}

function resetSource(type) {
  state.source = type;
  state.src = null;
  state.face = null;
  state.lastVideoTime = -1;
  onCut();
  el.webcamBtn.classList.toggle('active', type === 'webcam');
  el.demoMotionBtn.classList.toggle('active', type === 'demo');
}

// Fija el tamaño del fotograma de trabajo (máx. MAX_SRC px de lado).
function setSourceSize(w, h) {
  const k = Math.min(1, MAX_SRC / Math.max(w, h));
  state.srcSize = { w: Math.round(w * k), h: Math.round(h * k) };
  frameCanvas.width = state.srcSize.w;
  frameCanvas.height = state.srcSize.h;
  resetFilters();
  layout();
}

function resetFilters() {
  const s = parseFloat(el.smoothing.value);
  const scale = state.srcSize.h / 720;
  state.jointFilter = new OneEuro({ ...OneEuro.fromSmoothing(s, scale), dims: 2 });
  // La cara necesita reaccionar rápido (un parpadeo dura ~0,1 s).
  state.faceFilter = new OneEuro({ ...OneEuro.fromSmoothing(s * 0.5, scale), dims: 2 });
}

// Cambio de plano (o el video volvió a empezar): nada del plano anterior sirve.
function onCut() {
  state.jointFilter?.reset();
  state.faceFilter?.reset();
  state.cuts?.reset();
  state.srcRef = null;
  state.snapCamera = true;
  state.target?.face?.driver.reset();
}

// iOS (sobre todo en modo de bajo consumo) puede bloquear play() fuera de un toque.
// En ese caso pedimos al usuario que toque para reproducir.
async function playVideo() {
  try {
    await el.video.play();
    state.needsTap = false;
    return true;
  } catch (err) {
    if (err.name !== 'NotAllowedError') throw err;
    state.needsTap = true;
    setStatus('Toca el video o «▶ Reproducir» para empezar', 'busy');
    return false;
  }
}

function startDemo() {
  stopStream();
  el.video.pause();
  resetSource('demo');
  state.mirror = false;
  setSourceSize(DEMO_SIZE.w, DEMO_SIZE.h);
  setStatus('Movimiento de demostración');
}

async function ensureVideoLandmarker() {
  if (!state.landmarker || !state.faceLandmarker) {
    setStatus('Cargando los modelos de IA (cuerpo y cara)…', 'busy');
    [state.landmarker, state.faceLandmarker] = await Promise.all([getVideoLandmarker(), getFaceVideoLandmarker()]);
  }
}

function waitForMetadata(video) {
  return new Promise((resolve, reject) => {
    if (video.readyState >= 1) return resolve();
    video.onloadedmetadata = () => resolve();
    video.onerror = () => reject(new Error('No se pudo leer el video.'));
  });
}

async function startVideo(file) {
  try {
    stopStream();
    await ensureVideoLandmarker();
    if (el.video.src) URL.revokeObjectURL(el.video.src);
    el.video.src = URL.createObjectURL(file);
    await waitForMetadata(el.video);
    resetSource('video');
    state.mirror = false;
    setSourceSize(el.video.videoWidth, el.video.videoHeight);
    if (state.playing && !(await playVideo())) return;
    setStatus('Video cargado ✓ — transfiriendo movimiento');
  } catch (err) {
    console.error(err);
    setStatus(`Error con el video: ${err.message}`, 'error');
  }
}

async function startWebcam() {
  try {
    if (!navigator.mediaDevices?.getUserMedia) throw new Error('este navegador no permite usar la cámara aquí.');
    stopStream();
    state.stream = await navigator.mediaDevices.getUserMedia({
      video: { facingMode: 'user', width: { ideal: 1280 }, height: { ideal: 720 } },
      audio: false,
    });
    await ensureVideoLandmarker();
    if (el.video.src) {
      URL.revokeObjectURL(el.video.src);
      el.video.removeAttribute('src');
    }
    el.video.srcObject = state.stream;
    await waitForMetadata(el.video);
    resetSource('webcam');
    state.mirror = true;
    setSourceSize(el.video.videoWidth, el.video.videoHeight);
    if (!(await playVideo())) return;
    setStatus('Cámara activa ✓ — ¡muévete!');
  } catch (err) {
    console.error(err);
    setStatus(`No se pudo usar la cámara: ${err.message}`, 'error');
  }
}

// Copia el fotograma nuevo del video al lienzo de trabajo. Devuelve false si no hay fotograma nuevo.
function grabFrame() {
  const v = el.video;
  if (v.readyState < 2 || v.currentTime === state.lastVideoTime) return false;
  // El video volvió a empezar (bucle o salto): se trata como un cambio de plano.
  if (v.currentTime < state.lastVideoTime) onCut();
  state.lastVideoTime = v.currentTime;
  const { w, h } = state.srcSize;
  frameCtx.save();
  if (state.mirror) {
    frameCtx.translate(w, 0);
    frameCtx.scale(-1, 1);
  }
  frameCtx.drawImage(v, 0, 0, w, h);
  frameCtx.restore();
  return true;
}

const jointVec = new Float32Array(N * 2);

function detectFrame(now) {
  const { w, h } = state.srcSize;
  const t = now / 1000;
  if (state.cuts.check(frameCanvas, t)) onCut();

  // Cuerpo
  const res = state.landmarker.detectForVideo(frameCanvas, now);
  const lm = res.landmarks?.[0];
  if (lm) {
    const raw = fromLandmarks(lm, w, h);
    raw.forEach((p, i) => { jointVec[i * 2] = p.x; jointVec[i * 2 + 1] = p.y; });
    const f = state.jointFilter.filter(jointVec, t);
    state.src = raw.map((p, i) => ({ x: f[i * 2], y: f[i * 2 + 1], v: p.v }));
    state.poseLost = 0;
  } else if (state.src && ++state.poseLost > LOST_LIMIT) {
    state.src.forEach((p) => { p.v = 0; });
  }

  // Cara (solo si el personaje tiene cara que animar)
  if (!state.target?.face || !el.animateFace.checked) return;
  const fr = state.faceLandmarker.detectForVideo(frameCanvas, now);
  const flm = fr.faceLandmarks?.[0];
  if (!flm) {
    if (state.face) state.face.lost++;
    return;
  }
  state.face ??= { vec: new Float32Array(flm.length * 2), lm: flm.map(() => ({ x: 0, y: 0, z: 0 })), lost: 0 };
  const F = state.face;
  flm.forEach((p, i) => { F.vec[i * 2] = p.x * w; F.vec[i * 2 + 1] = p.y * h; });
  const f = state.faceFilter.filter(F.vec, t);
  flm.forEach((p, i) => { F.lm[i].x = f[i * 2]; F.lm[i].y = f[i * 2 + 1]; F.lm[i].z = p.z * w; });
  const cats = fr.faceBlendshapes?.[0]?.categories;
  F.blend = cats ? Object.fromEntries(cats.map((c) => [c.categoryName, c.score])) : null;
  F.lost = 0;
  state.target.face.driver.update(F.lm, F.blend);
  renderer.updateVideoTexture(frameCanvas);
}

function drawSource() {
  const { w, h } = state.srcSize;
  if (el.srcCanvas.width !== w || el.srcCanvas.height !== h) {
    el.srcCanvas.width = w;
    el.srcCanvas.height = h;
  }
  if (state.source === 'demo') {
    srcCtx.fillStyle = '#10131a';
    srcCtx.fillRect(0, 0, w, h);
    srcCtx.strokeStyle = '#1f2430';
    for (let x = 0; x < w; x += 40) { srcCtx.beginPath(); srcCtx.moveTo(x, 0); srcCtx.lineTo(x, h); srcCtx.stroke(); }
    for (let y = 0; y < h; y += 40) { srcCtx.beginPath(); srcCtx.moveTo(0, y); srcCtx.lineTo(w, y); srcCtx.stroke(); }
  } else {
    srcCtx.drawImage(frameCanvas, 0, 0);
  }
  if (state.src) drawSkeleton(srcCtx, state.src, { radius: Math.max(3, w / 180) });
  if (faceActive()) {
    srcCtx.fillStyle = '#7cf3c6';
    const r = Math.max(1.5, w / 400);
    for (const i of FACE_DOTS) {
      const p = state.face.lm[i];
      srcCtx.beginPath();
      srcCtx.arc(p.x, p.y, r, 0, Math.PI * 2);
      srcCtx.fill();
    }
  }
}

// ---------- Resultado ----------

function hexToRgb(hex) {
  const n = parseInt(hex.slice(1), 16);
  return [((n >> 16) & 255) / 255, ((n >> 8) & 255) / 255, (n & 255) / 255, 1];
}

const faceActive = () =>
  el.animateFace.checked && state.source !== 'demo' && state.target?.face && state.face && state.face.lost < LOST_LIMIT;

// Articulaciones "no visibles" para cuando la fuente no tiene cuerpo (p. ej. solo la cara).
const NO_BODY = Array.from({ length: N }, () => ({ x: 0, y: 0, v: 0 }));

function drawResult(dt) {
  const t = state.target;
  const src = state.src ?? (state.source !== 'demo' ? NO_BODY : null);
  const face = t.face;
  const faceOn = faceActive();
  let posed = t.rest;
  if (src) {
    if (!state.srcRef && src[J.pelvis].v >= VIS && src[J.chest].v >= VIS) {
      state.srcRef = { x: src[J.pelvis].x, y: src[J.pelvis].y, torso: dist(src[J.pelvis], src[J.chest]) || 1 };
    }
    let root = { ...t.rest[J.pelvis] };
    if (!autoFraming() && el.followRoot.checked && state.srcRef && src[J.pelvis].v >= VIS) {
      const k = t.info.torso / state.srcRef.torso;
      // Limitado para que el personaje no se salga del cuadro.
      const clamp = (v, m) => Math.max(-m, Math.min(m, v));
      root = {
        x: root.x + clamp((src[J.pelvis].x - state.srcRef.x) * k, t.padX * 0.7),
        y: root.y + clamp((src[J.pelvis].y - state.srcRef.y) * k, t.padY * 0.5),
        v: 1,
      };
    }
    // Con la cara visible, la inclinación de la cabeza sale de la línea de los ojos (sirve en primeros planos).
    const angles = faceOn
      ? { [J.head]: t.info.ang[J.head] + wrap(face.driver.eyeAngle() - face.rig.eyeAngle) }
      : null;
    posed = retarget(t.rest, t.info, src, root, angles);
  }
  state.posed = posed;
  boneTransforms(t.rest, posed, bones);

  // Cara: gestos en el espacio del personaje y luego el movimiento rígido de la cabeza.
  let faceDraw = null, mouthDraw = null;
  if (face) {
    if (faceOn && face.driver.ready) face.driver.computeTargets(face.targets);
    else face.targets.set(face.rig.rest);
    const k = J.head * 4, c = bones[k], sn = bones[k + 1], tx = bones[k + 2], ty = bones[k + 3];
    const T = face.targets, P = face.pos;
    for (let i = 0; i < face.rig.n; i++) {
      const x = T[i * 2], y = T[i * 2 + 1];
      P[i * 2] = c * x - sn * y + tx;
      P[i * 2 + 1] = sn * x + c * y + ty;
    }
    faceDraw = { positions: P };
    if (faceOn && face.driver.ready) mouthDraw = buildMouth(face);
  }

  updateView(src, posed, faceOn, dt);
  const bg = el.transparent.checked ? null : hexToRgb(el.bgColor.value);
  renderer.render({ bones, view: state.view, bg, wire: el.showWire.checked, face: faceDraw, mouth: mouthDraw });

  overlayCtx.clearRect(0, 0, el.overlay.width, el.overlay.height);
  if (el.showSkel.checked) {
    const v = state.view;
    drawSkeleton(overlayCtx, posed, { ox: v.ox, oy: v.oy, scale: v.scale, radius: Math.max(4, el.overlay.width / 180) });
  }
}

// Interior de la boca: el de la persona del video (dientes, lengua), deformado a la boca del personaje.
function buildMouth(face) {
  const lip = face.rig.innerLip, n = lip.length;
  const src = face.driver.sourceInnerLip();
  const P = face.pos, out = face.mouthPos, uv = face.mouthUv;
  let tcx = 0, tcy = 0, scx = 0, scy = 0;
  for (let i = 0; i < n; i++) {
    tcx += P[lip[i] * 2]; tcy += P[lip[i] * 2 + 1];
    scx += src[i * 2]; scy += src[i * 2 + 1];
  }
  tcx /= n; tcy /= n; scx /= n; scy /= n;
  // Un poco más grande que el hueco: los labios (dibujados encima) tapan el borde.
  const E = 1.12, { w, h } = state.srcSize;
  const tp = (i) => [tcx + (P[lip[i] * 2] - tcx) * E, tcy + (P[lip[i] * 2 + 1] - tcy) * E];
  const sp = (i) => [(scx + (src[i * 2] - scx) * E) / w, (scy + (src[i * 2 + 1] - scy) * E) / h];
  for (let i = 0; i < n; i++) {
    const j = (i + 1) % n, o = i * 6;
    const [ax, ay] = tp(i), [bx, by] = tp(j), [au, av] = sp(i), [bu, bv] = sp(j);
    out[o] = tcx; out[o + 1] = tcy; out[o + 2] = ax; out[o + 3] = ay; out[o + 4] = bx; out[o + 5] = by;
    uv[o] = scx / w; uv[o + 1] = scy / h; uv[o + 2] = au; uv[o + 3] = av; uv[o + 4] = bu; uv[o + 5] = bv;
  }
  return { positions: out, uvs: uv, mode: 1 };
}

// Cámara: en modo "Como el video" se ajusta para mostrar lo mismo que muestra el video.
function updateView(src, posed, faceOn, dt) {
  if (!autoFraming()) {
    state.view = fullView();
    return;
  }
  const pairs = [];
  if (src) {
    for (let i = 0; i < N; i++) {
      if (src[i].v < VIS) continue;
      const w = i <= J.rsh || i === J.lhip || i === J.rhip ? 1 : 0.4;
      pairs.push({ sx: src[i].x, sy: src[i].y, dx: posed[i].x, dy: posed[i].y, w });
    }
  }
  if (faceOn) {
    const P = state.target.face.pos;
    for (const i of FACE_FRAMING) {
      const p = state.face.lm[i];
      pairs.push({ sx: p.x, sy: p.y, dx: P[i * 2], dy: P[i * 2 + 1], w: 1.5 });
    }
  }
  const rect = state.camera.update(pairs, state.srcSize.w, state.srcSize.h, dt, state.snapCamera);
  state.snapCamera = false;
  state.view = rect ? fitView(rect, el.glCanvas.width, el.glCanvas.height) : fullView();
}

function frame(now) {
  const dt = Math.min(0.1, (now - state.lastTick) / 1000);
  state.lastTick = now;
  if (state.source === 'demo') {
    if (state.playing) state.t += dt;
    state.src = demoPose(state.t);
  } else if (state.playing && state.landmarker && grabFrame()) {
    try {
      detectFrame(now);
    } catch (err) {
      console.error(err);
    }
  }
  drawSource();
  if (state.target) drawResult(dt);
  requestAnimationFrame(frame);
}

// ---------- Grabación ----------

function toggleRecording() {
  if (state.recorder) {
    state.recorder.stop();
    return;
  }
  if (!window.MediaRecorder || !el.glCanvas.captureStream) {
    setStatus('Tu navegador no permite grabar el canvas.', 'error');
    return;
  }
  const mime = ['video/webm;codecs=vp9', 'video/webm;codecs=vp8', 'video/webm', 'video/mp4'].find((m) =>
    MediaRecorder.isTypeSupported(m),
  );
  const rec = new MediaRecorder(el.glCanvas.captureStream(30), {
    ...(mime && { mimeType: mime }),
    videoBitsPerSecond: 8_000_000,
  });
  const chunks = [];
  rec.ondataavailable = (e) => e.data.size && chunks.push(e.data);
  rec.onstop = () => {
    const type = rec.mimeType || 'video/webm';
    const blob = new Blob(chunks, { type });
    const a = document.createElement('a');
    a.href = URL.createObjectURL(blob);
    a.download = `transfer-motion.${type.includes('mp4') ? 'mp4' : 'webm'}`;
    a.click();
    setTimeout(() => URL.revokeObjectURL(a.href), 10_000);
    state.recorder = null;
    el.recBtn.textContent = '● Grabar';
    el.recBtn.classList.remove('active');
    setStatus('Video descargado ✓');
  };
  if (state.source === 'video') el.video.currentTime = 0;
  if (state.source === 'demo') state.t = 0;
  rec.start(250);
  state.recorder = rec;
  el.recBtn.textContent = '■ Detener y descargar';
  el.recBtn.classList.add('active');
  setStatus('Grabando…', 'busy');
}

// ---------- Eventos ----------

el.videoInput.addEventListener('change', () => {
  const f = el.videoInput.files[0];
  if (f) startVideo(f);
  el.videoInput.value = '';
});
el.imageInput.addEventListener('change', () => {
  const f = el.imageInput.files[0];
  if (f) loadCharacter(f);
  el.imageInput.value = '';
});
el.webcamBtn.addEventListener('click', startWebcam);
el.demoMotionBtn.addEventListener('click', startDemo);
el.demoCharBtn.addEventListener('click', () => {
  setTarget(DEMO.canvas, DEMO.rest, null);
  setStatus('Personaje de demostración');
});
el.cutout.addEventListener('change', () => state.target && rebuildTexture());
el.transparent.addEventListener('change', () => el.resultStage.classList.toggle('transparent', el.transparent.checked));
el.recalBtn.addEventListener('click', onCut);
el.smoothing.addEventListener('change', resetFilters);
el.framing.addEventListener('change', layout);
el.animateFace.addEventListener('change', () => {
  state.face = null;
  state.target?.face?.driver.reset();
});
el.playBtn.addEventListener('click', () => {
  state.playing = !state.playing;
  el.playBtn.textContent = state.playing ? '⏸ Pausar' : '▶ Reproducir';
  if (state.source !== 'demo') {
    if (state.playing) playVideo().then((ok) => ok && setStatus('Reproduciendo ✓'));
    else el.video.pause();
  }
});
el.recBtn.addEventListener('click', toggleRecording);
el.srcCanvas.addEventListener('click', () => {
  if (!state.needsTap || state.source === 'demo') return;
  state.playing = true;
  el.playBtn.textContent = '⏸ Pausar';
  playVideo().then((ok) => ok && setStatus('Reproduciendo ✓'));
});
window.addEventListener('resize', () => state.target && drawCharacter());

// Arranque: personaje y movimiento de demostración, sin necesidad de descargar nada.
setTarget(DEMO.canvas, DEMO.rest, null);
startDemo();
setStatus('Listo — sube un video y una imagen, o prueba la demo');
requestAnimationFrame(frame);
