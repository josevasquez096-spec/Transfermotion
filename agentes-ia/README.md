# Suite Pilot IA · 5 agentes de IA para negocios

Cinco aplicaciones de escritorio (`.exe` para Windows) en **español, inglés y francés**, con IA de Claude
(Anthropic) para trabajar más rápido con Excel, Power BI, Word, PowerPoint y reclamaciones de fraude.
El idioma se cambia en cualquier momento desde la cabecera de cada app.

| App | Para qué sirve | Funciones sin conexión | Funciones con IA ✨ |
| --- | --- | --- | --- |
| **DataPilot** (Excel) | Limpiar, analizar y documentar libros | Perfil de columnas, limpieza (espacios, duplicados, números y fechas en texto, «NORTE/Norte»), combinar varios archivos en uno, tablas dinámicas, **traductor de fórmulas EN↔ES↔FR**, informe Excel con formato y gráfico | Preguntas en lenguaje natural («ventas por región y trimestre»), crear y explicar fórmulas, conclusiones ejecutivas |
| **BIPilot** (Power BI) | Preparar el modelo y escribir DAX/M | Detecta hechos y dimensiones, propone relaciones 1:*, revisa la calidad (claves huérfanas o duplicadas), 12 medidas DAX habituales (YTD, interanual, media móvil…), tabla calendario en DAX / M / Excel, consulta M de limpieza, **tema .json** con tu color de marca | Medidas DAX a medida, consultas Power Query, explicación de DAX |
| **DocPilot** (Word) | Redactar y automatizar documentos | Estructuras de propuesta, informe, carta, acta, procedimiento y correo; análisis de legibilidad; **combinación de correspondencia** ({{Campo}} + Excel → un .docx por fila o uno solo) | Redactar con tus datos, resumir, corregir, cambiar el tono, traducir, extraer tareas, lenguaje claro |
| **SlidePilot** (PowerPoint) | Presentaciones en minutos | Esquema de texto → .pptx con 6 temas y 8 diseños (viñetas, KPI, gráfico nativo, columnas, línea de tiempo, cita, tabla, separador), Word → diapositivas, Excel → gráficos, vista previa | Presentación completa desde un tema o tu material, con notas del orador |
| **FraudPilot** (reclamaciones de fraude) | Registrar, priorizar y responder reclamaciones | Tipología (phishing, SIM swap, toma de cuenta, tarjeta clonada, estafa con pago autorizado, disputa comercial…), prioridad, señales de alerta, acciones, documentos y **plazos configurables**; registro de casos con vencimientos; **cartas** en 3 idiomas; **análisis masivo** (duplicados, reclamantes recurrentes, avisos tardíos, comercios con picos = posible punto de compromiso) | Análisis del relato del cliente (hechos, inconsistencias, preguntas), mejora de cartas, informe de patrones |

Todo lo marcado sin ✨ funciona **sin internet y sin clave de IA**. Cada app incluye datos de ejemplo
(botón «Cargar ejemplo») para probarla al momento.

## Descargar los .exe

Los ejecutables se crean automáticamente en GitHub (flujo `.github/workflows/agentes-ia.yml`):

1. En GitHub, abre **Actions → «Agentes IA (.exe para Windows)»** y entra en la última ejecución correcta.
2. Descarga el artefacto **PilotSuite-Windows** (un .zip con los 5 `.exe`).
3. Si subes una etiqueta `agentes-v1.0.0`, los `.exe` también se publican en **Releases**.

Cada `.exe` es un único archivo (≈60 MB) que no necesita Python. La primera vez Windows puede mostrar
«Windows protegió su PC» porque los ejecutables no están firmados: pulsa **Más información → Ejecutar de todas formas**.

## Activar la IA

