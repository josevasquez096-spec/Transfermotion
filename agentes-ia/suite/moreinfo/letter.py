"""No Pay Decision Letter from a blank Word template (.docx) filled inside the app.

Fields that are detected (and filled in place, keeping the template's layout):
- Content controls (Developer tab): plain/rich text, drop-down list, combo box and date picker. The label shown in
  the app is the control's Title (or Tag). Controls with the same Title/Tag, or bound to the same data, share one
  value: type the customer name once and it appears everywhere (for example also as a title further down).
- Legacy form fields (FORMTEXT and FORMDROPDOWN) and REF fields that repeat them.
- Placeholders written in the text: [Customer Name] or {{Customer Name}}.

Several values for one field (for example more than one decline reason): allowed when the control is inside a Word
repeating section, or when a drop-down is alone on its line (a bullet). Each extra value repeats that item or line.
"""

import re
import shutil
import tempfile
import zipfile
from copy import deepcopy
from dataclasses import dataclass, field
from pathlib import Path

from lxml import etree

W_NS = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"
W14_NS = "http://schemas.microsoft.com/office/word/2010/wordml"
W15_NS = "http://schemas.microsoft.com/office/word/2012/wordml"
DONE = "{urn:moreinfo-pilot}done"  # marcas temporales: control ya rellenado / control copiado
COPY = "{urn:moreinfo-pilot}copy"
W = f"{{{W_NS}}}"
PARTS = re.compile(r"word/(document|header\d*|footer\d*)\.xml")
PLACEHOLDER = re.compile(r"\{\{\s*([^{}\n]{1,60}?)\s*\}\}|\[([^\[\]\n]{2,60})\]")


@dataclass
class Field:
    key: str
    label: str
    kind: str = "text"  # text, dropdown, combo, date
    options: list = field(default_factory=list)
    value: str = ""
    count: int = 1  # veces que aparece en la carta
    multi: bool = False  # admite varios valores (p. ej. varias razones)


def _val(el, name):
    child = el.find(W + name) if el is not None else None
    return child.get(W + "val") if child is not None else None


def _text(el):
    return "".join(t.text or "" for t in el.iter(W + "t"))


def _parts(zf):
    names = [n for n in zf.namelist() if PARTS.fullmatch(n)]
    return sorted(names, key=lambda n: (not n.endswith("document.xml"), n))


def _leaf_sdts(tree):
    for sdt in tree.iter(W + "sdt"):
        content = sdt.find(W + "sdtContent")
        pr = sdt.find(W + "sdtPr")
        if content is None or pr is None or content.find(".//" + W + "sdt") is not None:
            continue
        if any(pr.find(W + tag) is not None for tag in ("docPartObj", "docPartList", "group", "citation",
                                                        "bibliography", "equation", "picture")):
            continue
        if pr.find(f"{{{W14_NS}}}checkbox") is not None:
            continue
        yield sdt, pr, content


def _sdt_key(pr, index):
    """Controls bound to the same data (Word mapping) are one field; otherwise the Tag/Title names the field."""
    binding = pr.find(W + "dataBinding")
    tag, alias = _val(pr, "tag"), _val(pr, "alias")
    if binding is not None and binding.get(W + "xpath"):
        xpath = binding.get(W + "xpath")
        return f"xp:{xpath}", alias or tag or xpath.rsplit("/", 1)[-1].split("[")[0].split(":")[-1]
    if tag or alias:
        return f"cc:{(tag or alias).strip().lower()}", alias or tag
    return f"cc:#{index}", None


def _repeat_unit(sdt, kind):
    """What is repeated for each extra value: the Word repeating-section item that holds the control or, for a
    drop-down alone on its line (a bullet), that paragraph. None when the field takes a single value."""
    for ancestor in sdt.iterancestors(W + "sdt"):
        pr = ancestor.find(W + "sdtPr")
        if pr is not None and pr.find(f"{{{W15_NS}}}repeatingSectionItem") is not None:
            return ancestor
    paragraph = sdt.getparent()
    if kind not in ("dropdown", "combo") or paragraph is None or paragraph.tag != W + "p":
        return None
    others = [el for el in paragraph if el is not sdt and el.tag != W + "pPr"]
    if any(el.tag in (W + "sdt", W + "fldSimple") or el.find(".//" + W + "fldChar") is not None for el in others):
        return None
    if re.sub(r"[\s.,;:•\-–]", "", "".join(_text(el) for el in others)):
        return None
    return paragraph


