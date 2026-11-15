"""Yönetici ekranları: ekip, talep kodu, kullanıcı, parola isteği ve giriş kaydı."""

import sys
import threading
import tkinter as tk
from tkinter import messagebox, ttk

import hesap

FONT = ".AppleSystemUIFont"
MONO = "Menlo"
CARD = "#FFFFFF"
INK = "#14182B"
MUTED = "#6B7287"
FAINT = "#9AA1B4"
LINE = "#E3E6EE"
DIVIDER = "#EEF0F4"
CANVAS = "#F3F4F7"
FIELD = "#FAFBFC"
ROW_HOVER = "#F7F8FB"
ACCENT = "#3250E6"
ACCENT_HOVER = "#2843C4"
SOFT = "#EAEEFD"
SOFT_HOVER = "#DDE3FB"
GHOST_HOVER = "#EEF0F4"
DANGER = "#D1343B"
OK = "#1F8A4C"
OK_SOFT = "#E5F4EA"
WARN = "#9A6508"
WARN_SOFT = "#FCF3DC"
NEUTRAL_SOFT = "#EEF0F4"
ROLES = ("Yönetici", "Sorumlu", "Kullanıcı", "İzleyici")
ALL = "Tümü"


def render(parent, app, page):
    for child in parent.winfo_children():
        child.destroy()
    parent.pack(fill="both", expand=True)
    token = getattr(app, "_admin_token", 0) + 1
    app._admin_token = token
    if page == "Ekipler":
        TeamsPage(parent, app, token)
        return
    if page == "Talep kodları":
        CodesPage(parent, app, token)
        return
    _title(parent, page)
    status = tk.Label(parent, text="Yükleniyor…", bg=CANVAS, fg=MUTED, font=(FONT, 13))
    status.pack(anchor="w", padx=22, pady=8)
    if page == "Kullanıcılar":
        _user_form(parent, app)

    def work():
        try:
            data = _load(page)
            error = None
        except (hesap.ApiError, ValueError) as exc:
            data, error = None, str(exc)

        def apply():
            if not parent.winfo_exists() or getattr(app, "_admin_token", None) != token:
                return
            if status.winfo_exists():
                status.destroy()
            if error:
                tk.Label(parent, text=error, bg=CANVAS, fg=INK, font=(FONT, 13), wraplength=640, justify="left").pack(anchor="w", padx=22, pady=8)
                return
            _paint(parent, app, page, data)

        app.after(0, apply)

    threading.Thread(target=work, daemon=True).start()


def _load(page):
    store = hesap.client()
    if page == "Kullanıcılar":
        return {"resets": store.resets(), "users": store.users()}
    return store.login_logs()


def _paint(parent, app, page, data):
    if page == "Kullanıcılar":
        _user_rows(parent, app, data)
    else:
        _log_rows(parent, data)


def _title(parent, text):
    tk.Label(parent, text=text, bg=CANVAS, fg=INK, font=(FONT, 20, "bold")).pack(anchor="w", padx=22, pady=(8, 8))


# --- Ortak parçalar -------------------------------------------------------

def _is_admin(app):
    try:
        account = app._current_talep_account()
    except Exception:
        account = None
    account = account or {}
    return bool(
        account.get("is_admin")
        or account.get("role") == "Yönetici"
        or "Talep kodları" in (account.get("screens") or [])
    )


def _clean(value, limit, dash=False):
    return "".join(ch for ch in str(value or "").upper() if ch.isalnum() or (dash and ch == "-"))[:limit]


class Button(tk.Label):
    """macOS'ta tk.Button renk almadığı için tıklanan etiket."""

    PALETTES = {
        "primary": (ACCENT, "#FFFFFF", ACCENT_HOVER, None),
        "soft": (SOFT, ACCENT, SOFT_HOVER, None),
        "ghost": (CARD, INK, GHOST_HOVER, LINE),
        "plain": (CARD, MUTED, GHOST_HOVER, None),
    }

    def __init__(self, master, text, command, kind="primary", padx=14, pady=7, font=None):
        bg, fg, hover, border = self.PALETTES[kind]
        super().__init__(
            master, text=text, bg=bg, fg=fg, cursor="hand2", padx=padx, pady=pady,
            font=font or (FONT, 13, "bold" if kind in ("primary", "soft") else "normal"),
            highlightthickness=1 if border else 0, highlightbackground=border or bg,
        )
        self._bg, self._hover = bg, hover
        self.command = command
        self.enabled = True
        self.bind("<Enter>", lambda _e: self.enabled and self.configure(bg=self._hover))
        self.bind("<Leave>", lambda _e: self.configure(bg=self._bg))
        self.bind("<Button-1>", lambda _e: self.enabled and self.command and self.command())

    def set_enabled(self, enabled, text=None):
        self.enabled = enabled
        self.configure(cursor="hand2" if enabled else "arrow", fg=self.cget("fg"))
        if text is not None:
            self.configure(text=text)


