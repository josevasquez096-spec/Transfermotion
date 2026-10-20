"""Búsqueda avanzada de correos con una sintaxis parecida a la de Gmail, en español, inglés y francés.

    fraude tarjeta                    las dos palabras (asunto, remitente, destinatarios, etiquetas o cuerpo)
    "cargo no reconocido"             frase exacta
    from:visa.com asunto:alerta       por campo (from/de, to/para, subject/asunto, body/cuerpo…)
    -boletín                          excluye
    contracargo OR chargeback         cualquiera de las dos (OR se aplica antes que el «y» implícito)
    (urgente OR prioritario) is:unread
    has:attachment has:card is:external is:phishing
    after:2026-09-01 before:01/10/2026 newer:30d size:>2mb
    re:"R-\\d{4}-\\d+"  subject:/^RE:/   expresiones regulares

`Query(texto).matches(msg, loader)` evalúa un correo: primero las condiciones baratas y, solo si hace falta,
carga el cuerpo. `to_dasl()` da un prefiltro para Outlook que nunca descarta un correo que la búsqueda aceptaría.
"""

import operator
import re
import unicodedata
from datetime import datetime, timedelta

from . import detectors


class QueryError(Exception):
    """Error en la búsqueda; `code` es el sufijo de la clave de traducción (q_err_…)."""

    def __init__(self, code, detail=""):
        super().__init__(f"{code}: {detail}" if detail else code)
        self.code = code
        self.detail = detail


# ---------------------------------------------------------------- normalización

_FOLD = {0x2018: "'", 0x2019: "'", 0x201C: '"', 0x201D: '"', 0x2013: "-", 0x2014: "-", 0x2011: "-"}
for _code in range(0xC0, 0x250):
    _base = "".join(c for c in unicodedata.normalize("NFKD", chr(_code)) if not unicodedata.combining(c))
    if _base and _base != chr(_code):
        _FOLD[_code] = _base
for _code in range(0x300, 0x370):  # acentos combinados
    _FOLD[_code] = None
_SPACES = re.compile(r"\s+")


def fold(text):
    """Minúsculas, sin acentos y con los espacios unificados: «Reclamación  Nº» → «reclamacion no»."""
    return _SPACES.sub(" ", (text or "").lower().translate(_FOLD))


def _key(word):
    return re.sub(r"[-_\s']", "", fold(word))


def _aliases(table):
    return {_key(alias): name for name, aliases in table.items() for alias in aliases}


