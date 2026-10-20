"""Traducciones. Cada clave tiene una tupla (español, inglés, francés)."""

import locale

LANGS = ("es", "en", "fr")
LANG_NAMES = {"es": "Español", "en": "English", "fr": "Français"}
# Nombre del idioma tal como se lo pedimos a la IA.
AI_LANG = {"es": "Spanish", "en": "English", "fr": "French"}


def detect_lang():
    """Idioma del sistema operativo si es uno de los tres; si no, inglés."""
    try:
        name = (locale.getlocale()[0] or "").lower()
    except ValueError:
        name = ""
    if name.startswith(("es", "spanish")):
        return "es"
    if name.startswith(("fr", "french")):
        return "fr"
    return "en"


class Translator:
    def __init__(self, *tables, lang="es"):
        self.table = {}
        for table in tables:
            self.table.update(table)
        self.lang = lang if lang in LANGS else "es"
        self.missing = set()  # claves pedidas sin traducción (las pruebas comprueban que quede vacío)

    def __call__(self, key, **kw):
        entry = self.table.get(key)
        if entry is None:
            self.missing.add(key)
            return key
        text = entry[LANGS.index(self.lang)]
        return text.format(**kw) if kw else text

    @property
    def ai_lang(self):
        return AI_LANG[self.lang]


