// Copia los binarios WASM de MediaPipe a public/ para servirlos localmente.
import { cpSync, mkdirSync } from 'node:fs';

const from = 'node_modules/@mediapipe/tasks-vision/wasm';
const to = 'public/mediapipe';
mkdirSync(to, { recursive: true });
cpSync(from, to, { recursive: true });
console.log(`WASM de MediaPipe copiado a ${to}`);
