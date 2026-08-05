"""
gui.py
------
CorePass'in CustomTkinter tabanlı, koyu temalı masaüstü arayüzü.

Ekranlar:
  1. Kilit Ekranı (LockScreen)   -> Master parola oluşturma / girme
  2. Ana Kasa Ekranı (VaultView)  -> Hesap listesi, ekleme, silme, şifre üretici,
                                      eklenti eşleştirme kodu
"""

import customtkinter as ctk
from tkinter import messagebox

from vault import Vault
from password_generator import generate_password, estimate_strength
import api as corepass_api

ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("dark-blue")

ACCENT = "#3DAEE9"
BG_CARD = "#1E2530"
DANGER = "#E85C5C"


class CorePassApp(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("CorePass — Yerel Şifre Kasası")
        self.geometry("880x600")
        self.minsize(760, 520)

        self.vault = Vault()
        corepass_api.bind_vault(self.vault)
        self._api_started = False

        self.container = ctk.CTkFrame(self, fg_color="transparent")
        self.container.pack(fill="both", expand=True)

        self.show_lock_screen()

    # ------------------------------------------------------------------ #
    def _clear_container(self):
        for widget in self.container.winfo_children():
            widget.destroy()

    def show_lock_screen(self):
        self._clear_container()
        LockScreen(self.container, self)

    def show_vault_view(self):
        self._clear_container()
        VaultView(self.container, self)

        if not self._api_started:
            corepass_api.run_api_server()
            self._api_started = True


class LockScreen(ctk.CTkFrame):
    def __init__(self, master, app: CorePassApp):
        super().__init__(master, fg_color="transparent")
        self.app = app
        self.pack(fill="both", expand=True)

        is_new = not Vault.vault_exists()

        wrapper = ctk.CTkFrame(self, fg_color=BG_CARD, corner_radius=16)
        wrapper.place(relx=0.5, rely=0.5, anchor="center")

        ctk.CTkLabel(
            wrapper, text="🔒 CorePass", font=ctk.CTkFont(size=28, weight="bold"), text_color=ACCENT
        ).pack(padx=50, pady=(35, 5))

        subtitle = "Yeni bir kasa oluşturun" if is_new else "Kasanızı açmak için master parolanızı girin"
        ctk.CTkLabel(wrapper, text=subtitle, text_color="gray70").pack(pady=(0, 20))

        self.pw_entry = ctk.CTkEntry(
            wrapper, placeholder_text="Master Parola", show="•", width=280, height=40
        )
        self.pw_entry.pack(padx=50, pady=6)
        self.pw_entry.bind("<Return>", lambda e: self._submit())

        if is_new:
            self.confirm_entry = ctk.CTkEntry(
                wrapper, placeholder_text="Master Parolayı Onayla", show="•", width=280, height=40
            )
            self.confirm_entry.pack(padx=50, pady=6)
            self.confirm_entry.bind("<Return>", lambda e: self._submit())
        else:
            self.confirm_entry = None

        self.error_label = ctk.CTkLabel(wrapper, text="", text_color=DANGER)
        self.error_label.pack(pady=(4, 0))

        btn_text = "Kasa Oluştur" if is_new else "Kasayı Aç"
        ctk.CTkButton(
            wrapper, text=btn_text, width=280, height=40, fg_color=ACCENT,
            command=self._submit,
        ).pack(padx=50, pady=(14, 35))

        self.is_new = is_new

    def _submit(self):
        pw = self.pw_entry.get()
        if len(pw) < 8:
            self.error_label.configure(text="Parola en az 8 karakter olmalı.")
            return

        if self.is_new:
            if pw != self.confirm_entry.get():
                self.error_label.configure(text="Parolalar eşleşmiyor.")
                return
            self.app.vault.create_vault(pw)
            self.app.show_vault_view()
        else:
            if self.app.vault.unlock(pw):
                self.app.show_vault_view()
            else:
                self.error_label.configure(text="Yanlış master parola.")


class VaultView(ctk.CTkFrame):
    def __init__(self, master, app: CorePassApp):
        super().__init__(master, fg_color="transparent")
        self.app = app
        self.pack(fill="both", expand=True, padx=20, pady=20)

        self._build_header()
        self._build_body()
        self.refresh_entries()

    # ------------------------------------------------------------------ #
    def _build_header(self):
        header = ctk.CTkFrame(self, fg_color="transparent")
        header.pack(fill="x", pady=(0, 15))

        ctk.CTkLabel(
            header, text="🔒 CorePass Kasa", font=ctk.CTkFont(size=22, weight="bold"), text_color=ACCENT
        ).pack(side="left")

        pairing_code = corepass_api.SESSION_TOKEN[:8]
        ctk.CTkLabel(
            header, text=f"Eklenti Eşleştirme Kodu: {pairing_code}",
            text_color="gray60", font=ctk.CTkFont(size=12),
        ).pack(side="left", padx=20)

        ctk.CTkButton(
            header, text="Kilitle", width=90, fg_color="transparent",
            border_width=1, border_color=DANGER, text_color=DANGER,
            command=self._lock,
        ).pack(side="right")

    def _lock(self):
        self.app.vault.lock()
        self.app.show_lock_screen()

    def _build_body(self):
        body = ctk.CTkFrame(self, fg_color="transparent")
        body.pack(fill="both", expand=True)
        body.grid_columnconfigure(0, weight=2)
        body.grid_columnconfigure(1, weight=1)
        body.grid_rowconfigure(0, weight=1)

        # --- Sol: Hesap Listesi ---
        left = ctk.CTkFrame(body, fg_color=BG_CARD, corner_radius=12)
        left.grid(row=0, column=0, sticky="nsew", padx=(0, 10))

        ctk.CTkLabel(left, text="Kayıtlı Hesaplar", font=ctk.CTkFont(size=16, weight="bold")).pack(
            anchor="w", padx=16, pady=(14, 6)
        )

        self.entries_scroll = ctk.CTkScrollableFrame(left, fg_color="transparent")
        self.entries_scroll.pack(fill="both", expand=True, padx=10, pady=(0, 10))

        # --- Sağ: Yeni Hesap Ekle + Şifre Üretici ---
        right = ctk.CTkFrame(body, fg_color=BG_CARD, corner_radius=12)
        right.grid(row=0, column=1, sticky="nsew")

        ctk.CTkLabel(right, text="Yeni Hesap Ekle", font=ctk.CTkFont(size=16, weight="bold")).pack(
            anchor="w", padx=16, pady=(14, 6)
        )

        self.site_entry = ctk.CTkEntry(right, placeholder_text="Site / Uygulama adı")
        self.site_entry.pack(fill="x", padx=16, pady=4)

        self.user_entry = ctk.CTkEntry(right, placeholder_text="Kullanıcı adı / E-posta")
        self.user_entry.pack(fill="x", padx=16, pady=4)

        pw_row = ctk.CTkFrame(right, fg_color="transparent")
        pw_row.pack(fill="x", padx=16, pady=4)
        self.password_entry = ctk.CTkEntry(pw_row, placeholder_text="Şifre")
        self.password_entry.pack(side="left", fill="x", expand=True)
        ctk.CTkButton(
            pw_row, text="Üret", width=60, fg_color=ACCENT, command=self._quick_generate
        ).pack(side="left", padx=(6, 0))

        self.strength_label = ctk.CTkLabel(right, text="", text_color="gray60")
        self.strength_label.pack(anchor="w", padx=16)

        ctk.CTkButton(
            right, text="Hesabı Kaydet", fg_color=ACCENT, command=self._add_entry
        ).pack(fill="x", padx=16, pady=(10, 20))

        # --- Şifre Üretici Ayarları ---
        ctk.CTkLabel(right, text="Şifre Üretici", font=ctk.CTkFont(size=16, weight="bold")).pack(
            anchor="w", padx=16, pady=(0, 6)
        )

        self.length_slider = ctk.CTkSlider(right, from_=8, to=32, number_of_steps=24)
        self.length_slider.set(16)
        self.length_slider.pack(fill="x", padx=16, pady=4)

        self.uppercase_var = ctk.BooleanVar(value=True)
        self.digits_var = ctk.BooleanVar(value=True)
        self.symbols_var = ctk.BooleanVar(value=True)

        for label, var in [
            ("Büyük Harf (A-Z)", self.uppercase_var),
            ("Rakam (0-9)", self.digits_var),
            ("Sembol (!@#$)", self.symbols_var),
        ]:
            ctk.CTkCheckBox(right, text=label, variable=var).pack(anchor="w", padx=16, pady=2)

        ctk.CTkButton(
            right, text="Yeni Şifre Üret ve Panoya Kopyala", fg_color="#2C3648",
            command=self._generate_and_copy,
        ).pack(fill="x", padx=16, pady=16)

    # ------------------------------------------------------------------ #
    def _quick_generate(self):
        pwd = generate_password(length=int(self.length_slider.get()))
        self.password_entry.delete(0, "end")
        self.password_entry.insert(0, pwd)
        self.strength_label.configure(text=f"Güç: {estimate_strength(pwd)}")

    def _generate_and_copy(self):
        pwd = generate_password(
            length=int(self.length_slider.get()),
            use_uppercase=self.uppercase_var.get(),
            use_digits=self.digits_var.get(),
            use_symbols=self.symbols_var.get(),
        )
        self.clipboard_clear()
        self.clipboard_append(pwd)
        messagebox.showinfo("CorePass", f"Yeni şifre panoya kopyalandı.\nGüç: {estimate_strength(pwd)}")

    def _add_entry(self):
        site = self.site_entry.get().strip()
        user = self.user_entry.get().strip()
        pwd = self.password_entry.get()

        if not site or not user or not pwd:
            messagebox.showwarning("CorePass", "Site, kullanıcı adı ve şifre zorunludur.")
            return

        self.app.vault.add_entry(site, user, pwd)
        self.site_entry.delete(0, "end")
        self.user_entry.delete(0, "end")
        self.password_entry.delete(0, "end")
        self.strength_label.configure(text="")
        self.refresh_entries()

    def refresh_entries(self):
        for widget in self.entries_scroll.winfo_children():
            widget.destroy()

        entries = self.app.vault.list_entries()
        if not entries:
            ctk.CTkLabel(self.entries_scroll, text="Henüz kayıtlı hesap yok.", text_color="gray50").pack(
                pady=20
            )
            return

        for entry in entries:
            self._build_entry_row(entry)

    def _build_entry_row(self, entry: dict):
        row = ctk.CTkFrame(self.entries_scroll, fg_color="#141922", corner_radius=8)
        row.pack(fill="x", pady=4, padx=2)

        info = ctk.CTkFrame(row, fg_color="transparent")
        info.pack(side="left", fill="x", expand=True, padx=10, pady=8)

        ctk.CTkLabel(info, text=entry["site"], font=ctk.CTkFont(weight="bold")).pack(anchor="w")
        ctk.CTkLabel(info, text=entry["username"], text_color="gray60", font=ctk.CTkFont(size=12)).pack(
            anchor="w"
        )

        ctk.CTkButton(
            row, text="Kopyala", width=70,
            command=lambda: self._copy_password(entry["password"]),
        ).pack(side="right", padx=(0, 8), pady=8)

        ctk.CTkButton(
            row, text="Sil", width=50, fg_color=DANGER, hover_color="#B84545",
            command=lambda: self._delete_entry(entry["id"]),
        ).pack(side="right", padx=(0, 6), pady=8)

    def _copy_password(self, password: str):
        self.clipboard_clear()
        self.clipboard_append(password)

    def _delete_entry(self, entry_id: str):
        if messagebox.askyesno("CorePass", "Bu hesabı silmek istediğinize emin misiniz?"):
            self.app.vault.delete_entry(entry_id)
            self.refresh_entries()
