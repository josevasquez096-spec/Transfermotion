"""MoreInfo Pilot: puts the screenshots of a fraud claim into CASE,MOREINFO.pdf (or a new Excel tab) and saves
it to the folders the analyst configures. English only."""

import hashlib
import json
import re
import tempfile
import tkinter as tk
from datetime import datetime
from pathlib import Path
from tkinter import filedialog, messagebox, simpledialog, ttk

from PIL import Image

from ..ui import PilotApp, ScrollFrame, TextBox, open_path
from . import letter, logic
from .strings import STRINGS

DEFAULTS = {"folder": "", "letter_folders": [], "use_word": True, "keep_docx": False, "base": logic.DEFAULT_BASE,
            "analyst": "", "sections": []}
BACKGROUND = Path(__file__).resolve().parent / "assets" / "background.jpg"
DOC_TYPES = ("*.pdf *.docx *.doc *.rtf *.xlsx *.xlsm *.xls *.csv *.txt *.msg *.eml *.png *.jpg *.jpeg")
POLL_MS = 800


def grab_clipboard():
    """Image(s) in the clipboard: a list of PIL images (empty if there is none)."""
    from PIL import ImageGrab

    data = ImageGrab.grabclipboard()
    if isinstance(data, Image.Image):
        return [data]
    if isinstance(data, list):  # archivos copiados en el Explorador
        out = []
        for name in data:
            if str(name).lower().endswith(logic.IMAGE_TYPES):
                with Image.open(name) as img:
                    out.append(img.copy())
        return out
    return []


AUTHOR = "Created by Jose Vasquez"


