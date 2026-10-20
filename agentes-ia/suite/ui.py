"""Ventana base y widgets comunes de las apps (Tkinter + tema Sun Valley)."""

import os
import subprocess
import sys
import threading
import traceback
import tkinter as tk
from tkinter import filedialog, messagebox, ttk

import pandas as pd

try:
    import sv_ttk
except ImportError:
    sv_ttk = None

from . import __version__
from .ai import EFFORTS, MODELS, AIClient, AIError
from .i18n import COMMON, LANG_NAMES, LANGS, Translator, detect_lang
from .icons import make_icon
from .privacy import Anonymizer
from .settings import Settings

FILETYPES = {
    "excel": ("ft_excel", "*.xlsx *.xlsm *.xls"),
    "csv": ("ft_csv", "*.csv *.txt *.tsv"),
    "word": ("ft_word", "*.docx"),
    "pptx": ("ft_pptx", "*.pptx"),
    "text": ("ft_text", "*.txt *.md"),
    "json": ("ft_json", "*.json"),
}
EXTENSIONS = {"excel": ".xlsx", "csv": ".csv", "word": ".docx", "pptx": ".pptx", "text": ".txt", "json": ".json"}


def open_path(path):
    try:
        if sys.platform == "win32":
            os.startfile(path)  # noqa: S606 - abre el archivo con su programa (Excel, Word…)
        elif sys.platform == "darwin":
            subprocess.Popen(["open", str(path)])
        else:
            subprocess.Popen(["xdg-open", str(path)])
    except OSError:
        pass


