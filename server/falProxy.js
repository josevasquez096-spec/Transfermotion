// Proxy hacia fal.ai para la "IA avanzada": guarda la clave (FAL_KEY) en el servidor y solo deja
// pasar las llamadas que usa la app (Wan 2.2 Animate y la subida de archivos).
// El video no pasa por aquí: el navegador lo sube directamente a la URL firmada que devuelve fal.
//
// Variables de entorno:
//   FAL_KEY      clave de API de fal.ai (obligatoria)
//   TM_PASSWORD  contraseña que pide la app (obligatoria: sin ella cualquiera con el enlace gastaría tu saldo)
import { timingSafeEqual } from 'node:crypto';

export const TARGET_HEADER = 'x-fal-target-url';
export const PASSWORD_HEADER = 'x-tm-password';

const ALLOWED = [
  // Enviar un trabajo a la cola
  { method: 'POST', url: /^https:\/\/queue\.fal\.run\/fal-ai\/wan\/v2\.2-14b\/animate\/(move|replace)$/ },
  // Estado y resultado del trabajo
  { method: 'GET', url: /^https:\/\/queue\.fal\.run\/fal-ai\/wan\/requests\/[A-Za-z0-9-]+(\/status)?(\?logs=[01])?$/ },
  // Cancelar
  { method: 'PUT', url: /^https:\/\/queue\.fal\.run\/fal-ai\/wan\/requests\/[A-Za-z0-9-]+\/cancel$/ },
  // Pedir una URL firmada para subir un archivo (la subida en sí va directa del navegador a fal)
  { method: 'POST', url: /^https:\/\/rest\.fal\.ai\/storage\/upload\/initiate\?storage_type=fal-cdn-v3$/ },
];

const MAX_BODY = 64 * 1024;

function same(a, b) {
  const x = Buffer.from(String(a ?? ''));
  const y = Buffer.from(String(b ?? ''));
  return x.length === y.length && timingSafeEqual(x, y);
}

const reply = (status, data) => ({
  status,
  headers: { 'content-type': 'application/json; charset=utf-8', 'cache-control': 'no-store' },
  body: JSON.stringify(data),
});

// req: { method, headers (minúsculas), body (string | undefined) }. Devuelve { status, headers, body }.
export async function proxyFal(req, env = process.env, fetchImpl = fetch) {
  const method = String(req.method || 'GET').toUpperCase();
  const h = (name) => {
    const v = req.headers?.[name];
    return Array.isArray(v) ? v[0] : v;
  };
  const configured = Boolean(env.FAL_KEY && env.TM_PASSWORD);
  const target = h(TARGET_HEADER);

  // Sin destino: la app pregunta si el servidor está configurado.
  if (!target) {
    if (method !== 'GET') return reply(400, { error: 'Falta la cabecera x-fal-target-url.' });
    return reply(200, { configured, missing: [!env.FAL_KEY && 'FAL_KEY', !env.TM_PASSWORD && 'TM_PASSWORD'].filter(Boolean) });
  }
  if (!configured) return reply(503, { error: 'El servidor no tiene configuradas FAL_KEY y TM_PASSWORD.' });
  if (!same(h(PASSWORD_HEADER), env.TM_PASSWORD)) return reply(401, { error: 'Contraseña incorrecta.' });
  if (!ALLOWED.some((a) => a.method === method && a.url.test(target))) {
    return reply(403, { error: 'Destino no permitido.' });
  }
  const body = method === 'GET' ? undefined : (req.body ?? '');
  if (body && body.length > MAX_BODY) return reply(413, { error: 'Petición demasiado grande.' });

  // Se reenvían las cabeceras x-fal-* del cliente (prioridad de cola, ciclo de vida de archivos...).
  const headers = {
    authorization: `Key ${env.FAL_KEY}`,
    accept: 'application/json',
    'content-type': 'application/json',
  };
  for (const [k, v] of Object.entries(req.headers || {})) {
    const key = k.toLowerCase();
    if (key.startsWith('x-fal-') && key !== TARGET_HEADER) headers[key] = Array.isArray(v) ? v[0] : v;
  }
  let res;
  try {
    res = await fetchImpl(target, { method, headers, body: body || undefined });
  } catch (err) {
    return reply(502, { error: `No se pudo contactar con fal.ai: ${err.message}` });
  }
  return {
    status: res.status,
    headers: {
      'content-type': res.headers.get('content-type') || 'application/json',
      'cache-control': 'no-store',
    },
    body: await res.text(),
  };
}

// Lee el cuerpo de una petición de Node (http.IncomingMessage) como texto, con límite de tamaño.
export async function readBody(req) {
  if (typeof req.body === 'string') return req.body;
  if (req.body && typeof req.body === 'object' && !Buffer.isBuffer(req.body)) return JSON.stringify(req.body);
  if (Buffer.isBuffer(req.body)) return req.body.toString('utf8');
  const chunks = [];
  let size = 0;
  for await (const c of req) {
    size += c.length;
    if (size > MAX_BODY) break;
    chunks.push(c);
  }
  return Buffer.concat(chunks).toString('utf8');
}

// Adaptador para servidores de Node (función de Vercel y servidor de desarrollo de Vite).
export async function handleNode(req, res, env = process.env) {
  const body = req.method === 'GET' || req.method === 'HEAD' ? undefined : await readBody(req);
  const out = await proxyFal({ method: req.method, headers: req.headers, body }, env);
  res.statusCode = out.status;
  for (const [k, v] of Object.entries(out.headers)) res.setHeader(k, v);
  res.end(out.body);
}
