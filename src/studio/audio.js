// Utilidades de audio del estudio (en el navegador, sin servidor): decodificar, mezclar,
// partir la voz en fragmentos, exportar WAV y grabar con el micrófono.

const Offline = globalThis.OfflineAudioContext || globalThis.webkitOfflineAudioContext;

export async function decode(arrayBuffer) {
  const ctx = new Offline(1, 1, 44100);
  return ctx.decodeAudioData(arrayBuffer);
}

const sleep = (ms) => new Promise((r) => setTimeout(r, ms));

// Descarga y decodifica un audio, reintentando los cortes de red (p. ej. al bloquear el iPhone).
export async function fetchAudio(url, { signal } = {}) {
  let bytes;
  for (let i = 0; ; i++) {
    if (signal?.aborted) throw new DOMException('Cancelado', 'AbortError');
    try {
      const r = await fetch(url, { signal });
      if (!r.ok) throw Object.assign(new Error(`No se pudo descargar el audio (${r.status}).`), { status: r.status });
      bytes = await r.arrayBuffer();
      break;
    } catch (e) {
      if (e?.name === 'AbortError' || e?.status || i >= 4) throw e;
      await sleep(1500 * (i + 1));
    }
  }
  return decode(bytes);
}

export const blobToAudio = async (blob) => decode(await blob.arrayBuffer());

// Mezcla pistas { buffer, gain = 1, offset = 0 } en un AudioBuffer nuevo (el navegador remuestrea).
export async function mix(tracks, { sampleRate = 44100, channels = 2, duration } = {}) {
  const len = duration ?? Math.max(...tracks.map((t) => (t.offset ?? 0) + t.buffer.duration));
  const ctx = new Offline(channels, Math.max(1, Math.ceil(len * sampleRate)), sampleRate);
  for (const t of tracks) {
    const src = ctx.createBufferSource();
    src.buffer = t.buffer;
    const g = ctx.createGain();
    g.gain.value = t.gain ?? 1;
    src.connect(g).connect(ctx.destination);
    src.start(t.offset ?? 0);
  }
  return ctx.startRendering();
}

// Mono a la frecuencia indicada (para subir la voz pesando poco).
export async function toMono(buffer, sampleRate = buffer.sampleRate) {
  const ctx = new Offline(1, Math.max(1, Math.ceil(buffer.duration * sampleRate)), sampleRate);
  const src = ctx.createBufferSource();
  src.buffer = buffer;
  src.connect(ctx.destination);
  src.start();
  return (await ctx.startRendering()).getChannelData(0);
}

// WAV PCM de 16 bits a partir de canales Float32Array.
export function encodeWav(channels, sampleRate) {
  const n = channels[0].length, ch = channels.length;
  const out = new DataView(new ArrayBuffer(44 + n * ch * 2));
  const str = (o, s) => { for (let i = 0; i < s.length; i++) out.setUint8(o + i, s.charCodeAt(i)); };
  str(0, 'RIFF'); out.setUint32(4, 36 + n * ch * 2, true); str(8, 'WAVE');
  str(12, 'fmt '); out.setUint32(16, 16, true); out.setUint16(20, 1, true); out.setUint16(22, ch, true);
  out.setUint32(24, sampleRate, true); out.setUint32(28, sampleRate * ch * 2, true);
  out.setUint16(32, ch * 2, true); out.setUint16(34, 16, true);
  str(36, 'data'); out.setUint32(40, n * ch * 2, true);
  let o = 44;
  for (let i = 0; i < n; i++) {
    for (let c = 0; c < ch; c++) {
      const v = Math.max(-1, Math.min(1, channels[c][i] || 0));
      out.setInt16(o, v < 0 ? v * 0x8000 : v * 0x7fff, true);
      o += 2;
    }
  }
  return new Blob([out.buffer], { type: 'audio/wav' });
}

export function bufferToWav(buffer) {
  const chans = [];
  for (let c = 0; c < buffer.numberOfChannels; c++) chans.push(buffer.getChannelData(c));
  return encodeWav(chans, buffer.sampleRate);
}

// Energía (RMS) en ventanas de `win` muestras.
export function rmsWindows(samples, win) {
  const n = Math.ceil(samples.length / win), out = new Float32Array(n);
  for (let w = 0; w < n; w++) {
    let s = 0;
    const a = w * win, b = Math.min(samples.length, a + win);
    for (let i = a; i < b; i++) s += samples[i] * samples[i];
    out[w] = Math.sqrt(s / Math.max(1, b - a));
  }
  return out;
}