def _kind(pr):
    if pr.find(W + "date") is not None:
        return "date", []
    for tag, k in (("dropDownList", "dropdown"), ("comboBox", "combo")):
        lst = pr.find(W + tag)
        if lst is not None:
            options = [i.get(W + "displayText") or i.get(W + "value") or "" for i in lst.findall(W + "listItem")]
            return k, [o for o in options if o.strip()]
    return "text", []


def _form_fields(tree):
    """Legacy form fields: (paragraph, begin run, ffData, result runs) for each field."""
    for paragraph in tree.iter(W + "p"):
        runs = [r for r in paragraph.iter(W + "r")]
        current = None
        for run in runs:
            fld = run.find(W + "fldChar")
            if fld is not None:
                kind = fld.get(W + "fldCharType")
                if kind == "begin":
                    current = {"begin": run, "ff": fld.find(W + "ffData"), "instr": "", "result": [], "state": "code"}
                elif kind == "separate" and current:
                    current["state"] = "result"
                elif kind == "end" and current:
                    yield current
                    current = None
                continue
            if current is None:
                continue
            instr = run.find(W + "instrText")
            if current["state"] == "code" and instr is not None:
                current["instr"] += instr.text or ""
            elif current["state"] == "result":
                current["result"].append(run)


def _ref_name(instr):
    m = re.match(r"\s*REF\s+(\S+)", instr or "", re.I)
    return m.group(1).lower() if m else None


def scan(path):
    """Fields of the template, in the order they appear, merged when they share a name."""
    fields, order = {}, []

    def add(key, label, kind="text", options=(), value="", multi=False):
        if key in fields:
            fields[key].count += 1
            fields[key].multi |= multi
            for option in options:
                if option not in fields[key].options:
                    fields[key].options.append(option)
            return
        fields[key] = Field(key, (label or key.split(":", 1)[1]).strip(), kind, list(options), value, multi=multi)
        order.append(key)

    with zipfile.ZipFile(path) as zf:
        for name in _parts(zf):
            tree = etree.fromstring(zf.read(name))
            for n, (sdt, pr, content) in enumerate(_leaf_sdts(tree)):
                key, label = _sdt_key(pr, f"{name}{n}")
                showing = pr.find(W + "showingPlcHdr") is not None
                current = "" if showing else _text(content).strip()
                kind, options = _kind(pr)
                add(key, label or _text(content).strip() or f"Field {len(order) + 1}", kind, options, current,
                    multi=_repeat_unit(sdt, kind) is not None)
            for ff in _form_fields(tree):
                data = ff["ff"]
                if data is None:
                    continue
                fname = _val(data, "name") or f"field{len(order) + 1}"
                dd = data.find(W + "ddList")
                if dd is not None:
                    entries = [e.get(W + "val") for e in dd.findall(W + "listEntry")]
                    index = int(_val(dd, "result") or _val(dd, "default") or 0)
                    add(f"ff:{fname.lower()}", fname, "dropdown", entries,
                        entries[index] if 0 <= index < len(entries) else "")
                elif data.find(W + "textInput") is not None:
                    add(f"ff:{fname.lower()}", fname, "text", (), "".join(_text(r) for r in ff["result"]).strip())
            for paragraph in tree.iter(W + "p"):
                if any(a.tag == W + "sdtContent" for a in paragraph.iterancestors()):
                    continue
                for m in PLACEHOLDER.finditer(_text(paragraph)):
                    label = (m.group(1) or m.group(2)).strip()
                    add(f"ph:{label.lower()}", label)
    return [fields[k] for k in order]


MONTHS = {"fr": ("janvier", "février", "mars", "avril", "mai", "juin", "juillet", "août", "septembre", "octobre",
                  "novembre", "décembre"),
          "es": ("enero", "febrero", "marzo", "abril", "mayo", "junio", "julio", "agosto", "septiembre", "octubre",
                 "noviembre", "diciembre")}
