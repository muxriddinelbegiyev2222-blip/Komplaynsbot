import os
import sys
from src.data_loader import DataLoader
from src.ui_dashboard import DashboardApp
import customtkinter as ctk
from tkinter import filedialog, messagebox

def main():
    # Standart excel yo'li
    default_excel = os.path.join("data", "murojaatlar.xlsx")
    
    excel_path = None
    if os.path.exists(default_excel):
        excel_path = default_excel
    else:
        # Fayl topilmasa, foydalanuvchidan tanlashni so'raydi
        ctk.set_appearance_mode("System")
        root = ctk.CTk()
        root.withdraw()
        messagebox.showinfo("Faylni tanlang", "Baza sifatida ishlatiladigan Excel (.xlsx) faylini tanlang.")
        selected = filedialog.askopenfilename(filetypes=[("Excel files", "*.xlsx *.xls")])
        root.destroy()
        if selected:
            excel_path = selected
        else:
            sys.exit(0)

    try:
        loader = DataLoader(excel_path)
        app = DashboardApp(loader)
        app.mainloop()
    except Exception as e:
        messagebox.showerror("Xatolik", f"Dasturni ishga tushirishda xatolik: {str(e)}")

if __name__ == "__main__":
    main()
