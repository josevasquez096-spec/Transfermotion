"""Conexión con Outlook clásico para Windows mediante COM (pywin32), sin internet.

Todo el acceso a Outlook ocurre en un único hilo propio (STA): las llamadas de la interfaz se encolan y esperan su
resultado. Fuera de ese hilo solo circulan datos de Python (Store, Folder, Message), nunca objetos COM.

Requisitos: Outlook clásico (Win32) instalado y con un perfil configurado; el «nuevo Outlook» no tiene COM.
Según la política de TI, Outlook puede preguntar si permite el acceso de un programa (protección del modelo de
objetos); con un antivirus gestionado y actualizado normalmente no pregunta.
"""

import concurrent.futures
import html as htmllib
import queue
import re
import sys
import threading
from datetime import datetime
from pathlib import Path

from .backend_base import BackendError, MailBackend, join_categories, safe_filename, split_categories, unique_path
from .edits import split_quoted, word_text
from .model import Category, Folder, Message, Store

# Constantes de Outlook (se usan sin su librería de tipos).
OL_MAIL = 43  # OlObjectClass.olMail
OL_MAIL_FOLDER = 0  # OlItemType.olMailItem: DefaultItemType de las carpetas de correo
OL_MSG_UNICODE = 9  # OlSaveAsType.olMSGUnicode
OL_RULE_RECEIVE = 0
OL_MARK_NO_DATE = 4
OL_FORMAT_HTML = 2
OL_INBOX = 6
SPECIAL_FOLDERS = {6: "inbox", 5: "sent", 16: "drafts", 3: "deleted", 23: "junk", 4: "outbox", 20: "sync"}
PUBLIC_FOLDERS = 2  # OlExchangeStoreType.olExchangePublicFolder
SHARED_TYPES = (1, 4)  # buzón de otra persona añadido al perfil / buzón adicional
PR_SMTP = "http://schemas.microsoft.com/mapi/proptag/0x5D01001F"
PR_HAS_ATTACHMENT = "urn:schemas:httpmail:hasattachment"
PR_FLAG = "http://schemas.microsoft.com/mapi/proptag/0x10900003"
COLUMNS = ("EntryID", "Subject", "SenderName", "SenderEmailAddress", PR_SMTP, "To", "CC", "ReceivedTime",
           "Categories", "UnRead", "Importance", "Size", PR_HAS_ATTACHMENT, PR_FLAG)
MAX_FOLDERS = 3000
NO_OUTLOOK = (-2147221005, -2147221164)  # clase no registrada: no hay Outlook clásico
DENIED = (-2147024891, -2147467260)  # acceso denegado / el usuario rechazó el aviso de seguridad


def list_separator():
    """Separador de listas de Windows: Outlook lo usa entre categorías («,» o «;» según el país)."""
    if sys.platform != "win32":
        return ","
    try:
        import winreg

        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, r"Control Panel\International") as key:
            return winreg.QueryValueEx(key, "sList")[0] or ","
    except OSError:
        return ","


def _naive(value):
    """Fecha de COM (pywintypes la marca como UTC aunque es hora local) a datetime local sin zona."""
    if not isinstance(value, datetime) or value.year >= 4500:  # 4501-01-01 significa «sin fecha»
        return None
    return datetime(value.year, value.month, value.day, value.hour, value.minute, value.second)


def _int(value, default=0):
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def _attr(obj, name, default=None):
    """Propiedad COM que puede fallar (permisos, tipo de elemento…) sin interrumpir la operación."""
    try:
        value = getattr(obj, name)
    except Exception:  # pywintypes.com_error y similares
        return default
    return default if value is None else value


def _com_text(exc):
    args = getattr(exc, "args", ())
    if len(args) >= 3 and args[2] and len(args[2]) > 2 and args[2][2]:
        return str(args[2][2]).strip()
    if len(args) >= 2 and args[1]:
        return str(args[1]).strip()
    return str(exc)


def _translate(exc):
    """Convierte un error de COM en BackendError; los demás errores se dejan pasar."""
    if type(exc).__name__ != "com_error":
        return exc
    args = getattr(exc, "args", ()) or (None,)
    codes = {args[0]}
    if len(args) >= 3 and args[2] and len(args[2]) > 5:
        codes.add(args[2][5])
    if codes & set(NO_OUTLOOK):
        return BackendError("no_outlook", _com_text(exc))
    if codes & set(DENIED):
        return BackendError("denied", _com_text(exc))
    return BackendError("com", _com_text(exc))


