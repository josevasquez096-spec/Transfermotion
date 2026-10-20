"""Autoprueba sin interfaz: `DataPilot.exe --selftest` genera los archivos de ejemplo de la app en una carpeta
temporal y termina con código 0 si todo funciona (sirve para comprobar el ejecutable empaquetado)."""

import sys
import tempfile
import traceback
from pathlib import Path


def _theme():
    import tkinter as tk

    import sv_ttk

    root = tk.Tk()
    root.withdraw()
    sv_ttk.set_theme("light")
    root.update()
    root.destroy()


def _datapilot(out):
    from . import samples
    from .datapilot import logic

    df = logic.clean(samples.sales("es"))[0]
    labels = {"data": "Datos", "summary": "Resumen", "profile": "Perfil", "insights": "IA", "disclaimer": "-"}
    logic.export_report(out / "report.xlsx", df, labels, logic.pivot(df, ["Región"], "Total"), "ok")


def _bipilot(out):
    from datetime import date

    from . import samples
    from .bipilot import logic

    tables = samples.bi_model("en")
    rels = logic.suggest_relationships(tables)
    labels = {k: k for k in ("doc", "doc_title", "table", "column", "type", "role", "role_fact", "role_dimension",
                             "role_other", "relationships", "one", "many", "cardinality", "coverage", "issues",
                             "calendar")}
    logic.export_model(out / "model.xlsx", tables, rels, "", labels,
                       logic.calendar_df(date(2025, 1, 1), date(2025, 12, 31)))


def _docpilot(out):
    from . import samples
    from .docpilot import logic

    tpl = logic.sample_template(out / "template.docx", "fr")
    assert len(logic.mail_merge(tpl, samples.merge_data("fr"), out / "merge", "fr")) == 5


def _slidepilot(out):
    from .slidepilot import logic
    from .slidepilot.strings import SAMPLE_OUTLINE

    logic.build_pptx(logic.parse_outline(SAMPLE_OUTLINE["en"]), out / "deck.pptx", "dark", "en")


def _fraudpilot(out):
    from . import samples
    from .docpilot.logic import markup_to_docx
    from .fraudpilot import logic

    store = logic.CaseStore(out / "cases.db")
    claim = logic.new_claim()
    claim.update(id="FR-TEST", customer_name="Test", amount=100)
    claim["evaluation"] = logic.evaluate(claim)
    store.save(claim)
    df = samples.fraud_claims("es")
    detail, result = logic.analyze_batch(df, logic.guess_mapping(df.columns))
    assert result["summary"]["cpp_merchants"]
    markup_to_docx("# Test\nok", out / "letter.docx")


def _icepilot(out):
    import re

    from .icepilot import content, games, office
    from .icepilot.build import build_html

    for game, spec in games.GAMES.items():
        cfg = games.new_config(game, "es")
        cfg["items"] = content.pack_items("fraud", game, "es", spec["columns"])
        page, _ = build_html(cfg)
        external = set(re.findall(r"https?://[^\s\"'<>)]+", page)) - {"http://www.w3.org/2000/svg"}
        assert not external, external
        (out / f"{game}.html").write_text(page, encoding="utf-8")
        office.build_docx(cfg, out / f"{game}.docx")
        if spec["pptx"]:
            office.build_pptx(cfg, out / f"{game}.pptx")


CHECKS = {"datapilot": _datapilot, "bipilot": _bipilot, "docpilot": _docpilot, "slidepilot": _slidepilot,
          "fraudpilot": _fraudpilot, "icepilot": _icepilot}


def run(app):
    try:
        out = Path(tempfile.mkdtemp(prefix=f"{app}_selftest_"))
        CHECKS[app](out)
        _theme()
        print(f"{app} selftest OK: {out}")
        return 0
    except Exception:  # se informa y se devuelve un código de error
        traceback.print_exc()
        return 1


def maybe_run(app):
    if "--selftest" in sys.argv:
        sys.exit(run(app))
