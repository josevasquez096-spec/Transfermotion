# Transfer Motion 🕺

> **Nuevo:** en [`agentes-ia/`](agentes-ia/README.md) está la **Suite Pilot IA**: cinco agentes de IA de escritorio
> (`.exe` para Windows, en español, inglés y francés) para Excel, Power BI, Word, presentaciones y reclamaciones de
> fraude, más **IcePilot**, un generador de icebreakers y juegos para reuniones de Teams, y **MailPilot**, un agente
> para Outlook (carpetas, búsqueda avanzada, etiquetas, reglas, corrección de inglés y detección de phishing), y
> **MoreInfo Pilot**, que crea el `CASE,MOREINFO.pdf` del Fraud Package con las capturas. Los tres últimos funcionan
> sin internet.

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

## IA avanzada (Wan 2.2 Animate en fal.ai)

La animación del navegador mueve los píxeles de la foto: no puede inventar lo que no está (labios cerrados sobre una
sonrisa, el otro lado de la cara…). Para un reemplazo realista, el panel **4 · IA avanzada** manda el video y la foto a
[Wan 2.2 Animate](https://fal.ai/models/fal-ai/wan/v2.2-14b/animate/move) en fal.ai, que genera cada fotograma de nuevo:

- **Mi foto hace lo del video**: tu foto con el movimiento, los gestos y la boca del video.
- **Poner mi foto en el video**: la persona del video se sustituye por la de tu foto, con el fondo del video.

Tarda unos minutos y fal.ai cobra por segundo de video (aprox. $0.04/s en 480p, $0.08/s en 720p; consulta su página).
Usa fotos tuyas o de personas que estén de acuerdo.

### Configuración (una sola vez)

1. Crea una cuenta en [fal.ai](https://fal.ai), añade saldo y crea una clave en **Dashboard → Keys**.
2. En Vercel: tu proyecto → **Settings → Environment Variables**, añade:
   - `FAL_KEY`: la clave de fal.ai.
   - `TM_PASSWORD`: una contraseña que tú elijas. La app la pide antes de generar, para que nadie más gaste tu saldo.
3. Vuelve a publicar (**Deployments → Redeploy**). En la app, escribe la contraseña en el panel 4.

La clave nunca llega al navegador: queda en la función `api/fal/proxy.js`, que solo deja pasar las llamadas a Wan 2.2
Animate y la subida de archivos. Los videos se suben directamente a fal.ai (no pasan por Vercel).

Para probarlo en local, crea `.env.local` con `FAL_KEY=...` y `TM_PASSWORD=...` y ejecuta `npm run dev`.

## Estudio de voz y música (`studio.html`)

Desde la pestaña **🎤 Voz y música** (usa la misma configuración de fal.ai que la IA avanzada de video):

1. **Tu voz**: graba 10–30 s leyendo la frase de consentimiento (o sube un audio, marcando que es tu voz o que
   tienes permiso). Se guarda solo en tu dispositivo.
2. **Hablar con tu voz**: escribe un texto y se lee con tu voz (Chatterbox multilingüe, 23 idiomas).
   ≈ $0.025 por cada 1000 caracteres.
3. **Cover con tu voz**: sube una canción; Demucs separa la voz de la música (≈ $0.0007/s), Chatterbox HD cambia la voz
   por la tuya en fragmentos cortados en los silencios, y la mezcla final se hace en el navegador (puedes ajustar el
   volumen de la voz sin volver a pagar). Opción «Solo separar» para karaoke. Experimental: el modelo de voz está pensado
   para el habla y en notas muy sostenidas puede perder la melodía.
4. **Crear una canción**: elige estilo (reguetón, bachata, corridos, rock, lo-fi…), ánimo y voz, y:
   - **Con mi letra**: MiniMax Music 2 (≈ $0.03 por canción).
   - **La IA escribe la letra**: Sonauto v2.
   - **Instrumental**: ACE-Step (≈ $0.012 por minuto).
   Con **«Cantarla con mi voz»** la canción creada pasa directamente al cover con tu voz.

Precios aproximados según fal.ai y terceros; el real lo marca fal.ai. Usa solo tu voz o la de personas que te hayan dado
permiso, y respeta los derechos de autor de las canciones que versiones.

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