// Parte una pista de voz en fragmentos de como mucho `maxLen` s, cortando en los momentos más
// silenciosos (entre frases). Marca como `silent` los fragmentos casi sin voz (no hace falta
// convertirlos). Devuelve [{ start, end, silent }] en segundos. Función pura.
export function findSegments(samples, sampleRate, { maxLen = 20, minLen = 6, silence = 0.01 } = {}) {
  const win = Math.round(sampleRate * 0.05);
  const rms = rmsWindows(samples, win);
  const wps = sampleRate / win; // ventanas por segundo
  const total = samples.length / sampleRate;
  const peak = rms.reduce((m, v) => Math.max(m, v), 0);
  const thr = Math.max(silence, peak * 0.04);
  const segs = [];
  let start = 0;
  while (total - start > maxLen) {
    // El punto más silencioso entre start+minLen y start+maxLen.
    const a = Math.floor((start + minLen) * wps), b = Math.min(rms.length - 1, Math.floor((start + maxLen) * wps));
    let best = b;
    for (let w = a; w <= b; w++) if (rms[w] < rms[best]) best = w;
    const cut = (best + 0.5) / wps;
    segs.push({ start, end: cut });
    start = cut;
  }
  segs.push({ start, end: total });
  for (const s of segs) {
    const a = Math.floor(s.start * wps), b = Math.max(a + 1, Math.ceil(s.end * wps));
    let voiced = 0;
    for (let w = a; w < b && w < rms.length; w++) if (rms[w] > thr) voiced++;
    s.silent = voiced / (b - a) < 0.03;
  }
  return segs;
}

// Copia un fragmento de una pista mono.
export const slice = (samples, sampleRate, start, end) =>
  samples.subarray(Math.floor(start * sampleRate), Math.min(samples.length, Math.ceil(end * sampleRate)));

// Coloca fragmentos convertidos ({ start, end, samples }) en una pista nueva de `length` muestras,
// cada uno en su sitio original (así no se desfasan aunque la IA cambie un poco su duración),
// con fundidos cortos en los bordes. Función pura.
export function placeSegments(length, sampleRate, parts, fade = 0.03) {
  const out = new Float32Array(length);
  const f = Math.max(1, Math.round(fade * sampleRate));
  for (const p of parts) {
    const a = Math.floor(p.start * sampleRate);
    const n = Math.min(p.samples.length, Math.ceil((p.end - p.start) * sampleRate), length - a);
    for (let i = 0; i < n; i++) {
      const g = Math.min(1, (i + 1) / f, (n - i) / f);
      out[a + i] += p.samples[i] * g;
    }
  }
  return out;
}

// Une audios uno tras otro con una pausa entre ellos.
export async function concat(buffers, { gap = 0.25, sampleRate = 44100 } = {}) {
  let t = 0;
  const tracks = buffers.map((b) => {
    const tr = { buffer: b, offset: t };
    t += b.duration + gap;
    return tr;
  });
  return mix(tracks, { sampleRate, channels: 1, duration: Math.max(0.1, t - gap) });
}

// Graba con el micrófono. Devuelve { stop(): Promise<Blob>, cancel() }.
// onLevel(0..1) recibe el volumen en vivo; se detiene sola a los maxSeconds.
export async function recordMic({ maxSeconds = 30, onLevel = () => {}, onTick = () => {} } = {}) {
  if (!navigator.mediaDevices?.getUserMedia || !window.MediaRecorder) {
    throw new Error('Este navegador no permite grabar audio.');
  }
  const stream = await navigator.mediaDevices.getUserMedia({
    audio: { echoCancellation: false, noiseSuppression: true, autoGainControl: true },
  });
  const mime = ['audio/webm;codecs=opus', 'audio/mp4', 'audio/webm', 'audio/ogg'].find((m) => MediaRecorder.isTypeSupported(m));
  const rec = new MediaRecorder(stream, mime ? { mimeType: mime } : undefined);
  const chunks = [];
  rec.ondataavailable = (e) => e.data.size && chunks.push(e.data);
  const AC = window.AudioContext || window.webkitAudioContext;
  const ac = new AC();
  const an = ac.createAnalyser();
  an.fftSize = 1024;
  ac.createMediaStreamSource(stream).connect(an);
  const buf = new Float32Array(an.fftSize);
  const t0 = performance.now();
  let raf = 0, timer = 0, done;
  const finished = new Promise((r) => { done = r; });
  const cleanup = () => {
    cancelAnimationFrame(raf);
    clearTimeout(timer);
    stream.getTracks().forEach((t) => t.stop());
    ac.close().catch(() => {});
  };
  rec.onstop = () => {
    cleanup();
    done(new Blob(chunks, { type: rec.mimeType || 'audio/webm' }));
  };
  const loop = () => {
    an.getFloatTimeDomainData(buf);
    let s = 0;
    for (const v of buf) s += v * v;
    onLevel(Math.min(1, Math.sqrt(s / buf.length) * 4));
    onTick((performance.now() - t0) / 1000);
    raf = requestAnimationFrame(loop);
  };
  rec.start(250);
  loop();
  timer = setTimeout(() => rec.state !== 'inactive' && rec.stop(), maxSeconds * 1000);
  return {
    stop() {
      if (rec.state !== 'inactive') rec.stop();
      return finished;
    },
    cancel() {
      rec.onstop = null;
      if (rec.state !== 'inactive') rec.stop();
      cleanup();
    },
  };
}