class MoreInfoPilot(PilotApp):
    APP_NAME = "MoreInfo Pilot"
    ICON_TEXT = "MI"
    ACCENT = "#0E7490"
    STRINGS = STRINGS

    def build(self):
        self.t.lang = "en"  # de momento solo en inglés
        self.lang_combo.master.pack_forget()  # sin selector de idioma ni ajustes de IA
        self.prefs_path = self.settings.data_dir() / "moreinfo.json"
        self.prefs = dict(DEFAULTS)
        try:
            self.prefs.update(json.loads(self.prefs_path.read_text(encoding="utf-8")))
        except (OSError, ValueError):
            pass
        old = self.prefs.pop("folders", None)  # versiones anteriores: lista de carpetas
        if not self.prefs["folder"] and old:
            self.prefs["folder"] = old[0]
        self.templates_dir = self.settings.data_dir() / "letter_templates"
        self.prefs.setdefault("templates", [])
        legacy = self.settings.data_dir() / "letter_template.docx"  # versión anterior: una sola plantilla
        if legacy.exists() and not self.prefs["templates"]:
            self.templates_dir.mkdir(parents=True, exist_ok=True)
            legacy.replace(self.templates_dir / "template_1.docx")
            name = Path(self.prefs.pop("template_name", "") or "Default letter").stem
            self.prefs["templates"].append({"name": name, "file": "template_1.docx"})
        self.shots = []
        self.documents = []
        self.dnd = self._enable_dnd()
        self._thumb = None
        self._last_clip = None
        self.last_output = None
        self._build_package()
        self._build_documents()
        self._build_settings()
        self._build_background()
        self.bind_all("<Control-v>", self._ctrl_v)
        self.after(POLL_MS, self._poll_clipboard)
        for fn in list(self._i18n):  # vuelve a pintar la cabecera en inglés
            fn()

    def set_lang(self, lang):
        pass

    def _enable_dnd(self):
        """Arrastrar y soltar archivos (tkdnd). Si no está disponible, la app funciona igual sin él."""
        try:
            from tkinterdnd2 import TkinterDnD

            TkinterDnD._require(self)
            return True
        except Exception:
            return False

    def _drop_target(self, widget, handler):
        if self.dnd:
            from tkinterdnd2 import DND_FILES

            widget.drop_target_register(DND_FILES)
            widget.dnd_bind("<<Drop>>", lambda e: handler(list(self.tk.splitlist(e.data))))

    def _build_background(self):
        """La foto de fondo se ve alrededor de las pestañas y en la vista previa vacía."""
        self._bg_source = None
        try:
            self._bg_source = Image.open(BACKGROUND).convert("RGB")
        except OSError:
            ttk.Label(self, text=AUTHOR, style="Hint.TLabel").pack(side="bottom", anchor="e", padx=44)
            return
        self.nb.pack_forget()
        self.bg = tk.Canvas(self, highlightthickness=0, borderwidth=0)
        self.bg.pack(fill="both", expand=True)
        self.nb.place(in_=self.bg, x=40, y=30, relwidth=1, relheight=1, width=-80, height=-60)
        self.nb.lift()
        self._bg_image = None
        self.bg.bind("<Configure>", self._paint_background)

    def _paint_background(self, event):
        w, h = max(1, event.width), max(1, event.height)
        self.bg.delete("all")
        try:
            from PIL import ImageTk
        except ImportError:
            ImageTk = None
        if ImageTk is not None:
            src = self._bg_source
            scale = max(w / src.width, h / src.height)  # cubre toda la ventana sin deformar
            img = src.resize((int(src.width * scale) + 1, int(src.height * scale) + 1))
            left, top = (img.width - w) // 2, (img.height - h) // 2
            self._bg_image = ImageTk.PhotoImage(img.crop((left, top, left + w, top + h)))
            self.bg.create_image(0, 0, image=self._bg_image, anchor="nw")
        # autoría, en la franja inferior del fondo (con sombra para leerse sobre la foto)
        font = ("Segoe UI", 10, "italic")
        self.bg.create_text(w - 39, h - 14, text=AUTHOR, anchor="e", fill="#1B2B34", font=font)
        self.bg.create_text(w - 40, h - 15, text=AUTHOR, anchor="e", fill="#FFFFFF", font=font, tags="author")

    def update_ai_status(self):
        self.ai_label.configure(text=self.t("offline"))

    def save_prefs(self):
        self.prefs_path.parent.mkdir(parents=True, exist_ok=True)
        self.prefs_path.write_text(json.dumps(self.prefs, indent=2), encoding="utf-8")

    # ------------------------------------------------------------ package tab
    def _build_package(self):
        tab = self.add_tab("tab_package", padding=10)
        top = ttk.Frame(tab)
        top.pack(fill="x")
        self.case_var = tk.StringVar()
        self.analyst_var = tk.StringVar(value=self.prefs.get("analyst", ""))
        self.lbl(top, "case").pack(side="left")
        case_entry = ttk.Entry(top, textvariable=self.case_var, width=18, font=("Segoe UI", 12))
        case_entry.pack(side="left", padx=(6, 18))
        self.lbl(top, "analyst").pack(side="left")
        ttk.Entry(top, textvariable=self.analyst_var, width=24).pack(side="left", padx=6)

        out = self.lframe(tab, "output", padding=8)
        out.pack(fill="x", pady=8)
        self.mode = tk.StringVar(value="pdf")
        for key in ("pdf", "excel"):
            self.tr(ttk.Radiobutton(out, variable=self.mode, value=key, command=self._mode_changed),
                    f"mode_{key}").pack(anchor="w")
        row = ttk.Frame(out)
        row.pack(fill="x", pady=(4, 0))
        self.lbl(row, "excel_file").pack(side="left")
        self.excel_var = tk.StringVar()
        self.excel_entry = ttk.Entry(row, textvariable=self.excel_var)
        self.excel_entry.pack(side="left", fill="x", expand=True, padx=6)
        self.excel_btn = self.btn(row, "browse", self.pick_excel)
        self.excel_btn.pack(side="left")

        self.result = TextBox(tab, height=4, readonly=True)
        self.result.pack(side="bottom", fill="x", pady=(6, 0))
        bottom = ttk.Frame(tab)
        bottom.pack(side="bottom", fill="x", pady=(8, 0))
        self.btn(bottom, "create", self.create, accent=True).pack(side="left")
        self.btn(bottom, "new_case", self.new_case).pack(side="left", padx=6)
        self.btn(bottom, "open_folder", self.open_output).pack(side="left")
        self.reminder = tk.Label(tab, bg="#FFF4CE", fg="#7A4F01", anchor="w", justify="left", padx=10, pady=6,
                                 font=("Segoe UI", 10, "bold"), cursor="hand2")
        self.reminder.pack(side="bottom", fill="x", pady=(8, 0))
        self.reminder.bind("<Configure>", lambda e: self.reminder.configure(wraplength=max(200, e.width - 24)))
        self.reminder.bind("<Button-1>", lambda e: self.nb.select(1))
        self.tr(self.reminder, "docs_reminder")

        panes = ttk.PanedWindow(tab, orient="horizontal")
        panes.pack(fill="both", expand=True)
        left = self.lframe(panes, "screenshots", padding=6)
        panes.add(left, weight=3)
        bar = ttk.Frame(left)
        bar.pack(fill="x")
        self.lbl(bar, "section").pack(side="left")
        self.section = ttk.Combobox(bar, state="readonly", width=24)
        self.section.pack(side="left", padx=6)
        self.btn(bar, "add_section", self.add_section, width=3).pack(side="left", padx=(0, 6))
        self.btn(bar, "paste", self.paste, accent=True).pack(side="left")
        self.btn(bar, "add_images", self.add_images).pack(side="left", padx=6)
        self.auto_var = tk.BooleanVar(value=False)
        self.chk(left, "auto_capture", self.auto_var).pack(anchor="w", pady=4)
        self.tree = ttk.Treeview(left, columns=("n", "section", "caption", "size"), show="headings", height=6)
        for col, width in (("n", 40), ("section", 160), ("caption", 260), ("size", 90)):
            self.tree.column(col, width=width, stretch=col == "caption")
            self.tree.heading(col, text=self.t(f"col_{col}"))
        self.tree.bind("<<TreeviewSelect>>", lambda e: self.show_preview())
        self.tree.bind("<Double-1>", lambda e: self.edit_caption())
        self.tree.bind("<Delete>", lambda e: self.remove_shot())
        tools = ttk.Frame(left)
        tools.pack(side="bottom", fill="x", pady=(4, 0))
        self.btn(tools, "caption", self.edit_caption).pack(side="left")
        self.btn(tools, "remove", self.remove_shot).pack(side="left", padx=6)
        self.btn(tools, "up", lambda: self.move_shot(-1), width=3).pack(side="left")
        self.btn(tools, "down", lambda: self.move_shot(1), width=3).pack(side="left", padx=4)
        self.tree.pack(fill="both", expand=True)
        self._drop_target(self.tree, self.drop_images)

        right = self.lframe(panes, "preview", padding=6)
        panes.add(right, weight=2)
        self.canvas = tk.Canvas(right, background="#F3F6F9", highlightthickness=0, width=360, height=260)
        self.canvas.pack(fill="both", expand=True)
        self.canvas.bind("<Configure>", lambda e: self.show_preview())

        self._mode_changed()
        case_entry.focus_set()

    def _mode_changed(self):
        excel = self.mode.get() == "excel"
        state = ["!disabled"] if excel else ["disabled"]
        self.excel_entry.state(state)
        self.excel_btn.state(state)

    def pick_excel(self):
        path = filedialog.askopenfilename(parent=self, filetypes=[("Excel", "*.xlsx *.xlsm *.xls"),
                                                                  (self.t("ft_all"), "*.*")])
        if path:
            self.excel_var.set(path)

    def _store(self, image):
        folder = Path(tempfile.gettempdir()) / "MoreInfoPilot"  # capturas pegadas (temporales)
        folder.mkdir(parents=True, exist_ok=True)
        path = folder / f"{datetime.now():%Y%m%d_%H%M%S_%f}.png"
        image.convert("RGB").save(path)
        return path

    @property
    def current_section(self):
        return self.section.get()

    def _need_section(self):
        """Las secciones las define el usuario: sin ninguna, se le pide crear la primera."""
        if self.current_section:
            return True
        messagebox.showinfo(self.APP_NAME, self.t("need_section"), parent=self)
        return self.add_section()

    def add_shot(self, path, section=None):
        with Image.open(path) as img:
            size = f"{img.width}×{img.height}"
        self.shots.append({"shot": logic.Shot(section or self.current_section, str(path)), "size": size})
        self._fill()

    def _fill(self, select=None):
        self.tree.delete(*self.tree.get_children())
        # se mantienen juntas las capturas de cada sección, en el orden de las secciones guardadas
        order = {s: n for n, s in enumerate(self.prefs["sections"])}
        self.shots.sort(key=lambda x: order.get(x["shot"].section, 99))
        for n, item in enumerate(self.shots):
            shot = item["shot"]
            self.tree.insert("", "end", iid=str(n), values=(n + 1, shot.section, shot.caption, item["size"]))
        if select is not None and 0 <= select < len(self.shots):
            self.tree.selection_set(str(select))
            self.tree.see(str(select))
        self.show_preview()

    def paste(self):
        if not self._need_section():
            return
        try:
            images = grab_clipboard()
        except Exception as exc:  # p. ej. Linux sin xclip
            messagebox.showwarning(self.APP_NAME, self.t("clipboard_error", detail=exc), parent=self)
            return
        if not images:
            messagebox.showinfo(self.APP_NAME, self.t("no_clipboard_image"), parent=self)
            return
        for image in images:
            self.add_shot(self._store(image))
        self._last_clip = self._fingerprint(images[-1])
        self.status(self.t("added_n", n=len(images), section=self.current_section))

    def _ctrl_v(self, event):
        if isinstance(event.widget, (tk.Entry, ttk.Entry, tk.Text)):
            return None  # pegar texto normal en los campos
        if self.nb.index("current") == 1:
            self.paste_documents()
        else:
            self.paste()
        return "break"

    @staticmethod
    def _fingerprint(image):
        return hashlib.md5(image.convert("RGB").resize((64, 64)).tobytes()).hexdigest()

    def _poll_clipboard(self):
        """Con «Auto-add», cada captura nueva del portapapeles se añade sola a la sección elegida."""
        try:
            if self.auto_var.get() and self.current_section:
                images = grab_clipboard()
                if images:
                    mark = self._fingerprint(images[-1])
                    if self._last_clip is None:
                        self._last_clip = mark  # lo que ya estaba al activar no se añade
                    elif mark != self._last_clip:
                        self._last_clip = mark
                        for image in images:
                            self.add_shot(self._store(image))
                        self.status(self.t("added_n", n=len(images), section=self.current_section))
            else:
                self._last_clip = None
        except Exception:  # el portapapeles puede estar ocupado por otro programa
            pass
        self.after(POLL_MS, self._poll_clipboard)

    def drop_images(self, paths):
        images = [p for p in paths if p.lower().endswith(logic.IMAGE_TYPES)]
        if images and self._need_section():
            for path in images:
                self.add_shot(path)
            self.status(self.t("added_n", n=len(images), section=self.current_section))

    def add_images(self):
        if not self._need_section():
            return
        paths = filedialog.askopenfilenames(parent=self, filetypes=[
            ("Images", " ".join(f"*{e}" for e in logic.IMAGE_TYPES)), (self.t("ft_all"), "*.*")])
        for path in paths:
            self.add_shot(path)

    def _selected(self):
        sel = self.tree.selection()
        if not sel:
            messagebox.showinfo(self.APP_NAME, self.t("need_selection"), parent=self)
            return None
        return int(sel[0])

    def edit_caption(self):
        index = self._selected()
        if index is None:
            return
        shot = self.shots[index]["shot"]
        text = simpledialog.askstring(self.APP_NAME, self.t("caption_prompt"), initialvalue=shot.caption,
                                      parent=self)
        if text is not None:
            shot.caption = text.strip()
            self._fill(index)

    def remove_shot(self):
        index = self._selected()
        if index is not None:
            del self.shots[index]
            self._fill(min(index, len(self.shots) - 1))

    def move_shot(self, step):
        index = self._selected()
        if index is None:
            return
        other = index + step
        if 0 <= other < len(self.shots) and \
                self.shots[other]["shot"].section == self.shots[index]["shot"].section:
            self.shots[index], self.shots[other] = self.shots[other], self.shots[index]
            self._fill(other)

    def show_preview(self):
        self.canvas.delete("all")
        sel = self.tree.selection()
        if not sel or int(sel[0]) >= len(self.shots):
            self._preview_background()
            return
        w, h = max(50, self.canvas.winfo_width()), max(50, self.canvas.winfo_height())
        with Image.open(self.shots[int(sel[0])]["shot"].path) as img:
            img = img.copy()
        img.thumbnail((w - 10, h - 10))
        try:
            from PIL import ImageTk
        except ImportError:  # Pillow sin soporte de Tk: no hay vista previa
            return
        self._thumb = ImageTk.PhotoImage(img)
        self.canvas.create_image(w // 2, h // 2, image=self._thumb)

    def _preview_background(self):
        """Vista previa vacía: la foto de fondo, aclarada."""
        source = getattr(self, "_bg_source", None)
        if source is None:
            return
        try:
            from PIL import ImageTk
        except ImportError:
            return
        w, h = max(50, self.canvas.winfo_width()), max(50, self.canvas.winfo_height())
        img = source.copy()
        img.thumbnail((w, h))
        img = Image.blend(img, Image.new("RGB", img.size, "white"), 0.55)
        self._thumb = ImageTk.PhotoImage(img)
        self.canvas.create_image(w // 2, h // 2, image=self._thumb)

    # ------------------------------------------------------------ documents tab
    def _build_documents(self):
        tab = self.add_tab("tab_documents", padding=10)
        top = ttk.Frame(tab)
        top.pack(fill="x")
        self.lbl(top, "case").pack(side="left")
        ttk.Entry(top, textvariable=self.case_var, width=18, font=("Segoe UI", 12)).pack(side="left", padx=6)
        self.lbl(tab, "docs_intro", hint=True, wraplength=1000, justify="left").pack(anchor="w", pady=(8, 6))
        tpl = self.lframe(tab, "letter_box", padding=8)
        tpl.pack(fill="x", pady=(0, 8))
        row = ttk.Frame(tpl)
        row.pack(fill="x")
        self.lbl(row, "template").pack(side="left")
        self.template_combo = ttk.Combobox(row, state="readonly", width=34)
        self.template_combo.pack(side="left", padx=6)
        self.template_combo.bind("<<ComboboxSelected>>", lambda e: self._show_template())
        self.btn(row, "load_template", self.load_template).pack(side="left")
        self.btn(row, "rename_template", self.rename_template).pack(side="left", padx=6)
        self.btn(row, "remove_template", self.remove_template).pack(side="left")
        self.btn(row, "fill_letter", self.fill_letter, accent=True).pack(side="right")
        self.template_label = ttk.Label(tpl, style="Hint.TLabel")
        self.template_label.pack(anchor="w", pady=(6, 0))
        self.tr_call(self._fill_templates)
        self.drop_zone = tk.Label(tab, bg="#E8F4F8", fg="#0E7490", font=("Segoe UI", 12, "bold"), height=4,
                                  relief="groove", borderwidth=2, cursor="hand2")
        self.drop_zone.pack(fill="x")
        self.tr(self.drop_zone, "drop_here" if self.dnd else "drop_unavailable")
        self.drop_zone.bind("<Button-1>", lambda e: self.browse_documents())
        bar = ttk.Frame(tab)
        bar.pack(fill="x", pady=8)
        self.btn(bar, "browse_docs", self.browse_documents, accent=True).pack(side="left")
        self.btn(bar, "paste_docs", self.paste_documents).pack(side="left", padx=6)
        self.btn(bar, "remove", self.remove_document).pack(side="left")
        self.btn(bar, "toggle_letter", self.toggle_letter).pack(side="left", padx=6)
        self.btn(bar, "preview_doc", self.preview_document).pack(side="left")
        self.btn(bar, "upload_docs", self.upload_documents).pack(side="right")
        self.doc_tree = ttk.Treeview(tab, columns=("n", "file", "type", "saved", "dest"), show="headings", height=6)
        for col, width in (("n", 40), ("file", 380), ("type", 90), ("saved", 120), ("dest", 200)):
            self.doc_tree.column(col, width=width, stretch=col == "file")
            self.doc_tree.heading(col, text=self.t(f"dcol_{col}"))
        self.doc_tree.pack(fill="both", expand=True)
        self.doc_tree.bind("<Delete>", lambda e: self.remove_document())
        self.doc_tree.bind("<Double-1>", lambda e: self.edit_or_preview())
        for widget in (self.drop_zone, self.doc_tree):
            self._drop_target(widget, self.add_documents)

    def add_documents(self, paths, letter_doc=False):
        added = 0
        for path in paths:
            if Path(path).is_file() and path not in [d["path"] for d in self.documents]:
                self.documents.append({"path": path, "letter": letter_doc})
                added += 1
        self._fill_documents()
        if added:
            self.status(self.t("docs_added", n=added))

    def _fill_documents(self):
        self.doc_tree.delete(*self.doc_tree.get_children())
        for n, doc in enumerate(self.documents):
            path = doc["path"]
            ext = Path(path).suffix.lower()
            target = logic.document_target(path)
            saved = "PDF" if target == ".pdf" else self.t("same_format")
            dest = self.t("dest_letter", n=len(self.prefs["letter_folders"]) or 1) if doc["letter"] \
                else self.t("dest_main")
            name = ("✉ " if doc["letter"] else "") + Path(path).name
            self.doc_tree.insert("", "end", iid=str(n), values=(n + 1, name, ext.lstrip(".").upper(), saved, dest))
        self.reminder.configure(text=self.t("docs_attached", n=len(self.documents)) if self.documents
                                else self.t("docs_reminder"),
                                bg="#DFF6DD" if self.documents else "#FFF4CE",
                                fg="#0B5A2E" if self.documents else "#7A4F01")

    def browse_documents(self):
        self.add_documents(list(filedialog.askopenfilenames(parent=self, filetypes=[
            (self.t("doc_types"), DOC_TYPES), (self.t("ft_all"), "*.*")])))

    def paste_documents(self):
        """Pega archivos copiados en el Explorador, una imagen (se guarda como PDF) o texto (correo, notas)."""
        try:
            from PIL import ImageGrab

            data = ImageGrab.grabclipboard()
        except Exception:
            data = None
        folder = Path(tempfile.gettempdir()) / "MoreInfoPilot"
        folder.mkdir(parents=True, exist_ok=True)
        stamp = f"{datetime.now():%Y%m%d_%H%M%S}"
        if isinstance(data, list) and data:
            self.add_documents([str(x) for x in data])
            return
        if isinstance(data, Image.Image):
            path = folder / f"pasted_{stamp}.png"
            data.convert("RGB").save(path)
            self.add_documents([str(path)])
            return
        try:
            text = self.clipboard_get()
        except tk.TclError:
            text = ""
        if text.strip():
            path = folder / f"pasted_text_{stamp}.txt"
            path.write_text(text, encoding="utf-8")
            self.add_documents([str(path)])
            return
        messagebox.showinfo(self.APP_NAME, self.t("nothing_to_paste"), parent=self)

    def toggle_letter(self):
        """Marca o desmarca un documento como la No Pay Decision Letter (va a las carpetas de la carta)."""
        sel = self.doc_tree.selection()
        if not sel:
            messagebox.showinfo(self.APP_NAME, self.t("need_document_selection"), parent=self)
            return
        for iid in sel:
            self.documents[int(iid)]["letter"] = not self.documents[int(iid)]["letter"]
        self._fill_documents()

    # ------------------------------------------------------------ decision letter templates (several, named)
    def _template_file(self, template):
        return self.templates_dir / template["file"]

    def current_template(self):
        index = self.template_combo.current()
        templates = self.prefs["templates"]
        return templates[index] if 0 <= index < len(templates) else None

    def _fill_templates(self, select=None):
        names = [t["name"] for t in self.prefs["templates"]]
        current = select or self.template_combo.get()
        self.template_combo["values"] = names
        if current in names:
            self.template_combo.set(current)
        elif names:
            self.template_combo.current(0)
        else:
            self.template_combo.set("")
        self._show_template()

    def _show_template(self):
        template = self.current_template()
        if template is None:
            self.template_label.configure(text=self.t("template_none"))
            return
        self.template_label.configure(text=self.t("template_loaded", name=template["name"],
                                                  n=len(self._template_fields(template))))

    def _template_fields(self, template):
        try:
            return letter.scan(self._template_file(template))
        except Exception:  # plantilla dañada o que no es .docx
            return []

    def _ask_template_name(self, initial=""):
        name = simpledialog.askstring(self.APP_NAME, self.t("template_name_prompt"), initialvalue=initial,
                                      parent=self)
        name = " ".join((name or "").split())
        if name and name != initial and name.lower() in {t["name"].lower() for t in self.prefs["templates"]}:
            messagebox.showwarning(self.APP_NAME, self.t("template_exists", name=name), parent=self)
            return None
        return name or None

    def load_template(self, path=None, name=None):
        """Añade una plantilla en blanco (.docx) con un nombre (p. ej. «Credit card – English», «Débit – French»)."""
        path = path or filedialog.askopenfilename(parent=self, filetypes=[("Word", "*.docx"),
                                                                          (self.t("ft_all"), "*.*")])
        if not path:
            return None
        try:
            fields = letter.scan(path)
        except Exception as exc:
            messagebox.showerror(self.APP_NAME, self.t("template_bad", detail=exc), parent=self)
            return None
        if not fields:
            messagebox.showwarning(self.APP_NAME, self.t("template_no_fields"), parent=self)
            return None
        name = name or self._ask_template_name(Path(path).stem)
        if not name:
            return None
        self.templates_dir.mkdir(parents=True, exist_ok=True)
        n = 1
        while (self.templates_dir / f"template_{n}.docx").exists():
            n += 1
        (self.templates_dir / f"template_{n}.docx").write_bytes(Path(path).read_bytes())
        self.prefs["templates"].append({"name": name, "file": f"template_{n}.docx"})
        self.save_prefs()
        self._fill_templates(select=name)
        return name

    def rename_template(self):
        template = self.current_template()
        if template is None:
            return
        name = self._ask_template_name(template["name"])
        if name:
            template["name"] = name
            self.save_prefs()
            self._fill_templates(select=name)

    def remove_template(self):
        template = self.current_template()
        if template is None or not messagebox.askyesno(self.APP_NAME, self.t("template_remove_confirm",
                                                                             name=template["name"]), parent=self):
            return
        self.prefs["templates"].remove(template)
        self._template_file(template).unlink(missing_ok=True)
        self.save_prefs()
        self._fill_templates()

    def fill_letter(self, template=None, values=None):
        template = template or self.current_template()
        if template is None:
            messagebox.showinfo(self.APP_NAME, self.t("template_none"), parent=self)
            return None
        fields = self._template_fields(template)
        if not fields:
            messagebox.showwarning(self.APP_NAME, self.t("template_no_fields"), parent=self)
            return None
        return LetterDialog(self, template, fields, values)

    def _letter_docx(self, template, values):
        # los campos sin rellenar quedan en blanco en la carta (sin el texto gris de ejemplo de la plantilla)
        values = {**{f.key: "" for f in self._template_fields(template)}, **values}
        folder = Path(tempfile.mkdtemp(prefix="moreinfo_letter_"))
        name = re.sub(r'[\\/:*?"<>|]', "-", template["name"])
        dest = folder / f"No Pay Decision Letter - {name}.docx"
        return letter.fill(self._template_file(template), values, dest)

    def preview_letter(self, template, values):
        """Crea la carta en PDF (igual que al subirla) y la abre para revisarla."""
        self._open_as_pdf(lambda: self._letter_docx(template, values))

    def _open_as_pdf(self, make_source):
        use_word = self.prefs["use_word"]

        def work():
            source = Path(make_source())
            if logic.document_target(source) != ".pdf":
                return source  # Excel, texto, correos: se abren con su programa
            folder = Path(tempfile.mkdtemp(prefix="moreinfo_preview_"))
            saved, _ = logic.prepare_document(source, folder / (source.stem + ".pdf"), use_word)
            return saved

        def done(path):
            open_path(path)
            self.status(self.t("preview_opened", name=Path(path).name))

        self.run_task(work, done)

    def letter_ready(self, template, values, previewed=False):
        """Rellena la plantilla y añade la carta a los documentos; al subirla se guarda en PDF."""
        dest = self._letter_docx(template, values)
        self.documents = [d for d in self.documents if not d.get("template")]  # una sola carta por caso
        self.documents.insert(0, {"path": str(dest), "letter": True, "template": template["name"],
                                  "values": dict(values), "previewed": previewed})
        self._fill_documents()
        self.status(self.t("letter_added"))

    def _template_by_name(self, name):
        return next((t for t in self.prefs["templates"] if t["name"] == name), None)

    def edit_or_preview(self):
        sel = self.doc_tree.selection()
        if not sel:
            return
        doc = self.documents[int(sel[0])]
        template = self._template_by_name(doc.get("template")) if doc.get("template") else None
        if template is not None:
            self.fill_letter(template, doc.get("values"))  # volver a editar la carta
        else:
            self.preview_document()

    def preview_document(self):
        sel = self.doc_tree.selection()
        if not sel:
            messagebox.showinfo(self.APP_NAME, self.t("need_document_selection"), parent=self)
            return
        doc = self.documents[int(sel[0])]
        if doc.get("template"):
            doc["previewed"] = True
        self._open_as_pdf(lambda: doc["path"])

    def remove_document(self):
        for iid in sorted((int(i) for i in self.doc_tree.selection()), reverse=True):
            del self.documents[iid]
        self._fill_documents()

    def upload_documents(self):
        """Sube solo los documentos (sin crear el MoreInfo con capturas)."""
        self._run(include_moreinfo=False)

    def new_case(self):
        if (self.shots or self.documents) and not messagebox.askyesno(self.APP_NAME, self.t("new_case_confirm"),
                                                                   parent=self):
            return
        self.shots, self.documents = [], []
        self._fill_documents()
        self.case_var.set("")
        self.excel_var.set("")
        self.result.set("")
        self._fill()

    def create(self):
        mode = self.mode.get()
        if mode == "excel" and not self.need(self.excel_var.get().strip(), "need_excel"):
            return
        if mode == "pdf" and not self.need(self.shots, "need_shots"):
            return
        if not self.documents:
            # recordatorio: el MoreInfo solo no es el paquete completo
            answer = messagebox.askyesnocancel(self.APP_NAME, self.t("docs_alert"), icon="warning", parent=self)
            if answer is None:
                return
            if answer is False:
                self.nb.select(1)
                return
        self._run(include_moreinfo=True)

    def _run(self, include_moreinfo):
        case = logic.clean_case(self.case_var.get())
        if not self.need(case, "need_case"):
            return
        pending = next((d for d in self.documents if d.get("template") and not d.get("previewed")), None)
        if pending is not None:
            # control: la carta se revisa antes de subirla
            answer = messagebox.askyesnocancel(self.APP_NAME, self.t("letter_not_previewed"), icon="warning",
                                               parent=self)
            if answer is None:
                return
            if answer:
                pending["previewed"] = True
                self.nb.select(1)
                self._open_as_pdf(lambda: pending["path"])
                return
        if not include_moreinfo and not self.need(self.documents, "need_documents"):
            return
        documents = [(d["path"], d["letter"]) for d in self.documents]
        needs_main = include_moreinfo or any(not is_letter for _, is_letter in documents)
        folder, letter_folders = self.prefs["folder"], list(self.prefs["letter_folders"])
        if (needs_main and not folder) or (not folder and not letter_folders):
            messagebox.showwarning(self.APP_NAME, self.t("no_folders"), parent=self)
            self.nb.select(2)
            return
        self.prefs["analyst"] = self.analyst_var.get().strip()
        self.save_prefs()
        shots = [item["shot"] for item in self.shots]
        p, excel, mode = dict(self.prefs), self.excel_var.get().strip() or None, self.mode.get()

        def work():
            return logic.create_package(case, p["analyst"], shots, documents, folder, letter_folders, mode, excel,
                                        p["base"] or logic.DEFAULT_BASE, p["use_word"], p["keep_docx"],
                                        include_moreinfo=include_moreinfo)

        self.run_task(work, self._created)

    def _created(self, r):
        t = self.t
        lines = [t("engine_" + r["engine"], sheet=logic.EXCEL_SHEET), ""] if r["engine"] else []
        lines += [t("created")] + [f"  • {name}" for name in r["names"]]
        lines += [t(note, name=name) for note, name in r["notes"]]
        if r["copied"]:
            lines += [t("copied_to")] + [f"  • {p}" for p in r["copied"]]
        if r["errors"]:
            lines += [t("copy_errors")] + [f"  • {folder}: {error}" for folder, error in r["errors"]]
        if r["kept"]:
            lines += ["", t("kept", folder=r["kept"])]
        self.result.set("\n".join(lines))
        self.last_output = r["copied"][0].parent if r["copied"] else r["kept"]
        (messagebox.showwarning if r["errors"] else messagebox.showinfo)(t("done_title"), "\n".join(lines),
                                                                         parent=self)

    def open_output(self):
        folder = self.last_output or self.prefs["folder"] or None
        if folder and Path(folder).is_dir():
            open_path(folder)

    # ------------------------------------------------------------ settings tab
    def _build_settings(self):
        outer = self.add_tab("tab_settings", padding=0)
        scroll = ScrollFrame(outer)
        scroll.pack(fill="both", expand=True)
        tab = ttk.Frame(scroll.inner, padding=12)
        tab.pack(fill="both", expand=True)
        main = self.lframe(tab, "main_folder", padding=8)
        main.pack(fill="x")
        self.folder_var = tk.StringVar(value=self.prefs["folder"])
        ttk.Entry(main, textvariable=self.folder_var).pack(side="left", fill="x", expand=True)
        self.btn(main, "browse", self.pick_main_folder).pack(side="left", padx=6)
        self.folder_var.trace_add("write", lambda *a: self._set_main_folder())
        box = self.lframe(tab, "letter_folders", padding=8)
        box.pack(fill="x", pady=(10, 0))
        self.folder_list = tk.Listbox(box, height=3)
        self.folder_list.pack(side="left", fill="x", expand=True)
        fb = ttk.Frame(box)
        fb.pack(side="left", padx=6)
        self.btn(fb, "add_folder", self.add_folder).pack(fill="x")
        self.btn(fb, "add_path", self.add_path).pack(fill="x", pady=4)
        self.btn(fb, "remove", self.remove_folder).pack(fill="x")
        self.lbl(tab, "letter_folders_hint", hint=True).pack(anchor="w")
        self._fill_folders()

        sections = self.lframe(tab, "sections_box", padding=8)
        sections.pack(fill="x", pady=(10, 0))
        self.section_list = tk.Listbox(sections, height=6)
        self.section_list.pack(side="left", fill="x", expand=True)
        sb = ttk.Frame(sections)
        sb.pack(side="left", padx=6)
        self.btn(sb, "section_add", self.add_section).pack(fill="x")
        self.btn(sb, "section_rename", self.rename_section).pack(fill="x", pady=4)
        self.btn(sb, "remove", self.remove_section).pack(fill="x")
        moves = ttk.Frame(sb)
        moves.pack(fill="x", pady=(4, 0))
        self.btn(moves, "up", lambda: self.move_section(-1), width=3).pack(side="left", expand=True, fill="x")
        self.btn(moves, "down", lambda: self.move_section(1), width=3).pack(side="left", expand=True, fill="x")
        self.lbl(tab, "sections_hint", hint=True).pack(anchor="w")
        self._fill_sections()

        opts = ttk.Frame(tab)
        opts.pack(fill="x", pady=10)
        self.use_word_var = tk.BooleanVar(value=self.prefs["use_word"])
        self.keep_docx_var = tk.BooleanVar(value=self.prefs["keep_docx"])
        for key, var in (("use_word", self.use_word_var), ("keep_docx", self.keep_docx_var)):
            self.chk(opts, key, var).pack(anchor="w", pady=2)
        form = ttk.Frame(tab)
        form.pack(fill="x")
        form.columnconfigure(1, weight=1)
        self.base_var = tk.StringVar(value=self.prefs["base"])
        self.field(form, "base_name", ttk.Entry(form, textvariable=self.base_var, width=20), 0, sticky="w")
        self.btn(tab, "save_settings", self.save_settings, accent=True).pack(anchor="w", pady=10)

    # ------------------------------------------------------------ sections (saved, defined by the user)
    def _fill_sections(self, select=None):
        names = self.prefs["sections"]
        self.section_list.delete(0, "end")
        for name in names:
            self.section_list.insert("end", name)
        current = self.section.get()
        self.section["values"] = names
        if select in names:
            self.section.set(select)
        elif current not in names:
            self.section.set(names[0] if names else "")
        if select in names:
            self.section_list.selection_set(names.index(select))

    def _ask_section(self, initial=""):
        name = simpledialog.askstring(self.APP_NAME, self.t("section_prompt"), initialvalue=initial, parent=self)
        name = " ".join((name or "").split())
        if name and name.lower() in {s.lower() for s in self.prefs["sections"]} and name != initial:
            messagebox.showwarning(self.APP_NAME, self.t("section_exists", name=name), parent=self)
            return None
        return name or None

    def add_section(self):
        name = self._ask_section()
        if not name:
            return False
        self.prefs["sections"].append(name)
        self.save_prefs()
        self._fill_sections(select=name)
        return True

    def _selected_section(self):
        sel = self.section_list.curselection()
        if not sel:
            messagebox.showinfo(self.APP_NAME, self.t("need_section_selection"), parent=self)
            return None
        return sel[0]

    def rename_section(self):
        index = self._selected_section()
        if index is None:
            return
        old = self.prefs["sections"][index]
        new = self._ask_section(old)
        if not new or new == old:
            return
        self.prefs["sections"][index] = new
        for item in self.shots:  # las capturas ya añadidas cambian de nombre de sección también
            if item["shot"].section == old:
                item["shot"].section = new
        self.save_prefs()
        self._fill_sections(select=new)
        self._fill()

    def remove_section(self):
        index = self._selected_section()
        if index is None:
            return
        name = self.prefs["sections"][index]
        if any(item["shot"].section == name for item in self.shots):
            messagebox.showwarning(self.APP_NAME, self.t("section_in_use", name=name), parent=self)
            return
        del self.prefs["sections"][index]
        self.save_prefs()
        self._fill_sections()

    def move_section(self, step):
        index = self._selected_section()
        names = self.prefs["sections"]
        if index is None or not 0 <= index + step < len(names):
            return
        names[index], names[index + step] = names[index + step], names[index]
        self.save_prefs()
        self._fill_sections(select=names[index + step])
        self._fill()

    def pick_main_folder(self):
        folder = filedialog.askdirectory(parent=self)
        if folder:
            self.folder_var.set(folder)

    def _set_main_folder(self):
        self.prefs["folder"] = self.folder_var.get().strip()
        self.save_prefs()

    def _fill_folders(self):
        self.folder_list.delete(0, "end")
        for folder in self.prefs["letter_folders"]:
            note = "" if Path(folder).is_dir() else f"   {self.t('folder_missing')}"
            self.folder_list.insert("end", folder + note)

    def _add(self, folder):
        folder = (folder or "").strip()
        if folder and folder not in self.prefs["letter_folders"]:
            self.prefs["letter_folders"].append(folder)
            self.save_prefs()
            self._fill_folders()

    def add_folder(self):
        self._add(filedialog.askdirectory(parent=self))

    def add_path(self):
        self._add(simpledialog.askstring(self.APP_NAME, self.t("path_prompt"), parent=self))

    def remove_folder(self):
        for index in reversed(self.folder_list.curselection()):
            del self.prefs["letter_folders"][index]
        self.save_prefs()
        self._fill_folders()

    def save_settings(self):
        base = logic.clean_case(self.base_var.get()) or logic.DEFAULT_BASE
        self.prefs.update(use_word=bool(self.use_word_var.get()),
                          keep_docx=bool(self.keep_docx_var.get()), base=base)
        self.base_var.set(base)
        self.save_prefs()
        self.status(self.t("settings_saved"))


class LetterDialog(tk.Toplevel):
    """Form generated from the template's fields (text, drop-downs, dates). One box per field name: a value that
    appears several times in the letter (for example the customer name) is typed only once. «Preview» builds the
    PDF exactly as it will be uploaded so the analyst can check it first."""

    def __init__(self, app, template, fields, values=None):
        super().__init__(app)
        self.app, self.template, self.fields, self.widgets = app, template, fields, {}
        self.more, self.add_buttons = {}, {}  # campos con varios valores: entradas extra y botón «＋»
        self.previewed = None
        self.title(f"{app.t('letter_title')} – {template['name']}")
        self.transient(app)
        self.geometry(f"{int(660 * app.scale)}x{int(580 * app.scale)}")
        ttk.Label(self, text=f"{app.t('template')}: {template['name']}", style="Title.TLabel").pack(
            anchor="w", padx=14, pady=(12, 0))
        ttk.Label(self, text=app.t("letter_intro"), style="Hint.TLabel", wraplength=int(620 * app.scale),
                  justify="left").pack(anchor="w", padx=14, pady=(4, 4))
        bar = ttk.Frame(self, padding=14)
        bar.pack(side="bottom", fill="x")
        ttk.Button(bar, text=app.t("cancel"), command=self.destroy).pack(side="right")
        ttk.Button(bar, text=app.t("letter_add"), style="Accent.TButton", command=self.accept).pack(side="right",
                                                                                                    padx=8)
        ttk.Button(bar, text=app.t("letter_preview"), command=self.preview).pack(side="left")
        scroll = ScrollFrame(self)
        scroll.pack(fill="both", expand=True, padx=14)
        form = scroll.inner
        form.columnconfigure(1, weight=1)
        case, analyst = app.case_var.get().strip(), app.analyst_var.get().strip()
        language = letter.language(app._template_file(template))
        self.address_roles = letter.address_roles(fields)
        self.address_entry = None
        row = -1
        for f in fields:
            row += 1
            if self.address_entry is None and f.key in self.address_roles.values():
                self._address_row(form, row)  # la dirección completa en una línea, antes de sus campos
                row += 1
            label = f.label + (f"  (×{f.count})" if f.count > 1 else "")
            ttk.Label(form, text=label).grid(row=row, column=0, sticky="nw" if f.multi else "w", padx=(0, 10),
                                             pady=(10 if f.multi else 4, 4))
            value, lower = (values or {}).get(f.key, f.value), f.label.lower()
            if not value and any(w in lower for w in ("case", "claim", "dossier", "réclamation")) and case:
                value = case
            elif not value and any(w in lower for w in ("analyst", "analyste")) and analyst:
                value = analyst
            elif not value and f.kind == "date":
                value = letter.today(language)
            if not f.multi:
                widget = self._input(form, f, value)
                widget.grid(row=row, column=1, sticky="ew", pady=4, padx=(0, 6))
                self.widgets[f.key] = widget
                continue
            # varios valores (p. ej. varias razones): una línea por valor y «＋ Add another»
            box = ttk.Frame(form)
            box.grid(row=row, column=1, sticky="ew", pady=4, padx=(0, 6))
            box.columnconfigure(0, weight=1)
            items = letter.unique(value if isinstance(value, (list, tuple)) else [value]) or [""]
            self.widgets[f.key] = self._input(box, f, items[0])
            self.widgets[f.key].grid(row=0, column=0, sticky="ew")
            self._no_repeats(f, self.widgets[f.key])
            self.more[f.key] = []
            add = ttk.Button(box, text=app.t("letter_add_more"), style="Toolbutton",
                             command=lambda f=f, box=box: self.add_value(f, box))
            self.add_buttons[f.key] = add
            for item in items[1:]:
                self.add_value(f, box, item)
            self._place_add(f.key)

    # ------------------------------------------------ full address on one line
    def _address_row(self, form, row):
        t = self.app.t
        ttk.Label(form, text=t("full_address"), font=("Segoe UI", 10, "bold")).grid(row=row, column=0, sticky="nw",
                                                                                   padx=(0, 10), pady=(8, 4))
        box = ttk.Frame(form)
        box.grid(row=row, column=1, sticky="ew", pady=(4, 8), padx=(0, 6))
        box.columnconfigure(0, weight=1)
        self.address_entry = ttk.Entry(box)
        self.address_entry.grid(row=0, column=0, sticky="ew")
        ttk.Button(box, text=t("address_fill"), command=self.fill_address).grid(row=0, column=1, padx=(6, 0))
        self.address_hint = ttk.Label(box, text=t("address_hint"), style="Hint.TLabel", justify="left",
                                      wraplength=int(520 * self.app.scale))
        self.address_hint.grid(row=1, column=0, columnspan=2, sticky="w", pady=(2, 0))
        self.address_entry.bind("<Return>", lambda e: self.fill_address())
        self.address_entry.bind("<<Paste>>", lambda e: self.after_idle(self.fill_address))

    def fill_address(self, text=None):
        """Splits the address typed on one line and fills each address field of the template."""
        t = self.app.t
        text = self.address_entry.get() if text is None else text
        if not text.strip():
            return {}
        found = letter.address_values(text, self.fields)
        for key in self.address_roles.values():  # lo que no se encuentra se vacía (no quedan datos anteriores)
            widget, value = self.widgets[key], found.get(key, "")
            if isinstance(widget, ttk.Combobox):
                widget.set(value)
            else:
                widget.delete(0, "end")
                widget.insert(0, value)
        names = ", ".join(f.label for f in self.fields if f.key in found)  # en el orden de la plantilla
        optional = self.address_roles.get("line2")  # la línea 2 (apto., suite) es opcional: no se pide
        missing = [f.label for f in self.fields
                   if f.key in self.address_roles.values() and f.key not in found and f.key != optional]
        if len(found) < 2:
            self.address_hint.configure(text=t("address_bad"))
        elif missing:
            self.address_hint.configure(text=t("address_missing", names=names, missing=", ".join(missing)))
        else:
            self.address_hint.configure(text=t("address_filled", names=names))
        postal = found.get(self.address_roles.get("postal"), "")
        if postal and not letter.valid_postal(postal) and not postal[:1].isdigit():
            self.address_hint.configure(text=self.address_hint.cget("text") + " " + t("address_postal_check",
                                                                                     postal=postal))
        return found

    # ------------------------------------------------ several values (reasons)
    def _all(self, key):
        return [self.widgets[key]] + self.more.get(key, [])

    def available(self, f, widget):
        """Options still free for this line: a reason already chosen on another line cannot be chosen again."""
        taken = {w.get().strip() for w in self._all(f.key) if w is not widget}
        return [o for o in f.options if o not in taken]

    def _no_repeats(self, f, widget):
        if isinstance(widget, ttk.Combobox):
            widget.configure(postcommand=lambda: widget.configure(values=self.available(f, widget)))
            widget.bind("<<ComboboxSelected>>", lambda e: self._place_add(f.key), add="+")

    def _input(self, parent, f, value=""):
        if f.kind in ("dropdown", "combo"):
            widget = ttk.Combobox(parent, values=f.options, state="readonly" if f.kind == "dropdown" else "normal")
            widget.set(value if value in f.options or f.kind == "combo" else "")
        else:
            widget = ttk.Entry(parent)
            widget.insert(0, value)
        return widget

    def add_value(self, f, box, value=""):
        """Another value for the same field (another reason): it becomes one more item or bullet in the letter."""
        if f.options and len(self._all(f.key)) >= len(f.options):
            return None  # ya están todas las opciones
        row = ttk.Frame(box)
        row.columnconfigure(0, weight=1)
        widget = self._input(row, f, value)
        widget.grid(row=0, column=0, sticky="ew")
        self._no_repeats(f, widget)
        ttk.Button(row, text="✕", width=3, command=lambda: self.remove_value(f.key, row, widget)).grid(
            row=0, column=1, padx=(4, 0))
        self.more[f.key].append(widget)
        row.grid(row=len(self.more[f.key]), column=0, sticky="ew", pady=(4, 0))
        self._place_add(f.key)
        return widget

    def remove_value(self, key, row, widget):
        self.more[key].remove(widget)
        row.destroy()
        for n, other in enumerate(self.more[key], start=1):
            other.master.grid(row=n)
        self._place_add(key)

    def _place_add(self, key):
        button = self.add_buttons[key]
        button.grid(row=len(self.more[key]) + 1, column=0, sticky="w", pady=(4, 0))
        field = next(f for f in self.fields if f.key == key)
        full = bool(field.options) and len(self._all(key)) >= len(field.options)
        button.state(["disabled"] if full else ["!disabled"])

    def values(self):
        values = {key: widget.get().strip() for key, widget in self.widgets.items()}
        for key in self.more:
            values[key] = letter.unique(w.get().strip() for w in self._all(key))
        return values

    def filled(self):
        return {k: v for k, v in self.values().items() if v}

    def preview(self):
        self.previewed = self.filled()
        self.app.preview_letter(self.template, self.previewed)

    def accept(self):
        values = self.values()
        missing = [f.label for f in self.fields if not values.get(f.key)]
        if missing and not messagebox.askyesno(self.app.APP_NAME, self.app.t("letter_missing",
                                                                            names=", ".join(missing)), parent=self):
            return
        self.app.letter_ready(self.template, self.filled(), previewed=self.previewed == self.filled())
        self.destroy()


def main():
    MoreInfoPilot().mainloop()
