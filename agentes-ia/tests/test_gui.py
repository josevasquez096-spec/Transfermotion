"""Arranca cada app, recorre los tres idiomas y comprueba que no falte ninguna traducción.

Necesita una pantalla (en Linux: xvfb-run python -m pytest).
"""

import os
import re
import sys

import pytest

tk = pytest.importorskip("tkinter")
if sys.platform.startswith("linux") and not os.environ.get("DISPLAY"):
    pytest.skip("sin pantalla", allow_module_level=True)

from suite.bipilot.app import BIPilot  # noqa: E402
from suite.datapilot.app import DataPilot  # noqa: E402
from suite.docpilot.app import DocPilot  # noqa: E402
from suite.fraudpilot.app import FraudPilot  # noqa: E402
from suite.icepilot import games as ice_games  # noqa: E402
from suite.icepilot.app import IcePilot  # noqa: E402
from suite.icepilot.build import build_html  # noqa: E402
from suite.mailpilot.app import MailPilot  # noqa: E402
from suite.moreinfo.app import MoreInfoPilot  # noqa: E402
from suite.slidepilot.app import SlidePilot  # noqa: E402
from suite.slidepilot.strings import SAMPLE_OUTLINE  # noqa: E402


def exercise(app):
    if isinstance(app, DataPilot):
        app.load_sample()
        app.apply_clean()
        app.calc_pivot()
    elif isinstance(app, BIPilot):
        app.load_sample()
        app.gen_measures()
        app.gen_calendar("m")
        app.gen_m()
    elif isinstance(app, DocPilot):
        app.draft_template()
        app.use_sample_data()
    elif isinstance(app, SlidePilot):
        app.outline.set(SAMPLE_OUTLINE["es"])
        app.load_excel_sample()
        app.excel_outline(True)
        app.draw_preview()
    elif isinstance(app, FraudPilot):
        app.sample_claim()
        app.evaluate()
        app.sample_batch()
        app.batch_result = __import__("suite.fraudpilot.logic", fromlist=["x"]).analyze_batch(
            app.batch_df, app._mapping())
        app._show_batch()
        app.gen_letter()
    elif isinstance(app, MailPilot):
        exercise_mailpilot(app)
    elif isinstance(app, MoreInfoPilot):
        exercise_moreinfo(app)
    elif isinstance(app, IcePilot):
        for game in ice_games.GAMES:
            app.select_game(game)
            app.nb.select(1)
            app.update()
            cfg = app.config()
            assert cfg["items"], game
            build_html(cfg)


def exercise_mailpilot(app):
    from tkinter import messagebox

    saved = {name: getattr(messagebox, name) for name in ("showinfo", "showwarning", "showerror", "askyesno")}
    for name in ("showinfo", "showwarning", "showerror"):
        setattr(messagebox, name, lambda *a, **k: None)
    messagebox.askyesno = lambda *a, **k: True
    try:
        app.connect_demo()
        app.mail_list.tree.selection_set("0")
        app.update()
        assert app.preview.header.cget("text")
        app.query_var.set("has:claim is:unread")
        app.scope.set_key("sc_all")
        app.run_search()
        assert app.search_list.messages
        app.search_list.tree.selection_set("0")
        app.update()
        app.bulk_query.insert(0, "from:visa.com")
        app.bulk_preview()
        app.bulk_apply(True)
        app.r_name.insert(0, "Visa")
        app.r_query.insert(0, "from:visa.com")
        app.rule_categories = ["Contracargo"]
        app.r_flag.set(True)
        app.save_rule()
        app.rule_scope.set_key("sc_store")
        app.run_rules(only_current=True, apply=True)
        assert app.rules and re.search(r"[1-9]", app.rule_summary.cget("text"))
        app.draft_from_outlook()
        assert app.issues and app.draft["editable"]
        app.issue_tree.selection_set("0")
        app.select_issue()
        app.apply_issue()
        app.apply_safe()
        app.draft_apply()
        app.an_scope.set_key("sc_all")
        for run in (app.an_run_overview, app.an_run_phishing, app.an_run_sensitive, app.an_run_claims):
            run()
            app.update()
        assert app.an_sheets and app.suggestions
    finally:
        for name, fn in saved.items():
            setattr(messagebox, name, fn)


