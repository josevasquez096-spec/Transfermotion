"""No Pay Decision Letter from a blank Word template (.docx) filled inside the app.

Fields that are detected (and filled in place, keeping the template's layout):
- Content controls (Developer tab): plain/rich text, drop-down list, combo box and date picker. The label shown in
  the app is the control's Title (or Tag). Controls with the same Title/Tag, or bound to the same data, share one
  value: type the customer name once and it appears everywhere (for example also as a title further down).
- Legacy form fields (FORMTEXT and FORMDROPDOWN) and REF fields that repeat them.
- Placeholders written in the text: [Customer Name] or {{Customer Name}}.
"""

import re
import shutil
import tempfile
import zipfile
from dataclasses import dataclass, field
from pathlib import Path

from lxml import etree

W_NS = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"
W14_NS = "http://schemas.microsoft.com/office/word/2010/wordml"
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
    binding = pr.find(W + "dataBinding")
    tag, alias = _val(pr, "tag"), _val(pr, "alias")
    if tag or alias:
        return f"cc:{(tag or alias).strip().lower()}", alias or tag
    if binding is not None:
        return f"xp:{binding.get(W + 'xpath')}", binding.get(W + "xpath").rsplit("/", 1)[-1].split("[")[0]
    return f"cc:#{index}", None


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

    def add(key, label, kind="text", options=(), value=""):
        if key in fields:
            fields[key].count += 1
            for option in options:
                if option not in fields[key].options:
                    fields[key].options.append(option)
            return
        fields[key] = Field(key, (label or key.split(":", 1)[1]).strip(), kind, list(options), value)
        order.append(key)

    with zipfile.ZipFile(path) as zf:
        for name in _parts(zf):
            tree = etree.fromstring(zf.read(name))
            for n, (_sdt, pr, content) in enumerate(_leaf_sdts(tree)):
                key, label = _sdt_key(pr, f"{name}{n}")
                showing = pr.find(W + "showingPlcHdr") is not None
                current = "" if showing else _text(content).strip()
                kind, options = "text", []
                for tag, k in (("dropDownList", "dropdown"), ("comboBox", "combo")):
                    lst = pr.find(W + tag)
                    if lst is not None:
                        kind = k
                        options = [i.get(W + "displayText") or i.get(W + "value") or ""
                                   for i in lst.findall(W + "listItem")]
                        options = [o for o in options if o.strip()]
                if pr.find(W + "date") is not None:
                    kind = "date"
                add(key, label or _text(content).strip() or f"Field {len(order) + 1}", kind, options, current)
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


def fill(template, values, dest):
    """Writes a copy of the template with the values (dict key → text). Returns dest."""
    template, dest = Path(template), Path(dest)
    bookmarks = {}  # nombre de marcador → clave, para los campos REF que repiten un valor
    bindings = []  # (storeItemID, xpath, prefixMappings, value)
    with zipfile.ZipFile(template) as zf:
        contents = {n: zf.read(n) for n in zf.namelist()}
    trees = {n: etree.fromstring(contents[n]) for n in _parts(zipfile.ZipFile(template))}
    for name, tree in trees.items():
        for n, (sdt, pr, content) in enumerate(_leaf_sdts(tree)):
            key, _ = _sdt_key(pr, f"{name}{n}")
            for mark in sdt.iter(W + "bookmarkStart"):
                bookmarks[(mark.get(W + "name") or "").lower()] = key
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

    def para(*pieces, bold=False, size=None):
        p = doc.add_paragraph()
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
    para("Claim number: [Claim number]")
    para("")
    para("Dear ", _sdt_xml("CustomerName", "Customer name"), ",")
    para("We have completed the investigation of your claim regarding the transaction(s) of ",
         _sdt_xml("Amount", "Disputed amount"), " at ", _sdt_xml("Merchant", "Merchant"), ".")
    para("After careful review, we are unable to refund the disputed amount for the following reason: ",
         _sdt_xml("Reason", "Decision reason", "dropdown",
                  ("Transaction authorized with the card and PIN", "Card was in the customer's possession",
                   "Merchant provided proof of delivery", "Claim filed after the allowed time")), ".")
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
