import { FaceLandmarker, FilesetResolver, PoseLandmarker } from '@mediapipe/tasks-vision';

// Los binarios WASM se sirven desde /mediapipe (ver scripts/copy-wasm.mjs).
const WASM = `${import.meta.env.BASE_URL}mediapipe`;
const MODEL =
  'https://storage.googleapis.com/mediapipe-models/pose_landmarker/pose_landmarker_full/float16/latest/pose_landmarker_full.task';

const FACE_MODEL =
  'https://storage.googleapis.com/mediapipe-models/face_landmarker/face_landmarker/float16/1/face_landmarker.task';

let fileset;
const cache = {};

async function withDelegate(Task, options) {
  fileset ??= await FilesetResolver.forVisionTasks(WASM);
  const opts = (delegate) => ({ ...options, baseOptions: { ...options.baseOptions, delegate } });
  try {
    return await Task.createFromOptions(fileset, opts('GPU'));
  } catch (err) {
    console.warn('Delegado GPU no disponible, usando CPU.', err);
    return Task.createFromOptions(fileset, opts('CPU'));
  }
}

const create = (runningMode, outputSegmentationMasks) =>
  withDelegate(PoseLandmarker, {
    baseOptions: { modelAssetPath: MODEL },
    runningMode,
    numPoses: 1,
    outputSegmentationMasks,
  });

const createFace = (runningMode) =>
  withDelegate(FaceLandmarker, {
    baseOptions: { modelAssetPath: FACE_MODEL },
    runningMode,
    numFaces: 1,
    outputFaceBlendshapes: runningMode === 'VIDEO',
  });

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

// Malla facial (478 puntos + gestos) para el video/cámara.
export const getFaceVideoLandmarker = () => cached('faceVideo', () => createFace('VIDEO'));

// Malla facial de la imagen del personaje.
export const getFaceImageLandmarker = () => cached('faceImage', () => createFace('IMAGE'));