class PilotApp(tk.Tk):
    """Ventana con cabecera (nombre, idioma, ajustes de IA), pestañas y barra de estado."""

    APP_NAME = "Pilot"
    ICON_TEXT = "P"
    ACCENT = "#2B579A"
    STRINGS = {}

    def __init__(self):
        super().__init__()
        self.settings = Settings.load()
        self.t = Translator(COMMON, self.STRINGS, lang=self.settings.get("lang") or detect_lang())
        self._i18n = []
        self._busy = 0
        self.withdraw()
        self._setup_theme()
        self.title(self.APP_NAME)
        self.geometry("1200x800")
        self.minsize(1000, 660)
        self._icon = None
        try:
            from PIL import ImageTk

            self._icon = ImageTk.PhotoImage(make_icon(self.ICON_TEXT, self.ACCENT, 64))
            self.iconphoto(True, self._icon)
        except Exception:  # el icono es decorativo
            pass
        self._build_chrome()
        self.build()
        self.tr_call(lambda: self.title(f"{self.APP_NAME} · {self.t('tagline')}"))
        self.update_ai_status()
        self.deiconify()

    # ---------- tema ----------
    def _setup_theme(self):
        if sv_ttk is not None:
            sv_ttk.set_theme("light")
        else:
            style = ttk.Style(self)
            style.theme_use("clam")
            style.configure("Accent.TButton", foreground="white", background=self.ACCENT)
        style = ttk.Style(self)
        style.configure("Treeview", rowheight=26)
        style.configure("Hint.TLabel", foreground="#5f6b7a")
        style.configure("Title.TLabel", font=("Segoe UI", 13, "bold"))
        style.configure("Big.TLabel", font=("Segoe UI", 22, "bold"))
        self.option_add("*TCombobox*Listbox.font", ("Segoe UI", 10))

    # ---------- estructura ----------
    def _build_chrome(self):
        header = tk.Frame(self, bg=self.ACCENT, height=64)
        header.pack(fill="x")
        left = tk.Frame(header, bg=self.ACCENT)
        left.pack(side="left", padx=18, pady=8)
        tk.Label(left, text=self.APP_NAME, bg=self.ACCENT, fg="white", font=("Segoe UI", 18, "bold")).pack(anchor="w")
        tagline = tk.Label(left, bg=self.ACCENT, fg="#eef2f7", font=("Segoe UI", 10))
        tagline.pack(anchor="w")
        self.tr(tagline, "tagline")

        right = tk.Frame(header, bg=self.ACCENT)
        right.pack(side="right", padx=18)
        self.lang_label = tk.Label(right, bg=self.ACCENT, fg="white", font=("Segoe UI", 10))
        self.lang_label.pack(side="left", padx=(0, 6))
        self.tr(self.lang_label, "language")
        self.lang_combo = ttk.Combobox(right, state="readonly", width=10, values=[LANG_NAMES[l] for l in LANGS])
        self.lang_combo.current(LANGS.index(self.t.lang))
        self.lang_combo.bind("<<ComboboxSelected>>", lambda e: self.set_lang(LANGS[self.lang_combo.current()]))
        self.lang_combo.pack(side="left", padx=(0, 12))
        self.btn(right, "settings", self.open_settings).pack(side="left")

        status = ttk.Frame(self, padding=(12, 4))
        status.pack(side="bottom", fill="x")
        ttk.Separator(self).pack(side="bottom", fill="x")
        self.status_var = tk.StringVar(value=self.t("ready"))
        ttk.Label(status, textvariable=self.status_var).pack(side="left")
        self.progress = ttk.Progressbar(status, mode="indeterminate", length=160)
        self.ai_label = ttk.Label(status, style="Hint.TLabel")
        self.ai_label.pack(side="right")
        ttk.Label(status, text=f"v{__version__}  ", style="Hint.TLabel").pack(side="right")

        self.nb = ttk.Notebook(self)
        self.nb.pack(fill="both", expand=True, padx=10, pady=(8, 4))

    def build(self):
        """Las subclases crean aquí sus pestañas con `add_tab`."""

    def add_tab(self, key, padding=12):
        frame = ttk.Frame(self.nb, padding=padding)
        self.nb.add(frame, text=key)
        self.tr_call(lambda: self.nb.tab(frame, text=self.t(key)))
        return frame

    # ---------- idioma ----------
    def tr(self, widget, key, option="text", **kw):
        def apply():
            widget.configure(**{option: self.t(key, **kw)})

        self._i18n.append(apply)
        apply()
        return widget

    def tr_call(self, fn):
        self._i18n.append(fn)
        fn()
        return fn

    def set_lang(self, lang):
        self.t.lang = lang
        self.lang_combo.current(LANGS.index(lang))
        self.settings["lang"] = lang
        self.settings.save()
        for fn in list(self._i18n):
            try:
                fn()
            except tk.TclError:  # widget destruido
                self._i18n.remove(fn)
        self.update_ai_status()
        self.status(self.t("ready"))

    # ---------- atajos de widgets ----------
    def btn(self, parent, key, command, accent=False, **kw):
        b = ttk.Button(parent, command=command, style="Accent.TButton" if accent else "TButton", **kw)
        return self.tr(b, key)

    def lbl(self, parent, key, hint=False, **kw):
        lab = ttk.Label(parent, style="Hint.TLabel" if hint else "TLabel", **kw)
        return self.tr(lab, key)

    def lframe(self, parent, key, padding=10):
        return self.tr(ttk.LabelFrame(parent, padding=padding), key)

    def chk(self, parent, key, var):
        return self.tr(ttk.Checkbutton(parent, variable=var), key)

    def field(self, parent, key, widget, row, col=0, sticky="ew", pady=3):
        """Etiqueta + control en una rejilla de dos columnas."""
        self.lbl(parent, key).grid(row=row, column=col, sticky="w", padx=(0, 8), pady=pady)
        widget.grid(row=row, column=col + 1, sticky=sticky, pady=pady)
        return widget

    # ---------- estado y tareas en segundo plano ----------
    def status(self, text):
        self.status_var.set(text)

    def update_ai_status(self):
        if self.settings.api_key:
            self.ai_label.configure(text=self.t("ai_on", model=self.settings.get("model")))
        else:
            self.ai_label.configure(text=self.t("ai_off"))

    def _set_busy(self, busy, text=None):
        self._busy += 1 if busy else -1
        if self._busy > 0:
            self.status(text or self.t("working"))
            if not self.progress.winfo_ismapped():
                self.progress.pack(side="left", padx=12)
                self.progress.start(12)
            self.configure(cursor="watch")
        else:
            self._busy = 0
            self.progress.stop()
            self.progress.pack_forget()
            self.configure(cursor="")
            self.status(self.t("ready"))

    def run_task(self, work, on_done=None, status_key="working"):
        """Ejecuta `work()` en otro hilo y llama a `on_done(resultado)` en el hilo de la interfaz."""
        self._set_busy(True, self.t(status_key))
        result = {}

        def target():
            try:
                result["value"] = work()
            except Exception as exc:  # se muestra al usuario
                result["error"] = exc
                result["trace"] = traceback.format_exc()

        thread = threading.Thread(target=target, daemon=True)
        thread.start()

        def poll():
            if thread.is_alive():
                self.after(80, poll)
                return
            self._set_busy(False)
            if "error" in result:
                self.show_error(result["error"], result.get("trace"))
            elif on_done:
                try:
                    on_done(result.get("value"))
                except Exception as exc:
                    self.show_error(exc, traceback.format_exc())

        self.after(80, poll)

    def run_ai(self, work, on_done):
        """Como run_task, pero `work(ai)` recibe el cliente de IA (o pide configurarlo)."""
        ai = self.get_ai()
        if ai is None:
            return
        self.run_task(lambda: work(ai), on_done, status_key="ai_working")

    def get_ai(self):
        try:
            return AIClient.from_settings(self.settings, self.t.lang)
        except AIError as exc:
            if exc.code == "no_key":
                if messagebox.askyesno(self.t("notice"), self.t("err_no_key"), parent=self):
                    self.open_settings()
            else:
                self.show_error(exc)
            return None

    def anonymizer(self):
        return Anonymizer() if self.settings.get("anonymize", True) else None

    def show_error(self, exc, trace=None):
        if isinstance(exc, AIError):
            message = self.t(f"err_{exc.code}", detail=exc.detail) if f"err_{exc.code}" in self.t.table else str(exc)
        else:
            message = f"{type(exc).__name__}: {exc}"
            if trace:
                sys.stderr.write(trace)
        messagebox.showerror(self.t("error"), message, parent=self)

    def info(self, text):
        messagebox.showinfo(self.APP_NAME, text, parent=self)

    def need(self, condition, key="no_data"):
        if not condition:
            messagebox.showwarning(self.APP_NAME, self.t(key), parent=self)
        return bool(condition)

    # ---------- archivos ----------
    def _filetypes(self, kinds):
        types = [(self.t(FILETYPES[k][0]), FILETYPES[k][1]) for k in kinds]
        return types + [(self.t("ft_all"), "*.*")]

    def ask_open(self, kinds, multiple=False):
        if multiple:
            return list(filedialog.askopenfilenames(parent=self, filetypes=self._filetypes(kinds)))
        return filedialog.askopenfilename(parent=self, filetypes=self._filetypes(kinds)) or None

    def ask_save(self, kind, name):
        return filedialog.asksaveasfilename(
            parent=self, filetypes=self._filetypes([kind]), defaultextension=EXTENSIONS[kind], initialfile=name
        ) or None

    def saved(self, path):
        self.status(self.t("saved_to", path=path).replace("\n", " "))
        if messagebox.askyesno(self.APP_NAME, self.t("saved_to", path=path) + "\n\n" + self.t("open_now"), parent=self):
            open_path(path)

    def ask_sheet(self, sheets):
        """Pequeño diálogo para elegir la hoja de un libro con varias."""
        if len(sheets) <= 1:
            return sheets[0] if sheets else None
        win = tk.Toplevel(self)
        win.title(self.t("choose_sheet"))
        win.transient(self)
        win.resizable(False, False)
        frame = ttk.Frame(win, padding=16)
        frame.pack(fill="both")
        ttk.Label(frame, text=self.t("choose_sheet")).pack(anchor="w")
        combo = ttk.Combobox(frame, state="readonly", values=sheets, width=34)
        combo.current(0)
        combo.pack(fill="x", pady=8)
        chosen = {}

        def accept():
            chosen["sheet"] = combo.get()
            win.destroy()

        ttk.Button(frame, text=self.t("ok"), style="Accent.TButton", command=accept).pack(anchor="e")
        win.grab_set()
        self.wait_window(win)
        return chosen.get("sheet")

    def copy(self, text):
        self.clipboard_clear()
        self.clipboard_append(text)
        self.status(self.t("copied"))

    # ---------- ajustes de IA ----------
    def open_settings(self):
        SettingsDialog(self)