FIELDS = _aliases({
    "subject": ("subject", "asunto", "sujet", "objet"),
    "from": ("from", "de", "remitente", "expediteur"),
    "to": ("to", "para", "destinatario", "destinataire"),
    "cc": ("cc",),
    "body": ("body", "cuerpo", "corps", "text", "texto", "texte"),
    "category": ("category", "categoria", "categorie", "tag", "etiqueta", "etiquette", "label"),
    "domain": ("domain", "dominio", "domaine"),
    "folder": ("folder", "in", "carpeta", "en", "dossier", "dans"),
    "filename": ("filename", "attachment", "adjunto", "archivo", "fichier", "pj"),
    "has": ("has", "tiene", "con", "avec"),
    "is": ("is", "es", "est"),
    "after": ("after", "since", "desde", "despues", "apres", "depuis"),
    "before": ("before", "until", "hasta", "antes", "avant"),
    "on": ("on", "date", "fecha"),
    "newer": ("newer", "newer_than", "ultimos", "recientes", "derniers", "recents"),
    "older": ("older", "older_than", "mas_antiguos", "plus_anciens"),
    "size": ("size", "tamano", "taille"),
    "larger": ("larger", "mayor", "plus_grand"),
    "smaller": ("smaller", "menor", "plus_petit"),
    "importance": ("importance", "importancia", "prioridad", "priorite"),
    "re": ("re", "regex", "regexp"),
})
HAS = _aliases({
    "attachment": ("attachment", "attachments", "adjunto", "adjuntos", "archivo", "pj", "piece_jointe", "fichier"),
    "card": ("card", "cards", "tarjeta", "tarjetas", "carte", "cartes", "pan"),
    "iban": ("iban", "ibans", "rib"),
    "claim": ("claim", "claims", "reclamacion", "reclamaciones", "reclamation", "reclamations", "caso", "case"),
    "phone": ("phone", "telefono", "telephone", "tel"),
    "amount": ("amount", "importe", "monto", "montant"),
    "link": ("link", "links", "url", "enlace", "enlaces", "lien", "liens"),
    "category": ("category", "categories", "categoria", "categorias", "tag", "etiqueta", "etiquetas", "etiquette"),
    "flag": ("flag", "bandera", "drapeau"),
})
IS = _aliases({
    "unread": ("unread", "no_leido", "nonlu", "non_lu"),
    "read": ("read", "leido", "lu"),
    "flagged": ("flagged", "starred", "marcado", "seguimiento", "suivi"),
    "important": ("important", "importante"),
    "external": ("external", "externo", "externe"),
    "internal": ("internal", "interno", "interne"),
    "phishing": ("phishing", "suspicious", "sospechoso", "suspect"),
    "uncategorized": ("uncategorized", "untagged", "sin_categoria", "sin_etiqueta", "sans_categorie"),
})
IMPORTANCE = _aliases({2: ("high", "alta", "haute"), 1: ("normal", "normale"), 0: ("low", "baja", "basse")})
TODAY = {_key(w) for w in ("today", "hoy", "aujourd'hui")}
YESTERDAY = {_key(w) for w in ("yesterday", "ayer", "hier")}
OR_WORDS = {"OR", "O", "OU", "|"}
AND_WORDS = {"AND", "Y", "ET", "&"}
TEXT_FIELDS = ("any", "subject", "from", "to", "cc", "body")
# Campos del correo que mira cada búsqueda de texto (el cuerpo siempre al final: es lo único que hay que cargar).
SOURCES = {"any": ("subject", "sender_name", "sender_email", "to", "cc", "categories", "body"),
           "subject": ("subject",), "from": ("sender_name", "sender_email"), "to": ("to",), "cc": ("cc",),
           "body": ("body",)}
# Propiedades equivalentes en las búsquedas DASL de Outlook.
DASL_PROPS = {
    "subject": ('"urn:schemas:httpmail:subject"',),
    "from": ('"urn:schemas:httpmail:sendername"', '"urn:schemas:httpmail:fromemail"',
             '"http://schemas.microsoft.com/mapi/proptag/0x5D01001F"'),
    "to": ('"urn:schemas:httpmail:displayto"',),
    "cc": ('"urn:schemas:httpmail:displaycc"',),
    "body": ('"urn:schemas:httpmail:textdescription"',),
}
DASL_PROPS["any"] = (DASL_PROPS["subject"] + DASL_PROPS["from"] + DASL_PROPS["to"] + DASL_PROPS["cc"]
                     + ('"urn:schemas-microsoft-com:office:office#Keywords"',) + DASL_PROPS["body"])
DASL_UNSAFE = re.compile(r"[%_\[\]\\\"]")
# Fragmentos que la normalización no cambia (sin letras, comillas ni guiones): se pueden buscar tal cual en Outlook.
STABLE_RUN = re.compile(r"[0-9@./#:+=*&$€£,;]{3,}")


# ---------------------------------------------------------------- nodos

class Node:
    cost = 0  # 0 = basta la lista de correos, 1 = necesita el cuerpo, 2 = necesita también el HTML

    def match(self, ev):
        raise NotImplementedError


class And(Node):
    def __init__(self, items):
        self.items = sorted(items, key=lambda n: n.cost)  # lo barato primero
        self.cost = max((n.cost for n in items), default=0)

    def match(self, ev):
        return all(n.match(ev) for n in self.items)


