import { defineConfig, loadEnv } from 'vite';
import { handleNode } from './server/falProxy.js';

// En desarrollo y en `vite preview` se monta el mismo proxy que la función de Vercel
// (/api/fal/proxy), leyendo FAL_KEY y TM_PASSWORD de .env.local.
function falProxy(env) {
  const mount = (server) => {
    server.middlewares.use('/api/fal/proxy', (req, res) => {
      handleNode(req, res, { ...process.env, ...env }).catch((err) => {
        res.statusCode = 500;
        res.end(JSON.stringify({ error: err.message }));
      });
    });
  };
  return { name: 'fal-proxy', configureServer: mount, configurePreviewServer: mount };
}

export default defineConfig(({ mode }) => ({
  plugins: [falProxy(loadEnv(mode, process.cwd(), ''))],
  // Dos páginas: el video (index.html) y el estudio de voz y música (studio.html).
  build: { rollupOptions: { input: { main: 'index.html', studio: 'studio.html' } } },
}));