_STOP = {"fr": {"le", "la", "les", "des", "vous", "votre", "nous", "madame", "monsieur", "et", "est", "pour"},
         "es": {"el", "los", "las", "usted", "su", "nosotros", "señor", "señora", "y", "para", "del"},
         "en": {"the", "you", "your", "we", "dear", "and", "is", "for", "of", "to"}}


def language(path):
    """Language of a template (en, fr or es), guessed from its words, for the default date format."""
    try:
        with zipfile.ZipFile(path) as zf:
            words = re.findall(r"[a-zà-ÿ]+", " ".join(_text(etree.fromstring(zf.read(n))) for n in _parts(zf)).lower())
    except Exception:
        return "en"
    scores = {lang: sum(w in stop for w in words) for lang, stop in _STOP.items()}
    return max(scores, key=scores.get) if any(scores.values()) else "en"


def today(lang="en", now=None):
    from datetime import date

    now = now or date.today()
    if lang in MONTHS:
        return f"{now.day} {MONTHS[lang][now.month - 1]} {now.year}"
    return f"{now:%B} {now.day}, {now.year}"

# ---------------------------------------------------------------- address typed on one line

PROVINCES = {  # código → nombres (inglés y francés)
    "AB": ("Alberta",), "BC": ("British Columbia", "Colombie-Britannique"), "MB": ("Manitoba",),
    "NB": ("New Brunswick", "Nouveau-Brunswick"), "NL": ("Newfoundland and Labrador", "Terre-Neuve-et-Labrador",
                                                          "Newfoundland"),
    "NS": ("Nova Scotia", "Nouvelle-Écosse"), "NT": ("Northwest Territories", "Territoires du Nord-Ouest"),
    "NU": ("Nunavut",), "ON": ("Ontario",), "PE": ("Prince Edward Island", "Île-du-Prince-Édouard", "PEI"),
    "QC": ("Quebec", "Québec", "PQ"), "SK": ("Saskatchewan",), "YT": ("Yukon",),
}
POSTAL = re.compile(r"\b([A-Za-z]\d[A-Za-z])[ -]?(\d[A-Za-z]\d)\b")
ZIP = re.compile(r"\b(\d{5}(?:-\d{4})?)\s*$")
UNIT = re.compile(r"(?:^|\s)((?:apt\.?|apartment|suite|ste\.?|unit|app\.?|appartement|bureau|room|#)\s*\S+)\s*$", re.I)
STREET_TYPES = {"st", "street", "ave", "avenue", "rd", "road", "blvd", "boulevard", "dr", "drive", "way", "lane", "ln",
                "cres", "crescent", "crt", "court", "ct", "pl", "place", "terr", "terrace", "trail", "trl", "pkwy",
                "parkway", "hwy", "highway", "cir", "circle", "sq", "square", "gate", "grove", "row", "line", "sideroad",
                "concession", "close", "path", "heights", "hts", "gardens", "gdns", "park", "walk", "cove", "mews"}
DIRECTIONS = {"n", "s", "e", "w", "ne", "nw", "se", "sw", "north", "south", "east", "west", "nord", "sud", "est",
              "ouest", "o"}
ADDRESS_ROLES = (  # (papel, palabras de la etiqueta del campo), en orden de prioridad
    ("line2", ("line 2", "address 2", "ligne 2", "adresse 2", "suite", "apt", "unit", "appartement")),
    ("postal", ("postal", "zip", "code postal")),
    ("province", ("province", "state", "prov")),
    ("city", ("city", "ville", "town", "municipalit")),
    ("line1", ("line 1", "address 1", "ligne 1", "adresse 1", "street", "rue", "address", "adresse")),
)


def _fold(text):
    import unicodedata

    return "".join(c for c in unicodedata.normalize("NFKD", text) if not unicodedata.combining(c)).casefold().strip()


def address_roles(fields):
    """Address fields of the template: {role: field key} for line1, line2, city, province and postal."""
    roles = {}
    for f in fields:
        if f.kind not in ("text", "dropdown", "combo") or f.multi:
            continue
        label = _fold(f.label)
        for role, words in ADDRESS_ROLES:
            if role not in roles and any(w in label for w in words):
                roles[role] = f.key
                break
    return roles if "line1" in roles and len(roles) >= 2 else {}


