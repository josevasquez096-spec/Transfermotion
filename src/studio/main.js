import { falClient, upload, runJob, serverStatus, explainError, findUrl, aborted } from '../fal.js';
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
  song: null, // { file: Blob, name, duration }
  cover: null, // { inst, vocals (AudioBuffer) }
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
    });
  },
  get: (k) => idb.run('readonly', (s) => s.get(k)).catch(() => null),
  set: (k, v) => idb.run('readwrite', (s) => s.put(v, k)).catch(() => null),
};

const usd = (v) => `$${v < 0.01 ? v.toFixed(3) : v.toFixed(2)} USD`;
const mmss = (s) => `${Math.floor(s / 60)}:${String(Math.round(s % 60)).padStart(2, '0')}`;

function setStatus(id, text, error = false) {
  const el = $(id);
  el.textContent = text;
  el.classList.toggle('error', error);
}

function showResult(id, url, downloads = {}) {
  const box = $(id);
  box.hidden = false;
  box.querySelector('audio').src = url;
  const links = box.querySelectorAll('a[download]');
  links.forEach((a) => {
    const key = a.dataset.dl;
    a.href = key ? downloads[key] ?? '#' : downloads.main ?? url;
    a.hidden = key ? !downloads[key] : false;
  });
}

// Copia local (mismo origen) de un archivo remoto para que «Descargar» funcione.
async function localCopy(url) {
  try {
    const r = await fetch(url);
    if (!r.ok) throw new Error();
    return URL.createObjectURL(await r.blob());
  } catch {
    return url;
  }
}

const wavUrl = (buffer) => URL.createObjectURL(bufferToWav(buffer));

function makeBuffer(samples, sampleRate) {
  const b = new AudioBuffer({ length: Math.max(1, samples.length), numberOfChannels: 1, sampleRate });
  b.copyToChannel(samples, 0);
  return b;
}

async function pool(items, n, fn) {
  const out = new Array(items.length);
  let next = 0;
  const worker = async () => {
    while (next < items.length) {
      const i = next++;
      out[i] = await fn(items[i], i);
    }
  };
  await Promise.all(Array.from({ length: Math.min(n, items.length) }, worker));
  return out;
}

// Ejecuta una tarea de IA con contraseña, confirmación de costo, cancelación y mensajes de error.
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
  state.busy = true;
  state.abort = new AbortController();
  if (cancelId) $(cancelId).hidden = false;
  updateButtons();
  try {
    await run({ fal: falClient(password), signal: state.abort.signal, status: (t) => setStatus(statusId, t) });
  } catch (err) {
    console.error(err);
    if (err?.name === 'AbortError') setStatus(statusId, 'Cancelado. Lo que la IA ya procesó puede cobrarse.', true);
    else setStatus(statusId, `No se pudo completar: ${explainError(err)}`, true);
  } finally {
    state.busy = false;
    state.abort = null;
    if (cancelId) $(cancelId).hidden = true;
    updateButtons();
  }
}

// Sube la muestra de voz una vez por visita.
async function voiceUrl(fal, signal) {
  if (!state.voice) throw new Error('Primero graba o sube tu voz (paso 1).');
  state.voice.url ??= await upload(fal, state.voice.wav, { signal });
  return state.voice.url;
}

// ---------- 1. Tu voz ----------

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
  idb.set('voice', { wav, source, date: Date.now() });
  $('voicePlayer').src = URL.createObjectURL(wav);
  $('voicePlayer').hidden = false;
  $('voiceBadge').hidden = false;
  setStatus('voiceStatus', `Voz guardada en este dispositivo (${Math.min(30, buffer.duration).toFixed(0)} s, ${source}).`);
  updateButtons();
}

let recording = null;
$('recBtn').addEventListener('click', async () => {
  if (recording) {
    const blob = await recording.stop();
    recording = null;
    $('recBtn').textContent = '● Grabar mi voz';
    $('recBtn').classList.remove('recording');
    $('recLevel').style.width = '0';
    return setVoice(blob, 'grabada');
  }
  try {
    recording = await recordMic({
      maxSeconds: 30,
      onLevel: (v) => { $('recLevel').style.width = `${Math.round(v * 100)}%`; },
      onTick: (s) => { $('recInfo').textContent = `${s.toFixed(0)} / 30 s${s < 10 ? ' (mínimo 10 s)' : ''}`; },
    });
    $('recBtn').textContent = '■ Terminar';
    $('recBtn').classList.add('recording');
    setStatus('voiceStatus', 'Grabando… lee la frase y sigue hablando con naturalidad.');
    // Se detiene sola a los 30 s.
    setTimeout(async () => { if (recording) $('recBtn').click(); }, 30_500);
  } catch (err) {
    recording = null;
    setStatus('voiceStatus', `No se pudo usar el micrófono: ${err.message}`, true);
  }
});