def _check_name(name):
    name = (name or "").strip()
    if not name or any(c in name for c in "\\/"):
        raise BackendError("folder_name", name)
    return name


class _ComThread:
    """Hilo único para Outlook: COM exige usar sus objetos desde el hilo que los creó."""

    def __init__(self, com_init=True):
        self._queue = queue.Queue()
        self._com_init = com_init
        self.thread = threading.Thread(target=self._run, name="outlook-com", daemon=True)
        self.thread.start()

    def _run(self):
        pythoncom = None
        if self._com_init:
            try:
                import pythoncom

                pythoncom.CoInitialize()
            except ImportError:
                pythoncom = None
        try:
            while True:
                job = self._queue.get()
                if job is None:
                    break
                fn, args, kwargs, future = job
                if not future.set_running_or_notify_cancel():
                    continue
                try:
                    future.set_result(fn(*args, **kwargs))
                except BaseException as exc:  # se entrega al hilo que llamó
                    future.set_exception(exc)
        finally:
            if pythoncom is not None:
                pythoncom.CoUninitialize()

    def call(self, fn, *args, **kwargs):
        if threading.current_thread() is self.thread:
            return fn(*args, **kwargs)
        future = concurrent.futures.Future()
        self._queue.put((fn, args, kwargs, future))
        return future.result()

    def post(self, fn):
        """Encola una tarea sin esperar su resultado."""
        self._queue.put((fn, (), {}, concurrent.futures.Future()))

    def stop(self):
        self._queue.put(None)