def _province(part):
    """(code, name as written, rest of the text) when the text ends with a province, otherwise None."""
    folded = _fold(part)
    names = sorted(((n, code) for code, ns in PROVINCES.items() for n in (code,) + ns), key=lambda x: -len(x[0]))
    for name, code in names:
        key = _fold(name)
        if folded == key or folded.endswith(" " + key):
            return code, part[len(part) - len(name):].strip(), part[:len(part) - len(name)].strip()
    return None


def province_option(code, written, options=()):
    """The province as the template's drop-down lists it (code or name), or as it was written."""
    if not options:
        return written if len(written) > 2 else code
    wanted = {_fold(n) for n in (code,) + PROVINCES[code]}
    return next((o for o in options if _fold(o) in wanted), "")


def _split_street(text):
    """«221 Main Street Apt 4B Toronto» (no commas) → street, unit, city, using the street type as the end."""
    words = text.split()
    for i in range(len(words) - 1, 0, -1):
        if _fold(words[i]).rstrip(".") in STREET_TYPES and any(c.isdigit() for c in " ".join(words[:i])):
            end = i + 1
            if end < len(words) and _fold(words[end]).rstrip(".") in DIRECTIONS:
                end += 1
            rest = words[end:]
            unit = ""
            if rest and rest[0].startswith("#") and len(rest[0]) > 1:  # «#12»
                unit, rest = rest[0], rest[1:]
            elif len(rest) > 1 and UNIT.match(" ".join(rest[:2])):  # «Apt 4B», «Suite 1801»
                unit, rest = " ".join(rest[:2]), rest[2:]
            return " ".join(words[:end]), unit, " ".join(rest)
    return text, "", ""


def split_address(text):
    """Splits an address typed on one line, e.g. «221 Main Street, Apt 4B, Toronto ON M5V 2T6» or
    «123 rue Principale, app. 4, Montréal (Québec) H2X 1Y4», into line1, line2, city, province (code and name as
    written) and postal. Parts that are not found are left out."""
    s = " ".join(text.replace("\n", ", ").replace("(", ",").replace(")", ",").split())
    out = {}
    matches = list(POSTAL.finditer(s))
    if matches:
        m = matches[-1]
        out["postal"] = f"{m.group(1)} {m.group(2)}".upper()
        s = s[:m.start()] + "," + s[m.end():]
    else:
        m = ZIP.search(s)
        if m:
            out["postal"], s = m.group(1), s[:m.start()]
    parts = [p.strip(" .;") for p in s.split(",") if p.strip(" .;")]
    if parts and _fold(parts[-1]) == "canada":
        parts.pop()
    if parts:
        found = _province(parts[-1])
        if found and (found[2] or len(parts) > 1):
            out["province"] = found[0]
            out["province_written"] = found[1]
            if found[2]:
                parts[-1] = found[2]
            else:
                parts.pop()
    if len(parts) == 1:
        line1, line2, city = _split_street(parts[0])
        parts = [line1] + ([line2] if line2 else []) + ([city] if city else [])
        if len(parts) == 1:
            out["line1"] = parts[0]
            return out
        out["city"] = parts.pop()
    elif len(parts) > 1:
        out["city"] = parts.pop()
    if parts:
        line1, rest = parts[0], parts[1:]
        unit = UNIT.search(line1)
        if not rest and unit and unit.start() > 0:  # «221 Main Street Apt 4B, Toronto»
            line1, rest = line1[:unit.start()].strip(), [unit.group(1)]
        out["line1"] = line1
        if rest:
            out["line2"] = ", ".join(rest)
    return out


def address_values(text, fields):
    """Values for the template's address fields from an address typed on one line. What has no field of its own
    goes with the closest field (e.g. the unit with the street when there is no line 2)."""
    roles = address_roles(fields)
    if not roles:
        return {}
    by_key = {f.key: f for f in fields}
    parts = split_address(text)
    if "province" in parts:
        field = by_key.get(roles.get("province"))
        options = field.options if field is not None and field.kind == "dropdown" else ()
        parts["province"] = province_option(parts["province"], parts.pop("province_written"), options)
    if "line2" in parts and "line2" not in roles:
        parts["line1"] = f"{parts['line1']}, {parts.pop('line2')}"
    if "city" in parts and "city" not in roles:
        parts["line1"] = f"{parts['line1']}, {parts.pop('city')}"
    for role in ("province", "postal"):
        if parts.get(role) and role not in roles:
            target = "city" if "city" in parts else "line1"
            parts[target] = f"{parts.get(target, '')} {parts.pop(role)}".strip()
    return {roles[role]: value for role, value in parts.items() if role in roles and value}