def _chip(master, text, bg=SOFT, fg=ACCENT, mono=True, bold=True):
    return tk.Label(
        master, text=text, bg=bg, fg=fg, padx=8, pady=2,
        font=(MONO if mono else FONT, 12 if mono else 11, "bold" if bold else "normal"),
    )


def _entry(master, var, width=None):
    entry = tk.Entry(
        master, textvariable=var, font=(FONT, 13), relief="flat", bg=FIELD, fg=INK,
        insertbackground=INK, highlightthickness=1, highlightbackground=LINE, highlightcolor=ACCENT,
    )
    if width:
        entry.configure(width=width)
    return entry


def _field(master, label, hint=""):
    box = tk.Frame(master, bg=CARD)
    tk.Label(box, text=label, bg=CARD, fg=INK, font=(FONT, 12, "bold")).pack(anchor="w")
    hint_label = tk.Label(box, text=hint, bg=CARD, fg=FAINT, font=(FONT, 11))
    box.hint = hint_label
    return box


class Segmented(tk.Frame):
    def __init__(self, master, options, value, command=None, bg=CANVAS):
        super().__init__(master, bg=NEUTRAL_SOFT, padx=3, pady=3)
        self.value = value
        self.command = command
        self.items = {}
        for option in options:
            label = tk.Label(self, text=option, font=(FONT, 12), padx=12, pady=4, cursor="hand2", bg=NEUTRAL_SOFT, fg=MUTED)
            label.pack(side="left")
            label.bind("<Button-1>", lambda _e, o=option: self.set(o, notify=True))
            self.items[option] = label
        self._paint()

    def set(self, value, notify=False):
        self.value = value
        self._paint()
        if notify and self.command:
            self.command(value)

    def _paint(self):
        for option, label in self.items.items():
            on = option == self.value
            label.configure(bg=CARD if on else NEUTRAL_SOFT, fg=INK if on else MUTED,
                            font=(FONT, 12, "bold" if on else "normal"))


class ScrollArea(tk.Frame):
    def __init__(self, master, bg=CARD):
        super().__init__(master, bg=bg)
        self.canvas = tk.Canvas(self, bg=bg, highlightthickness=0, bd=0)
        self.bar = ttk.Scrollbar(self, orient="vertical", command=self.canvas.yview)
        self.inner = tk.Frame(self.canvas, bg=bg)
        self._win = self.canvas.create_window((0, 0), window=self.inner, anchor="nw")
        self.canvas.configure(yscrollcommand=self.bar.set)
        self.canvas.pack(side="left", fill="both", expand=True)
        self.inner.bind("<Configure>", self._sync)
        self.canvas.bind("<Configure>", self._fit)
        self.bind("<Enter>", self._grab)
        self.bind("<Leave>", self._release)

    def _sync(self, _event=None):
        self.canvas.configure(scrollregion=self.canvas.bbox("all"))
        overflow = self.inner.winfo_reqheight() > self.canvas.winfo_height() > 1
        if overflow and not self.bar.winfo_ismapped():
            self.bar.pack(side="right", fill="y")
        elif not overflow and self.bar.winfo_ismapped():
            self.bar.pack_forget()
            self.canvas.yview_moveto(0)

    def _fit(self, event):
        self.canvas.itemconfigure(self._win, width=event.width)
        self._sync()

    def _wheel(self, event):
        if self.inner.winfo_reqheight() <= self.canvas.winfo_height():
            return
        if getattr(event, "num", None) == 4:
            step = -1
        elif getattr(event, "num", None) == 5:
            step = 1
        elif sys.platform == "darwin":
            step = -event.delta
        else:
            step = -int(event.delta / 120) or (-1 if event.delta > 0 else 1)
        self.canvas.yview_scroll(step, "units")

    def _grab(self, _event):
        self.bind_all("<MouseWheel>", self._wheel)
        self.bind_all("<Button-4>", self._wheel)
        self.bind_all("<Button-5>", self._wheel)

    def _release(self, _event):
        self.unbind_all("<MouseWheel>")
        self.unbind_all("<Button-4>")
        self.unbind_all("<Button-5>")

    def top(self):
        self.canvas.yview_moveto(0)


# --- Liste + form iskeleti ---------------------------------------------------

