# MoreInfo Pilot para Word (VBA)

*Created by Jose Vasquez.* Versión de MoreInfo Pilot que funciona **dentro de Word**, sin instalar ningún programa y sin internet. Hace lo mismo que el `.exe`:

- **MoreInfo:** captura pantallas y las agrupa en tus secciones, que se guardan para cada caso nuevo.
  - Pegas cada captura con Ctrl+V, o con **captura automática**: cada Win+Shift+S se agrega sola.
  - Se crea `CASE,MOREINFO.pdf` con Word, o una pestaña «Additional info» en el Excel de transacciones.
- **No Pay Decision Letter:**
  - Se llena dentro de la app desde tus plantillas con nombre (una por producto o idioma), con sus listas desplegables.
  - El nombre del cliente se escribe una sola vez.
  - La dirección completa se pega en una línea y se reparte en sus campos.
  - Admite varias razones, y ninguna se puede repetir.
  - Tiene vista previa en PDF, y la app avisa si la carta no se revisó antes de subirla.
- **Otros documentos del caso:**
  - Se agregan con Examinar, o copiando archivos en el Explorador y pulsando Pegar.
  - Word e imágenes se guardan como PDF; Excel, TXT y correos conservan su formato.
- **Subida automática:**
  - El MoreInfo y los documentos van al folder del caso; la carta va a sus folders (por ejemplo, dos).
  - Los archivos se numeran `CASE,MOREINFO1`, `CASE,MOREINFO2`… sin sobrescribir nada.
  - No queda ninguna copia local.

## Instalación (una sola vez, unos 5 minutos)

Solo necesitas los archivos de esta carpeta: `MIText.bas`, `MIPilot.bas`, `MICtl.cls`, `MIMain.cls`, `MILetter.cls` y `MIForm_code.txt`.

1. **Crear la plantilla**
   1. Abre Word y crea un documento en blanco.
   2. Ve a **Archivo > Guardar como**.
   3. En Tipo elige **Plantilla de Word habilitada para macros (\*.dotm)**.
   4. Nómbrala `MoreInfoPilot.dotm` y guárdala, por ejemplo en Documentos.
2. **Abrir el editor de VBA**
   1. Pulsa **Alt+F11**.
   2. En el panel *Proyecto* (izquierda), haz clic en el proyecto de **MoreInfoPilot**; no en *Normal*.
3. **Crear el formulario en blanco**
   1. Ve al menú **Insertar > UserForm**.
   2. Pulsa **F4**. En la ventana *Propiedades*, cambia **(Name)** de `UserForm1` a **`MIForm`**.
   3. Pulsa **F7** para abrir el código del formulario y borra lo que tenga.
   4. Pega todo el contenido de `MIForm_code.txt`.
4. **Importar los módulos**
   1. Ve a **Archivo > Importar archivo…** (Ctrl+M).
   2. Importa uno por uno: `MIText.bas`, `MIPilot.bas`, `MICtl.cls`, `MIMain.cls` y `MILetter.cls`.
5. **Compilar:** ve al menú **Depurar > Compilar** (el nombre del proyecto aparece al lado).
   - Si no aparece ningún mensaje, todo está bien.
   - Si aparece un error, toma una captura que muestre el mensaje y la línea marcada, y envíamela.
6. **Probar**
   1. Haz clic dentro de `Sub MoreInfoPilot` (está en el módulo `MIPilot`).
   2. Pulsa **F5**. Se abre la ventana de MoreInfo Pilot.
7. **Guardar:** pulsa **Ctrl+S** y cierra Word.
8. **Dejarlo siempre disponible**
   1. Copia `MoreInfoPilot.dotm` en la carpeta de inicio de Word: pega `%APPDATA%\Microsoft\Word\STARTUP` en la barra de direcciones del Explorador.
   2. Abre Word. En la pestaña **Complementos** aparece el botón **MoreInfo Pilot**.
   3. También puedes abrirlo con Alt+F8 > `MoreInfoPilot` > Ejecutar.

**Para otros analistas:** basta con copiar `MoreInfoPilot.dotm` en su carpeta `%APPDATA%\Microsoft\Word\STARTUP`. No tienen que repetir la instalación.

## Primer uso

1. **Folders & options:**
   - Elige el folder del MoreInfo y los documentos.
   - Agrega los folders de la carta (Add folder…).
   - Crea tus secciones, por ejemplo Customer profile, Cards y Claim details.
2. **No Pay Decision Letter & documents:** con **Add template (.docx)…** agrega cada plantilla en blanco y dale un nombre.
3. **MoreInfo package:**
   1. Escribe el Case #.
   2. Elige la sección.
   3. Pega las capturas. Si marcas *Auto-add every new screenshot copied*, cada Win+Shift+S se agrega sola a la sección elegida.
4. Llena la carta y agrega los demás documentos. Luego pulsa **Create and save**.

## Si algo falla

Cada error muestra un mensaje con el número de error y el **paso** en el que ocurrió (*Step: …*). Pulsa **Ctrl+C** sobre el mensaje para copiarlo y envíamelo.

Los ajustes se guardan para tu usuario de Windows y las plantillas se guardan en `%APPDATA%\MoreInfoPilot\Templates`.

## Para desarrolladores

- `tests/check_vba.py`: revisión estática; detecta variables sin declarar, bloques sin cerrar, argumentos y `Set`.
- `tests/run_libreoffice.py`: ejecuta en LibreOffice Basic el código que no depende de Word (direcciones, numeración, fechas) y lo compara con la versión Python.

Ambas pruebas corren con `pytest tests/test_vba.py`.
