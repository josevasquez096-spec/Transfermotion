"""IcePilot: generador de icebreakers y juegos para reuniones en Teams (funciona sin internet)."""

import json
import re
import tempfile
import tkinter as tk
from pathlib import Path
from tkinter import colorchooser, messagebox, ttk

import pandas as pd

from ..ai import STR, obj
from ..tabular import list_sheets, read_table, write_df
from ..ui import Choice, EditableTable, PilotApp, TextBox, open_path
from . import content, games, office
from .build import build_html
from .strings import STRINGS

LANG_KEYS = ["es", "en", "fr"]
ICONS = ("🏆", "🎯", "🧠", "🎉", "🛡️", "🔐", "💳", "🕵️", "🎲", "🐍", "🎡", "🎱", "🔎", "😀", "🤔", "⭐", "🚀", "☕")
WIDTHS = {"question": 320, "statement": 420, "explain": 300, "a": 150, "b": 150, "c": 150, "d": 150, "correct": 110,
          "points": 70, "lie": 100, "text": 620, "term": 360, "prompt": 140, "s1": 230, "s2": 230, "s3": 230,
          "answer": 260, "hint": 420, "word": 220, "clue": 420, "category": 170, "person": 140}
AI_SYSTEM = """You are IcePilot, an expert facilitator who designs short, inclusive icebreaker games for online
business meetings (Microsoft Teams) at a bank. Create the requested number of items for the given game type and
topic, appropriate for a professional audience, accurate (no invented facts or statistics) and fun.
Field meanings for this game: {fields}. Return only the items."""


