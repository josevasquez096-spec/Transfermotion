# Suite Pilot IA · agentes de IA para negocios

Ocho aplicaciones de escritorio (`.exe` para Windows) en **español, inglés y francés**: cinco agentes con IA de
Claude (Anthropic) para trabajar más rápido con Excel, Power BI, Word, PowerPoint y reclamaciones de fraude,
**IcePilot**, un generador de icebreakers y juegos para reuniones de Teams, y **MailPilot**, un agente para Outlook
(carpetas, búsqueda avanzada, etiquetas, reglas, corrección de inglés y seguridad) y **MoreInfo Pilot** (en inglés),
que arma el archivo MoreInfo del Fraud Package con las capturas de pantalla. IcePilot, MailPilot y MoreInfo Pilot
funcionan **sin internet**. El idioma se cambia en cualquier momento desde la cabecera de cada app.

| App | Para qué sirve | Funciones sin conexión | Funciones con IA ✨ |
| --- | --- | --- | --- |
| **DataPilot** (Excel) | Limpiar, analizar y documentar libros | Perfil de columnas, limpieza (espacios, duplicados, números y fechas en texto, «NORTE/Norte»), combinar varios archivos en uno, tablas dinámicas, **traductor de fórmulas EN↔ES↔FR**, informe Excel con formato y gráfico | Preguntas en lenguaje natural («ventas por región y trimestre»), crear y explicar fórmulas, conclusiones ejecutivas |
| **BIPilot** (Power BI) | Preparar el modelo y escribir DAX/M | Detecta hechos y dimensiones, propone relaciones 1:*, revisa la calidad (claves huérfanas o duplicadas), 12 medidas DAX habituales (YTD, interanual, media móvil…), tabla calendario en DAX / M / Excel, consulta M de limpieza, **tema .json** con tu color de marca | Medidas DAX a medida, consultas Power Query, explicación de DAX |
| **DocPilot** (Word) | Redactar y automatizar documentos | Estructuras de propuesta, informe, carta, acta, procedimiento y correo; análisis de legibilidad; **combinación de correspondencia** ({{Campo}} + Excel → un .docx por fila o uno solo) | Redactar con tus datos, resumir, corregir, cambiar el tono, traducir, extraer tareas, lenguaje claro |
| **SlidePilot** (PowerPoint) | Presentaciones en minutos | Esquema de texto → .pptx con 6 temas y 8 diseños (viñetas, KPI, gráfico nativo, columnas, línea de tiempo, cita, tabla, separador), Word → diapositivas, Excel → gráficos, vista previa | Presentación completa desde un tema o tu material, con notas del orador |
| **IcePilot** (icebreakers para Teams) | Juegos personalizables para reuniones | 12 juegos: quiz tipo Kahoot, verdadero/falso, trivia por categorías, ahorcado, adivina con emojis, palabras desordenadas, serpientes y escaleras por equipos, ruleta, bingo, sopa de letras, dos verdades y una mentira, ¿qué prefieres? · contenido de ejemplo de **fraudes recurrentes** y rompehielos · exporta a HTML, PowerPoint y Word | Crear preguntas o palabras sobre cualquier tema (opcional, requiere internet) |
| **MailPilot** (Outlook) | Ordenar el correo, encontrar lo importante y escribir mejor en inglés | Carpetas de tu buzón, **buzones compartidos** y archivos .pst · **búsqueda avanzada** (palabras, frases, `from:`, `asunto:`, `has:card`, `is:phishing`, fechas, tamaño, expresiones regulares…) · **etiquetas** (categorías de Outlook) y etiquetado en lote · **reglas** que se prueban antes de aplicarlas y se pueden crear como reglas de Outlook · **corrector de inglés** (ortografía, gramática, errores típicos de hispanohablantes, estilo y tono) que corrige el borrador abierto sin perder el formato · frases y plantillas · **phishing**, tarjetas e IBAN enviados en claro, índice de reclamaciones | Mejorar o traducir un correo al inglés con el tono elegido, resumir un correo y proponer respuesta, sugerir reglas para ordenar el buzón |
| **MoreInfo Pilot** (Fraud Package, en inglés) | Crear el MoreInfo del caso con las capturas | Pegar capturas (Ctrl+V o automático al usar Win+Shift+S) por sección (transacciones, cliente, tarjetas, perfil, reclamación) → Word → **`CASE,MOREINFO.pdf`** (con Word si está instalado o con su propio generador) · modo **Excel**: añade una pestaña con las capturas al archivo de transacciones descargado · documentos extra numerados (`CASE,MOREINFO1.pdf`, `CASE,MOREINFO2.pdf`…) · copia automática a las carpetas configuradas (de red o locales), opcionalmente en una subcarpeta por caso | — |
| **FraudPilot** (reclamaciones de fraude) | Registrar, priorizar y responder reclamaciones | Tipología (phishing, SIM swap, toma de cuenta, tarjeta clonada, estafa con pago autorizado, disputa comercial…), prioridad, señales de alerta, acciones, documentos y **plazos configurables**; registro de casos con vencimientos; **cartas** en 3 idiomas; **análisis masivo** (duplicados, reclamantes recurrentes, avisos tardíos, comercios con picos = posible punto de compromiso) | Análisis del relato del cliente (hechos, inconsistencias, preguntas), mejora de cartas, informe de patrones |

