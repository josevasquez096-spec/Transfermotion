from pathlib import Path

import pytest
from docx import Document
from openpyxl import Workbook, load_workbook
from PIL import Image

from suite.moreinfo import logic


def shots(tmp_path, sections=("Transactions", "Transactions", "Profile", "Cards", "Claim information")):
    out = []
    for n, section in enumerate(sections):
        path = tmp_path / f"shot{n}.png"
        Image.new("RGB", (1600 if n == 0 else 700, 300 + 250 * n), (200, 220, 240)).save(path)
        out.append(logic.Shot(section, str(path), f"caption {n}" if n % 2 else ""))
    return out


def test_clean_case_and_numbering(tmp_path):
    assert logic.clean_case(' 1234/56 "x" ') == "123456x"
    a, b = tmp_path / "a", tmp_path / "b"
    a.mkdir()
    b.mkdir()
    assert logic.next_names("C1", "MOREINFO", [a, b], [".pdf", ".pdf"]) == ["C1,MOREINFO.pdf", "C1,MOREINFO1.pdf"]
    (a / "C1,MOREINFO.pdf").touch()
    (b / "c1,moreinfo2.xlsx").touch()
    (b / "C10,MOREINFO1.pdf").touch()  # otro caso
    assert logic.next_names("C1", "MOREINFO", [a, b, tmp_path / "missing"], [".pdf", ".docx"]) == [
        "C1,MOREINFO1.pdf", "C1,MOREINFO3.docx"]


def test_pdf_package_is_numbered_and_copied(tmp_path):
    share1, share2 = tmp_path / "share1", tmp_path / "share2"
    share1.mkdir()
    share2.mkdir()
    (share2 / "777,MOREINFO.pdf").write_bytes(b"%PDF")
    extra_img = tmp_path / "extra.png"
    Image.new("RGB", (300, 200), "red").save(extra_img)
    extra_doc = tmp_path / "statement.xlsx"
    Workbook().save(extra_doc)
    result = logic.create_package("777", "Ana", shots(tmp_path), [str(extra_img), (str(extra_doc), True)],
                                  share1, [share1, share2], use_word=False, keep_docx=True)
    assert result["engine"] == "builtin" and not result["errors"] and result["kept"] is None
    names = result["names"]
    assert names == ["777,MOREINFO1.pdf", "777,MOREINFO1.docx", "777,MOREINFO2.pdf", "777,MOREINFO3.xlsx"]
    assert sorted(p.name for p in share1.iterdir()) == sorted(names)
    # la carta (marcada) va también a la segunda carpeta de cartas; el resto solo a la principal
    assert sorted(p.name for p in share2.iterdir()) == ["777,MOREINFO.pdf", "777,MOREINFO3.xlsx"]
    pdf = (share1 / names[0]).read_bytes()
    assert pdf.startswith(b"%PDF") and pdf.count(b"/Type /Page\n") + pdf.count(b"/Type /Page\r") >= 1
    doc = Document(share1 / names[1])
    assert len(doc.inline_shapes) == 5
    assert [p.text for p in doc.paragraphs if p.style.name.startswith("Heading")] == [
        "Transactions", "Profile", "Cards", "Claim information"]


def test_existing_file_continues_numbering(tmp_path):
    share = tmp_path / "share"
    logic.create_package("888", "", shots(tmp_path)[:1], [], share, use_word=False)
    again = logic.create_package("888", "", shots(tmp_path)[:1], [], share, use_word=False)
    assert again["names"] == ["888,MOREINFO1.pdf"] and not again["errors"]
    assert sorted(p.name for p in share.iterdir()) == ["888,MOREINFO.pdf", "888,MOREINFO1.pdf"]


