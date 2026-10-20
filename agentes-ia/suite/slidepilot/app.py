"""SlidePilot: agente de IA para crear presentaciones de PowerPoint."""

import tkinter as tk
from pathlib import Path
from tkinter import ttk

from .. import samples
from ..docpilot.logic import read_docx_text
from ..tabular import list_sheets, read_table
from ..ui import Choice, PilotApp, TextBox
from . import logic
from .strings import SAMPLE_OUTLINE, STRINGS

LANG_KEYS = ["es", "en", "fr"]
THUMB_W, THUMB_H = 300, 169


class SlidePilot(PilotApp):
    APP_NAME = "SlidePilot"
    ICON_TEXT = "P"
    ACCENT = "#C43E1C"
    STRINGS = STRINGS

    def build(self):
        self.excel_df = None
        self._build_content()
        self._build_design()

    # ------------------------------------------------------------ contenido
    def _build_content(self):
        tab = self.add_tab("tab_content")
        panes = ttk.PanedWindow(tab, orient="horizontal")
        panes.pack(fill="both", expand=True)
        sources = ttk.Notebook(panes)
        self._build_ai_source(sources)
        self._build_text_source(sources)
        self._build_excel_source(sources)
        right = self.lframe(panes, "outline", padding=6)
        self.outline = TextBox(right, height=26, font=("Consolas", 10))
        self.outline.pack(fill="both", expand=True)
        self.outline.text.bind("<<Modified>>", self._outline_changed)
        self.outline_info = ttk.Label(right, style="Hint.TLabel")
        self.outline_info.pack(anchor="w", pady=(4, 0))
        self.tr_call(self._update_outline_info)
        panes.add(sources, weight=2)
        panes.add(right, weight=3)

    def _sub_tab(self, nb, key):
        frame = ttk.Frame(nb, padding=10)
        nb.add(frame, text=key)
        self.tr_call(lambda: nb.tab(frame, text=self.t(key)))
        return frame

    def _build_ai_source(self, nb):
        tab = self._sub_tab(nb, "src_ai")
        tab.columnconfigure(1, weight=1)
        self.topic = self.field(tab, "topic", ttk.Entry(tab, width=36), 0)
        self.audience = self.field(tab, "audience", ttk.Entry(tab, width=36), 1)
        self.goal = self.field(tab, "goal", ttk.Entry(tab, width=36), 2)
        self.n_slides = self.field(tab, "n_slides", ttk.Spinbox(tab, from_=3, to=25, width=6), 3, sticky="w")
        self.n_slides.set(8)
        self.deck_lang = self.field(tab, "deck_lang", Choice(self, tab, LANG_KEYS, [f"lang_{k}" for k in LANG_KEYS],
                                                             default=LANG_KEYS.index(self.t.lang)), 4, sticky="w")
        self.lbl(tab, "material").grid(row=5, column=0, columnspan=2, sticky="w", pady=(8, 2))
        self.material = TextBox(tab, height=10, width=44)
        self.material.grid(row=6, column=0, columnspan=2, sticky="nsew")
        tab.rowconfigure(6, weight=1)
        bar = ttk.Frame(tab)
        bar.grid(row=7, column=0, columnspan=2, sticky="ew", pady=(8, 0))
        self.btn(bar, "gen_outline", self.generate_ai, accent=True).pack(side="left")
        self.btn(bar, "load_material", self.load_material).pack(side="left", padx=6)

    def _build_text_source(self, nb):
        tab = self._sub_tab(nb, "src_text")
        bar = ttk.Frame(tab)
        bar.pack(fill="x")
        self.btn(bar, "import_word", self.import_word, accent=True).pack(side="left")
        self.btn(bar, "insert_example", lambda: self.outline.set(SAMPLE_OUTLINE[self.t.lang])).pack(side="left",
                                                                                                   padx=6)
        box = self.lframe(tab, "syntax_title")
        box.pack(fill="both", expand=True, pady=(10, 0))
        syntax = TextBox(box, height=24, readonly=True, font=("Consolas", 9), width=44)
        syntax.pack(fill="both", expand=True)
        self.tr_call(lambda: syntax.set(self.t("syntax")))

    def _build_excel_source(self, nb):
        tab = self._sub_tab(nb, "src_excel")
        bar = ttk.Frame(tab)
        bar.pack(fill="x")
        self.btn(bar, "open_excel", self.open_excel, accent=True).pack(side="left")
        self.btn(bar, "load_sample", self.load_excel_sample).pack(side="left", padx=6)
        self.excel_info = ttk.Label(tab, style="Hint.TLabel")
        self.excel_info.pack(anchor="w", pady=6)
        form = ttk.Frame(tab)
        form.pack(fill="both", expand=True)
        form.columnconfigure(1, weight=1)
        self.cat_combo = self.field(form, "category", ttk.Combobox(form, state="readonly", width=28), 0)
        self.lbl(form, "values").grid(row=1, column=0, sticky="nw", pady=3)
        self.values_list = tk.Listbox(form, selectmode="extended", height=8, exportselection=False,
                                      font=("Segoe UI", 10), relief="flat", highlightthickness=1,
                                      highlightbackground="#d7dde5")
        self.values_list.grid(row=1, column=1, sticky="nsew", pady=3)
        self.chart_type = self.field(form, "chart_type", Choice(self, form, logic.CHART_TYPES,
                                                                [f"ct_{c}" for c in logic.CHART_TYPES]), 2)
        self.top_n = self.field(form, "top_n", ttk.Spinbox(form, from_=3, to=30, width=6), 3, sticky="w")
        self.top_n.set(10)
        bar2 = ttk.Frame(tab)
        bar2.pack(fill="x", pady=(8, 0))
        self.btn(bar2, "replace_outline", lambda: self.excel_outline(False), accent=True).pack(side="left")
        self.btn(bar2, "append_outline", lambda: self.excel_outline(True)).pack(side="left", padx=6)

    def _outline_changed(self, _event=None):
        if self.outline.text.edit_modified():
            self.outline.text.edit_modified(False)
            self.after_idle(self._update_outline_info)

    def _update_outline_info(self):
        deck = logic.parse_outline(self.outline.get())
        self.outline_info.configure(text=self.t("outline_info", n=len(deck["slides"])))

    def generate_ai(self):
        topic, material = self.topic.get().strip(), self.material.get()
        if not self.need(topic or material, "need_topic"):
            return
        lang = self.deck_lang.key
        try:
            n = int(self.n_slides.get())
        except ValueError:
            n = 8
        anon = self.anonymizer()
        body = anon.mask(material) if anon and material else material
        prompt = (f"Topic: {topic or '(infer from material)'}\nAudience: {self.audience.get().strip() or '-'}\n"
                  f"Goal: {self.goal.get().strip() or '-'}\nNumber of content slides: {n}\n"
                  f"Material:\n<<<\n{body or '-'}\n>>>")

        def work(ai):
            ai.lang = lang
            deck = ai.ask_json(logic.DECK_SYSTEM, prompt, logic.DECK_SCHEMA, max_tokens=32000)
            text = logic.deck_to_outline(deck)
            return anon.unmask(text) if anon else text

        self.run_ai(work, self.outline.set)

    def load_material(self):
        path = self.ask_open(["word", "text"])
        if path:
            text = read_docx_text(path) if path.lower().endswith(".docx") else Path(path).read_text(
                encoding="utf-8", errors="replace")
            self.material.set(text)

    def import_word(self):
        path = self.ask_open(["word"])
        if path:
            lang = self.t.lang
            self.run_task(lambda: logic.markup_to_outline(read_docx_text(path), lang), self.outline.set)

    def open_excel(self):
        path = self.ask_open(["excel", "csv"])
        if not path:
            return
        sheet = self.ask_sheet(list_sheets(path))
        self.run_task(lambda: read_table(path, sheet), lambda df: self._set_excel(df, Path(path).name))

    def load_excel_sample(self):
        from ..datapilot.logic import clean

        self._set_excel(clean(samples.sales(self.t.lang))[0], "sample.xlsx")

    def _set_excel(self, df, name):
        import pandas as pd

        self.excel_df = df
        self.excel_info.configure(text=f"{name} · {len(df)} × {len(df.columns)}")
        text_cols = [str(c) for c in df.columns if not pd.api.types.is_numeric_dtype(df[c])]
        num_cols = [str(c) for c in df.columns if pd.api.types.is_numeric_dtype(df[c])]
        self.cat_combo["values"] = text_cols + num_cols
        if text_cols:
            self.cat_combo.set(next((c for c in text_cols if 1 < df[c].nunique() <= 30), text_cols[0]))
        self.values_list.delete(0, "end")
        for c in num_cols:
            self.values_list.insert("end", c)
        if num_cols:
            self.values_list.selection_set(len(num_cols) - 1)

    def excel_outline(self, append):
        cat = self.cat_combo.get()
        values = [self.values_list.get(i) for i in self.values_list.curselection()]
        if not self.need(self.excel_df is not None and cat and values, "need_values"):
            return
        try:
            top = int(self.top_n.get())
        except ValueError:
            top = 10
        text = logic.excel_to_outline(self.excel_df, cat, values, self.chart_type.key, top, lang=self.t.lang)
        if append and self.outline.get():
            body = text.split("\n## ", 1)  # sin título ni subtítulo del bloque añadido
            text = self.outline.get() + "\n\n## " + body[1] if len(body) > 1 else self.outline.get()
        self.outline.set(text)

    # ------------------------------------------------------------ diseño
    def _build_design(self):
        tab = self.add_tab("tab_design")
        left = ttk.Frame(tab)
        left.pack(side="left", fill="y", padx=(0, 10))
        themes = self.lframe(left, "theme")
        themes.pack(fill="x")
        self.theme_var = tk.StringVar(value="corporate")
        for key, th in logic.THEMES.items():
            row = ttk.Frame(themes)
            row.pack(fill="x", pady=2)
            sw = tk.Canvas(row, width=64, height=22, highlightthickness=0)
            sw.create_rectangle(0, 0, 32, 22, fill="#" + th["primary"], outline="")
            sw.create_rectangle(32, 0, 48, 22, fill="#" + th["accent"], outline="")
            sw.create_rectangle(48, 0, 64, 22, fill="#" + th["panel"], outline="")
            sw.pack(side="left", padx=(0, 8))
            rb = ttk.Radiobutton(row, variable=self.theme_var, value=key, command=self.draw_preview)
            rb.pack(side="left")
            self.tr(rb, f"th_{key}")
        opts = self.lframe(left, "options")
        opts.pack(fill="x", pady=(10, 0))
        self.lbl(opts, "author").pack(anchor="w")
        self.author = ttk.Entry(opts, width=34)
        self.author.pack(fill="x", pady=(0, 6))
        self.lbl(opts, "contact").pack(anchor="w")
        self.contact = ttk.Entry(opts, width=34)
        self.contact.pack(fill="x", pady=(0, 6))
        self.agenda_var, self.closing_var = tk.BooleanVar(value=True), tk.BooleanVar(value=True)
        self.chk(opts, "add_agenda", self.agenda_var).pack(anchor="w")
        self.chk(opts, "add_closing", self.closing_var).pack(anchor="w")
        self.btn(left, "create_pptx", self.create_pptx, accent=True).pack(fill="x", pady=(14, 4))
        self.btn(left, "refresh_preview", self.draw_preview).pack(fill="x")

        right = self.lframe(tab, "preview", padding=6)
        right.pack(side="left", fill="both", expand=True)
        self.preview = tk.Canvas(right, highlightthickness=0, background="#e5e7eb")
        bar = ttk.Scrollbar(right, orient="vertical", command=self.preview.yview)
        self.preview.configure(yscrollcommand=bar.set)
        bar.pack(side="right", fill="y")
        self.preview.pack(side="left", fill="both", expand=True)
        self.preview.bind("<Configure>", lambda e: self.draw_preview())
        self.nb.bind("<<NotebookTabChanged>>", lambda e: self.draw_preview())

    def _deck(self):
        return logic.parse_outline(self.outline.get())

    def create_pptx(self):
        deck = self._deck()
        if not self.need(deck["slides"] or deck["title"], "empty_outline"):
            return
        path = self.ask_save("pptx", f"{deck['title'] or 'SlidePilot'}.pptx"[:120])
        if not path:
            return
        lang = self.deck_lang.key
        args = (self.theme_var.get(), lang, self.author.get().strip(), self.agenda_var.get(),
                self.closing_var.get(), self.contact.get().strip())
        self.run_task(lambda: logic.build_pptx(deck, path, *args), self.saved)

    # Vista previa simplificada dibujada en un Canvas (miniaturas aproximadas).
    def draw_preview(self):
        if not hasattr(self, "preview"):
            return
        c = self.preview
        c.delete("all")
        deck = self._deck()
        th = {k: ("#" + v if isinstance(v, str) else v) for k, v in logic.THEMES[self.theme_var.get()].items()}
        slides = [("cover", {"title": deck["title"], "subtitle": deck["subtitle"]})]
        slides += [(s["layout"], s) for s in deck["slides"]]
        if self.closing_var.get():
            slides.append(("closing", {"title": logic.CLOSING[self.deck_lang.key]}))
        width = max(c.winfo_width(), 400)
        cols = max(1, (width - 10) // (THUMB_W + 14))
        for i, (layout, s) in enumerate(slides):
            x = 10 + (i % cols) * (THUMB_W + 14)
            y = 10 + (i // cols) * (THUMB_H + 14)
            self._thumb(c, x, y, layout, s, th, i + 1)
        rows = (len(slides) + cols - 1) // cols
        c.configure(scrollregion=(0, 0, width, 20 + rows * (THUMB_H + 14)))

    def _thumb(self, c, x, y, layout, s, th, number):
        w, h = THUMB_W, THUMB_H
        dark_bg = layout in ("cover", "closing")
        c.create_rectangle(x, y, x + w, y + h, fill=th["primary"] if dark_bg else th["bg"], outline="#c7cdd6")
        f = ("Segoe UI", 8)
        if layout == "cover":
            c.create_rectangle(x + 16, y + 52, x + 46, y + 55, fill=th["accent"], outline="")
            c.create_text(x + 16, y + 62, text=s["title"][:60], anchor="nw", fill="white", width=w - 30,
                          font=("Segoe UI", 12, "bold"))
            c.create_text(x + 16, y + 112, text=s.get("subtitle", "")[:70], anchor="nw", fill="#cbd5e1", font=f)
            c.create_rectangle(x, y + h - 28, x + w, y + h - 25, fill=th["accent"], outline="")
            return
        if layout == "closing":
            c.create_text(x + w / 2, y + h / 2 - 6, text=s["title"], fill="white", font=("Segoe UI", 16, "bold"))
            return
        if layout == "section":
            c.create_rectangle(x, y, x + w * 0.32, y + h, fill=th["accent"], outline="")
            c.create_text(x + 14, y + h / 2, text=f"{number:02d}", anchor="w", fill="white",
                          font=("Segoe UI", 20, "bold"))
            c.create_text(x + w * 0.36, y + h / 2, text=s["title"][:50], anchor="w", fill=th["text"], width=w * 0.6,
                          font=("Segoe UI", 11, "bold"))
            return
        c.create_rectangle(x + 12, y + 12, x + 15, y + 28, fill=th["accent"], outline="")
        c.create_text(x + 20, y + 20, text=s["title"][:55], anchor="w", fill=th["text"], width=w - 30,
                      font=("Segoe UI", 9, "bold"))
        top = y + 40
        if layout == "kpis":
            kpis = s["kpis"][:4] or [{"value": "—", "label": ""}]
            cw = (w - 24 - 6 * (len(kpis) - 1)) / len(kpis)
            for i, k in enumerate(kpis):
                kx = x + 12 + i * (cw + 6)
                c.create_rectangle(kx, top + 14, kx + cw, top + 84, fill=th["panel"], outline="")
                c.create_rectangle(kx, top + 14, kx + cw, top + 16, fill=th["accent"], outline="")
                c.create_text(kx + cw / 2, top + 40, text=k["value"][:9], fill=th["accent"],
                              font=("Segoe UI", 12, "bold"))
                c.create_text(kx + cw / 2, top + 64, text=k["label"][:22], fill=th["text"], font=("Segoe UI", 7),
                              width=cw - 6)
        elif layout == "chart" and s["chart"]["series"]:
            series = s["chart"]["series"]
            cats = s["chart"]["categories"][:12]
            peak = max((max(v["values"][:12] or [0]) for v in series), default=1) or 1
            n = len(cats) * len(series)
            bw = (w - 40) / max(1, n + len(cats))
            base = y + h - 18
            for ci in range(len(cats)):
                for si, ser in enumerate(series):
                    val = ser["values"][ci] if ci < len(ser["values"]) else 0
                    bx = x + 20 + (ci * (len(series) + 1) + si) * bw
                    bh = (base - top - 6) * max(0, val) / peak
                    c.create_rectangle(bx, base - bh, bx + bw - 1, base, outline="",
                                       fill="#" + logic.THEMES[self.theme_var.get()]["series"][si % 6])
            c.create_line(x + 16, base, x + w - 16, base, fill=th["muted"])
        elif layout == "columns":
            for i, side in enumerate(("left", "right")):
                px = x + 12 + i * (w - 24) / 2
                c.create_rectangle(px + 2, top, px + (w - 24) / 2 - 2, y + h - 14, fill=th["panel"], outline="")
                c.create_text(px + 8, top + 8, text=s[f"{side}_title"][:24], anchor="nw", fill=th["accent"],
                              font=("Segoe UI", 8, "bold"))
                for j, b in enumerate(s[f"{side}_bullets"][:5]):
                    c.create_text(px + 10, top + 26 + j * 14, text="• " + b[:30], anchor="nw", fill=th["text"], font=f)
        elif layout == "timeline":
            steps = s["steps"][:6] or ["—"]
            gap = (w - 24) / len(steps)
            ly = top + 45
            c.create_line(x + 16, ly, x + w - 16, ly, fill=th["muted"], width=2)
            for i, st in enumerate(steps):
                cx = x + 12 + gap * i + gap / 2
                c.create_oval(cx - 7, ly - 7, cx + 7, ly + 7, fill=th["accent"], outline="")
                c.create_text(cx, ly + 20, text=st.split(":")[0][:14], fill=th["text"], font=("Segoe UI", 7, "bold"))
        elif layout == "quote":
            c.create_text(x + 20, top + 6, text="“", anchor="nw", fill=th["accent"], font=("Segoe UI", 28, "bold"))
            c.create_text(x + 44, top + 30, text=s["quote"][:120], anchor="nw", fill=th["text"], width=w - 70,
                          font=("Segoe UI", 9, "italic"))
        elif layout == "table" and s["table"]:
            rows = s["table"][:7]
            ncols = max(len(r) for r in rows)
            cw = (w - 24) / ncols
            for ri, row in enumerate(rows):
                ry = top + ri * 16
                fill = th["primary"] if ri == 0 else (th["panel"] if ri % 2 else th["bg"])
                c.create_rectangle(x + 12, ry, x + w - 12, ry + 16, fill=fill, outline="")
                for ci, cell in enumerate(row[:ncols]):
                    c.create_text(x + 16 + ci * cw, ry + 8, text=str(cell)[:14], anchor="w",
                                  fill="white" if ri == 0 else th["text"], font=("Segoe UI", 7))
        else:
            for j, b in enumerate(s["bullets"][:7]):
                indent = 12 if b.startswith("  ") else 0
                c.create_text(x + 22 + indent, top + 4 + j * 16, text="• " + b.strip().replace("**", "")[:52],
                              anchor="nw", fill=th["text"], font=f)
        c.create_text(x + w - 8, y + h - 8, text=str(number), anchor="se", fill=th["muted"], font=("Segoe UI", 7))


def main():
    SlidePilot().mainloop()


if __name__ == "__main__":
    main()
