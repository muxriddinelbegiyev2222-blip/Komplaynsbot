import os
import sys
import tkinter as tk
import customtkinter as ctk
from tkinter import messagebox
from src.data_loader import DataLoader
from src.ui_dashboard import DashboardApp
from src.db_manager import DatabaseManager


class App(ctk.CTk):
    """Bitta root oyna: login ham, dashboard ham shu yerda ishlaydi."""
    def __init__(self):
        super().__init__()
        ctk.set_appearance_mode("Light")
        self.configure(fg_color="#ECEFF4")
        self.title("Komplayens Nazorat")
        self.geometry("450x380")
        self.eval('tk::PlaceWindow . center')

        # Kerakli papkalar
        os.makedirs("data", exist_ok=True)
        os.makedirs(os.path.join("data", "attachments"), exist_ok=True)
        os.makedirs(os.path.join("data", "topshiriqlar"), exist_ok=True)
        os.makedirs(os.path.join("data", "backup"), exist_ok=True)
        os.makedirs("assets", exist_ok=True)

        self.db = DatabaseManager()
        self.data_loader = None
        self.dashboard = None
        self._show_login()

    def _show_login(self):
        for w in self.winfo_children():
            w.destroy()

        self.title("Tizimga kirish - Komplayens Nazorat")
        self.geometry("450x380")

        frame = ctk.CTkFrame(self, fg_color="#FFFFFF", corner_radius=10,
                             border_width=1, border_color="#CBD5E1")
        frame.pack(fill="both", expand=True, padx=20, pady=20)

        ctk.CTkLabel(frame, text="🔒 TIZIMGA KIRISH",
                     font=ctk.CTkFont(size=18, weight="bold"),
                     text_color="#0F2537").pack(pady=(30, 5))
        ctk.CTkLabel(frame,
                     text="Onlayn korrupsiyaga qarshi monitoring tizimi",
                     font=ctk.CTkFont(size=12, slant="italic"),
                     text_color="#64748B").pack(pady=(0, 20))

        ctk.CTkLabel(frame, text="Login:",
                     font=ctk.CTkFont(size=12, weight="bold")).pack(anchor="w", padx=50)
        self.username = ctk.CTkEntry(frame, placeholder_text="Foydalanuvchi nomi",
                                      width=300, height=35)
        self.username.pack(pady=(5, 15))

        ctk.CTkLabel(frame, text="Parol:",
                     font=ctk.CTkFont(size=12, weight="bold")).pack(anchor="w", padx=50)
        self.password = ctk.CTkEntry(frame, placeholder_text="Maxfiy so'z",
                                      show="*", width=300, height=35)
        self.password.pack(pady=(5, 20))
        self.password.bind("<Return>", lambda e: self._check_login())

        ctk.CTkButton(frame, text="Tizimga kirish ➔", width=300, height=40,
                      fg_color="#1B4D7E", hover_color="#1E3A56",
                      font=ctk.CTkFont(size=14, weight="bold"),
                      command=self._check_login).pack()

    def _check_login(self):
        user = self.username.get().strip()
        pwd = self.password.get().strip()
        role = self.db.check_user_login(user, pwd)
        if role:
            self._launch_dashboard(role)
        else:
            messagebox.showerror("Xatolik",
                                 "Login yoki parol noto'g'ri yoxud akkaunt bloklangan!")

    def _launch_dashboard(self, role):
        # Login UI'ni o'chirish
        for w in self.winfo_children():
            w.destroy()

        # Root oynani dashboard uchun tayyorlash
        self.title("Komplayens Nazorat Tizimi")
        self.geometry("1440x920")
        self.minsize(1220, 740)
        self.eval('tk::PlaceWindow . center')

        try:
            self.data_loader = DataLoader()
        except Exception as e:
            messagebox.showerror("Xatolik",
                                 f"Ma'lumotlar bazasini yuklab bo'lmadi:\n{e}")
            self._show_login()
            return

        # Dashboard'ni mavjud root ichida quramiz
        try:
            self.dashboard = DashboardApp.__new__(DashboardApp)
            # DashboardApp'ni CTk o'rniga mavjud root ustida ishga tushirish
            # Buning uchun ui_dashboard.py da kichik o'zgarish kerak (pastga qarang)
            DashboardApp.__init__(self.dashboard, self.data_loader, current_role=role,
                                  _root_override=self)
        except Exception as e:
            messagebox.showerror("Xatolik",
                                 f"Dashboard ochilmadi:\n{type(e).__name__}: {e}")
            self._show_login()


if __name__ == "__main__":
    app = App()
    app.mainloop()
