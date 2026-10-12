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

export async function serverStatus() {
  try {
    const r = await fetch(PROXY, { cache: 'no-store' });
    if (!r.ok) return { available: false };
    return { available: true, ...(await r.json()) };
  } catch {
    return { available: false };
  }
}

// Mensaje entendible para los errores más comunes.
export function explainError(err) {
  const status = err?.status ?? err?.response?.status;
  const detail = err?.body?.detail ?? err?.body?.error;
  if (status === 401) return 'Contraseña incorrecta.';
  if (status === 503) return 'El servidor aún no está configurado (faltan FAL_KEY y TM_PASSWORD en Vercel).';
  if (status === 403) return 'Petición no permitida por el servidor.';
  if (status === 422) return `fal.ai rechazó los datos: ${typeof detail === 'string' ? detail : JSON.stringify(detail)}`;
  if (status === 402 || /balance|credit|payment/i.test(String(detail ?? err?.message))) {
    return 'Tu cuenta de fal.ai no tiene saldo suficiente.';
  }
  return err?.message || 'Error desconocido.';
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

// video: File del video fuente; image: File/Blob de la foto. onStatus(texto) informa del progreso.
export async function generate({ mode, video, image, password, resolution = '480p', onStatus = () => {}, signal }) {
  const endpoint = ENDPOINTS[mode];
  if (!endpoint) throw new Error('Modo desconocido.');
  const fal = createFalClient({
    proxyUrl: PROXY,
    // La contraseña viaja solo hasta nuestro servidor (las subidas van directas a fal sin ella).
    requestMiddleware: async (req) => ({ ...req, headers: { ...(req.headers || {}), 'x-tm-password': password } }),
  });

  onStatus('Subiendo el video…');
  const videoUrl = await fal.storage.upload(video);
  if (signal?.aborted) throw new DOMException('Cancelado', 'AbortError');
  onStatus('Subiendo la foto…');
  const imageUrl = await fal.storage.upload(image);
  if (signal?.aborted) throw new DOMException('Cancelado', 'AbortError');

  onStatus('Enviando a la IA…');
  const started = Date.now();
  const result = await fal.subscribe(endpoint, {
    input: { video_url: videoUrl, image_url: imageUrl, resolution },
    mode: 'polling',
    pollInterval: 4000,
    logs: true,
    abortSignal: signal,
    onQueueUpdate: (u) => {
      const secs = Math.round((Date.now() - started) / 1000);
      if (u.status === 'IN_QUEUE') onStatus(`En cola (posición ${u.queue_position ?? '?'})… ${secs} s`);
      else if (u.status === 'IN_PROGRESS') onStatus(`Generando el video con IA… ${secs} s (suele tardar 1–5 min)`);
    },
  });
  const url = findVideoUrl(result?.data);
  if (!url) throw new Error('La IA terminó pero no devolvió ningún video.');
  return { url, seed: result.data?.seed };
}
