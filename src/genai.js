import { createFalClient } from '@fal-ai/client';

// "IA avanzada": genera el video en los servidores de fal.ai con Wan 2.2 Animate.
//  - move:    tu foto hace el movimiento y los gestos del video (fondo de tu foto).
//  - replace: la persona del video se sustituye por la de tu foto (fondo del video).
// La clave de fal vive en el servidor (/api/fal/proxy); aquí solo se manda la contraseña de la app.

const PROXY = '/api/fal/proxy';
export const ENDPOINTS = {
  move: 'fal-ai/wan/v2.2-14b/animate/move',
  replace: 'fal-ai/wan/v2.2-14b/animate/replace',
};
// Precio aproximado por segundo de video (dólares). Fuente: tarifas publicadas por terceros;
// el precio real lo marca fal.ai.
export const PRICE_PER_SECOND = { '480p': 0.04, '580p': 0.06, '720p': 0.08 };

// Trabajo en curso guardado: si la página se cierra (p. ej. el iPhone se bloquea), se puede recuperar.
const JOB_KEY = 'tm-ai-job';
const sleep = (ms) => new Promise((r) => setTimeout(r, ms));
const store = {
  get() { try { return JSON.parse(localStorage.getItem(JOB_KEY) || 'null'); } catch { return null; } },
  set(job) { try { localStorage.setItem(JOB_KEY, JSON.stringify(job)); } catch { /* sin almacenamiento */ } },
  clear() { try { localStorage.removeItem(JOB_KEY); } catch { /* sin almacenamiento */ } },
};
export const pendingJob = () => store.get();
export const forgetJob = () => store.clear();

export async function serverStatus() {
  try {
    const r = await fetch(PROXY, { cache: 'no-store' });
    if (!r.ok) return { available: false };
    return { available: true, ...(await r.json()) };
  } catch {
    return { available: false, network: true };
  }
}

// Mensaje entendible para los errores más comunes. El proxy marca los suyos con source: 'proxy';
// el resto viene de fal.ai (texto en body.detail).
export function explainError(err) {
  const status = err?.status ?? err?.response?.status;
  const body = err?.body ?? {};
  const raw = body.detail ?? body.error;
  const text = typeof raw === 'string' ? raw
    : Array.isArray(raw) ? raw.map((d) => d?.msg ?? JSON.stringify(d)).join('; ')
    : raw ? JSON.stringify(raw) : '';
  if (status === 402 || /balance|credit|payment|locked/i.test(text)) return 'Tu cuenta de fal.ai no tiene saldo suficiente.';
  if (body.source === 'proxy') {
    if (body.code === 'bad_password') return 'Contraseña incorrecta.';
    if (body.code === 'not_configured') return 'El servidor aún no está configurado (faltan FAL_KEY y TM_PASSWORD en Vercel).';
    if (body.code === 'blocked') return 'Petición no permitida por el servidor.';
    return text || `Error ${status} del servidor.`;
  }
  if (status === 401 || status === 403) return `fal.ai rechazó la clave FAL_KEY del servidor (revísala en Vercel). ${text}`.trim();
  if (status === 422) return `fal.ai rechazó los datos: ${text}`;
  if (status === 413) return 'El archivo es demasiado grande.';
  if (!status && !text) return 'Error de red: revisa tu conexión.';
  return text || err?.message || `Error ${status}.`;
}

function findVideoUrl(data) {
  if (data?.video?.url) return data.video.url;
  // Por si la respuesta cambia de forma: primera URL de video que aparezca.
  let found = null;
  JSON.stringify(data ?? {}, (k, v) => {
    if (!found && typeof v === 'string' && /^https?:\/\/.+\.(mp4|webm|mov)(\?|$)/i.test(v)) found = v;
    return v;
  });
  return found;
}

function client(password) {
  return createFalClient({
    proxyUrl: PROXY,
    // La contraseña viaja solo hasta nuestro servidor (las subidas van directas a fal sin ella).
    // Se codifica para que cualquier carácter (€, emojis…) quepa en una cabecera HTTP.
    requestMiddleware: async (req) => ({
      ...req,
      headers: { ...(req.headers || {}), 'x-tm-password': encodeURIComponent(password) },
    }),
  });
}

