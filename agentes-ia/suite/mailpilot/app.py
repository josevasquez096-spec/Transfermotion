"""MailPilot: agente para Outlook. Carpetas y buzones, búsqueda avanzada, etiquetas, reglas, redacción en inglés
y análisis de seguridad. Funciona sin internet con Outlook clásico; la IA (✨) es opcional."""

import re
import sys
import threading
import tkinter as tk
import traceback
from datetime import datetime, timedelta
from tkinter import filedialog, messagebox, simpledialog, ttk

from ..docpilot.logic import readability_level, text_stats
from ..ui import Choice, DataTable, PilotApp, TextBox, open_path
from . import analysis, assist, detectors, english, rules
from .backend_base import SKIP_IN_MAILBOX, BackendError, Progress
from .backend_demo import DRAFTS, EXTRA_SHARED, DemoBackend
from .edits import diff_changes
from .model import PICKER_COLORS
from .phrases import PHRASES, TEMPLATES
from .prefs import Prefs
from .query import Query, QueryError
from .strings import HELP, STRINGS
from .widgets import CategoryDialog, FolderDialog, MessageList, Preview, ResultDialog, swatch, tk_index

PERIODS = {"p7": 7, "p30": 30, "p90": 90, "p365": 365, "pall": None}
SCOPES = ("sc_folder", "sc_subfolders", "sc_store", "sc_all")
RULE_SCOPES = ("sc_inbox", "sc_folder", "sc_store", "sc_all")
MAX_LIST = 2000
QUICK_FILTERS = (("qf_unread", "is:unread"), ("qf_attachment", "has:attachment"), ("qf_external", "is:external"),
                 ("qf_phishing", "is:phishing"), ("qf_card", "has:card"), ("qf_claim", "has:claim"),
                 ("qf_week", "newer:7d"))
BUILTIN_SEARCHES = (("ss_unread_claims", "has:claim is:unread"), ("ss_phishing", "is:phishing"),
                    ("ss_cards", "has:card OR has:iban"), ("ss_external_links", "is:external has:link"),
                    ("ss_big", "has:attachment size:>5mb"),
                    ("ss_chargebacks", "contracargo OR chargeback OR rétrofacturation"),
                    ("ss_flagged", "is:flagged"), ("ss_week", "newer:7d is:unread"))
KIND_COLORS = {"spelling": "#FDE2E1", "grammar": "#FFE3C2", "esl": "#FFE3C2", "punctuation": "#FFF4C2",
               "style": "#E1EDFF", "tone": "#F1E3FF", "clarity": "#E3F2E6"}
AUTO_CHECK_MS = 900