class ManagedPage:
    noun = "kayıt"
    add_text = "Yeni kayıt"
    search_hint = "Ara"
    filters = ()
    columns = ()  # (başlık, sabit genişlik, ağırlık)

    def __init__(self, parent, app, token):
        self.parent = parent
        self.app = app
        self.token = token
        self.items = []
        self.teams = []
        self.codes = []
        self.filter = ALL
        self.query = tk.StringVar()
        self.form = None
        self.busy = False
        self.loaded = False
        self.can_edit = _is_admin(app)
        self._build()
        self.reload()

    # Alt sınıflar doldurur.
    def load(self):
        raise NotImplementedError

    def matches(self, item):
        return True

    def cells(self, row, item):
        raise NotImplementedError

    def build_form(self, body, item):
        raise NotImplementedError

    def submit(self, item):
        raise NotImplementedError

    def empty_text(self):
        return f"Henüz {self.noun} yok."

    # İskelet
    def alive(self):
        return self.parent.winfo_exists() and getattr(self.app, "_admin_token", None) == self.token

    def run(self, work, done, fail):
        def thread():
            try:
                result, error = work(), None
            except (hesap.ApiError, ValueError) as exc:
                result, error = None, str(exc)
            except Exception as exc:  # ağ hatası vb.; form kilitli kalmasın
                result, error = None, f"Beklenmeyen hata: {exc}"

            def apply():
                if not self.alive():
                    return
                if error is None:
                    done(result)
                else:
                    fail(error)

            self.app.after(0, apply)

        threading.Thread(target=thread, daemon=True).start()

    def _build(self):
        bar = tk.Frame(self.parent, bg=CANVAS)
        bar.pack(fill="x", padx=24, pady=(6, 12))
        search = tk.Frame(bar, bg=CARD, highlightthickness=1, highlightbackground=LINE, highlightcolor=LINE)
        search.pack(side="left")
        tk.Label(search, text="⌕", bg=CARD, fg=FAINT, font=(FONT, 15)).pack(side="left", padx=(10, 2))
        self.search_entry = tk.Entry(
            search, textvariable=self.query, font=(FONT, 13), relief="flat", bg=CARD, fg=INK,
            insertbackground=INK, highlightthickness=0, width=26,
        )
        self.search_entry.pack(side="left", ipady=6, padx=(0, 10))
        self._placeholder(self.search_entry, self.search_hint)
        self.query.trace_add("write", lambda *_: self.paint())
        if self.filters:
            Segmented(bar, self.filters, ALL, self._set_filter).pack(side="left", padx=(12, 0))
        if self.can_edit:
            Button(bar, f"+  {self.add_text}", lambda: self.open_form(None)).pack(side="right")
        self.toast = tk.Label(bar, text="", bg=CANVAS, fg=OK, font=(FONT, 12, "bold"))
        self.toast.pack(side="right", padx=12)

        self.form_slot = tk.Frame(self.parent, bg=CANVAS)
        self.form_slot.pack(fill="x", padx=24)

        card = tk.Frame(self.parent, bg=CARD, highlightthickness=1, highlightbackground=LINE, highlightcolor=LINE)
        card.pack(fill="both", expand=True, padx=24, pady=(0, 12))
        head = tk.Frame(card, bg=CARD)
        head.pack(fill="x", padx=18, pady=(12, 8))
        self._grid(head)
        for index, (title, _w, _g) in enumerate(self.columns):
            tk.Label(head, text=title.upper(), bg=CARD, fg=FAINT, font=(FONT, 10, "bold"), anchor="w", width=1).grid(
                row=0, column=index, sticky="ew", padx=(0, 12))
        tk.Frame(card, bg=LINE, height=1).pack(fill="x")
        self.scroll = ScrollArea(card)
        self.scroll.pack(fill="both", expand=True)

        foot = tk.Frame(self.parent, bg=CANVAS)
        foot.pack(fill="x", padx=26, pady=(0, 12))
        self.count = tk.Label(foot, text="", bg=CANVAS, fg=MUTED, font=(FONT, 12))
        self.count.pack(side="left")

    def _placeholder(self, entry, text):
        def show(_e=None):
            if not entry.get():
                entry._ph = True
                entry.configure(fg=FAINT)
                entry.insert(0, text)

        def hide(_e=None):
            if getattr(entry, "_ph", False):
                entry.delete(0, "end")
                entry.configure(fg=INK)
                entry._ph = False

        entry.bind("<FocusIn>", hide)
        entry.bind("<FocusOut>", show)
        show()

    def search_text(self):
        if getattr(self.search_entry, "_ph", False):
            return ""
        return self.query.get().strip().casefold()

    def _grid(self, frame):
        for index, (_t, width, weight) in enumerate(self.columns):
            frame.grid_columnconfigure(index, minsize=width, weight=weight, uniform=None)

    def _set_filter(self, value):
        self.filter = value
        self.paint()

    def reload(self, then=None):
        self.count.configure(text="Yükleniyor…")

        def done(_result):
            self.loaded = True
            self.paint()
            if then:
                then()

        def fail(error):
            self.items = []
            self._clear()
            tk.Label(self.scroll.inner, text=error, bg=CARD, fg=DANGER, font=(FONT, 13), wraplength=640,
                     justify="left").pack(anchor="w", padx=18, pady=18)
            self.count.configure(text="")

        self.run(self.load, done, fail)

    def _clear(self):
        for child in self.scroll.inner.winfo_children():
            child.destroy()

    def paint(self):
        if not self.alive() or not self.loaded:
            return
        self._clear()
        query = self.search_text()
        shown = [item for item in self.items if self.matches(item) and self._hit(item, query)]
        total = len(self.items)
        if len(shown) == total:
            self.count.configure(text=f"{total} {self.noun}")
        else:
            self.count.configure(text=f"{len(shown)} / {total} {self.noun} gösteriliyor")
        if not shown:
            self._empty(total == 0)
            self.scroll._sync()
            return
        for index, item in enumerate(shown):
            if index:
                tk.Frame(self.scroll.inner, bg=DIVIDER, height=1).pack(fill="x", padx=18)
            self._row(item)
        self.scroll.top()

    def _hit(self, item, query):
        if not query:
            return True
        return query in " ".join(str(v or "") for v in self.haystack(item)).casefold()

    def haystack(self, item):
        return item.values()

    def _empty(self, nothing):
        box = tk.Frame(self.scroll.inner, bg=CARD)
        box.pack(fill="x", pady=48)
        tk.Label(box, text=self.empty_text() if nothing else "Eşleşen kayıt yok.", bg=CARD, fg=INK,
                 font=(FONT, 15, "bold")).pack()
        sub = "İlk kaydı oluşturarak başla." if nothing and self.can_edit else "Aramayı veya filtreyi değiştir."
        tk.Label(box, text=sub, bg=CARD, fg=MUTED, font=(FONT, 12)).pack(pady=(4, 12))
        if nothing and self.can_edit:
            Button(box, f"+  {self.add_text}", lambda: self.open_form(None), kind="soft").pack()

    def _row(self, item):
        row = tk.Frame(self.scroll.inner, bg=CARD, cursor="hand2" if self.can_edit else "")
        row.pack(fill="x")
        inner = tk.Frame(row, bg=CARD)
        inner.pack(fill="x", padx=18, pady=11)
        self._grid(inner)
        self.cells(inner, item)
        arrow = tk.Label(inner, text="›" if self.can_edit else "", bg=CARD, fg=FAINT, font=(FONT, 18))
        arrow.grid(row=0, column=len(self.columns) - 1, rowspan=2, sticky="e")
        tinted = [row, inner]
        for child in inner.winfo_children():
            if getattr(child, "_tint", True):
                tinted.append(child)
            for grand in child.winfo_children():
                if getattr(grand, "_tint", True) and isinstance(child, tk.Frame):
                    tinted.append(grand)

        def paint(bg, arrow_fg):
            for widget in tinted:
                try:
                    widget.configure(bg=bg)
                except tk.TclError:
                    pass
            arrow.configure(fg=arrow_fg)

        def enter(_e):
            paint(ROW_HOVER, ACCENT)

        def leave(event):
            x, y = row.winfo_pointerxy()
            target = row.winfo_containing(x, y)
            while target is not None and target is not row:
                target = getattr(target, "master", None)
            if target is None:
                paint(CARD, FAINT)

        widgets = [row, inner] + list(inner.winfo_children())
        for child in list(inner.winfo_children()):
            widgets.extend(child.winfo_children())
        for widget in widgets:
            widget.bind("<Enter>", enter, add="+")
            widget.bind("<Leave>", leave, add="+")
            if self.can_edit:
                widget.bind("<Button-1>", lambda _e, it=item: self.open_form(it), add="+")

    def text(self, master, value, row=0, column=0, muted=False, small=False, bold=False):
        label = tk.Label(
            master, text=value or "—", bg=CARD, fg=MUTED if (muted or not value) else INK, anchor="w", width=1,
            font=(FONT, 11 if small else 13, "bold" if bold else "normal"),
        )
        label.grid(row=row, column=column, sticky="ew", padx=(0, 12))
        return label

    def flash(self, message):
        self.toast.configure(text=f"✓  {message}")

        def clear():
            if self.alive() and self.toast.winfo_exists():
                self.toast.configure(text="")

        self.app.after(2600, clear)

    # Form
    def open_form(self, item):
        if not self.can_edit:
            return
        self.close_form()
        card = tk.Frame(self.form_slot, bg=CARD, highlightthickness=1, highlightbackground=LINE, highlightcolor=LINE)
        card.pack(fill="x", pady=(0, 12))
        accent = tk.Frame(card, bg=ACCENT, height=3)
        accent.pack(fill="x")
        head = tk.Frame(card, bg=CARD)
        head.pack(fill="x", padx=20, pady=(14, 4))
        tk.Label(head, text=self.form_title(item), bg=CARD, fg=INK, font=(FONT, 16, "bold")).pack(side="left")
        close = tk.Label(head, text="✕", bg=CARD, fg=MUTED, font=(FONT, 14), cursor="hand2")
        close.pack(side="right")
        close.bind("<Button-1>", lambda _e: self.close_form())
        body = tk.Frame(card, bg=CARD)
        body.pack(fill="x", padx=20, pady=(8, 4))
        first = self.build_form(body, item)
        foot = tk.Frame(card, bg=CARD)
        foot.pack(fill="x", padx=20, pady=(8, 16))
        self.form_error = tk.Label(foot, text="", bg=CARD, fg=DANGER, font=(FONT, 12), anchor="w", justify="left")
        self.form_error.pack(side="left", fill="x", expand=True)
        self.save_button = Button(foot, "Kaydet" if item else "Oluştur", lambda: self._save(item))
        self.save_button.pack(side="right")
        Button(foot, "Vazgeç", self.close_form, kind="ghost").pack(side="right", padx=8)
        self.form = card
        for widget in self._descendants(card):
            if isinstance(widget, (tk.Entry, ttk.Combobox)):
                widget.bind("<Return>", lambda _e: self._save(item))
                widget.bind("<Escape>", lambda _e: self.close_form())
        if first is not None:
            first.focus_set()
            first.icursor("end")

    def _descendants(self, widget):
        for child in widget.winfo_children():
            yield child
            yield from self._descendants(child)

    def close_form(self):
        if self.form is not None and self.form.winfo_exists():
            self.form.destroy()
        self.form = None
        self.busy = False

    def _save(self, item):
        if self.busy:
            return
        self.form_error.configure(text="")
        try:
            work, message = self.submit(item)
        except ValueError as exc:
            self.form_error.configure(text=str(exc))
            return
        self.busy = True
        self.save_button.set_enabled(False, "Kaydediliyor…")

        def done(_r):
            self.close_form()
            self.reload(lambda: self.flash(message))

        def fail(error):
            self.busy = False
            if self.form is not None and self.form.winfo_exists():
                self.save_button.set_enabled(True, "Kaydet" if item else "Oluştur")
                self.form_error.configure(text=error)

        self.run(work, done, fail)