class Or(Node):
    def __init__(self, items):
        self.items = sorted(items, key=lambda n: n.cost)
        self.cost = max(n.cost for n in items)

    def match(self, ev):
        return any(n.match(ev) for n in self.items)


class Not(Node):
    def __init__(self, item):
        self.item = item
        self.cost = item.cost

    def match(self, ev):
        return not self.item.match(ev)


class Text(Node):
    def __init__(self, field, value, regex=False, whole_word=False, exact=False):
        self.field, self.value, self.regex, self.exact = field, value, regex, exact
        self.cost = 1 if field in ("any", "body") else 0
        self.pattern = None
        if regex:
            try:
                self.pattern = re.compile(value, 0 if exact else re.I)
            except re.error as exc:
                raise QueryError("regex", f"{value} ({exc})") from None
            self.needle = ""
        else:
            self.needle = (_SPACES.sub(" ", value) if exact else fold(value)).strip()
            if whole_word:
                self.pattern = re.compile(r"(?<!\w)" + re.escape(self.needle) + r"(?!\w)")

    def match(self, ev):
        for name in SOURCES[self.field]:
            if self.regex:
                if self.pattern.search(ev.raw(name)):
                    return True
            else:
                text = ev.text(name, folded=not self.exact)
                if (self.pattern.search(text) if self.pattern else self.needle in text):
                    return True
        return False


class Category(Node):
    def __init__(self, value, whole_word=False, exact=False):
        self.value = value if exact else fold(value)
        self.whole_word, self.exact = whole_word, exact

    def match(self, ev):
        for cat in ev.msg.categories:
            cat = cat if self.exact else fold(cat)
            if cat == self.value or (not self.whole_word and self.value in cat):
                return True
        return False


class Domain(Node):
    def __init__(self, value):
        self.value = value.strip().lstrip("@").lower()

    def match(self, ev):
        domain = ev.msg.domain
        if "." not in self.value:
            return self.value in domain
        return domain == self.value or domain.endswith("." + self.value)


class Folder(Node):
    def __init__(self, value):
        self.value = fold(value)

    def match(self, ev):
        return self.value in fold(ev.msg.folder_path)


class Filename(Node):
    cost = 1

    def __init__(self, value):
        self.value = fold(value)

    def match(self, ev):
        if not ev.msg.has_attachments:
            return False
        ev.details()
        return any(self.value in fold(name) for name in ev.msg.attachments)


class Has(Node):
    BODY = ("card", "iban", "claim", "phone", "amount", "link")

    def __init__(self, kind, claim_pattern):
        self.kind, self.claim_pattern = kind, claim_pattern
        self.cost = 1 if kind in self.BODY else 0

    def match(self, ev):
        msg = ev.msg
        if self.kind == "attachment":
            return msg.has_attachments
        if self.kind == "category":
            return bool(msg.categories)
        if self.kind == "flag":
            return msg.flagged
        return bool(ev.found(self.kind, self.claim_pattern))


class Is(Node):
    def __init__(self, kind):
        self.kind = kind
        self.cost = 2 if kind == "phishing" else 0

    def match(self, ev):
        msg, kind = ev.msg, self.kind
        if kind in ("unread", "read"):
            return msg.unread == (kind == "unread")
        if kind == "flagged":
            return msg.flagged
        if kind == "important":
            return msg.importance == 2
        if kind == "uncategorized":
            return not msg.categories
        if kind in ("external", "internal"):
            return ev.external == (kind == "external")
        return ev.phishing >= detectors.PHISHING_THRESHOLD


class Importance(Node):
    def __init__(self, level):
        self.level = level

    def match(self, ev):
        return ev.msg.importance == self.level


class DateRange(Node):
    def __init__(self, start=None, end=None):
        self.start, self.end = start, end

    def match(self, ev):
        received = ev.msg.received
        if received is None:
            return False
        return (self.start is None or received >= self.start) and (self.end is None or received < self.end)


