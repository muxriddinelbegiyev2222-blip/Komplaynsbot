import os
import sys
from src.data_loader import DataLoader
from src.ui_dashboard import DashboardApp

def main():
    # Kerakli kataloglar mavjudligini ta'minlash
    os.makedirs("data", exist_ok=True)
    os.makedirs(os.path.join("data", "attachments"), exist_ok=True)
    os.makedirs(os.path.join("data", "topshiriqlar"), exist_ok=True)
    os.makedirs(os.path.join("data", "backup"), exist_ok=True)
    os.makedirs("assets", exist_ok=True)

    # Ma'lumotlar yuklovchisi va asosiy dashboard oynasini ishga tushirish
    data_loader = DataLoader()
    app = DashboardApp(data_loader)
    app.mainloop()

if __name__ == "__main__":
    main()
