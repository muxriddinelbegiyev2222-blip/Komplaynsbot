import os
import gspread
from oauth2client.service_account import ServiceAccountCredentials

key_path = os.path.join("data", "credentials.json")
if not os.path.exists(key_path):
    key_path = "credentials.json"

print(f"1. credentials.json fayli tekshirilmoqda: {os.path.exists(key_path)}")

try:
    scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
    creds = ServiceAccountCredentials.from_json_keyfile_name(key_path, scope)
    client = gspread.authorize(creds)
    
    # Aniq ID orqali ochish (eng ishonchli usul)
    spreadsheet = client.open_by_key("17igQpL4sNkEyQnIkJ58oqWVKQpVHh0mj4njx-UJXN34")
    print("2. Google Sheets bilan ulanish: MUVAFFAQIYATLI!")
    
    sheet = spreadsheet.worksheet("Murojaatlar")
    sheet.update_acell("A1", "#")
    print("3. Jadvalga yozish: MUVAFFAQIYATLI! A1 katagiga '#' yozildi.")
except Exception as e:
    print(f"\nXATOLIK YUZ BERDI:\n{e}")