def test_case_documents_keep_or_convert_format(tmp_path):
    share = tmp_path / "share"
    letter = tmp_path / "No pay letter.docx"
    doc = Document()
    doc.add_paragraph("We have completed the review of your claim.")
    table = doc.add_table(rows=1, cols=2)
    table.rows[0].cells[0].text, table.rows[0].cells[1].text = "Amount", "$120.00"
    doc.save(letter)
    pdf = tmp_path / "footprint.pdf"
    logic.image_to_pdf(_png(tmp_path), pdf)
    sheet = tmp_path / "voice match.xlsx"
    Workbook().save(sheet)
    email = tmp_path / "approval.msg"
    email.write_bytes(b"msg")
    text = tmp_path / "web extraction.txt"
    text.write_text("extract", encoding="utf-8")
    old_doc = tmp_path / "old.doc"
    old_doc.write_bytes(b"doc")
    documents = [str(x) for x in (letter, pdf, sheet, email, text, old_doc)]
    result = logic.create_package("4321", "", shots(tmp_path)[:1], documents, share, use_word=False)
    assert result["names"] == ["4321,MOREINFO.pdf", "4321,MOREINFO1.pdf", "4321,MOREINFO2.pdf",
                               "4321,MOREINFO3.xlsx", "4321,MOREINFO4.msg", "4321,MOREINFO5.txt",
                               "4321,MOREINFO6.doc"]
    assert result["notes"] == [("doc_text_only", "No pay letter.docx"), ("doc_kept", "old.doc")]
    assert (share / "4321,MOREINFO1.pdf").read_bytes().startswith(b"%PDF")
    only = logic.create_package("4321", "", [], [str(text)], share, include_moreinfo=False)
    assert only["names"] == ["4321,MOREINFO7.txt"] and only["engine"] is None
    with pytest.raises(ValueError):
        logic.create_package("4321", "", [], [], share, include_moreinfo=False)


def _png(tmp_path, name="img.png"):
    path = tmp_path / name
    Image.new("RGB", (200, 100), "white").save(path)
    return path


def test_excel_package_adds_tab(tmp_path):
    wb = Workbook()
    wb.active.title = "Transactions"
    wb.active.append(["Date", "Merchant", "Amount"])
    wb.active.append(["2026-10-01", "Shop", 120.5])
    src = tmp_path / "txns.xlsx"
    wb.save(src)
    result = logic.create_package("999", "Ana", shots(tmp_path)[2:], [], tmp_path / "out", mode="excel",
                                  excel_source=str(src))
    book = load_workbook(tmp_path / "out" / "999,MOREINFO.xlsx")
    assert result["names"] == ["999,MOREINFO.xlsx"]
    assert book.sheetnames == ["Transactions", "Additional info"] and book["Transactions"]["C2"].value == 120.5
    assert len(book["Additional info"]._images) == 3 and book["Additional info"]["A1"].value == \
        "Additional info – Case 999"


def test_validation(tmp_path):
    cases = [(" ", shots(tmp_path), tmp_path, {}), ("1", shots(tmp_path), "", {}), ("1", [], tmp_path, {}),
             ("1", [], tmp_path, {"mode": "excel"})]
    for case, items, folders, kwargs in cases:
        with pytest.raises(ValueError):
            logic.create_package(case, "", items, [], folders, **kwargs)


def test_unreachable_folder_is_reported(tmp_path):
    blocker = tmp_path / "file.txt"
    blocker.write_text("x")
    result = logic.create_package("5", "", shots(tmp_path)[:1], [], blocker / "sub", use_word=False)
    assert result["errors"] and (Path(result["kept"]) / "5,MOREINFO.pdf").exists()  # nada se pierde


# ---------------------------------------------------------------- No Pay Decision Letter template

W_NS = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"