COMMON = {
    "language": ("Idioma", "Language", "Langue"),
    "settings": ("⚙ Configuración IA", "⚙ AI settings", "⚙ Paramètres IA"),
    "settings_title": ("Configuración de la IA", "AI settings", "Paramètres de l'IA"),
    "api_key": ("Clave de API de Anthropic", "Anthropic API key", "Clé API Anthropic"),
    "show_key": ("Mostrar", "Show", "Afficher"),
    "model": ("Modelo", "Model", "Modèle"),
    "effort": ("Esfuerzo de razonamiento", "Reasoning effort", "Effort de raisonnement"),
    "effort_low": ("Bajo (rápido y barato)", "Low (fast, cheap)", "Faible (rapide, économique)"),
    "effort_medium": ("Medio (recomendado)", "Medium (recommended)", "Moyen (recommandé)"),
    "effort_high": ("Alto (más preciso)", "High (most accurate)", "Élevé (plus précis)"),
    "anonymize": (
        "Anonimizar datos personales antes de enviarlos a la IA",
        "Anonymize personal data before sending it to the AI",
        "Anonymiser les données personnelles avant de les envoyer à l'IA",
    ),
    "settings_hint": (
        "Crea tu clave en console.anthropic.com → API Keys. Se guarda solo en este equipo.\n"
        "Sin clave, las funciones sin conexión (marcadas sin ✨) siguen funcionando.",
        "Create your key at console.anthropic.com → API Keys. It is stored only on this computer.\n"
        "Without a key, offline features (those without ✨) keep working.",
        "Créez votre clé sur console.anthropic.com → API Keys. Elle reste sur cet ordinateur.\n"
        "Sans clé, les fonctions hors ligne (sans ✨) restent disponibles.",
    ),
    "test_connection": ("Probar conexión", "Test connection", "Tester la connexion"),
    "connection_ok": ("Conexión correcta ✔", "Connection OK ✔", "Connexion réussie ✔"),
    "save": ("Guardar", "Save", "Enregistrer"),
    "cancel": ("Cancelar", "Cancel", "Annuler"),
    "close": ("Cerrar", "Close", "Fermer"),
    "ai_on": ("✨ IA activa · {model}", "✨ AI on · {model}", "✨ IA active · {model}"),
    "ai_off": (
        "IA sin configurar · funciones sin conexión disponibles",
        "AI not configured · offline features available",
        "IA non configurée · fonctions hors ligne disponibles",
    ),
    "ready": ("Listo", "Ready", "Prêt"),
    "working": ("Trabajando…", "Working…", "Traitement…"),
    "ai_working": ("La IA está trabajando…", "The AI is working…", "L'IA travaille…"),
    "open": ("Abrir…", "Open…", "Ouvrir…"),
    "load_sample": ("Cargar ejemplo", "Load sample", "Charger un exemple"),
    "export": ("Exportar…", "Export…", "Exporter…"),
    "copy": ("Copiar", "Copy", "Copier"),
    "copied": ("Copiado al portapapeles", "Copied to clipboard", "Copié dans le presse-papiers"),
    "clear": ("Limpiar", "Clear", "Effacer"),
    "error": ("Error", "Error", "Erreur"),
    "done": ("Hecho", "Done", "Terminé"),
    "notice": ("Aviso", "Notice", "Avis"),
    "saved_to": ("Guardado en:\n{path}", "Saved to:\n{path}", "Enregistré sous :\n{path}"),
    "open_now": ("¿Abrir el archivo ahora?", "Open the file now?", "Ouvrir le fichier maintenant ?"),
    "no_data": ("Primero carga datos.", "Load some data first.", "Chargez d'abord des données."),
    "loaded_rows": (
        "{name}: {rows} filas × {cols} columnas",
        "{name}: {rows} rows × {cols} columns",
        "{name} : {rows} lignes × {cols} colonnes",
    ),
    "sheet": ("Hoja", "Sheet", "Feuille"),
    "choose_sheet": ("Elige la hoja", "Choose the sheet", "Choisissez la feuille"),
    "ok": ("Aceptar", "OK", "OK"),
    "need_text": ("Escribe primero el texto o la descripción.", "Type the text or description first.",
                  "Saisissez d'abord le texte ou la description."),
    "rows_shown": (
        "Mostrando {shown} de {total} filas",
        "Showing {shown} of {total} rows",
        "{shown} lignes affichées sur {total}",
    ),
    "ft_excel": ("Libros de Excel", "Excel workbooks", "Classeurs Excel"),
    "ft_csv": ("Archivos CSV", "CSV files", "Fichiers CSV"),
    "ft_word": ("Documentos de Word", "Word documents", "Documents Word"),
    "ft_pptx": ("Presentaciones de PowerPoint", "PowerPoint presentations", "Présentations PowerPoint"),
    "ft_text": ("Texto", "Text", "Texte"),
    "ft_json": ("JSON", "JSON", "JSON"),
    "ft_all": ("Todos los archivos", "All files", "Tous les fichiers"),
    "err_no_key": (
        "Esta función usa IA. Abre «⚙ Configuración IA» y pega tu clave de API de Anthropic.",
        "This feature uses AI. Open “⚙ AI settings” and paste your Anthropic API key.",
        "Cette fonction utilise l'IA. Ouvrez « ⚙ Paramètres IA » et collez votre clé API Anthropic.",
    ),
    "err_no_sdk": (
        "Falta la librería «anthropic». Instálala con: pip install anthropic",
        "The “anthropic” library is missing. Install it with: pip install anthropic",
        "La bibliothèque « anthropic » est absente. Installez-la : pip install anthropic",
    ),
    "err_auth": (
        "La clave de API no es válida o no tiene permisos.",
        "The API key is invalid or lacks permissions.",
        "La clé API est invalide ou n'a pas les droits nécessaires.",
    ),
    "err_rate": (
        "Se alcanzó el límite de uso de la IA. Espera un minuto y vuelve a intentarlo.",
        "AI rate limit reached. Wait a minute and try again.",
        "Limite d'utilisation de l'IA atteinte. Patientez une minute puis réessayez.",
    ),
    "err_network": (
        "No hay conexión con el servicio de IA. Revisa tu internet o proxy.",
        "Cannot reach the AI service. Check your internet or proxy.",
        "Impossible de joindre le service d'IA. Vérifiez internet ou le proxy.",
    ),
    "err_refusal": (
        "La IA no pudo atender esta solicitud. Reformúlala e inténtalo de nuevo.",
        "The AI could not handle this request. Rephrase it and try again.",
        "L'IA n'a pas pu traiter cette demande. Reformulez-la et réessayez.",
    ),
    "err_truncated": (
        "La respuesta de la IA quedó incompleta. Pide algo más corto.",
        "The AI response was cut off. Ask for something shorter.",
        "La réponse de l'IA est incomplète. Demandez quelque chose de plus court.",
    ),
    "err_server": (
        "El servicio de IA tuvo un problema ({detail}). Inténtalo más tarde.",
        "The AI service had a problem ({detail}). Try again later.",
        "Le service d'IA a rencontré un problème ({detail}). Réessayez plus tard.",
    ),
    "err_bad_request": ("Solicitud no válida: {detail}", "Invalid request: {detail}", "Requête invalide : {detail}"),
    "err_bad_output": (
        "La IA devolvió un resultado inesperado. Inténtalo de nuevo.",
        "The AI returned an unexpected result. Please try again.",
        "L'IA a renvoyé un résultat inattendu. Veuillez réessayer.",
    ),
    "privacy_note": (
        "A la IA solo se envía lo necesario (nombres de columnas, muestras o el texto indicado).",
        "Only what is needed is sent to the AI (column names, samples or the given text).",
        "Seul le nécessaire est envoyé à l'IA (noms de colonnes, échantillons ou texte fourni).",
    ),
    "ai_disclaimer": (
        "Contenido generado por IA: revísalo antes de usarlo.",
        "AI-generated content: review it before use.",
        "Contenu généré par l'IA : relisez-le avant de l'utiliser.",
    ),
}
