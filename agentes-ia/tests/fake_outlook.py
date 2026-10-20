"""Modelo de objetos de Outlook (y de Word para los borradores) simulado en Python.

Imita solo lo que usa `backend_outlook`: almacenes, carpetas, tablas, elementos, categorías, reglas, inspectores
y la búsqueda de Word. Sirve para probar el conector sin Windows ni Outlook.
"""

import itertools
from datetime import datetime

_ids = itertools.count(1)


def new_id(prefix):
    return f"{prefix}{next(_ids):06d}"


class ComError(Exception):
    """Imita pywintypes.com_error: args = (hresult, texto, excepinfo, argerr)."""


ComError.__name__ = "com_error"


class Collection:
    def __init__(self, items=None):
        self.items = list(items or [])

    @property
    def Count(self):  # noqa: N802 - nombres del modelo de objetos de Outlook
        return len(self.items)

    def Item(self, index):  # noqa: N802
        return self.items[index - 1]


class Attachment:
    def __init__(self, name):
        self.FileName = name
        self.DisplayName = name

    def SaveAsFile(self, path):  # noqa: N802
        with open(path, "w", encoding="utf-8") as fh:
            fh.write(self.FileName)


class Recipient:
    def __init__(self, address, resolvable=True):
        self.Address = address
        self._ok = resolvable

    def Resolve(self):  # noqa: N802
        return self._ok


class Range:
    def __init__(self, doc, start, end):
        self.doc, self.Start, self.End = doc, start, end
        self.Find = Find(self)

    @property
    def Text(self):  # noqa: N802
        return self.doc.text[self.Start:self.End]

    @Text.setter
    def Text(self, value):  # noqa: N802
        self.doc.text = self.doc.text[:self.Start] + value + self.doc.text[self.End:]
        self.End = self.Start + len(value)

    def Collapse(self, direction):  # noqa: N802
        if direction == 0:
            self.Start = self.End
        else:
            self.End = self.Start


class Find:
    CODES = {"^^": "^", "^p": "\r", "^l": "\x0b"}

    def __init__(self, rng):
        self.rng = rng
        self.Text = ""
        self.Forward = True
        self.Wrap = 0
        self.MatchCase = False
        self.MatchWholeWord = False
        self.MatchWildcards = False

    def ClearFormatting(self):  # noqa: N802
        pass

    def Execute(self):  # noqa: N802
        needle, i = "", 0
        while i < len(self.Text):
            pair = self.Text[i:i + 2]
            if pair in self.CODES:
                needle += self.CODES[pair]
                i += 2
            else:
                needle += self.Text[i]
                i += 1
        doc = self.rng.doc
        end = len(doc.text) if self.rng.Start == self.rng.End else self.rng.End
        hay = doc.text[:end] if self.MatchCase else doc.text[:end].lower()
        at = hay.find(needle if self.MatchCase else needle.lower(), self.rng.Start)
        if at < 0:
            return False
        self.rng.Start, self.rng.End = at, at + len(needle)
        return True


class Document:
    def __init__(self, text):
        self.text = text

    @property
    def Content(self):  # noqa: N802
        return Range(self, 0, len(self.text))

    def Range(self, start, end):  # noqa: N802
        return Range(self, start, end)


class Inspector:
    def __init__(self, item):
        self.CurrentItem = item
        self.WordEditor = item.document


