import { falClient, upload, runJob, resumeJob, jobStore, serverStatus, explainError, findUrl, aborted } from '../fal.js';
import { fetchAudio, blobToAudio, mix, toMono, encodeWav, bufferToWav, findSegments, slice, placeSegments, concat, recordMic } from './audio.js';

// Estudio de voz y música:
//  1. Tu voz: una muestra de 10–30 s (grabada leyendo la frase de consentimiento, o subida).
//  2. Hablar con tu voz: Chatterbox multilingüe con tu muestra como referencia.
//  3. Cover: Demucs separa voz y música, Chatterbox HD cambia la voz por la tuya y se mezcla aquí.
//  4. Crear canción: MiniMax Music 2 (tu letra), Sonauto v2 (letra de la IA) o ACE-Step (instrumental).

const $ = (id) => document.getElementById(id);
const M = {
  tts: 'fal-ai/chatterbox/text-to-speech/multilingual',
  demucs: 'fal-ai/demucs',
  vc: 'resemble-ai/chatterboxhd/speech-to-speech',
  minimax: 'fal-ai/minimax-music/v2',
  sonauto: 'sonauto/v2/text-to-music',
  ace: 'fal-ai/ace-step',
};
// Precios aproximados (publicados en fal.ai o por terceros); el real lo marca fal.ai.
const PRICE = { ttsChar: 0.025 / 1000, demucsSec: 0.0007, minimax: 0.03, aceSec: 0.0002 };
const MUSIC_JOB = 'tm-studio-music';
const AUDIO_EXT = ['mp3', 'wav', 'flac', 'ogg', 'm4a'];

const STYLES = [
  ['Pop', 'pop, catchy, modern production'],
  ['Reguetón', 'reggaeton, dembow rhythm, latin urban'],
  ['Bachata', 'bachata, romantic guitar, latin'],
  ['Salsa', 'salsa, brass section, latin percussion'],
  ['Cumbia', 'cumbia, accordion, latin groove'],
  ['Corridos', 'regional mexican corridos, acoustic guitars'],
  ['Mariachi', 'mariachi, trumpets, violins, ranchera'],
  ['Balada', 'romantic ballad, piano, strings'],
  ['Rock', 'rock, electric guitars, live drums'],
  ['Trap', 'trap, 808 bass, hi-hats'],
  ['R&B', 'r&b, smooth, soulful'],
  ['Lo-fi', 'lo-fi hip hop, chill, warm vinyl'],
  ['Electrónica', 'electronic dance music, synths, four on the floor'],
  ['Jazz', 'jazz, swing, saxophone'],
  ['Bossa nova', 'bossa nova, nylon guitar, soft'],
  ['Country', 'country, acoustic guitar, banjo'],
  ['K-pop', 'k-pop, energetic, polished'],
  ['Gospel', 'gospel, choir, organ'],
  ['Metal', 'heavy metal, distorted guitars, powerful drums'],
  ['Orquestal', 'orchestral, cinematic, strings and brass'],
];

const state = {
  server: null,
  voice: null, // { wav: Blob, url?: string (fal) }
  song: null, // { file, name, duration, url?, sep? } — sep guarda la separación ya pagada
  cover: null, // resultado publicado: { inst, vocals, url }
  style: 0,
  music: null,
  busy: false,
  abort: null,
};

// ---------- utilidades ----------

const storage = {
  get: (k) => { try { return localStorage.getItem(k) ?? ''; } catch { return ''; } },
  set: (k, v) => { try { localStorage.setItem(k, v); } catch { /* sin almacenamiento */ } },
};