def _legacy_template(path):
    """Plantilla con un campo de formulario antiguo, un desplegable antiguo, un REF que repite el nombre y un
    marcador partido en dos fragmentos de texto."""
    from lxml import etree

    doc = Document()
    p = doc.add_paragraph()
    xml = (
        f'<w:p xmlns:w="{W_NS}"><w:r><w:t xml:space="preserve">Name: </w:t></w:r>'
        '<w:bookmarkStart w:id="1" w:name="CustName"/>'
        '<w:r><w:fldChar w:fldCharType="begin"><w:ffData><w:name w:val="CustName"/><w:enabled/>'
        '<w:textInput/></w:ffData></w:fldChar></w:r><w:r><w:instrText> FORMTEXT </w:instrText></w:r>'
        '<w:r><w:fldChar w:fldCharType="separate"/></w:r><w:r><w:t>     </w:t></w:r>'
        '<w:r><w:fldChar w:fldCharType="end"/></w:r><w:bookmarkEnd w:id="1"/></w:p>')
    p._p.getparent().replace(p._p, etree.fromstring(xml))
    p = doc.add_paragraph()
    xml = (
        f'<w:p xmlns:w="{W_NS}"><w:r><w:fldChar w:fldCharType="begin"><w:ffData><w:name w:val="Outcome"/>'
        '<w:ddList><w:listEntry w:val="Denied"/><w:listEntry w:val="Partially approved"/></w:ddList>'
        '</w:ffData></w:fldChar></w:r><w:r><w:instrText> FORMDROPDOWN </w:instrText></w:r>'
        '<w:r><w:fldChar w:fldCharType="separate"/></w:r><w:r><w:fldChar w:fldCharType="end"/></w:r></w:p>')
    p._p.getparent().replace(p._p, etree.fromstring(xml))
    p = doc.add_paragraph()
    xml = (
        f'<w:p xmlns:w="{W_NS}"><w:r><w:fldChar w:fldCharType="begin"/></w:r>'
        '<w:r><w:instrText> REF CustName \\h </w:instrText></w:r><w:r><w:fldChar w:fldCharType="separate"/></w:r>'
        '<w:r><w:t>old</w:t></w:r><w:r><w:fldChar w:fldCharType="end"/></w:r></w:p>')
    p._p.getparent().replace(p._p, etree.fromstring(xml))
    p = doc.add_paragraph("Case: ")
    p.add_run("[Case")
    p.add_run(" number] end")
    doc.save(path)
    return path


def _all_text(path):
    import zipfile

    from lxml import etree

    tree = etree.fromstring(zipfile.ZipFile(path).read("word/document.xml"))
    return ["".join(t.text or "" for t in p.iter(f"{{{W_NS}}}t")) for p in tree.iter(f"{{{W_NS}}}p")]


def test_letter_content_controls(tmp_path):
    from suite.moreinfo import letter

    template = letter.make_sample_template(tmp_path / "blank.docx")
    fields = {f.key: f for f in letter.scan(template)}
    assert fields["cc:customername"].count == 3 and fields["cc:reason"].kind == "dropdown"
    assert fields["cc:letterdate"].kind == "date" and fields["cc:channel"].kind == "combo"
    assert len(fields["cc:reason"].options) == 4 and "ph:claim number" in fields
    values = {"cc:customername": "Laura Méndez", "cc:reason": fields["cc:reason"].options[1],
              "cc:letterdate": "October 30, 2026", "ph:claim number": "R-2026-0042", "cc:channel": "Online"}
    out = letter.fill(template, values, tmp_path / "letter.docx")
    text = _all_text(out)
    assert sum(t.count("Laura Méndez") for t in text) == 3  # también como título al final
    assert "Claim number: R-2026-0042" in text and any("Card was in the customer" in t for t in text)
    assert text[-1] == "Laura Méndez"
    again = {f.key: f for f in letter.scan(out)}
    assert again["cc:customername"].value == "Laura Méndez"
    # solo quedan con el texto gris de ejemplo los campos que no se rellenaron (importe, comercio, analista y los
    # 5 de la dirección)
    assert __import__("zipfile").ZipFile(out).read("word/document.xml").decode().count("PlaceholderText") == 8


def test_letter_legacy_fields_ref_and_split_placeholder(tmp_path):
    from suite.moreinfo import letter

    template = _legacy_template(tmp_path / "legacy.docx")
    fields = {f.key: f for f in letter.scan(template)}
    assert set(fields) == {"ff:custname", "ff:outcome", "ph:case number"}
    assert fields["ff:outcome"].options == ["Denied", "Partially approved"]
    out = letter.fill(template, {"ff:custname": "Emma Wilson", "ff:outcome": "Partially approved",
                                 "ph:case number": "R-77"}, tmp_path / "out.docx")
    text = _all_text(out)
    assert text[0].startswith("Name: ") and "Emma Wilson" in text[0]
    assert text[2] == "Emma Wilson"  # el REF repite el nombre
    assert text[3] == "Case: R-77 end"
    xml = __import__("zipfile").ZipFile(out).read("word/document.xml").decode()
    assert 'w:result w:val="1"' in xml