SIZE_OPS = {">": operator.gt, ">=": operator.ge, "<": operator.lt, "<=": operator.le, "=": operator.eq}


class Size(Node):
    def __init__(self, op, size):
        self.op, self.size = op, size

    def match(self, ev):
        return SIZE_OPS[self.op](ev.msg.size or 0, self.size)


class Ev:
    """Correo en evaluación: guarda los textos normalizados y carga el cuerpo solo cuando hace falta."""

    def __init__(self, msg, loader=None, internal_domains=()):
        self.msg = msg
        self.loader = loader
        self.internal = {d.strip().lstrip("@").lower() for d in internal_domains if d and d.strip()}
        self._texts = {}
        self._found = {}
        self._phishing = None

    def details(self, html=False):
        msg = self.msg
        if self.loader is not None and (msg.body is None or (html and msg.html is None)):
            self.loader(msg, html)

    @property
    def body(self):
        self.details()
        return self.msg.body or ""

    @property
    def html(self):
        self.details(html=True)
        return self.msg.html or ""

    def raw(self, name):
        if name == "body":
            return self.body
        if name == "categories":
            return " ".join(self.msg.categories)
        return getattr(self.msg, name) or ""

    def text(self, name, folded=True):
        key = (name, folded)
        if key not in self._texts:
            raw = self.raw(name)
            self._texts[key] = fold(raw) if folded else _SPACES.sub(" ", raw)
        return self._texts[key]

    def found(self, kind, claim_pattern=None):
        """Datos encontrados en asunto y cuerpo (tarjetas, IBAN, reclamaciones…), calculados una vez."""
        if kind not in self._found:
            text = f"{self.msg.subject}\n{self.body}"
            if kind == "claim":
                self._found[kind] = detectors.find_claims(text, claim_pattern or detectors.DEFAULT_CLAIM_REGEX)
            else:
                self._found[kind] = detectors.DETECTORS[kind](text)
        return self._found[kind]

    @property
    def external(self):
        domain = self.msg.domain
        return bool(domain) and not any(domain == d or domain.endswith("." + d) for d in self.internal)

    @property
    def phishing(self):
        if self._phishing is None:
            self._phishing = detectors.phishing_score(self.msg, self.body, self.html, self.internal)[0]
        return self._phishing


# ---------------------------------------------------------------- análisis del texto

def _quoted(text, i):
    end = text.find('"', i + 1)
    if end < 0:
        return text[i + 1:], len(text)
    return text[i + 1:end], end + 1


def _tokens(text):
    """Divide la búsqueda en («lp», neg, campo) («rp»,) («or»,) y («term», neg, campo, valor, tipo)."""
    out, i, n = [], 0, len(text)
    while i < n:
        c = text[i]
        if c.isspace():
            i += 1
            continue
        neg = False
        if c == "-" and i + 1 < n and not text[i + 1].isspace():
            neg, i = True, i + 1
            c = text[i]
        if c == "(":
            out.append(("lp", neg, None))
            i += 1
            continue
        if c == ")":
            out.append(("rp",))
            i += 1
            continue
        if c == '"':
            value, i = _quoted(text, i)
            if value.strip():
                out.append(("term", neg, None, value, "phrase"))
            continue
        j = i
        while j < n and not text[j].isspace() and text[j] not in '()":':
            j += 1
        field = FIELDS.get(_key(text[i:j])) if j < n and text[j] == ":" and j > i else None
        if field:
            j += 1
            if j < n and text[j] == '"':
                value, j = _quoted(text, j)
                kind = "phrase"
            elif j < n and text[j] == "(" and field != "re":
                out.append(("lp", neg, field))
                i = j + 1
                continue
            else:
                k = j
                free = field == "re" or text[j:j + 1] == "/"  # las expresiones regulares pueden llevar paréntesis
                while k < n and not text[k].isspace() and (free or text[k] not in "()"):
                    k += 1
                value, j, kind = text[j:k], k, "word"
            if len(value) > 2 and value.startswith("/") and value.endswith("/"):
                value, kind = value[1:-1], "regex"
            if value:
                out.append(("term", neg, field, value, kind))
            i = j
            continue
        k = i
        free = text[i] == "/"
        while k < n and not text[k].isspace() and (free or text[k] not in '()"'):
            k += 1
        word, i = text[i:k], k
        if not neg and word in OR_WORDS:
            out.append(("or",))
        elif not neg and word in AND_WORDS:
            continue
        elif len(word) > 2 and word.startswith("/") and word.endswith("/"):
            out.append(("term", neg, None, word[1:-1], "regex"))
        else:
            out.append(("term", neg, None, word, "word"))
    return out