// IndexedDB para guardar tu muestra de voz entre visitas (solo en este dispositivo).
const idb = {
  open() {
    return new Promise((res, rej) => {
      const r = indexedDB.open('tm-studio', 1);
      r.onupgradeneeded = () => r.result.createObjectStore('kv');
      r.onsuccess = () => res(r.result);
      r.onerror = () => rej(r.error);
    });
  },
  async run(mode, fn) {
    const db = await this.open();
    return new Promise((res, rej) => {
      const tx = db.transaction('kv', mode);
      const req = fn(tx.objectStore('kv'));
      tx.oncomplete = () => res(req?.result);
      tx.onerror = () => rej(tx.error);
      tx.onabort = () => rej(tx.error);
    });
  },
  get: (k) => idb.run('readonly', (s) => s.get(k)).catch(() => null),
  set: (k, v) => idb.run('readwrite', (s) => s.put(v, k)).then(() => true).catch(() => false),
  del: (k) => idb.run('readwrite', (s) => s.delete(k)).then(() => true).catch(() => false),
};

const usd = (v) => `$${v < 0.01 ? v.toFixed(3) : v.toFixed(2)} USD`;
const mmss = (s) => `${Math.floor(s / 60)}:${String(Math.round(s % 60)).padStart(2, '0')}`;

function setStatus(id, text, error = false) {
  const el = $(id);
  el.textContent = text;
  el.classList.toggle('error', error);
}

// URL de objeto que se libera al reemplazarla (evita acumular cientos de MB en el móvil).
const urls = {};
function ownUrl(key, blob) {
  if (urls[key]) URL.revokeObjectURL(urls[key]);
  urls[key] = blob ? URL.createObjectURL(blob) : null;
  return urls[key];
}

// Copia local (mismo origen) de un archivo remoto para que «Descargar» lo guarde de verdad.
async function localCopy(url) {
  const r = await fetch(url);
  if (!r.ok) throw new Error(`Error ${r.status}`);
  return r.blob();
}

function makeBuffer(samples, sampleRate) {
  const b = new AudioBuffer({ length: Math.max(1, samples.length), numberOfChannels: 1, sampleRate });
  b.copyToChannel(samples, 0);
  return b;
}

// Reparte el trabajo en n procesos; al primer error deja de empezar trabajos nuevos.
async function pool(items, n, fn) {
  const out = new Array(items.length);
  let next = 0, failed = false;
  const worker = async () => {
    while (!failed && next < items.length) {
      const i = next++;
      try {
        out[i] = await fn(items[i], i);
      } catch (e) {
        failed = true;
        throw e;
      }
    }
  };
  await Promise.all(Array.from({ length: Math.min(n, items.length) }, worker));
  return out;
}

// Ejecuta una tarea de IA con contraseña, confirmación de costo, cancelación y mensajes de error.
// Al terminar (bien, mal o cancelada) se aborta su señal: si queda algún trabajo en fal.ai, se cancela.
async function task({ statusId, cancelId, confirmText, run }) {
  if (state.busy) return;
  const password = $('password').value;
  if (!state.server?.configured) return setStatus(statusId, 'El servidor no está configurado (mira el aviso de arriba).', true);
  if (!password) {
    $('password').focus();
    return setStatus(statusId, 'Escribe la contraseña de la app (TM_PASSWORD).', true);
  }
  if (confirmText && !window.confirm(confirmText)) return;
  storage.set('tm-ai-password', password);
  setStatus(statusId, 'Empezando…');
  const ac = new AbortController();
  state.busy = true;
  state.abort = ac;
  if (cancelId) $(cancelId).hidden = false;
  updateButtons();
  try {
    await run({
      fal: falClient(password),
      signal: ac.signal,
      // Tras cancelar o fallar, los procesos que aún terminan no pisan el mensaje final.
      status: (t) => { if (!ac.signal.aborted) setStatus(statusId, t); },
    });
  } catch (err) {
    console.error(err);
    const msg = err?.name === 'AbortError'
      ? 'Cancelado. Lo que la IA ya procesó puede cobrarse.'
      : `No se pudo completar: ${explainError(err)}`;
    ac.abort();
    setStatus(statusId, msg + (err?.hint ? ` ${err.hint}` : ''), true);
  } finally {
    ac.abort();
    state.busy = false;
    state.abort = null;
    if (cancelId) $(cancelId).hidden = true;
    updateButtons();
  }
}