def exercise_moreinfo(app):
    import tempfile
    from pathlib import Path
    from tkinter import messagebox

    from PIL import Image

    tmp = Path(tempfile.mkdtemp())
    for n in range(3):
        Image.new("RGB", (800, 400), (200, 200, 230)).save(tmp / f"s{n}.png")
        app.prefs["sections"] = ["Customer profile", "Cards", "Claim"]
        app._fill_sections(select=app.prefs["sections"][n])
        app.add_shot(tmp / f"s{n}.png")
    app.tree.selection_set("1")
    app.update()
    app.prefs.update(folder=str(tmp / "share"), letter_folders=[str(tmp / "letters1"), str(tmp / "letters2")], use_word=False)
    app.case_var.set("12345")
    saved = messagebox.showinfo, messagebox.showwarning, messagebox.askyesnocancel
    messagebox.showinfo = messagebox.showwarning = lambda *a, **k: None
    asked = []
    messagebox.askyesnocancel = lambda *a, **k: asked.append(a) or False  # subir sin vista previa
    letter = tmp / "letter.txt"
    letter.write_text("No pay decision", encoding="utf-8")
    app.add_documents([str(letter)])
    from suite.moreinfo import letter as letter_tpl

    app.load_template(str(letter_tpl.make_sample_template(tmp / "blank.docx")), name="Credit card - English")
    app.load_template(str(letter_tpl.make_sample_template(tmp / "blank2.docx")), name="Débit - French")
    assert list(app.template_combo["values"]) == ["Credit card - English", "Débit - French"]
    app.template_combo.current(0)
    dialog = app.fill_letter()
    dialog.widgets["cc:customername"].insert(0, "Laura Méndez")
    reasons = dialog.widgets["cc:reason"]["values"]
    dialog.widgets["cc:reason"].set(reasons[0])
    field = next(f for f in dialog.fields if f.key == "cc:reason")
    dialog.add_value(field, dialog.add_buttons["cc:reason"].master, reasons[2])
    extra = dialog.add_value(field, dialog.add_buttons["cc:reason"].master, reasons[3])
    dialog.remove_value("cc:reason", extra.master, extra)  # ✕ quita una razón
    app.update()
    assert dialog.filled()["cc:reason"] == [reasons[0], reasons[2]]
    # una razón elegida no se puede volver a elegir; con todas elegidas no se añaden más líneas
    assert dialog.available(field, dialog.more["cc:reason"][0]) == [r for r in reasons if r != reasons[0]]
    dialog.add_value(field, dialog.add_buttons["cc:reason"].master, reasons[1])
    last = dialog.add_value(field, dialog.add_buttons["cc:reason"].master)
    assert dialog.available(field, last) == [reasons[3]]
    last.set(reasons[3])
    assert dialog.add_value(field, dialog.add_buttons["cc:reason"].master) is None
    assert dialog.add_buttons["cc:reason"].instate(["disabled"])
    dialog.remove_value("cc:reason", last.master, last)
    assert not dialog.add_buttons["cc:reason"].instate(["disabled"])
    # la dirección en una sola línea llena sus campos
    dialog.address_entry.insert(0, "221 Main Street, Apt 4B, Toronto ON M5V 2T6")
    dialog.fill_address()
    assert {k: dialog.widgets[k].get() for k in ("cc:addressline1", "cc:addressline2", "cc:city", "cc:province",
                                                 "cc:postalcode")} == {
        "cc:addressline1": "221 Main Street", "cc:addressline2": "Apt 4B", "cc:city": "Toronto",
        "cc:province": "ON", "cc:postalcode": "M5V 2T6"}
    app.letter_ready(dialog.template, dialog.filled())
    dialog.destroy()
    again = app.fill_letter(app._template_by_name("Credit card - English"), app.documents[0]["values"])
    assert again.values()["cc:reason"] == [reasons[0], reasons[2], reasons[1]]  # al volver a editar se conservan
    assert again.widgets["cc:addressline1"].get() == "221 Main Street"
    again.destroy()
    assert "2" in app.reminder.cget("text") and app.documents[0]["letter"]
    assert app.documents[0]["values"]["cc:customername"] == "Laura Méndez" and not app.documents[0]["previewed"]
    try:
        app.create()
        while app._busy:
            app.update()
            app.after(50)
    finally:
        messagebox.showinfo, messagebox.showwarning, messagebox.askyesnocancel = saved
    assert any("previewed" in str(x) for x in asked)
    assert (tmp / "share" / "12345,MOREINFO.pdf").exists() and (tmp / "share" / "12345,MOREINFO2.txt").exists()
    assert (tmp / "letters1" / "12345,MOREINFO1.pdf").exists() and (tmp / "letters2" / "12345,MOREINFO1.pdf").exists()
    app.nb.select(1)
    app.update()
    app.mode.set("excel")
    app._mode_changed()


@pytest.mark.parametrize("cls", [DataPilot, BIPilot, DocPilot, SlidePilot, FraudPilot, IcePilot, MailPilot,
                                 MoreInfoPilot])
def test_app_starts_and_switches_language(cls):
    app = cls()
    try:
        app.update()
        exercise(app)
        for lang in ("es", "en", "fr"):
            app.set_lang(lang)
            for i in range(len(app.nb.tabs())):
                app.nb.select(i)
                app.update()
        assert not app.t.missing, app.t.missing
    finally:
        app.destroy()
