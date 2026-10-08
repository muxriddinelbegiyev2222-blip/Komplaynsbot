import os
import sys
import customtkinter as ctk
from tkinter import messagebox
from src.data_loader import DataLoader
from src.ui_dashboard import DashboardApp
from src.db_manager import DatabaseManager


class LoginWindow(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("Tizimga kirish - Komplayens Nazorat")
        self.geometry("450x380")
        self.eval('tk::PlaceWindow . center')
        ctk.set_appearance_mode("Light")
        self.configure(fg_color="#ECEFF4")

        self.db = DatabaseManager()
        self.data_loader = None
        self._build_login_ui()

    def _build_login_ui(self):
        for w in self.winfo_children():
            w.destroy()

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
        self.password.bind("<Return>", lambda e: self.check_login())

        ctk.CTkButton(frame, text="Tizimga kirish ➔", width=300, height=40,
                      fg_color="#1B4D7E", hover_color="#1E3A56",
                      font=ctk.CTkFont(size=14, weight="bold"),
                      command=self.check_login).pack()

    def check_login(self):
        user = self.username.get().strip()
        pwd = self.password.get().strip()

        role = self.db.check_user_login(user, pwd)

        if role:
            self._launch_dashboard(role)
        else:
            messagebox.showerror("Xatolik",
                                 "Login yoki parol noto'g'ri yoxud akkaunt bloklangan!")

    def _launch_dashboard(self, role):
        """Login oynasining O'ZINI dashboard'ga aylantiradi (yangi CTk yaratmaydi)."""
        # Kerakli papkalar
        os.makedirs("data", exist_ok=True)
        os.makedirs(os.path.join("data", "attachments"), exist_ok=True)
        os.makedirs(os.path.join("data", "topshiriqlar"), exist_ok=True)
        os.makedirs(os.path.join("data", "backup"), exist_ok=True)
        os.makedirs("assets", exist_ok=True)

        # Login oynasini yashirish
        for w in self.winfo_children():
            w.destroy()

        # Dashboard'ni qurish uchun maxsus yondashuv:
        # DashboardApp'ni alohida oyna sifatida emas, balki mavjud root ichida quramiz
        try:
            self.data_loader = DataLoader()
        except Exception as e:
            messagebox.showerror("Xatolik", f"Ma'lumotlar bazasini yuklab bo'lmadi:\n{e}")
            return

        # Root oynani dashboard uchun tayyorlaymiz
        self.withdraw()  # yashirin

        # MUHIM: DashboardApp yangi CTk emas, lekin biz uning UI qismini
        # to'g'ridan-to'g'ri chaqira olmaymiz. Shuning uchun eng oson yo'l:
        # LoginWindow'ni yo'q qilmasdan, uning ichida DashboardApp'ni
        # Toplevel sifatida ochish.
        self._open_dashboard_window(role)

    def _open_dashboard_window(self, role):
        """Dashboard'ni alohida oyna sifatida ochadi (login yopiq qoladi)."""
        try:
            dash = DashboardApp(self.data_loader, current_role=role)
            dash.mainloop()
        except Exception as e:
            messagebox.showerror("Xatolik",
                                 f"Dashboard ochilmadi:\n{type(e).__name__}: {e}")
            self.deiconify()  # login oynasini qaytarish


if __name__ == "__main__":
    login_app = LoginWindow()
    login_app.mainloop()
