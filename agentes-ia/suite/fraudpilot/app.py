"""FraudPilot: agente de IA para reclamaciones de fraude."""

import tkinter as tk
from datetime import date, timedelta
from pathlib import Path
from tkinter import messagebox, ttk

import pandas as pd

from .. import samples
from ..datapilot.logic import parse_number
from ..docpilot.logic import format_date, format_number, markup_to_docx
from ..i18n import Translator
from ..tabular import list_sheets, read_table
from ..ui import Choice, DataTable, PilotApp, ScrollFrame, TextBox
from . import logic
from .strings import LETTERS, STRINGS

LANG_KEYS = ["es", "en", "fr"]
CURRENCIES = ("USD", "EUR", "MXN", "COP", "CAD", "GBP", "CLP", "PEN", "ARS", "DOP", "GTQ", "CHF", "MAD", "XOF")
LETTER_KEYS = ("ack", "info_request", "provisional", "favorable", "unfavorable", "dispute")
STATUS_FILTERS = ("all", "open") + logic.STATUSES
SAMPLE_CLAIM = {
    "es": ("Laura Méndez", "Recibí una llamada de alguien que decía ser del banco. Me dijo que había un cargo "
           "sospechoso y que, para anularlo, le diera el código que me llegó por SMS. Después vi tres "
           "transferencias a una cuenta que no conozco. Bloqueé la app en cuanto me di cuenta."),
    "en": ("Emma Wilson", "I got a call from someone claiming to be from the bank. They said there was a suspicious "
           "charge and asked for the code I received by SMS to cancel it. Then I saw three transfers to an account "
           "I don't know. I locked the app as soon as I noticed."),
    "fr": ("Pierre Lefèvre", "J'ai reçu un appel d'une personne se présentant comme la banque. Elle m'a parlé d'un "
           "débit suspect et m'a demandé le code reçu par SMS pour l'annuler. Ensuite j'ai vu trois virements vers "
           "un compte que je ne connais pas. J'ai bloqué l'application dès que je m'en suis aperçu."),
}