# ---------------------------------------------------------------- filling

def _set_runs_text(runs, value):
    texts = [t for r in runs for t in r.iter(W + "t")]
    if not texts:
        if not runs:
            return
        t = etree.SubElement(runs[0], W + "t")
        texts = [t]
    texts[0].text = value
    texts[0].set("{http://www.w3.org/XML/1998/namespace}space", "preserve")
    for t in texts[1:]:
        t.text = ""


def _fill_sdt(pr, content, value):
    texts = list(content.iter(W + "t"))
    if not texts:
        run = content.find(".//" + W + "r")
        if run is None:
            parent = content.find(W + "p")
            run = etree.SubElement(parent if parent is not None else content, W + "r")
        texts = [etree.SubElement(run, W + "t")]
    texts[0].text = value
    texts[0].set("{http://www.w3.org/XML/1998/namespace}space", "preserve")
    for t in texts[1:]:
        t.text = ""
    showing = pr.find(W + "showingPlcHdr")
    if showing is not None:
        pr.remove(showing)
    for style in list(content.iter(W + "rStyle")):  # quita el estilo gris del texto de ejemplo
        if "placeholder" in (style.get(W + "val") or "").lower():
            style.getparent().remove(style)


def _fill_placeholders(paragraph, values):
    texts = list(paragraph.iter(W + "t"))
    full = "".join(t.text or "" for t in texts)

    def repl(m):
        key = f"ph:{(m.group(1) or m.group(2)).strip().lower()}"
        return values.get(key, m.group(0))

    new = PLACEHOLDER.sub(repl, full)
    if new == full or not texts:
        return
    # se reparte el texto nuevo respetando los trozos (runs) que no cambian
    pos, out = 0, []
    starts = []
    for t in texts:
        starts.append(pos)
        pos += len(t.text or "")
    changed = [(m.start(), m.end()) for m in PLACEHOLDER.finditer(full)
               if f"ph:{(m.group(1) or m.group(2)).strip().lower()}" in values]
    for i, t in enumerate(texts):
        a, b = starts[i], starts[i] + len(t.text or "")
        if any(s < b and a < e for s, e in changed):
            out.append(i)
    if not out:
        return
    first, last = out[0], out[-1]
    a, b = starts[first], starts[last] + len(texts[last].text or "")
    segment = PLACEHOLDER.sub(repl, full[a:b])
    texts[first].text = segment
    texts[first].set("{http://www.w3.org/XML/1998/namespace}space", "preserve")
    for t in texts[first + 1:last + 1]:
        t.text = ""


def unique(values):
    """Non-empty values without repeats, in order (a reason chosen twice counts once)."""
    out = []
    for value in values:
        if value and value not in out:
            out.append(value)
    return out


def _flat(value):
    return "; ".join(unique(value)) if isinstance(value, (list, tuple)) else value


def _clean_clone(element):
    """A repeated item must not reuse the ids and bookmarks of the original."""
    for pr in element.iter(W + "sdtPr"):
        for el in pr.findall(W + "id"):
            pr.remove(el)
    for tag in ("bookmarkStart", "bookmarkEnd"):
        for el in list(element.iter(W + tag)):
            el.getparent().remove(el)
    for el in element.iter(W + "p"):
        for attr in (f"{{{W14_NS}}}paraId", f"{{{W14_NS}}}textId"):
            el.attrib.pop(attr, None)


def _repeat_values(tree, name, values):
    """Fields with several values: the item (or bullet line) is repeated once per extra value, in order."""
    for n, (sdt, pr, content) in enumerate(list(_leaf_sdts(tree))):
        key, _ = _sdt_key(pr, f"{name}{n}")
        value = values.get(key)
        if not isinstance(value, (list, tuple)) or len(unique(value)) < 2 or sdt.get(DONE):
            continue
        unit = _repeat_unit(sdt, _kind(pr)[0])
        if unit is None:
            continue
        items = unique(value)
        anchor = unit
        for item in items[1:]:
            clone = deepcopy(unit)
            _clean_clone(clone)
            for c_sdt, c_pr, c_content in _leaf_sdts(clone):
                c_sdt.set(COPY, "1")
                if _sdt_key(c_pr, "")[0] == key:
                    _fill_sdt(c_pr, c_content, item)
                    c_sdt.set(DONE, "1")
            anchor.addnext(clone)
            anchor = clone
        _fill_sdt(pr, content, items[0])
        sdt.set(DONE, "1")