class OutlookBackend(MailBackend):
    kind = "outlook"

    def __init__(self, dispatch=None, com_init=True, separator=None):
        self._dispatch = dispatch
        self._com = _ComThread(com_init)
        self.sep = separator or list_separator()
        self.app = self.ns = None
        self._folder_store = {}  # EntryID de carpeta -> StoreID
        self._folder_path = {}  # EntryID de carpeta -> ruta mostrada
        self._shared = {}  # StoreID -> (dirección, EntryID de su bandeja de entrada) abiertos con open_shared
        self._current = None  # (elemento, documento de Word) del borrador activo; solo en el hilo COM

    def _call(self, fn, *args, **kwargs):
        try:
            return self._com.call(fn, *args, **kwargs)
        except BackendError:
            raise
        except Exception as exc:
            translated = _translate(exc)
            if translated is exc:
                raise
            raise translated from exc

    # ------------------------------------------------------------ conexión
    def connect(self):
        return self._call(self._connect)

    def _connect(self):
        dispatch = self._dispatch
        if dispatch is None:
            try:
                import win32com.client
            except ImportError:
                raise BackendError("no_pywin32") from None

            def dispatch():
                return win32com.client.Dispatch("Outlook.Application")

        self.app = dispatch()
        self.ns = self.app.GetNamespace("MAPI")
        return self._stores()

    def close(self):
        """Suelta los objetos de Outlook y termina el hilo COM sin esperar (no bloquea al cerrar la ventana)."""
        def release():
            self.app = self.ns = self._current = None

        self._com.post(release)
        self._com.stop()

    def stores(self):
        return self._call(self._stores)

    def _profile_stores(self):
        stores = self.ns.Stores
        return [stores.Item(i) for i in range(1, stores.Count + 1)]

    def _stores(self):
        default = _attr(_attr(self.ns, "DefaultStore"), "StoreID", "")
        out, seen = [], set()
        for store in self._profile_stores():
            store_type = _attr(store, "ExchangeStoreType", 3)
            if store_type == PUBLIC_FOLDERS:
                continue
            store_id = store.StoreID
            seen.add(store_id)
            if store_id == default:
                kind = "primary"
            elif store_type in SHARED_TYPES:
                kind = "shared"
            elif str(_attr(store, "FilePath", "")).lower().endswith(".pst"):
                kind = "pst"
            else:
                kind = "other"
            out.append(Store(id=store_id, name=_attr(store, "DisplayName", "") or store_id[:12], kind=kind,
                             address=self._account_address(store_id)))
        for store_id, (address, _entry) in self._shared.items():
            if store_id not in seen:
                out.append(Store(id=store_id, name=address, kind="shared", address=address))
        return out

    def _account_address(self, store_id):
        """Dirección SMTP de la cuenta que entrega en ese almacén (para saber qué dominios son internos)."""
        accounts = _attr(self.ns, "Accounts")
        for i in range(1, _int(_attr(accounts, "Count", 0)) + 1):
            account = accounts.Item(i)
            if _attr(_attr(account, "DeliveryStore"), "StoreID") == store_id:
                return _attr(account, "SmtpAddress", "") or ""
        return ""

    def open_shared(self, address):
        return self._call(self._open_shared, address)

    def _open_shared(self, address):
        address = (address or "").strip()
        recipient = self.ns.CreateRecipient(address)
        if not address or not recipient.Resolve():
            raise BackendError("shared_failed", address)
        try:
            inbox = self.ns.GetSharedDefaultFolder(recipient, OL_INBOX)
        except Exception as exc:
            raise BackendError("shared_failed", f"{address}: {_com_text(exc)}") from None
        store_id = inbox.StoreID
        for store in self._stores():
            if store.id == store_id:  # ya estaba en el perfil (asignación automática de Exchange)
                return store
        self._shared[store_id] = (address, inbox.EntryID)
        self._folder_store[inbox.EntryID] = store_id
        return Store(id=store_id, name=address, kind="shared", address=address)

    # ------------------------------------------------------------ carpetas
    def _store(self, store_id):
        for store in self._profile_stores():
            if store.StoreID == store_id:
                return store
        return None

    def _specials(self, store):
        out = {}
        for number, kind in SPECIAL_FOLDERS.items():
            try:
                out[store.GetDefaultFolder(number).EntryID] = kind
            except Exception:  # el almacén no tiene esa carpeta (p. ej. un .pst de archivo)
                pass
        return out

    def folders(self, store_id):
        return self._call(self._folders, store_id)

    def _folders(self, store_id):
        store = self._store(store_id)
        if store is not None:
            root, specials, root_name = store.GetRootFolder(), self._specials(store), store.DisplayName
        elif store_id in self._shared:
            address, entry = self._shared[store_id]
            root, specials, root_name = self.ns.GetFolderFromID(entry, store_id), {entry: "inbox"}, address
        else:
            raise BackendError("not_found", store_id)
        out = []

        def walk(folder, parent_id, path, depth):
            folder_id = folder.EntryID
            self._folder_store[folder_id] = store_id
            self._folder_path[folder_id] = path
            out.append(Folder(id=folder_id, store_id=store_id, name=root_name if depth == 0 else folder.Name,
                              path=path, parent_id=parent_id, depth=depth,
                              unread=_int(_attr(folder, "UnReadItemCount", 0)),
                              total=_int(_attr(_attr(folder, "Items"), "Count", 0)),
                              special=specials.get(folder_id, "")))
            subs = folder.Folders
            for i in range(1, subs.Count + 1):
                if len(out) >= MAX_FOLDERS:
                    return
                sub = subs.Item(i)
                if _attr(sub, "DefaultItemType", -1) != OL_MAIL_FOLDER:
                    continue  # calendario, contactos, tareas…
                name = sub.Name
                walk(sub, folder_id, f"{path}/{name}" if path else name, depth + 1)

        walk(root, "", "", 0)
        return out

    def _folder(self, folder_id):
        store_id = self._folder_store.get(folder_id)
        try:
            if store_id:
                return self.ns.GetFolderFromID(folder_id, store_id)
            return self.ns.GetFolderFromID(folder_id)
        except Exception:
            raise BackendError("not_found", folder_id) from None

    def create_folder(self, parent_id, name):
        return self._call(self._create_folder, parent_id, name)

    def _create_folder(self, parent_id, name):
        name = _check_name(name)
        parent = self._folder(parent_id)
        subs = parent.Folders
        for i in range(1, subs.Count + 1):
            if subs.Item(i).Name.lower() == name.lower():
                raise BackendError("folder_exists", name)
        folder = subs.Add(name)
        store_id = self._folder_store.get(parent_id, "")
        parent_path = self._folder_path.get(parent_id, "")
        path = f"{parent_path}/{name}" if parent_path else name
        self._folder_store[folder.EntryID] = store_id
        self._folder_path[folder.EntryID] = path
        return Folder(id=folder.EntryID, store_id=store_id, name=name, path=path, parent_id=parent_id)

    def rename_folder(self, folder_id, name):
        return self._call(self._rename_folder, folder_id, name)

    def _rename_folder(self, folder_id, name):
        self._folder(folder_id).Name = _check_name(name)

    def move_folder(self, folder_id, parent_id):
        return self._call(self._move_folder, folder_id, parent_id)

    def _move_folder(self, folder_id, parent_id):
        self._folder(folder_id).MoveTo(self._folder(parent_id))

    def delete_folder(self, folder_id):
        return self._call(self._delete_folder, folder_id)

    def _delete_folder(self, folder_id):
        self._folder(folder_id).Delete()  # Outlook la mueve a Elementos eliminados

    # ------------------------------------------------------------ correos
    def _columns(self, table):
        columns = table.Columns
        columns.RemoveAll()
        names = []
        for name in COLUMNS:
            try:
                columns.Add(name)
                names.append(name)
            except Exception:  # propiedad que este almacén no admite en tablas
                pass
        return names

    def _message(self, values, folder_id, store_id, path):
        email = values.get(PR_SMTP) or ""
        if "@" not in email:
            email = values.get("SenderEmailAddress") or ""
            if "@" not in email:
                email = ""  # dirección interna de Exchange (X500)
        return Message(id=values.get("EntryID") or "", store_id=store_id, folder_id=folder_id, folder_path=path,
                       subject=values.get("Subject") or "", sender_name=values.get("SenderName") or "",
                       sender_email=email, to=values.get("To") or "", cc=values.get("CC") or "",
                       received=_naive(values.get("ReceivedTime")),
                       categories=split_categories(values.get("Categories") or "", self.sep),
                       unread=bool(values.get("UnRead")), flagged=values.get(PR_FLAG) == 2,
                       importance=_int(values.get("Importance"), 1),
                       has_attachments=bool(values.get(PR_HAS_ATTACHMENT)), size=_int(values.get("Size")))

    def _iter_messages(self, folder_id, dasl, floor):
        folder = self._folder(folder_id)
        store_id = self._folder_store.get(folder_id) or _attr(folder, "StoreID", "")
        path = self._folder_path.get(folder_id)
        if path is None:
            path = "/".join(str(_attr(folder, "FolderPath", "")).strip("\\").split("\\")[1:])
        table = None
        if dasl:
            try:
                table = folder.GetTable(dasl, 0)
            except Exception:  # filtro no admitido: se evalúa todo en Python
                table = None
        if table is None:
            table = folder.GetTable("", 0)
        names = self._columns(table)
        try:
            table.Sort("ReceivedTime", True)
        except Exception:
            pass
        while not table.EndOfTable:
            row = table.GetNextRow()
            if row is None:
                break
            msg = self._message(dict(zip(names, row.GetValues(), strict=False)), folder_id, store_id, path)
            if floor and msg.received and msg.received < floor:
                break  # la tabla va de más reciente a más antiguo
            yield msg

    def messages(self, folder_id, since=None, limit=1000):
        return self._call(self._messages, folder_id, since, limit)

    def _messages(self, folder_id, since, limit):
        out = []
        for msg in self._iter_messages(folder_id, "", since):
            if limit and len(out) >= limit:
                return out, True
            out.append(msg)
        return out, False

    def search(self, folder_ids, query, since=None, limit=1000, internal_domains=(), progress=None):
        return self._call(self._search, folder_ids, query, since, limit, internal_domains, progress)

    def details(self, msg, html=False):
        return self._call(self._load_details, msg, html)

    def scan(self, messages, html=False, progress=None):
        return self._call(self._scan, messages, html, progress)

    def _load_details(self, msg, html=False):
        try:
            item = self.ns.GetItemFromID(msg.id, msg.store_id)
            if msg.body is None:
                msg.body = (_attr(item, "Body", "") or "").replace("\r\n", "\n")
                msg.attachments = self._attachment_names(item)
                msg.reply_to = self._reply_to(item)
            if html and msg.html is None:
                is_html = _attr(item, "BodyFormat", 0) == OL_FORMAT_HTML
                msg.html = (_attr(item, "HTMLBody", "") or "") if is_html else ""
        except Exception:  # un correo ilegible (cifrado, dañado…) no detiene la búsqueda
            if msg.body is None:
                msg.body = ""
            if html and msg.html is None:
                msg.html = ""
        return msg

    def _attachment_names(self, item):
        names = []
        attachments = _attr(item, "Attachments")
        for i in range(1, _int(_attr(attachments, "Count", 0)) + 1):
            att = attachments.Item(i)
            names.append(_attr(att, "FileName", "") or _attr(att, "DisplayName", "") or "")
        return [n for n in names if n]

    def _reply_to(self, item):
        recipients = _attr(item, "ReplyRecipients")
        for i in range(1, _int(_attr(recipients, "Count", 0)) + 1):
            recipient = recipients.Item(i)
            address = _attr(recipient, "Address", "") or ""
            if "@" not in address:
                user = None
                entry = _attr(recipient, "AddressEntry")
                if entry is not None:
                    try:
                        user = entry.GetExchangeUser()
                    except Exception:
                        user = None
                address = _attr(user, "PrimarySmtpAddress", "") if user is not None else ""
            if "@" in address:
                return address
        return ""

    def _each(self, messages, action):
        """Aplica `action(item)` a cada correo; devuelve cuántos cambiaron. Falla solo si fallan todos."""
        done, error = 0, None
        for msg in messages:
            try:
                item = self.ns.GetItemFromID(msg.id, msg.store_id)
                if action(item) is not False:
                    done += 1
            except Exception as exc:
                error = error or exc
        if error is not None and done == 0:
            raise error
        return done

    def move_messages(self, messages, folder_id):
        return self._call(self._move_messages, messages, folder_id)

    def _move_messages(self, messages, folder_id):
        dest = self._folder(folder_id)

        def action(item):
            item.Move(dest)

        return self._each(messages, action)

    def set_categories(self, messages, add=(), remove=()):
        return self._call(self._set_categories, messages, tuple(add), tuple(remove))

    def _set_categories(self, messages, add, remove):
        drop = {c.lower() for c in remove}

        def action(item):
            current = _attr(item, "Categories", "") or ""
            cats = [c for c in split_categories(current, self.sep) if c.lower() not in drop]
            have = {c.lower() for c in cats}
            cats += [c for c in add if c.lower() not in have]
            new = join_categories(cats, self.sep)
            if new == current:
                return False
            item.Categories = new
            item.Save()
            return True

        return self._each(messages, action)

    def mark_read(self, messages, read=True):
        return self._call(self._mark_read, messages, read)

    def _mark_read(self, messages, read):
        def action(item):
            item.UnRead = not read
            item.Save()

        return self._each(messages, action)

    def set_flag(self, messages, flagged=True):
        return self._call(self._set_flag, messages, flagged)

    def _set_flag(self, messages, flagged):
        def action(item):
            if flagged:
                item.MarkAsTask(OL_MARK_NO_DATE)
            else:
                item.ClearTaskFlag()
            item.Save()

        return self._each(messages, action)

    def delete_messages(self, messages):
        return self._call(self._each, messages, lambda item: item.Delete())

    def save_messages(self, messages, folder):
        return self._call(self._save_messages, messages, Path(folder))

    def _save_messages(self, messages, folder):
        paths = []

        def action(item):
            received = _naive(_attr(item, "ReceivedTime"))
            stamp = received.strftime("%Y-%m-%d") if received else ""
            path = unique_path(folder, safe_filename(f"{stamp} {_attr(item, 'Subject', '')}"), ".msg")
            item.SaveAs(str(path), OL_MSG_UNICODE)
            paths.append(path)

        self._each(messages, action)
        return paths

    def save_attachments(self, messages, folder):
        return self._call(self._save_attachments, messages, Path(folder))

    def _save_attachments(self, messages, folder):
        paths = []

        def action(item):
            attachments = item.Attachments
            for i in range(1, attachments.Count + 1):
                att = attachments.Item(i)
                name = _attr(att, "FileName", "")
                if not name:
                    continue  # elemento incrustado sin archivo
                stem, dot, ext = name.rpartition(".")
                path = unique_path(folder, safe_filename(stem or name), f".{ext}" if dot else "")
                att.SaveAsFile(str(path))
                paths.append(path)

        self._each(messages, action)
        return paths

    def open_message(self, msg):
        return self._call(self._open_message, msg)

    def _open_message(self, msg):
        self.ns.GetItemFromID(msg.id, msg.store_id).Display()
        return True

    # ------------------------------------------------------------ categorías
    def categories(self):
        return self._call(self._categories)

    def _category_list(self):
        cats = self.ns.Categories
        return [cats.Item(i) for i in range(1, cats.Count + 1)]

    def _categories(self):
        return [Category(_attr(c, "Name", ""), _int(_attr(c, "Color", 0))) for c in self._category_list()]

    def _find_category(self, name):
        for index, cat in enumerate(self._category_list(), start=1):
            if (_attr(cat, "Name", "") or "").lower() == (name or "").strip().lower():
                return index, cat
        return None, None

    def create_category(self, name, color):
        return self._call(self._create_category, name, color)

    def _create_category(self, name, color):
        name = (name or "").strip()
        if not name or self.sep in name or "," in name:
            raise BackendError("category_name", name)
        if self._find_category(name)[1] is not None:
            raise BackendError("category_exists", name)
        self.ns.Categories.Add(name, int(color))

    def update_category(self, name, new_name=None, color=None):
        return self._call(self._update_category, name, new_name, color)

    def _update_category(self, name, new_name, color):
        _, cat = self._find_category(name)
        if cat is None:
            raise BackendError("not_found", name)
        if new_name and new_name.strip() != cat.Name:
            new_name = new_name.strip()
            if self.sep in new_name or "," in new_name:
                raise BackendError("category_name", new_name)
            if self._find_category(new_name)[1] is not None:
                raise BackendError("category_exists", new_name)
            cat.Name = new_name
        if color is not None:
            cat.Color = int(color)

    def delete_category(self, name):
        return self._call(self._delete_category, name)

    def _delete_category(self, name):
        index, _ = self._find_category(name)
        if index is None:
            raise BackendError("not_found", name)
        self.ns.Categories.Remove(index)

    # ------------------------------------------------------------ reglas
    def create_rule(self, name, spec, store_id=None, folder_id=None, categories=(), flag=False):
        return self._call(self._create_rule, name, spec, store_id, folder_id, tuple(categories), flag)

    def _create_rule(self, name, spec, store_id, folder_id, categories, flag):
        store = (self._store(store_id) if store_id else None) or self.ns.DefaultStore
        rules = store.GetRules()
        rule = rules.Create(name, OL_RULE_RECEIVE)
        for kind, value in spec["conditions"].items():
            self._rule_condition(rule.Conditions, kind, value)
        for kind, value in spec.get("exceptions", {}).items():
            self._rule_condition(rule.Exceptions, kind, value)
        if folder_id:
            action = rule.Actions.MoveToFolder
            action.Folder = self._folder(folder_id)
            action.Enabled = True
        if categories:
            action = rule.Actions.AssignToCategory
            action.Categories = list(categories)
            action.Enabled = True
        if flag:
            action = rule.Actions.MarkAsTask
            action.MarkInterval = OL_MARK_NO_DATE
            action.Enabled = True
        rule.Enabled = True
        rules.Save(False)
        return name

    @staticmethod
    def _rule_condition(conditions, kind, value):
        if kind in ("subject", "body", "body_or_subject"):
            condition = getattr(conditions, {"subject": "Subject", "body": "Body",
                                             "body_or_subject": "BodyOrSubject"}[kind])
            condition.Text = list(value)
        elif kind == "sender_address":
            condition = conditions.SenderAddress
            condition.Address = list(value)
        elif kind == "has_attachment":
            condition = conditions.HasAttachment
        elif kind == "importance":
            condition = conditions.Importance
            condition.Importance = int(value)
        else:
            raise BackendError("rule", kind)
        condition.Enabled = True

    # ------------------------------------------------------------ borradores
    def create_draft(self, to, subject, body, cc=""):
        return self._call(self._create_draft, to, subject, body, cc)

    def _create_draft(self, to, subject, body, cc):
        mail = self.app.CreateItem(0)
        mail.To = to or ""
        if cc:
            mail.CC = cc
        mail.Subject = subject or ""
        mail.Display()  # al mostrarlo, Outlook añade la firma predeterminada
        existing = _attr(mail, "HTMLBody", "") or ""
        start = re.search(r"<body[^>]*>", existing, re.I)
        if start and _attr(mail, "BodyFormat", 0) == OL_FORMAT_HTML:
            paragraphs = "".join(f"<p class=MsoNormal>{htmllib.escape(line) or '&nbsp;'}</p>"
                                 for line in (body or "").split("\n"))
            mail.HTMLBody = existing[:start.end()] + paragraphs + existing[start.end():]
        else:
            signature = _attr(mail, "Body", "") or ""
            mail.Body = (body or "") + ("\r\n\r\n" + signature if signature.strip() else "")
        return True

    def current_draft(self):
        return self._call(self._current_draft)

    def _current_draft(self):
        self._current = None
        item = document = None
        inspector = self._active(self.app, "ActiveInspector")
        if inspector is not None:
            item, document = _attr(inspector, "CurrentItem"), _attr(inspector, "WordEditor")
        else:
            explorer = self._active(self.app, "ActiveExplorer")
            if explorer is not None:
                inline = _attr(explorer, "ActiveInlineResponse")
                if inline is not None:
                    item, document = inline, _attr(explorer, "ActiveInlineResponseWordEditor")
                else:
                    selection = _attr(explorer, "Selection")
                    if selection is not None and _int(_attr(selection, "Count", 0)):
                        item = selection.Item(1)
        if item is None or _attr(item, "Class", 0) != OL_MAIL:
            raise BackendError("no_current")
        draft = not _attr(item, "Sent", True)
        if draft and document is None:
            document = _attr(_attr(item, "GetInspector"), "WordEditor")
        if document is not None:
            text = word_text(_attr(_attr(document, "Content"), "Text", "") or "")
        else:
            text = (_attr(item, "Body", "") or "").replace("\r\n", "\n")
        own, _ = split_quoted(text)
        editable = draft and document is not None
        if editable:
            self._current = (item, document)
        return {"subject": _attr(item, "Subject", "") or "", "body": own, "to": _attr(item, "To", "") or "",
                "editable": editable}

    @staticmethod
    def _active(app, method):
        try:
            return getattr(app, method)()
        except Exception:
            return None

    def apply_to_current(self, changes, subject=None):
        return self._call(self._apply_to_current, list(changes), subject)

    def _apply_to_current(self, changes, subject):
        if not self._current:
            raise BackendError("no_current")
        item, document = self._current
        applied = failed = 0
        start = 0
        for find, replace, skips in changes:
            found = self._word_find(document, start, find, skips)
            if found is None:
                failed += 1
                continue
            found.Text = replace.replace("\n", "\r")
            start = found.End
            applied += 1
        if subject is not None:
            item.Subject = subject
        if applied or subject is not None:
            try:
                item.Save()
            except Exception:  # el borrador sigue abierto con los cambios; Outlook lo guardará al enviarlo
                pass
        own, _ = split_quoted(word_text(_attr(_attr(document, "Content"), "Text", "") or ""))
        return applied, failed, own

    @staticmethod
    def _word_find(document, start, find, skips):
        """Busca con Word desde `start` (sin comodines y respetando mayúsculas); devuelve el rango encontrado."""
        if not find:
            return None
        text = find.replace("^", "^^")
        variants = [text.replace("\n", code) for code in ("^p", "^l")] if "\n" in text else [text]
        for variant in variants:
            if len(variant) > 255:  # límite de búsqueda de Word
                continue
            found = document.Range(start, document.Content.End)
            finder = found.Find
            finder.ClearFormatting()
            finder.Text = variant
            finder.Forward = True
            finder.Wrap = 0  # wdFindStop
            finder.MatchCase = True
            finder.MatchWholeWord = False
            finder.MatchWildcards = False
            ok = finder.Execute()
            for _ in range(skips):
                if not ok:
                    break
                found.Collapse(0)  # wdCollapseEnd: sigue buscando después de esta aparición
                ok = finder.Execute()
            if ok:
                return found
        return None