Todo lo marcado sin ✨ funciona **sin internet y sin clave de IA**. Cada app incluye datos de ejemplo
(botón «Cargar ejemplo») para probarla al momento.

## Descargar los .exe

Los ejecutables se crean automáticamente en GitHub (flujo `.github/workflows/agentes-ia.yml`):

1. En GitHub, abre **Actions → «Agentes IA (.exe para Windows)»** y entra en la última ejecución correcta.
2. Descarga el artefacto **PilotSuite-Windows** (un .zip con los 8 `.exe`).
3. Si subes una etiqueta `agentes-v1.0.0`, los `.exe` también se publican en **Releases**.

Antes de publicarse, cada `.exe` se prueba en Windows con `--selftest` (genera sus archivos de ejemplo).

Cada `.exe` es un único archivo (≈60 MB) que no necesita Python. La primera vez Windows puede mostrar
«Windows protegió su PC» porque los ejecutables no están firmados: pulsa **Más información → Ejecutar de todas formas**.

## Activar la IA

1. Crea una clave en [console.anthropic.com](https://console.anthropic.com) → *API Keys* (necesita saldo).
2. En cualquiera de las apps: **⚙ Configuración IA** → pega la clave → *Probar conexión* → *Guardar*.
   La configuración se comparte entre todas las apps y se guarda solo en tu equipo
   (`%APPDATA%\PilotSuite\settings.json`). También se puede usar la variable de entorno `ANTHROPIC_API_KEY`.
3. Modelo: `claude-opus-5-5` (por defecto, el más capaz), `claude-sonnet-5-5` (más económico) o
   `claude-haiku-5-5` (el más rápido y barato). Precio aproximado por millón de tokens de entrada/salida:
   4 $/20 $, 2 $/10 $ y 0,10 $/0,50 $; una consulta típica usa unos pocos miles de tokens. Consulta
   los precios vigentes en anthropic.com.

**Privacidad.** Solo se envía a la IA lo necesario: nombres de columnas y estadísticas (no las filas completas)
en DataPilot y BIPilot, el texto que tú indiques en DocPilot, SlidePilot y FraudPilot, y en MailPilot solo el correo
que pidas mejorar o resumir (o estadísticas de remitentes y carpetas para sugerir reglas). Con la opción
«Anonimizar datos personales» (activada por defecto), correos, teléfonos, tarjetas (validadas con Luhn), IBAN,
números de cuenta y el nombre del cliente se sustituyen por marcadores como `[CLIENTE_1]` antes de enviarlos y se
restauran en la respuesta. Revisa siempre el contenido generado por IA.

## IcePilot: juegos para reuniones en Teams (red interna del banco)

1. Elige el juego, carga el contenido de ejemplo («Fraudes recurrentes» o «Rompehielos de equipo») o escribe el tuyo
   en la tabla (doble clic para editar) o impórtalo desde Excel.
2. En **🎨 Personalizar** cambia título, icono, colores, idioma del juego, equipos, sonidos y las opciones de cada
   juego (tiempo por pregunta, puntos, tamaño del tablero, modo de serpientes y escaleras, cartones de bingo…).
3. **▶ Probar en el navegador** y, cuando te guste, guárdalo como **HTML**, **PowerPoint** o **Word**.

| Formato | Para qué |
| --- | --- |
| HTML (todos los juegos) | Un único archivo que se abre en Edge o Chrome. Compártelo en Teams (Compartir → Ventana) y usa la pantalla completa. Marcador por equipos, temporizador, sonidos y confeti. |
| PowerPoint (quiz, verdadero/falso, trivia, emojis, palabras, ruleta, dos verdades, ¿qué prefieres?) | Para presentar con PowerPoint Live: cada pregunta tiene su diapositiva de respuesta y las soluciones van en las notas del orador. |
| Word (todos) | Guía del moderador con reglas y respuestas, cartones de bingo para imprimir o enviar, sopa de letras con clave, hojas de respuestas. |

**Pensado para PCs sin internet.** Los juegos no cargan fuentes, imágenes ni scripts externos y llevan una política
de seguridad (CSP) que bloquea cualquier conexión: funcionan desde una carpeta local o compartida de la red del
banco y no guardan ni envían datos de los participantes. En el bingo y la sopa de letras, el mismo archivo `.html`
se envía por el chat de Teams y cada persona lo abre en su PC (el bingo pregunta si eres moderador o jugador y tu
número de cartón). La única función que necesita internet es la creación de contenido con IA, que es opcional.

Los proyectos se guardan como `.icepilot.json` para reutilizarlos o compartirlos con otros moderadores.

**Ejemplos listos para usar:** en [`ejemplos/icebreakers/es/`](ejemplos/icebreakers/es) están los 12 juegos sobre
fraudes recurrentes ya generados (más el quiz en PowerPoint y los cartones de bingo en Word). Descarga el `.html` y
ábrelo con doble clic. Para regenerarlos o crearlos en otro idioma: `python make_examples.py en`.

## MailPilot: agente para Outlook (red interna del banco)

**Requisitos.** Windows con **Outlook clásico** (el de Microsoft 365 / Office) abierto o configurado. MailPilot se
conecta a él por COM, como una macro: no usa internet, ni Microsoft Graph, ni contraseñas, y trabaja con lo que el
propio Outlook ya tiene (buzón de Exchange, buzones compartidos y archivos .pst). El «nuevo Outlook» y Outlook en la
web no permiten esta conexión. Sin Outlook (o para probar) usa **Modo demostración**, con un buzón ficticio de un
equipo de reclamaciones: phishing, contracargos, un número de tarjeta enviado en claro y borradores en inglés con
errores.

| Pestaña | Qué hace |
| --- | --- |
| 📁 Buzón y carpetas | Árbol de todos los buzones (propio, compartidos, .pst) con no leídos; crear, renombrar, mover y eliminar carpetas; **abrir un buzón compartido** por su dirección; lista de correos con vista previa que avisa de phishing y de tarjetas escritas en el correo; mover, etiquetar, marcar como leído o para seguimiento, eliminar, guardar como .msg, guardar adjuntos, exportar a Excel. |
| 🔍 Buscar y filtrar | Búsqueda tipo Gmail en carpeta, subcarpetas, buzón o todos los buzones, con filtros rápidos, búsquedas guardadas y resaltado de lo encontrado (ver «Ayuda de búsqueda» en la app). |
| 🏷 Etiquetas | Crear, renombrar (actualizando los correos), cambiar color y eliminar categorías; etiquetar en lote todo lo que cumpla una búsqueda. |
| ⚙ Reglas | Reglas locales «búsqueda + acciones» (mover, etiquetar, marcar como leído o para seguimiento) que se **prueban sin cambiar nada** y luego se ejecutan; si la búsqueda es sencilla se crean también como **reglas de Outlook** que se aplican solas a los correos nuevos. |
| ✍ Redacción en inglés | Trae el borrador abierto en Outlook, marca los errores mientras escribes (ortografía, gramática, errores típicos de hispanohablantes, puntuación, estilo, tono y claridad) con su explicación en tu idioma, y **aplica las correcciones en el mismo borrador** sin tocar formato, firma ni el historial citado. Frases útiles y plantillas de reclamaciones en inglés. |
| 🛡 Análisis y seguridad | Resumen del buzón y sugerencias para ordenarlo, **detección de phishing** (dominios que imitan al del banco, suplantación de departamentos, enlaces engañosos, adjuntos peligrosos, fraude del CEO…), **datos sensibles** enviados en claro (tarjetas validadas con Luhn e IBAN, siempre enmascarados en pantalla) e **índice de reclamaciones** por número de caso; todo exportable a Excel. |

**Ejemplos de búsqueda:** `has:claim is:unread newer:7d` · `from:visa.com OR from:mastercard.com` ·
`asunto:reclamación -is:read` · `is:external has:link "verify your account"` · `has:card` · `size:>5mb` ·
`re:"R-\d{4}-\d+"`. Los campos se pueden escribir en español, inglés o francés (`de:`, `from:`, `expediteur:`).

**Seguridad y privacidad.** Todo se procesa en el PC: MailPilot no envía correos ni guarda copias; sus reglas,
búsquedas guardadas y diccionario personal están en `%APPDATA%\PilotSuite\mailpilot.json`. El corrector de inglés
funciona sin conexión; solo los botones ✨ usan internet. Según la política de seguridad de Outlook, la primera
vez puede aparecer un aviso «Un programa intenta obtener acceso…»: acéptalo o pide a TI que permita MailPilot.
Las búsquedas en el cuerpo de buzones muy grandes pueden tardar; el periodo («Últimos 90 días»), el ámbito y la
opción «Mayúsculas y acentos exactos» (que deja filtrar primero a Outlook) las aceleran, y siempre se pueden detener.

## MoreInfo Pilot: archivo MoreInfo del Fraud Package

1. En **⚙ Folders & options** añade las carpetas donde se guarda el paquete (por ejemplo `\\servidor\Fraude\Packages`)
   y, si quieres, una subcarpeta por caso. Las opciones se guardan en `%APPDATA%\PilotSuite\moreinfo.json`.
2. Escribe el **Case #**, elige la sección y pega cada captura con **Ctrl+V** (o activa *Auto-add* y ve haciendo
   Win+Shift+S en cada pantalla o aplicación: cada captura nueva se añade sola). Puedes poner un pie a cada una.