def fill(template, values, dest):
    """Writes a copy of the template with the values (dict key → text, or a list of texts for a field that takes
    several values). Returns dest."""
    template, dest = Path(template), Path(dest)
    multi, values = values, {k: _flat(v) for k, v in values.items()}
    bookmarks = {}  # nombre de marcador → clave, para los campos REF que repiten un valor
    bindings = []  # (storeItemID, xpath, prefixMappings, value)
    with zipfile.ZipFile(template) as zf:
        contents = {n: zf.read(n) for n in zf.namelist()}
    trees = {n: etree.fromstring(contents[n]) for n in _parts(zipfile.ZipFile(template))}
    for name, tree in trees.items():
        _repeat_values(tree, name, multi)
        n = 0
        for sdt, pr, content in list(_leaf_sdts(tree)):
            copy, done = sdt.attrib.pop(COPY, None), sdt.attrib.pop(DONE, None)
            if copy or done:
                etree.cleanup_namespaces(sdt)  # sin rastro de las marcas temporales
            if copy is None:  # las copias no cuentan para los controles sin nombre
                key, _ = _sdt_key(pr, f"{name}{n}")
                n += 1
            else:
                key, _ = _sdt_key(pr, "")
            for mark in sdt.iter(W + "bookmarkStart"):
                bookmarks[(mark.get(W + "name") or "").lower()] = key
            if done:
                continue
            if key in values:
                _fill_sdt(pr, content, values[key])
                binding = pr.find(W + "dataBinding")
                if binding is not None:
                    bindings.append((binding.get(W + "storeItemID"), binding.get(W + "xpath"),
                                     binding.get(W + "prefixMappings") or "", values[key]))
        for ff in list(_form_fields(tree)):
            data = ff["ff"]
            if data is None:
                continue
            fname = (_val(data, "name") or "").lower()
            bookmarks.setdefault(fname, f"ff:{fname}")
            key = f"ff:{fname}"
            if key not in values:
                continue
            dd = data.find(W + "ddList")
            if dd is not None:
                entries = [e.get(W + "val") for e in dd.findall(W + "listEntry")]
                if values[key] in entries:
                    result = dd.find(W + "result")
                    if result is None:
                        result = etree.SubElement(dd, W + "result")
                    result.set(W + "val", str(entries.index(values[key])))
            else:
                _set_runs_text(ff["result"], values[key])
        for paragraph in tree.iter(W + "p"):
            if not any(a.tag == W + "sdtContent" for a in paragraph.iterancestors()):
                _fill_placeholders(paragraph, values)
    for tree in trees.values():  # campos REF: repiten el valor de otro campo
        for ff in list(_form_fields(tree)):
            ref = _ref_name(ff["instr"])
            if ref and bookmarks.get(ref) in values:
                _set_runs_text(ff["result"], values[bookmarks[ref]])
        for simple in tree.iter(W + "fldSimple"):
            ref = _ref_name(simple.get(W + "instr"))
            if ref and bookmarks.get(ref) in values:
                _set_runs_text(list(simple.iter(W + "r")), values[bookmarks[ref]])
    for name, tree in trees.items():
        contents[name] = etree.tostring(tree, xml_declaration=True, encoding="UTF-8", standalone=True)
    _update_custom_xml(contents, bindings)
    tmp = Path(tempfile.mkdtemp()) / dest.name
    with zipfile.ZipFile(tmp, "w", zipfile.ZIP_DEFLATED) as out:
        for name, data in contents.items():
            out.writestr(name, data)
    dest.parent.mkdir(parents=True, exist_ok=True)
    shutil.move(str(tmp), dest)
    return dest


