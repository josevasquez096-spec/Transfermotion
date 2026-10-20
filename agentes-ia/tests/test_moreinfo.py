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
    result = logic.create_package("777", "Ana", shots(tmp_path), [str(extra_img), str(extra_doc)],
                                  [share1, share2], tmp_path / "work", use_word=False, keep_docx=True)
    assert result["engine"] == "builtin" and not result["errors"]
    names = [p.name for p in result["created"]]
    assert names == ["777,MOREINFO1.pdf", "777,MOREINFO1.docx", "777,MOREINFO2.pdf", "777,MOREINFO3.xlsx"]
    assert sorted(p.name for p in share1.iterdir()) == sorted(names)
    pdf = result["created"][0].read_bytes()
    assert pdf.startswith(b"%PDF") and pdf.count(b"/Type /Page\n") + pdf.count(b"/Type /Page\r") >= 1
    doc = Document(result["created"][1])
    assert len(doc.inline_shapes) == 5
    assert [p.text for p in doc.paragraphs if p.style.name.startswith("Heading")] == [
        "Transactions", "Profile", "Cards", "Claim information"]


def test_per_case_folder_and_existing_file(tmp_path):
    share = tmp_path / "share"
    logic.create_package("888", "", shots(tmp_path)[:1], [], [share], tmp_path / "work",
                                  per_case_folder=True, use_word=False)
    assert (share / "888" / "888,MOREINFO.pdf").exists()
    again = logic.create_package("888", "", shots(tmp_path)[:1], [], [share], tmp_path / "work",
                                 per_case_folder=True, use_word=False)
    assert again["created"][0].name == "888,MOREINFO1.pdf" and not again["errors"]


def test_excel_package_adds_tab(tmp_path):
    wb = Workbook()
    wb.active.title = "Transactions"
    wb.active.append(["Date", "Merchant", "Amount"])
    wb.active.append(["2026-10-01", "Shop", 120.5])
    src = tmp_path / "txns.xlsx"
    wb.save(src)
    result = logic.create_package("999", "Ana", shots(tmp_path)[2:], [], [tmp_path / "out"], tmp_path / "work",
                                  mode="excel", excel_source=str(src))
    book = load_workbook(result["created"][0])
    assert result["created"][0].name == "999,MOREINFO.xlsx"
    assert book.sheetnames == ["Transactions", "Additional info"] and book["Transactions"]["C2"].value == 120.5
    assert len(book["Additional info"]._images) == 3 and book["Additional info"]["A1"].value == \
        "Additional info – Case 999"


def test_validation(tmp_path):
    with pytest.raises(ValueError):
        logic.create_package(" ", "", shots(tmp_path), [], [], tmp_path)
    with pytest.raises(ValueError):
        logic.create_package("1", "", [], [], [], tmp_path)
    with pytest.raises(ValueError):
        logic.create_package("1", "", [], [], [], tmp_path, mode="excel")


def test_unreachable_folder_is_reported(tmp_path):
    blocker = tmp_path / "file.txt"
    blocker.write_text("x")
    result = logic.create_package("5", "", shots(tmp_path)[:1], [], [blocker / "sub"], tmp_path / "work",
                                  use_word=False)
    assert result["errors"] and Path(result["created"][0]).exists()