class MailItem:
    Class = 43

    def __init__(self, folder, subject="", sender=("", ""), body="", received=None, categories="", unread=False,
                 flagged=False, importance=1, attachments=(), html="", to="", cc="", sent=True, reply_to=""):
        self.EntryID = new_id("item")
        self.folder = folder
        self.Subject, self.Body, self.To, self.CC = subject, body, to, cc
        self.SenderName, self.SenderEmailAddress = sender
        self.ReceivedTime = received or datetime(4501, 1, 1)
        self.Categories, self.UnRead, self.Importance = categories, unread, importance
        self.flagged = flagged
        self.Size = 1000 + len(body)
        self.Attachments = Collection(Attachment(a) for a in attachments)
        self.HTMLBody = html
        self.BodyFormat = 2 if html else 1
        self.Sent = sent
        self.ReplyRecipients = Collection([Recipient(reply_to)] if reply_to else [])
        self.document = Document(body.replace("\n", "\r") + "\r")
        self.saved = 0
        self.displayed = False

    @property
    def StoreID(self):  # noqa: N802
        return self.folder.StoreID

    @property
    def GetInspector(self):  # noqa: N802
        return Inspector(self)

    def row(self, column):
        if column == "http://schemas.microsoft.com/mapi/proptag/0x5D01001F":
            return self.SenderEmailAddress if "@" in self.SenderEmailAddress else ""
        if column == "urn:schemas:httpmail:hasattachment":
            return self.Attachments.Count > 0
        if column == "http://schemas.microsoft.com/mapi/proptag/0x10900003":
            return 2 if self.flagged else None
        return getattr(self, column)

    def Save(self):  # noqa: N802
        self.saved += 1

    def Move(self, dest):  # noqa: N802
        self.folder.items.remove(self)
        dest.items.append(self)
        self.folder.store.index.pop(self.EntryID, None)
        self.folder = dest
        self.EntryID = new_id("item")  # como en Exchange, el identificador cambia al mover
        self.folder.store.index[self.EntryID] = self
        return self

    def Delete(self):  # noqa: N802
        trash = self.folder.store.default_folders.get(3)
        if trash is not None and self.folder is not trash:
            self.Move(trash)
        else:
            self.folder.items.remove(self)

    def MarkAsTask(self, interval):  # noqa: N802
        self.flagged = True

    def ClearTaskFlag(self):  # noqa: N802
        self.flagged = False

    def SaveAs(self, path, kind):  # noqa: N802
        with open(path, "w", encoding="utf-8") as fh:
            fh.write(f"{kind}:{self.Subject}")

    def Display(self):  # noqa: N802
        self.displayed = True


class Row:
    def __init__(self, values):
        self.values = values

    def GetValues(self):  # noqa: N802
        return tuple(self.values)


class Columns:
    def __init__(self, table):
        self.table = table
        self.names = ["EntryID", "Subject"]

    def RemoveAll(self):  # noqa: N802
        self.names = []

    def Add(self, name):  # noqa: N802
        if name in self.table.folder.store.unsupported_columns:
            raise ComError(-2147352567, "Property not supported", None, None)
        self.names.append(name)


class Table:
    def __init__(self, folder, filter_):
        self.folder, self.filter = folder, filter_
        self.Columns = Columns(self)
        self.rows = list(folder.items)
        self.pos = 0

    def Sort(self, prop, descending):  # noqa: N802
        self.rows.sort(key=lambda item: getattr(item, prop), reverse=descending)

    @property
    def EndOfTable(self):  # noqa: N802
        return self.pos >= len(self.rows)

    def GetNextRow(self):  # noqa: N802
        item = self.rows[self.pos]
        self.pos += 1
        return Row([item.row(name) for name in self.Columns.names])


class Folders(Collection):
    def __init__(self, parent):
        super().__init__()
        self.parent = parent

    def Add(self, name, kind=None):  # noqa: N802
        if any(f.Name.lower() == name.lower() for f in self.items):
            raise ComError(-2147352567, "Cannot create the folder.", None, None)
        return self.parent.add_folder(name)


