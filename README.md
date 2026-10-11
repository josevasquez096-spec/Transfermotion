# Transfer Motion 🕺

Transfiere el movimiento de un video (o de tu cámara) a la imagen de cualquier personaje, con IA y directamente en el navegador.

1. **Movimiento**: sube un video, usa la cámara o la coreografía de demostración.
2. **Personaje**: sube una foto o dibujo de una persona de cuerpo completo (o usa el personaje demo).
3. **Resultado**: el personaje imita el movimiento en tiempo real. Pulsa **Grabar** para descargar un video `.webm`.

Todo se procesa localmente; ninguna imagen ni video sale de tu equipo.

## Cómo usarla

```bash
npm install
npm run dev      # http://localhost:5173
npm run build    # genera dist/ para publicar en cualquier hosting estático
```

Necesita un navegador moderno con WebGL (Chrome, Edge, Firefox o Safari recientes). La primera vez descarga el modelo de pose de MediaPipe (~9 MB) desde Google.

## Cómo funciona

- **Detección de pose**: [MediaPipe Pose Landmarker](https://ai.google.dev/edge/mediapipe/solutions/vision/pose_landmarker) obtiene 33 puntos del cuerpo en cada fotograma del video y en la imagen del personaje, además de una máscara para recortar el fondo.
- **Esqueleto y retargeting** (`src/skeleton.js`): los puntos se reducen a un esqueleto de 19 articulaciones. Se copia la dirección de cada hueso del video, pero con las longitudes de hueso del personaje, para conservar sus proporciones. Hombros y caderas siguen la columna, de modo que el personaje no se deforma cuando la persona del video gira de lado.
- **Deformación** (`src/mesh.js`, `src/renderer.js`): sobre la imagen se crea una malla con pesos de skinning (cada vértice sigue a los huesos más cercanos) y la GPU la deforma con WebGL en cada fotograma.
- **Ajuste manual**: si la detección no es perfecta, arrastra los puntos del esqueleto en el panel del personaje.

## Consejos

- Usa imágenes del personaje de frente, de cuerpo completo y con los brazos algo separados del cuerpo.
- Los PNG con fondo transparente dan los mejores resultados.
- Si el personaje se desplaza demasiado, desactiva "Seguir desplazamiento" o pulsa "Recalibrar posición".