def test_letter_bound_to_custom_xml(tmp_path):
    import zipfile

    from suite.moreinfo import letter

    template = tmp_path / "bound.docx"
    letter.make_sample_template(template)
    data = {n: zipfile.ZipFile(template).read(n) for n in zipfile.ZipFile(template).namelist()}
    xml = data["word/document.xml"].decode().replace(
        '<w:tag w:val="Merchant"/>', '<w:tag w:val="Merchant"/><w:dataBinding w:prefixMappings="xmlns:ns0=\'urn:x\'" '
        'w:xpath="/ns0:letter[1]/ns0:merchant[1]" w:storeItemID="{11111111-1111-1111-1111-111111111111}"/>')
    data["word/document.xml"] = xml.encode()
    data["customXml/item1.xml"] = b'<letter xmlns="urn:x"><merchant>old</merchant></letter>'
    with zipfile.ZipFile(template, "w") as zf:
        for name, content in data.items():
            zf.writestr(name, content)
    key = next(f.key for f in letter.scan(template) if f.label == "Merchant")
    assert key.startswith("xp:")
    out = letter.fill(template, {key: "TechStore"}, tmp_path / "out.docx")
    assert b"TechStore" in zipfile.ZipFile(out).read("customXml/item1.xml")


def test_letter_language_and_date(tmp_path):
    from datetime import date

    from suite.moreinfo import letter

    english = letter.make_sample_template(tmp_path / "en.docx")
    french = tmp_path / "fr.docx"
    doc = Document()
    doc.add_paragraph("Madame, Monsieur [Nom du client], nous avons étudié votre réclamation et la décision est "
                      "pour le dossier [Numéro de dossier].")
    doc.save(french)
    assert letter.language(english) == "en" and letter.language(french) == "fr"
    assert letter.today("fr", date(2026, 10, 3)) == "3 octobre 2026"
    assert letter.today("en", date(2026, 10, 3)) == "October 3, 2026"
    assert {f.label for f in letter.scan(french)} == {"Nom du client", "Numéro de dossier"}


def test_two_controls_bound_to_the_same_data_are_one_field(tmp_path):
    """Como la plantilla del banco: «Customer Name» y su copia bloqueada «Customer Name (auto)»."""
    import zipfile

    from suite.moreinfo import letter

    template = tmp_path / "bound2.docx"
    letter.make_sample_template(template)
    data = {n: zipfile.ZipFile(template).read(n) for n in zipfile.ZipFile(template).namelist()}
    binding = ('<w:dataBinding w:prefixMappings="xmlns:ns0=\'urn:x\'" w:xpath="/ns0:letter[1]/ns0:name[1]" '
               'w:storeItemID="{11111111-1111-1111-1111-111111111111}"/>')
    xml = data["word/document.xml"].decode()
    xml = xml.replace('<w:tag w:val="CustomerName"/>', '<w:tag w:val="CustomerName"/>' + binding, 1)
    xml = xml.replace('<w:tag w:val="Analyst"/>', '<w:tag w:val="NameAuto"/>' + binding)  # otro control, mismo dato
    data["word/document.xml"] = xml.encode()
    data["customXml/item1.xml"] = b'<letter xmlns="urn:x"><name></name></letter>'
    with zipfile.ZipFile(template, "w") as zf:
        for name, content in data.items():
            zf.writestr(name, content)
    bound = [f for f in letter.scan(template) if f.key.startswith("xp:")]
    assert len(bound) == 1 and bound[0].count == 2 and bound[0].label == "Customer name"
    out = letter.fill(template, {bound[0].key: "Emma Wilson"}, tmp_path / "out.docx")
    assert _all_text(out).count("Emma Wilson") == 2


REASONS = ("Chip and PIN used", "Known device", "OTP verified")


def _lines(path):
    """(estilo, texto) de cada párrafo, también los que están dentro de controles de contenido."""
    from suite.moreinfo import letter

    w = f"{{{letter.W_NS}}}"
    out = []
    for p in Document(path).element.body.iter(w + "p"):
        style = p.find(f"{w}pPr/{w}pStyle")
        text = "".join(t.text or "" for t in p.iter(w + "t"))
        out.append((style.get(w + "val") if style is not None else None, text))
    return out


