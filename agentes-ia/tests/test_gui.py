"""Arranca cada app, recorre los tres idiomas y comprueba que no falte ninguna traducción.

Necesita una pantalla (en Linux: xvfb-run python -m pytest).
"""

import os
import sys

import pytest

tk = pytest.importorskip("tkinter")
if sys.platform.startswith("linux") and not os.environ.get("DISPLAY"):
    pytest.skip("sin pantalla", allow_module_level=True)

from suite.bipilot.app import BIPilot  # noqa: E402
from suite.datapilot.app import DataPilot  # noqa: E402
from suite.docpilot.app import DocPilot  # noqa: E402
from suite.fraudpilot.app import FraudPilot  # noqa: E402
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


@pytest.mark.parametrize("cls", [DataPilot, BIPilot, DocPilot, SlidePilot, FraudPilot])
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