class MailPilot(PilotApp):
    APP_NAME = "MailPilot"
    ICON_TEXT = "MP"
    ACCENT = "#0F6CBD"
    STRINGS = STRINGS

    def build(self):
        self.prefs = Prefs.load(self.settings.data_dir() / "mailpilot.json")
        self.backend = None
        self.stores, self.folders, self.folder_index, self.categories = [], {}, {}, []
        self.current_folder = None
        self.search_query = None
        self.task_progress = None
        self.rules = [rules.MailRule.from_dict(d) for d in self.prefs["rules"] if isinstance(d, dict)]
        self.rule_index = None
        self.rule_folder = ("", "")
        self.rule_categories = []
        self.issues, self.ignored = [], set()
        self.draft = None
        self._check_job = None
        self._preview_token = 0
        self.an_rows, self.an_sheets, self.an_overview = [], [], None
        self.suggestions = []
        self._images = []
        self._build_mailbox()
        self._build_search()
        self._build_tags()
        self._build_rules()
        self._build_writing()
        self._build_analysis()
        self.tr_call(self._update_connection)
        threading.Thread(target=english.speller, args=("en",), daemon=True).start()  # carga el diccionario
        if self.prefs["backend"] == "demo":
            self.after_idle(self.connect_demo)
        elif self.prefs["backend"] == "outlook" and sys.platform == "win32":
            self.after(400, self.connect_outlook)

    def destroy(self):
        self.stop_task()
        if self.backend is not None:
            try:
                self.backend.close()
            except Exception:  # al cerrar no importa
                pass
        super().destroy()

    # ------------------------------------------------------------ utilidades
    def task(self, work, done=None, status_key="working"):
        """Operación con el buzón: en segundo plano con Outlook; al momento en la demostración (está en memoria)."""
        if self.backend is not None and self.backend.kind == "demo":
            try:
                result = work()
            except Exception as exc:
                self.show_error(exc, traceback.format_exc())
                return
            if done:
                done(result)
            return
        self.run_task(work, done, status_key)

    def show_error(self, exc, trace=None):
        for kind, prefix in ((BackendError, "mp_err_"), (QueryError, "q_err_")):
            if isinstance(exc, kind):
                key = prefix + exc.code
                text = self.t(key, detail=exc.detail) if key in self.t.table else f"{exc.code}: {exc.detail}"
                messagebox.showerror(self.t("error"), text, parent=self)
                return
        super().show_error(exc, trace)

    def watch(self, progress, key="mp_progress"):
        """Muestra en la barra de estado cuántos correos lleva revisados una operación larga."""
        self.task_progress = progress
        self.stop_buttons(True)

        def poll():
            if self.task_progress is not progress:
                return
            if self._busy:
                self.status(self.t(key, seen=progress.seen, found=progress.found))
                self.after(300, poll)
            else:
                self.task_progress = None
                self.stop_buttons(False)

        self.after(300, poll)

    def stop_buttons(self, active):
        for button in (self.stop_btn, self.an_stop_btn):
            button.state(["!disabled"] if active else ["disabled"])

    def stop_task(self):
        if self.task_progress is not None:
            self.task_progress.cancel.set()

    def since(self, key):
        days = PERIODS.get(key)
        return datetime.now() - timedelta(days=days) if days else None

    def internal_domains(self):
        own = [s.address.split("@")[-1].lower() for s in self.stores if s.kind == "primary" and "@" in s.address]
        own += [s.name.split("@")[-1].lower() for s in self.stores if s.kind == "primary" and "@" in s.name]
        return self.prefs.domains(fallback=list(dict.fromkeys(own)))

    def query_options(self):
        return {"whole_word": bool(self.whole_var.get()), "exact": bool(self.exact_var.get()),
                "dayfirst": self.t.lang != "en", "claim_pattern": self.prefs["claim_regex"]}

    def make_query(self, text, **extra):
        try:
            return Query(text, **{**self.query_options(), **extra})
        except QueryError as exc:
            self.show_error(exc)
            return None

    def connected(self):
        return self.need(self.backend is not None, "mp_need_connect")

    def store_of(self, folder_id):
        folder = self.folder_index.get(folder_id)
        return next((s for s in self.stores if folder and s.id == folder.store_id), None)

    def default_folder(self):
        primary = [s.id for s in self.stores if s.kind == "primary"] or [s.id for s in self.stores]
        for store_id in primary:
            for folder in self.folders.get(store_id, []):
                if folder.special == "inbox":
                    return folder.id
        for folders in self.folders.values():
            for folder in folders:
                if folder.depth > 0:
                    return folder.id
        return None

    def descendants(self, folder_id):
        out, pending = [], [folder_id]
        children = {}
        for folders in self.folders.values():
            for folder in folders:
                children.setdefault(folder.parent_id, []).append(folder.id)
        while pending:
            current = pending.pop()
            out.append(current)
            pending.extend(children.get(current, []))
        return out

    def scope_folders(self, key):
        """Carpetas donde buscar según el ámbito elegido (sin Eliminados, No deseado ni conflictos)."""
        folder_id = self.current_folder or self.default_folder()
        folder = self.folder_index.get(folder_id)
        if key in ("sc_folder", "sc_subfolders", "sc_inbox") and folder is None:
            return []
        if key == "sc_inbox":
            store_folders = self.folders.get(folder.store_id, [])
            return [f.id for f in store_folders if f.special == "inbox"] or [folder.id]
        if key == "sc_folder" and folder.depth > 0:
            return [folder.id]
        if key in ("sc_folder", "sc_subfolders"):
            return self.descendants(folder.id)
        stores = [folder.store_id] if key == "sc_store" and folder else [s.id for s in self.stores]
        return [f.id for sid in stores for f in self.folders.get(sid, []) if f.special not in SKIP_IN_MAILBOX]

    def ensure_category(self, name, color=9):
        if name.lower() not in {c.name.lower() for c in self.categories}:
            self.backend.create_category(name, color)
            self.categories = self.backend.categories()
            self._fill_categories()

    def _create_category_now(self, name, color):
        """Para el diálogo de etiquetas (que es modal): crea la etiqueta al momento."""
        try:
            self.backend.create_category(name, color)
            self.categories = self.backend.categories()
            self._fill_categories()
            return True
        except Exception as exc:
            self.show_error(exc)
            return False

    def popup(self, menu, widget):
        menu.tk_popup(widget.winfo_rootx(), widget.winfo_rooty() + widget.winfo_height())

    @staticmethod
    def place_sash(panes, ratio):
        """Coloca el divisor en esa proporción cuando el panel recibe su tamaño real (al mostrarse la pestaña)."""
        def apply(event):
            size = event.width if str(panes.cget("orient")) == "horizontal" else event.height
            if size > 200:
                panes.sashpos(0, int(size * ratio))
                panes.unbind("<Configure>", bind_id)

        bind_id = panes.bind("<Configure>", apply, add="+")

    # ------------------------------------------------------------ buzón y carpetas
    def _build_mailbox(self):
        tab = self.add_tab("tab_mailbox", padding=8)
        top = ttk.Frame(tab)
        top.pack(fill="x", pady=(0, 6))
        self.btn(top, "connect_outlook", self.connect_outlook, accent=True).pack(side="left")
        self.btn(top, "connect_demo", self.connect_demo).pack(side="left", padx=6)
        self.btn(top, "open_shared", self.open_shared).pack(side="left")
        self.conn_label = ttk.Label(top, style="Hint.TLabel")
        self.conn_label.pack(side="left", padx=12)

        panes = ttk.PanedWindow(tab, orient="horizontal")
        panes.pack(fill="both", expand=True)
        left = ttk.Frame(panes)
        panes.add(left, weight=1)
        bar = ttk.Frame(left)
        bar.pack(fill="x", pady=(0, 4))
        folder_btn = self.btn(bar, "folder_menu", lambda: self.popup(self.folder_menu(), folder_btn))
        folder_btn.pack(side="left")
        self.btn(bar, "refresh", self.refresh_all).pack(side="left", padx=4)
        self.tree = ttk.Treeview(left, show="tree", selectmode="browse")
        ys = ttk.Scrollbar(left, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=ys.set)
        ys.pack(side="right", fill="y")
        self.tree.pack(fill="both", expand=True)
        self.tree.bind("<<TreeviewSelect>>", lambda e: self.on_folder())
        self.tree.bind("<Button-3>", lambda e: self._tree_popup(e))

        right = ttk.PanedWindow(panes, orient="vertical")
        panes.add(right, weight=4)
        upper = ttk.Frame(right)
        right.add(upper, weight=3)
        bar = ttk.Frame(upper)
        bar.pack(fill="x", pady=(0, 4))
        self.lbl(bar, "period").pack(side="left")
        self.mail_period = Choice(self, bar, list(PERIODS), width=14, default=2)
        self.mail_period.pack(side="left", padx=(4, 12))
        self.mail_period.bind("<<ComboboxSelected>>", lambda e: self.load_folder(), add="+")
        actions = self.btn(bar, "actions", lambda: self.popup(self.actions_menu(self.mail_list), actions))
        actions.pack(side="left")
        self.btn(bar, "export_excel", lambda: self.export_list(self.mail_list)).pack(side="left", padx=6)
        self.mail_list = MessageList(upper, self, height=14, on_select=lambda m: self.show_preview(m, self.preview),
                                     on_open=self.open_message, menu=lambda: self.actions_menu(self.mail_list))
        self.mail_list.pack(fill="both", expand=True)
        self.preview = Preview(right, self)
        right.add(self.preview, weight=2)
        self.place_sash(panes, 0.24)

    def _update_connection(self):
        if self.backend is None:
            text = self.t("conn_off")
        elif self.backend.kind == "demo":
            text = self.t("conn_demo")
        else:
            text = self.t("conn_outlook", n=len(self.stores))
        self.conn_label.configure(text=text)

    def connect_outlook(self):
        if sys.platform != "win32":
            if messagebox.askyesno(self.APP_NAME, self.t("mp_no_windows"), parent=self):
                self.connect_demo()
            return
        from .backend_outlook import OutlookBackend

        shared = list(self.prefs["shared"])

        def work():
            backend = OutlookBackend()
            try:
                backend.connect()
                for address in shared:
                    try:
                        backend.open_shared(address)
                    except BackendError:
                        pass  # sin permiso o ya no existe: se sigue con el resto
            except BaseException:
                backend.close()
                raise
            return backend

        self.run_task(work, lambda backend: self._connected(backend, "outlook"), "mp_connecting")

    def connect_demo(self):
        backend = DemoBackend(self.t.lang)
        backend.connect()
        self._connected(backend, "demo")

    def _connected(self, backend, kind):
        old, self.backend = self.backend, backend
        if old is not None and old is not backend:
            try:
                old.close()
            except Exception:  # la conexión anterior ya no importa
                pass
        self.prefs["backend"] = kind
        self.prefs.save()
        self.current_folder = None
        self.mail_list.set([])
        self.preview.clear()
        self.refresh_all()

    def refresh_all(self, reload_list=True):
        if not self.connected():
            return
        backend = self.backend

        def work():
            stores = backend.stores()
            return stores, {s.id: backend.folders(s.id) for s in stores}, backend.categories()

        def done(result):
            self.stores, self.folders, self.categories = result
            self.folder_index = {f.id: f for folders in self.folders.values() for f in folders}
            if self.current_folder not in self.folder_index:
                self.current_folder = self.default_folder()
            self._fill_tree()
            self._fill_categories()
            self._update_connection()
            if not self.domains_var.get().strip():
                self.domains_var.set(", ".join(self.internal_domains()))
            if reload_list:
                self.load_folder()

        self.task(work, done, "mp_loading")

    def _fill_tree(self):
        tree = self.tree
        opened = set()
        pending = list(tree.get_children())
        while pending:
            iid = pending.pop()
            if tree.item(iid, "open"):
                opened.add(iid)
            pending.extend(tree.get_children(iid))
        tree.delete(*tree.get_children())
        tree.tag_configure("store", font=self.mail_list._bold)
        for store in self.stores:
            for folder in self.folders.get(store.id, []):
                parent = folder.parent_id if folder.depth and tree.exists(folder.parent_id) else ""
                label = store.name if folder.depth == 0 else folder.name
                if folder.unread:
                    label += f"  ({folder.unread})"
                is_open = folder.id in opened or folder.depth == 0 or folder.special == "inbox"
                tree.insert(parent, "end", iid=folder.id, text=label, open=is_open,
                            tags=("store",) if folder.depth == 0 else ())
        if self.current_folder and tree.exists(self.current_folder):
            tree.selection_set(self.current_folder)
            tree.see(self.current_folder)

    def on_folder(self):
        sel = self.tree.selection()
        if sel and sel[0] != self.current_folder:
            self.current_folder = sel[0]
            self.load_folder()

    def load_folder(self):
        folder_id = self.current_folder
        if self.backend is None or folder_id not in self.folder_index:
            return
        since = self.since(self.mail_period.key)

        def done(result):
            messages, truncated = result
            key = "mail_count_more" if truncated else "mail_count"
            self.mail_list.set(messages, self.t(key, n=len(messages), folder=self.folder_index[folder_id].path
                                                or self.folder_index[folder_id].name))
            self.preview.clear()

        self.task(lambda: self.backend.messages(folder_id, since, MAX_LIST), done, "mp_loading")

    def folder_menu(self):
        menu = tk.Menu(self, tearoff=False)
        for key, command in (("folder_new", self.folder_new), ("folder_rename", self.folder_rename),
                             ("folder_move", self.folder_move), ("folder_delete", self.folder_delete)):
            menu.add_command(label=self.t(key), command=command)
        return menu

    def _tree_popup(self, event):
        row = self.tree.identify_row(event.y)
        if row:
            self.tree.selection_set(row)
            self.folder_menu().tk_popup(event.x_root, event.y_root)

    def _selected_folder(self, editable=False):
        if not self.connected():
            return None
        folder = self.folder_index.get(self.current_folder)
        if not self.need(folder, "mp_need_folder"):
            return None
        if editable and (folder.depth == 0 or folder.special):
            messagebox.showwarning(self.APP_NAME, self.t("mp_err_folder_special", detail=folder.name), parent=self)
            return None
        return folder

    def folder_new(self):
        parent = self._selected_folder()
        if parent is None:
            return
        name = simpledialog.askstring(self.APP_NAME, self.t("folder_new_prompt", parent=parent.path or parent.name),
                                      parent=self)
        if name:
            self.task(lambda: self.backend.create_folder(parent.id, name),
                      lambda folder: self.refresh_all(reload_list=False))

    def folder_rename(self):
        folder = self._selected_folder(editable=True)
        if folder is None:
            return
        name = simpledialog.askstring(self.APP_NAME, self.t("folder_rename_prompt"), initialvalue=folder.name,
                                      parent=self)
        if name and name != folder.name:
            self.task(lambda: self.backend.rename_folder(folder.id, name), lambda _: self.refresh_all())

    def folder_move(self):
        folder = self._selected_folder(editable=True)
        if folder is None:
            return
        dest = FolderDialog(self, "folder_move", self.stores, self.folders, allow_root=True).result
        if not dest or dest == folder.id:
            return
        if self.folder_index[dest].store_id != folder.store_id:
            messagebox.showwarning(self.APP_NAME, self.t("folder_move_store"), parent=self)
            return
        self.task(lambda: self.backend.move_folder(folder.id, dest), lambda _: self.refresh_all())

    def folder_delete(self):
        folder = self._selected_folder(editable=True)
        if folder is None or not messagebox.askyesno(self.APP_NAME, self.t("folder_delete_confirm", name=folder.name),
                                                     parent=self):
            return
        self.task(lambda: self.backend.delete_folder(folder.id), lambda _: self.refresh_all())

    def open_shared(self):
        if not self.connected():
            return
        prompt = self.t("shared_prompt")
        if self.backend.kind == "demo":
            prompt += "\n" + self.t("shared_prompt_demo", address=EXTRA_SHARED)
        address = simpledialog.askstring(self.APP_NAME, prompt, parent=self)
        if not address:
            return
        address = address.strip()

        def done(store):
            if self.backend.kind == "outlook" and address not in self.prefs["shared"]:
                self.prefs["shared"].append(address)
                self.prefs.save()
            self.refresh_all(reload_list=False)
            self.status(self.t("shared_opened", name=store.name))

        self.task(lambda: self.backend.open_shared(address), done, "mp_connecting")

    # ------------------------------------------------------------ acciones sobre correos
    def actions_menu(self, mlist):
        menu = tk.Menu(self, tearoff=False)
        entries = (("act_move", self.act_move), ("act_tag", self.act_tag), None,
                   ("act_read", lambda m: self.act_read(m, True)), ("act_unread", lambda m: self.act_read(m, False)),
                   ("act_flag", lambda m: self.act_flag(m, True)), ("act_unflag", lambda m: self.act_flag(m, False)),
                   None, ("act_open", lambda m: self.open_message(self._picked(m)[0]) if self._picked(m) else None),
                   ("act_save_msg", self.act_save_msg), ("act_save_att", self.act_save_attachments), None,
                   ("act_summary_ai", self.act_summary), ("act_select_all", self.act_select_all), None,
                   ("act_delete", self.act_delete))
        for entry in entries:
            if entry is None:
                menu.add_separator()
            else:
                menu.add_command(label=self.t(entry[0]), command=lambda fn=entry[1]: fn(mlist))
        return menu

    def _picked(self, mlist):
        messages = mlist.selected()
        if not messages:
            messagebox.showwarning(self.APP_NAME, self.t("mp_need_selection"), parent=self)
        return messages

    def act_select_all(self, mlist):
        mlist.tree.selection_set(mlist.tree.get_children())

    def act_move(self, mlist):
        messages = self._picked(mlist)
        if not messages or not self.connected():
            return
        dest = FolderDialog(self, "act_move", self.stores, self.folders).result
        if not dest:
            return

        def done(n):
            mlist.remove(messages)
            self.status(self.t("moved_n", n=n, folder=self.folder_index[dest].path))
            self.refresh_all(reload_list=False)

        self.task(lambda: self.backend.move_messages(messages, dest), done)

    def act_tag(self, mlist):
        messages = self._picked(mlist)
        if not messages or not self.connected():
            return
        result = CategoryDialog(self, self.categories, messages, create=self._create_category_now).result
        if not result or not any(result):
            return
        add, remove = result

        def done(n):
            drop = {r.lower() for r in remove}
            for msg in messages:
                cats = [c for c in msg.categories if c.lower() not in drop]
                cats += [c for c in add if c.lower() not in {x.lower() for x in cats}]
                msg.categories = cats
            mlist.refresh()
            self.status(self.t("tagged_n", n=n))

        self.task(lambda: self.backend.set_categories(messages, add, remove), done)

    def act_read(self, mlist, read):
        messages = self._picked(mlist)
        if messages and self.connected():
            self.task(lambda: self.backend.mark_read(messages, read),
                      lambda n: self._updated(mlist, messages, "unread", not read))

    def act_flag(self, mlist, flagged):
        messages = self._picked(mlist)
        if messages and self.connected():
            self.task(lambda: self.backend.set_flag(messages, flagged),
                      lambda n: self._updated(mlist, messages, "flagged", flagged))

    def _updated(self, mlist, messages, attr, value):
        for msg in messages:
            setattr(msg, attr, value)
        mlist.refresh()
        self.status(self.t("updated_n", n=len(messages)))

    def act_delete(self, mlist):
        messages = self._picked(mlist)
        if not messages or not self.connected():
            return
        if not messagebox.askyesno(self.APP_NAME, self.t("delete_confirm", n=len(messages)), parent=self):
            return

        def done(n):
            mlist.remove(messages)
            self.status(self.t("deleted_n", n=n))
            self.refresh_all(reload_list=False)

        self.task(lambda: self.backend.delete_messages(messages), done)

    def open_message(self, msg):
        if not self.connected():
            return

        def done(opened):
            if not opened:
                self.info(self.t("open_demo"))

        self.task(lambda: self.backend.open_message(msg), done)

    def _save(self, mlist, method, empty_key):
        messages = self._picked(mlist)
        if not messages or not self.connected():
            return
        folder = filedialog.askdirectory(parent=self)
        if not folder:
            return

        def done(paths):
            if not paths:
                self.info(self.t(empty_key))
            elif messagebox.askyesno(self.APP_NAME, self.t("files_saved", n=len(paths), folder=folder), parent=self):
                open_path(folder)

        self.task(lambda: method(messages, folder), done)

    def act_save_msg(self, mlist):
        self._save(mlist, self.backend.save_messages if self.backend else None, "nothing_saved")

    def act_save_attachments(self, mlist):
        self._save(mlist, self.backend.save_attachments if self.backend else None, "no_attachments")

    def act_summary(self, mlist):
        messages = self._picked(mlist)
        if not messages or not self.connected():
            return
        msg = messages[0]
        backend, anon = self.backend, self.anonymizer()
        if anon:
            anon.add_known(msg.sender_name, "NAME")

        def work(ai):
            backend.details(msg)
            text = f"From: {msg.sender_name} <{msg.sender_email}>\nSubject: {msg.subject}\n\n{msg.body}"
            data = ai.ask_json(assist.SUMMARY_SYSTEM, anon.mask(text) if anon else text, assist.SUMMARY_SCHEMA,
                               max_tokens=6000)
            return assist.unmask_all(data, anon)

        def done(data):
            subject = msg.subject if msg.subject.lower().startswith("re:") else f"RE: {msg.subject}"
            ResultDialog(self, "summary_title", [
                ("summary", data["summary"], False, 5),
                ("actions_needed", "\n".join(f"• {a}" for a in data["actions"]), False, 5),
                ("suggested_reply", data["reply"], True, 10)],
                [("reply_to_writing", lambda d: self._reply_to_writing(d, subject, msg.sender_email)),
                 ("copy", lambda d: self.copy(d.value("suggested_reply")))])

        self.run_ai(work, done)

    def _reply_to_writing(self, dialog, subject, to):
        body = dialog.value("suggested_reply")
        dialog.destroy()
        self.set_draft(subject, body)
        self.draft = {"original": None, "subject": subject, "editable": False, "to": to}
        self.apply_btn.state(["disabled"])
        self.draft_label.configure(text="")
        self.nb.select(4)

    def export_list(self, mlist):
        if not self.need(mlist.messages, "no_data"):
            return
        path = self.ask_save("excel", "MailPilot.xlsx")
        if path:
            df = analysis.message_table(mlist.messages)
            analysis.export_excel(path, [(self.t("sheet_messages"), self._translated(df))])
            self.saved(path)

    def _translated(self, df):
        out = df.rename(columns=lambda c: self.t(c) if str(c).startswith("col_") else c)
        for col in out.columns:
            if out[col].dtype == bool:
                out[col] = out[col].map({True: self.t("yes"), False: self.t("no")})
        return out

    # ------------------------------------------------------------ vista previa
    def show_preview(self, messages, preview, query=None):
        if len(messages) != 1 or self.backend is None:
            preview.clear()
            return
        msg = messages[0]
        self._preview_token += 1
        token = self._preview_token
        internal = self.internal_domains()

        def done(_):
            if token == self._preview_token:
                preview.show(msg, query.highlights() if query else (), lambda: self.warnings_for(msg, internal))

        self.task(lambda: self.backend.details(msg, html=True), done, "mp_loading")

    def warnings_for(self, msg, internal):
        out = []
        score, flags = detectors.phishing_score(msg, msg.body or "", msg.html or "", internal)
        if score >= detectors.PHISHING_THRESHOLD:
            out.append(self.t("warn_phishing", score=score, level=self.t("risk_" + detectors.risk_level(score)),
                              signals=", ".join(self.t(f) for f in flags)))
        cards = detectors.find_cards(f"{msg.subject}\n{msg.body or ''}")
        if cards:
            out.append(self.t("warn_card", n=len(cards)))
        return out

    # ------------------------------------------------------------ buscar y filtrar
    def _build_search(self):
        tab = self.add_tab("tab_search", padding=8)
        row = ttk.Frame(tab)
        row.pack(fill="x")
        self.query_var = tk.StringVar()
        entry = ttk.Entry(row, textvariable=self.query_var, font=("Segoe UI", 11))
        entry.pack(side="left", fill="x", expand=True)
        entry.bind("<Return>", lambda e: self.run_search())
        self.btn(row, "search", self.run_search, accent=True).pack(side="left", padx=6)
        self.stop_btn = self.btn(row, "stop", self.stop_task)
        self.stop_btn.pack(side="left")
        self.stop_btn.state(["disabled"])
        self.btn(row, "syntax_help", self.show_help).pack(side="left", padx=(6, 0))

        opts = ttk.Frame(tab)
        opts.pack(fill="x", pady=(6, 0))
        self.lbl(opts, "scope").pack(side="left")
        self.scope = Choice(self, opts, SCOPES, width=24, default=2)
        self.scope.pack(side="left", padx=(4, 12))
        self.lbl(opts, "period").pack(side="left")
        self.search_period = Choice(self, opts, list(PERIODS), width=14, default=2)
        self.search_period.pack(side="left", padx=(4, 12))
        self.lbl(opts, "max_results").pack(side="left")
        self.limit_var = tk.StringVar(value="1000")
        ttk.Spinbox(opts, from_=50, to=50000, increment=50, width=7, textvariable=self.limit_var).pack(side="left",
                                                                                                     padx=4)
        checks = ttk.Frame(tab)
        checks.pack(fill="x", pady=4)
        self.whole_var, self.exact_var = tk.BooleanVar(value=False), tk.BooleanVar(value=False)
        self.chk(checks, "whole_word", self.whole_var).pack(side="left")
        self.chk(checks, "exact_match", self.exact_var).pack(side="left", padx=12)
        chips = ttk.Frame(tab)
        chips.pack(fill="x")
        self.lbl(chips, "quick_filters", hint=True).pack(side="left", padx=(0, 6))
        for key, text in QUICK_FILTERS:
            self.btn(chips, key, lambda q=text: self.add_filter(q)).pack(side="left", padx=2)
        saved = ttk.Frame(tab)
        saved.pack(fill="x", pady=6)
        self.lbl(saved, "saved_searches").pack(side="left")
        self.saved_combo = ttk.Combobox(saved, state="readonly", width=40)
        self.saved_combo.pack(side="left", padx=6)
        self.saved_combo.bind("<<ComboboxSelected>>", lambda e: self.use_saved())
        self.btn(saved, "save_search", self.save_search).pack(side="left")
        self.btn(saved, "delete_search", self.delete_search).pack(side="left", padx=6)
        self.tr_call(self._fill_saved)

        panes = ttk.PanedWindow(tab, orient="vertical")
        panes.pack(fill="both", expand=True)
        upper = ttk.Frame(panes)
        panes.add(upper, weight=3)
        bar = ttk.Frame(upper)
        bar.pack(fill="x", pady=(0, 4))
        actions = self.btn(bar, "actions", lambda: self.popup(self.actions_menu(self.search_list), actions))
        actions.pack(side="left")
        self.btn(bar, "export_excel", lambda: self.export_list(self.search_list)).pack(side="left", padx=6)
        self.btn(bar, "rule_from_search", self.rule_from_search).pack(side="left")
        self.search_list = MessageList(upper, self, folder_column=True, height=12,
                                       on_select=lambda m: self.show_preview(m, self.search_preview,
                                                                             self.search_query),
                                       on_open=self.open_message, menu=lambda: self.actions_menu(self.search_list))
        self.search_list.pack(fill="both", expand=True)
        self.search_list.tree.bind("<Control-a>", lambda e: self.act_select_all(self.search_list))
        self.search_preview = Preview(panes, self)
        panes.add(self.search_preview, weight=2)

    def add_filter(self, text):
        current = self.query_var.get().strip()
        if text not in current.split():
            self.query_var.set(f"{current} {text}".strip())

    def run_search(self):
        if not self.connected():
            return
        query = self.make_query(self.query_var.get())
        if query is None:
            return
        folder_ids = self.scope_folders(self.scope.key)
        if not self.need(folder_ids, "mp_need_folder"):
            return
        try:
            limit = max(1, int(self.limit_var.get()))
        except ValueError:
            limit = 1000
        since, internal, progress = self.since(self.search_period.key), self.internal_domains(), Progress()
        backend = self.backend

        def done(result):
            messages, truncated = result
            self.search_query = query
            key = "results_more" if truncated and not progress.cancel.is_set() else "results"
            if progress.cancel.is_set():
                key = "results_stopped"
            self.search_list.set(messages, self.t(key, n=len(messages), seen=progress.seen))
            self.search_preview.clear()

        self.task(lambda: backend.search(folder_ids, query, since, limit, internal, progress), done, "mp_searching")
        if self._busy:
            self.watch(progress)

    def show_help(self):
        win = tk.Toplevel(self)
        win.title(self.t("syntax_help"))
        win.transient(self)
        box = TextBox(win, height=30, readonly=True, width=96, font=("Consolas", 10))
        box.pack(fill="both", expand=True, padx=12, pady=12)
        box.set(HELP[self.t.lang])
        ttk.Button(win, text=self.t("close"), command=win.destroy).pack(pady=(0, 12))

    def _fill_saved(self):
        self.saved_items = [(self.t(key), query) for key, query in BUILTIN_SEARCHES]
        self.saved_items += [(f"★ {s['name']}", s["query"]) for s in self.prefs["saved_searches"]
                             if isinstance(s, dict) and s.get("name") and s.get("query")]
        self.saved_combo["values"] = [f"{name}   ·   {query}" for name, query in self.saved_items]

    def use_saved(self):
        index = self.saved_combo.current()
        if 0 <= index < len(self.saved_items):
            self.query_var.set(self.saved_items[index][1])

    def save_search(self):
        query = self.query_var.get().strip()
        if not self.need(query, "mp_need_query") or self.make_query(query) is None:
            return
        name = simpledialog.askstring(self.APP_NAME, self.t("save_search_prompt"), parent=self)
        if name:
            self.prefs["saved_searches"] = [s for s in self.prefs["saved_searches"] if s.get("name") != name]
            self.prefs["saved_searches"].append({"name": name.strip(), "query": query})
            self.prefs.save()
            self._fill_saved()

    def delete_search(self):
        index = self.saved_combo.current()
        builtin = len(BUILTIN_SEARCHES)
        if not self.need(index >= 0, "mp_need_saved"):
            return
        if index < builtin:
            messagebox.showwarning(self.APP_NAME, self.t("search_builtin"), parent=self)
            return
        del self.prefs["saved_searches"][index - builtin]
        self.prefs.save()
        self.saved_combo.set("")
        self._fill_saved()

    def rule_from_search(self):
        query = self.query_var.get().strip()
        if not self.need(query, "mp_need_query"):
            return
        self.new_rule(query=query)
        self.nb.select(3)

    # ------------------------------------------------------------ etiquetas
    def _build_tags(self):
        tab = self.add_tab("tab_tags", padding=8)
        panes = ttk.PanedWindow(tab, orient="horizontal")
        panes.pack(fill="both", expand=True)
        left = self.lframe(panes, "tags_list")
        panes.add(left, weight=1)
        bar = ttk.Frame(left)
        bar.pack(side="bottom", fill="x", pady=(6, 0))
        for n, (key, command) in enumerate((("tag_new", self.tag_new), ("tag_rename", self.tag_rename),
                                            ("tag_color", self.tag_color), ("tag_delete", self.tag_delete),
                                            ("tag_show", self.tag_show))):
            self.btn(bar, key, command).grid(row=n // 2, column=n % 2, sticky="ew", padx=2, pady=2)
        for col in range(2):
            bar.columnconfigure(col, weight=1)
        self.cat_tree = ttk.Treeview(left, show="tree", height=16, selectmode="browse")
        self.cat_tree.pack(fill="both", expand=True)
        self.place_sash(panes, 0.27)

        right = self.lframe(panes, "bulk_tag")
        panes.add(right, weight=3)
        form = ttk.Frame(right)
        form.pack(fill="x")
        form.columnconfigure(1, weight=1)
        self.bulk_cat = ttk.Combobox(form, state="readonly", width=30)
        self.field(form, "tag", self.bulk_cat, 0, sticky="w")
        self.bulk_query = ttk.Entry(form)
        self.field(form, "search_label", self.bulk_query, 1)
        scope_row = ttk.Frame(form)
        self.bulk_scope = Choice(self, scope_row, SCOPES, width=24, default=2)
        self.bulk_scope.pack(side="left")
        self.bulk_period = Choice(self, scope_row, list(PERIODS), width=14, default=2)
        self.bulk_period.pack(side="left", padx=8)
        self.field(form, "scope", scope_row, 2, sticky="w")
        bar = ttk.Frame(right)
        bar.pack(fill="x", pady=6)
        self.btn(bar, "preview_btn", self.bulk_preview).pack(side="left")
        self.btn(bar, "tag_apply", lambda: self.bulk_apply(True), accent=True).pack(side="left", padx=6)
        self.btn(bar, "tag_remove", lambda: self.bulk_apply(False)).pack(side="left")
        self.bulk_list = MessageList(right, self, folder_column=True, height=12)
        self.bulk_list.pack(fill="both", expand=True)
        self.lbl(right, "bulk_hint", hint=True, wraplength=700, justify="left").pack(anchor="w", pady=(4, 0))

    def _fill_categories(self):
        self.cat_tree.delete(*self.cat_tree.get_children())
        self._images = []
        for n, cat in enumerate(self.categories):
            image = swatch(self, cat.color)
            self._images.append(image)
            self.cat_tree.insert("", "end", iid=str(n), text=f"  {cat.name}", image=image)
        names = [c.name for c in self.categories]
        self.bulk_cat["values"] = names
        if names and self.bulk_cat.get() not in names:
            self.bulk_cat.current(0)

    def _selected_category(self):
        sel = self.cat_tree.selection()
        if not self.connected() or not self.need(sel, "mp_need_category"):
            return None
        return self.categories[int(sel[0])]

    def _ask_color(self, title_key, name=None, color=1):
        """Pequeño diálogo con nombre (opcional) y color. Devuelve (nombre, color) o None."""
        win = tk.Toplevel(self)
        win.title(self.t(title_key))
        win.transient(self)
        win.resizable(False, False)
        frame = ttk.Frame(win, padding=16)
        frame.pack()
        entry = None
        if name is not None:
            ttk.Label(frame, text=self.t("tag_name")).grid(row=0, column=0, sticky="w")
            entry = ttk.Entry(frame, width=30)
            entry.insert(0, name)
            entry.grid(row=0, column=1, pady=4)
        ttk.Label(frame, text=self.t("tag_color_label")).grid(row=1, column=0, sticky="w", padx=(0, 8))
        colors = ttk.Combobox(frame, state="readonly", width=28, values=[self.t(k) for k, _ in PICKER_COLORS])
        codes = [c for _, c in PICKER_COLORS]
        colors.current(codes.index(color) if color in codes else 0)
        colors.grid(row=1, column=1, pady=4)
        result = {}

        def accept():
            value = entry.get().strip() if entry is not None else ""
            if entry is not None and not value:
                return
            result["value"] = (value, codes[colors.current()])
            win.destroy()

        buttons = ttk.Frame(frame)
        buttons.grid(row=2, column=0, columnspan=2, sticky="e", pady=(10, 0))
        ttk.Button(buttons, text=self.t("cancel"), command=win.destroy).pack(side="right")
        ttk.Button(buttons, text=self.t("ok"), style="Accent.TButton", command=accept).pack(side="right", padx=8)
        win.grab_set()
        (entry or colors).focus_set()
        self.wait_window(win)
        return result.get("value")

    def _reload_categories(self, _=None):
        self.task(self.backend.categories, lambda cats: (setattr(self, "categories", cats), self._fill_categories()))

    def tag_new(self):
        if not self.connected():
            return
        answer = self._ask_color("tag_new", name="")
        if answer:
            self.task(lambda: self.backend.create_category(*answer), self._reload_categories)

    def tag_color(self):
        cat = self._selected_category()
        if cat is None:
            return
        answer = self._ask_color("tag_color", color=cat.color)
        if answer:
            self.task(lambda: self.backend.update_category(cat.name, color=answer[1]), self._reload_categories)

    def tag_rename(self):
        cat = self._selected_category()
        if cat is None:
            return
        new = simpledialog.askstring(self.APP_NAME, self.t("tag_rename_prompt"), initialvalue=cat.name, parent=self)
        if not new or new.strip() == cat.name:
            return
        new = new.strip()
        retag = messagebox.askyesno(self.APP_NAME, self.t("tag_retag_confirm", old=cat.name, new=new), parent=self)

        def done(_):
            self._reload_categories()
            if retag:
                self._retag(cat.name, [new])

        self.task(lambda: self.backend.update_category(cat.name, new_name=new), done)

    def tag_delete(self):
        cat = self._selected_category()
        if cat is None or not messagebox.askyesno(self.APP_NAME, self.t("tag_delete_confirm", name=cat.name),
                                                  parent=self):
            return
        untag = messagebox.askyesno(self.APP_NAME, self.t("tag_untag_confirm", name=cat.name), parent=self)

        def done(_):
            self._reload_categories()
            if untag:
                self._retag(cat.name, [])

        self.task(lambda: self.backend.delete_category(cat.name), done)

    def _retag(self, old, new):
        """Cambia una etiqueta por otra (o la quita) en los correos de todos los buzones conectados."""
        query = self.make_query(f'category:"{old}"', whole_word=True)
        folder_ids = self.scope_folders("sc_all")
        backend, progress = self.backend, Progress()

        def work():
            found, _ = backend.search(folder_ids, query, None, 0, (), progress)
            return backend.set_categories(found, add=new, remove=[old]) if found else 0

        self.task(work, lambda n: self.status(self.t("tagged_n", n=n)), "mp_searching")
        if self._busy:
            self.watch(progress)

    def tag_show(self):
        cat = self._selected_category()
        if cat is not None:
            self.query_var.set(f'category:"{cat.name}"')
            self.scope.set_key("sc_all")
            self.nb.select(1)
            self.run_search()

    def bulk_preview(self):
        if not self.connected():
            return
        query = self.make_query(self.bulk_query.get())
        folder_ids = self.scope_folders(self.bulk_scope.key)
        if query is None or not self.need(folder_ids, "mp_need_folder"):
            return
        since, internal, progress = self.since(self.bulk_period.key), self.internal_domains(), Progress()
        backend = self.backend

        def done(result):
            messages, truncated = result
            self.bulk_list.set(messages, self.t("results_more" if truncated else "results", n=len(messages),
                                                seen=progress.seen))

        self.task(lambda: backend.search(folder_ids, query, since, 0, internal, progress), done, "mp_searching")
        if self._busy:
            self.watch(progress)

    def bulk_apply(self, add):
        name = self.bulk_cat.get()
        messages = self.bulk_list.messages
        if not self.connected() or not self.need(name, "mp_need_category") or not self.need(messages, "mp_need_preview"):
            return
        key = "bulk_add_confirm" if add else "bulk_remove_confirm"
        if not messagebox.askyesno(self.APP_NAME, self.t(key, name=name, n=len(messages)), parent=self):
            return

        def done(n):
            for msg in messages:
                if add and name not in msg.categories:
                    msg.categories.append(name)
                elif not add:
                    msg.categories = [c for c in msg.categories if c.lower() != name.lower()]
            self.bulk_list.refresh()
            self.status(self.t("tagged_n", n=n))

        work = (lambda: self.backend.set_categories(messages, add=[name])) if add else \
            (lambda: self.backend.set_categories(messages, remove=[name]))
        self.task(work, done)

    # ------------------------------------------------------------ reglas
    def _build_rules(self):
        tab = self.add_tab("tab_rules", padding=8)
        panes = ttk.PanedWindow(tab, orient="horizontal")
        panes.pack(fill="both", expand=True)
        left = self.lframe(panes, "rules_list")
        panes.add(left, weight=2)
        self.rule_tree = ttk.Treeview(left, columns=("on", "name", "query"), show="headings", height=12,
                                      selectmode="browse")
        for col, width in (("on", 40), ("name", 160), ("query", 240)):
            self.rule_tree.column(col, width=width, stretch=col == "query", anchor="center" if col == "on" else "w")
        self.tr_call(lambda: [self.rule_tree.heading(c, text=self.t(f"rcol_{c}")) for c in ("on", "name", "query")])
        self.rule_tree.pack(fill="both", expand=True)
        self.rule_tree.bind("<<TreeviewSelect>>", lambda e: self.select_rule())
        bar = ttk.Frame(left)
        bar.pack(fill="x", pady=(6, 0))
        self.btn(bar, "rule_new", lambda: self.new_rule()).pack(side="left")
        self.btn(bar, "rule_delete", self.delete_rule).pack(side="left", padx=4)
        self.btn(bar, "move_up", lambda: self.move_rule(-1)).pack(side="left")
        self.btn(bar, "move_down", lambda: self.move_rule(1)).pack(side="left", padx=4)

        right = ttk.Frame(panes)
        panes.add(right, weight=3)
        self.place_sash(panes, 0.34)
        form = self.lframe(right, "rule_edit")
        form.pack(fill="x")
        form.columnconfigure(1, weight=1)
        self.r_name, self.r_query = ttk.Entry(form), ttk.Entry(form)
        self.field(form, "rule_name", self.r_name, 0)
        self.field(form, "search_label", self.r_query, 1)
        self.r_move = tk.BooleanVar(value=False)
        move = ttk.Frame(form)
        self.chk(move, "rule_move", self.r_move).pack(side="left")
        self.r_folder_label = ttk.Label(move, style="Hint.TLabel")
        self.r_folder_label.pack(side="left", padx=6)
        self.btn(move, "choose", self.rule_pick_folder).pack(side="left")
        move.grid(row=2, column=0, columnspan=2, sticky="w", pady=3)
        cats = ttk.Frame(form)
        self.lbl(cats, "rule_tag").pack(side="left")
        self.r_cats_label = ttk.Label(cats, style="Hint.TLabel")
        self.r_cats_label.pack(side="left", padx=6)
        self.btn(cats, "choose", self.rule_pick_categories).pack(side="left")
        cats.grid(row=3, column=0, columnspan=2, sticky="w", pady=3)
        flags = ttk.Frame(form)
        self.r_read, self.r_flag, self.r_enabled = (tk.BooleanVar(value=False), tk.BooleanVar(value=False),
                                                    tk.BooleanVar(value=True))
        self.chk(flags, "rule_read", self.r_read).pack(side="left")
        self.chk(flags, "rule_flag", self.r_flag).pack(side="left", padx=12)
        self.chk(flags, "rule_enabled", self.r_enabled).pack(side="left")
        flags.grid(row=4, column=0, columnspan=2, sticky="w", pady=3)
        buttons = ttk.Frame(form)
        buttons.grid(row=5, column=0, columnspan=2, sticky="w", pady=(8, 0))
        self.btn(buttons, "rule_save", self.save_rule, accent=True).pack(side="left")
        self.btn(buttons, "rule_test", lambda: self.run_rules(only_current=True, apply=False)).pack(side="left",
                                                                                                   padx=6)
        self.btn(buttons, "rule_run", lambda: self.run_rules(only_current=True, apply=True)).pack(side="left")
        self.btn(buttons, "rule_outlook", self.rule_to_outlook).pack(side="left", padx=6)

        run = self.lframe(right, "rule_scope")
        run.pack(fill="x", pady=8)
        self.rule_scope = Choice(self, run, RULE_SCOPES, width=26)
        self.rule_scope.pack(side="left")
        self.rule_period = Choice(self, run, list(PERIODS), width=14, default=1)
        self.rule_period.pack(side="left", padx=8)
        self.btn(run, "rules_run_all", lambda: self.run_rules(only_current=False, apply=True)).pack(side="left")
        self.rule_summary = ttk.Label(right, style="Hint.TLabel", wraplength=700, justify="left")
        self.rule_summary.pack(anchor="w")
        self.rule_list = MessageList(right, self, folder_column=True, height=10)
        self.rule_list.pack(fill="both", expand=True)
        self.tr_call(self._fill_rules)

    def _fill_rules(self):
        self.rule_tree.delete(*self.rule_tree.get_children())
        for n, rule in enumerate(self.rules):
            self.rule_tree.insert("", "end", iid=str(n), values=("✓" if rule.enabled else "", rule.name, rule.query))
        if self.rule_index is not None and self.rule_index < len(self.rules):
            self.rule_tree.selection_set(str(self.rule_index))
        self._show_rule_targets()

    def _show_rule_targets(self):
        store, path = self.rule_folder
        self.r_folder_label.configure(text=f"{path} ({store})" if path else self.t("none"))
        self.r_cats_label.configure(text=", ".join(self.rule_categories) or self.t("none"))

    def _save_rules(self):
        self.prefs["rules"] = [r.to_dict() for r in self.rules]
        self.prefs.save()
        self._fill_rules()

    def select_rule(self):
        sel = self.rule_tree.selection()
        if not sel:
            return
        self.rule_index = int(sel[0])
        rule = self.rules[self.rule_index]
        for entry, value in ((self.r_name, rule.name), (self.r_query, rule.query)):
            entry.delete(0, "end")
            entry.insert(0, value)
        self.rule_folder = (rule.folder_store, rule.folder_path)
        self.rule_categories = list(rule.categories)
        self.r_move.set(bool(rule.folder_path))
        self.r_read.set(rule.mark_read)
        self.r_flag.set(rule.flag)
        self.r_enabled.set(rule.enabled)
        self._show_rule_targets()

    def new_rule(self, query=""):
        self.rule_index = None
        self.rule_tree.selection_set(())
        for entry, value in ((self.r_name, ""), (self.r_query, query)):
            entry.delete(0, "end")
            entry.insert(0, value)
        self.rule_folder, self.rule_categories = ("", ""), []
        for var, value in ((self.r_move, False), (self.r_read, False), (self.r_flag, False), (self.r_enabled, True)):
            var.set(value)
        self._show_rule_targets()
        self.r_name.focus_set()

    def form_rule(self):
        name, query = self.r_name.get().strip(), self.r_query.get().strip()
        if not self.need(name and query, "rule_need_fields") or self.make_query(query) is None:
            return None
        store, path = self.rule_folder if self.r_move.get() else ("", "")
        return rules.MailRule(name, query, bool(self.r_enabled.get()), store, path, list(self.rule_categories),
                              bool(self.r_read.get()), bool(self.r_flag.get()))

    def save_rule(self):
        rule = self.form_rule()
        if rule is None:
            return None
        if self.rule_index is None:
            self.rules.append(rule)
            self.rule_index = len(self.rules) - 1
        else:
            self.rules[self.rule_index] = rule
        self._save_rules()
        self.status(self.t("rule_saved", name=rule.name))
        return rule

    def delete_rule(self):
        if self.rule_index is None or not messagebox.askyesno(
                self.APP_NAME, self.t("rule_delete_confirm", name=self.rules[self.rule_index].name), parent=self):
            return
        del self.rules[self.rule_index]
        self.rule_index = None
        self._save_rules()
        self.new_rule()

    def move_rule(self, step):
        i = self.rule_index
        if i is None or not 0 <= i + step < len(self.rules):
            return
        self.rules[i], self.rules[i + step] = self.rules[i + step], self.rules[i]
        self.rule_index = i + step
        self._save_rules()

    def rule_pick_folder(self):
        if not self.connected():
            return
        dest = FolderDialog(self, "rule_move", self.stores, self.folders).result
        if dest:
            folder = self.folder_index[dest]
            store = self.store_of(dest)
            self.rule_folder = (store.name if store else "", folder.path)
            self.r_move.set(True)
            self._show_rule_targets()

    def rule_pick_categories(self):
        if not self.connected():
            return
        result = CategoryDialog(self, self.categories, initial=self.rule_categories,
                                create=self._create_category_now).result
        if result:
            add, remove = result
            drop = {r.lower() for r in remove}
            self.rule_categories = [c for c in self.rule_categories if c.lower() not in drop] + add
            self._show_rule_targets()

    def _resolver(self):
        return lambda rule: rules.find_folder(self.stores, self.folders, rule.folder_store, rule.folder_path)

    def run_rules(self, only_current, apply):
        if not self.connected():
            return
        if only_current:
            rule = self.form_rule()
            if rule is None:
                return
            selected = [rules.MailRule(**{**rule.to_dict(), "enabled": True})]
        else:
            selected = [r for r in self.rules if r.enabled]
            if not self.need(selected, "rules_none_active"):
                return
        folder_ids = self.scope_folders(self.rule_scope.key)
        if not self.need(folder_ids, "mp_need_folder"):
            return
        try:
            rules.compile_rules(selected)
        except QueryError as exc:
            self.show_error(exc)
            return
        query = self.make_query(selected[0].query) if len(selected) == 1 else Query("")
        since, internal, progress = self.since(self.rule_period.key), self.internal_domains(), Progress()
        backend, resolve, options = self.backend, self._resolver(), self.query_options()
        missing = [r.name for r in selected if r.folder_path and resolve(r) is None]

        def work():
            found, _ = backend.search(folder_ids, query, since, 0, internal, progress)
            return rules.plan(selected, found, resolve, backend.details, internal, **options)

        def done(planned):
            self.rule_list.set([p.msg for p in planned])
            summary = self.t("rule_plan", n=len(planned), moved=sum(1 for p in planned if p.move_to),
                             tagged=sum(1 for p in planned if p.add), read=sum(p.mark_read for p in planned),
                             flagged=sum(p.flag for p in planned))
            if missing:
                summary += "\n" + self.t("rule_missing_folder", names=", ".join(missing))
            self.rule_summary.configure(text=summary)
            if apply and planned and messagebox.askyesno(self.APP_NAME, summary + "\n\n" + self.t("rule_apply_confirm"),
                                                         parent=self):
                self.task(lambda: rules.execute(backend, planned), self._rules_done)
            elif apply and not planned:
                self.info(self.t("rule_nothing"))

        self.task(work, done, "mp_searching")
        if self._busy:
            self.watch(progress)

    def _rules_done(self, counts):
        self.rule_summary.configure(text=self.t("rule_done", **counts))
        self.rule_list.set([])
        self.refresh_all()

    def rule_to_outlook(self):
        if not self.connected():
            return
        rule = self.save_rule()
        if rule is None:
            return
        spec, notes = rules.to_outlook(rule)
        if spec is None:
            messagebox.showwarning(self.APP_NAME, "\n".join(self.t(n) for n in notes), parent=self)
            return
        folder_id = self._resolver()(rule) if rule.folder_path else None
        if rule.folder_path and folder_id is None:
            messagebox.showwarning(self.APP_NAME, self.t("rule_missing_folder", names=rule.name), parent=self)
            return
        lines = [self.t("rule_outlook_intro", name=rule.name), ""] + self.describe_spec(spec)
        lines += [self.t("rule_outlook_actions")]
        if folder_id:
            lines.append(f"  • {self.t('rule_move')} {rule.folder_path}")
        if rule.categories:
            lines.append(f"  • {self.t('rule_tag')} {', '.join(rule.categories)}")
        if rule.flag:
            lines.append(f"  • {self.t('rule_flag')}")
        lines += [""] + [self.t(n) for n in notes] + [self.t("rule_outlook_confirm")]
        if not messagebox.askyesno(self.APP_NAME, "\n".join(lines), parent=self):
            return
        store = self.store_of(folder_id) if folder_id else next((s for s in self.stores if s.kind == "primary"), None)
        name = f"MailPilot - {rule.name}"

        def done(_):
            key = "rule_outlook_demo" if self.backend.kind == "demo" else "rule_outlook_done"
            self.info(self.t(key, name=name))

        self.task(lambda: self.backend.create_rule(name, spec, store.id if store else None, folder_id,
                                                   rule.categories, rule.flag), done)

    def describe_spec(self, spec):
        lines = []
        for part, title in (("conditions", "rule_outlook_when"), ("exceptions", "rule_outlook_except")):
            if spec[part]:
                lines.append(self.t(title))
                for kind, value in spec[part].items():
                    if kind == "importance":
                        value = self.t({2: "imp_high", 1: "imp_normal", 0: "imp_low"}[value])
                    elif isinstance(value, list):
                        value = " / ".join(f"«{v}»" for v in value)
                    else:
                        value = ""
                    lines.append(f"  • {self.t('rc_' + kind)} {value}".rstrip())
        return lines

    # ------------------------------------------------------------ redacción en inglés
    def _build_writing(self):
        tab = self.add_tab("tab_writing", padding=8)
        bar = ttk.Frame(tab)
        bar.pack(fill="x")
        self.btn(bar, "from_outlook", self.draft_from_outlook, accent=True).pack(side="left")
        self.apply_btn = self.btn(bar, "apply_outlook", self.draft_apply)
        self.apply_btn.pack(side="left", padx=6)
        self.apply_btn.state(["disabled"])
        self.btn(bar, "new_draft", self.draft_new).pack(side="left")
        self.btn(bar, "copy", self.draft_copy).pack(side="left", padx=6)
        self.btn(bar, "clear", lambda: self.set_draft("", "")).pack(side="left")
        self.btn(bar, "load_sample", self.draft_sample).pack(side="left", padx=6)
        self.draft_label = ttk.Label(tab, style="Hint.TLabel")
        self.draft_label.pack(anchor="w", pady=(4, 0))

        subject = ttk.Frame(tab)
        subject.pack(fill="x", pady=6)
        self.lbl(subject, "subject").pack(side="left", padx=(0, 6))
        self.subject_var = tk.StringVar()
        ttk.Entry(subject, textvariable=self.subject_var, font=("Segoe UI", 11)).pack(side="left", fill="x",
                                                                                      expand=True)
        self.subject_var.trace_add("write", lambda *a: self.schedule_check())

        panes = ttk.PanedWindow(tab, orient="horizontal")
        panes.pack(fill="both", expand=True)
        left = ttk.Frame(panes)
        panes.add(left, weight=3)
        holder = ttk.Frame(left)
        holder.pack(fill="both", expand=True)
        self.editor = tk.Text(holder, wrap="word", undo=True, font=("Segoe UI", 11), relief="flat", borderwidth=1,
                              highlightthickness=1, highlightcolor="#7aa7e0", highlightbackground="#d7dde5",
                              padx=10, pady=8, height=18)
        ys = ttk.Scrollbar(holder, orient="vertical", command=self.editor.yview)
        self.editor.configure(yscrollcommand=ys.set)
        ys.pack(side="right", fill="y")
        self.editor.pack(fill="both", expand=True)
        for kind, color in KIND_COLORS.items():
            self.editor.tag_configure(kind, background=color, underline=kind == "spelling")
        self.editor.tag_configure("current", background="#FFD24D")
        self.editor.bind("<<Modified>>", self._on_modified)
        self.stats_label = ttk.Label(left, style="Hint.TLabel")
        self.stats_label.pack(anchor="w", pady=(4, 0))

        side = ttk.Notebook(panes)
        panes.add(side, weight=2)
        review = ttk.Frame(side, padding=6)
        side.add(review, text="")
        phrases = ttk.Frame(side, padding=6)
        side.add(phrases, text="")
        templates = ttk.Frame(side, padding=6)
        side.add(templates, text="")
        self.tr_call(lambda: [side.tab(frame, text=self.t(key)) for frame, key in
                              ((review, "wt_review"), (phrases, "wt_phrases"), (templates, "wt_templates"))])
        self._build_review(review)
        self._build_phrases(phrases)
        self._build_templates(templates)
        self.place_sash(panes, 0.56)

    def _build_review(self, frame):
        bar = ttk.Frame(frame)
        bar.pack(fill="x")
        self.btn(bar, "check_now", self.check_text, accent=True).pack(side="left")
        self.btn(bar, "apply_safe", self.apply_safe).pack(side="left", padx=6)
        self.issue_tree = ttk.Treeview(frame, columns=("kind", "text", "suggestion"), show="headings", height=9,
                                       selectmode="browse")
        for col, width in (("kind", 110), ("text", 130), ("suggestion", 150)):
            self.issue_tree.column(col, width=width, stretch=col != "kind")
        self.tr_call(lambda: [self.issue_tree.heading(c, text=self.t(f"icol_{c}")) for c in ("kind", "text",
                                                                                            "suggestion")])
        self.issue_tree.pack(fill="both", expand=True, pady=6)
        self.issue_tree.bind("<<TreeviewSelect>>", lambda e: self.select_issue())
        self.issue_tree.bind("<Double-1>", lambda e: self.apply_issue())
        self.explain = ttk.Label(frame, wraplength=420, justify="left")
        self.explain.pack(fill="x")
        self.sugg_list = tk.Listbox(frame, height=3, exportselection=False, font=("Segoe UI", 10))
        self.sugg_list.pack(fill="x", pady=4)
        self.sugg_list.bind("<Double-1>", lambda e: self.apply_issue())
        buttons = ttk.Frame(frame)
        buttons.pack(fill="x")
        self.btn(buttons, "apply_fix", self.apply_issue).pack(side="left")
        self.btn(buttons, "ignore", self.ignore_issue).pack(side="left", padx=6)
        self.btn(buttons, "add_dictionary", self.add_to_dictionary).pack(side="left")
        ai = self.lframe(frame, "ai_writing", padding=6)
        ai.pack(fill="x", pady=(8, 0))
        self.tone = Choice(self, ai, assist.TONES, [f"tone_{tone}" for tone in assist.TONES], width=20)
        self.tone.pack(side="left")
        self.btn(ai, "ai_improve", lambda: self.ai_email(False)).pack(side="left", padx=6)
        self.btn(ai, "ai_translate", lambda: self.ai_email(True)).pack(side="left")

    def _build_phrases(self, frame):
        keys = list(PHRASES)
        self.phrase_cat = Choice(self, frame, keys, [f"pc_{k}" for k in keys], width=28)
        self.phrase_cat.pack(anchor="w")
        self.phrase_cat.bind("<<ComboboxSelected>>", lambda e: self._fill_phrases(), add="+")
        self.phrase_list = tk.Listbox(frame, height=12, exportselection=False, font=("Segoe UI", 10))
        self.phrase_list.pack(fill="both", expand=True, pady=6)
        self.phrase_list.bind("<<ListboxSelect>>", lambda e: self._phrase_hint())
        self.phrase_list.bind("<Double-1>", lambda e: self.insert_phrase())
        self.phrase_note = ttk.Label(frame, style="Hint.TLabel", wraplength=420, justify="left")
        self.phrase_note.pack(fill="x")
        self.btn(frame, "insert", self.insert_phrase).pack(anchor="w", pady=(6, 0))
        self.tr_call(self._fill_phrases)

    def _fill_phrases(self):
        self.phrase_list.delete(0, "end")
        for english_text, *_ in PHRASES[self.phrase_cat.key]:
            self.phrase_list.insert("end", english_text)
        self.phrase_note.configure(text="")

    def _phrase_hint(self):
        sel = self.phrase_list.curselection()
        if sel and self.t.lang != "en":
            phrase = PHRASES[self.phrase_cat.key][sel[0]]
            self.phrase_note.configure(text=phrase[1] if self.t.lang == "es" else phrase[2])

    def insert_phrase(self):
        sel = self.phrase_list.curselection()
        if sel:
            self.editor.insert("insert", PHRASES[self.phrase_cat.key][sel[0]][0] + " ")
            self.editor.focus_set()

    def _build_templates(self, frame):
        self.template_list = tk.Listbox(frame, height=8, exportselection=False, font=("Segoe UI", 10))
        self.template_list.pack(fill="x")
        self.template_list.bind("<<ListboxSelect>>", lambda e: self._template_preview())
        self.template_box = TextBox(frame, height=12, readonly=True, width=40)
        self.template_box.pack(fill="both", expand=True, pady=6)
        self.btn(frame, "use_template", self.use_template).pack(anchor="w")
        self.tr_call(self._fill_templates)

    def _fill_templates(self):
        self.template_list.delete(0, "end")
        for key in TEMPLATES:
            self.template_list.insert("end", self.t(key))

    def _template_preview(self):
        sel = self.template_list.curselection()
        if sel:
            subject, body = TEMPLATES[list(TEMPLATES)[sel[0]]]
            self.template_box.set(f"Subject: {subject}\n\n{body}")

    def use_template(self):
        sel = self.template_list.curselection()
        if not self.need(sel, "mp_need_template"):
            return
        if self.editor_text().strip() and not messagebox.askyesno(self.APP_NAME, self.t("replace_text_confirm"),
                                                                  parent=self):
            return
        self.set_draft(*TEMPLATES[list(TEMPLATES)[sel[0]]])

    def editor_text(self):
        return self.editor.get("1.0", "end-1c")

    def set_draft(self, subject, body):
        self.subject_var.set(subject)
        self.editor.edit_separator()
        self.editor.delete("1.0", "end")
        self.editor.insert("1.0", body)
        self.editor.edit_separator()
        self.check_text()

    def schedule_check(self):
        if self._check_job is not None:
            self.after_cancel(self._check_job)
        self._check_job = self.after(AUTO_CHECK_MS, self.check_text)

    def _on_modified(self, event=None):
        if self.editor.edit_modified():
            self.editor.edit_modified(False)
            self.schedule_check()

    def check_text(self):
        if self._check_job is not None:
            self.after_cancel(self._check_job)
            self._check_job = None
        text, subject = self.editor_text(), self.subject_var.get()
        issues = english.check(text, subject, user_words=self.prefs["user_words"]) if text.strip() else []
        self.issues = [i for i in issues if (i.rule, i.text.lower()) not in self.ignored]
        for tag in list(KIND_COLORS) + ["current"]:
            self.editor.tag_remove(tag, "1.0", "end")
        self.issue_tree.delete(*self.issue_tree.get_children())
        for n, issue in enumerate(self.issues):
            if issue.start >= 0 and issue.end > issue.start:
                self.editor.tag_add(issue.kind, tk_index(text, issue.start), tk_index(text, issue.end))
            where = f"[{self.t('subject')}] " if issue.start < 0 else ""
            self.issue_tree.insert("", "end", iid=str(n), values=(
                self.t(f"kind_{issue.kind}"), where + (issue.text or "—").replace("\n", " ")[:60],
                (issue.suggestions[0] if issue.suggestions else "—").replace("\n", " ⏎ ")[:60]))
        self.editor.tag_raise("current")
        self.explain.configure(text=self.t("no_issues") if text.strip() and not self.issues else "")
        self.sugg_list.delete(0, "end")
        self._show_stats(text)

    def _show_stats(self, text):
        if not text.strip():
            self.stats_label.configure(text="")
            return
        st = text_stats(text, "en")
        counts = {}
        for issue in self.issues:
            counts[issue.kind] = counts.get(issue.kind, 0) + 1
        found = ", ".join(f"{self.t('kind_' + k)}: {v}" for k, v in counts.items()) or self.t("none")
        self.stats_label.configure(text=self.t(
            "writing_stats", words=st["words"], sentences=st["sentences"], score=st["score"],
            level=self.t("lvl_" + readability_level(st["score"])),
            passive=sum(1 for i in self.issues if i.rule == "passive"), found=found))

    def _issue(self):
        sel = self.issue_tree.selection()
        return self.issues[int(sel[0])] if sel and int(sel[0]) < len(self.issues) else None

    def select_issue(self):
        issue = self._issue()
        if issue is None:
            return
        text = self.editor_text()
        self.editor.tag_remove("current", "1.0", "end")
        if issue.start >= 0:
            start = tk_index(text, issue.start)
            if issue.end > issue.start:
                self.editor.tag_add("current", start, tk_index(text, issue.end))
            self.editor.see(start)
        message = english.MESSAGES.get(issue.rule, english.MESSAGES["spelling"])
        self.explain.configure(text=message[("es", "en", "fr").index(self.t.lang)].format(**issue.params))
        self.sugg_list.delete(0, "end")
        for suggestion in issue.suggestions:
            self.sugg_list.insert("end", suggestion.replace("\n", " ⏎ "))
        if issue.suggestions:
            self.sugg_list.selection_set(0)

    def apply_issue(self):
        issue = self._issue()
        if issue is None or not issue.suggestions:
            return
        sel = self.sugg_list.curselection()
        suggestion = issue.suggestions[sel[0] if sel else 0]
        if issue.start < 0:
            self.subject_var.set(suggestion)
        else:
            text = self.editor_text()
            if text[issue.start:issue.end] != issue.text and issue.end > issue.start:
                self.check_text()  # el texto cambió desde la revisión
                return
            start, end = tk_index(text, issue.start), tk_index(text, issue.end)
            self.editor.edit_separator()
            self.editor.delete(start, end)
            self.editor.insert(start, suggestion)
            self.editor.edit_separator()
        self.check_text()

    def apply_safe(self):
        text, subject = english.apply_safe(self.editor_text(), self.subject_var.get(),
                                           user_words=self.prefs["user_words"])
        if text != self.editor_text() or subject != self.subject_var.get():
            self.set_draft(subject, text)

    def ignore_issue(self):
        issue = self._issue()
        if issue is not None:
            self.ignored.add((issue.rule, issue.text.lower()))
            self.check_text()

    def add_to_dictionary(self):
        issue = self._issue()
        if issue is None or issue.kind != "spelling":
            messagebox.showwarning(self.APP_NAME, self.t("dictionary_only_spelling"), parent=self)
            return
        word = issue.text.lower()
        if word not in self.prefs["user_words"]:
            self.prefs["user_words"].append(word)
            self.prefs.save()
        self.check_text()

    def draft_from_outlook(self):
        if not self.connected():
            return

        def done(draft):
            self.draft = {"original": draft["body"], "subject": draft["subject"], "editable": draft["editable"],
                          "to": draft["to"]}
            self.set_draft(draft["subject"], draft["body"])
            self.apply_btn.state(["!disabled"] if draft["editable"] else ["disabled"])
            self.draft_label.configure(text=self.t("draft_editable" if draft["editable"] else "draft_readonly"))

        self.task(self.backend.current_draft, done, "mp_loading")

    def draft_apply(self):
        if not self.connected() or not self.draft or not self.draft.get("editable"):
            return
        text, subject = self.editor_text(), self.subject_var.get()
        changes = diff_changes(self.draft["original"], text)
        new_subject = subject if subject != self.draft["subject"] else None
        if not changes and new_subject is None:
            self.info(self.t("no_changes"))
            return

        def done(result):
            applied, failed, current = result
            self.draft.update(original=current, subject=subject)
            message = self.t("applied_n", n=applied + (new_subject is not None))
            if failed:
                message += "\n" + self.t("failed_n", n=failed)
            self.info(message)

        self.task(lambda: self.backend.apply_to_current(changes, new_subject), done)

    def draft_new(self):
        if not self.connected() or not self.need(self.editor_text().strip(), "need_text"):
            return
        to, subject, body = (self.draft or {}).get("to", ""), self.subject_var.get(), self.editor_text()

        def done(_):
            self.info(self.t("draft_created_demo" if self.backend.kind == "demo" else "draft_created"))

        self.task(lambda: self.backend.create_draft(to, subject, body), done)

    def draft_copy(self):
        if self.need(self.editor_text().strip(), "need_text"):
            self.copy(self.editor_text())

    def draft_sample(self):
        _, subject, body = DRAFTS[0]
        self.draft = None
        self.apply_btn.state(["disabled"])
        self.draft_label.configure(text="")
        self.set_draft(subject.format(claim="R-2026-0412"), body)

    def ai_email(self, translate):
        text, subject = self.editor_text(), self.subject_var.get()
        if not self.need(text.strip(), "need_text"):
            return
        tone, anon = self.tone.key, self.anonymizer()

        def work(ai):
            body, subj = (anon.mask(text), anon.mask(subject)) if anon else (text, subject)
            system = assist.TRANSLATE_SYSTEM if translate else assist.REWRITE_SYSTEM
            data = ai.ask_json(system, assist.email_prompt(subj, body, tone), assist.EMAIL_SCHEMA, max_tokens=8000)
            return assist.unmask_all(data, anon)

        def done(data):
            ResultDialog(self, "ai_result_title", [
                ("subject", data["subject"], True, 1), ("ai_body", data["body"], True, 14),
                ("ai_changes", "\n".join(f"• {c}" for c in data["changes"]), False, 6)],
                [("use_text", self._use_ai_text)])

        self.run_ai(work, done)

    def _use_ai_text(self, dialog):
        subject, body = dialog.value("subject"), dialog.value("ai_body")
        dialog.destroy()
        self.set_draft(subject, body)

    # ------------------------------------------------------------ análisis y seguridad
    def _build_analysis(self):
        tab = self.add_tab("tab_analysis", padding=8)
        opts = ttk.Frame(tab)
        opts.pack(fill="x")
        self.lbl(opts, "scope").pack(side="left")
        self.an_scope = Choice(self, opts, SCOPES, width=24, default=2)
        self.an_scope.pack(side="left", padx=(4, 12))
        self.lbl(opts, "period").pack(side="left")
        self.an_period = Choice(self, opts, list(PERIODS), width=14, default=2)
        self.an_period.pack(side="left", padx=(4, 12))
        self.lbl(opts, "internal_domains").pack(side="left")
        self.domains_var = tk.StringVar(value=self.prefs["internal_domains"])
        ttk.Entry(opts, textvariable=self.domains_var, width=24).pack(side="left", padx=(4, 12))
        self.lbl(opts, "claim_pattern").pack(side="left")
        self.claim_var = tk.StringVar(value=self.prefs["claim_regex"])
        ttk.Entry(opts, textvariable=self.claim_var, width=30).pack(side="left", padx=4)

        bar = ttk.Frame(tab)
        bar.pack(fill="x", pady=6)
        self.btn(bar, "an_overview", self.an_run_overview, accent=True).pack(side="left")
        for key, command in (("an_phishing", self.an_run_phishing), ("an_sensitive", self.an_run_sensitive),
                             ("an_claims", self.an_run_claims), ("an_ai", self.an_run_ai)):
            self.btn(bar, key, command).pack(side="left", padx=(6, 0))
        self.an_stop_btn = self.btn(bar, "stop", self.stop_task)
        self.an_stop_btn.pack(side="left", padx=6)
        self.an_stop_btn.state(["disabled"])
        self.btn(bar, "export_excel", self.an_export).pack(side="right")

        panes = ttk.PanedWindow(tab, orient="vertical")
        panes.pack(fill="both", expand=True)
        upper = ttk.PanedWindow(panes, orient="horizontal")
        panes.add(upper, weight=1)
        self.an_text = TextBox(upper, height=5, readonly=True)
        upper.add(self.an_text, weight=3)
        sugg = self.lframe(upper, "suggestions", padding=6)
        upper.add(sugg, weight=2)
        sbar = ttk.Frame(sugg)
        sbar.pack(side="bottom", fill="x", pady=(4, 0))
        self.btn(sbar, "sugg_search", lambda: self.use_suggestion(False)).pack(side="left")
        self.btn(sbar, "sugg_rule", lambda: self.use_suggestion(True)).pack(side="left", padx=6)
        self.sugg_tree = ttk.Treeview(sugg, show="tree", height=3, selectmode="browse")
        self.sugg_tree.pack(fill="both", expand=True)
        self.place_sash(upper, 0.6)
        lower = ttk.Frame(panes)
        panes.add(lower, weight=3)
        rbar = ttk.Frame(lower)
        rbar.pack(side="bottom", fill="x", pady=(4, 0))
        self.btn(rbar, "act_open", self.an_open).pack(side="left")
        self.btn(rbar, "an_tag_phishing", self.an_tag_phishing).pack(side="left", padx=6)
        self.btn(rbar, "an_move_junk", self.an_move_junk).pack(side="left")
        self.an_table = DataTable(lower, self, height=10)
        self.an_table.pack(fill="both", expand=True)
        self.an_table.tree.bind("<Double-1>", lambda e: self.an_open())

    def _an_settings(self):
        pattern = self.claim_var.get().strip() or detectors.DEFAULT_CLAIM_REGEX
        try:
            re.compile(pattern)
        except re.error as exc:
            messagebox.showerror(self.t("error"), self.t("q_err_regex", detail=f"{pattern} ({exc})"), parent=self)
            return None
        self.prefs["claim_regex"], self.prefs["internal_domains"] = pattern, self.domains_var.get().strip()
        self.prefs.save()
        return pattern

    def _an_collect(self, then, bodies=False, html=False, filter_=None):
        """Reúne los correos del ámbito (y su cuerpo si hace falta) y llama a `then(correos)` en otro hilo."""
        if not self.connected():
            return
        pattern = self._an_settings()
        folder_ids = self.scope_folders(self.an_scope.key)
        if pattern is None or not self.need(folder_ids, "mp_need_folder"):
            return
        since, internal, progress = self.since(self.an_period.key), self.internal_domains(), Progress()
        backend = self.backend

        def work():
            messages, _ = backend.search(folder_ids, Query(""), since, 0, internal, progress)
            if filter_:
                messages = [m for m in messages if filter_(m, internal)]
            if bodies:
                messages = backend.scan(messages, html, progress)
            return then(messages, internal, pattern)

        return work, progress

    def _an_start(self, prepared, done, key="mp_analyzing"):
        if prepared is None:
            return
        work, progress = prepared
        self.task(work, done, key)
        if self._busy:
            self.watch(progress, "mp_progress_scan")

    def _an_show(self, df, rows, summary, sheets):
        self.an_rows = rows
        self.an_sheets = sheets
        self.an_text.set(summary)
        self.an_table.show(self._translated(df) if df is not None else None)

    def an_run_overview(self):
        def then(messages, internal, pattern):
            return (messages, analysis.overview(messages), analysis.senders(messages), analysis.domains(messages,
                    internal), analysis.by_month(messages), analysis.suggestions(messages, internal, pattern))

        def done(result):
            _, ov, senders, domains, months, suggestions = result
            self.an_overview = (ov, senders, domains)
            lines = [self.t("an_overview_text", **{k: (v.strftime("%Y-%m-%d") if hasattr(v, "strftime") else
                                                       ("—" if v is None else v)) for k, v in ov.items()})]
            self._show_suggestions(suggestions)
            if suggestions:
                lines += ["", self.t("an_has_suggestions", n=len(suggestions))]
            self._an_show(senders, [], "\n".join(lines),
                          [(self.t("sheet_senders"), self._translated(senders)),
                           (self.t("sheet_domains"), self._translated(domains)),
                           (self.t("sheet_months"), self._translated(months))])

        self._an_start(self._an_collect(then), done)

    def _show_suggestions(self, suggestions):
        self.suggestions = suggestions
        self.sugg_tree.delete(*self.sugg_tree.get_children())
        for n, s in enumerate(suggestions):
            self.sugg_tree.insert("", "end", iid=str(n), text=self.t(s["key"], **s["params"]))

    def use_suggestion(self, as_rule):
        sel = self.sugg_tree.selection()
        if not self.need(sel, "mp_need_suggestion"):
            return
        s = self.suggestions[int(sel[0])]
        if not as_rule:
            self.query_var.set(s["query"])
            self.scope.set_key(self.an_scope.key)
            self.nb.select(1)
            self.run_search()
            return
        self.new_rule(query=s["query"])
        self.r_name.insert(0, self.t(s["key"], **s["params"])[:60])
        if s["action"] == "read":
            self.r_read.set(True)
        self.nb.select(3)

    def an_run_phishing(self):
        def external(m, internal):
            return bool(m.domain) and not any(m.domain == d or m.domain.endswith("." + d) for d in internal)

        def then(messages, internal, pattern):
            return len(messages), analysis.phishing(messages, internal)

        def done(result):
            checked, rows = result
            extra = [{"col_score": s, "col_risk": self.t("risk_" + detectors.risk_level(s)),
                      "col_signals": ", ".join(self.t(f) for f in flags)} for s, flags, _ in rows]
            df = analysis.message_table([m for *_, m in rows], extra)
            df = df[["col_score", "col_risk", "col_date", "col_sender", "col_email", "col_subject", "col_signals",
                     "col_folder"]] if len(df) else None
            self._an_show(df, [m for *_, m in rows], self.t("an_phishing_text", n=len(rows), checked=checked),
                          [(self.t("sheet_phishing"), self._translated(df))] if df is not None else [])

        self._an_start(self._an_collect(then, bodies=True, html=True, filter_=external), done)

    def an_run_sensitive(self):
        def then(messages, internal, pattern):
            return len(messages), analysis.sensitive(messages)

        def done(result):
            checked, rows = result
            extra = [{"col_kind": self.t("kind_" + kind), "col_value": value} for kind, value, _ in rows]
            df = analysis.message_table([m for *_, m in rows], extra)
            df = df[["col_kind", "col_value", "col_date", "col_sender", "col_subject", "col_folder"]] if len(df) \
                else None
            self._an_show(df, [m for *_, m in rows], self.t("an_sensitive_text", n=len(rows), checked=checked,
                                                             msgs=len({m.id for *_, m in rows})),
                          [(self.t("sheet_sensitive"), self._translated(df))] if df is not None else [])

        self._an_start(self._an_collect(then, bodies=True), done)

    def an_run_claims(self):
        def then(messages, internal, pattern):
            return len(messages), analysis.claims(messages, pattern, internal)

        def done(result):
            checked, df = result
            self._an_show(df, [], self.t("an_claims_text", n=len(df), checked=checked),
                          [(self.t("sheet_claims"), self._translated(df))])

        self._an_start(self._an_collect(then, bodies=True), done)

    def an_run_ai(self):
        if self.an_overview is None:
            messagebox.showinfo(self.APP_NAME, self.t("an_ai_need_overview"), parent=self)
            return
        ov, senders, domains = self.an_overview
        folders = [f.path for fl in self.folders.values() for f in fl if f.depth > 0][:80]
        prompt = assist.organize_prompt(ov, senders, domains, folders, [c.name for c in self.categories])
        anon = self.anonymizer()

        def work(ai):
            data = ai.ask_json(assist.ORGANIZE_SYSTEM, anon.mask(prompt) if anon else prompt,
                               assist.ORGANIZE_SCHEMA, max_tokens=6000)
            return assist.unmask_all(data, anon)

        self.run_ai(work, self._ai_rules)

    def _ai_rules(self, data):
        valid = []
        for item in data.get("rules", []):
            try:
                Query(item["query"])
            except QueryError:
                continue
            valid.append(item)
        lines = [f"• {r['name']}: {r['query']}" + (f"  →  {r['folder']}" if r["folder"] else "")
                 + (f"  [{r['category']}]" if r["category"] else "") for r in valid]
        notes = "\n".join(f"• {n}" for n in data.get("notes", []))

        def add(dialog):
            primary = next((s.name for s in self.stores if s.kind == "primary"), "")
            for item in valid:
                self.rules.append(rules.MailRule(item["name"], item["query"], enabled=False,
                                                 folder_store=primary if item["folder"] else "",
                                                 folder_path=item["folder"],
                                                 categories=[item["category"]] if item["category"] else []))
            self._save_rules()
            dialog.destroy()
            self.nb.select(3)
            self.info(self.t("ai_rules_added", n=len(valid)))

        ResultDialog(self, "ai_rules_title", [("ai_rules", "\n".join(lines) or self.t("none"), False, 10),
                                              ("ai_notes", notes, False, 5)],
                     [("ai_rules_add", add)] if valid else [])

    def _an_selected(self):
        index = self.an_table.selected_index()
        if index is None or index >= len(self.an_rows):
            messagebox.showwarning(self.APP_NAME, self.t("mp_need_selection"), parent=self)
            return None
        return self.an_rows[index]

    def an_open(self):
        msg = self._an_selected()
        if msg is not None:
            self.open_message(msg)

    def an_tag_phishing(self):
        if not self.connected() or not self.need(self.an_rows, "no_data"):
            return
        name = next((c.name for c in self.categories if c.name.lower() in ("phishing", "hameçonnage")),
                    self.t("phishing_category"))
        if not messagebox.askyesno(self.APP_NAME, self.t("bulk_add_confirm", name=name, n=len(self.an_rows)),
                                   parent=self):
            return
        messages, backend = list(self.an_rows), self.backend
        exists = name.lower() in {c.name.lower() for c in self.categories}

        def work():
            if not exists:
                backend.create_category(name, 9)
            return backend.set_categories(messages, add=[name]), backend.categories()

        def done(result):
            n, self.categories = result
            self._fill_categories()
            self.status(self.t("tagged_n", n=n))

        self.task(work, done)

    def an_move_junk(self):
        if not self.connected() or not self.need(self.an_rows, "no_data"):
            return
        if not messagebox.askyesno(self.APP_NAME, self.t("junk_confirm", n=len(self.an_rows)), parent=self):
            return
        groups = {}
        for msg in self.an_rows:
            junk = next((f.id for f in self.folders.get(msg.store_id, []) if f.special == "junk"), None)
            if junk and junk != msg.folder_id:
                groups.setdefault(junk, []).append(msg)

        def work():
            return sum(self.backend.move_messages(messages, junk) for junk, messages in groups.items())

        def done(n):
            moved = {m.id for group in groups.values() for m in group}
            self.an_rows = [m for m in self.an_rows if m.id not in moved]
            self.status(self.t("moved_n", n=n, folder=self.t("junk")))
            self.refresh_all(reload_list=False)

        self.task(work, done)

    def an_export(self):
        if not self.need(self.an_sheets, "no_data"):
            return
        path = self.ask_save("excel", "MailPilot_analysis.xlsx")
        if path:
            analysis.export_excel(path, self.an_sheets)
            self.saved(path)


def main():
    MailPilot().mainloop()