def _dropdown(tag, items=REASONS):
    from suite.moreinfo import letter

    return letter._sdt_xml(tag, tag, "dropdown", items, placeholder="Select a reason")


def test_several_reasons_in_a_word_repeating_section(tmp_path):
    """Como la plantilla del banco: la razón está en una sección repetible de Word (Reasons → Reason)."""
    from lxml import etree

    from suite.moreinfo import letter

    w, w15 = letter.W_NS, letter.W15_NS
    doc = Document()
    doc.add_paragraph("Your claim has been declined for the following reason(s):")
    section = etree.fromstring(
        f'<w:sdt xmlns:w="{w}" xmlns:w15="{w15}"><w:sdtPr><w:alias w:val="Reasons"/><w:id w:val="5"/>'
        f'<w15:repeatingSection/></w:sdtPr><w:sdtContent><w:sdt><w:sdtPr><w:id w:val="6"/>'
        f'<w15:repeatingSectionItem/></w:sdtPr><w:sdtContent><w:p><w:pPr><w:pStyle w:val="ListBullet"/></w:pPr>'
        f'<w:bookmarkStart w:id="1" w:name="reason"/><w:bookmarkEnd w:id="1"/></w:p>'
        f'</w:sdtContent></w:sdt></w:sdtContent></w:sdt>')
    section.find(f".//{{{w}}}p").append(etree.fromstring(_dropdown("Reason")))
    doc.add_paragraph("Sincerely,")._p.addprevious(section)
    doc.save(tmp_path / "t.docx")
    (reason,) = letter.scan(tmp_path / "t.docx")
    assert reason.multi and reason.options == list(REASONS)
    out = letter.fill(tmp_path / "t.docx", {reason.key: list(REASONS)}, tmp_path / "out.docx")
    paragraphs = [text for _, text in _lines(out)]
    assert paragraphs[1:4] == list(REASONS) and paragraphs[-1] == "Sincerely,"
    xml = __import__("zipfile").ZipFile(out).read("word/document.xml").decode()
    assert xml.count("repeatingSectionItem") == 3 and xml.count('w:name="reason"') == 1
    assert "urn:moreinfo-pilot" not in xml and "PlaceholderText" not in xml
    assert letter.scan(out)[0].count == 3


def test_several_reasons_in_bullets_and_inline(tmp_path):
    from suite.moreinfo import letter

    doc = Document()
    doc.add_paragraph("Declined because:")
    doc.add_paragraph(style="List Bullet")._p.append(__import__("lxml.etree").etree.fromstring(_dropdown("Reason")))
    doc.add_paragraph("Province: ")._p.append(__import__("lxml.etree").etree.fromstring(_dropdown("Province")))
    doc.save(tmp_path / "t.docx")
    reason, province = letter.scan(tmp_path / "t.docx")
    assert reason.multi and not province.multi  # en una frase: un solo valor
    out = letter.fill(tmp_path / "t.docx", {reason.key: ["Known device", "OTP verified"],
                                            province.key: "ON"}, tmp_path / "out.docx")
    assert _lines(out)[1:] == [("ListBullet", "Known device"), ("ListBullet", "OTP verified"),
                               (None, "Province: ON")]
    # un solo valor en forma de lista, o varios valores en un campo de frase: se escriben juntos
    out = letter.fill(tmp_path / "t.docx", {reason.key: ["Known device"], province.key: ["ON", "QC"]},
                      tmp_path / "out2.docx")
    assert [text for _, text in _lines(out)][1:] == ["Known device", "Province: ON; QC"]


