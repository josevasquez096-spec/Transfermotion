import { FilesetResolver, PoseLandmarker } from '@mediapipe/tasks-vision';

// Los binarios WASM se sirven desde /mediapipe (ver scripts/copy-wasm.mjs).
const WASM = `${import.meta.env.BASE_URL}mediapipe`;
const MODEL =
  'https://storage.googleapis.com/mediapipe-models/pose_landmarker/pose_landmarker_full/float16/latest/pose_landmarker_full.task';

let fileset;
const cache = {};

async function create(runningMode, outputSegmentationMasks) {
  fileset ??= await FilesetResolver.forVisionTasks(WASM);
  const options = (delegate) => ({
    baseOptions: { modelAssetPath: MODEL, delegate },
    runningMode,
    numPoses: 1,
    outputSegmentationMasks,
  });
  try {
    return await PoseLandmarker.createFromOptions(fileset, options('GPU'));
  } catch (err) {
    console.warn('Delegado GPU no disponible, usando CPU.', err);
    return PoseLandmarker.createFromOptions(fileset, options('CPU'));
  }
}

function cached(key, factory) {
  cache[key] ??= factory().catch((err) => {
    delete cache[key];
    throw err;
  });
  return cache[key];
}

// Detector para video/cámara (modo VIDEO, con seguimiento entre fotogramas).
export const getVideoLandmarker = () => cached('video', () => create('VIDEO', false));

// Detector para la imagen del personaje (modo IMAGE, con máscara de segmentación).
export const getImageLandmarker = () => cached('image', () => create('IMAGE', true));