function cancelTask(statusId) {
  if (!state.abort) return;
  state.abort.abort();
  setStatus(statusId, 'Cancelando…');
}

// Sube la muestra de voz una vez por visita.
async function voiceUrl(fal, signal) {
  if (!state.voice) throw new Error('Primero graba o sube tu voz (paso 1).');
  state.voice.url ??= await upload(fal, state.voice.wav, { signal });
  return state.voice.url;
}

// ---------- 1. Tu voz ----------

function showVoice(wav, text) {
  $('voicePlayer').src = ownUrl('voice', wav);
  $('voicePlayer').hidden = false;
  $('voiceBadge').hidden = false;
  $('voiceForget').hidden = false;
  setStatus('voiceStatus', text);
}

async function setVoice(blob, source) {
  setStatus('voiceStatus', 'Preparando la muestra…');
  let buffer;
  try {
    buffer = await blobToAudio(blob);
  } catch {
    return setStatus('voiceStatus', 'No se pudo leer ese audio. Prueba con otro archivo (mp3, m4a, wav).', true);
  }
  if (buffer.duration < 8) return setStatus('voiceStatus', `La muestra dura ${buffer.duration.toFixed(1)} s: necesitas al menos 10 s.`, true);
  // Mono 24 kHz y como mucho 30 s: pesa poco y es lo que usan los modelos de voz.
  const samples = await toMono(buffer, 24000);
  const wav = encodeWav([samples.subarray(0, 30 * 24000)], 24000);
  state.voice = { wav };
  const secs = Math.min(30, buffer.duration).toFixed(0);
  showVoice(wav, `Voz lista (${secs} s, ${source}).`);
  updateButtons();
  const saved = await idb.set('voice', { wav, source, date: Date.now() });
  if (state.voice?.wav === wav) {
    setStatus('voiceStatus', saved
      ? `Voz lista y guardada en este dispositivo (${secs} s, ${source}).`
      : `Voz lista (${secs} s, ${source}). Este navegador no deja guardarla: tendrás que grabarla otra vez la próxima visita.`);
  }
}

let recording = null;
$('recBtn').addEventListener('click', async () => {
  if (recording) {
    const take = recording;
    recording = null;
    const blob = await take.stop();
    $('recBtn').textContent = '● Grabar mi voz';
    $('recBtn').classList.remove('recording');
    $('recLevel').style.width = '0';
    return setVoice(blob, 'grabada');
  }
  try {
    const take = await recordMic({
      maxSeconds: 30,
      onLevel: (v) => { $('recLevel').style.width = `${Math.round(v * 100)}%`; },
      onTick: (s) => { $('recInfo').textContent = `${s.toFixed(0)} / 30 s${s < 10 ? ' (mínimo 10 s)' : ''}`; },
    });
    recording = take;
    $('recBtn').textContent = '■ Terminar';
    $('recBtn').classList.add('recording');
    setStatus('voiceStatus', 'Grabando… lee la frase y sigue hablando con naturalidad.');
    // Se detiene sola a los 30 s (solo esta toma, no una posterior).
    setTimeout(() => { if (recording === take) $('recBtn').click(); }, 30_500);
  } catch (err) {
    recording = null;
    setStatus('voiceStatus', `No se pudo usar el micrófono: ${err.message}`, true);
  }
});

const needConsent = () => {
  if ($('voiceConsent').checked) return false;
  setStatus('voiceStatus', 'Primero marca la casilla: solo puedes usar tu voz o la de alguien que te dé permiso.', true);
  return true;
};
// Se comprueba antes de abrir el selector de archivos (y otra vez al elegir, por si acaso).
$('voiceInput').addEventListener('click', (e) => { if (needConsent()) e.preventDefault(); });
$('voiceInput').addEventListener('change', () => {
  const f = $('voiceInput').files[0];
  $('voiceInput').value = '';
  if (f && !needConsent()) setVoice(f, 'subida');
});
$('voiceForget').addEventListener('click', async () => {
  state.voice = null;
  await idb.del('voice');
  ownUrl('voice', null);
  $('voicePlayer').hidden = true;
  $('voiceBadge').hidden = true;
  $('voiceForget').hidden = true;
  setStatus('voiceStatus', 'Voz borrada de este dispositivo.');
  updateButtons();
});

