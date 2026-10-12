// Función de Vercel: /api/fal/proxy (ver server/falProxy.js).
import { handleNode } from '../../server/falProxy.js';

export default function handler(req, res) {
  return handleNode(req, res);
}
