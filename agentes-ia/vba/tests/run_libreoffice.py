"""Runs the Word-independent VBA code (MIText.bas) in LibreOffice Basic and compares it with the Python version.

Usage:  python vba/tests/run_libreoffice.py
Needs LibreOffice (soffice) and the suite's Python packages. Exit code 0 when every case matches.
"""

import os
import subprocess
import sys
import tempfile
from pathlib import Path
from xml.sax.saxutils import escape

HERE = Path(__file__).resolve().parent
VBA = HERE.parent
sys.path.insert(0, str(VBA.parent))

from suite.moreinfo import letter, logic  # noqa: E402

ADDRESSES = [
    "221 Main Street, Apt 4B, Toronto ON M5V 2T6",
    "221 Main Street Apt 4B Toronto ON m5v2t6",
    "221 Main Street Apt 4B, Toronto, ON, M5V2T6",
    "123 rue Principale, app. 4, Montréal (Québec) H2X 1Y4",
    "4-123 King St W, Hamilton, Ontario L8P 4S6, Canada",
    "10 Elm Ave #12 Ottawa ON K1A 0B1",
    "55 Water St. Vancouver BC V6B 1A1",
    "88 Queen St, Charlottetown PE C1A 4A1",
    "1 Yonge Street, Suite 1801, Toronto, ON M5E 1W7",
    "500 Boul. René-Lévesque, Montréal, QC H2Z 1W7",
    "221 Main Street",
    "12345 Road Hill Drive, Toronto, ON, M5V 2ST",
    "12345 Road Hill Drive Toronto ON M5V2ST",
    "1 Bay Way, Toronto, ON",
    "12345 Road Hill Drive, Toronto, ON, M4T 4R5",
    "350 Fifth Avenue, New York 10118",
    "77 Bloor St W\nToronto ON\nM5S 1M2",
]
NAMES = ["R-1,MOREINFO.pdf", "r-1,moreinfo3.XLSX", "R-1,MOREINFO12.msg", "R-1,MOREINFO.tar.gz", "R-1,MOREINFOX.pdf",
         "R-10,MOREINFO.pdf", "R-1,MOREINFO", "Other.pdf"]
PLACEHOLDER_TEXTS = ["Dear [Customer Name], claim [Claim number] of {{ Amount }} at [a[bc] and [Customer name] [x]."]
LABELS = ["Address Line 1", "Address Line 2", "City", "Province", "Postal Code", "Street", "Ville", "Code postal",
          "Customer Name", "Card Product"]


def vba_string(s):
    """A VBA string expression (ChrW for anything that is not plain ASCII)."""
    out, plain = [], ""
    for ch in s:
        if 32 <= ord(ch) < 127 and ch != '"':
            plain += ch
            continue
        if plain:
            out.append(f'"{plain}"')
            plain = ""
        out.append('""""' if ch == '"' else f"ChrW({ord(ch)})")
    if plain or not out:
        out.append(f'"{plain}"')
    return " & ".join(out)


def expected():
    lines = []
    for text in ADDRESSES:
        p = letter.split_address(text)
        lines.append("ADDR " + "|".join(p.get(k, "") for k in ("line1", "line2", "city", "province",
                                                                "province_written", "postal")))
    for name in NAMES:
        m = logic.taken_numbers  # same rule, one file at a time
        tmp = Path(tempfile.mkdtemp())
        (tmp / name).write_text("x")
        used = m("R-1", "MOREINFO", [tmp])
        lines.append(f"TAKEN {name} {next(iter(used)) if used else -1}")
    lines.append("NEXT " + "|".join(["R-1,MOREINFO.pdf", "R-1,MOREINFO2.pdf", "R-1,MOREINFO4.xlsx"]))
    lines.append("CLEAN " + logic.clean_case(' R-2026/00 42?* '))
    lines.append("TARGET " + "|".join(logic.document_target(p) for p in ("a.DOCX", "b.png", "c.xlsx", "d.msg", "e.pdf")))
    from datetime import date
    for lang in ("en", "fr", "es"):
        lines.append("DATE " + letter.today(lang, date(2026, 11, 4)))
    lines.append("LANG en fr es")
    lines.append("POSTAL True False False")
    lines.append("PROVOPT ON|Ontario|QC|")
    roles, assigned = [], ""
    for label in LABELS:
        role = ""
        folded = letter._fold(label)
        for r, words in letter.ADDRESS_ROLES:
            if f"|{r}|" not in assigned and any(w in folded for w in words):
                role = r
                break
        roles.append(role)
        if role:
            assigned += f"|{role}|"
    lines.append("ROLES " + "|".join(roles))
    seen = []
    for text in PLACEHOLDER_TEXTS:
        for m in letter.PLACEHOLDER.finditer(text):
            label = (m.group(1) or m.group(2)).strip()
            if label.lower() not in [x.lower() for x in seen]:
                seen.append(label)
    lines.append("PH " + "|".join(seen))
    return lines


TEST_MODULE = '''Option Explicit
Private outText As String

Private Sub Out(ByVal s As String)
    outText = outText & s & Chr(10)
End Sub

Sub Main()
    Dim p As Variant, n As Variant, assigned As String, role As String, roles As String, f As Integer
{body}
    f = FreeFile
    Open "{out}" For Output As #f
    Print #f, outText;
    Close #f
End Sub
'''