class _Parser:
    """Como en Gmail, OR une más que el «y» implícito: «a b OR c» = a y (b o c)."""

    def __init__(self, tokens, build):
        self.tokens, self.pos, self.build = tokens, 0, build

    def peek(self):
        return self.tokens[self.pos][0] if self.pos < len(self.tokens) else None

    def take(self):
        self.pos += 1
        return self.tokens[self.pos - 1] if self.pos <= len(self.tokens) else None

    def parse(self):
        node = self.sequence(None)
        if self.peek() is not None:
            raise QueryError("paren")
        return node

    def sequence(self, field):
        items = []
        while self.peek() not in (None, "rp"):
            if self.peek() == "or":  # «OR» sin nada a la izquierda
                self.take()
                continue
            items.append(self.alternatives(field))
        return items[0] if len(items) == 1 else And(items)

    def alternatives(self, field):
        options = [self.unary(field)]
        while self.peek() == "or":
            self.take()
            if self.peek() in (None, "rp", "or"):
                break
            options.append(self.unary(field))
        return options[0] if len(options) == 1 else Or(options)

    def unary(self, field):
        token = self.take()
        if token[0] == "lp":
            node = self.sequence(token[2] or field)
            if self.take() is None:
                raise QueryError("paren")
            return Not(node) if token[1] else node
        _, neg, own_field, value, kind = token
        node = self.build(own_field or field, value, kind)
        return Not(node) if neg else node


# ---------------------------------------------------------------- consulta

_REL = re.compile(r"^(\d+)([a-z]*)$")
_UNITS = {"h": 1 / 24, "d": 1, "j": 1, "w": 7, "s": 7, "m": 30, "y": 365, "a": 365}
_ISO = re.compile(r"^(\d{4})[-/.](\d{1,2})[-/.](\d{1,2})$")
_DMY = re.compile(r"^(\d{1,2})[-/.](\d{1,2})[-/.](\d{4}|\d{2})$")
_SIZE = re.compile(r"^(>=|<=|>|<|=)?(\d+(?:[.,]\d+)?)([kmg]?)(?:i?[bo])?$")


