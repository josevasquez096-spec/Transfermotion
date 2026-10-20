"""Controles de MailPilot: lista de correos, vista previa y diálogos para elegir carpeta o etiquetas."""

import tkinter as tk
from tkinter import font as tkfont
from tkinter import ttk

from ..ui import TextBox
from .model import CATEGORY_HEX, PICKER_COLORS

STATE_SYMBOLS = (("unread", "●"), ("flagged", "⚑"), ("has_attachments", "⎘"))


def tk_index(text, offset):
    """Índice de Tk para una posición de una cadena de Python: Tcl 8.6 cuenta como dos los caracteres que no
    caben en 16 bits (emojis)."""
    extra = sum(1 for ch in text[:offset] if ord(ch) > 0xFFFF) if _WIDE else 0
    return f"1.0 + {offset + extra} chars"


_WIDE = tk.TkVersion < 8.7


def fmt_date(value):
    return value.strftime("%Y-%m-%d %H:%M") if value else ""


def fmt_size(size):
    return f"{size / 1024:,.0f} KB" if size < 1024 * 1024 else f"{size / 1024 / 1024:,.1f} MB"


def swatch(master, color, size=14):
    """Cuadradito de color para las etiquetas (hay que guardar la referencia de la imagen)."""
    image = tk.PhotoImage(master=master, width=size, height=size)
    image.put(CATEGORY_HEX.get(color, "#C8C8C8"), to=(0, 0, size, size))
    image.put("#6E6E6E", to=(0, 0, size, 1))
    image.put("#6E6E6E", to=(0, size - 1, size, size))
    image.put("#6E6E6E", to=(0, 0, 1, size))
    image.put("#6E6E6E", to=(size - 1, 0, size, size))
    return image


class MessageList(ttk.Frame):
    """Lista de correos con estado (● no leído, ⚑ seguimiento, ⎘ adjuntos), fecha, remitente, asunto…"""

    WIDTHS = {"state": 46, "received": 142, "sender": 180, "subject": 380, "categories": 150, "size": 76,
              "folder": 220}
    KEYS = {"received": lambda m: m.received or 0, "sender": lambda m: (m.sender_name or m.sender_email).lower(),
            "subject": lambda m: m.subject.lower(), "categories": lambda m: ", ".join(m.categories).lower(),
            "size": lambda m: m.size, "folder": lambda m: m.folder_path.lower(),
            "state": lambda m: (m.unread, m.flagged, m.has_attachments)}

    def __init__(self, parent, app, folder_column=False, height=12, on_select=None, on_open=None, menu=None):
        super().__init__(parent)
        self.app = app
        self.messages = []
        self.columns = ["state", "received", "sender", "subject", "categories", "size"]
        if folder_column:
            self.columns.append("folder")
        self.tree = ttk.Treeview(self, columns=self.columns, show="headings", height=height, selectmode="extended")
        for col in self.columns:
            self.tree.column(col, width=self.WIDTHS[col], stretch=col == "subject", anchor="e" if col == "size" else "w")
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
        bold = tkfont.nametofont("TkDefaultFont").copy()
        bold.configure(weight="bold")
        self._bold = bold
        self.tree.tag_configure("unread", font=bold)
        self._sort = ("received", True)
        app.tr_call(self._headings)
        if on_select:
            self.tree.bind("<<TreeviewSelect>>", lambda e: on_select(self.selected()))
        if on_open:
            self.tree.bind("<Double-1>", lambda e: self.selected() and on_open(self.selected()[0]))
        if menu:
            self.tree.bind("<Button-3>", lambda e: self._popup(e, menu))
            self.tree.bind("<Shift-F10>", lambda e: self._popup(None, menu))

    def _headings(self):
        for col in self.columns:
            arrow = (" ▼" if self._sort[1] else " ▲") if self._sort[0] == col else ""
            text = "" if col == "state" else self.app.t(f"col_{col}") + arrow
            self.tree.heading(col, text=text, command=lambda c=col: self.sort_by(c))

    def set(self, messages, footer=""):
        self.messages = list(messages)
        self._fill()
        self.footer.configure(text=footer)

    def refresh(self):
        self._fill(keep=True)

    def _fill(self, keep=False):
        selected = {self.messages[int(i)].id for i in self.tree.selection() if int(i) < len(self.messages)} if keep \
            else set()
        self.tree.delete(*self.tree.get_children())
        for n, m in enumerate(self.messages):
            state = "".join(symbol for attr, symbol in STATE_SYMBOLS if getattr(m, attr))
            values = [state, fmt_date(m.received), m.sender_name or m.sender_email, m.subject,
                      ", ".join(m.categories), fmt_size(m.size)]
            if "folder" in self.columns:
                values.append(m.folder_path)
            self.tree.insert("", "end", iid=str(n), values=values, tags=("unread",) if m.unread else ())
            if m.id in selected:
                self.tree.selection_add(str(n))

    def sort_by(self, column):
        descending = not self._sort[1] if self._sort[0] == column else column in ("received", "size", "state")
        self._sort = (column, descending)
        self.messages.sort(key=self.KEYS[column], reverse=descending)
        self._fill()
        self._headings()

    def selected(self):
        return [self.messages[int(i)] for i in self.tree.selection() if int(i) < len(self.messages)]

    def remove(self, messages):
        gone = {m.id for m in messages}
        self.messages = [m for m in self.messages if m.id not in gone]
        self._fill()

    def _popup(self, event, menu):
        if event is not None:
            row = self.tree.identify_row(event.y)
            if row and row not in self.tree.selection():
                self.tree.selection_set(row)
            x, y = event.x_root, event.y_root
        else:
            x, y = self.tree.winfo_rootx() + 40, self.tree.winfo_rooty() + 40
        if self.selected():
            menu().tk_popup(x, y)