class SettingsDialog(tk.Toplevel):
    def __init__(self, app):
        super().__init__(app)
        self.app = app
        t = app.t
        self.title(t("settings_title"))
        self.transient(app)
        self.resizable(False, False)
        frame = ttk.Frame(self, padding=18)
        frame.pack(fill="both", expand=True)
        frame.columnconfigure(1, weight=1)

        ttk.Label(frame, text=t("api_key")).grid(row=0, column=0, sticky="w", pady=4)
        self.key_var = tk.StringVar(value=app.settings.get("api_key", ""))
        self.key_entry = ttk.Entry(frame, textvariable=self.key_var, show="•", width=52)
        self.key_entry.grid(row=0, column=1, sticky="ew", pady=4)
        self.show_var = tk.BooleanVar(value=False)
        ttk.Checkbutton(
            frame, text=t("show_key"), variable=self.show_var,
            command=lambda: self.key_entry.configure(show="" if self.show_var.get() else "•"),
        ).grid(row=0, column=2, padx=(8, 0))

        ttk.Label(frame, text=t("model")).grid(row=1, column=0, sticky="w", pady=4)
        self.model = ttk.Combobox(frame, state="readonly", values=MODELS)
        current = app.settings.get("model")
        self.model.current(MODELS.index(current) if current in MODELS else 0)
        self.model.grid(row=1, column=1, sticky="ew", pady=4)

        ttk.Label(frame, text=t("effort")).grid(row=2, column=0, sticky="w", pady=4)
        self.effort = ttk.Combobox(frame, state="readonly", values=[t(f"effort_{e}") for e in EFFORTS])
        effort = app.settings.get("effort")
        self.effort.current(EFFORTS.index(effort) if effort in EFFORTS else 1)
        self.effort.grid(row=2, column=1, sticky="ew", pady=4)

        self.anon_var = tk.BooleanVar(value=bool(app.settings.get("anonymize", True)))
        ttk.Checkbutton(frame, text=t("anonymize"), variable=self.anon_var).grid(
            row=3, column=0, columnspan=3, sticky="w", pady=(8, 4)
        )
        ttk.Label(frame, text=t("settings_hint"), style="Hint.TLabel", justify="left").grid(
            row=4, column=0, columnspan=3, sticky="w", pady=(4, 12)
        )

        buttons = ttk.Frame(frame)
        buttons.grid(row=5, column=0, columnspan=3, sticky="ew")
        ttk.Button(buttons, text=t("test_connection"), command=self.test).pack(side="left")
        ttk.Button(buttons, text=t("save"), style="Accent.TButton", command=self.save).pack(side="right")
        ttk.Button(buttons, text=t("cancel"), command=self.destroy).pack(side="right", padx=8)
        self.grab_set()
        self.key_entry.focus_set()

    def _apply(self):
        s = self.app.settings
        s["api_key"] = self.key_var.get().strip()
        s["model"] = self.model.get()
        s["effort"] = EFFORTS[self.effort.current()]
        s["anonymize"] = bool(self.anon_var.get())

    def save(self):
        self._apply()
        self.app.settings.save()
        self.app.update_ai_status()
        self.destroy()

    def test(self):
        self._apply()

        def done(_):
            messagebox.showinfo(self.app.APP_NAME, self.app.t("connection_ok"), parent=self)

        self.app.run_ai(lambda ai: ai.ping(), done)


