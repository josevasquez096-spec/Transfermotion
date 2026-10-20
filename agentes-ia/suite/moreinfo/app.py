"""MoreInfo Pilot: puts the screenshots of a fraud claim into CASE,MOREINFO.pdf (or a new Excel tab) and saves
it to the folders the analyst configures. English only."""

import hashlib
import json
import tkinter as tk
from datetime import datetime
from pathlib import Path
from tkinter import filedialog, messagebox, simpledialog, ttk

from PIL import Image

from ..ui import Choice, PilotApp, TextBox, open_path
from . import logic
from .strings import STRINGS

DEFAULTS = {"folders": [], "per_case": False, "use_word": True, "keep_docx": False, "base": logic.DEFAULT_BASE,
            "sheet": "MoreInfo", "work": "", "analyst": ""}
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
        if not self.prefs["work"]:
            self.prefs["work"] = str(Path.home() / "Documents" / "MoreInfo")
        self.shots = []
        self.extras = []
        self._thumb = None
        self._last_clip = None
        self.last_output = None
        self._build_package()
        self._build_settings()
        self.bind_all("<Control-v>", self._ctrl_v)
        self.after(POLL_MS, self._poll_clipboard)
        for fn in list(self._i18n):  # vuelve a pintar la cabecera en inglés
            fn()

    def set_lang(self, lang):
        pass

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
        extras = self.lframe(tab, "extras", padding=6)
        extras.pack(side="bottom", fill="x", pady=(8, 0))
        self.extra_list = tk.Listbox(extras, height=2)
        self.extra_list.pack(side="left", fill="x", expand=True)
        eb = ttk.Frame(extras)
        eb.pack(side="left", padx=6)
        self.btn(eb, "add_files", self.add_extras).pack(fill="x")
        self.btn(eb, "remove", self.remove_extra).pack(fill="x", pady=(4, 0))

        panes = ttk.PanedWindow(tab, orient="horizontal")
        panes.pack(fill="both", expand=True)
        left = self.lframe(panes, "screenshots", padding=6)
        panes.add(left, weight=3)
        bar = ttk.Frame(left)
        bar.pack(fill="x")
        self.lbl(bar, "section").pack(side="left")
        self.section = Choice(self, bar, logic.SECTIONS, width=20, translate=False)
        self.section.pack(side="left", padx=6)
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
        if excel and self.section.key == "Transactions":
            self.section.set_key("Profile")

    def pick_excel(self):
        path = filedialog.askopenfilename(parent=self, filetypes=[("Excel", "*.xlsx *.xlsm *.xls"),
                                                                  (self.t("ft_all"), "*.*")])
        if path:
            self.excel_var.set(path)

    def _store(self, image):
        folder = Path(self.prefs["work"]) / "_screenshots"
        folder.mkdir(parents=True, exist_ok=True)
        path = folder / f"{datetime.now():%Y%m%d_%H%M%S_%f}.png"
        image.convert("RGB").save(path)
        return path

    def add_shot(self, path, section=None):
        with Image.open(path) as img:
            size = f"{img.width}×{img.height}"
        self.shots.append({"shot": logic.Shot(section or self.section.key, str(path)), "size": size})
        self._fill()

    def _fill(self, select=None):
        self.tree.delete(*self.tree.get_children())
        # se mantienen juntas las capturas de cada sección, en el orden de SECTIONS
        order = {s: n for n, s in enumerate(logic.SECTIONS)}
        self.shots.sort(key=lambda x: order.get(x["shot"].section, 99))
        for n, item in enumerate(self.shots):
            shot = item["shot"]
            self.tree.insert("", "end", iid=str(n), values=(n + 1, shot.section, shot.caption, item["size"]))
        if select is not None and 0 <= select < len(self.shots):
            self.tree.selection_set(str(select))
            self.tree.see(str(select))
        self.show_preview()

    def paste(self):
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
        self.status(self.t("added_n", n=len(images), section=self.section.key))

    def _ctrl_v(self, event):
        if isinstance(event.widget, (tk.Entry, ttk.Entry, tk.Text)):
            return None  # pegar texto normal en los campos
        self.paste()
        return "break"

    @staticmethod
    def _fingerprint(image):
        return hashlib.md5(image.convert("RGB").resize((64, 64)).tobytes()).hexdigest()

    def _poll_clipboard(self):
        """Con «Auto-add», cada captura nueva del portapapeles se añade sola a la sección elegida."""
        try:
            if self.auto_var.get():
                images = grab_clipboard()
                if images:
                    mark = self._fingerprint(images[-1])
                    if self._last_clip is None:
                        self._last_clip = mark  # lo que ya estaba al activar no se añade
                    elif mark != self._last_clip:
                        self._last_clip = mark
                        for image in images:
                            self.add_shot(self._store(image))
                        self.status(self.t("added_n", n=len(images), section=self.section.key))
            else:
                self._last_clip = None
        except Exception:  # el portapapeles puede estar ocupado por otro programa
            pass
        self.after(POLL_MS, self._poll_clipboard)

    def add_images(self):
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

    def add_extras(self):
        for path in filedialog.askopenfilenames(parent=self):
            self.extras.append(path)
            self.extra_list.insert("end", Path(path).name)

    def remove_extra(self):
        for index in reversed(self.extra_list.curselection()):
            del self.extras[index]
            self.extra_list.delete(index)

    def new_case(self):
        if (self.shots or self.extras) and not messagebox.askyesno(self.APP_NAME, self.t("new_case_confirm"),
                                                                   parent=self):
            return
        self.shots, self.extras = [], []
        self.extra_list.delete(0, "end")
        self.case_var.set("")
        self.excel_var.set("")
        self.result.set("")
        self._fill()

    def create(self):
        case = logic.clean_case(self.case_var.get())
        mode = self.mode.get()
        if not self.need(case, "need_case"):
            return
        if mode == "excel" and not self.need(self.excel_var.get().strip(), "need_excel"):
            return
        if mode == "pdf" and not self.need(self.shots, "need_shots"):
            return
        folders = list(self.prefs["folders"])
        if not folders and not messagebox.askyesno(self.APP_NAME, self.t("no_folders"), parent=self):
            return
        self.prefs["analyst"] = self.analyst_var.get().strip()
        self.save_prefs()
        shots, extras = [item["shot"] for item in self.shots], list(self.extras)
        p, excel = dict(self.prefs), self.excel_var.get().strip() or None

        def work():
            return logic.create_package(case, p["analyst"], shots, extras, folders, p["work"], mode, excel,
                                        p["base"] or logic.DEFAULT_BASE, p["per_case"], p["use_word"],
                                        p["keep_docx"], p["sheet"] or "MoreInfo")

        self.run_task(work, self._created)

    def _created(self, r):
        t = self.t
        lines = [t("engine_" + r["engine"], sheet=self.prefs["sheet"]), "", t("created")]
        lines += [f"  • {p}" for p in r["created"]]
        if r["copied"]:
            lines += [t("copied_to")] + [f"  • {p}" for p in r["copied"]]
        elif not self.prefs["folders"]:
            lines.append(t("only_local"))
        if r["errors"]:
            lines += [t("copy_errors")] + [f"  • {folder}: {error}" for folder, error in r["errors"]]
        self.result.set("\n".join(lines))
        self.last_output = r["created"][0].parent
        (messagebox.showwarning if r["errors"] else messagebox.showinfo)(t("done_title"), "\n".join(lines),
                                                                         parent=self)

    def open_output(self):
        folder = self.last_output or Path(self.prefs["work"])
        Path(folder).mkdir(parents=True, exist_ok=True)
        open_path(folder)

    # ------------------------------------------------------------ settings tab
    def _build_settings(self):
        tab = self.add_tab("tab_settings", padding=12)
        box = self.lframe(tab, "dest_folders", padding=8)
        box.pack(fill="x")
        self.folder_list = tk.Listbox(box, height=6)
        self.folder_list.pack(side="left", fill="x", expand=True)
        fb = ttk.Frame(box)
        fb.pack(side="left", padx=6)
        self.btn(fb, "add_folder", self.add_folder).pack(fill="x")
        self.btn(fb, "add_path", self.add_path).pack(fill="x", pady=4)
        self.btn(fb, "remove", self.remove_folder).pack(fill="x")
        self._fill_folders()

        opts = ttk.Frame(tab)
        opts.pack(fill="x", pady=10)
        self.per_case_var = tk.BooleanVar(value=self.prefs["per_case"])
        self.use_word_var = tk.BooleanVar(value=self.prefs["use_word"])
        self.keep_docx_var = tk.BooleanVar(value=self.prefs["keep_docx"])
        for key, var in (("per_case", self.per_case_var), ("use_word", self.use_word_var),
                         ("keep_docx", self.keep_docx_var)):
            self.chk(opts, key, var).pack(anchor="w", pady=2)
        form = ttk.Frame(tab)
        form.pack(fill="x")
        form.columnconfigure(1, weight=1)
        self.base_var = tk.StringVar(value=self.prefs["base"])
        self.sheet_var = tk.StringVar(value=self.prefs["sheet"])
        self.work_var = tk.StringVar(value=self.prefs["work"])
        self.field(form, "base_name", ttk.Entry(form, textvariable=self.base_var, width=20), 0, sticky="w")
        self.field(form, "sheet_name", ttk.Entry(form, textvariable=self.sheet_var, width=20), 1, sticky="w")
        self.field(form, "work_folder", ttk.Entry(form, textvariable=self.work_var), 2)
        self.btn(tab, "save_settings", self.save_settings, accent=True).pack(anchor="w", pady=10)

    def _fill_folders(self):
        self.folder_list.delete(0, "end")
        for folder in self.prefs["folders"]:
            note = "" if Path(folder).is_dir() else f"   {self.t('folder_missing')}"
            self.folder_list.insert("end", folder + note)

    def _add(self, folder):
        folder = (folder or "").strip()
        if folder and folder not in self.prefs["folders"]:
            self.prefs["folders"].append(folder)
            self.save_prefs()
            self._fill_folders()

    def add_folder(self):
        self._add(filedialog.askdirectory(parent=self))

    def add_path(self):
        self._add(simpledialog.askstring(self.APP_NAME, self.t("path_prompt"), parent=self))

    def remove_folder(self):
        for index in reversed(self.folder_list.curselection()):
            del self.prefs["folders"][index]
        self.save_prefs()
        self._fill_folders()

    def save_settings(self):
        base = logic.clean_case(self.base_var.get()) or logic.DEFAULT_BASE
        self.prefs.update(per_case=bool(self.per_case_var.get()), use_word=bool(self.use_word_var.get()),
                          keep_docx=bool(self.keep_docx_var.get()), base=base,
                          sheet=self.sheet_var.get().strip()[:31] or "MoreInfo",
                          work=self.work_var.get().strip() or self.prefs["work"])
        self.base_var.set(base)
        self.save_prefs()
        self.status(self.t("settings_saved"))


def main():
    MoreInfoPilot().mainloop()