class Preview(ttk.Frame):
    """Encabezado, avisos (phishing, datos de tarjeta) y cuerpo del correo con los términos buscados resaltados."""

    def __init__(self, parent, app, height=10):
        super().__init__(parent)
        self.app = app
        self.header = ttk.Label(self, justify="left", anchor="w")
        self.header.pack(fill="x")
        self.warning = tk.Label(self, bg="#FDE7E9", fg="#A4262C", anchor="w", justify="left", padx=8, pady=4)
        self.body = TextBox(self, height=height, readonly=True)
        self.body.pack(fill="both", expand=True, pady=(4, 0))
        self.body.text.tag_configure("hit", background="#FFF59D")
        self.msg = None
        self._last = None
        app.tr_call(self._relabel)

    def _relabel(self):
        if self._last is not None and self.msg is not None:
            self.show(*self._last)

    def clear(self):
        self.msg = self._last = None
        self.header.configure(text="")
        self.warning.pack_forget()
        self.body.set("")

    def show(self, msg, highlights=(), warnings=()):
        """`warnings` puede ser una función: así los avisos se traducen de nuevo al cambiar de idioma."""
        t = self.app.t
        self.msg, self._last = msg, (msg, highlights, warnings)
        warnings = warnings() if callable(warnings) else warnings
        sender = f"{msg.sender_name} <{msg.sender_email}>" if msg.sender_email else msg.sender_name
        lines = [f"{t('pv_subject')}: {msg.subject}", f"{t('pv_from')}: {sender}", f"{t('pv_to')}: {msg.to}"]
        if msg.cc:
            lines.append(f"{t('pv_cc')}: {msg.cc}")
        lines.append(f"{t('pv_date')}: {fmt_date(msg.received)}   ·   {t('pv_folder')}: {msg.folder_path}")
        if msg.categories:
            lines.append(f"{t('pv_categories')}: {', '.join(msg.categories)}")
        if msg.attachments:
            lines.append(f"{t('pv_attachments')}: {', '.join(msg.attachments)}")
        self.header.configure(text="\n".join(lines))
        if warnings:
            self.warning.configure(text="\n".join(warnings), wraplength=max(300, self.winfo_width() - 30))
            self.warning.pack(fill="x", pady=(4, 0), before=self.body)
        else:
            self.warning.pack_forget()
        self.body.set(msg.body or "")
        text = self.body.text
        content = msg.body or ""
        for pattern in highlights:
            for m in pattern.finditer(content):
                if m.end() > m.start():
                    text.tag_add("hit", tk_index(content, m.start()), tk_index(content, m.end()))


class FolderDialog(tk.Toplevel):
    """Elige una carpeta de cualquier buzón conectado. `result` es su id (o None si se cancela)."""

    def __init__(self, app, title_key, stores, folders, allow_root=False):
        super().__init__(app)
        self.app, self.result, self.allow_root = app, None, allow_root
        self.title(app.t(title_key))
        self.transient(app)
        frame = ttk.Frame(self, padding=12)
        frame.pack(fill="both", expand=True)
        self.tree = ttk.Treeview(frame, show="tree", height=18, selectmode="browse")
        bar = ttk.Scrollbar(frame, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=bar.set)
        self.tree.grid(row=0, column=0, sticky="nsew")
        bar.grid(row=0, column=1, sticky="ns")
        frame.rowconfigure(0, weight=1)
        frame.columnconfigure(0, weight=1)
        self.depth = {}
        for store in stores:
            for folder in folders.get(store.id, []):
                parent = "" if folder.depth == 0 else folder.parent_id
                text = store.name if folder.depth == 0 else folder.name
                self.tree.insert(parent, "end", iid=folder.id, text=text, open=folder.depth < 2)
                self.depth[folder.id] = folder.depth
        buttons = ttk.Frame(frame)
        buttons.grid(row=1, column=0, columnspan=2, sticky="e", pady=(10, 0))
        ttk.Button(buttons, text=app.t("cancel"), command=self.destroy).pack(side="right")
        ttk.Button(buttons, text=app.t("ok"), style="Accent.TButton", command=self.accept).pack(side="right", padx=8)
        self.tree.bind("<Double-1>", lambda e: self.accept())
        self.geometry(f"{int(420 * app.scale)}x{int(520 * app.scale)}")
        self.grab_set()
        self.tree.focus_set()
        app.wait_window(self)

    def accept(self):
        sel = self.tree.selection()
        if not sel or (self.depth.get(sel[0]) == 0 and not self.allow_root):
            return
        self.result = sel[0]
        self.destroy()


