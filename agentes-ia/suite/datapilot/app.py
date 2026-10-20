"""DataPilot: agente de IA para Excel."""

import tkinter as tk
from pathlib import Path
from tkinter import ttk


from .. import samples
from ..tabular import list_sheets, read_table
from ..ui import Choice, DataTable, PilotApp, TextBox
from . import logic
from .strings import STRINGS

AGG_KEYS = list(logic.AGGS)


class DataPilot(PilotApp):
    APP_NAME = "DataPilot"
    ICON_TEXT = "XL"
    ACCENT = "#217346"
    STRINGS = STRINGS

    def build(self):
        self.original = None
        self.df = None
        self.name = ""
        self.result = None
        self.report_summary = None
        self.report_summary_name = ""
        self._build_data()
        self._build_clean()
        self._build_analyze()
        self._build_formulas()
        self._build_report()

    # ------------------------------------------------------------ datos
    def _build_data(self):
        tab = self.add_tab("tab_data")
        bar = ttk.Frame(tab)
        bar.pack(fill="x")
        self.btn(bar, "open_data", self.open_data, accent=True).pack(side="left")
        self.btn(bar, "merge_files", self.merge).pack(side="left", padx=6)
        self.btn(bar, "load_sample", self.load_sample).pack(side="left")
        self.data_info = ttk.Label(bar, style="Title.TLabel")
        self.data_info.pack(side="left", padx=16)
        self.tr_call(self._show_data_info)
        self.lbl(tab, "data_hint", hint=True).pack(anchor="w", pady=(6, 6))

        panes = ttk.PanedWindow(tab, orient="vertical")
        panes.pack(fill="both", expand=True)
        top = self.lframe(panes, "preview", padding=6)
        self.preview = DataTable(top, self, height=10)
        self.preview.pack(fill="both", expand=True)
        bottom = self.lframe(panes, "col_profile", padding=6)
        self.profile_table = DataTable(bottom, None, height=7)
        self.profile_table.pack(fill="both", expand=True)
        panes.add(top, weight=3)
        panes.add(bottom, weight=2)
        self.tr_call(self._show_profile)

    def _set_data(self, df, name, reset=True):
        if reset:
            self.original = df.copy()
        self.df = df
        self.name = name
        self._show_data_info()
        self.preview.show(df)
        self.clean_preview.show(df)
        self._show_profile()
        self._refresh_columns()

    def _show_data_info(self):
        if self.df is not None:
            self.data_info.configure(text=self.t("loaded_rows", name=self.name, rows=len(self.df),
                                                 cols=len(self.df.columns)))

    def _show_profile(self):
        if self.df is None:
            return
        prof = logic.profile(self.df)
        prof["kind"] = prof["kind"].map(lambda k: self.t(f"kind_{k}"))
        prof.columns = [self.t(f"p_{c}") for c in prof.columns]
        self.profile_table.show(prof)

    def open_data(self):
        path = self.ask_open(["excel", "csv"])
        if not path:
            return
        sheet = self.ask_sheet(list_sheets(path))
        self.run_task(lambda: read_table(path, sheet), lambda df: self._set_data(df, Path(path).name))

    def merge(self):
        paths = self.ask_open(["excel", "csv"], multiple=True)
        if not paths:
            return
        label = self.t("source_col")
        self.run_task(lambda: logic.merge_files(paths, label),
                      lambda df: self._set_data(df, self.t("merged", n=len(paths))))

    def load_sample(self):
        self._set_data(samples.sales(self.t.lang), "sample.xlsx")

    # ------------------------------------------------------------ limpiar
    def _build_clean(self):
        tab = self.add_tab("tab_clean")
        left = self.lframe(tab, "clean_options")
        left.pack(side="left", fill="y", padx=(0, 10))
        self.clean_vars = {}
        for key in ("trim", "drop_empty", "dedupe", "numbers", "dates", "unify"):
            var = tk.BooleanVar(value=True)
            self.clean_vars[key] = var
            self.chk(left, f"opt_{key}", var).pack(anchor="w", pady=2)
        self.lbl(left, "case_label").pack(anchor="w", pady=(10, 2))
        self.case_choice = Choice(self, left, ["none", "title", "upper", "lower"],
                                  ["case_none", "case_title", "case_upper", "case_lower"])
        self.case_choice.pack(anchor="w", fill="x")
        self.btn(left, "apply_clean", self.apply_clean, accent=True).pack(fill="x", pady=(16, 4))
        self.btn(left, "undo", self.undo_clean).pack(fill="x", pady=4)
        self.btn(left, "save_excel", self.save_clean).pack(fill="x", pady=4)
        self.clean_report = TextBox(left, height=14, readonly=True, width=44)
        self.clean_report.pack(fill="both", expand=True, pady=(10, 0))

        right = self.lframe(tab, "preview", padding=6)
        right.pack(side="left", fill="both", expand=True)
        self.clean_preview = DataTable(right, self)
        self.clean_preview.pack(fill="both", expand=True)

    def apply_clean(self):
        if not self.need(self.df is not None):
            return
        options = {k: v.get() for k, v in self.clean_vars.items()}
        options["case"] = self.case_choice.key
        df, report = logic.clean(self.df, options, dayfirst=self.t.lang != "en")
        none = self.t("none")
        self.clean_report.set(self.t(
            "clean_report", rows=len(df), numbers=", ".join(report["numbers"]) or none,
            dates=", ".join(report["dates"]) or none,
            **{k: v for k, v in report.items() if k not in ("numbers", "dates")},
        ))
        self._set_data(df, self.name, reset=False)

    def undo_clean(self):
        if self.original is not None:
            self._set_data(self.original.copy(), self.name, reset=False)
            self.clean_report.set(self.t("undone"))

    def save_clean(self):
        if not self.need(self.df is not None):
            return
        path = self.ask_save("excel", Path(self.name).stem + "_clean.xlsx")
        if path:
            from openpyxl import Workbook

            from ..tabular import write_df

            def work():
                wb = Workbook()
                wb.active.title = self.t("sheet_data")
                write_df(wb.active, self.df, accent="217346")
                wb.save(path)

            self.run_task(work, lambda _: self.saved(path))

    # ------------------------------------------------------------ analizar
    def _build_analyze(self):
        tab = self.add_tab("tab_analyze")
        left = ttk.Frame(tab)
        left.pack(side="left", fill="y", padx=(0, 10))

        box = self.lframe(left, "pivot_box")
        box.pack(fill="x")
        box.columnconfigure(1, weight=1)
        self.rows_combo = self.field(box, "rows_by", ttk.Combobox(box, state="readonly", width=26), 0)
        self.cols_combo = self.field(box, "cols_by", ttk.Combobox(box, state="readonly", width=26), 1)
        self.value_combo = self.field(box, "value", ttk.Combobox(box, state="readonly", width=26), 2)
        self.agg_choice = self.field(box, "aggregation", Choice(self, box, AGG_KEYS, [f"agg_{a}" for a in AGG_KEYS]), 3)
        self.btn(box, "calculate", self.calc_pivot, accent=True).grid(row=4, column=0, columnspan=2, sticky="ew",
                                                                      pady=(8, 0))

        ask = self.lframe(left, "ask_box")
        ask.pack(fill="x", pady=(12, 0))
        self.question = TextBox(ask, height=4, width=44)
        self.question.pack(fill="x")
        self.lbl(ask, "ask_hint", hint=True, justify="left").pack(anchor="w", pady=4)
        self.btn(ask, "ask", self.ask_ai, accent=True).pack(fill="x")
        self.lbl(ask, "privacy_note", hint=True, wraplength=330, justify="left").pack(anchor="w", pady=(6, 0))

        right = self.lframe(tab, "result", padding=6)
        right.pack(side="left", fill="both", expand=True)
        self.result_note = ttk.Label(right, wraplength=640, justify="left")
        self.result_note.pack(anchor="w", pady=(0, 6))
        self.result_table = DataTable(right, self)
        self.result_table.pack(fill="both", expand=True)
        bar = ttk.Frame(right)
        bar.pack(fill="x", pady=(6, 0))
        self.btn(bar, "export_result", self.export_result).pack(side="left")
        self.btn(bar, "use_in_report", self.use_in_report).pack(side="left", padx=6)

    def _refresh_columns(self):
        cols = [str(c) for c in self.df.columns] if self.df is not None else []
        numeric = [str(c) for c in self.df.columns if logic.col_kind(self.df[c]) == "number"] if cols else []
        self.rows_combo["values"] = cols
        self.cols_combo["values"] = [""] + cols
        self.value_combo["values"] = numeric + [c for c in cols if c not in numeric]
        if cols:
            text = [c for c in cols if logic.col_kind(self.df[c]) == "text"]
            self.rows_combo.set(text[0] if text else cols[0])
            self.cols_combo.set("")
            self.value_combo.set(numeric[-1] if numeric else cols[0])

    def _show_result(self, df, note):
        self.result = df
        self.result_note.configure(text=note)
        self.result_table.show(df)

    def calc_pivot(self):
        if not self.need(self.df is not None):
            return
        rows, value = self.rows_combo.get(), self.value_combo.get()
        if not self.need(rows and value, "need_value"):
            return
        columns = self.cols_combo.get() or None
        agg = self.agg_choice.key
        df = logic.pivot(self.df, [rows], value, agg, columns)
        self._show_result(df, f"{self.t('agg_' + agg)} · {value} · {rows}" + (f" × {columns}" if columns else ""))

    def ask_ai(self):
        if not self.need(self.df is not None):
            return
        question = self.question.get()
        if not self.need(question, "need_question"):
            return
        prompt = f"Spreadsheet columns:\n{logic.schema_summary(self.df)}\n\nQuestion: {question}"
        df = self.df

        def work(ai):
            plan = ai.ask_json(logic.PLAN_SYSTEM, prompt, logic.PLAN_SCHEMA)
            try:
                return plan, logic.run_plan(df, plan)
            except KeyError as exc:
                return plan, exc

        def done(out):
            plan, result = out
            if isinstance(result, KeyError):
                self.info(self.t("plan_error", col=result.args[0]))
                return
            self._show_result(result, "✨ " + plan.get("explanation", ""))

        self.run_ai(work, done)

    def export_result(self):
        if not self.need(self.result is not None):
            return
        path = self.ask_save("excel", self.t("result") + ".xlsx")
        if path:
            from openpyxl import Workbook

            from ..tabular import write_df

            wb = Workbook()
            write_df(wb.active, self.result)
            wb.save(path)
            self.saved(path)

    def use_in_report(self):
        if not self.need(self.result is not None):
            return
        self.report_summary = self.result.copy()
        self.report_summary_name = self.result_note.cget("text")[:80]
        self._update_report_state()
        self.status(self.t("added_to_report"))

    # ------------------------------------------------------------ fórmulas
    def _build_formulas(self):
        tab = self.add_tab("tab_formulas")
        left = ttk.Frame(tab)
        left.pack(side="left", fill="both", expand=True, padx=(0, 10))

        gen = self.lframe(left, "formula_box")
        gen.pack(fill="x")
        self.formula_request = TextBox(gen, height=4)
        self.formula_request.pack(fill="x")
        self.lbl(gen, "formula_hint", hint=True, wraplength=520, justify="left").pack(anchor="w", pady=4)
        self.use_columns = tk.BooleanVar(value=True)
        self.chk(gen, "use_my_columns", self.use_columns).pack(anchor="w")
        self.btn(gen, "generate_formula", self.generate_formula, accent=True).pack(anchor="w", pady=(6, 0))

        trans = self.lframe(left, "translator_box")
        trans.pack(fill="x", pady=(12, 0))
        self.lbl(trans, "translator_hint", hint=True, wraplength=520, justify="left").pack(anchor="w")
        row = ttk.Frame(trans)
        row.pack(fill="x", pady=6)
        self.lbl(row, "formula_in").pack(side="left")
        self.formula_input = ttk.Entry(row, font=("Consolas", 11))
        self.formula_input.pack(side="left", fill="x", expand=True, padx=6)
        row2 = ttk.Frame(trans)
        row2.pack(fill="x")
        self.lbl(row2, "from_lang").pack(side="left")
        self.formula_lang = Choice(self, row2, ["en", "es", "fr"], ["lang_en", "lang_es", "lang_fr"], width=18)
        self.formula_lang.pack(side="left", padx=6)
        self.btn(row2, "translate", self.translate_formula).pack(side="left")
        self.btn(row2, "explain_formula", self.explain_formula).pack(side="left", padx=6)

        right = ttk.Frame(tab)
        right.pack(side="left", fill="both", expand=True)
        out = self.lframe(right, "formula_out")
        out.pack(fill="x")
        out.columnconfigure(1, weight=1)
        self.formula_outs = {}
        for i, lang in enumerate(("en", "es", "fr")):
            self.lbl(out, f"lang_{lang}").grid(row=i, column=0, sticky="w", pady=3)
            entry = ttk.Entry(out, font=("Consolas", 11))
            entry.grid(row=i, column=1, sticky="ew", padx=6, pady=3)
            self.btn(out, "copy", lambda e=entry: self.copy(e.get())).grid(row=i, column=2, pady=3)
            self.formula_outs[lang] = entry
        how = self.lframe(right, "how_it_works")
        how.pack(fill="both", expand=True, pady=(12, 0))
        self.formula_explain = TextBox(how, height=12, readonly=True)
        self.formula_explain.pack(fill="both", expand=True)

    def _set_formulas(self, formula_en):
        for lang, entry in self.formula_outs.items():
            entry.delete(0, "end")
            entry.insert(0, logic.translate_formula(formula_en, "en", lang))

    def translate_formula(self):
        formula = self.formula_input.get().strip()
        if formula:
            self._set_formulas(logic.translate_formula(formula, self.formula_lang.key, "en"))

    def generate_formula(self):
        request = self.formula_request.get()
        if not self.need(request, "need_question"):
            return
        prompt = f"Request: {request}"
        if self.use_columns.get() and self.df is not None:
            prompt += f"\n\nSheet layout (row 1 = headers, data from row 2 to {len(self.df) + 1}): " \
                      f"{logic.sheet_layout(self.df)}"

        def done(data):
            self._set_formulas(data.get("formula_en", ""))
            steps = "\n".join(f"• {s}" for s in data.get("steps", []))
            self.formula_explain.set(f"{data.get('explanation', '')}\n\n{steps}\n\n{data.get('example', '')}")

        self.run_ai(lambda ai: ai.ask_json(logic.FORMULA_SYSTEM, prompt, logic.FORMULA_SCHEMA), done)

    def explain_formula(self):
        formula = self.formula_input.get().strip() or self.formula_outs["en"].get().strip()
        if not self.need(formula, "need_question"):
            return
        self.run_ai(lambda ai: ai.ask(logic.EXPLAIN_SYSTEM, f"Formula: {formula}", max_tokens=4000),
                    self.formula_explain.set)

    # ------------------------------------------------------------ informe
    def _build_report(self):
        tab = self.add_tab("tab_report")
        box = self.lframe(tab, "report_box")
        box.pack(fill="x")
        self.lbl(box, "report_hint", hint=True, justify="left").pack(anchor="w")
        self.report_state = ttk.Label(box)
        self.report_state.pack(anchor="w", pady=6)
        bar = ttk.Frame(box)
        bar.pack(fill="x")
        self.btn(bar, "gen_insights", self.gen_insights).pack(side="left")
        self.btn(bar, "export_report", self.export_report, accent=True).pack(side="left", padx=6)
        ins = self.lframe(tab, "insights")
        ins.pack(fill="both", expand=True, pady=(12, 0))
        self.insights = TextBox(ins, height=16)
        self.insights.pack(fill="both", expand=True)
        self.tr_call(self._update_report_state)

    def _update_report_state(self):
        if self.report_summary is None:
            self.report_state.configure(text=self.t("report_no_summary"))
        else:
            self.report_state.configure(text=self.t("report_summary_state", name=self.report_summary_name))

    def gen_insights(self):
        if not self.need(self.df is not None):
            return
        context = logic.insights_context(self.df)
        self.run_ai(lambda ai: ai.ask(logic.INSIGHTS_SYSTEM, f"Dataset: {self.name}\n\n{context}", max_tokens=6000),
                    self.insights.set)

    def export_report(self):
        if not self.need(self.df is not None):
            return
        path = self.ask_save("excel", f"{self.t('report_name')}_{Path(self.name).stem}.xlsx")
        if not path:
            return
        labels = {
            "data": self.t("sheet_data"), "summary": self.t("sheet_summary"), "profile": self.t("sheet_profile"),
            "insights": self.t("sheet_insights"), "disclaimer": self.t("ai_disclaimer"),
            **{f"p_{c}": self.t(f"p_{c}") for c in ("column", "kind", "filled", "empty", "unique", "example", "min",
                                                     "max", "mean")},
        }
        df, summary, insights = self.df, self.report_summary, self.insights.get()
        if summary is None:
            text_cols = [c for c in df.columns if logic.col_kind(df[c]) == "text" and df[c].nunique() <= 40]
            num_cols = [c for c in df.columns if logic.col_kind(df[c]) == "number"]
            if text_cols and num_cols:
                summary = logic.pivot(df, [text_cols[0]], num_cols[-1], "sum")
        self.run_task(lambda: logic.export_report(path, df, labels, summary, insights), self.saved)


def main():
    DataPilot().mainloop()


if __name__ == "__main__":
    main()