class FraudPilot(PilotApp):
    APP_NAME = "FraudPilot"
    ICON_TEXT = "FR"
    ACCENT = "#7B1E3A"
    STRINGS = STRINGS

    def build(self):
        self.store = logic.CaseStore(self.settings.data_dir() / "fraudpilot_cases.db")
        self.sla = {**logic.DEFAULT_SLA, **(self.store.get_meta("sla") or {})}
        self.claim = logic.new_claim()
        self.ai_result = None
        self.batch_df = None
        self.batch_result = None
        self._build_claim()
        self._build_cases()
        self._build_letters()
        self._build_batch()
        self.new_claim()

    # ------------------------------------------------------------ reclamación
    def _build_claim(self):
        tab = self.add_tab("tab_claim", padding=8)
        panes = ttk.PanedWindow(tab, orient="horizontal")
        panes.pack(fill="both", expand=True)
        scroll = ScrollFrame(panes)
        form = scroll.inner
        panes.add(scroll, weight=3)

        data = self.lframe(form, "claim_data")
        data.pack(fill="x", padx=(0, 8))
        for col in (1, 3):
            data.columnconfigure(col, weight=1)
        self.entries = {}

        def entry(key, row, col, widget=None):
            w = widget or ttk.Entry(data, width=22)
            self.lbl(data, f"f_{key}").grid(row=row, column=col, sticky="w", padx=(0 if col == 0 else 12, 6), pady=3)
            w.grid(row=row, column=col + 1, sticky="ew", pady=3)
            self.entries[key] = w
            return w

        entry("id", 0, 0).configure(state="readonly")
        entry("received", 0, 2)
        entry("customer_name", 1, 0)
        entry("customer_id", 1, 2)
        entry("account", 2, 0)
        entry("merchant", 2, 2)
        self.product = entry("product", 3, 0, Choice(self, data, logic.PRODUCTS, [f"prod_{p}" for p in logic.PRODUCTS]))
        self.channel = entry("channel", 3, 2, Choice(self, data, logic.CHANNELS, [f"ch_{c}" for c in logic.CHANNELS]))
        entry("txn_date", 4, 0)
        entry("amount", 4, 2)
        entry("currency", 5, 0, ttk.Combobox(data, values=CURRENCIES, width=10))
        entry("n_txns", 5, 2, ttk.Spinbox(data, from_=1, to=999, width=10))
        entry("prior_claims", 6, 0, ttk.Spinbox(data, from_=0, to=99, width=10))

        ind = self.lframe(form, "indicators")
        ind.pack(fill="x", padx=(0, 8), pady=(8, 0))
        self.ind_vars = {}
        for n, key in enumerate(logic.INDICATORS):
            var = tk.BooleanVar(value=False)
            self.ind_vars[key] = var
            self.chk(ind, f"ind_{key}", var).grid(row=n // 2, column=n % 2, sticky="w", padx=(0, 16), pady=1)

        nar = self.lframe(form, "f_narrative")
        nar.pack(fill="both", expand=True, padx=(0, 8), pady=(8, 0))
        self.narrative = TextBox(nar, height=6)
        self.narrative.pack(fill="both", expand=True)

        bar = ttk.Frame(form)
        bar.pack(fill="x", pady=8)
        self.btn(bar, "new_claim", self.new_claim).pack(side="left")
        self.btn(bar, "load_sample", self.sample_claim).pack(side="left", padx=6)
        self.btn(bar, "save_case", self.save_case, accent=True).pack(side="right", padx=(6, 8))

        right = self.lframe(panes, "assessment", padding=6)
        panes.add(right, weight=2)
        rbar = ttk.Frame(right)
        rbar.pack(fill="x")
        self.btn(rbar, "evaluate", self.evaluate, accent=True).pack(side="left")
        self.btn(rbar, "analyze_ai", self.analyze_ai).pack(side="left", padx=6)
        self.assessment = TextBox(right, height=30, readonly=True, width=40)
        self.assessment.pack(fill="both", expand=True, pady=(6, 0))
        self.lbl(right, "ev_disclaimer", hint=True, wraplength=420).pack(anchor="w", pady=(4, 0))
        self.tr_call(self._render_assessment)
        # El formulario necesita más ancho que la evaluación.
        self.after(300, lambda: panes.sashpos(0, int(panes.winfo_width() * 0.58)))

    def _set(self, key, value):
        w = self.entries[key]
        readonly = str(w.cget("state")) == "readonly" and not isinstance(w, ttk.Combobox)
        if readonly:
            w.configure(state="normal")
        w.delete(0, "end")
        w.insert(0, "" if value is None else str(value))
        if readonly:
            w.configure(state="readonly")

    def fill_form(self, claim):
        self.claim = claim
        for key in ("id", "received", "customer_name", "customer_id", "account", "merchant", "txn_date", "currency",
                    "n_txns", "prior_claims"):
            self._set(key, claim.get(key, ""))
        amount = claim.get("amount") or 0
        self._set("amount", f"{float(amount):.2f}" if amount else "")
        self.product.set_key(claim.get("product"))
        self.channel.set_key(claim.get("channel"))
        for key, var in self.ind_vars.items():
            var.set(bool(claim.get("indicators", {}).get(key)))
        self.narrative.set(claim.get("narrative", ""))
        self.ai_result = claim.get("ai_result")
        self._render_assessment()

    def collect(self):
        c = dict(self.claim)
        for key in ("id", "received", "customer_name", "customer_id", "account", "merchant", "txn_date", "currency"):
            c[key] = self.entries[key].get().strip()
        amount = parse_number(self.entries["amount"].get())
        c["amount"] = amount if amount is not None else None
        for key in ("n_txns", "prior_claims"):
            try:
                c[key] = int(self.entries[key].get())
            except ValueError:
                c[key] = 1 if key == "n_txns" else 0
        c["product"], c["channel"] = self.product.key, self.channel.key
        c["indicators"] = {k: bool(v.get()) for k, v in self.ind_vars.items()}
        c["narrative"] = self.narrative.get()
        return c

    def new_claim(self):
        claim = logic.new_claim()
        claim["id"] = logic.new_id(self.store.ids())
        claim["currency"] = "EUR" if self.t.lang in ("es", "fr") else "USD"
        self.fill_form(claim)

    def sample_claim(self):
        claim = logic.new_claim()
        name, story = SAMPLE_CLAIM[self.t.lang]
        today = date.today()
        claim.update(id=logic.new_id(self.store.ids()), customer_name=name, customer_id="C-1042", account="****4421",
                     product="transfer", channel="mobile_app", txn_date=(today - timedelta(days=1)).isoformat(),
                     amount=2850.0, currency="EUR" if self.t.lang != "en" else "USD", n_txns=3,
                     merchant="ES91 2100 0418 4502 0005 1332", narrative=story, prior_claims=0)
        claim["indicators"].update(contacted_by_fraudster=True, shared_credentials=True, authorized_payment=True)
        self.fill_form(claim)

    def evaluate(self):
        claim = self.collect()
        if not self.need(claim["customer_name"] and claim["amount"], "need_customer"):
            return None
        claim["evaluation"] = logic.evaluate(claim, self.sla)
        self.claim = claim
        self._render_assessment()
        return claim

    def _render_assessment(self):
        ev = self.claim.get("evaluation") or {}
        if not ev:
            self.assessment.set("")
            return
        t = self.t
        lines = [t("ev_header", typology=t("typ_" + ev["typology"]), priority=t("prio_" + ev["priority"]),
                   urgency=ev["urgency"], consistency=ev["consistency_risk"]),
                 t("ev_deadlines", **ev["deadlines"]), "", t("ev_flags")]
        lines += [f"• {t(k, **p)}" for k, p in ev["flags"]] or [t("ev_no_flags")]
        lines += ["", t("ev_actions")] + [f"{n}. {t(k)}" for n, k in enumerate(ev["actions"], start=1)]
        lines += ["", t("ev_documents")] + [f"☐ {t(k)}" for k in ev["documents"]]
        ai = self.ai_result
        if ai:
            lines += ["", "─" * 40, t("ev_ai"),
                      t("ai_typology", typology=t("typ_" + ai.get("typology", "undetermined")),
                        risk=t("risk_" + ai.get("risk_level", "medium"))), "", ai.get("summary", "")]
            for key, field in (("ai_facts", "key_facts"), ("ai_inconsistencies", "inconsistencies"),
                               ("ai_missing", "missing_information"), ("ai_questions", "questions_for_customer"),
                               ("ai_actions", "recommended_actions")):
                if ai.get(field):
                    lines += ["", t(key) + ":"] + [f"• {x}" for x in ai[field]]
            if ai.get("liability_view"):
                lines += ["", t("ai_liability") + ":", ai["liability_view"]]
        self.assessment.set("\n".join(lines))

    def analyze_ai(self):
        claim = self.evaluate()
        if claim is None:
            return
        anon = self.anonymizer()
        prompt = logic.case_prompt(claim, claim["evaluation"], anon)

        def work(ai):
            data = ai.ask_json(logic.CASE_SYSTEM, prompt, logic.CASE_SCHEMA)
            if anon:
                for key, value in data.items():
                    if isinstance(value, str):
                        data[key] = anon.unmask(value)
                    elif isinstance(value, list):
                        data[key] = [anon.unmask(v) for v in value]
            return data

        def done(data):
            self.ai_result = data
            self.claim["ai_result"] = data
            self._render_assessment()

        self.run_ai(work, done)

    def save_case(self):
        claim = self.evaluate()
        if claim is None:
            return
        claim["ai_result"] = self.ai_result
        self.claim = self.store.save(claim)
        self.refresh_cases()
        self.status(self.t("case_saved", id=claim["id"]))
        self.info(self.t("case_saved", id=claim["id"]))

    # ------------------------------------------------------------ casos
    def _build_cases(self):
        tab = self.add_tab("tab_cases")
        self.kpi_label = ttk.Label(tab, style="Title.TLabel")
        self.kpi_label.pack(anchor="w")
        bar = ttk.Frame(tab)
        bar.pack(fill="x", pady=6)
        self.lbl(bar, "filter").pack(side="left")
        self.status_filter = Choice(self, bar, STATUS_FILTERS, [f"st_{s}" for s in STATUS_FILTERS], width=20,
                                    default=1)
        self.status_filter.bind("<<ComboboxSelected>>", lambda e: self.refresh_cases(), add="+")
        self.status_filter.pack(side="left", padx=6)
        self.btn(bar, "open_case", self.open_selected).pack(side="left", padx=(12, 0))
        self.new_status = Choice(self, bar, logic.STATUSES, [f"st_{s}" for s in logic.STATUSES], width=20)
        self.new_status.pack(side="left", padx=(12, 4))
        self.btn(bar, "set_status", self.set_status).pack(side="left")
        self.btn(bar, "delete_case", self.delete_case).pack(side="left", padx=6)
        self.btn(bar, "export_cases", self.export_cases).pack(side="right")
        self.cases_table = DataTable(tab, self, height=14)
        self.cases_table.pack(fill="both", expand=True)
        self.cases_table.tree.bind("<Double-1>", lambda e: self.open_selected())

        sla = self.lframe(tab, "sla_box")
        sla.pack(fill="x", pady=(8, 0))
        self.sla_entries = {}
        for i, (key, label) in enumerate((("ack_days", "sla_ack"), ("provisional_days", "sla_provisional"),
                                          ("resolution_days", "sla_resolution"), ("late_days", "sla_late"),
                                          ("high_amount", "sla_high"))):
            self.lbl(sla, label).grid(row=0, column=2 * i, sticky="w", padx=(0 if i == 0 else 12, 4))
            e = ttk.Entry(sla, width=7)
            e.insert(0, str(self.sla[key]))
            e.grid(row=0, column=2 * i + 1)
            self.sla_entries[key] = e
        self.btn(sla, "save", self.save_sla).grid(row=0, column=10, padx=(12, 0))
        self.visible_cases = []
        self.tr_call(self.refresh_cases)

    def refresh_cases(self):
        if not hasattr(self, "cases_table"):
            return
        cases = self.store.all()
        flt = self.status_filter.key
        if flt == "open":
            cases = [c for c in cases if c.get("status") in logic.OPEN_STATUSES]
        elif flt != "all":
            cases = [c for c in cases if c.get("status") == flt]
        self.visible_cases = cases
        rows = logic.case_rows(cases)
        t = self.t
        colors = []
        for r in rows:
            left = r["days_left"]
            colors.append("#fde2e2" if left is not None and left < 0 else "#fff4cc" if left is not None and left <= 5
                          else None)
            r["typology"] = t("typ_" + r["typology"]) if r["typology"] else ""
            r["priority"] = t("prio_" + r["priority"]) if r["priority"] else ""
            r["status"] = t("st_" + r["status"])
        df = pd.DataFrame(rows, columns=["id", "received", "customer", "typology", "amount", "currency", "priority",
                                         "status", "due", "days_left"])
        df.columns = [t("c_" + c) for c in df.columns]
        self.cases_table.show(df, colors)
        all_rows = logic.case_rows(self.store.all())
        open_rows = [r for r in all_rows if r["days_left"] is not None]
        self.kpi_label.configure(text=t(
            "kpi_line", open=len(open_rows), overdue=sum(r["days_left"] < 0 for r in open_rows),
            soon=sum(0 <= r["days_left"] <= 5 for r in open_rows), amount=sum(r["amount"] for r in open_rows)))
        if hasattr(self, "letter_case"):
            self.letter_case["values"] = [t("current_form")] + self.store.ids()

    def _selected_case(self):
        idx = self.cases_table.selected_index()
        if idx is None or idx >= len(self.visible_cases):
            self.need(False, "select_case")
            return None
        return self.visible_cases[idx]

    def open_selected(self):
        case = self._selected_case()
        if case:
            self.fill_form(case)
            self.nb.select(0)

    def set_status(self):
        case = self._selected_case()
        if case:
            case["status"] = self.new_status.key
            self.store.save(case)
            self.refresh_cases()

    def delete_case(self):
        case = self._selected_case()
        if case and messagebox.askyesno(self.APP_NAME, self.t("confirm_delete", id=case["id"]), parent=self):
            self.store.delete(case["id"])
            self.refresh_cases()

    def export_cases(self):
        path = self.ask_save("excel", f"FraudPilot_{date.today().isoformat()}.xlsx")
        if not path:
            return
        t = self.t
        rows = logic.case_rows(self.store.all())
        for r in rows:
            r["typology"] = t("typ_" + r["typology"]) if r["typology"] else ""
            r["priority"] = t("prio_" + r["priority"]) if r["priority"] else ""
            r["status"] = t("st_" + r["status"])
        rows = [{t("c_" + k): v for k, v in r.items()} for r in rows]
        logic.export_cases(path, rows, {"sheet_cases": t("sheet_cases")})
        self.saved(path)

    def save_sla(self):
        for key, e in self.sla_entries.items():
            value = parse_number(e.get())
            if value is not None and value >= 0:
                self.sla[key] = int(value) if key != "high_amount" else float(value)
        self.store.set_meta("sla", self.sla)
        self.status(self.t("sla_saved"))

    # ------------------------------------------------------------ cartas
    def _build_letters(self):
        tab = self.add_tab("tab_letters")
        form = ttk.Frame(tab)
        form.pack(side="left", fill="y", padx=(0, 10))
        form.columnconfigure(1, weight=1)
        self.letter_case = self.field(form, "letter_case", ttk.Combobox(form, state="readonly", width=26), 0)
        self.letter_type = self.field(form, "letter_type", Choice(self, form, LETTER_KEYS,
                                                                  [f"lt_{k}" for k in LETTER_KEYS], width=26), 1)
        self.letter_lang = self.field(form, "letter_lang", Choice(self, form, LANG_KEYS,
                                                                  [f"lang_{k}" for k in LANG_KEYS], width=26,
                                                                  default=LANG_KEYS.index(self.t.lang)), 2)
        self.company = self.field(form, "company", ttk.Entry(form, width=28), 3)
        self.lbl(form, "reason").grid(row=4, column=0, columnspan=2, sticky="w", pady=(8, 2))
        self.reason = TextBox(form, height=4, width=40)
        self.reason.grid(row=5, column=0, columnspan=2, sticky="ew")
        self.btn(form, "gen_letter", self.gen_letter, accent=True).grid(row=6, column=0, columnspan=2, sticky="ew",
                                                                        pady=(12, 4))
        self.btn(form, "improve_letter", self.improve_letter).grid(row=7, column=0, columnspan=2, sticky="ew", pady=4)
        self.btn(form, "export_word", self.export_letter).grid(row=8, column=0, columnspan=2, sticky="ew", pady=4)
        right = self.lframe(tab, "letter", padding=6)
        right.pack(side="left", fill="both", expand=True)
        self.letter = TextBox(right, height=28)
        self.letter.pack(fill="both", expand=True)
        self.tr_call(self._letter_case_values)

    def _letter_case_values(self):
        values = [self.t("current_form")] + self.store.ids()
        index = max(0, self.letter_case.current())
        self.letter_case["values"] = values
        self.letter_case.current(min(index, len(values) - 1))

    def _letter_claim(self):
        if self.letter_case.current() > 0:
            return self.store.get(self.letter_case.get())
        claim = self.collect()
        claim["evaluation"] = logic.evaluate(claim, self.sla) if claim.get("amount") else {}
        return claim

    def gen_letter(self):
        claim = self._letter_claim()
        if not self.need(claim and claim.get("customer_name"), "need_customer"):
            return
        lang = self.letter_lang.key
        ev = claim.get("evaluation") or logic.evaluate(claim, self.sla)
        docs_t = Translator(STRINGS, lang=lang)
        documents = "\n".join(f"- {docs_t(d)}" for d in ev.get("documents", []))
        txn = logic.to_date(claim.get("txn_date"))
        due = logic.to_date((ev.get("deadlines") or {}).get("resolution"))
        reason = self.reason.get() or {"es": "[motivo]", "en": "[reason]", "fr": "[motif]"}[lang]
        text = LETTERS[self.letter_type.key][lang].format(
            customer=claim.get("customer_name", ""), claim_id=claim.get("id", ""),
            amount=format_number(float(claim.get("amount") or 0), lang), currency=claim.get("currency", ""),
            merchant=claim.get("merchant") or "—", txn_date=format_date(txn, lang) if txn else "—",
            due=format_date(due, lang) if due else "—", documents=documents, reason=reason.replace("\n", " "),
            company=self.company.get().strip() or "—", today=format_date(date.today(), lang))
        self.letter.set(text)

    def improve_letter(self):
        text = self.letter.get()
        if not self.need(text, "need_text"):
            return
        claim = self._letter_claim() or {}
        anon = self.anonymizer()
        body = text
        if anon:
            anon.add_known(claim.get("customer_name"), "CLIENTE")
            body = anon.mask(text)
        lang = self.letter_lang.key

        def work(ai):
            ai.lang = lang
            result = ai.ask(logic.LETTER_SYSTEM, body, max_tokens=8000)
            return anon.unmask(result) if anon else result

        self.run_ai(work, self.letter.set)

    def export_letter(self):
        text = self.letter.get()
        if not self.need(text, "need_text"):
            return
        claim = self._letter_claim() or {}
        path = self.ask_save("word", f"{claim.get('id', 'carta')}_{self.letter_type.key}.docx")
        if path:
            markup_to_docx(text, path, self.letter_lang.key, self.company.get().strip(), "#7B1E3A")
            self.saved(path)

    # ------------------------------------------------------------ análisis masivo
    def _build_batch(self):
        tab = self.add_tab("tab_batch")
        self.lbl(tab, "batch_hint", hint=True, wraplength=1100, justify="left").pack(anchor="w")
        bar = ttk.Frame(tab)
        bar.pack(fill="x", pady=6)
        self.btn(bar, "open_claims", self.open_batch, accent=True).pack(side="left")
        self.btn(bar, "load_sample", self.sample_batch).pack(side="left", padx=6)
        self.batch_info = ttk.Label(bar, style="Hint.TLabel")
        self.batch_info.pack(side="left", padx=8)
        mapping = self.lframe(tab, "mapping")
        mapping.pack(fill="x")
        self.map_combos = {}
        for i, field in enumerate(logic.FIELDS):
            self.lbl(mapping, f"m_{field}").grid(row=(i // 4) * 2, column=i % 4, sticky="w", padx=4)
            combo = ttk.Combobox(mapping, state="readonly", width=24)
            combo.grid(row=(i // 4) * 2 + 1, column=i % 4, sticky="w", padx=4, pady=(0, 6))
            self.map_combos[field] = combo
        self.lbl(mapping, "cluster_min").grid(row=2, column=3, sticky="w", padx=4)
        self.cluster_min = ttk.Spinbox(mapping, from_=3, to=100, width=6)
        self.cluster_min.set(5)
        self.cluster_min.grid(row=3, column=3, sticky="w", padx=4)
        bar2 = ttk.Frame(tab)
        bar2.pack(fill="x", pady=6)
        self.btn(bar2, "run_batch", self.run_batch, accent=True).pack(side="left")
        self.btn(bar2, "batch_ai", self.batch_ai).pack(side="left", padx=6)
        self.btn(bar2, "export_batch", self.export_batch).pack(side="left")
        self.batch_summary = ttk.Label(tab, justify="left")
        self.batch_summary.pack(anchor="w", pady=(0, 6))
        panes = ttk.PanedWindow(tab, orient="vertical")
        panes.pack(fill="both", expand=True)
        table_frame = ttk.Frame(panes)
        self.batch_table = DataTable(table_frame, self, height=8)
        self.batch_table.pack(fill="both", expand=True)
        self.batch_report = TextBox(panes, height=6, readonly=True)
        panes.add(table_frame, weight=3)
        panes.add(self.batch_report, weight=1)
        self.tr_call(self._show_batch)

    def open_batch(self):
        path = self.ask_open(["excel", "csv"])
        if not path:
            return
        sheet = self.ask_sheet(list_sheets(path))
        self.run_task(lambda: read_table(path, sheet), lambda df: self._set_batch(df, Path(path).name))

    def sample_batch(self):
        self._set_batch(samples.fraud_claims(self.t.lang), "sample.xlsx")

    def _set_batch(self, df, name):
        self.batch_df, self.batch_result = df, None
        self.batch_info.configure(text=f"{name} · {len(df)} × {len(df.columns)}")
        guess = logic.guess_mapping(df.columns)
        cols = [""] + [str(c) for c in df.columns]
        for field, combo in self.map_combos.items():
            combo["values"] = cols
            combo.set(str(guess.get(field, "")))
        self.batch_table.show(df)
        self.batch_summary.configure(text="")
        self.batch_report.set("")

    def _mapping(self):
        return {f: c.get() for f, c in self.map_combos.items() if c.get()}

    def run_batch(self):
        if not self.need(self.batch_df is not None):
            return
        mapping = self._mapping()
        if not self.need(mapping.get("amount"), "need_amount_map"):
            return
        try:
            cluster = int(self.cluster_min.get())
        except ValueError:
            cluster = 5
        df, sla = self.batch_df, self.sla

        def done(result):
            self.batch_result = result
            self._show_batch()

        self.run_task(lambda: logic.analyze_batch(df, mapping, sla, cluster), done)

    def _flag_names(self):
        return {k: self.t(k) for k in ("b_duplicate", "b_repeat", "b_late", "b_date_error", "b_high_amount", "b_round",
                                       "b_cpp")}

    def _show_batch(self):
        if not self.batch_result:
            return
        detail, result = self.batch_result
        s = result["summary"]
        self.batch_summary.configure(text=self.t("batch_summary", cpp=", ".join(s["cpp_merchants"]) or "—",
                                                 **{k: v for k, v in s.items() if k != "cpp_merchants"}))
        names = self._flag_names()
        view = detail.drop(columns=[c for c in detail.columns if c == "_delay_days"]).copy()
        view["_flags"] = view["_flags"].map(lambda v: ", ".join(names.get(x.strip(), x) for x in v.split(",") if x.strip()))
        view = view.rename(columns={"_score": self.t("score"), "_flags": self.t("flags")})
        cols = [self.t("score"), self.t("flags")] + [c for c in view.columns if c not in (self.t("score"), self.t("flags"))]
        view = view[cols]
        colors = ["#fde2e2" if sc >= 50 else "#fff4cc" if sc >= 25 else None for sc in detail["_score"].head(500)]
        self.batch_table.show(view, colors)

    def batch_ai(self):
        if not self.need(self.batch_result):
            return
        context = logic.batch_context(self.batch_result[1], self._mapping())
        self.run_ai(lambda ai: ai.ask(logic.BATCH_SYSTEM, context, max_tokens=6000), self.batch_report.set)

    def export_batch(self):
        if not self.need(self.batch_result):
            return
        path = self.ask_save("excel", f"FraudPilot_triage_{date.today().isoformat()}.xlsx")
        if not path:
            return
        keys = ("sheet_triage", "score", "flags", "sheet_summary", "k_claims", "k_amount", "k_flagged", "k_duplicates",
                "k_repeat", "k_late", "k_high", "k_cpp", "channel", "sheet_merchants", "merchant", "customers",
                "peak_30d", "peak_start", "suspect")
        labels = {k: self.t(k) for k in keys}
        detail, result = self.batch_result
        names = self._flag_names()
        self.run_task(lambda: logic.export_batch(path, detail, result, labels, names), self.saved)


def main():
    FraudPilot().mainloop()


if __name__ == "__main__":
    main()