$('voiceInput').addEventListener('change', () => {
  const f = $('voiceInput').files[0];
  $('voiceInput').value = '';
  if (!f) return;
  if (!$('voiceConsent').checked) {
    return setStatus('voiceStatus', 'Marca la casilla: solo puedes usar tu voz o la de alguien que te dé permiso.', true);
  }
  setVoice(f, 'subida');
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
  return out;
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
  task({
    statusId: 'ttsStatus',
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
        const url = data?.audio?.url ?? findUrl(data, ['wav', 'mp3', 'flac', 'ogg', 'm4a']);
        if (!url) throw new Error('La IA no devolvió audio.');
        buffers.push(await fetchAudio(url, { signal }));
      }
      const out = await concat(buffers, { gap: 0.3, sampleRate: buffers[0].sampleRate });
      const url = wavUrl(out);
      showResult('ttsResult', url, { main: url });
      status('¡Listo! ✓');
    },
  });
});

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
  const sep = s.duration * PRICE.demucsSec;
  $('coverInfo').textContent = $('karaoke').checked
    ? `Separar ${mmss(s.duration)}: ~${usd(sep)}`
    : `Separar ~${usd(sep)} + cambiar la voz (${frags(s.duration)}, tarifa de fal.ai)`;
}

$('songInput').addEventListener('change', () => {
  const f = $('songInput').files[0];
  $('songInput').value = '';
  if (f) setSong(f, f.name);
});

async function remixCover() {
  const c = state.cover;
  if (!c) return;
  const tracks = [{ buffer: c.inst }];
  if (c.vocals) tracks.push({ buffer: c.vocals, gain: Number($('vocalGain').value) });
  const out = await mix(tracks, { sampleRate: c.inst.sampleRate, channels: 2, duration: c.inst.duration });
  if (c.coverUrl) URL.revokeObjectURL(c.coverUrl);
  c.coverUrl = wavUrl(out);
  showResult('coverResult', c.coverUrl, { cover: c.coverUrl, inst: c.instUrl, vocals: c.vocalsUrl });
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
      status('Subiendo la canción…');
      const songUrl = await upload(fal, song.file, { signal });
      const stems = await runJob(fal, M.demucs, {
        audio_url: songUrl, model: 'htdemucs', stems: ['vocals', 'drums', 'bass', 'other'], output_format: 'mp3',
      }, { signal, onStatus: status, label: 'Separando voz y música' });
      status('Descargando las pistas…');
      const [vocals, ...rest] = await Promise.all(['vocals', 'drums', 'bass', 'other'].map((k) => {
        const url = stems?.[k]?.url;
        return url ? fetchAudio(url, { signal }) : null;
      }));
      const parts = rest.filter(Boolean);
      if (!vocals || !parts.length) throw new Error('La separación no devolvió las pistas esperadas.');
      const inst = await mix(parts.map((b) => ({ buffer: b })), { sampleRate: parts[0].sampleRate, channels: 2 });
      state.cover = { inst, instUrl: wavUrl(inst), vocals: karaoke ? null : undefined };

      if (karaoke) {
        state.cover.vocalsUrl = wavUrl(vocals);
        await remixCover();
        return status('¡Listo! ✓ Instrumental separado.');
      }

      // Voz en fragmentos de ≤ 20 s cortados en silencios; los mudos no se convierten.
      const SR = 24000;
      const voice = await voiceUrl(fal, signal);
      const mono = await toMono(vocals, SR);
      const segs = findSegments(mono, SR, { maxLen: 20, minLen: 6 });
      const todo = segs.filter((s) => !s.silent);
      let done = 0;
      status(`Cambiando la voz: 0/${todo.length}…`);
      const converted = await pool(todo, 3, async (seg) => {
        const wav = encodeWav([slice(mono, SR, seg.start, seg.end)], SR);
        const src = await upload(fal, wav, { signal });
        const data = await runJob(fal, M.vc, {
          source_audio_url: src, target_voice_audio_url: voice, high_quality_audio: true,
        }, { signal, label: 'Cambiando la voz' });
        const url = data?.audio?.url ?? findUrl(data, ['wav', 'mp3', 'flac', 'ogg', 'm4a']);
        if (!url) throw new Error('La IA no devolvió la voz convertida.');
        const out = await toMono(await fetchAudio(url, { signal }), SR);
        status(`Cambiando la voz: ${++done}/${todo.length}…`);
        return { ...seg, samples: out };
      });
      if (signal.aborted) throw aborted();
      status('Mezclando…');
      const newVocals = makeBuffer(placeSegments(mono.length, SR, converted), SR);
      state.cover.vocals = newVocals;
      state.cover.vocalsUrl = wavUrl(newVocals);
      await remixCover();
      status('¡Listo! ✓ Ajusta el volumen de la voz si hace falta.');
    },
  });
}

