import { createFalClient } from '@fal-ai/client';

// Cliente común para los modelos de fal.ai (video, voz y música). La clave de fal vive en el
// servidor (/api/fal/proxy); aquí solo se manda la contraseña de la app.

export const PROXY = '/api/fal/proxy';
const sleep = (ms) => new Promise((r) => setTimeout(r, ms));

export async function serverStatus() {
  try {
    const r = await fetch(PROXY, { cache: 'no-store' });
    if (!r.ok) return { available: false };
    return { available: true, ...(await r.json()) };
  } catch {
    return { available: false, network: true };
  }
}

export function falClient(password) {
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
  if (!status && !text && err?.name !== 'Error') return 'Error de red: revisa tu conexión.';
  return text || err?.message || `Error ${status}.`;
}

export const aborted = () => new DOMException('Cancelado', 'AbortError');
// Fallo de red pasajero (sin respuesta HTTP), no una cancelación ni un error del servidor.
export const isTransient = (e) => e?.name !== 'AbortError' && !(e?.status ?? e?.response?.status) && !(e instanceof RangeError);

// Trabajos guardados (para recuperarlos si la página se cierra, p. ej. al bloquear el iPhone).
export const jobStore = {
  get(key) { try { return JSON.parse(localStorage.getItem(key) || 'null'); } catch { return null; } },
  set(key, job) { try { localStorage.setItem(key, JSON.stringify(job)); } catch { /* sin almacenamiento */ } },
  clear(key) { try { localStorage.removeItem(key); } catch { /* sin almacenamiento */ } },
};

// Sube un archivo/Blob a fal y devuelve su URL. Reintenta los cortes de red.
export async function upload(fal, blob, { signal } = {}) {
  for (let i = 0; ; i++) {
    if (signal?.aborted) throw aborted();
    try {
      return await fal.storage.upload(blob);
    } catch (e) {
      if (!isTransient(e) || i >= 3) throw e;
      await sleep(1500 * (i + 1));
    }
  }
}

// Espera a un trabajo de la cola aguantando cortes de red (pantalla bloqueada, cambio de app o de wifi).
async function waitForJob(fal, job, { signal, onStatus = () => {}, label = 'Generando' }) {
  for (let fails = 0; ;) {
    if (signal?.aborted) throw aborted();
    try {
      const s = await fal.queue.status(job.endpoint, { requestId: job.requestId, logs: false, abortSignal: signal });
      fails = 0;
      const secs = Math.round((Date.now() - job.startedAt) / 1000);
      if (s.status === 'IN_QUEUE') onStatus(`En cola (posición ${s.queue_position ?? '?'})… ${secs} s`);
      else if (s.status === 'IN_PROGRESS') onStatus(`${label}… ${secs} s`);
      else if (s.status === 'COMPLETED') break;
    } catch (e) {
      if (!isTransient(e) || ++fails > 45) throw e;
      onStatus('Conexión perdida, reintentando…');
    }
    await sleep(job.poll ?? 3000);
  }
  for (let i = 0; ; i++) {
    try {
      return await fal.queue.result(job.endpoint, { requestId: job.requestId, abortSignal: signal });
    } catch (e) {
      if (!isTransient(e) || i >= 5) throw e;
      await sleep(2000);
    }
  }
}

// Espera el trabajo y, si el usuario cancela, también lo cancela en fal (si no, seguiría y se cobraría).
export async function finishJob(fal, job, { signal, onStatus, label, storeKey } = {}) {
  const cancel = () => fal.queue.cancel(job.endpoint, { requestId: job.requestId }).catch(() => {});
  signal?.addEventListener('abort', cancel, { once: true });
  try {
    const result = await waitForJob(fal, job, { signal, onStatus, label });
    if (storeKey) jobStore.clear(storeKey);
    return result.data;
  } catch (e) {
    // Si solo falló la red, el trabajo sigue guardado para recuperarlo después.
    if (storeKey && !isTransient(e)) jobStore.clear(storeKey);
    throw e;
  } finally {
    signal?.removeEventListener('abort', cancel);
  }
}

// Envía un trabajo a la cola y espera su resultado (devuelve result.data).
// storeKey (opcional): guarda el trabajo en localStorage para poder recuperarlo con resumeJob.
export async function runJob(fal, endpoint, input, { signal, onStatus = () => {}, label, storeKey, poll } = {}) {
  if (signal?.aborted) throw aborted();
  const { request_id: requestId } = await fal.queue.submit(endpoint, { input });
  const job = { endpoint, requestId, startedAt: Date.now(), poll };
  if (storeKey) jobStore.set(storeKey, job);
  if (signal?.aborted) {
    await fal.queue.cancel(endpoint, { requestId }).catch(() => {});
    if (storeKey) jobStore.clear(storeKey);
    throw aborted();
  }
  return finishJob(fal, job, { signal, onStatus, label, storeKey });
}

export async function resumeJob(fal, storeKey, opts = {}) {
  const job = jobStore.get(storeKey);
  if (!job?.endpoint || !job?.requestId) throw new Error('No hay ningún trabajo pendiente.');
  return finishJob(fal, job, { ...opts, storeKey });
}

// Primera URL de un archivo del tipo indicado dentro de una respuesta (por si la forma cambia).
export function findUrl(data, exts) {
  const re = new RegExp(`^https?://.+\\.(${exts.join('|')})(\\?|$)`, 'i');
  let found = null;
  JSON.stringify(data ?? {}, (k, v) => {
    if (!found && typeof v === 'string' && re.test(v)) found = v;
    return v;
  });
  return found;
}
