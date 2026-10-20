"""Interfaz común de los buzones (Outlook clásico o demostración) y búsqueda compartida."""

import re
import threading
from datetime import datetime

# Carpetas que no se recorren al buscar en todo el buzón.
SKIP_IN_MAILBOX = ("deleted", "junk", "sync", "outbox")


class BackendError(Exception):
    """Error del buzón; `code` es el sufijo de la clave de traducción (mp_err_…)."""

    def __init__(self, code, detail=""):
        super().__init__(f"{code}: {detail}" if detail else code)
        self.code = code
        self.detail = detail


class Progress:
    """Contadores que la búsqueda (en otro hilo) actualiza y la interfaz lee; `cancel` la detiene."""

    def __init__(self):
        self.seen = 0
        self.found = 0
        self.folder = ""
        self.cancel = threading.Event()


def split_categories(text, sep=","):
    return [c.strip() for c in (text or "").split(sep) if c.strip()]


def join_categories(categories, sep=","):
    return f"{sep} ".join(dict.fromkeys(c for c in categories if c))


def safe_filename(text, limit=80):
    name = re.sub(r'[\\/:*?"<>|\r\n\t]+', " ", text or "").strip(" .")
    return re.sub(r"\s+", " ", name)[:limit].strip() or "mail"


class MailBackend:
    """Operaciones de buzón. Los correos son `model.Message`; las carpetas y almacenes, `Folder` y `Store`.

    Las subclases implementan las operaciones con nombre público y, para la búsqueda, `_iter_messages`
    (correos de una carpeta, del más reciente al más antiguo) y `_load_details` (cuerpo, HTML y adjuntos)."""

    kind = "base"

    # -------- conexión y carpetas
    def connect(self):
        raise NotImplementedError

    def close(self):
        pass

    def stores(self):
        raise NotImplementedError

    def open_shared(self, address):
        raise NotImplementedError

    def folders(self, store_id):
        """Carpetas de correo del almacén en orden de árbol; la primera (profundidad 0) es la raíz."""
        raise NotImplementedError

    def create_folder(self, parent_id, name):
        raise NotImplementedError

    def rename_folder(self, folder_id, name):
        raise NotImplementedError

    def move_folder(self, folder_id, parent_id):
        raise NotImplementedError

    def delete_folder(self, folder_id):
        raise NotImplementedError

    # -------- correos
    def messages(self, folder_id, since=None, limit=1000):
        """(correos, truncado): los más recientes de la carpeta, como mucho `limit`."""
        raise NotImplementedError

    def search(self, folder_ids, query, since=None, limit=1000, internal_domains=(), progress=None):
        """(correos, truncado): los que cumplen la búsqueda en esas carpetas, del más reciente al más antiguo."""
        return self._search(folder_ids, query, since, limit, internal_domains, progress)

    def _search(self, folder_ids, query, since, limit, internal_domains, progress):
        progress = progress or Progress()
        floor = max([d for d in (since, query.date_floor()) if d], default=None)
        dasl = query.to_dasl()
        results = []
        for folder_id in folder_ids:
            for msg in self._iter_messages(folder_id, dasl, floor):
                if progress.cancel.is_set():
                    return self._sorted(results), True
                progress.seen += 1
                progress.folder = msg.folder_path
                if query.matches(msg, self._load_details, internal_domains):
                    results.append(msg)
                    progress.found += 1
                    if limit and len(results) >= limit:
                        return self._sorted(results), True
        return self._sorted(results), False

    @staticmethod
    def _sorted(messages):
        return sorted(messages, key=lambda m: m.received or datetime.min, reverse=True)

    def _iter_messages(self, folder_id, dasl, floor):
        raise NotImplementedError

    def _load_details(self, msg, html=False):
        raise NotImplementedError

    def details(self, msg, html=False):
        """Carga en `msg` el cuerpo, los adjuntos, la dirección de respuesta y, si se pide, el HTML."""
        raise NotImplementedError

    def scan(self, messages, html=False, progress=None):
        """Carga el cuerpo de muchos correos de una vez (para los análisis); se detiene con `progress.cancel`."""
        return self._scan(messages, html, progress)

    def _scan(self, messages, html, progress):
        progress = progress or Progress()
        out = []
        for msg in messages:
            if progress.cancel.is_set():
                break
            self._load_details(msg, html)
            progress.seen += 1
            out.append(msg)
        return out

    def move_messages(self, messages, folder_id):
        raise NotImplementedError

    def set_categories(self, messages, add=(), remove=()):
        raise NotImplementedError

    def mark_read(self, messages, read=True):
        raise NotImplementedError

    def set_flag(self, messages, flagged=True):
        raise NotImplementedError

    def delete_messages(self, messages):
        raise NotImplementedError

    def save_messages(self, messages, folder):
        raise NotImplementedError

    def save_attachments(self, messages, folder):
        raise NotImplementedError

    def open_message(self, msg):
        raise NotImplementedError

    # -------- categorías, reglas y borradores
    def categories(self):
        raise NotImplementedError

    def create_category(self, name, color):
        raise NotImplementedError

    def update_category(self, name, new_name=None, color=None):
        raise NotImplementedError

    def delete_category(self, name):
        raise NotImplementedError

    def create_rule(self, name, spec, store_id=None, folder_id=None, categories=(), flag=False):
        """Crea una regla de Outlook con las condiciones de `query.outlook_conditions`."""
        raise NotImplementedError

    def create_draft(self, to, subject, body, cc=""):
        raise NotImplementedError

    def current_draft(self):
        """Borrador o correo activo: {"subject", "body", "to", "editable"} (cuerpo sin el historial citado)."""
        raise NotImplementedError

    def apply_to_current(self, changes, subject=None):
        """Aplica cambios de `edits.diff_changes` (y el asunto, si se da) al borrador activo.

        Devuelve (aplicados, fallidos, texto propio del borrador tal como quedó)."""
        raise NotImplementedError


def unique_path(folder, name, suffix):
    path = folder / f"{name}{suffix}"
    n = 2
    while path.exists():
        path = folder / f"{name} ({n}){suffix}"
        n += 1
    return path
