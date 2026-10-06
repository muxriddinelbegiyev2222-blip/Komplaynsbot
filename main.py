import os
import sys

# PyInstaller uchun majburiy importlar:
import pandas as pd
import openpyxl
import customtkinter as ctk
import matplotlib
import PIL
import docx

from src.data_loader import DataLoader
from src.ui_dashboard import DashboardApp
from tkinter import messagebox

def main():
    try:
        # Baza mavjud bo'lsa ochadi, bo'lmasa o'zi data/ ichida yaratadi
        loader = DataLoader()
        
        # Agar dastlabki murojaatlar fayli bo'lsa uni yuklab oladi
        default_file = os.path.join("data", "murojaatlar.xlsx")
        if os.path.exists(default_file) and loader.df.empty:
            loader.load_from_excel(default_file)

        app = DashboardApp(loader)
        app.mainloop()
    except Exception as e:
        messagebox.showerror("Xatolik", f"Dasturda kutilmagan xatolik: {str(e)}")

if __name__ == "__main__":
    main()