// ---------- 2. Hablar con tu voz ----------

// Trozos de ≤ 280 caracteres cortando en finales de frase (el modelo admite 300).
function chunkText(text, max = 280) {
  const parts = text.replace(/\s+/g, ' ').trim().match(/[^.!?…\n]+[.!?…]*\s*/g) ?? [];
  const out = [];
  let cur = '';
  for (let p of parts) {
    while (p.length > max) {
      const cut = p.lastIndexOf(' ', max) > max / 2 ? p.lastIndexOf(' ', max) : max;
      out.push(p.slice(0, cut).trim());
      p = p.slice(cut);
    }
    if ((cur + p).length > max) { if (cur.trim()) out.push(cur.trim()); cur = ''; }
    cur += p;
  }
  if (cur.trim()) out.push(cur.trim());
  return out.filter((c) => /[\p{L}\p{N}]/u.test(c));
}

function updateTtsInfo() {
  const n = $('ttsText').value.trim().length;
  $('ttsInfo').textContent = n ? `${n} caracteres · costo aproximado: ${usd(n * PRICE.ttsChar)}` : '';
}

$('ttsBtn').addEventListener('click', () => {
  const text = $('ttsText').value.trim();
  if (!text) return setStatus('ttsStatus', 'Escribe un texto.', true);
  if (!state.voice) return setStatus('ttsStatus', 'Primero graba o sube tu voz (paso 1).', true);
  const chunks = chunkText(text);
  if (!chunks.length) return setStatus('ttsStatus', 'Escribe un texto con palabras, no solo signos.', true);
  task({
    statusId: 'ttsStatus',
    cancelId: 'ttsCancel',
    confirmText: `Se generará el audio con tu voz en fal.ai (unos ${usd(text.length * PRICE.ttsChar)}). ¿Continuar?`,
    run: async ({ fal, signal, status }) => {
      status('Subiendo tu voz…');
      const voice = await voiceUrl(fal, signal);
      const buffers = [];
      for (const [i, chunk] of chunks.entries()) {
        status(`Generando ${i + 1}/${chunks.length}…`);
        const data = await runJob(fal, M.tts, {
          text: chunk,
          voice,
          custom_audio_language: $('ttsLang').value,
          exaggeration: Number($('ttsExpr').value),
        }, { signal, onStatus: (t) => status(`${i + 1}/${chunks.length} · ${t}`), label: 'Generando' });
        const url = data?.audio?.url ?? findUrl(data, AUDIO_EXT);
        if (!url) throw new Error('La IA no devolvió audio.');
        buffers.push(await fetchAudio(url, { signal }));
      }
      const out = await concat(buffers, { gap: 0.3, sampleRate: buffers[0].sampleRate });
      const url = ownUrl('tts', bufferToWav(out));
      $('ttsResult').hidden = false;
      $('ttsResult').querySelector('audio').src = url;
      $('ttsResult').querySelector('a').href = url;
      status('¡Listo! ✓');
    },
  });
});
$('ttsCancel').addEventListener('click', () => cancelTask('ttsStatus'));

// ---------- 3. Cover ----------

async function setSong(blob, name) {
  setStatus('coverStatus', 'Leyendo la canción…');
  try {
    const buf = await blobToAudio(blob);
    state.song = { file: blob, name, duration: buf.duration };
    $('songName').textContent = `${name} · ${mmss(buf.duration)}`;
    setStatus('coverStatus', buf.duration > 360 ? 'La canción dura más de 6 min: recórtala para que funcione bien en el móvil.' : '');
  } catch {
    state.song = null;
    $('songName').textContent = '';
    setStatus('coverStatus', 'No se pudo leer ese archivo. Prueba con mp3, m4a o wav.', true);
  }
  updateButtons();
}