const aborted = () => new DOMException('Cancelado', 'AbortError');
// Fallo de red pasajero (sin respuesta HTTP), no una cancelación ni un error del servidor.
const transient = (e) => e?.name !== 'AbortError' && !(e?.status ?? e?.response?.status);

// Espera al trabajo aguantando cortes de red (pantalla bloqueada, cambio de app o de wifi).
async function waitForJob(fal, job, { signal, onStatus }) {
  for (let fails = 0; ;) {
    if (signal?.aborted) throw aborted();
    try {
      const s = await fal.queue.status(job.endpoint, { requestId: job.requestId, logs: false, abortSignal: signal });
      fails = 0;
      const secs = Math.round((Date.now() - job.startedAt) / 1000);
      if (s.status === 'IN_QUEUE') onStatus(`En cola (posición ${s.queue_position ?? '?'})… ${secs} s`);
      else if (s.status === 'IN_PROGRESS') onStatus(`Generando el video con IA… ${secs} s (suele tardar 1–5 min)`);
      else if (s.status === 'COMPLETED') break;
    } catch (e) {
      if (!transient(e) || ++fails > 45) throw e;
      onStatus('Conexión perdida, reintentando…');
    }
    await sleep(4000);
  }
  for (let i = 0; ; i++) {
    try {
      return await fal.queue.result(job.endpoint, { requestId: job.requestId, abortSignal: signal });
    } catch (e) {
      if (!transient(e) || i >= 5) throw e;
      await sleep(2000);
    }
  }
}

async function finish(fal, job, opts) {
  const { signal } = opts;
  // Cancelar también avisa a fal.ai (si solo se dejara de esperar, el trabajo seguiría y se cobraría).
  const cancel = () => fal.queue.cancel(job.endpoint, { requestId: job.requestId }).catch(() => {});
  signal?.addEventListener('abort', cancel, { once: true });
  try {
    const result = await waitForJob(fal, job, opts);
    const url = findVideoUrl(result?.data);
    if (!url) throw new Error('La IA terminó pero no devolvió ningún video.');
    store.clear();
    return { url, seed: result.data?.seed };
  } catch (e) {
    // Si solo falló la red, el trabajo sigue guardado para recuperarlo después.
    if (!transient(e)) store.clear();
    throw e;
  } finally {
    signal?.removeEventListener('abort', cancel);
  }
}

// video: File del video fuente; image: File/Blob de la foto. onStatus(texto) informa del progreso.
export async function generate({ mode, video, image, password, resolution = '480p', onStatus = () => {}, signal }) {
  const endpoint = ENDPOINTS[mode];
  if (!endpoint) throw new Error('Modo desconocido.');
  const fal = client(password);

  onStatus('Subiendo el video…');
  const videoUrl = await fal.storage.upload(video);
  if (signal?.aborted) throw aborted();
  onStatus('Subiendo la foto…');
  const imageUrl = await fal.storage.upload(image);
  if (signal?.aborted) throw aborted();

  onStatus('Enviando a la IA…');
  const { request_id: requestId } = await fal.queue.submit(endpoint, {
    input: { video_url: videoUrl, image_url: imageUrl, resolution },
  });
  const job = { endpoint, requestId, startedAt: Date.now() };
  store.set(job);
  if (signal?.aborted) {
    await fal.queue.cancel(endpoint, { requestId }).catch(() => {});
    store.clear();
    throw aborted();
  }
  return finish(fal, job, { signal, onStatus });
}

// Retoma el último trabajo guardado (p. ej. tras recargar la página).
export async function resume({ password, onStatus = () => {}, signal }) {
  const job = store.get();
  if (!job?.endpoint || !job?.requestId) throw new Error('No hay ningún video pendiente.');
  onStatus('Recuperando el video pendiente…');
  return finish(client(password), job, { signal, onStatus });
}