class Choice(ttk.Combobox):
    """Combobox de solo lectura cuyas opciones son claves traducibles."""

    def __init__(self, app, parent, keys, labels=None, width=24, default=0):
        super().__init__(parent, state="readonly", width=width)
        self.app = app
        self.keys = list(keys)
        self.labels = list(labels or keys)
        self._index = default
        self.bind("<<ComboboxSelected>>", lambda e: setattr(self, "_index", self.current()))
        app.tr_call(self._refresh)

    def _refresh(self):
        self["values"] = [self.app.t(k) for k in self.labels]
        if self.keys:
            self.current(min(self._index, len(self.keys) - 1))

    @property
    def key(self):
        return self.keys[self.current()] if self.keys and self.current() >= 0 else None

    def set_key(self, key):
        if key in self.keys:
            self._index = self.keys.index(key)
            self.current(self._index)


class DataTable(ttk.Frame):
    """Vista de un DataFrame (primeras filas) con barras de desplazamiento."""

    def __init__(self, parent, app=None, max_rows=500, height=12):
        super().__init__(parent)
        self.app = app
        self.max_rows = max_rows
        self.tree = ttk.Treeview(self, show="headings", height=height)
        ys = ttk.Scrollbar(self, orient="vertical", command=self.tree.yview)
        xs = ttk.Scrollbar(self, orient="horizontal", command=self.tree.xview)
        self.tree.configure(yscrollcommand=ys.set, xscrollcommand=xs.set)
        self.tree.grid(row=0, column=0, sticky="nsew")
        ys.grid(row=0, column=1, sticky="ns")
        xs.grid(row=1, column=0, sticky="ew")
        self.footer = ttk.Label(self, style="Hint.TLabel")
        self.footer.grid(row=2, column=0, sticky="w", pady=(2, 0))
        self.rowconfigure(0, weight=1)
        self.columnconfigure(0, weight=1)

    def show(self, df, row_colors=None):
        """row_colors: lista opcional con un color de fondo (o None) por fila."""
        self.tree.delete(*self.tree.get_children())
        if df is None:
            self.tree["columns"] = ()
            self.footer.configure(text="")
            return
        cols = [str(c) for c in df.columns]
        rows = [[fmt(v) for v in row] for row in df.head(self.max_rows).itertuples(index=False)]
        self.tree["columns"] = cols
        for j, c in enumerate(cols):
            longest = max([len(c)] + [len(r[j]) for r in rows[:60]])
            self.tree.heading(c, text=c)
            self.tree.column(c, width=max(70, min(320, 8 * longest + 24)), stretch=False)
        for i, row in enumerate(rows):
            color = row_colors[i] if row_colors and i < len(row_colors) else None
            tags = ()
            if color:
                tags = (f"c{color}",)
                self.tree.tag_configure(tags[0], background=color)
            self.tree.insert("", "end", iid=str(i), values=row, tags=tags)
        if self.app is not None:
            self.footer.configure(text=self.app.t("rows_shown", shown=min(len(df), self.max_rows), total=len(df)))


    def selected_index(self):
        sel = self.tree.selection()
        return int(sel[0]) if sel else None