def _update_custom_xml(contents, bindings):
    """Controls bound to custom XML (Quick Parts / mapped fields): the stored value is updated too."""
    if not bindings:
        return
    for name in [n for n in contents if re.fullmatch(r"customXml/item\d+\.xml", n)]:
        try:
            tree = etree.fromstring(contents[name])
        except etree.XMLSyntaxError:
            continue
        changed = False
        for _store, xpath, prefixes, value in bindings:
            namespaces = dict(re.findall(r"xmlns:(\w+)=['\"]([^'\"]+)['\"]", prefixes))
            try:
                nodes = tree.xpath(xpath, namespaces=namespaces)
            except etree.XPathError:
                continue
            for node in nodes:
                if isinstance(node, etree._Element):
                    node.text = value
                    changed = True
        if changed:
            contents[name] = etree.tostring(tree, xml_declaration=True, encoding="UTF-8")


# ---------------------------------------------------------------- sample template (for testing and as an example)

def _sdt_xml(tag, alias, kind="text", options=(), placeholder="Click or tap here to enter text.", run_level=True):
    items = "".join(f'<w:listItem w:displayText="{o}" w:value="{o}"/>' for o in options)
    extra = {"text": "<w:text/>", "dropdown": f"<w:dropDownList>{items}</w:dropDownList>",
             "combo": f"<w:comboBox>{items}</w:comboBox>",
             "date": '<w:date><w:dateFormat w:val="MMMM d, yyyy"/><w:lid w:val="en-US"/></w:date>'}[kind]
    body = (f'<w:r><w:rPr><w:rStyle w:val="PlaceholderText"/></w:rPr><w:t>{placeholder}</w:t></w:r>')
    return (f'<w:sdt xmlns:w="{W_NS}"><w:sdtPr><w:alias w:val="{alias}"/><w:tag w:val="{tag}"/>'
            f'<w:showingPlcHdr/>{extra}</w:sdtPr><w:sdtContent>{body}</w:sdtContent></w:sdt>')


def make_sample_template(path):
    """Blank letter with the kinds of fields the bank's templates use (to try the app; not a real letter)."""
    from docx import Document
    from docx.shared import Pt

    doc = Document()
    doc.styles["Normal"].font.name = "Calibri"
    doc.styles["Normal"].font.size = Pt(11)

    def para(*pieces, bold=False, size=None, style=None):
        p = doc.add_paragraph(style=style)
        for piece in pieces:
            if piece.startswith("<w:sdt"):
                p._p.append(etree.fromstring(piece))
            else:
                run = p.add_run(piece)
                run.bold = bold
                if size:
                    run.font.size = Pt(size)
        return p

    para(_sdt_xml("LetterDate", "Letter date", "date", placeholder="Click to choose a date."))
    para(_sdt_xml("CustomerName", "Customer name"))
    para(_sdt_xml("AddressLine1", "Address line 1"))
    para(_sdt_xml("AddressLine2", "Address line 2"))
    para(_sdt_xml("City", "City"), " ", _sdt_xml("Province", "Province", "dropdown", tuple(PROVINCES)), "  ",
         _sdt_xml("PostalCode", "Postal code"))
    para("Claim number: [Claim number]")
    para("")
    para("Dear ", _sdt_xml("CustomerName", "Customer name"), ",")
    para("We have completed the investigation of your claim regarding the transaction(s) of ",
         _sdt_xml("Amount", "Disputed amount"), " at ", _sdt_xml("Merchant", "Merchant"), ".")
    para("After careful review, we are unable to refund the disputed amount for the following reason(s):")
    para(_sdt_xml("Reason", "Decision reason", "dropdown",
                  ("Transaction authorized with the card and PIN", "Card was in the customer's possession",
                   "Merchant provided proof of delivery", "Claim filed after the allowed time")),
         style="List Bullet")  # una viñeta por razón: «＋ Add another» añade más
    para("Channel of the transaction: ", _sdt_xml("Channel", "Channel", "combo",
                                                  ("Card present", "Online", "ATM", "Mobile banking")), ".")
    para("If you do not agree with this decision, you may reply within 15 business days with any additional "
         "information.")
    para("Sincerely,")
    para(_sdt_xml("Analyst", "Analyst name"))
    para("")
    para(_sdt_xml("CustomerName", "Customer name"), bold=True, size=14)
    doc.save(path)
    return path