class IcePilot(PilotApp):
    APP_NAME = "IcePilot"
    ICON_TEXT = "IB"
    ACCENT = "#6D28D9"
    STRINGS = STRINGS

    def build(self):
        self.game = "quiz"
        self.items = {}
        self.seed = games.new_config()["seed"]
        self.colors = {"primary": "", "accent": ""}
        self._build_game_tab()
        self._build_custom_tab()
        self._build_help_tab()
        self._build_actions()
        self.select_game("quiz")

    # ------------------------------------------------------------ juego y contenido
    def _build_game_tab(self):
        tab = self.add_tab("tab_game", padding=8)
        left = self.lframe(tab, "games", padding=6)
        left.pack(side="left", fill="y", padx=(0, 8))
        self.game_list = ttk.Treeview(left, show="tree", selectmode="browse", height=12)
        self.game_list.column("#0", width=250)
        for key, spec in games.GAMES.items():
            self.game_list.insert("", "end", iid=key, text=spec["emoji"])
        self.game_list.pack(fill="y", expand=True)
        self.game_list.bind("<<TreeviewSelect>>", lambda e: self.select_game(self.game_list.selection()[0]))
        self.tr_call(self._label_games)
        self.game_desc = ttk.Label(left, wraplength=250, justify="left")
        self.game_desc.pack(fill="x", pady=(8, 0))
        self.game_formats = ttk.Label(left, style="Hint.TLabel", wraplength=250, justify="left")
        self.game_formats.pack(fill="x", pady=(4, 0))

        right = self.lframe(tab, "content", padding=6)
        right.pack(side="left", fill="both", expand=True)
        bar = ttk.Frame(right)
        bar.pack(fill="x")
        self.btn(bar, "add_row", lambda: self.table.add_row()).pack(side="left")
        self.btn(bar, "del_row", lambda: self.table.delete_selected()).pack(side="left", padx=4)
        self.btn(bar, "up", lambda: self.table.move(-1), width=3).pack(side="left")
        self.btn(bar, "down", lambda: self.table.move(1), width=3).pack(side="left", padx=4)
        self.btn(bar, "edit_row", self.edit_row).pack(side="left")
        self.btn(bar, "import", self.import_items).pack(side="right")
        self.btn(bar, "export_template", self.export_items).pack(side="right", padx=4)
        self.table = EditableTable(right, height=16)
        self.table.pack(fill="both", expand=True, pady=6)
        self.lbl(right, "content_hint", hint=True).pack(anchor="w")
        bar2 = ttk.Frame(right)
        bar2.pack(fill="x", pady=(6, 0))
        self.lbl(bar2, "pack").pack(side="left")
        self.pack_choice = Choice(self, bar2, ["fraud", "team"], ["pack_fraud", "pack_team"], width=24)
        self.pack_choice.pack(side="left", padx=6)
        self.btn(bar2, "load_pack", self.load_pack, accent=True).pack(side="left")
        self.btn(bar2, "ai_content", self.ai_dialog).pack(side="right")

    def _label_games(self):
        for key, spec in games.GAMES.items():
            self.game_list.item(key, text=f"{spec['emoji']}  {self.t('g_' + key)}")
        self._describe()
        if hasattr(self, "table") and self.table.keys:
            self.table.relabel([self.t("col_" + c) for c in self.table.keys])

    def _describe(self):
        if not hasattr(self, "game_desc"):
            return
        self.game_desc.configure(text=self.t("d_" + self.game))
        formats = ["HTML"] + (["PowerPoint"] if games.GAMES[self.game]["pptx"] else []) + ["Word"]
        self.game_formats.configure(text=self.t("exports", formats=", ".join(formats)))

    def select_game(self, game):
        if game not in games.GAMES or (game == self.game and self.table.keys == games.GAMES[game]["columns"]):
            return
        if hasattr(self, "table") and self.table.keys:
            self.items[self.game] = self.table.get_rows()
        if getattr(self, "option_vars", None):
            self.option_values[self.game] = self._options()
        self.game = game
        if self.game_list.selection() != (game,):
            self.game_list.selection_set(game)
        cols = games.GAMES[game]["columns"]
        self.table.set_columns(cols, [self.t("col_" + c) for c in cols], WIDTHS)
        self.table.set_rows(self.items.get(game, []))
        if not self.items.get(game):
            self.load_pack(confirm=False)
        self._describe()
        if hasattr(self, "options_box"):
            self._build_options()
            self._teams_state()
            self.icon_combo.set(games.GAMES[game]["emoji"])

    def load_pack(self, confirm=True):
        if confirm and self.table.get_rows() and not messagebox.askyesno(self.APP_NAME, self.t("replace_content"),
                                                                          parent=self):
            return
        lang = self.game_lang.key if hasattr(self, "game_lang") else self.t.lang
        pack = self.pack_choice.key
        rows = content.pack_items(pack, self.game, lang, games.GAMES[self.game]["columns"])
        self.table.set_rows(rows)
        self.items[self.game] = rows
        if hasattr(self, "title_entry"):
            title, subtitle = content.pack_titles(pack, lang)
            self._set_entry(self.title_entry, title)
            self._set_entry(self.subtitle_entry, subtitle)

    def edit_row(self):
        sel = self.table.tree.selection()
        if not sel:
            return
        iid = sel[0]
        win = tk.Toplevel(self)
        win.title(self.t("edit_row"))
        win.transient(self)
        frame = ttk.Frame(win, padding=16)
        frame.pack(fill="both", expand=True)
        frame.columnconfigure(1, weight=1)
        entries = {}
        for i, key in enumerate(self.table.keys):
            ttk.Label(frame, text=self.t("col_" + key)).grid(row=i, column=0, sticky="w", pady=3, padx=(0, 8))
            e = ttk.Entry(frame, width=80)
            e.insert(0, self.table.tree.set(iid, key))
            e.grid(row=i, column=1, sticky="ew", pady=3)
            entries[key] = e

        def save():
            for key, e in entries.items():
                self.table.tree.set(iid, key, e.get())
            win.destroy()

        ttk.Button(frame, text=self.t("save"), style="Accent.TButton", command=save).grid(
            row=len(entries), column=1, sticky="e", pady=(10, 0))
        win.grab_set()

    def _match_columns(self, df_cols):
        """Asocia las columnas del Excel con las del juego por nombre (en cualquier idioma) o por posición."""
        keys = games.GAMES[self.game]["columns"]
        norm = lambda s: re.sub(r"[^a-z0-9ñ]", "", games.strip_accents(str(s).lower(), keep_enye=True))  # noqa: E731
        names = {}
        for key in keys:
            names[norm(key)] = key
            for label in self.t.table["col_" + key]:
                names[norm(label)] = key
                names[norm(re.sub(r"\(.*\)", "", label))] = key
        mapping = {c: names[norm(c)] for c in df_cols if norm(c) in names}
        if not mapping:
            mapping = {c: k for c, k in zip(df_cols, keys)}
        return mapping

    def import_items(self):
        path = self.ask_open(["excel", "csv"])
        if not path:
            return
        sheet = self.ask_sheet(list_sheets(path))

        def done(df):
            mapping = self._match_columns(list(df.columns))
            rows = []
            for rec in df.to_dict("records"):
                row = {}
                for col, key in mapping.items():
                    value = rec.get(col)
                    if value is None or (isinstance(value, float) and pd.isna(value)):
                        value = ""
                    elif isinstance(value, float) and value.is_integer():
                        value = int(value)
                    row[key] = str(value).strip()
                if any(row.values()):
                    rows.append(row)
            self.table.set_rows(rows)
            self.status(self.t("imported", n=len(rows)))

        self.run_task(lambda: read_table(path, sheet), done)

    def export_items(self):
        path = self.ask_save("excel", f"IcePilot_{self.game}.xlsx")
        if not path:
            return
        from openpyxl import Workbook

        keys = games.GAMES[self.game]["columns"]
        df = pd.DataFrame(self.table.get_rows(), columns=keys)
        df.columns = [self.t("col_" + k) for k in keys]
        wb = Workbook()
        wb.active.title = self.t("g_" + self.game)[:31]
        write_df(wb.active, df, accent="6D28D9")
        wb.save(path)
        self.saved(path)

    def ai_dialog(self):
        win = tk.Toplevel(self)
        win.title(self.t("ai_content"))
        win.transient(self)
        frame = ttk.Frame(win, padding=16)
        frame.pack(fill="both", expand=True)
        ttk.Label(frame, text=self.t("ai_topic")).pack(anchor="w")
        topic = ttk.Entry(frame, width=60)
        topic.pack(fill="x", pady=4)
        row = ttk.Frame(frame)
        row.pack(fill="x")
        ttk.Label(row, text=self.t("ai_count")).pack(side="left")
        count = ttk.Spinbox(row, from_=3, to=40, width=6)
        count.set(10)
        count.pack(side="left", padx=6)
        ttk.Label(frame, text=self.t("ai_note"), style="Hint.TLabel", wraplength=460, justify="left").pack(anchor="w",
                                                                                                          pady=8)

        def go():
            subject = topic.get().strip()
            if not self.need(subject, "need_text"):
                return
            try:
                n = int(count.get())
            except ValueError:
                n = 10
            win.destroy()
            self.ai_generate(subject, n)

        ttk.Button(frame, text=self.t("generate"), style="Accent.TButton", command=go).pack(anchor="e")
        topic.focus_set()

    def ai_generate(self, subject, n):
        keys = games.GAMES[self.game]["columns"]
        lang = self.game_lang.key
        fields = "; ".join(f"{k} = {self.t.table['col_' + k][1]}" for k in keys)
        if self.game == "quiz":
            fields += "; correct = letter A-D of the right option"
        elif self.game == "truefalse":
            fields += "; answer = T or F"
        elif self.game == "truths":
            fields += "; lie = 1, 2 or 3"
        schema = obj({"items": {"type": "array", "items": obj({k: STR for k in keys})}})
        prompt = f"Game type: {self.t.table['g_' + self.game][1]}\nTopic: {subject}\nNumber of items: {n}"

        def work(ai):
            ai.lang = lang
            return ai.ask_json(AI_SYSTEM.format(fields=fields), prompt, schema, max_tokens=16000)["items"]

        self.run_ai(work, lambda rows: self.table.set_rows(rows))

    # ------------------------------------------------------------ personalizar
    def _build_custom_tab(self):
        tab = self.add_tab("tab_custom")
        left = self.lframe(tab, "look")
        left.pack(side="left", fill="y", padx=(0, 10))
        left.columnconfigure(1, weight=1)
        self.title_entry = self.field(left, "title", ttk.Entry(left, width=36), 0)
        self.subtitle_entry = self.field(left, "subtitle", ttk.Entry(left, width=36), 1)
        self.icon_combo = self.field(left, "emoji", ttk.Combobox(left, values=ICONS, width=8,
                                                                 font=("Segoe UI Emoji", 12)), 2, sticky="w")
        self.icon_combo.set("🏆")
        self.theme_choice = self.field(left, "theme", Choice(self, left, list(games.THEMES),
                                                             [f"th_{k}" for k in games.THEMES]), 3)
        self.theme_choice.bind("<<ComboboxSelected>>", lambda e: self._paint_swatches(), add="+")
        colors = ttk.Frame(left)
        colors.grid(row=4, column=0, columnspan=2, sticky="w", pady=4)
        self.swatches = {}
        for key in ("primary", "accent"):
            self.btn(colors, key, lambda k=key: self.pick_color(k)).pack(side="left", padx=(0, 4))
            sw = tk.Label(colors, width=3, relief="flat")
            sw.pack(side="left", padx=(0, 10))
            self.swatches[key] = sw
        self.btn(colors, "reset_colors", self.reset_colors).pack(side="left")
        self.game_lang = self.field(left, "game_lang", Choice(self, left, LANG_KEYS, [f"lang_{k}" for k in LANG_KEYS],
                                                              default=LANG_KEYS.index(self.t.lang)), 5)
        self.game_lang.bind("<<ComboboxSelected>>", lambda e: self._lang_changed(manual=True), add="+")
        self._game_lang_manual = False
        self.tr_call(self._follow_ui_lang)
        self.sound_var = tk.BooleanVar(value=True)
        self.chk(left, "sound", self.sound_var).grid(row=6, column=0, columnspan=2, sticky="w", pady=4)
        self.teams_label = self.lbl(left, "teams")
        self.teams_label.grid(row=7, column=0, columnspan=2, sticky="w", pady=(10, 2))
        self.teams_box = TextBox(left, height=6, width=36)
        self.teams_box.grid(row=8, column=0, columnspan=2, sticky="ew")
        self.teams_box.set("\n".join(games.DEFAULT_TEAMS[self.t.lang][:2]))
        self.teams_note = self.lbl(left, "teams_off", hint=True)

        self.options_box = self.lframe(tab, "game_options")
        self.options_box.pack(side="left", fill="both", expand=True)
        self.option_vars = {}
        self.option_values = {}
        self._paint_swatches()
        self._build_options()
        self._teams_state()

    def _build_options(self):
        box = self.options_box
        for child in box.winfo_children():
            child.destroy()
        previous = self.option_values.get(self.game, {})
        self.option_vars = {}
        specs = games.GAMES[self.game]["options"]
        if not specs:
            self.lbl(box, "no_options", hint=True).grid(row=0, column=0, sticky="w")
        for i, (key, kind, default, extra) in enumerate(specs):
            if kind == "bool":
                var = tk.BooleanVar(value=previous.get(key, default))
                self.chk(box, f"opt_{key}", var).grid(row=i, column=0, columnspan=2, sticky="w", pady=3)
            elif kind == "int":
                var = tk.StringVar(value=str(previous.get(key, default)))
                self.lbl(box, f"opt_{key}").grid(row=i, column=0, sticky="w", pady=3, padx=(0, 8))
                ttk.Spinbox(box, from_=extra[0], to=extra[1], textvariable=var, width=8).grid(row=i, column=1, sticky="w")
            else:
                self.lbl(box, f"opt_{key}").grid(row=i, column=0, sticky="w", pady=3, padx=(0, 8))
                translated = key in ("mode", "win")
                labels = [f"{key}_{c}" for c in extra] if translated else list(extra)
                current = previous.get(key, default)
                choice = Choice(self, box, list(extra), labels, width=30,
                                default=list(extra).index(current if current in extra else default),
                                translate=translated)
                choice.grid(row=i, column=1, sticky="w")
                var = choice
            self.option_vars[key] = var
        row = len(specs) + 1
        if games.GAMES[self.game]["engine"] in ("snakes", "bingo", "wordsearch", "guess"):
            ttk.Separator(box).grid(row=row, column=0, columnspan=2, sticky="ew", pady=10)
            self.lbl(box, "seed").grid(row=row + 1, column=0, sticky="w")
            self.seed_label = ttk.Label(box, text=str(self.seed))
            self.seed_label.grid(row=row + 1, column=1, sticky="w")
            self.btn(box, "reshuffle", self.reshuffle).grid(row=row + 2, column=0, columnspan=2, sticky="w", pady=4)

    def reshuffle(self):
        import random

        self.seed = random.randint(1, 999_999)
        self.seed_label.configure(text=str(self.seed))

    def _options(self):
        out = {}
        for key, kind, default, extra in games.GAMES[self.game]["options"]:
            var = self.option_vars.get(key)
            if var is None:
                out[key] = default
            elif kind == "bool":
                out[key] = bool(var.get())
            elif kind == "int":
                try:
                    out[key] = max(extra[0], min(extra[1], int(var.get())))
                except ValueError:
                    out[key] = default
            else:
                out[key] = var.key
        return out

    def _teams_state(self):
        uses = games.GAMES[self.game]["teams"]
        if uses:
            self.teams_note.grid_forget()
            self.teams_box.text.configure(state="normal")
        else:
            self.teams_note.grid(row=9, column=0, columnspan=2, sticky="w")
            self.teams_box.text.configure(state="disabled")

    def _follow_ui_lang(self):
        """Mientras no se elija otro, el juego usa el idioma de la interfaz (y el ejemplo se traduce)."""
        if self._game_lang_manual or self.game_lang.key == self.t.lang:
            return
        old = self.game_lang.key
        untouched = self.table.get_rows() == content.pack_items(self.pack_choice.key, self.game, old,
                                                                games.GAMES[self.game]["columns"])
        self.game_lang.set_key(self.t.lang)
        self._lang_changed()
        if untouched:
            self.items = {}
            self.load_pack(confirm=False)

    def _lang_changed(self, manual=False):
        self._game_lang_manual = self._game_lang_manual or manual
        lang = self.game_lang.key
        current = [t.strip() for t in self.teams_box.get().splitlines() if t.strip()]
        if all(t in sum(games.DEFAULT_TEAMS.values(), []) for t in current):
            self.teams_box.set("\n".join(games.DEFAULT_TEAMS[lang][:max(2, len(current))]))

    def pick_color(self, key):
        start = self.colors[key] or games.THEMES[self.theme_choice.key][key]
        color = colorchooser.askcolor(start, parent=self)[1]
        if color:
            self.colors[key] = color.upper()
            self._paint_swatches()

    def reset_colors(self):
        self.colors = {"primary": "", "accent": ""}
        self._paint_swatches()

    def _paint_swatches(self):
        theme = games.THEMES[self.theme_choice.key]
        for key, sw in self.swatches.items():
            sw.configure(bg=self.colors[key] or theme[key])

    @staticmethod
    def _set_entry(entry, value):
        entry.delete(0, "end")
        entry.insert(0, value)

    # ------------------------------------------------------------ ayuda
    def _build_help_tab(self):
        tab = self.add_tab("tab_help")
        self.tr(ttk.Label(tab, style="Title.TLabel"), "help_title").pack(anchor="w", pady=(0, 8))
        text = TextBox(tab, height=24, readonly=True)
        text.pack(fill="both", expand=True)
        self.tr_call(lambda: text.set(self.t("help_text")))

    # ------------------------------------------------------------ acciones
    def _build_actions(self):
        bar = ttk.Frame(self, padding=(10, 4))
        bar.pack(side="bottom", fill="x", before=self.nb)
        self.btn(bar, "preview", self.preview, accent=True).pack(side="left")
        self.btn(bar, "save_html", lambda: self.export("html")).pack(side="left", padx=6)
        self.btn(bar, "save_pptx", lambda: self.export("pptx")).pack(side="left")
        self.btn(bar, "save_docx", lambda: self.export("docx")).pack(side="left", padx=6)
        self.btn(bar, "save_project", self.save_project).pack(side="right")
        self.btn(bar, "open_project", self.open_project).pack(side="right", padx=6)

    def config(self):
        self.items[self.game] = self.table.get_rows()
        teams = [t.strip() for t in self.teams_box.get().splitlines() if t.strip()][:8]
        return {
            "type": self.game, "lang": self.game_lang.key,
            "title": self.title_entry.get().strip() or self.t.table["g_" + self.game][LANG_KEYS.index(self.game_lang.key)],
            "subtitle": self.subtitle_entry.get().strip(), "emoji": self.icon_combo.get().strip() or "🎮",
            "theme": self.theme_choice.key, "primary": self.colors["primary"], "accent": self.colors["accent"],
            "teams": teams if games.GAMES[self.game]["teams"] else [], "sound": bool(self.sound_var.get()),
            "seed": self.seed, "options": self._options(), "items": self.items[self.game],
        }

    def _check(self, cfg):
        _, warnings = games.prepare(cfg)
        if cfg["type"] == "snakes" and len(cfg["teams"]) < 2:
            warnings.append(("w_teams", {}))
        if not warnings:
            return True
        text = "\n".join("• " + self.t(k, **p) for k, p in warnings)
        blocking = any(k == "w_empty" for k, _ in warnings)
        if blocking:
            messagebox.showwarning(self.t("warnings_title"), text, parent=self)
            return False
        return messagebox.askyesno(self.t("warnings_title"), text + "\n\n" + self.t("continue_anyway"), parent=self)

    def _file_name(self, cfg, ext):
        base = re.sub(r'[<>:"/\\|?*]+', "_", cfg["title"]).strip() or "IcePilot"
        return f"{base}{ext}"

    def preview(self):
        cfg = self.config()
        if not self._check(cfg):
            return
        page, _ = build_html(cfg)
        folder = Path(tempfile.gettempdir()) / "IcePilot"
        folder.mkdir(exist_ok=True)
        path = folder / f"preview_{cfg['type']}.html"
        path.write_text(page, encoding="utf-8")
        open_path(path)

    def export(self, kind):
        cfg = self.config()
        if kind == "pptx" and not games.GAMES[cfg["type"]]["pptx"]:
            self.info(self.t("no_pptx"))
            return
        if not self._check(cfg):
            return
        names = {"html": ("html", ".html"), "pptx": ("pptx", ".pptx"), "docx": ("word", ".docx")}
        filetype, ext = names[kind]
        path = self.ask_save(filetype, self._file_name(cfg, ext))
        if not path:
            return

        def work():
            if kind == "html":
                page, _ = build_html(cfg)
                Path(path).write_text(page, encoding="utf-8")
            elif kind == "pptx":
                office.build_pptx(cfg, path)
            else:
                office.build_docx(cfg, path)
            return path

        self.run_task(work, self.saved)

    def save_project(self):
        cfg = self.config()
        path = self.ask_save("json", self._file_name(cfg, ".icepilot.json"))
        if path:
            Path(path).write_text(json.dumps({"icepilot": 1, **cfg}, ensure_ascii=False, indent=2), encoding="utf-8")
            self.saved(path)

    def open_project(self):
        path = self.ask_open(["json"])
        if not path:
            return
        try:
            cfg = json.loads(Path(path).read_text(encoding="utf-8"))
            if not isinstance(cfg, dict) or cfg.get("type") not in games.GAMES:
                raise ValueError
        except (OSError, ValueError):
            self.info(self.t("bad_project"))
            return
        self.items[cfg["type"]] = cfg.get("items", [])
        self.select_game(cfg["type"])
        self.table.set_rows(cfg.get("items", []))
        self._set_entry(self.title_entry, cfg.get("title", ""))
        self._set_entry(self.subtitle_entry, cfg.get("subtitle", ""))
        self.icon_combo.set(cfg.get("emoji", "🎮"))
        self.theme_choice.set_key(cfg.get("theme", "bank"))
        self.colors = {"primary": cfg.get("primary", ""), "accent": cfg.get("accent", "")}
        self._paint_swatches()
        self.game_lang.set_key(cfg.get("lang", self.t.lang))
        self.sound_var.set(bool(cfg.get("sound", True)))
        self.teams_box.set("\n".join(cfg.get("teams", [])))
        self.seed = int(cfg.get("seed", self.seed))
        self.option_values[cfg["type"]] = dict(cfg.get("options") or {})
        self._build_options()
        self.status(self.t("project_loaded"))


def main():
    IcePilot().mainloop()


if __name__ == "__main__":
    main()