3. Elige la salida: **Word → PDF** o **Excel** (elige el archivo de transacciones descargado; se añade la pestaña
   «MoreInfo» con las capturas de perfil, tarjetas y reclamación). Añade documentos extra si los hay.
4. **Create and save**: se crea `CASE,MOREINFO.pdf` (o `.xlsx`) y los extras como `CASE,MOREINFO1…`, y se copian a
   todas las carpetas. Si el caso ya tiene un MoreInfo en alguna carpeta, el número sigue (`CASE,MOREINFO1.pdf`…),
   nunca se sobrescribe nada. Siempre queda una copia en la carpeta de trabajo (`Documents\MoreInfo`).

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
python DataPilot.py      # o BIPilot.py, DocPilot.py, SlidePilot.py, FraudPilot.py, IcePilot.py, MailPilot.py, MoreInfoPilot.py
```

## Crear los .exe en tu PC (Windows)

```bash
cd agentes-ia
python -m pip install -r requirements-dev.txt
python build_exe.py              # las ocho apps → carpeta dist\
python build_exe.py FraudPilot   # solo una
dist\FraudPilot.exe --selftest   # autoprueba sin interfaz (código de salida 0 = correcto)
```

## Pruebas

```bash
python -m pytest -q              # en Linux sin pantalla: xvfb-run -a python -m pytest -q
```

Cubren la lógica de las siete apps, el cliente de IA (con un Claude simulado, sin coste), la anonimización,
que todas las traducciones existan en los tres idiomas con los mismos campos, el arranque de cada app
cambiando de idioma, que los juegos HTML no contengan direcciones externas y la sintaxis de su JavaScript
(con Node.js). Si Playwright está instalado, también se juega a cada juego en Chromium. La conexión de MailPilot
con Outlook se prueba con un modelo de objetos de Outlook y Word simulado (`tests/fake_outlook.py`), y el
corrector de inglés con frases correctas (sin falsos positivos) y con errores típicos.

## Estructura

```
agentes-ia/
├── DataPilot.py … MoreInfoPilot.py  puntos de entrada (uno por .exe)
├── build_exe.py                    crea los .exe con PyInstaller
├── suite/
│   ├── ai.py                       cliente de Claude (salidas JSON estructuradas, respaldo ante rechazos)
│   ├── i18n.py, settings.py        idiomas y configuración compartida
│   ├── privacy.py                  anonimización de datos personales
│   ├── ui.py, icons.py             ventana base, widgets e iconos
│   ├── tabular.py, samples.py      lectura/escritura de Excel y datos de ejemplo
│   ├── selftest.py                 autoprueba de los ejecutables
│   ├── datapilot/ bipilot/ docpilot/ slidepilot/ fraudpilot/   logic.py (sin interfaz), strings.py, app.py
│   ├── icepilot/                   games.py (catálogo y tableros), build.py + web_*.py (juegos HTML),
│   │                               office.py (PowerPoint/Word), content.py (contenido de ejemplo)
│   ├── moreinfo/                   logic.py (Word, PDF, Excel, numeración y copia a carpetas), app.py
│   └── mailpilot/                  query.py (búsqueda), english.py (corrector), detectors.py (phishing y datos
│                                   sensibles), backend_outlook.py (COM) y backend_demo.py, rules.py, analysis.py
└── tests/
```

---

### English

Eight desktop apps (Windows `.exe`) in **Spanish, English and French**: **DataPilot** (Excel cleaning, natural
language questions, EN/ES/FR formula translator, reports), **BIPilot** (Power BI model checks, DAX measures,
calendar table, Power Query, themes), **DocPilot** (Word drafting, proofreading, translation, mail merge),
**SlidePilot** (PowerPoint decks from a topic, an outline, a Word file or an Excel) and **FraudPilot** (fraud claim
intake, typology, priority, deadlines, letters, case log and batch triage with point-of-compromise detection), plus
**IcePilot**, an offline generator of 12 customizable icebreaker games for Teams meetings (Kahoot-style quiz, trivia,
hangman, emoji puzzles, snakes and ladders, bingo, word search…) exported as self-contained HTML, PowerPoint or Word,
and **MailPilot**, an offline agent for classic Outlook: folders and shared mailboxes, Gmail-style advanced search,
tags (categories), testable rules that can become Outlook rules, an English grammar and style checker that fixes the
open draft in place, phishing and sensitive-data detection, and a claims index, and **MoreInfo Pilot** (English):
paste the claim screenshots and get `CASE,MOREINFO.pdf` (or a new tab in the transaction Excel file), numbered extra
documents and automatic copies to the configured folders.
Offline features work without an API key; ✨ features use Claude — add your Anthropic API key in **⚙ AI settings**.
Download the `.exe` files from **Actions → PilotSuite-Windows** or build them with `python build_exe.py`.

### Français

Huit applications de bureau (`.exe` Windows) en **espagnol, anglais et français** : **DataPilot** (nettoyage Excel,
questions en langage naturel, traducteur de formules, rapports), **BIPilot** (modèle Power BI, mesures DAX,
calendrier, Power Query, thèmes), **DocPilot** (rédaction Word, correction, traduction, publipostage),
**SlidePilot** (présentations PowerPoint à partir d'un sujet, d'un plan, d'un Word ou d'un Excel) et **FraudPilot**
(réclamations de fraude : typologie, priorité, délais, courriers, suivi des dossiers et analyse de masse), ainsi
qu'**IcePilot**, un générateur hors ligne de 12 jeux brise-glace personnalisables pour les réunions Teams (quiz façon
Kahoot, trivia, pendu, emojis, serpents et échelles, bingo, mots mêlés…) exportés en HTML autonome, PowerPoint ou Word,
et **MailPilot**, un agent hors ligne pour Outlook classique : dossiers et boîtes partagées, recherche avancée façon
Gmail, catégories, règles testables convertibles en règles Outlook, correcteur d'anglais qui corrige le brouillon
ouvert sans perdre la mise en forme, détection d'hameçonnage et de données sensibles, index des réclamations.
Les fonctions hors ligne marchent sans clé ; les fonctions ✨ utilisent Claude — ajoutez votre clé API Anthropic
dans **⚙ Paramètres IA**. Téléchargez les `.exe` depuis **Actions → PilotSuite-Windows** ou créez-les avec
`python build_exe.py`.