// Fragmentos de voz previstos (se corta en silencios, así que suelen salir de unos 15 s).
function frags(duration) {
  const n = Math.max(1, Math.ceil(duration / 15));
  return n === 1 ? '1 fragmento' : `unos ${n} fragmentos`;
}

function updateCoverInfo() {
  const s = state.song;
  if (!s) return void ($('coverInfo').textContent = '');
  const sep = s.sep ? 'separación ya hecha (gratis)' : `separar ~${usd(s.duration * PRICE.demucsSec)}`;
  $('coverInfo').textContent = $('karaoke').checked
    ? `${mmss(s.duration)} · ${sep}`
    : `${mmss(s.duration)} · ${sep} + cambiar la voz (${frags(s.duration)}, sin estimación: tarifa de fal.ai)`;
}

$('songInput').addEventListener('change', () => {
  const f = $('songInput').files[0];
  $('songInput').value = '';
  if (f) setSong(f, f.name);
});

// Mezcla el resultado publicado con el volumen de voz actual, sin reiniciar la reproducción.
async function remixCover() {
  const c = state.cover;
  if (!c) return;
  const tracks = [{ buffer: c.inst }];
  if (c.vocals) tracks.push({ buffer: c.vocals, gain: Number($('vocalGain').value) });
  const out = await mix(tracks, { sampleRate: c.inst.sampleRate, channels: 2, duration: c.inst.duration });
  if (state.cover !== c) return;
  const player = $('coverResult').querySelector('audio');
  const t = player.currentTime, playing = !player.paused;
  c.url = ownUrl('cover', bufferToWav(out));
  player.src = c.url;
  if (t) player.currentTime = t;
  if (playing) player.play().catch(() => {});
  $('coverResult').hidden = false;
  $('coverResult').querySelector('[data-dl="cover"]').href = c.url;
  // Instrumental y voz: el WAV se crea al pulsar (ver el manejador de clics de abajo).
  $('coverResult').querySelectorAll('[data-dl="inst"], [data-dl="vocals"]').forEach((a) => { a.href = '#'; });
  $('coverResult').querySelector('[data-dl="vocals"]').hidden = !(c.vocals || c.origVocals);
}

// Instrumental y voz se convierten en WAV solo al pulsar «Descargar» (ahorra mucha memoria).
$('coverResult').addEventListener('click', (e) => {
  const a = e.target.closest('a[data-dl]');
  if (!a || a.dataset.dl === 'cover' || !state.cover) return;
  // «Voz sola»: tu voz convertida o, en karaoke, la voz original separada.
  const buf = a.dataset.dl === 'inst' ? state.cover.inst : state.cover.vocals ?? state.cover.origVocals;
  if (buf) a.href = ownUrl(`dl-${a.dataset.dl}`, bufferToWav(buf));
});

// Suma pistas una a una sobre la primera (sin tener todas a la vez en memoria).
async function sumStems(urls, signal) {
  let acc = null;
  for (const url of urls) {
    if (!url) continue;
    const b = await fetchAudio(url, { signal });
    if (!acc) { acc = b; continue; }
    for (let c = 0; c < acc.numberOfChannels; c++) {
      const dst = acc.getChannelData(c), src = b.getChannelData(Math.min(c, b.numberOfChannels - 1));
      for (let i = 0, n = Math.min(dst.length, src.length); i < n; i++) dst[i] += src[i];
    }
  }
  return acc;
}

