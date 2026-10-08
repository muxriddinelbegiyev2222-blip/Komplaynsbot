import sys
import customtkinter as ctk
from tkinter import messagebox
from src.db_manager import DatabaseManager
from src.ui_dashboard import DashboardApp

class LoginWindow(ctk.CTk):
    def __init__(self):
        super().__init__()

        self.title("Tizimga kirish — Kadastr Monitoring")
        self.geometry("420x420")
        self.resizable(False, False)

        ctk.set_appearance_mode("System")
        ctk.set_default_color_theme("blue")

        self.db = DatabaseManager()

        self._build_ui()

    def _build_ui(self):
        frame = ctk.CTkFrame(self, corner_radius=12)
        frame.pack(padx=25, pady=25, fill="both", expand=True)

        lbl_logo = ctk.CTkLabel(
            frame,
            text="🛡 AVTORIZATSIYA",
            font=ctk.CTkFont(size=20, weight="bold")
        )
        lbl_logo.pack(pady=(25, 5))

        lbl_sub = ctk.CTkLabel(
            frame,
            text="Komplayens nazorat tizimi",
            font=ctk.CTkFont(size=12),
            text_color="gray"
        )
        lbl_sub.pack(pady=(0, 25))

        self.e_username = ctk.CTkEntry(frame, width=280, placeholder_text="Login")
        self.e_username.pack(pady=8)

        self.e_password = ctk.CTkEntry(frame, width=280, placeholder_text="Parol", show="*")
        self.e_password.pack(pady=8)
        self.e_password.bind("<Return>", lambda e: self.do_login())

        btn_login = ctk.CTkButton(
            frame,
            text="Kirish",
            width=280,
            command=self.do_login,
            height=38,
            font=ctk.CTkFont(size=14, weight="bold")
        )
        btn_login.pack(pady=25)

    def do_login(self):
        u = self.e_username.get().strip()
        p = self.e_password.get().strip()

        if not u or not p:
            messagebox.showwarning("Ogohlantirish", "Login va parolni kiriting!")
            return

        role = self.db.check_user_login(u, p)
        if role:
            self.destroy()
            app = DashboardApp(username=u, role=role, db=self.db)
            app.mainloop()
        else:
            messagebox.showerror("Xatolik", "Login yoki parol noto‘g‘ri!")


if __name__ == "__main__":
    app = LoginWindow()
    app.mainloop()