def test_body():
    body = []
    for text in ADDRESSES:
        body.append(f"    p = SplitAddress({vba_string(text.replace(chr(10), chr(13) + chr(10)))})")
        body.append('    Out "ADDR " & Join(p, "|")')
    for name in NAMES:
        body.append(f'    Out "TAKEN {name} " & TakenNumber("{name}", "R-1", "MOREINFO")')
    body.append('    n = NextNames("R-1", "MOREINFO", "|1||3|", Array(".PDF", ".pdf", ".xlsx"))')
    body.append('    Out "NEXT " & Join(n, "|")')
    body.append('    Out "CLEAN " & CleanCase(" R-2026/00 42?* ")')
    body.append('    Out "TARGET " & DocumentTarget("a.DOCX") & "|" & DocumentTarget("b.png") & "|" & '
                'DocumentTarget("c.xlsx") & "|" & DocumentTarget("d.msg") & "|" & DocumentTarget("e.pdf")')
    for lang in ("en", "fr", "es"):
        body.append(f'    Out "DATE " & DateText("{lang}", DateSerial(2026, 11, 4))')
    body.append('    Out "LANG " & GuessLanguage("Dear customer, we reviewed your claim and the result is") & " " & '
                'GuessLanguage("Madame, nous avons " & ChrW(233) & "tudi" & ChrW(233) & " votre dossier et la '
                'demande est") & " " & GuessLanguage("Estimado cliente, usted y los documentos del caso para")')
    body.append('    Out "POSTAL " & ValidPostal("M5V 2T6") & " " & ValidPostal("M5V 2ST") & " " & ValidPostal("")')
    body.append('    Out "PROVOPT " & ProvinceOption("ON", "ON", Array("AB", "ON")) & "|" & '
                'ProvinceOption("ON", "ON", Array("Alberta", "Ontario")) & "|" & ProvinceOption("QC", "QC", Empty) '
                '& "|" & ProvinceOption("QC", "QC", Array("Ontario"))')
    body.append("    assigned = \"\"")
    for label in LABELS:
        body.append(f'    role = AddressRole("{label}", assigned)')
        body.append('    If Len(role) > 0 Then assigned = assigned & "|" & role & "|"')
        body.append('    roles = roles & role & "|"')
    body.append('    Out "ROLES " & Left(roles, Len(roles) - 1)')
    body.append(f'    Out "PH " & Join(PlaceholderLabels({vba_string(PLACEHOLDER_TEXTS[0])}), "|")')
    return "\n".join(body)


def xba(name, code):
    return ('<?xml version="1.0" encoding="UTF-8"?>\n<!DOCTYPE script:module PUBLIC "-//OpenOffice.org//DTD '
            'OfficeDocument 1.0//EN" "module.dtd">\n<script:module xmlns:script="http://openoffice.org/2000/script" '
            f'script:name="{name}" script:language="StarBasic">{escape(code)}</script:module>\n')


def basic_code(path):
    """A .bas file as LibreOffice Basic: without the Attribute lines and in VBA compatibility mode."""
    text = path.read_text(encoding="cp1252")
    lines = [line for line in text.splitlines() if not line.startswith("Attribute VB_")]
    return "Option VBASupport 1\n" + "\n".join(lines) + "\n"


def run():
    work = Path(tempfile.mkdtemp(prefix="vba_lo_"))
    profile = work / "profile"
    subprocess.run(["soffice", f"-env:UserInstallation=file://{profile}", "--headless", "--terminate_after_init"],
                   check=True, capture_output=True, timeout=120)
    lib = profile / "user" / "basic" / "Standard"
    out = work / "out.txt"
    modules = {"MIText": basic_code(VBA / "MIText.bas"),
               "MITest": "Option VBASupport 1\n" + TEST_MODULE.format(body=test_body(), out=out)}
    for name, code in modules.items():
        (lib / f"{name}.xba").write_text(xba(name, code), encoding="utf-8")
    elements = "".join(f' <library:element library:name="{n}"/>\n' for n in ["Module1", *modules])
    (lib / "script.xlb").write_text(
        '<?xml version="1.0" encoding="UTF-8"?>\n<!DOCTYPE library:library PUBLIC "-//OpenOffice.org//DTD '
        'OfficeDocument 1.0//EN" "library.dtd">\n<library:library xmlns:library="http://openoffice.org/2000/library" '
        'library:name="Standard" library:readonly="false" library:passwordprotected="false">\n'
        f"{elements}</library:library>\n", encoding="utf-8")
    env = dict(os.environ, SAL_USE_VCLPLUGIN="svp")
    proc = subprocess.run(["soffice", f"-env:UserInstallation=file://{profile}", "--headless", "--invisible",
                           "macro:///Standard.MITest.Main"], capture_output=True, text=True, timeout=180, env=env)
    if not out.exists():
        print("LibreOffice did not produce output.", proc.stdout, proc.stderr, sep="\n")
        return 2
    got = out.read_text(encoding="utf-8", errors="replace").splitlines()
    want = expected()
    bad = 0
    for i, line in enumerate(want):
        have = got[i] if i < len(got) else "<missing>"
        if have != line:
            bad += 1
            print(f"DIFF\n  python: {line}\n  vba:    {have}")
    print(f"{len(want) - bad}/{len(want)} cases match")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(run())
