"""Flujos con IA de cada app, con un cliente de Claude simulado (sin red ni coste)."""

import json
import os
import sys
import time
from types import SimpleNamespace

import pytest

tk = pytest.importorskip("tkinter")
if sys.platform.startswith("linux") and not os.environ.get("DISPLAY"):
    pytest.skip("sin pantalla", allow_module_level=True)

from suite import ui  # noqa: E402
from suite.ai import AIClient  # noqa: E402
from suite.bipilot import logic as bi  # noqa: E402
from suite.datapilot import logic as dp  # noqa: E402
from suite.docpilot import logic as doc  # noqa: E402
from suite.fraudpilot import logic as fraud  # noqa: E402
from suite.slidepilot import logic as sl  # noqa: E402

RESPONSES = {
    id(dp.PLAN_SCHEMA): {"explanation": "Ventas por región", "filters": [],
                         "group_by": [{"column": "Región", "date_part": "none"}],
                         "metrics": [{"column": "Total", "agg": "sum", "alias": "Ventas"}], "select_columns": [],
                         "sort_by": "Ventas", "ascending": False, "limit": 3},
    id(dp.FORMULA_SCHEMA): {"formula_en": '=SUMIFS(H:H,B:B,"Norte")', "explanation": "Suma", "steps": ["a"],
                            "example": "I2"},
    id(bi.DAX_SCHEMA): {"measure_name": "Margen", "dax": "Margen = DIVIDE ( 1, 2 )", "format_string": "0%",
                        "explanation": "x", "notes": ""},
    id(bi.M_SCHEMA): {"m_code": "let\n    Source = 1\nin\n    Source", "explanation": "x"},
    id(doc.DRAFT_SCHEMA): {"title": "Propuesta para [CLIENTE_1]", "subtitle": "Acme",
                           "sections": [{"heading": "Resumen", "paragraphs": ["Texto"], "bullets": ["uno"]}]},
    id(sl.DECK_SCHEMA): {"title": "Deck IA", "subtitle": "s", "slides": [
        {**sl.empty_slide("bullets", "Idea"), "bullets": ["a", "b"], "notes": "nota"},
        {**sl.empty_slide("chart", "Cifras"), "chart": {"type": "pie", "categories": ["A", "B"],
                                                         "series": [{"name": "S", "values": [1, 2]}]}}]},
    id(fraud.CASE_SCHEMA): {"summary": "Caso de [CLIENTE_1]", "typology": "app_scam", "risk_level": "high",
                            "key_facts": ["f"], "inconsistencies": [], "missing_information": ["m"],
                            "recommended_actions": ["r"], "liability_view": "l", "questions_for_customer": ["q"]},
}


class FakeClient:
    def __init__(self):
        self.calls = []
        self.beta = SimpleNamespace(messages=SimpleNamespace(stream=self._stream))

    def _stream(self, **kwargs):
        self.calls.append(kwargs)
        fmt = kwargs["output_config"].get("format")
        if fmt:
            text = json.dumps(RESPONSES[id(fmt["schema"])])
        else:
            text = "# Texto IA\nResultado para " + kwargs["messages"][0]["content"][:20]
        message = SimpleNamespace(stop_reason="end_turn", content=[SimpleNamespace(type="text", text=text)])
        return _Stream(message)


class _Stream:
    def __init__(self, message):
        self.message = message

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False

    def get_final_message(self):
        return self.message


@pytest.fixture
def fake(monkeypatch):
    client = FakeClient()
    monkeypatch.setattr(ui.AIClient, "from_settings",
                        classmethod(lambda cls, settings, lang: AIClient("k", lang=lang, client=client)))
    monkeypatch.setattr(ui.messagebox, "showinfo", lambda *a, **k: None)
    monkeypatch.setattr(ui.messagebox, "showerror", lambda *a, **k: pytest.fail(f"error dialog: {a}"))
    return client


def wait(app):
    deadline = time.time() + 10
    app.update()
    while app._busy and time.time() < deadline:
        app.update()
        time.sleep(0.02)
    app.update()
    assert not app._busy


def test_datapilot_ai(fake):
    from suite.datapilot.app import DataPilot

    app = DataPilot()
    try:
        app.set_lang("es")
        app.load_sample()
        app.apply_clean()
        app.question.set("ventas por región")
        app.ask_ai()
        wait(app)
        assert list(app.result.columns) == ["Región", "Ventas"] and len(app.result) == 3
        app.formula_request.set("suma norte")
        app.generate_formula()
        wait(app)
        assert app.formula_outs["es"].get() == '=SUMAR.SI.CONJUNTO(H:H;B:B;"Norte")'
        app.gen_insights()
        wait(app)
        assert app.insights.get().startswith("# Texto IA")
    finally:
        app.destroy()


def test_bipilot_ai(fake):
    from suite.bipilot.app import BIPilot

    app = BIPilot()
    try:
        app.load_sample()
        app.dax_request.set("margen")
        app.gen_dax_ai()
        wait(app)
        assert "Margen = DIVIDE" in app.dax_out.get()
        assert "Relationship:" in fake.calls[-1]["messages"][0]["content"]
        app.m_request.set("dividir columna")
        app.gen_m_ai()
        wait(app)
        assert "Source = 1" in app.m_out.get()
    finally:
        app.destroy()


def test_docpilot_ai_masks_personal_data(fake):
    from suite.docpilot.app import DocPilot

    app = DocPilot()
    try:
        app.points.set("Cliente: ana@example.com, cuenta 0123456789")
        app.draft_ai()
        wait(app)
        sent = fake.calls[-1]["messages"][0]["content"]
        assert "ana@example.com" not in sent and "0123456789" not in sent
        assert app.editor.get().startswith("# Propuesta")
        app.source.set("Texto de prueba.")
        app.action.set_key("translate")
        app.improve()
        wait(app)
        assert app.result.get().startswith("# Texto IA")
    finally:
        app.destroy()


def test_slidepilot_ai(fake, tmp_path):
    from suite.slidepilot.app import SlidePilot

    app = SlidePilot()
    try:
        app.topic.insert(0, "Plan")
        app.generate_ai()
        wait(app)
        deck = app._deck()
        assert deck["title"] == "Deck IA" and [s["layout"] for s in deck["slides"]] == ["bullets", "chart"]
        sl.build_pptx(deck, tmp_path / "d.pptx")
    finally:
        app.destroy()


def test_fraudpilot_ai(fake):
    from suite.fraudpilot.app import FraudPilot

    app = FraudPilot()
    try:
        app.sample_claim()
        name = app.entries["customer_name"].get()
        app.analyze_ai()
        wait(app)
        assert name not in fake.calls[-1]["messages"][0]["content"]
        assert f"Caso de {name}" in app.assessment.get()  # el marcador se restaura en la respuesta
        app.gen_letter()
        app.improve_letter()
        wait(app)
        assert app.letter.get().startswith("# Texto IA")
        app.sample_batch()
        app.run_batch()
        wait(app)
        app.batch_ai()
        wait(app)
        assert app.batch_report.get()
    finally:
        app.destroy()