async function separate(fal, song, { signal, status }) {
  if (song.sep) return song.sep;
  status('Subiendo la canción…');
  song.url ??= await upload(fal, song.file, { signal });
  const stems = await runJob(fal, M.demucs, {
    audio_url: song.url, model: 'htdemucs', stems: ['vocals', 'drums', 'bass', 'other'], output_format: 'mp3',
  }, { signal, onStatus: status, label: 'Separando voz y música' });
  status('Descargando las pistas…');
  const inst = await sumStems(['drums', 'bass', 'other'].map((k) => stems?.[k]?.url), signal);
  const vocals = stems?.vocals?.url ? await fetchAudio(stems.vocals.url, { signal }) : null;
  if (!vocals || !inst) throw new Error('La separación no devolvió las pistas esperadas.');
  // Se guarda: si luego falla el cambio de voz, reintentar no vuelve a cobrar la separación.
  song.sep = { inst, vocals };
  return song.sep;
}

async function runCover() {
  const karaoke = $('karaoke').checked;
  if (!state.song) return setStatus('coverStatus', 'Sube una canción.', true);
  if (!karaoke && !state.voice) return setStatus('coverStatus', 'Primero graba o sube tu voz (paso 1), o marca «Solo separar».', true);
  const song = state.song;
  await task({
    statusId: 'coverStatus',
    cancelId: 'coverCancel',
    confirmText: `Se procesará «${song.name}» en fal.ai (${$('coverInfo').textContent}). ¿Continuar?`,
    run: async ({ fal, signal, status }) => {
      const { inst, vocals } = await separate(fal, song, { signal, status });
      updateCoverInfo();
      if (karaoke) {
        state.cover = { inst, vocals: null, origVocals: vocals };
        await remixCover();
        return status('¡Listo! ✓ Instrumental separado.');
      }

      // Voz en fragmentos de ≤ 20 s cortados en silencios; los mudos no se convierten.
      const SR = 24000;
      const voice = await voiceUrl(fal, signal);
      const mono = await toMono(vocals, SR);
      const segs = findSegments(mono, SR, { maxLen: 20, minLen: 6 }).filter((s) => s.end - s.start > 0.3);
      const todo = segs.filter((s) => !s.silent);
      let done = 0;
      status(`Cambiando la voz: 0/${todo.length}…`);
      let converted;
      try {
        converted = await pool(todo, 3, async (seg) => {
          const wav = encodeWav([slice(mono, SR, seg.start, seg.end)], SR);
          const src = await upload(fal, wav, { signal });
          const data = await runJob(fal, M.vc, {
            // 24 kHz nativos: es la frecuencia con la que se coloca la voz.
            source_audio_url: src, target_voice_audio_url: voice, high_quality_audio: false,
          }, { signal, label: 'Cambiando la voz' });
          const url = data?.audio?.url ?? findUrl(data, AUDIO_EXT);
          if (!url) throw new Error('La IA no devolvió la voz convertida.');
          const out = await toMono(await fetchAudio(url, { signal }), SR);
          status(`Cambiando la voz: ${++done}/${todo.length}…`);
          return { ...seg, samples: out };
        });
      } catch (e) {
        e.hint = 'La separación ya está guardada: puedes reintentar sin pagarla otra vez, o marcar «Solo separar».';
        throw e;
      }
      if (signal.aborted) throw aborted();
      status('Mezclando…');
      state.cover = { inst, vocals: makeBuffer(placeSegments(mono.length, SR, converted), SR) };
      await remixCover();
      status('¡Listo! ✓ Ajusta el volumen de la voz si hace falta.');
    },
  });
}

$('coverBtn').addEventListener('click', runCover);
$('coverCancel').addEventListener('click', () => cancelTask('coverStatus'));
$('karaoke').addEventListener('change', updateCoverInfo);
let remixTimer = 0;
$('vocalGain').addEventListener('input', () => {
  clearTimeout(remixTimer);
  remixTimer = setTimeout(() => remixCover().catch(console.error), 300);
});

// ---------- 4. Crear canción ----------

