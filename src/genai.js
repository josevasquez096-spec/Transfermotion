import { falClient, upload, runJob, resumeJob, jobStore, findUrl, aborted } from './fal.js';

export { serverStatus, explainError } from './fal.js';

// "IA avanzada" de video: Wan 2.2 Animate en fal.ai.
//  - move:    tu foto hace el movimiento y los gestos del video (fondo de tu foto).
//  - replace: la persona del video se sustituye por la de tu foto (fondo del video).

export const ENDPOINTS = {
  move: 'fal-ai/wan/v2.2-14b/animate/move',
  replace: 'fal-ai/wan/v2.2-14b/animate/replace',
};
// Precio aproximado por segundo de video (dólares). Fuente: tarifas publicadas por terceros;
// el precio real lo marca fal.ai.
export const PRICE_PER_SECOND = { '480p': 0.04, '580p': 0.06, '720p': 0.08 };

// Trabajo en curso guardado: si la página se cierra (p. ej. el iPhone se bloquea), se puede recuperar.
const JOB_KEY = 'tm-ai-job';
export const pendingJob = () => jobStore.get(JOB_KEY);
export const forgetJob = () => jobStore.clear(JOB_KEY);

const LABEL = 'Generando el video con IA (suele tardar 1–5 min)';

function videoResult(data) {
  const url = data?.video?.url ?? findUrl(data, ['mp4', 'webm', 'mov']);
  if (!url) throw new Error('La IA terminó pero no devolvió ningún video.');
  return { url, seed: data?.seed };
}

// video: File del video fuente; image: File/Blob de la foto. onStatus(texto) informa del progreso.
export async function generate({ mode, video, image, password, resolution = '480p', onStatus = () => {}, signal }) {
  const endpoint = ENDPOINTS[mode];
  if (!endpoint) throw new Error('Modo desconocido.');
  const fal = falClient(password);
  onStatus('Subiendo el video…');
  const videoUrl = await upload(fal, video, { signal });
  onStatus('Subiendo la foto…');
  const imageUrl = await upload(fal, image, { signal });
  if (signal?.aborted) throw aborted();
  onStatus('Enviando a la IA…');
  const data = await runJob(fal, endpoint, { video_url: videoUrl, image_url: imageUrl, resolution }, {
    signal, onStatus, label: LABEL, storeKey: JOB_KEY, poll: 4000,
  });
  return videoResult(data);
}

// Retoma el último trabajo guardado (p. ej. tras recargar la página).
export async function resume({ password, onStatus = () => {}, signal }) {
  onStatus('Recuperando el video pendiente…');
  return videoResult(await resumeJob(falClient(password), JOB_KEY, { signal, onStatus, label: LABEL }));
}