class MAPIFolder:
    def __init__(self, store, name, parent=None, item_type=0):
        self.EntryID = new_id("fold")
        self.store, self.Name, self.Parent = store, name, parent
        self.DefaultItemType = item_type
        self.Folders = Folders(self)
        self.items = []
        self.tables = []
        store.folders[self.EntryID] = self

    @property
    def StoreID(self):  # noqa: N802
        return self.store.StoreID

    @property
    def FolderPath(self):  # noqa: N802
        parts, node = [], self
        while node is not None:
            parts.append(node.Name)
            node = node.Parent
        return "\\\\" + "\\".join(reversed(parts))

    @property
    def Items(self):  # noqa: N802
        return Collection(self.items)

    @property
    def UnReadItemCount(self):  # noqa: N802
        return sum(1 for i in self.items if i.UnRead)

    def add_folder(self, name, item_type=0):
        folder = MAPIFolder(self.store, name, self, item_type)
        self.Folders.items.append(folder)
        return folder

    def add_mail(self, **kw):
        item = MailItem(self, **kw)
        self.items.append(item)
        self.store.index[item.EntryID] = item
        return item

    def GetTable(self, filter_="", contents=0):  # noqa: N802
        if filter_ and self.store.reject_filters:
            raise ComError(-2147352567, "Filter not supported", None, None)
        table = Table(self, filter_)
        self.tables.append(filter_)
        return table

    def MoveTo(self, dest):  # noqa: N802
        self.Parent.Folders.items.remove(self)
        dest.Folders.items.append(self)
        self.Parent = dest

    def Delete(self):  # noqa: N802
        trash = self.store.default_folders[3]
        self.MoveTo(trash)


class RuleCondition:
    def __init__(self):
        self.Enabled = False
        self.Text = self.Address = self.Importance = None


class RuleConditions:
    def __init__(self):
        for name in ("Subject", "Body", "BodyOrSubject", "SenderAddress", "HasAttachment", "Importance"):
            setattr(self, name, RuleCondition())


class RuleAction:
    def __init__(self):
        self.Enabled = False
        self.Folder = self.Categories = self.MarkInterval = None


class RuleActions:
    def __init__(self):
        for name in ("MoveToFolder", "AssignToCategory", "MarkAsTask"):
            setattr(self, name, RuleAction())


class Rule:
    def __init__(self, name, kind):
        self.Name, self.RuleType, self.Enabled = name, kind, False
        self.Conditions, self.Exceptions, self.Actions = RuleConditions(), RuleConditions(), RuleActions()


class Rules(Collection):
    def __init__(self):
        super().__init__()
        self.saved = 0

    def Create(self, name, kind):  # noqa: N802
        rule = Rule(name, kind)
        self.items.append(rule)
        return rule

    def Save(self, show_progress=True):  # noqa: N802
        self.saved += 1


class OutlookStore:
    def __init__(self, name, store_type=0, file_path=""):
        self.StoreID = new_id("store")
        self.DisplayName = name
        self.ExchangeStoreType = store_type
        self.FilePath = file_path
        self.folders, self.index = {}, {}
        self.default_folders = {}
        self.unsupported_columns = set()
        self.reject_filters = False
        self.rules = Rules()
        self.root = MAPIFolder(self, name)

    def GetRootFolder(self):  # noqa: N802
        return self.root

    def GetDefaultFolder(self, number):  # noqa: N802
        if number not in self.default_folders:
            raise ComError(-2147221233, "The folder does not exist.", None, None)
        return self.default_folders[number]

    def GetRules(self):  # noqa: N802
        return self.rules

    def standard(self, names=None):
        names = names or {6: "Inbox", 5: "Sent Items", 16: "Drafts", 3: "Deleted Items", 23: "Junk Email"}
        for number, name in names.items():
            self.default_folders[number] = self.root.add_folder(name)
        self.root.add_folder("Calendar", item_type=1)
        return self


class Category:
    def __init__(self, name, color):
        self.Name, self.Color = name, color


class Categories(Collection):
    def Add(self, name, color=0, shortcut=0):  # noqa: N802
        self.items.append(Category(name, color))
        return self.items[-1]

    def Remove(self, index):  # noqa: N802
        del self.items[index - 1]


