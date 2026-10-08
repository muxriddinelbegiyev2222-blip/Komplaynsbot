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

        # Bazani ulaymiz
        self.db = DatabaseManager()

        frame = ctk.CTkFrame(self, fg_color="#FFFFFF", corner_radius=10, border_width=1, border_color="#CBD5E1")
        frame.pack(fill="both", expand=True, padx=20, pady=20)

        ctk.CTkLabel(frame, text="🔒 TIZIMGA KIRISH", font=ctk.CTkFont(size=18, weight="bold"), text_color="#0F2537").pack(pady=(30, 5))
        ctk.CTkLabel(frame, text="Onlayn korrupsiyaga qarshi monitoring tizimi", font=ctk.CTkFont(size=12, slant="italic"), text_color="#64748B").pack(pady=(0, 20))

        ctk.CTkLabel(frame, text="Login:", font=ctk.CTkFont(size=12, weight="bold")).pack(anchor="w", padx=50)
        self.username = ctk.CTkEntry(frame, placeholder_text="Foydalanuvchi nomi", width=300, height=35)
        self.username.pack(pady=(5, 15))

        ctk.CTkLabel(frame, text="Parol:", font=ctk.CTkFont(size=12, weight="bold")).pack(anchor="w", padx=50)
        self.password = ctk.CTkEntry(frame, placeholder_text="Maxfiy so'z", show="*", width=300, height=35)
        self.password.pack(pady=(5, 20))
        
        # Enter bosilganda ham kirish
        self.password.bind("<Return>", lambda event: self.check_login())

        ctk.CTkButton(frame, text="Tizimga kirish ➔", width=300, height=40, fg_color="#1B4D7E", hover_color="#1E3A56", font=ctk.CTkFont(size=14, weight="bold"), command=self.check_login).pack()

    def check_login(self):
        user = self.username.get().strip()
        pwd = self.password.get().strip()

        # Tizim bazasidan (users jadvalidan) tekshirish
        role = self.db.check_user_login(user, pwd)
        
        if role:
            self.destroy()
            start_app(role=role)
        else:
            messagebox.showerror("Xatolik", "Login yoki parol noto'g'ri yoxud akkaunt bloklangan!")

def start_app(role):
    # Dastur ishlashi uchun kerakli papkalarni yaratish
    os.makedirs("data", exist_ok=True)
    os.makedirs(os.path.join("data", "attachments"), exist_ok=True)
    os.makedirs(os.path.join("data", "topshiriqlar"), exist_ok=True)
    os.makedirs(os.path.join("data", "backup"), exist_ok=True)
    os.makedirs("assets", exist_ok=True)

    data_loader = DataLoader()
    # MANA SHU YERDA ZANJIR ASL HOLIGA QAYTARILDI:
    app = DashboardApp(data_loader, current_role=role)
    app.mainloop()

if __name__ == "__main__":
    login_app = LoginWindow()
    login_app.mainloop()