STYLES.forEach(([name], i) => {
  const b = document.createElement('button');
  b.className = 'chip';
  b.type = 'button';
  b.setAttribute('role', 'radio');
  b.setAttribute('aria-checked', String(i === state.style));
  b.textContent = name;
  b.addEventListener('click', () => {
    state.style = i;
    document.querySelectorAll('#styles .chip').forEach((c, j) => c.setAttribute('aria-checked', String(j === i)));
  });
  $('styles').append(b);
});

function updateMusicMode() {
  const mode = $('musicMode').value;
  $('lyrics').hidden = mode !== 'lyrics';
  $('durField').hidden = mode !== 'inst';
  $('singer').disabled = mode === 'inst';
  const cost = mode === 'lyrics' ? `~${usd(PRICE.minimax)}` : mode === 'inst' ? `~${usd(PRICE.aceSec * Number($('duration').value))}` : 'sin estimación (tarifa de fal.ai)';
  $('musicInfo').textContent = `Costo aproximado: ${cost}`;
}

function musicPrompt(extra = []) {
  const parts = [STYLES[state.style][1], $('mood').value, $('musicMode').value !== 'inst' && $('singer').value, ...extra, $('musicDesc').value.trim()];
  return parts.filter(Boolean).join(', ').slice(0, 300);
}