1. Crea una clave en [console.anthropic.com](https://console.anthropic.com) → *API Keys* (necesita saldo).
2. En cualquiera de las apps: **⚙ Configuración IA** → pega la clave → *Probar conexión* → *Guardar*.
   La configuración se comparte entre las cinco apps y se guarda solo en tu equipo
   (`%APPDATA%\PilotSuite\settings.json`). También se puede usar la variable de entorno `ANTHROPIC_API_KEY`.
3. Modelo: `claude-opus-5-5` (por defecto, el más capaz), `claude-sonnet-5-5` (más económico) o
   `claude-haiku-5-5` (el más rápido y barato). Precio aproximado por millón de tokens de entrada/salida:
   4 $/20 $, 2 $/10 $ y 0,10 $/0,50 $; una consulta típica usa unos pocos miles de tokens. Consulta
   los precios vigentes en anthropic.com.

**Privacidad.** Solo se envía a la IA lo necesario: nombres de columnas y estadísticas (no las filas completas)
en DataPilot y BIPilot, y el texto que tú indiques en DocPilot, SlidePilot y FraudPilot. Con la opción
«Anonimizar datos personales» (activada por defecto), correos, teléfonos, tarjetas (validadas con Luhn), IBAN,
números de cuenta y el nombre del cliente se sustituyen por marcadores como `[CLIENTE_1]` antes de enviarlos y se
restauran en la respuesta. Revisa siempre el contenido generado por IA.

## FraudPilot: notas importantes

- Es una **herramienta de apoyo a la decisión**: la resolución final la toma un analista.
- Los plazos (acuse, abono provisional, resolución), el umbral de aviso tardío y el de importe alto se ajustan en
  **Casos → Plazos** según la normativa de cada país y la política de la entidad. Los valores iniciales
  (2 días hábiles, 10 días hábiles, 45 días naturales) son solo un punto de partida.
- Los códigos de contracargo que se sugieren (Visa 10.x / 13.1, Mastercard 4837 / 4855) son orientativos.
- Los casos se guardan en una base SQLite local: `%APPDATA%\PilotSuite\fraudpilot_cases.db`.
- El análisis masivo reconoce automáticamente columnas en español, inglés o francés (puedes corregir la asignación).

## Ejecutar desde el código (Windows, macOS o Linux)

```bash
cd agentes-ia
python -m pip install -r requirements.txt     # Python 3.10 o superior, con Tkinter
python DataPilot.py      # o BIPilot.py, DocPilot.py, SlidePilot.py, FraudPilot.py
```

## Crear los .exe en tu PC (Windows)

```bash
cd agentes-ia
python -m pip install -r requirements-dev.txt
python build_exe.py              # las cinco apps → carpeta dist\
python build_exe.py FraudPilot   # solo una
dist\FraudPilot.exe --selftest   # autoprueba sin interfaz (código de salida 0 = correcto)
```

## Pruebas

```bash
python -m pytest -q              # en Linux sin pantalla: xvfb-run -a python -m pytest -q
```

Cubren la lógica de las cinco apps, el cliente de IA (con un Claude simulado, sin coste), la anonimización,
que todas las traducciones existan en los tres idiomas con los mismos campos, y el arranque de cada app
cambiando de idioma.

## Estructura

```
agentes-ia/
├── DataPilot.py … FraudPilot.py   puntos de entrada (uno por .exe)
├── build_exe.py                    crea los .exe con PyInstaller
├── suite/
│   ├── ai.py                       cliente de Claude (salidas JSON estructuradas, respaldo ante rechazos)
│   ├── i18n.py, settings.py        idiomas y configuración compartida
│   ├── privacy.py                  anonimización de datos personales
│   ├── ui.py, icons.py             ventana base, widgets e iconos
│   ├── tabular.py, samples.py      lectura/escritura de Excel y datos de ejemplo
│   ├── selftest.py                 autoprueba de los ejecutables
│   └── datapilot/ bipilot/ docpilot/ slidepilot/ fraudpilot/   logic.py (sin interfaz), strings.py, app.py
└── tests/
```

---

### English

Five desktop AI agents (Windows `.exe`) in **Spanish, English and French**: **DataPilot** (Excel cleaning, natural
language questions, EN/ES/FR formula translator, reports), **BIPilot** (Power BI model checks, DAX measures,
calendar table, Power Query, themes), **DocPilot** (Word drafting, proofreading, translation, mail merge),
**SlidePilot** (PowerPoint decks from a topic, an outline, a Word file or an Excel) and **FraudPilot** (fraud claim
intake, typology, priority, deadlines, letters, case log and batch triage with point-of-compromise detection).
Offline features work without an API key; ✨ features use Claude — add your Anthropic API key in **⚙ AI settings**.
Download the `.exe` files from **Actions → PilotSuite-Windows** or build them with `python build_exe.py`.

### Français

Cinq agents IA de bureau (`.exe` Windows) en **espagnol, anglais et français** : **DataPilot** (nettoyage Excel,
questions en langage naturel, traducteur de formules, rapports), **BIPilot** (modèle Power BI, mesures DAX,
calendrier, Power Query, thèmes), **DocPilot** (rédaction Word, correction, traduction, publipostage),
**SlidePilot** (présentations PowerPoint à partir d'un sujet, d'un plan, d'un Word ou d'un Excel) et **FraudPilot**
(réclamations de fraude : typologie, priorité, délais, courriers, suivi des dossiers et analyse de masse).
Les fonctions hors ligne marchent sans clé ; les fonctions ✨ utilisent Claude — ajoutez votre clé API Anthropic
dans **⚙ Paramètres IA**. Téléchargez les `.exe` depuis **Actions → PilotSuite-Windows** ou créez-les avec
`python build_exe.py`.