# --- Ekipler -----------------------------------------------------------------

class TeamsPage(ManagedPage):
    noun = "ekip"
    add_text = "Yeni ekip"
    search_hint = "Ekip, kod veya konu ara"
    columns = (("Kod", 120, 0), ("Ekip", 160, 2), ("Konu", 160, 3), ("Talep kodları", 140, 0), ("", 24, 0))

    def load(self):
        store = hesap.client()
        teams = store.teams() or []
        try:
            codes = store.request_codes() or []
        except (hesap.ApiError, ValueError):
            codes = []
        self.items = sorted(teams, key=lambda t: str(t.get("name") or "").casefold())
        self.codes = codes
        return teams

    def haystack(self, item):
        return (item.get("code"), item.get("name"), item.get("topic"))

    def _code_count(self, team):
        return sum(1 for code in self.codes if code.get("team_id") == team.get("id"))

    def cells(self, row, item):
        holder = tk.Frame(row, bg=CARD)
        holder.grid(row=0, column=0, sticky="w")
        _chip(holder, item.get("code") or "—")._tint = False
        holder.winfo_children()[0].pack(side="left")
        self.text(row, item.get("name"), column=1, bold=True)
        self.text(row, item.get("topic"), column=2, muted=True)
        count = self._code_count(item)
        self.text(row, f"{count} kod" if count else "—", column=3, muted=not count)

    def form_title(self, item):
        return "Ekibi düzenle" if item else "Yeni ekip"

    def build_form(self, body, item):
        item = item or {}
        self.f_name = tk.StringVar(value=item.get("name") or "")
        self.f_topic = tk.StringVar(value=item.get("topic") or "")
        self.f_code = tk.StringVar(value=item.get("code") or "")
        self.f_code.trace_add("write", lambda *_: self._fix(self.f_code, 8, False))
        for column, weight in ((0, 1), (1, 1), (2, 1)):
            body.grid_columnconfigure(column, weight=weight, uniform="team")
        name = self._input(body, 0, "Ekip adı", self.f_name, "Örn. Muhasebe")
        self._input(body, 1, "Konu", self.f_topic, "Ekibin ilgilendiği iş")
        self._input(body, 2, "Dış talep kodu", self.f_code, "Boşsa konudan üretilir", mono=True)
        return name

    def _input(self, body, column, label, var, hint, mono=False):
        box = _field(body, label, hint)
        box.grid(row=0, column=column, sticky="new", padx=(0 if column == 0 else 14, 0))
        entry = _entry(box, var)
        if mono:
            entry.configure(font=(MONO, 13))
        entry.pack(fill="x", ipady=7, pady=(6, 0))
        box.hint.pack(anchor="w", pady=(4, 0))
        return entry

    @staticmethod
    def _fix(var, limit, dash):
        value = var.get()
        clean = _clean(value, limit, dash)
        if clean != value:
            # Entry yazarken trace içinden değiştirmek görüntüyü bozabiliyor; bir sonraki turda düzelt.
            root = getattr(var, "_root", None)
            (root.after_idle if root else (lambda f: f()))(lambda: var.set(_clean(var.get(), limit, dash)))

    def submit(self, item):
        name = " ".join(self.f_name.get().split())
        topic = " ".join(self.f_topic.get().split())
        code = self.f_code.get().strip()
        if len(name) < 2:
            raise ValueError("Ekip adı en az 2 karakter olmalı.")
        if not topic and len(code) < 2:
            raise ValueError("Konu yaz ya da en az 2 karakterlik bir kod gir.")
        store = hesap.client()
        if item:
            return (lambda: store.update_team(item["id"], name, topic, code)), "Ekip güncellendi"
        return (lambda: store.add_team(name, code, topic)), "Ekip oluşturuldu"