class Query:
    def __init__(self, text, whole_word=False, exact=False, dayfirst=True, claim_pattern=None, now=None):
        self.text = (text or "").strip()
        self.whole_word, self.exact, self.dayfirst = whole_word, exact, dayfirst
        self.claim_pattern = claim_pattern or detectors.DEFAULT_CLAIM_REGEX
        self.now = now or datetime.now()
        self.root = _Parser(_tokens(self.text), self._build).parse() if self.text else And([])

    @property
    def empty(self):
        return isinstance(self.root, And) and not self.root.items

    @property
    def needs_body(self):
        return self.root.cost >= 1

    def matches(self, msg, loader=None, internal_domains=()):
        return self.root.match(Ev(msg, loader, internal_domains))

    def _top(self):
        return self.root.items if isinstance(self.root, And) else [self.root]

    def date_floor(self):
        """Fecha mínima que exige la búsqueda (para dejar de recorrer una carpeta ordenada por fecha)."""
        floors = [n.start for n in self._top() if isinstance(n, DateRange) and n.start]
        return max(floors) if floors else None

    # -------- construcción de nodos
    def _build(self, field, value, kind):
        field = field or "any"
        if field == "re" or (kind == "regex" and field in TEXT_FIELDS):
            return Text("any" if field == "re" else field, value, regex=True, exact=self.exact)
        if field in TEXT_FIELDS:
            return Text(field, value, whole_word=self.whole_word, exact=self.exact)
        if field == "category":
            return Category(value, self.whole_word, self.exact)
        if field == "domain":
            return Domain(value)
        if field == "folder":
            return Folder(value)
        if field == "filename":
            return Filename(value)
        if field == "has":
            if _key(value) not in HAS:
                raise QueryError("has", value)
            return Has(HAS[_key(value)], self.claim_pattern)
        if field == "is":
            if _key(value) not in IS:
                raise QueryError("is", value)
            return Is(IS[_key(value)])
        if field == "importance":
            if _key(value) not in IMPORTANCE:
                raise QueryError("importance", value)
            return Importance(IMPORTANCE[_key(value)])
        if field in ("size", "larger", "smaller"):
            return self._size(field, value)
        return self._date(field, value)

    def _size(self, field, value):
        m = _SIZE.match(value.lower().replace(" ", ""))
        if not m:
            raise QueryError("size", value)
        op = m.group(1) or {"size": ">=", "larger": ">=", "smaller": "<"}[field]
        number = float(m.group(2).replace(",", "."))
        return Size(op, int(number * {"": 1, "k": 1024, "m": 1024 ** 2, "g": 1024 ** 3}[m.group(3)]))

    def _point(self, value):
        """Fecha absoluta (2026-10-01, 01/10/2026), relativa (7d, 2w, 3m) u hoy/ayer."""
        key = _key(value)
        today = datetime(self.now.year, self.now.month, self.now.day)
        if key in TODAY:
            return today
        if key in YESTERDAY:
            return today - timedelta(days=1)
        m = _ISO.match(value)
        if m:
            y, mo, d = (int(g) for g in m.groups())
        elif _DMY.match(value):
            a, b, y = (int(g) for g in _DMY.match(value).groups())
            y += 2000 if y < 100 else 0
            d, mo = (a, b) if (self.dayfirst and b <= 12) or a > 12 else (b, a)
        else:
            m = _REL.match(key)
            unit = (m.group(2) or "d")[0] if m else ""
            if unit not in _UNITS or int(m.group(1)) * _UNITS[unit] > 36500:
                raise QueryError("date", value)
            return self.now - timedelta(days=int(m.group(1)) * _UNITS[unit])
        try:
            return datetime(y, mo, d)
        except ValueError:
            raise QueryError("date", value) from None

    def _date(self, field, value):
        moment = self._point(value)
        if field in ("after", "newer"):
            return DateRange(start=moment)
        if field in ("before", "older"):
            return DateRange(end=moment)
        start = datetime(moment.year, moment.month, moment.day)
        return DateRange(start=start, end=start + timedelta(days=1))

    # -------- prefiltro para Outlook
    def to_dasl(self):
        """Filtro DASL («@SQL=…») con las condiciones que Outlook puede comprobar sin perder resultados.

        Es un superconjunto: los correos que devuelve se vuelven a evaluar con `matches`."""
        parts = [p for p in (self._dasl(n) for n in self._top()) if p]
        return "@SQL=" + " AND ".join(parts) if parts else ""

    def _dasl(self, node):
        if isinstance(node, Text) and not node.regex:
            pieces = node.needle.split(" ") if self.exact else STABLE_RUN.findall(node.needle)
            conds = []
            for piece in pieces:
                if piece and not DASL_UNSAFE.search(piece):
                    literal = piece.replace("'", "''")
                    props = DASL_PROPS[node.field]
                    cond = " OR ".join(f"{p} LIKE '%{literal}%'" for p in props)
                    conds.append(f"({cond})" if len(props) > 1 else cond)
            return " AND ".join(conds) or None
        if isinstance(node, Or):
            parts = [self._dasl(n) for n in node.items]
            return "(" + " OR ".join(f"({p})" for p in parts) + ")" if all(parts) else None
        if isinstance(node, Is):
            return {"unread": '"urn:schemas:httpmail:read" = 0', "read": '"urn:schemas:httpmail:read" = 1',
                    "important": '"urn:schemas:httpmail:importance" = 2',
                    "flagged": '"http://schemas.microsoft.com/mapi/proptag/0x10900003" = 2'}.get(node.kind)
        if isinstance(node, Has) and node.kind == "attachment":
            return '"urn:schemas:httpmail:hasattachment" = 1'
        if isinstance(node, Importance):
            return f'"urn:schemas:httpmail:importance" = {node.level}'
        if isinstance(node, Size):
            return f'"http://schemas.microsoft.com/mapi/proptag/0x0E080003" {node.op} {node.size}'
        return None

    # -------- resaltado
    def highlights(self):
        """Expresiones para resaltar en la vista previa los textos buscados (no los excluidos)."""
        out = []

        def walk(node):
            if isinstance(node, (And, Or)):
                for item in node.items:
                    walk(item)
            elif isinstance(node, Text) and node.field in ("any", "subject", "body"):
                if node.regex:
                    out.append(node.pattern)
                elif node.needle:
                    out.append(re.compile(_loose(node.value.strip(), self.exact), 0 if self.exact else re.I))

        walk(self.root)
        return out


