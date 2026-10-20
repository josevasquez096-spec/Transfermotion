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


@pytest.mark.parametrize("cls", [DataPilot, BIPilot, DocPilot, SlidePilot, FraudPilot, IcePilot, MailPilot])
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