# --- Talep kodları -----------------------------------------------------------

class CodesPage(ManagedPage):
    noun = "talep kodu"
    add_text = "Yeni talep kodu"
    search_hint = "Kod, başlık veya ekip ara"
    filters = (ALL, "İç", "Dış", "Tüm ekipler")
    columns = (("Kod", 150, 0), ("Başlık", 180, 3), ("Ekip", 140, 2), ("Kapsam", 170, 0), ("", 24, 0))

    def load(self):
        store = hesap.client()
        codes = store.request_codes() or []
        teams = store.teams() or []
        self.teams = sorted(teams, key=lambda t: str(t.get("name") or "").casefold())
        self.items = codes
        return codes

    def matches(self, item):
        if self.filter == ALL:
            return True
        if self.filter == "Tüm ekipler":
            return bool(item.get("all_teams"))
        return (item.get("scope") or "İç") == self.filter

    def haystack(self, item):
        return (item.get("code"), item.get("title"), item.get("team_name"), item.get("work_code"))

    def cells(self, row, item):
        holder = tk.Frame(row, bg=CARD)
        holder.grid(row=0, column=0, rowspan=2, sticky="w")
        chip = _chip(holder, item.get("code") or "—")
        chip._tint = False
        chip.pack(side="left")
        work = item.get("work_code") or ""
        title = self.text(row, item.get("title"), column=1, bold=True)
        if work and work != item.get("code"):
            title.grid_configure(rowspan=1)
            self.text(row, f"İş kodu  {work}", row=1, column=1, muted=True, small=True)
        else:
            title.grid_configure(rowspan=2)
        team = item.get("team_name") or ""
        self.text(row, ("Hedef: " + team) if item.get("all_teams") and team else team, column=2, muted=True).grid_configure(rowspan=2)
        badges = tk.Frame(row, bg=CARD)
        badges.grid(row=0, column=3, rowspan=2, sticky="w")
        scope = item.get("scope") or "İç"
        b = _chip(badges, scope, *((WARN_SOFT, WARN) if scope == "Dış" else (NEUTRAL_SOFT, INK)), mono=False)
        b._tint = False
        b.pack(side="left")
        if item.get("all_teams"):
            s = _chip(badges, "Tüm ekipler", OK_SOFT, OK, mono=False)
            s._tint = False
            s.pack(side="left", padx=(6, 0))

    def form_title(self, item):
        return f"Talep kodunu düzenle · {item.get('code')}" if item else "Yeni talep kodu"

    def _team_label(self, team):
        return f"{team.get('name')}  ({team.get('code')})" if team.get("code") else str(team.get("name"))

    def build_form(self, body, item):
        item = item or {}
        self.f_code = tk.StringVar(value=item.get("code") or "")
        self.f_title = tk.StringVar(value=item.get("title") or "")
        self.f_work = tk.StringVar(value="" if item.get("work_code") == item.get("code") else (item.get("work_code") or ""))
        self.f_all = tk.BooleanVar(value=bool(item.get("all_teams")))
        self.labels = [self._team_label(team) for team in self.teams]
        current = next((self._team_label(t) for t in self.teams if t.get("id") == item.get("team_id")), "")
        if not current and len(self.teams) == 1:
            current = self.labels[0]
        self.f_team = tk.StringVar(value=current)
        self.f_code.trace_add("write", lambda *_: TeamsPage._fix(self.f_code, 16, True))

        for column in range(3):
            body.grid_columnconfigure(column, weight=1, uniform="code")

        code_box = _field(body, "Talep kodu", "Harf, rakam ve tire · en fazla 16")
        code_box.grid(row=0, column=0, sticky="new")
        code = _entry(code_box, self.f_code)
        code.configure(font=(MONO, 13))
        code.pack(fill="x", ipady=7, pady=(6, 0))
        code_box.hint.pack(anchor="w", pady=(4, 0))

        title_box = _field(body, "Başlık", "Kullanıcının listede göreceği ad")
        title_box.grid(row=0, column=1, columnspan=2, sticky="new", padx=(14, 0))
        _entry(title_box, self.f_title).pack(fill="x", ipady=7, pady=(6, 0))
        title_box.hint.pack(anchor="w", pady=(4, 0))

        team_box = _field(body, "Ekip", "")
        team_box.grid(row=1, column=0, sticky="new", pady=(14, 0))
        self.team_caption = team_box.winfo_children()[0]
        if self.teams:
            combo = ttk.Combobox(team_box, textvariable=self.f_team, values=self.labels, state="readonly", font=(FONT, 13))
            combo.pack(fill="x", ipady=3, pady=(6, 0))
        else:
            tk.Label(team_box, text="Önce Ekipler ekranından bir ekip oluştur.", bg=CARD, fg=DANGER,
                     font=(FONT, 12)).pack(anchor="w", pady=(10, 0))

        work_box = _field(body, "İş kodu", "Boşsa talep kodu kullanılır")
        work_box.grid(row=1, column=1, sticky="new", padx=(14, 0), pady=(14, 0))
        _entry(work_box, self.f_work).pack(fill="x", ipady=7, pady=(6, 0))
        work_box.hint.pack(anchor="w", pady=(4, 0))

        scope_box = _field(body, "Kapsam", "")
        scope_box.grid(row=1, column=2, sticky="new", padx=(14, 0), pady=(14, 0))
        self.f_scope = Segmented(scope_box, ("İç", "Dış"), item.get("scope") or "İç")
        self.f_scope.configure(bg=NEUTRAL_SOFT)
        self.f_scope.pack(anchor="w", pady=(6, 0))

        share = tk.Frame(body, bg=CARD)
        share.grid(row=2, column=0, columnspan=3, sticky="w", pady=(16, 0))
        tk.Checkbutton(
            share, text="Tüm ekipler bu kodu seçebilsin", variable=self.f_all, bg=CARD, fg=INK,
            activebackground=CARD, font=(FONT, 13), highlightthickness=0, bd=0,
            command=self._sync_team_caption,
        ).pack(side="left")
        tk.Label(share, text="  Seçilen ekip talebin gideceği hedef ekip olur.", bg=CARD, fg=FAINT,
                 font=(FONT, 11)).pack(side="left")
        self._sync_team_caption()
        return code

    def _sync_team_caption(self):
        self.team_caption.configure(text="Hedef ekip" if self.f_all.get() else "Ekip")

    def submit(self, item):
        code = self.f_code.get().strip("-")
        title = " ".join(self.f_title.get().split())
        work = " ".join(self.f_work.get().split()) or code
        if len(code) < 2:
            raise ValueError("Talep kodu en az 2 karakter olmalı.")
        if len(title) < 2:
            raise ValueError("Başlık en az 2 karakter olmalı.")
        if not self.teams:
            raise ValueError("Önce bir ekip oluştur.")
        label = self.f_team.get()
        if label not in self.labels:
            raise ValueError("Hedef ekip seç." if self.f_all.get() else "Ekip seç.")
        team_id = self.teams[self.labels.index(label)]["id"]
        taken = {str(c.get("code")).upper() for c in self.items if not item or c.get("id") != item.get("id")}
        if code in taken:
            raise ValueError(f"{code} kodu zaten kullanılıyor.")
        args = (code, team_id, work, title, self.f_scope.value, self.f_all.get())
        store = hesap.client()
        if item:
            return (lambda: store.update_request_code(item["id"], *args)), f"{code} güncellendi"
        return (lambda: store.add_request_code(*args)), f"{code} oluşturuldu"