_VARIANTS = {"a": "aáàâäãå", "e": "eéèêë", "i": "iíìîï", "o": "oóòôöõ", "u": "uúùûü", "n": "nñ", "c": "cç",
             "y": "yýÿ"}


def _loose(value, exact):
    """Patrón que también encuentra la palabra con o sin acentos («reclamacion» → «reclamación»)."""
    out = []
    for ch in _SPACES.sub(" ", value):
        low = fold(ch)
        if ch.isspace():
            out.append(r"\s+")
        elif not exact and low in _VARIANTS:
            out.append(f"[{_VARIANTS[low]}]")
        else:
            out.append(re.escape(ch))
    return "".join(out)


# ---------------------------------------------------------------- reglas de Outlook

RULE_TEXT = {"subject": "subject", "body": "body", "any": "body_or_subject", "from": "sender_address"}


def _rule_kind(node):
    if isinstance(node, Text) and not node.regex:
        if node.field == "from" and " " in node.value.strip():
            return None  # Outlook compara con la dirección, no con el nombre
        return RULE_TEXT.get(node.field)
    if isinstance(node, Domain):
        return "sender_address"
    if isinstance(node, Has) and node.kind == "attachment":
        return "has_attachment"
    if isinstance(node, (Importance, Is)) and getattr(node, "kind", "important") == "important":
        return "importance"
    return None


def outlook_conditions(query):
    """Traduce la búsqueda a condiciones y excepciones de una regla de Outlook, o None si no se puede.

    Outlook une con OR los textos de una misma condición y con Y las condiciones distintas; por eso solo se
    admiten búsquedas como «subject:(a OR b) from:visa.com -body:prueba»."""
    spec = {"conditions": {}, "exceptions": {}}
    for node in query._top():
        target = spec["conditions"]
        if isinstance(node, Not):
            target, node = spec["exceptions"], node.item
        options = node.items if isinstance(node, Or) else [node]
        kinds = {_rule_kind(n) for n in options}
        if len(kinds) != 1 or None in kinds:
            return None
        kind = kinds.pop()
        if kind in target:
            return None
        if kind == "has_attachment":
            if len(options) > 1:
                return None
            target[kind] = True
        elif kind == "importance":
            if len(options) > 1:
                return None
            target[kind] = getattr(options[0], "level", 2)
        else:
            target[kind] = [n.value.strip() if isinstance(n, Text) else n.value for n in options]
    return spec if spec["conditions"] else None