class CategoryDialog(tk.Toplevel):
    """Marca las etiquetas que deben tener los correos elegidos (o una regla).

    `result` = (añadir, quitar) o None. Las etiquetas que solo tienen algunos correos no cambian salvo que el
    usuario las toque. Desde aquí también se pueden crear etiquetas nuevas con `create(nombre, color)`."""

    def __init__(self, app, categories, messages=(), initial=(), create=None):
        super().__init__(app)
        self.app, self.result, self.create = app, None, create
        self.title(app.t("cat_dialog_title"))
        self.transient(app)
        self.vars, self.before, self.touched, self.images = {}, {}, set(), []
        frame = ttk.Frame(self, padding=14)
        frame.pack(fill="both", expand=True)
        self.list = ttk.Frame(frame)
        self.list.pack(fill="both", expand=True)
        messages = list(messages)
        initial = {c.lower() for c in initial}
        for cat in categories:
            having = sum(1 for m in messages if cat.name.lower() in {c.lower() for c in m.categories})
            state = "all" if messages and having == len(messages) else "some" if having else "none"
            if not messages:
                state = "all" if cat.name.lower() in initial else "none"
            self._row(cat.name, cat.color, state)
        if create is not None:
            new = ttk.LabelFrame(frame, text=app.t("cat_new"), padding=8)
            new.pack(fill="x", pady=(10, 0))
            self.new_name = ttk.Entry(new, width=24)
            self.new_name.pack(side="left")
            self.new_color = ttk.Combobox(new, state="readonly", width=12,
                                          values=[app.t(key) for key, _ in PICKER_COLORS])
            self.new_color.current(0)
            self.new_color.pack(side="left", padx=6)
            ttk.Button(new, text=app.t("cat_create"), command=self._create).pack(side="left")
        buttons = ttk.Frame(frame)
        buttons.pack(fill="x", pady=(12, 0))
        ttk.Button(buttons, text=app.t("cancel"), command=self.destroy).pack(side="right")
        ttk.Button(buttons, text=app.t("ok"), style="Accent.TButton", command=self.accept).pack(side="right", padx=8)
        self.grab_set()
        app.wait_window(self)

    def _row(self, name, color, state):
        image = swatch(self, color)
        self.images.append(image)
        var = tk.BooleanVar(value=state == "all")
        label = name + (f"  ({self.app.t('cat_some')})" if state == "some" else "")
        ttk.Checkbutton(self.list, text=label, image=image, compound="left", variable=var,
                        command=lambda: self.touched.add(name)).pack(anchor="w", pady=1)
        self.vars[name], self.before[name] = var, state

    def _create(self):
        name = self.new_name.get().strip()
        if not name or name.lower() in {n.lower() for n in self.vars}:
            return
        color = PICKER_COLORS[max(0, self.new_color.current())][1]
        if self.create(name, color):
            self._row(name, color, "none")
            self.vars[name].set(True)
            self.touched.add(name)
            self.new_name.delete(0, "end")

    def accept(self):
        add, remove = [], []
        for name, var in self.vars.items():
            state = self.before[name]
            if var.get() and (state == "none" or (state == "some" and name in self.touched)):
                add.append(name)
            elif not var.get() and (state == "all" or (state == "some" and name in self.touched)):
                remove.append(name)
        self.result = (add, remove)
        self.destroy()


class ResultDialog(tk.Toplevel):
    """Muestra el resultado de la IA en secciones (algunas editables) con botones de acción."""

    def __init__(self, app, title_key, sections, buttons):
        super().__init__(app)
        self.app = app
        self.title(app.t(title_key))
        self.transient(app)
        frame = ttk.Frame(self, padding=14)
        frame.pack(fill="both", expand=True)
        self.boxes = {}
        for key, text, editable, height in sections:
            ttk.Label(frame, text=app.t(key), style="Title.TLabel").pack(anchor="w", pady=(6, 2))
            if height == 1:
                box = ttk.Entry(frame, width=90)
                box.insert(0, text)
            else:
                box = TextBox(frame, height=height, readonly=not editable, width=90)
                box.set(text)
            box.pack(fill="both", expand=height > 1)
            self.boxes[key] = box
        bar = ttk.Frame(frame)
        bar.pack(fill="x", pady=(12, 0))
        ttk.Button(bar, text=app.t("close"), command=self.destroy).pack(side="right")
        for n, (key, callback) in enumerate(buttons):
            ttk.Button(bar, text=app.t(key), style="Accent.TButton" if n == 0 else "TButton",
                       command=lambda cb=callback: cb(self)).pack(side="right", padx=(0, 8))
        self.ai_note = ttk.Label(frame, text=app.t("ai_disclaimer"), style="Hint.TLabel", wraplength=700)
        self.ai_note.pack(anchor="w", pady=(8, 0))

    def value(self, key):
        box = self.boxes[key]
        return box.get().strip() if isinstance(box, ttk.Entry) else box.get()