# --- Kullanıcılar ve giriş kayıtları -------------------------------------------

def _user_form(parent, app):
    form = tk.Frame(parent, bg=CARD, highlightbackground=LINE, highlightthickness=1, padx=12, pady=10)
    form.pack(fill="x", padx=22, pady=12)
    fields = {}
    for label in ("Ad", "Kullanıcı adı", "E-posta", "Parola"):
        tk.Label(form, text=label, bg=CARD, fg=MUTED, font=(FONT, 11, "bold")).pack(anchor="w")
        var = tk.StringVar()
        tk.Entry(form, textvariable=var, show="•" if label == "Parola" else "", font=(FONT, 13)).pack(fill="x", ipady=4, pady=(0, 6))
        fields[label] = var
    role = tk.StringVar(value="Kullanıcı")
    ttk.Combobox(form, textvariable=role, values=list(ROLES), state="readonly").pack(anchor="w", pady=4)

    def add():
        try:
            store = hesap.client()
            user_id = store.add_user(
                fields["Ad"].get(), fields["E-posta"].get(), fields["Parola"].get(), "",
                role.get() == "Yönetici", fields["Kullanıcı adı"].get(), role=role.get(),
            )
            teams = store.teams()
            if teams:
                store.add_member(user_id, teams[0]["id"])
        except ValueError as exc:
            messagebox.showwarning(app.title(), str(exc), parent=app)
            return
        render(parent, app, "Kullanıcılar")

    tk.Button(form, text="Kullanıcı ekle", command=add).pack(anchor="e", pady=(8, 0))


