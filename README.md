# Transfer Motion 🕺

Transfiere el movimiento de un video (o de tu cámara) a la imagen de cualquier personaje, con IA y directamente en el navegador.

1. **Movimiento**: sube un video, usa la cámara o la coreografía de demostración. Sirven planos de cuerpo
   entero, planos medios y primeros planos de la cara, y los cambios de plano se detectan solos.
2. **Personaje**: sube una foto o dibujo de una persona (o usa el personaje demo).
3. **Resultado**: el personaje imita el movimiento del cuerpo y, si se le ve la cara, también los gestos:
   parpadeos, mirada, cejas, sonrisa, boca abierta con dientes y giros de cabeza (con el pelo y las orejas).
   Con el encuadre **Como el video** el resultado copia el plano de la fuente (primer plano, plano medio…).
   Pulsa **Grabar** para descargar un video `.webm`.

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
- **Capas** (`src/mesh.js`): el personaje se recorta en capas independientes (cuerpo, brazos y piernas) como un muñeco de papel. Así un brazo pegado al cuerpo puede separarse sin estirar la piel del torso, y el hueco que deja se rellena con los colores de alrededor.
- **Deformación** (`src/mesh.js`, `src/renderer.js`): cada capa tiene una malla con pesos de skinning (cada vértice sigue a los huesos más cercanos) y la GPU la deforma con WebGL en cada fotograma.
- **Cara** (`src/face.js`): MediaPipe Face Landmarker da 478 puntos de la cara del video y del personaje. Cada
  fotograma se compara con el más neutro de la toma tras quitar la pose de la cabeza, y esas diferencias se aplican a
  la malla facial del personaje. El interior de la boca (dientes, lengua) sale del video, recoloreado con los labios y
  la piel del personaje.
- **Encuadre y cortes** (`src/camera.js`, `src/filters.js`): la cámara se ajusta para mostrar lo mismo que el video;
  un detector de cambios de plano reinicia suavizados, referencias y cámara en cada corte. El suavizado usa un filtro
  One Euro (poco retraso en movimientos rápidos, sin temblor en reposo).
- **Ajuste manual**: si la detección no es perfecta, arrastra los puntos del esqueleto en el panel del personaje.

## Consejos

- Usa imágenes del personaje de frente, de cuerpo completo y con los brazos algo separados del cuerpo (lo que queda tapado por un brazo se rellena, pero se inventa).
- En el video, la persona debe verse con buena luz; en planos de cuerpo entero, sin ropa que tape las piernas.
- Para animar la cara, el personaje debe tener la cara visible y más o menos de frente.
- Los PNG con fondo transparente dan los mejores resultados.
- Si el personaje se desplaza demasiado, desactiva "Seguir desplazamiento" o pulsa "Recalibrar posición".
