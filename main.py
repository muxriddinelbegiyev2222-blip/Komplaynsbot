import os
import sys

if getattr(sys, 'frozen', False):
    BASE_DIR = os.path.dirname(sys.executable)
else:
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))

os.chdir(BASE_DIR)

import customtkinter as ctk
from tkinter import messagebox
from src.data_loader import DataLoader
from src.ui_dashboard import DashboardApp
from src.db_manager import DatabaseManager
from src.logger import log_error, log_info


class LoginWindow(ctk.CTk):
    def __init__(self, db):
        super().__init__()
        self.db = db
        self.authenticated_role = None
        self.authenticated_user = None

        self.title("Tizimga kirish - Komplayens Nazorat")
        self.geometry("450x420")
        try:
            self.eval('tk::PlaceWindow . center')
        except Exception:
            pass
        ctk.set_appearance_mode("Light")
        self.configure(fg_color="#ECEFF4")

        frame = ctk.CTkFrame(self, fg_color="#FFFFFF", corner_radius=10,
                             border_width=1, border_color="#CBD5E1")
        frame.pack(fill="both", expand=True, padx=20, pady=20)

        ctk.CTkLabel(frame, text="🔒 TIZIMGA KIRISH",
                     font=ctk.CTkFont(size=18, weight="bold"),
                     text_color="#0F2537").pack(pady=(30, 5))
        ctk.CTkLabel(frame,
                     text="Onlayn korrupsiyaga qarshi monitoring tizimi",
                     font=ctk.CTkFont(size=12, slant="italic"),
                     text_color="#64748B").pack(pady=(0, 15))

        ctk.CTkLabel(frame, text="Login:",
                     font=ctk.CTkFont(size=12, weight="bold")).pack(anchor="w", padx=50)
        self.username = ctk.CTkEntry(frame, placeholder_text="Foydalanuvchi nomi",
                                      width=300, height=35)
        self.username.pack(pady=(5, 12))
        self.username.bind("<Return>", lambda e: self.password.focus_set())

        ctk.CTkLabel(frame, text="Parol:",
                     font=ctk.CTkFont(size=12, weight="bold")).pack(anchor="w", padx=50)
        self.password = ctk.CTkEntry(frame, placeholder_text="Maxfiy so'z",
                                      show="*", width=300, height=35)
        self.password.pack(pady=(5, 15))
        self.password.bind("<Return>", lambda e: self.check_login())

        self.status_label = ctk.CTkLabel(frame, text="",
                                          font=ctk.CTkFont(size=11),
                                          text_color="#C0392B")
        self.status_label.pack(pady=(0, 5))

        self.login_btn = ctk.CTkButton(frame, text="Tizimga kirish ➔", width=300, height=40,
                                        fg_color="#1B4D7E", hover_color="#1E3A56",
                                        font=ctk.CTkFont(size=14, weight="bold"),
                                        command=self.check_login)
        self.login_btn.pack()

    def check_login(self):
        user = self.username.get().strip()
        pwd = self.password.get().strip()

        if not user or not pwd:
            self.status_label.configure(text="⚠️ Login va parolni kiriting!", text_color="#C0392B")
            return

        self.status_label.configure(text="⏳ Tekshirilmoqda...", text_color="#D35400")
        self.login_btn.configure(state="disabled")
        self.update_idletasks()

        try:
            role = self.db.check_user_login(user, pwd)
        except Exception as e:
            log_error(e, "check_login")
            self.status_label.configure(text=f"❌ Xatolik: {e}", text_color="#C0392B")
            self.login_btn.configure(state="normal")
            return

        if role:
            self.authenticated_role = role
            self.authenticated_user = user
            self.status_label.configure(text="✅ Muvaffaqiyatli!", text_color="#1B5E20")
            self.update_idletasks()
            self.after(200, self._finish_login)
        else:
            self.status_label.configure(
                text="❌ Login yoki parol noto'g'ri (yoki 5 daqiqa bloklangan)",
                text_color="#C0392B")
            self.login_btn.configure(state="normal")
            self.password.delete(0, 'end')

    def _finish_login(self):
        try:
            self.quit()
            self.destroy()
        except Exception:
            pass


def main():
    os.makedirs(os.path.join(BASE_DIR, "data"), exist_ok=True)
    os.makedirs(os.path.join(BASE_DIR, "data", "attachments"), exist_ok=True)
    os.makedirs(os.path.join(BASE_DIR, "data", "topshiriqlar"), exist_ok=True)
    os.makedirs(os.path.join(BASE_DIR, "data", "backup"), exist_ok=True)
    os.makedirs(os.path.join(BASE_DIR, "assets"), exist_ok=True)

    db = DatabaseManager()
    login_app = LoginWindow(db=db)
    login_app.mainloop()

    if login_app.authenticated_role:
        try:
            data_loader = DataLoader(db=db)
            app = DashboardApp(
                data_loader,
                current_role=login_app.authenticated_role,
                current_user=login_app.authenticated_user or "admin"
            )
            app.mainloop()
        except Exception as e:
            log_error(e, "open_dashboard")
            messagebox.showerror(
                "Xatolik",
                f"Dashboard ochilmadi:\n{type(e).__name__}: {e}"
            )


if __name__ == "__main__":
    main()