def _user_rows(parent, app, data):
    resets = data["resets"]
    if resets:
        tk.Label(parent, text="Parola istekleri", bg=CANVAS, fg=INK, font=(FONT, 14, "bold")).pack(anchor="w", padx=22, pady=(4, 4))
    for item in resets:
        line = tk.Frame(parent, bg=CANVAS)
        line.pack(fill="x", padx=22, pady=2)
        tk.Label(line, text=f"{item.get('name') or ''}  ·  {item.get('username') or ''}", bg=CANVAS, fg=INK, font=(FONT, 13)).pack(side="left")
        temporary = tk.StringVar()
        tk.Entry(line, textvariable=temporary, show="•", width=16, font=(FONT, 12)).pack(side="left", padx=8)

        def give(reset_id=item["id"], var=temporary):
            if len(var.get()) < 6:
                messagebox.showwarning(app.title(), "Geçici parola en az 6 karakter olmalı.", parent=app)
                return
            try:
                hesap.client().grant_reset(reset_id, var.get())
            except ValueError as exc:
                messagebox.showwarning(app.title(), str(exc), parent=app)
                return
            render(parent, app, "Kullanıcılar")

        tk.Button(line, text="Geçici parola ver", command=give).pack(side="left")
    users = data["users"]
    if not users:
        tk.Label(parent, text="Kullanıcı yok.", bg=CANVAS, fg=MUTED, font=(FONT, 13)).pack(anchor="w", padx=22, pady=8)
        return
    for user in users:
        tk.Label(
            parent,
            text=f"{user.get('name') or ''}  ·  {user.get('username') or ''}  ·  {user.get('role') or ''}",
            bg=CANVAS, fg=INK, font=(FONT, 13),
        ).pack(anchor="w", padx=22, pady=2)


def _log_rows(parent, rows):
    if not rows:
        tk.Label(parent, text="Giriş kaydı yok.", bg=CANVAS, fg=MUTED, font=(FONT, 13)).pack(anchor="w", padx=22, pady=8)
        return
    table = ttk.Treeview(parent, columns=("when", "event", "who"), show="headings", height=18)
    table.heading("when", text="Zaman")
    table.heading("event", text="Olay")
    table.heading("who", text="Kim")
    table.column("when", width=160, anchor="w")
    table.column("event", width=120, anchor="w")
    table.column("who", width=280, anchor="w")
    table.pack(fill="both", expand=True, padx=22, pady=(0, 12))
    for row in rows:
        table.insert("", "end", values=(
            row.get("created_at") or "",
            row.get("event") or "",
            row.get("name") or row.get("email") or "",
        ))