class Namespace:
    def __init__(self, app):
        self.app = app
        self.Stores = Collection()
        self.Categories = Categories([Category("Urgente", 1), Category("Seguimiento", 2)])
        self.shared = {}

    @property
    def DefaultStore(self):  # noqa: N802
        return self.Stores.Item(1)

    def _all_stores(self):
        return list(self.Stores.items) + [s for s in self.shared.values() if s not in self.Stores.items]

    def GetFolderFromID(self, entry_id, store_id=None):  # noqa: N802
        for store in self._all_stores():
            if entry_id in store.folders and (store_id is None or store.StoreID == store_id):
                return store.folders[entry_id]
        raise ComError(-2147221233, "The operation failed. An object could not be found.", None, None)

    def GetItemFromID(self, entry_id, store_id=None):  # noqa: N802
        for store in self._all_stores():
            item = store.index.get(entry_id)
            if item is not None and item in item.folder.items:
                return item
        raise ComError(-2147221233, "The operation failed. An object could not be found.", None, None)

    def CreateRecipient(self, address):  # noqa: N802
        return Recipient(address, resolvable=address in self.shared)

    def GetSharedDefaultFolder(self, recipient, number):  # noqa: N802
        return self.shared[recipient.Address].default_folders[number]


class Explorer:
    def __init__(self):
        self.Selection = Collection()
        self.ActiveInlineResponse = None


class OutlookApp:
    def __init__(self):
        self.ns = Namespace(self)
        self.inspector = None
        self.explorer = Explorer()
        self.created = []

    def GetNamespace(self, name):  # noqa: N802
        assert name == "MAPI"
        return self.ns

    def ActiveInspector(self):  # noqa: N802
        return self.inspector

    def ActiveExplorer(self):  # noqa: N802
        return self.explorer

    def CreateItem(self, kind):  # noqa: N802
        drafts = self.ns.DefaultStore.default_folders[16]
        item = drafts.add_mail(sent=False)
        item.HTMLBody = "<html><body><p>--<br>Firma</p></body></html>"
        item.BodyFormat = 2
        self.created.append(item)
        return item


def build():
    """Perfil con un buzón propio, uno compartido (sin asignar) y un .pst."""
    app = OutlookApp()
    primary = OutlookStore("ana.torres@banco-demo.com").standard()
    pst = OutlookStore("Archivo 2025", store_type=3, file_path=r"C:\Users\ana\Archivo 2025.pst")
    pst.root.add_folder("Reclamaciones 2025").add_mail(subject="Reclamación R-2025-0101", body="Cargo no reconocido",
                                                      received=datetime(2025, 3, 1, 10), sender=("Cliente", "c@gmail.com"))
    app.ns.Stores.items += [primary, pst]
    shared = OutlookStore("Reclamaciones Fraude", store_type=1).standard({6: "Bandeja de entrada", 3: "Eliminados"})
    shared.default_folders[6].add_mail(subject="Reclamación R-2026-0042", body="Tarjeta 4539 1488 0343 6467",
                                       received=datetime(2026, 10, 10, 9), sender=("Laura", "laura@gmail.com"))
    app.ns.shared["fraude@banco-demo.com"] = shared
    inbox = primary.default_folders[6]
    claims = inbox.add_folder("Reclamaciones")
    inbox.add_mail(subject="Chargeback notification", sender=("Visa", "disputes@visa.com"), body="Case CLM-778100",
                   received=datetime(2026, 10, 18, 9), categories="Urgente; Seguimiento", unread=True,
                   attachments=["notice.pdf"])
    inbox.add_mail(subject="URGENT: verify your account", sender=("IT Service Desk", "it@banco-dem0.com"),
                   body="Verify your account within 24 hours", received=datetime(2026, 10, 19, 8),
                   html='<a href="http://evil.top/x">https://outlook.banco-demo.com</a>', reply_to="x@evil.top")
    inbox.add_mail(subject="Reunión", sender=("Marta Gil", "/O=EXCHANGELABS/OU=EXCHANGE/CN=MARTA"),
                   body="Nos vemos a las 10:30", received=datetime(2026, 9, 1, 8), flagged=True)
    claims.add_mail(subject="Reclamación R-2026-0007", sender=("Jorge", "jorge@hotmail.com"),
                    body="Cargo de 120,00 € en TechStore", received=datetime(2026, 8, 2, 12))
    primary.default_folders[16].add_mail(
        subject="Chargeback docs", to="disputes@visa.com", sent=False, received=datetime(2026, 10, 20, 7),
        body="Dear team,\ni am writting to informe you about the case.\nThanks\n\nFrom: Visa\nSent: Monday\nold")
    return app
