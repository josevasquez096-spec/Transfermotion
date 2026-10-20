"""Reglas locales de MailPilot: una búsqueda y unas acciones (mover, etiquetar, marcar como leído o para
seguimiento).

Se prueban sin tocar nada (`plan`), se ejecutan sobre las carpetas elegidas (`execute`) y, si la búsqueda es
sencilla, se convierten en una regla de Outlook que se aplica sola a los correos nuevos (`to_outlook`).
"""

from dataclasses import asdict, dataclass, field, fields

from .query import Query, QueryError, outlook_conditions


@dataclass
class MailRule:
    name: str
    query: str
    enabled: bool = True
    folder_store: str = ""  # nombre del almacén de la carpeta destino
    folder_path: str = ""  # ruta de la carpeta destino ("" = no mover)
    categories: list = field(default_factory=list)
    mark_read: bool = False
    flag: bool = False

    @classmethod
    def from_dict(cls, data):
        names = {f.name for f in fields(cls)}
        return cls(**{k: v for k, v in data.items() if k in names})

    def to_dict(self):
        return asdict(self)


@dataclass
class Planned:
    msg: object
    rules: list
    move_to: str | None = None  # id de la carpeta destino
    add: list = field(default_factory=list)
    mark_read: bool = False
    flag: bool = False


def find_folder(stores, folders, store_name, path):
    """Id de la carpeta con esa ruta, en el almacén con ese nombre (o en el primero que la tenga)."""
    for store in stores:
        if store_name and store.name != store_name:
            continue
        for folder in folders.get(store.id, []):
            if folder.depth > 0 and folder.path == path:
                return folder.id
    return None


def compile_rules(rules, **query_options):
    out = []
    for rule in rules:
        if rule.enabled and rule.query.strip():
            try:
                out.append((rule, Query(rule.query, **query_options)))
            except QueryError as exc:
                raise QueryError(exc.code, f"{rule.name}: {exc.detail}") from None
    return out


def plan(rules, messages, resolve, loader=None, internal_domains=(), **query_options):
    """Qué haría cada regla activa con cada correo, sin cambiar nada.

    `resolve(regla)` devuelve el id de la carpeta destino (o None). Si varias reglas coinciden, se suman sus
    etiquetas y marcas; el correo se mueve a la carpeta de la primera que tenga destino."""
    compiled = compile_rules(rules, **query_options)
    out = []
    for msg in messages:
        hits = [rule for rule, query in compiled if query.matches(msg, loader, internal_domains)]
        if not hits:
            continue
        move = next((resolve(r) for r in hits if r.folder_path), None)
        have = {c.lower() for c in msg.categories}
        add = list(dict.fromkeys(c for r in hits for c in r.categories if c.lower() not in have))
        step = Planned(msg, [r.name for r in hits], move if move != msg.folder_id else None, add,
                       any(r.mark_read for r in hits) and msg.unread, any(r.flag for r in hits) and not msg.flagged)
        if step.move_to or step.add or step.mark_read or step.flag:
            out.append(step)
    return out


def execute(backend, planned):
    """Aplica el plan agrupando operaciones. Mueve al final, porque mover cambia el identificador del correo."""
    counts = {"categorized": 0, "read": 0, "flagged": 0, "moved": 0}
    groups = {}
    for step in planned:
        if step.add:
            groups.setdefault(tuple(step.add), []).append(step.msg)
    for add, messages in groups.items():
        counts["categorized"] += backend.set_categories(messages, add=add)
    read = [s.msg for s in planned if s.mark_read]
    if read:
        counts["read"] = backend.mark_read(read, True)
    flag = [s.msg for s in planned if s.flag]
    if flag:
        counts["flagged"] = backend.set_flag(flag, True)
    moves = {}
    for step in planned:
        if step.move_to:
            moves.setdefault(step.move_to, []).append(step.msg)
    for folder_id, messages in moves.items():
        counts["moved"] += backend.move_messages(messages, folder_id)
    return counts


def to_outlook(rule):
    """(condiciones, avisos) para crear la regla en Outlook; (None, avisos) si la búsqueda no se puede traducir."""
    spec = outlook_conditions(Query(rule.query))
    if spec is None:
        return None, ["rule_not_convertible"]
    notes = ["rule_note_read"] if rule.mark_read else []  # las reglas de Outlook no marcan como leído
    if not (rule.folder_path or rule.categories or rule.flag):
        return None, ["rule_no_actions"]
    return spec, notes
