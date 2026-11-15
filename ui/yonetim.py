"""Yönetici ekranları: ekip, talep kodu, kullanıcı, parola isteği ve giriş kaydı."""

import threading
import tkinter as tk
from tkinter import messagebox, ttk

import hesap

FONT = ".AppleSystemUIFont"
CARD = "#FFFFFF"
INK = "#14182B"
MUTED = "#6B7287"
LINE = "#E3E6EE"
CANVAS = "#F3F4F7"
ROLES = ("Yönetici", "Sorumlu", "Kullanıcı", "İzleyici")


def render(parent, app, page):
    for child in parent.winfo_children():
        child.destroy()
    parent.pack(fill="both", expand=True)
    token = getattr(app, "_admin_token", 0) + 1
    app._admin_token = token
    _title(parent, page)
    status = tk.Label(parent, text="Yükleniyor…", bg=CANVAS, fg=MUTED, font=(FONT, 13))
    status.pack(anchor="w", padx=22, pady=8)
    if page == "Ekipler":
        _team_form(parent, app)
    elif page == "Kullanıcılar":
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
    if page == "Ekipler":
        return store.teams()
    if page == "Talep kodları":
        return store.request_codes()
    if page == "Kullanıcılar":
        return {"resets": store.resets(), "users": store.users()}
    return store.login_logs()


def _paint(parent, app, page, data):
    if page == "Ekipler":
        _team_rows(parent, data)
    elif page == "Talep kodları":
        _code_rows(parent, data)
    elif page == "Kullanıcılar":
        _user_rows(parent, app, data)
    else:
        _log_rows(parent, data)


def _title(parent, text):
    tk.Label(parent, text=text, bg=CANVAS, fg=INK, font=(FONT, 20, "bold")).pack(anchor="w", padx=22, pady=(8, 8))


def _team_form(parent, app):
    name = tk.StringVar()
    topic = tk.StringVar()
    row = tk.Frame(parent, bg=CANVAS)
    row.pack(fill="x", padx=22)
    tk.Entry(row, textvariable=name, width=22, font=(FONT, 13)).pack(side="left", ipady=4)
    tk.Entry(row, textvariable=topic, width=22, font=(FONT, 13)).pack(side="left", padx=8, ipady=4)

    def add():
        try:
            hesap.client().add_team(name.get(), "", topic.get())
        except ValueError as exc:
            messagebox.showwarning(app.title(), str(exc), parent=app)
            return
        render(parent, app, "Ekipler")

    tk.Button(row, text="Ekle", command=add).pack(side="left")


def _team_rows(parent, teams):
    if not teams:
        tk.Label(parent, text="Ekip yok.", bg=CANVAS, fg=MUTED, font=(FONT, 13)).pack(anchor="w", padx=22, pady=8)
        return
    for team in teams:
        tk.Label(
            parent,
            text=f"{team['code']}  ·  {team['name']}  ·  {team.get('topic') or ''}",
            bg=CANVAS, fg=INK, font=(FONT, 13),
        ).pack(anchor="w", padx=22, pady=2)


def _code_rows(parent, items):
    if not items:
        tk.Label(parent, text="Talep kodu yok.", bg=CANVAS, fg=MUTED, font=(FONT, 13)).pack(anchor="w", padx=22, pady=8)
        return
    for item in items:
        shared = "  ·  tüm ekipler" if item.get("all_teams") else ""
        tk.Label(
            parent,
            text=f"{item['code']}  ·  {item.get('title') or ''}  ·  {item.get('team_name') or ''}{shared}",
            bg=CANVAS, fg=INK, font=(FONT, 13),
        ).pack(anchor="w", padx=22, pady=2)


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
