"""DocPilot: agente de IA para Word."""

import tkinter as tk
from pathlib import Path
from tkinter import colorchooser, filedialog, ttk

from .. import samples
from ..tabular import list_sheets, read_table
from ..ui import Choice, PilotApp, TextBox, open_path
from . import logic
from .strings import STRINGS

LANG_KEYS = ["es", "en", "fr"]


class DocPilot(PilotApp):
    APP_NAME = "DocPilot"
    ICON_TEXT = "W"
    ACCENT = "#2B579A"
    STRINGS = STRINGS

    def build(self):
        self.doc_color = "#2B579A"
        self.merge_template = None
        self.merge_df = None
        self._build_draft()
        self._build_improve()
        self._build_merge()

    # ------------------------------------------------------------ redactar
    def _build_draft(self):
        tab = self.add_tab("tab_draft")
        form = ttk.Frame(tab)
        form.pack(side="left", fill="y", padx=(0, 10))
        form.columnconfigure(1, weight=1)
        self.doc_type = self.field(form, "doc_type", Choice(self, form, logic.DOC_TYPES,
                                                            [f"type_{k}" for k in logic.DOC_TYPES], width=30), 0)
        self.tone = self.field(form, "tone", Choice(self, form, logic.TONES, [f"tone_{k}" for k in logic.TONES]), 1)
        self.length = self.field(form, "length", Choice(self, form, logic.LENGTHS,
                                                        [f"len_{k}" for k in logic.LENGTHS], default=1), 2)
        self.doc_lang = self.field(form, "doc_lang", Choice(self, form, LANG_KEYS, [f"lang_{k}" for k in LANG_KEYS],
                                                            default=LANG_KEYS.index(self.t.lang)), 3)
        self.title_entry = self.field(form, "title", ttk.Entry(form, width=32), 4)
        self.company = self.field(form, "company", ttk.Entry(form, width=32), 5)
        self.recipient = self.field(form, "recipient", ttk.Entry(form, width=32), 6)
        self.lbl(form, "key_points").grid(row=7, column=0, columnspan=2, sticky="w", pady=(8, 2))
        self.points = TextBox(form, height=9, width=44)
        self.points.grid(row=8, column=0, columnspan=2, sticky="nsew")
        form.rowconfigure(8, weight=1)
        bar = ttk.Frame(form)
        bar.grid(row=9, column=0, columnspan=2, sticky="ew", pady=(8, 0))
        self.btn(bar, "draft_ai", self.draft_ai, accent=True).pack(side="left")
        self.btn(bar, "draft_template", self.draft_template).pack(side="left", padx=6)
        self.btn(bar, "accent", self.pick_color).pack(side="left")
        self.color_dot = tk.Label(bar, bg=self.doc_color, width=2)
        self.color_dot.pack(side="left", padx=4)

        right = self.lframe(tab, "editor", padding=6)
        right.pack(side="left", fill="both", expand=True)
        self.lbl(right, "markup_hint", hint=True).pack(anchor="w", pady=(0, 4))
        self.editor = TextBox(right, height=24)
        self.editor.pack(fill="both", expand=True)
        out = ttk.Frame(right)
        out.pack(fill="x", pady=(6, 0))
        self.btn(out, "export_word", lambda: self.export_markup(self.editor.get()), accent=True).pack(side="left")
        self.btn(out, "copy", lambda: self.copy(self.editor.get())).pack(side="left", padx=6)
        self.btn(out, "analyze", lambda: self.show_stats(self.editor.get(), self.doc_lang.key)).pack(side="left")

    def pick_color(self):
        color = colorchooser.askcolor(self.doc_color, parent=self)[1]
        if color:
            self.doc_color = color
            self.color_dot.configure(bg=color)

    def draft_template(self):
        title = self.title_entry.get().strip() or self.t(f"type_{self.doc_type.key}")
        self.editor.set(logic.skeleton(self.doc_type.key, self.doc_lang.key, title, self.company.get().strip(),
                                       self.recipient.get().strip()))

    def draft_ai(self):
        points, title = self.points.get(), self.title_entry.get().strip()
        if not self.need(points or title, "need_title"):
            return
        lang = self.doc_lang.key
        anon = self.anonymizer()
        prompt = (f"Document type: {self.doc_type.key}\nTone: {self.tone.key}\nLength: {self.length.key}\n"
                  f"Language: {self.t.table['lang_' + lang][1]}\nTitle: {title or '(choose one)'}\n"
                  f"Company: {self.company.get().strip() or '-'}\nRecipient/audience: {self.recipient.get().strip() or '-'}\n"
                  f"Facts and key points:\n{points or '-'}")
        if anon:
            prompt = anon.mask(prompt)

        def work(ai):
            ai.lang = lang  # el documento sale en su idioma, no en el de la interfaz
            data = ai.ask_json(logic.DRAFT_SYSTEM, prompt, logic.DRAFT_SCHEMA, max_tokens=32000)
            text = logic.draft_to_markup(data)
            return anon.unmask(text) if anon else text

        self.run_ai(work, self.editor.set)

    def export_markup(self, text, name=None):
        if not self.need(text, "need_text"):
            return
        first = next((l[2:].strip() for l in text.splitlines() if l.startswith("# ")), None)
        path = self.ask_save("word", f"{name or first or 'DocPilot'}.docx"[:120])
        if path:
            lang = self.doc_lang.key
            self.run_task(lambda: logic.markup_to_docx(text, path, lang, self.company.get().strip(), self.doc_color),
                          self.saved)

    # ------------------------------------------------------------ mejorar
    def _build_improve(self):
        tab = self.add_tab("tab_improve")
        left = self.lframe(tab, "source", padding=6)
        left.pack(side="left", fill="both", expand=True, padx=(0, 10))
        bar = ttk.Frame(left)
        bar.pack(fill="x")
        self.btn(bar, "open_docx", self.open_source).pack(side="left")
        self.lbl(bar, "paste_hint", hint=True).pack(side="left", padx=8)
        self.source = TextBox(left, height=18)
        self.source.pack(fill="both", expand=True, pady=6)
        opts = ttk.Frame(left)
        opts.pack(fill="x")
        self.lbl(opts, "action").grid(row=0, column=0, sticky="w")
        self.action = Choice(self, opts, logic.IMPROVE_ACTIONS, [f"act_{a}" for a in logic.IMPROVE_ACTIONS], width=28)
        self.action.grid(row=0, column=1, sticky="w", padx=6)
        self.lbl(opts, "target_lang").grid(row=1, column=0, sticky="w", pady=4)
        self.target_lang = Choice(self, opts, LANG_KEYS, [f"lang_{k}" for k in LANG_KEYS], width=28,
                                  default=1 if self.t.lang == "es" else 0)
        self.target_lang.grid(row=1, column=1, sticky="w", padx=6)
        self.lbl(opts, "tone").grid(row=2, column=0, sticky="w")
        self.improve_tone = Choice(self, opts, logic.TONES, [f"tone_{k}" for k in logic.TONES], width=28)
        self.improve_tone.grid(row=2, column=1, sticky="w", padx=6)
        bar2 = ttk.Frame(left)
        bar2.pack(fill="x", pady=(8, 0))
        self.btn(bar2, "apply_ai", self.improve, accent=True).pack(side="left")
        self.btn(bar2, "analyze", lambda: self.show_stats(self.source.get(), None)).pack(side="left", padx=6)

        right = self.lframe(tab, "result", padding=6)
        right.pack(side="left", fill="both", expand=True)
        self.result = TextBox(right, height=24)
        self.result.pack(fill="both", expand=True)
        bar3 = ttk.Frame(right)
        bar3.pack(fill="x", pady=(6, 0))
        self.btn(bar3, "export_word", lambda: self.export_markup(self.result.get()), accent=True).pack(side="left")
        self.btn(bar3, "copy", lambda: self.copy(self.result.get())).pack(side="left", padx=6)
        self.btn(bar3, "use_as_source", lambda: self.source.set(self.result.get())).pack(side="left")

    def open_source(self):
        path = self.ask_open(["word", "text"])
        if not path:
            return
        if path.lower().endswith(".docx"):
            self.run_task(lambda: logic.read_docx_text(path), self.source.set)
        else:
            self.source.set(Path(path).read_text(encoding="utf-8", errors="replace"))

    def improve(self):
        text = self.source.get()
        if not self.need(text, "need_text"):
            return
        action = self.action.key
        extra = ""
        if action == "translate":
            extra = f"Target language: {self.t.table['lang_' + self.target_lang.key][1]}\n"
        elif action == "tone":
            extra = f"Requested tone: {self.improve_tone.key}\n"
        anon = self.anonymizer()
        body = anon.mask(text) if anon else text
        prompt = f"{extra}Document:\n<<<\n{body}\n>>>"
        out_lang = self.target_lang.key if action == "translate" else None

        def work(ai):
            if out_lang:
                ai.lang = out_lang
            result = ai.ask(logic.IMPROVE_SYSTEMS[action], prompt, max_tokens=64000)
            return anon.unmask(result) if anon else result

        self.run_ai(work, self.result.set)

    def show_stats(self, text, lang):
        if not self.need(text, "need_text"):
            return
        lang = lang or self.t.lang
        st = logic.text_stats(text, lang)
        out = self.t("stats", level=self.t("lvl_" + logic.readability_level(st["score"])),
                     **{k: st[k] for k in ("words", "sentences", "paragraphs", "minutes", "avg_sentence", "score")})
        if st["long"]:
            out += "\n" + self.t("long_sentences", n=len(st["long"])) + "\n" + "\n".join(
                f"• {s[:220]}" for s in st["long"][:8]) + "\n"
        if st["repeated"]:
            out += "\n" + self.t("repeated_words") + " " + ", ".join(f"{w} ({c})" for c, w in st["repeated"])
        self.info(out)

    # ------------------------------------------------------------ combinar
    def _build_merge(self):
        tab = self.add_tab("tab_merge")
        self.lbl(tab, "merge_hint", hint=True, wraplength=1100, justify="left").pack(anchor="w", pady=(0, 8))
        grid = ttk.Frame(tab)
        grid.pack(fill="x")
        grid.columnconfigure(1, weight=1)
        self.lbl(grid, "template").grid(row=0, column=0, sticky="w", pady=4)
        self.tpl_label = ttk.Label(grid, text="—", style="Hint.TLabel")
        self.tpl_label.grid(row=0, column=1, sticky="w", padx=8)
        self.btn(grid, "choose", self.choose_template).grid(row=0, column=2, padx=4)
        self.btn(grid, "sample_template", self.create_sample_template).grid(row=0, column=3)
        self.lbl(grid, "data").grid(row=1, column=0, sticky="w", pady=4)
        self.data_label = ttk.Label(grid, text="—", style="Hint.TLabel")
        self.data_label.grid(row=1, column=1, sticky="w", padx=8)
        self.merge_name = ""
        self.tr_call(self._show_data_label)
        self.btn(grid, "choose", self.choose_data).grid(row=1, column=2, padx=4)
        self.btn(grid, "sample_data", self.use_sample_data).grid(row=1, column=3, sticky="ew")
        self.lbl(grid, "out_folder").grid(row=2, column=0, sticky="w", pady=4)
        self.out_dir = tk.StringVar(value=str(Path.home() / "Documents" / "DocPilot"))
        ttk.Entry(grid, textvariable=self.out_dir).grid(row=2, column=1, sticky="ew", padx=8)
        self.btn(grid, "choose", self.choose_folder).grid(row=2, column=2, padx=4)

        mid = ttk.Frame(tab)
        mid.pack(fill="both", expand=True, pady=10)
        fields = self.lframe(mid, "fields_check", padding=6)
        fields.pack(side="left", fill="both", expand=True, padx=(0, 10))
        self.fields_box = TextBox(fields, height=12, readonly=True)
        self.fields_box.pack(fill="both", expand=True)
        opts = ttk.Frame(mid)
        opts.pack(side="left", fill="y")
        self.lbl(opts, "file_name_col").pack(anchor="w")
        self.name_col = ttk.Combobox(opts, state="readonly", width=28)
        self.name_col.pack(anchor="w", pady=(2, 10))
        self.single = tk.BooleanVar(value=False)
        self.chk(opts, "single_file", self.single).pack(anchor="w")
        self.btn(opts, "generate_docs", self.generate, accent=True).pack(fill="x", pady=(16, 4))
        self.btn(opts, "open_folder", lambda: open_path(self.out_dir.get())).pack(fill="x")
        self.tr_call(self._check_fields)

    def choose_template(self):
        path = self.ask_open(["word"])
        if path:
            self.merge_template = path
            self.tpl_label.configure(text=path)
            self._check_fields()

    def create_sample_template(self):
        path = self.ask_save("word", "template.docx")
        if path:
            logic.sample_template(path, self.t.lang)
            self.merge_template = path
            self.tpl_label.configure(text=path)
            self._check_fields()
            open_path(path)

    def choose_data(self):
        path = self.ask_open(["excel", "csv"])
        if not path:
            return
        sheet = self.ask_sheet(list_sheets(path))

        def done(df):
            self.merge_df, self.merge_name = df, Path(path).name
            self._show_data_label()
            self._check_fields()

        self.run_task(lambda: read_table(path, sheet), done)

    def use_sample_data(self):
        self.merge_df, self.merge_name = samples.merge_data(self.t.lang), "sample.xlsx"
        self._show_data_label()
        self._check_fields()

    def _show_data_label(self):
        if self.merge_df is not None:
            self.data_label.configure(text=self.t("loaded_rows", name=self.merge_name, rows=len(self.merge_df),
                                                  cols=len(self.merge_df.columns)))

    def choose_folder(self):
        folder = filedialog.askdirectory(parent=self, initialdir=self.out_dir.get())
        if folder:
            self.out_dir.set(folder)

    def _check_fields(self):
        cols = [str(c).strip() for c in self.merge_df.columns] if self.merge_df is not None else []
        self.name_col["values"] = [""] + cols
        if cols and not self.name_col.get():
            self.name_col.set(cols[0])
        if not self.merge_template:
            self.fields_box.set("")
            return
        try:
            fields = logic.find_placeholders(self.merge_template)
        except Exception as exc:  # plantilla dañada o no es .docx
            self.fields_box.set(str(exc))
            return
        if not fields:
            self.fields_box.set(self.t("no_fields"))
            return
        lines = [self.t("field_ok" if f in cols else "field_missing", name=f) for f in fields] if cols else fields
        self.fields_box.set("\n".join(lines))

    def generate(self):
        if not self.need(self.merge_template and self.merge_df is not None and self.out_dir.get(), "need_merge"):
            return
        template, df, folder = self.merge_template, self.merge_df, self.out_dir.get()
        name_col, single, lang = self.name_col.get() or None, self.single.get(), self.t.lang

        def done(paths):
            self.info(self.t("merge_done", n=len(paths), folder=folder))
            open_path(folder)

        self.run_task(lambda: logic.mail_merge(template, df, folder, lang, name_col, single), done)


def main():
    DocPilot().mainloop()


if __name__ == "__main__":
    main()