async function showSong(data, { inst, words }) {
  const audio = Array.isArray(data?.audio) ? data.audio[0] : data?.audio;
  const url = audio?.url ?? findUrl(data, AUDIO_EXT);
  if (!url) throw new Error('La IA no devolvió la canción.');
  const ext = ((audio?.file_name ?? url).match(/\.(mp3|wav|flac|ogg|m4a)(?:$|[?#])/i)?.[1]
    ?? (/wav/i.test(audio?.content_type ?? '') ? 'wav' : 'mp3')).toLowerCase();
  state.music = { url, inst };
  const box = $('musicResult');
  box.hidden = false;
  box.querySelector('audio').src = url;
  const dl = box.querySelector('a[download]');
  dl.download = `cancion.${ext}`;
  // Hasta tener la copia local, el enlace abre el archivo en otra pestaña (no saca de la app).
  dl.href = url;
  $('singWithMe').hidden = inst;
  $('musicLyrics').hidden = !words;
  $('musicLyrics').textContent = words || '';
  localCopy(url).then((blob) => {
    if (state.music?.url !== url) return;
    state.music.blob = blob;
    dl.href = ownUrl('music', blob);
  }).catch(() => {});
}

function musicTask(run) {
  return task({
    statusId: 'musicStatus',
    cancelId: 'musicCancel',
    ...run,
  });
}

$('musicBtn').addEventListener('click', () => {
  const mode = $('musicMode').value;
  const lyrics = $('lyrics').value.trim();
  if (mode === 'lyrics' && lyrics.length < 10) return setStatus('musicStatus', 'Escribe la letra (al menos una línea), o elige «La IA escribe la letra».', true);
  musicTask({
    confirmText: `Se creará la canción en fal.ai. ${$('musicInfo').textContent}. ¿Continuar?`,
    run: async ({ fal, signal, status }) => {
      let endpoint, input;
      if (mode === 'lyrics') {
        endpoint = M.minimax;
        input = { prompt: musicPrompt().padEnd(10, '.'), lyrics_prompt: lyrics };
      } else if (mode === 'auto') {
        endpoint = M.sonauto;
        input = { prompt: musicPrompt(['lyrics in Spanish']), output_format: 'mp3', num_songs: 1 };
      } else {
        endpoint = M.ace;
        input = { tags: musicPrompt(), lyrics: '[instrumental]', duration: Number($('duration').value) };
      }
      storage.set(`${MUSIC_JOB}-meta`, JSON.stringify({ mode, lyrics: mode === 'lyrics' ? lyrics : '' }));
      const data = await runJob(fal, endpoint, input, {
        signal, onStatus: status, label: 'Componiendo (suele tardar 1–3 min)', storeKey: MUSIC_JOB,
      });
      await showSong(data, { inst: mode === 'inst', words: mode === 'lyrics' ? lyrics : mode === 'auto' ? data?.lyrics : '' });
      status('¡Listo! ✓');
      updateButtons();
    },
  });
});

// Canción pendiente (la pestaña se cerró mientras se componía): se recupera sin volver a pagar.
$('musicResume').addEventListener('click', () => {
  let meta = {};
  try { meta = JSON.parse(storage.get(`${MUSIC_JOB}-meta`) || '{}'); } catch { /* sin datos */ }
  musicTask({
    run: async ({ fal, signal, status }) => {
      status('Recuperando la canción pendiente…');
      const data = await resumeJob(fal, MUSIC_JOB, { signal, onStatus: status, label: 'Componiendo' });
      await showSong(data, { inst: meta.mode === 'inst', words: meta.mode === 'lyrics' ? meta.lyrics : data?.lyrics });
      status('¡Listo! ✓');
      updateButtons();
    },
  });
});
$('musicCancel').addEventListener('click', () => cancelTask('musicStatus'));

$('singWithMe').addEventListener('click', async () => {
  if (!state.music || state.music.inst || state.busy) return;
  if (!state.voice) return setStatus('musicStatus', 'Primero graba o sube tu voz (paso 1).', true);
  setStatus('musicStatus', 'Preparando la canción…');
  try {
    const blob = state.music.blob ?? await localCopy(state.music.url);
    await setSong(blob, 'canción creada');
    $('karaoke').checked = false;
    updateCoverInfo();
    $('coverPanel').scrollIntoView({ behavior: 'smooth' });
    setStatus('musicStatus', '');
    runCover();
  } catch (err) {
    setStatus('musicStatus', `No se pudo preparar: ${err.message}`, true);
  }
});

$('musicMode').addEventListener('change', updateMusicMode);
$('duration').addEventListener('change', updateMusicMode);

// ---------- arranque ----------

function updateButtons() {
  const ok = !!state.server?.configured && !state.busy;
  $('ttsBtn').disabled = !ok;
  $('coverBtn').disabled = !ok || !state.song;
  $('musicBtn').disabled = !ok;
  $('singWithMe').disabled = !ok;
  $('vocalGain').disabled = state.busy;
  $('musicResume').hidden = !jobStore.get(MUSIC_JOB);
  $('musicResume').disabled = !ok;
  updateTtsInfo();
  updateCoverInfo();
}

async function checkServer() {
  state.server = await serverStatus();
  const box = $('setup');
  if (!state.server.available) {
    box.hidden = false;
    box.innerHTML = state.server.network
      ? 'No se pudo contactar con el servidor. <button type="button" class="btn small" id="retry">Reintentar</button>'
      : 'Estas funciones necesitan el servidor de la app (la versión publicada en Vercel).';
    $('retry')?.addEventListener('click', checkServer);
  } else if (!state.server.configured) {
    box.hidden = false;
    box.innerHTML = 'Falta configurar el servidor: en Vercel → tu proyecto → Settings → Environment Variables, añade '
      + '<code>FAL_KEY</code> (tu clave de fal.ai) y <code>TM_PASSWORD</code> (una contraseña que tú elijas), y vuelve a publicar.';
  } else {
    box.hidden = true;
  }
  updateButtons();
}

$('password').value = storage.get('tm-ai-password');
$('ttsText').addEventListener('input', updateTtsInfo);
window.addEventListener('online', () => { if (!state.server?.configured) checkServer(); });
updateMusicMode();
checkServer();
idb.get('voice').then((v) => {
  if (!v?.wav || state.voice) return;
  state.voice = { wav: v.wav };
  showVoice(v.wav, `Usando tu voz guardada (${v.source ?? 'muestra'}). Puedes grabar otra cuando quieras.`);
  updateButtons();
});

// Depuración / pruebas automáticas.
if (new URLSearchParams(location.search).has('debug')) window.__studio = { state, chunkText, setVoice, setSong };
