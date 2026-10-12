import { J, VIS, fromLandmarks, restInfo, retarget, boneTransforms, drawSkeleton, dist } from './skeleton.js';
import { buildMesh } from './mesh.js';
import { Renderer } from './renderer.js';
import { demoPose, demoCharacter, DEMO_SIZE } from './demo.js';
import { getVideoLandmarker, getImageLandmarker } from './pose.js';

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
};

function setStatus(text, kind = '') {
  el.status.textContent = text;
  el.status.className = `status ${kind}`;
}

// ---------- Personaje ----------

const cloneJoints = (js) => js.map((p) => ({ x: p.x, y: p.y, v: 1 }));

function setTarget(base, rest, mask) {
  state.target = { base, rest: cloneJoints(rest), mask, w: base.width, h: base.height };
  state.srcRef = null;
  rebuildTexture();
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
  renderer.setTexture(c);
  rebuildMesh();
}

function rebuildMesh() {
  const t = state.target;
  t.info = restInfo(t.rest);
  renderer.setMesh(buildMesh(t.imageData, t.rest));
  t.pad = Math.round(0.22 * Math.max(t.w, t.h));
  const W = t.w + 2 * t.pad, H = t.h + 2 * t.pad;
  renderer.resize(W, H);
  el.overlay.width = W;
  el.overlay.height = H;
  el.charCanvas.width = t.w;
  el.charCanvas.height = t.h;
  drawCharacter();
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
    const s = Math.min(1, 900 / Math.max(img.naturalWidth, img.naturalHeight));
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
    if (res.landmarks?.[0]) {
      setTarget(base, fromLandmarks(res.landmarks[0], base.width, base.height), mask);
      setStatus('Personaje listo ✓ — ajusta los puntos si hace falta');
    } else {
      setTarget(base, templateRest(base.width, base.height), null);
      setStatus('No se detectó una persona: coloca los puntos del esqueleto a mano', 'error');
    }
  } catch (err) {
    console.error(err);
    setStatus(`Error al procesar la imagen: ${err.message}`, 'error');
  } finally {
    URL.revokeObjectURL(url);
  }
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
  state.srcRef = null;
  state.lastVideoTime = -1;
  el.webcamBtn.classList.toggle('active', type === 'webcam');
  el.demoMotionBtn.classList.toggle('active', type === 'demo');
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
  state.srcSize = { ...DEMO_SIZE };
  setStatus('Movimiento de demostración');
}

async function ensureVideoLandmarker() {
  if (!state.landmarker) {
    setStatus('Cargando el modelo de IA de pose…', 'busy');
    state.landmarker = await getVideoLandmarker();
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
    state.srcSize = { w: el.video.videoWidth, h: el.video.videoHeight };
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
    state.srcSize = { w: el.video.videoWidth, h: el.video.videoHeight };
    if (!(await playVideo())) return;
    setStatus('Cámara activa ✓ — ¡muévete!');
  } catch (err) {
    console.error(err);
    setStatus(`No se pudo usar la cámara: ${err.message}`, 'error');
  }
}

function detectFrame(now) {
  const v = el.video;
  if (!state.landmarker || v.readyState < 2 || v.currentTime === state.lastVideoTime) return null;
  state.lastVideoTime = v.currentTime;
  const res = state.landmarker.detectForVideo(v, now);
  const lm = res.landmarks?.[0];
  return lm ? fromLandmarks(lm, state.srcSize.w, state.srcSize.h, state.mirror) : null;
}

function smoothInto(raw) {
  const a = Math.max(0.05, 1 - parseFloat(el.smoothing.value));
  if (!state.src) {
    state.src = raw.map((p) => ({ ...p }));
    return;
  }
  raw.forEach((r, i) => {
    const s = state.src[i];
    if (r.v >= VIS) {
      const k = s.v >= VIS ? a : 1;
      s.x += (r.x - s.x) * k;
      s.y += (r.y - s.y) * k;
    }
    s.v = r.v;
  });
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
    srcCtx.save();
    if (state.mirror) {
      srcCtx.translate(w, 0);
      srcCtx.scale(-1, 1);
    }
    srcCtx.drawImage(el.video, 0, 0, w, h);
    srcCtx.restore();
  }
  if (state.src) drawSkeleton(srcCtx, state.src, { radius: Math.max(4, w / 160) });
}

// ---------- Resultado ----------

function hexToRgb(hex) {
  const n = parseInt(hex.slice(1), 16);
  return [((n >> 16) & 255) / 255, ((n >> 8) & 255) / 255, (n & 255) / 255, 1];
}

function drawResult() {
  const t = state.target;
  let posed = t.rest;
  const src = state.src;
  if (src) {
    if (!state.srcRef && src[J.pelvis].v >= VIS && src[J.chest].v >= VIS) {
      state.srcRef = { x: src[J.pelvis].x, y: src[J.pelvis].y, torso: dist(src[J.pelvis], src[J.chest]) || 1 };
    }
    let root = { ...t.rest[J.pelvis] };
    if (el.followRoot.checked && state.srcRef && src[J.pelvis].v >= VIS) {
      const k = t.info.torso / state.srcRef.torso;
      root = { x: root.x + (src[J.pelvis].x - state.srcRef.x) * k, y: root.y + (src[J.pelvis].y - state.srcRef.y) * k, v: 1 };
    }
    posed = retarget(t.rest, t.info, src, root);
  }
  state.posed = posed;
  boneTransforms(t.rest, posed, bones);
  const bg = el.transparent.checked ? null : hexToRgb(el.bgColor.value);
  renderer.render(bones, [t.pad, t.pad], bg, el.showWire.checked);

  overlayCtx.clearRect(0, 0, el.overlay.width, el.overlay.height);
  if (el.showSkel.checked) {
    drawSkeleton(overlayCtx, posed, { ox: t.pad, oy: t.pad, radius: Math.max(4, el.overlay.width / 180) });
  }
}

function frame(now) {
  const dt = Math.min(0.1, (now - state.lastTick) / 1000);
  state.lastTick = now;
  let raw = null;
  if (state.source === 'demo') {
    if (state.playing) state.t += dt;
    raw = demoPose(state.t);
  } else if (state.playing) {
    try {
      raw = detectFrame(now);
    } catch (err) {
      console.error(err);
    }
  }
  if (raw) smoothInto(raw);
  drawSource();
  if (state.target) drawResult();
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
el.recalBtn.addEventListener('click', () => {
  state.srcRef = null;
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