@pytest.mark.parametrize("text, expected", [
    ("221 Main Street, Apt 4B, Toronto ON M5V 2T6",
     dict(line1="221 Main Street", line2="Apt 4B", city="Toronto", province="ON", postal="M5V 2T6")),
    ("221 Main Street Apt 4B Toronto ON m5v2t6",  # sin comas
     dict(line1="221 Main Street", line2="Apt 4B", city="Toronto", province="ON", postal="M5V 2T6")),
    ("123 rue Principale, app. 4, Montréal (Québec) H2X 1Y4",
     dict(line1="123 rue Principale", line2="app. 4", city="Montréal", province="QC", postal="H2X 1Y4")),
    ("4-123 King St W, Hamilton, Ontario L8P 4S6, Canada",
     dict(line1="4-123 King St W", city="Hamilton", province="ON", postal="L8P 4S6")),
    ("10 Elm Ave #12 Ottawa ON K1A 0B1",
     dict(line1="10 Elm Ave", line2="#12", city="Ottawa", province="ON", postal="K1A 0B1")),
    ("221 Main Street", dict(line1="221 Main Street")),
    # código postal mal escrito («T» en vez de número): igual va a su campo (la app pide revisarlo)
    ("12345 Road Hill Drive, Toronto, ON, M5V 2ST",
     dict(line1="12345 Road Hill Drive", city="Toronto", province="ON", postal="M5V 2ST")),
    ("12345 Road Hill Drive Toronto ON M5V2ST",
     dict(line1="12345 Road Hill Drive", city="Toronto", province="ON", postal="M5V 2ST")),
    ("1 Bay Way, Toronto, ON", dict(line1="1 Bay Way", city="Toronto", province="ON")),
])
def test_split_address(text, expected):
    from suite.moreinfo import letter

    parts = letter.split_address(text)
    parts.pop("province_written", None)
    assert parts == expected


def test_address_values_follow_the_template_fields(tmp_path):
    from suite.moreinfo import letter

    fields = letter.scan(letter.make_sample_template(tmp_path / "t.docx"))
    assert letter.address_roles(fields) == {"line1": "cc:addressline1", "line2": "cc:addressline2", "city": "cc:city",
                                            "province": "cc:province", "postal": "cc:postalcode"}
    values = letter.address_values("123 rue Principale, app. 4, Montréal (Québec) H2X 1Y4", fields)
    assert values == {"cc:addressline1": "123 rue Principale", "cc:addressline2": "app. 4", "cc:city": "Montréal",
                      "cc:province": "QC", "cc:postalcode": "H2X 1Y4"}
    # sin «Address line 2» ni «Postal code» en la plantilla: el resto va con el campo más cercano
    fewer = [f for f in fields if f.key not in ("cc:addressline2", "cc:postalcode")]
    values = letter.address_values("221 Main Street, Apt 4B, Toronto ON M5V 2T6", fewer)
    assert values["cc:addressline1"] == "221 Main Street, Apt 4B" and values["cc:city"] == "Toronto M5V 2T6"
    # una lista de provincias con nombres
    fields[[f.key for f in fields].index("cc:province")].options = ["Ontario", "Québec"]
    assert letter.address_values("1 Bay St, Toronto ON M5J 2R8", fields)["cc:province"] == "Ontario"


def test_a_reason_counts_once(tmp_path):
    from suite.moreinfo import letter

    template = letter.make_sample_template(tmp_path / "t.docx")
    reason = next(f for f in letter.scan(template) if f.key == "cc:reason")
    twice = [reason.options[0], reason.options[1], reason.options[0]]
    out = letter.fill(template, {"cc:reason": twice}, tmp_path / "out.docx")
    assert next(f for f in letter.scan(out) if f.key == "cc:reason").count == 2


def test_valid_postal():
    from suite.moreinfo import letter

    assert letter.valid_postal("M5V 2T6") and not letter.valid_postal("M5V 2ST") and not letter.valid_postal("")


def test_empty_field_leaves_no_example_text_or_blank_line(tmp_path):
    from suite.moreinfo import letter

    template = letter.make_sample_template(tmp_path / "t.docx")
    values = {f.key: "" for f in letter.scan(template)}
    values.update({"cc:customername": "Jose Vasquez", "cc:addressline1": "12345 Road Hill Drive", "cc:city": "Toronto",
                   "cc:province": "ON", "cc:postalcode": "M5V 2T6"})
    out = letter.fill(template, values, tmp_path / "out.docx")
    lines = [text for _, text in _lines(out)]
    assert "PlaceholderText" not in __import__("zipfile").ZipFile(out).read("word/document.xml").decode()
    start = lines.index("Jose Vasquez")
    assert lines[start:start + 3] == ["Jose Vasquez", "12345 Road Hill Drive", "Toronto ON  M5V 2T6"]