def fmt(value):
    if value is None:
        return ""
    try:
        if pd.isna(value):
            return ""
    except (TypeError, ValueError):
        pass
    if isinstance(value, float):
        return f"{value:,.2f}"
    if isinstance(value, pd.Timestamp):
        return value.strftime("%Y-%m-%d") if value == value.normalize() else value.strftime("%Y-%m-%d %H:%M")
    return str(value)


class TextBox(ttk.Frame):
    def __init__(self, parent, height=10, readonly=False, font=("Segoe UI", 10), wrap="word", width=60):
        super().__init__(parent)
        self.text = tk.Text(self, height=height, width=width, wrap=wrap, font=font, relief="flat",
                            borderwidth=1, highlightthickness=1, highlightcolor="#7aa7e0",
                            highlightbackground="#d7dde5", padx=8, pady=6, undo=True)
        bar = ttk.Scrollbar(self, orient="vertical", command=self.text.yview)
        self.text.configure(yscrollcommand=bar.set)
        bar.pack(side="right", fill="y")
        self.text.pack(side="left", fill="both", expand=True)
        self.readonly = readonly
        if readonly:
            self.text.configure(state="disabled", background="#fbfcfd")

    def get(self):
        return self.text.get("1.0", "end").strip()

    def set(self, value):
        self.text.configure(state="normal")
        self.text.delete("1.0", "end")
        self.text.insert("1.0", value or "")
        if self.readonly:
            self.text.configure(state="disabled")


class ScrollFrame(ttk.Frame):
    """Marco con desplazamiento vertical para formularios largos."""

    def __init__(self, parent):
        super().__init__(parent)
        self.canvas = tk.Canvas(self, highlightthickness=0, borderwidth=0)
        bar = ttk.Scrollbar(self, orient="vertical", command=self.canvas.yview)
        self.inner = ttk.Frame(self.canvas)
        self.inner.bind("<Configure>", lambda e: self.canvas.configure(scrollregion=self.canvas.bbox("all")))
        self._win = self.canvas.create_window((0, 0), window=self.inner, anchor="nw")
        self.canvas.bind("<Configure>", lambda e: self.canvas.itemconfigure(self._win, width=e.width))
        self.canvas.configure(yscrollcommand=bar.set)
        self.canvas.pack(side="left", fill="both", expand=True)
        bar.pack(side="right", fill="y")
        self.canvas.bind("<Enter>", lambda e: self.canvas.bind_all("<MouseWheel>", self._wheel))
        self.canvas.bind("<Leave>", lambda e: self.canvas.unbind_all("<MouseWheel>"))
        try:
            self.canvas.configure(background=ttk.Style().lookup("TFrame", "background"))
        except tk.TclError:
            pass

    def _wheel(self, event):
        self.canvas.yview_scroll(int(-event.delta / 120) or (-1 if event.delta > 0 else 1), "units")