$('coverBtn').addEventListener('click', runCover);
$('coverCancel').addEventListener('click', () => state.abort?.abort());
$('karaoke').addEventListener('change', updateCoverInfo);
let remixTimer = 0;
$('vocalGain').addEventListener('input', () => {
  clearTimeout(remixTimer);
  remixTimer = setTimeout(() => remixCover().catch(console.error), 250);
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
  const cost = mode === 'lyrics' ? `~${usd(PRICE.minimax)}` : mode === 'inst' ? `~${usd(PRICE.aceSec * Number($('duration').value))}` : 'tarifa de fal.ai';
  $('musicInfo').textContent = `Costo aproximado: ${cost}`;
}

function musicPrompt(extra = []) {
  const parts = [STYLES[state.style][1], $('mood').value, $('musicMode').value !== 'inst' && $('singer').value, ...extra, $('musicDesc').value.trim()];
  return parts.filter(Boolean).join(', ').slice(0, 300);
}

$('musicBtn').addEventListener('click', () => {
  const mode = $('musicMode').value;
  const lyrics = $('lyrics').value.trim();
  if (mode === 'lyrics' && lyrics.length < 10) return setStatus('musicStatus', 'Escribe la letra (al menos una línea), o elige «La IA escribe la letra».', true);
  task({
    statusId: 'musicStatus',
    confirmText: `Se creará la canción en fal.ai. ${$('musicInfo').textContent}. ¿Continuar?`,
    run: async ({ fal, signal, status }) => {
      let data, endpoint, input;
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
      data = await runJob(fal, endpoint, input, { signal, onStatus: status, label: 'Componiendo (suele tardar 1–3 min)' });
      const audio = Array.isArray(data?.audio) ? data.audio[0] : data?.audio;
      const url = audio?.url ?? findUrl(data, ['mp3', 'wav', 'flac', 'ogg', 'm4a']);
      if (!url) throw new Error('La IA no devolvió la canción.');
      state.music = { url };
      showResult('musicResult', url, { main: url });
      localCopy(url).then((local) => {
        state.music.local = local;
        $('musicResult').querySelector('a[download]').href = local;
      });
      const words = mode === 'lyrics' ? lyrics : data?.lyrics;
      $('musicLyrics').hidden = !words;
      $('musicLyrics').textContent = words || '';
      status('¡Listo! ✓');
    },
  });
});

$('singWithMe').addEventListener('click', async () => {
  if (!state.music) return;
  if (!state.voice) return setStatus('musicStatus', 'Primero graba o sube tu voz (paso 1).', true);
  setStatus('musicStatus', 'Preparando la canción…');
  try {
    const r = await fetch(state.music.local ?? state.music.url);
    await setSong(await r.blob(), 'canción creada');
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
  $('voicePlayer').src = URL.createObjectURL(v.wav);
  $('voicePlayer').hidden = false;
  $('voiceBadge').hidden = false;
  setStatus('voiceStatus', `Usando tu voz guardada (${v.source ?? 'muestra'}). Puedes grabar otra cuando quieras.`);
  updateButtons();
});

// Depuración / pruebas automáticas.
if (new URLSearchParams(location.search).has('debug')) window.__studio = { state, chunkText, setVoice, setSong };
